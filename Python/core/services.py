# core/services.py
import os
import time
from typing import Any, Optional, List, Dict
from PyQt5 import QtCore

from core.arduino_linker import ArduinoLink


class SynthesisManager(QtCore.QObject):
    """
    Manages the synthesis process in the background and reports progress to the UI.
    """
    status_updated = QtCore.pyqtSignal(int, int)
    synthesis_finished = QtCore.pyqtSignal()
    log_message = QtCore.pyqtSignal(str)

    def __init__(self, services):
        super().__init__()
        self.s = services
        self._protocol = []
        self._worker = None
        self._total_cycles = 0
        self._is_paused = False

    def set_protocol(self, protocol: List[list]):
        self._protocol = protocol

    def set_total_cycles(self, cycles: int):
        self._total_cycles = cycles

    def start_synthesis(self):
        if not self._protocol:
            self.log_message.emit("[ERR] Protocol is not set.")
            return
        if self._total_cycles <= 0:
            self.log_message.emit("[ERR] Sequence file with valid cycles is not loaded.")
            return
        if self.s.arduino is None:
            self.log_message.emit("[ERR] Arduino is not connected.")
            return

        self._worker = SynthesisWorker(
            self.s.arduino,
            self._protocol,
            self._total_cycles,
            self.s.sequence_file_path
        )
        self._worker.status_updated.connect(self.status_updated)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.log_message.connect(self.log_message)
        self._worker.start()
        self.log_message.emit("[RUN] Synthesis started.")

    def toggle_pause_resume(self):
        """Toggles the pause state."""
        if not self._worker or not self._worker.isRunning():
            return

        self._is_paused = not self._is_paused
        if self._is_paused:
            self._worker.pause()
            self.log_message.emit("[PAUSE] Synthesis paused.")
        else:
            self._worker.resume()
            self.log_message.emit("[RESUME] Synthesis resumed.")
        return self._is_paused

    def stop_synthesis(self):
        if self._worker and self._worker.isRunning():
            if self._is_paused:
                self.toggle_pause_resume()
            self._worker.requestInterruption()
            self.log_message.emit("[STOP] Stop request sent.")

    def _on_worker_finished(self):
        self.log_message.emit("[DONE] Synthesis finished.")
        self.synthesis_finished.emit()
        self._worker = None
        self._is_paused = False


