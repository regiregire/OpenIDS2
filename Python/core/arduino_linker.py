# core/hardware.py
from __future__ import annotations
import threading
import time
from typing import Optional, List

import serial
import serial.tools.list_ports

DEFAULT_BAUD = 115200
DEFAULT_TIMEOUT = 2.0  # read timeout (sec)
DEFAULT_WRITE_TIMEOUT = 2.0


class ArduinoLink:


    def __init__(self,
                 port: str,
                 baudrate: int = DEFAULT_BAUD,
                 timeout: float = DEFAULT_TIMEOUT,
                 write_timeout: float = DEFAULT_WRITE_TIMEOUT,
                 append_newline: bool = False,  # Disable newline as Arduino reads based on ';'
                 ensure_semicolon: bool = True,  # Automatically add ';' to the end of the command
                 encoding: str = "ascii"):
        self.port_name = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.write_timeout = write_timeout
        self.append_newline = append_newline
        self.ensure_semicolon = ensure_semicolon
        self.encoding = encoding

        self._ser: Optional[serial.Serial] = None
        self._lock = threading.Lock()

    # ---------- Utilities ----------
    @staticmethod
    def list_ports() -> List[str]:
        """Returns a list of available serial ports."""
        return [p.device for p in serial.tools.list_ports.comports()]

    # ---------- Connection ----------
    def open(self) -> None:
        """Opens the port (ignored if already open)."""
        if self.is_open():
            return
        self._ser = serial.Serial(
            self.port_name,
            self.baudrate,
            timeout=self.timeout,
            write_timeout=self.write_timeout
        )
        # Wait for Arduino reset (depends on board/bootloader)
        time.sleep(2)  # Increased wait time for a stable connection
        self.flush()

    def close(self) -> None:
        with self._lock:
            if self._ser:
                try:
                    self._ser.close()
                finally:
                    self._ser = None

    def is_open(self) -> bool:
        return bool(self._ser and self._ser.is_open)

    def flush(self) -> None:
        """Flush input/output buffers."""
        with self._lock:
            if self._ser:
                self._ser.reset_input_buffer()
                self._ser.reset_output_buffer()

    # ---------- Send/Receive ----------
    def _format_cmd(self, cmd: str) -> bytes:
        s = cmd.strip()
        if self.ensure_semicolon and not s.endswith(';'):
            s += ';'
        if self.append_newline and not s.endswith(''):
            s += ''
        return s.encode(self.encoding, errors="replace")

    def send(self, cmd: str) -> None:
        """Sends a command without waiting for a response."""
        with self._lock:
            if not self.is_open():
                raise RuntimeError("Serial port is not open")
            payload = self._format_cmd(cmd)
            self._ser.write(payload)
            self._ser.flush()

    def send_line(self, slave_addr: int, payload: bytes):
        """Requests the master to send 16-byte line data to a specific slave address."""
        if not self.is_open():
            raise RuntimeError("Serial port is not open")

        # Convert payload to a hexadecimal string
        hex_payload = payload.hex()
        # Command format: "line,address,hex_data"
        command = f"line,{slave_addr},{hex_payload}"
        self.send(command)  # The send method adds a semicolon

    def query_line(self, slave_addr: int, payload: bytes, timeout: Optional[float] = None) -> Optional[str]:
        """
        Sends a line of data and waits for a one-line response.
        """
        self.send_line(slave_addr, payload)
        return self.read_line(timeout=timeout)

    def read_line(self, timeout: Optional[float] = None) -> Optional[str]:
        """
        Reads one line (based on the semicolon ';'). Returns None on timeout.
        This function assumes that the Arduino's response ends with a ';'.
        """
        deadline = time.time() + (timeout if timeout is not None else self.timeout)
        line = bytearray()
        self.flush()
        while time.time() < deadline:
            with self._lock:
                if not self.is_open():
                    return None

                # Check if there is data to read
                if self._ser.in_waiting > 0:
                    # Read data byte by byte to check for a semicolon
                    char = self._ser.read(1)

                    if char == b';':  # If the delimiter (;) is found, exit the loop
                        try:
                            # Decode the buffer collected so far into a string and return it
                            return line.decode(self.encoding).strip()
                        except UnicodeDecodeError:
                            return None  # Return None on decoding failure
                    else:
                        # If it is not a delimiter, add it to the buffer
                        line.extend(char)

            time.sleep(0.005)  # Short wait to reduce CPU usage

        # Return None on timeout
        return None

    def query(self, cmd: str, timeout: Optional[float] = None) -> Optional[str]:
        """
        Sends a command and waits for a one-line response.
        """
        self.send(cmd)
        return self.read_line(timeout=timeout)

    @staticmethod
    def autodetect_openids_arduino(cmd="WHOAMI;", expect="openIDS", per_port_timeout=5):
        candidates = [p.device for p in serial.tools.list_ports.comports()]
        for dev in candidates:
            link = None
            try:
                # Add ';' by default
                link = ArduinoLink(dev, baudrate=115200, timeout=0.2, write_timeout=0.2)
                link.open()
                link.flush()
                time.sleep(0.5)
                link._ser.write(b'WHOAMI;')
                resp = link.read_line(timeout=per_port_timeout)

                if resp and expect in resp:
                    return link  # Return the connected object itself
                else:
                    link.close()
            except Exception:
                if link:
                    link.close()
        return None