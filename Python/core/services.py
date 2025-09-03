# core/services.py
import os, time, glob
from typing import Any, Optional, List, Tuple
from PyQt5 import QtCore
from .arduino_linker import ArduinoLink


class SynthesisManager(QtCore.QObject):
    """
    합성 프로세스를 백그라운드에서 관리하고 UI에 진행 상황을 알립니다.
    """
    status_updated = QtCore.pyqtSignal(int, str)
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
            self.log_message.emit("[ERR] Sequence folder with valid cycle files is not loaded.")
            return
        if self.s.arduino is None:
            self.log_message.emit("[ERR] Arduino is not connected.")
            return

        self._worker = SynthesisWorker(
            self.s.arduino,
            self._protocol,
            self._total_cycles,
            self.s.sequence_dir_path  # 시퀀스 폴더 경로 전달
        )
        self._worker.status_updated.connect(self.status_updated)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.log_message.connect(self.log_message)
        self._worker.start()
        self.log_message.emit("[RUN] Synthesis started.")

    def toggle_pause_resume(self):
        """일시정지 상태를 토글합니다."""
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
                self.toggle_pause_resume()  # 재개하여 루프를 빠져나오게 함
            self._worker.requestInterruption()
            self.log_message.emit("[STOP] Stop request sent.")

    def _on_worker_finished(self):
        self.log_message.emit("[DONE] Synthesis finished.")
        self.synthesis_finished.emit()
        self._worker = None
        self._is_paused = False


class SynthesisWorker(QtCore.QThread):
    status_updated = QtCore.pyqtSignal(int, str)
    log_message = QtCore.pyqtSignal(str)

    def __init__(self, arduino_link, protocol, total_cycles, sequence_path):
        super().__init__()
        self.arduino = arduino_link
        self.protocol = protocol
        self.total_cycles = total_cycles
        self.sequence_path = sequence_path  # 시퀀스 폴더 경로 저장
        self._is_paused = False
        self._mutex = QtCore.QMutex()

    def pause(self):
        with QtCore.QMutexLocker(self._mutex):
            self._is_paused = True

    def resume(self):
        with QtCore.QMutexLocker(self._mutex):
            self._is_paused = False

    def run(self):
        try:
            for cycle in range(1, self.total_cycles + 1):
                if self.isInterruptionRequested(): break
                self.log_message.emit(f"--- Starting Cycle {cycle}/{self.total_cycles} ---")

                for step, vol, inc in self.protocol:
                    if self.isInterruptionRequested(): break

                    # 일시정지 확인 로직
                    while True:
                        with QtCore.QMutexLocker(self._mutex):
                            if not self._is_paused:
                                break
                        self.sleep(1)

                    self.status_updated.emit(cycle, step)
                    self.log_message.emit(f"Cycle {cycle}, Step {step}, Vol {vol}, Inc {inc}")

                    # --- 'coupling' 단계 특별 처리 ---
                    if step.lower() == 'coupling':
                        base_map = {
                            'ACT': 0x13, 'A': 0x14, 'T': 0x15, 'G': 0x16, 'C': 0x17
                        }

                        for base, slave_addr in base_map.items():
                            if self.isInterruptionRequested(): break

                            file_pattern = os.path.join(self.sequence_path, f"{cycle}_{base}.*")
                            found_files = glob.glob(file_pattern)

                            if not found_files:
                                self.log_message.emit(
                                    f"[INFO] Cycle {cycle}, Base {base}: Skip, file not found for pattern {file_pattern}")
                                continue

                            filepath = found_files[0]
                            self.log_message.emit(
                                f"  > Coupling: Processing {os.path.basename(filepath)} for slave 0x{slave_addr:02X}")

                            try:
                                with open(filepath, 'rb') as f:
                                    line_num = 0
                                    while True:
                                        chunk = f.read(16)
                                        if not chunk:
                                            break
                                        if len(chunk) < 16:
                                            chunk += b'\x00' * (16 - len(chunk))

                                        # 아두이노로 라인 전송하고 응답 확인
                                        response = self.arduino.query_line(slave_addr, chunk)
                                        if response and "OK" in response:
                                            # 성공 로그는 너무 많으므로 필요 시 주석 해제
                                            # self.log_message.emit(f"    Line {line_num}: OK")
                                            pass
                                        else:
                                            self.log_message.emit(
                                                f"    [ERR] Line {line_num}: Master response: {response}")
                                            # 필요하다면 여기서 전송을 중단하거나 재시도 로직 추가

                                        line_num += 1
                                        self.msleep(5)  # I2C 통신을 위한 최소한의 딜레이

                            except IOError as e:
                                self.log_message.emit(f"[ERR] Failed to read {filepath}: {e}")
                    else:
                        command_str = f"bulk_{step}_{int(vol)}"
                        self.arduino.send(command_str)

                    if inc < 0.5:
                        self.msleep(500)
                    else:
                        self.sleep(int(inc))

        except Exception as e:
            self.log_message.emit(f"[ERR] Worker failed: {e}")


class Services:
    def __init__(self, bus: Optional[Any] = None, port: Optional[str] = None, baudrate: int = 115200):
        self.bus = bus
        self.arduino: Optional[ArduinoLink] = None
        self.synthesis_manager = SynthesisManager(self)
        self.sequence_dir_path = ""

        if port is None:
            ports = ArduinoLink.list_ports()
            port = ports[0] if ports else None

        if port:
            try:
                self.arduino = ArduinoLink.autodetect_openids_arduino()
                if self.arduino:
                    self.arduino.ensure_semicolon = True
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

    def load_sequence_directory(self, dir_path: str) -> int:
        print(f"[Services] Loading sequence directory: {dir_path}")
        self.sequence_dir_path = dir_path

        max_cycle = 0
        if not os.path.isdir(dir_path):
            return 0
        try:
            for filename in os.listdir(dir_path):
                if os.path.isfile(os.path.join(dir_path, filename)):
                    try:
                        cycle_num = int(filename.split('_')[0])
                        if cycle_num > max_cycle:
                            max_cycle = cycle_num
                    except (ValueError, IndexError):
                        continue
        except Exception as e:
            print(f"[Services] Error counting cycles in {dir_path}: {e}")
            return 0

        return max_cycle