class SynthesisWorker(QtCore.QThread):
    status_updated = QtCore.pyqtSignal(int, int)
    log_message = QtCore.pyqtSignal(str)

    def __init__(self, arduino_link, protocol, total_cycles, sequence_filepath):
        super().__init__()
        self.arduino = arduino_link
        self.protocol = protocol
        self.total_cycles = total_cycles
        self.sequence_filepath = sequence_filepath
        self.sequence_data: Dict[int, List[str]] = {}
        self._is_paused = False
        self._mutex = QtCore.QMutex()

    def pause(self):
        with QtCore.QMutexLocker(self._mutex):
            self._is_paused = True

    def resume(self):
        with QtCore.QMutexLocker(self._mutex):
            self._is_paused = False

    def _load_and_parse_sequence_file(self) -> bool:
        """Pre-reads the sequence file, parses data for each cycle, and stores it."""
        try:
            with open(self.sequence_filepath, 'r', encoding='utf-8') as f:
                current_cycle = -1
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    if line.lower().startswith("cycle :"):
                        current_cycle = int(line.split(':')[1].strip())
                        if current_cycle not in self.sequence_data:
                            self.sequence_data[current_cycle] = []
                    elif line.lower().startswith("head_"):
                        if current_cycle == -1:
                            current_cycle = 1
                            if current_cycle not in self.sequence_data:
                                self.sequence_data[current_cycle] = []
                        self.sequence_data[current_cycle].append(line)

            if not self.sequence_data:
                self.log_message.emit(
                    f"[WARN] No valid data found in sequence file: {os.path.basename(self.sequence_filepath)}")
                return True

            self.log_message.emit(
                f"[INFO] Successfully loaded and parsed sequence file: {os.path.basename(self.sequence_filepath)}")
            return True
        except Exception as e:
            self.log_message.emit(f"[ERR] Failed to load or parse sequence file: {e}")
            return False

    def run(self):
        if not self._load_and_parse_sequence_file():
            return

        try:
            self.arduino.send(f"linear_init;")
            self.log_message.emit(f"  [SEND] linear_init")
            resp = ""
            while (resp != "OK"):
                self.arduino.send(f"is_ready;")
                resp = self.arduino.read_line(1)
                print(resp)
                self.msleep(50)

            for cycle in range(1, self.total_cycles + 1):
                if self.isInterruptionRequested(): break
                self.log_message.emit(f"--- Starting Cycle {cycle}/{self.total_cycles} ---")
                step_num = 0
                for step, vol, inc in self.protocol:
                    step_num += 1
                    if self.isInterruptionRequested(): break

                    while True:
                        with QtCore.QMutexLocker(self._mutex):
                            if not self._is_paused:
                                break
                        self.sleep(1)

                    self.status_updated.emit(cycle, step_num)
                    self.log_message.emit(f"Cycle {cycle}, Step {step}, Vol {vol}, Inc {inc}")

                    if step.lower() == 'coupling':

                        try:
                            self.arduino.send(f"linear_init;")
                            self.log_message.emit(f"  [SEND] linear_init")
                            resp = ""
                            while (resp != "OK"):
                                self.arduino.send(f"is_ready;")
                                resp = self.arduino.read_line(1)
                                print(resp)
                                self.msleep(50)

                        except:
                            pass

                        data_lines_for_cycle = self.sequence_data.get(cycle, [])
                        if not data_lines_for_cycle:
                            self.log_message.emit(f"[INFO] Cycle {cycle}: No coupling data found, skipping.")
                            continue

                        self.log_message.emit(
                            f"  > Coupling: Processing {len(data_lines_for_cycle)} lines for cycle {cycle}.")

                        self.arduino.send(f"ph_power_up;")
                        self.log_message.emit(f"  [SEND] ph_power_up")
                        resp = ""
                        while (resp != "OK"):
                            self.arduino.send(f"is_ready;")
                            resp = self.arduino.read_line(1)
                            print(resp)
                            self.msleep(50)

                        for line in data_lines_for_cycle:
                            if self.isInterruptionRequested(): break

                            try:
                                command = f"{line};"
                                self.arduino.send(command)

                                MAX_ATTEMPTS = 15
                                attempts = 0
                                response_ok = False
                                response_buffer = ""  # Buffer variable to accumulate received data

                                while attempts < MAX_ATTEMPTS:
                                    if self.isInterruptionRequested():
                                        self.log_message.emit("    [INFO] Stop requested during wait.")
                                        break

                                    resp = self.arduino.read_line(1)
                                    attempts += 1

                                    if resp is None:
                                        self.log_message.emit(
                                            f"    [WAIT] Attempt {attempts}/{MAX_ATTEMPTS}: No response from Master.")
                                        continue

                                    # Add the received data piece to the buffer
                                    cleaned_resp = resp.strip()
                                    response_buffer += cleaned_resp
                                    # self.log_message.emit(
                                    #    f"    [RECV] Got data: '{cleaned_resp}'. Buffer is now: '{response_buffer}'")

                                    # Check if the entire buffer contains "OK" or "ERROR"
                                    if "K" in response_buffer:
                                        response_ok = True
                                        break
                                    elif "ERROR" in response_buffer:
                                        self.log_message.emit(
                                            f"    [FATAL] Master reported an error: {response_buffer}. Stopping synthesis.")
                                        self.requestInterruption()
                                        break

                                # --- End of response processing logic ---

                                if not response_ok and not self.isInterruptionRequested():
                                    self.log_message.emit(
                                        f"    [FATAL] Timeout: Master did not respond with 'OK' after {MAX_ATTEMPTS} seconds. Stopping synthesis.")
                                    self.requestInterruption()

                            except Exception as e:
                                self.log_message.emit(f"    [ERR] Failed to process line '{line}': {e}")

                        self.arduino.send(f"ph_power_down;")
                        self.log_message.emit(f"  [SEND] ph_power_down")
                        resp = ""
                        while (resp != "OK"):
                            self.arduino.send(f"is_ready;")
                            resp = self.arduino.read_line(1)
                            print(resp)
                            self.msleep(50)

                        self.arduino.send(f"Lwaste;")
                        self.log_message.emit(f"  [SEND] Lwaste")
                        resp = ""
                        while (resp != "OK"):
                            self.arduino.send(f"is_ready;")
                            resp = self.arduino.read_line(1)
                            print(resp)
                            self.msleep(50)



                    elif step.lower() == 'blow':
                        self.arduino.send(f"blow;")
                        self.log_message.emit(f"  [SEND] blow")
                        resp = ""
                        while (resp != "OK"):
                            self.arduino.send(f"is_ready;")
                            resp = self.arduino.read_line(1)
                            print(resp)
                            self.msleep(50)





                    elif step.lower() == 'waste':
                        self.arduino.send(f"Lwaste;")
                        self.log_message.emit(f"  [SEND] Lwaste")
                        resp = ""
                        while (resp != "OK"):
                            self.arduino.send(f"is_ready;")
                            resp = self.arduino.read_line(1)
                            print(resp)
                            self.msleep(50)


                    else:
                        command_str = f"bulk_{step}_{int(vol)};"
                        self.arduino.send(command_str)
                        self.log_message.emit(f"  [SEND] Sending bulk command: {command_str}")
                        resp = ""
                        while (resp != "OK"):
                            self.arduino.send(f"is_ready;")
                            resp = self.arduino.read_line(1)
                            print(resp)
                            self.msleep(50)

                    # Incubation time
                    if inc < 0.05:  # Handle very short times with msleep
                        self.msleep(50)
                    else:
                        self.sleep(int(inc))

            self.arduino.send(f"bulk_wash_{int(500)};")
            self.log_message.emit(f"  [SEND] Sending bulk command: bulk_wash_{int(500)};")
            resp = ""
            while (resp != "OK"):
                self.arduino.send(f"is_ready;")
                resp = self.arduino.read_line(1)
                print(resp)
                self.msleep(50)

        except Exception as e:
            self.log_message.emit(f"[ERR] Worker failed: {e}")


class Services:
    def __init__(self, bus: Optional[Any] = None, port: Optional[str] = None, baudrate: int = 115200):
        self.bus = bus
        self.arduino: Optional[ArduinoLink] = None
        self.synthesis_manager = SynthesisManager(self)
        self.sequence_file_path = ""

        if port is None:
            ports = ArduinoLink.list_ports()
            port = ports[0] if ports else None

        if port:
            try:
                self.arduino = ArduinoLink.autodetect_openids_arduino()
                if self.arduino:
                    # self.arduino.ensure_semicolon = True # May be necessary depending on the linker
                    self.arduino.open()
                    print(f"[Services] Arduino open: {self.arduino.port_name} @ {self.arduino.baudrate}")
                else:
                    print("No target Arduino found.")
            except Exception as e:
                print(f"[Services] Arduino open failed: {e}")
        else:
            print("[Services] No serial ports found")

    def load_protocol(self, filepath: str) -> List[list]:
        protocol_list = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip() or line.strip().startswith('#'):
                    continue
                parts = [p.strip() for p in line.split('\t')]
                if len(parts) >= 3:
                    try:
                        protocol_list.append([parts[0], float(parts[1]), int(parts[2])])
                    except (ValueError, IndexError) as e:
                        print(f"[Services] Warning: Skipping malformed line '{line}': {e}")
        return protocol_list

    def load_sequence_file(self, filepath: str) -> int:
        print(f"[Services] Loading sequence file: {filepath}")

        if not os.path.exists(filepath):
            print(f"[Services] Error: File not found at {filepath}")
            self.sequence_file_path = ""
            return 0

        self.sequence_file_path = filepath
        print(f"[Services] Sequence file set to: {self.sequence_file_path}")

        max_cycle = 0
        try:
            with open(self.sequence_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.lower().startswith("cycle :"):
                        try:
                            cycle_num = int(line.split(':')[1].strip())
                            if cycle_num > max_cycle:
                                max_cycle = cycle_num
                        except (ValueError, IndexError):
                            print(f"[Services] Warning: Could not parse cycle number from line: '{line}'")
                            continue
        except Exception as e:
            print(f"[Services] Error parsing cycles from {self.sequence_file_path}: {e}")
            return 0

        if max_cycle == 0 and os.path.getsize(filepath) > 0:
            print("[Services] No 'cycle :' line found. Assuming 1 cycle.")
            max_cycle = 1

        print(f"[Services] Max cycle found in file: {max_cycle}")
        return max_cycle
