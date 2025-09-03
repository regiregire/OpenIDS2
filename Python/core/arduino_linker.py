# core/hardware.py
from __future__ import annotations
import threading
import time
from typing import Optional, List

import serial
import serial.tools.list_ports

DEFAULT_BAUD = 115200
DEFAULT_TIMEOUT = 0.2  # read timeout (sec)
DEFAULT_WRITE_TIMEOUT = 0.2


class ArduinoLink:
    """
    아두이노와 직렬 통신(라인 기반)에 특화된 간단 드라이버.
    - 명령은 문자열로 전송(기본: 줄끝 '\n' 추가). 필요하면 ';' 자동 추가 옵션 지원.
    - 응답은 개행(\r\n 등) 기준 줄 단위로 수신.
    - thread-safe (write/read에 Lock)
    """

    def __init__(self,
                 port: str,
                 baudrate: int = DEFAULT_BAUD,
                 timeout: float = DEFAULT_TIMEOUT,
                 write_timeout: float = DEFAULT_WRITE_TIMEOUT,
                 append_newline: bool = False,  # 아두이노가 ';' 기준으로 읽으므로 '\n' 비활성화
                 ensure_semicolon: bool = True,  # 명령어 끝에 ';' 자동 추가
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

    # ---------- 유틸 ----------
    @staticmethod
    def list_ports() -> List[str]:
        """사용 가능한 직렬 포트 목록을 반환."""
        return [p.device for p in serial.tools.list_ports.comports()]

    # ---------- 연결 ----------
    def open(self) -> None:
        """포트를 연다(이미 열려 있으면 무시)."""
        if self.is_open():
            return
        self._ser = serial.Serial(
            self.port_name,
            self.baudrate,
            timeout=self.timeout,
            write_timeout=self.write_timeout
        )
        # 아두이노 리셋 대기(보드/부트로더에 따라 다름)
        time.sleep(2)  # 안정적인 연결을 위해 대기 시간 증가
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
        """입출력 버퍼 비우기."""
        with self._lock:
            if self._ser:
                self._ser.reset_input_buffer()
                self._ser.reset_output_buffer()

    # ---------- 송수신 ----------
    def _format_cmd(self, cmd: str) -> bytes:
        s = cmd.strip()
        if self.ensure_semicolon and not s.endswith(';'):
            s += ';'
        if self.append_newline and not s.endswith('\n'):
            s += '\n'
        return s.encode(self.encoding, errors="replace")

    def send(self, cmd: str) -> None:
        """응답을 기다리지 않고 명령만 보냄."""
        with self._lock:
            if not self.is_open():
                raise RuntimeError("Serial port is not open")
            payload = self._format_cmd(cmd)
            self._ser.write(payload)
            self._ser.flush()

    def send_line(self, slave_addr: int, payload: bytes):
        """16바이트 라인 데이터를 특정 슬레이브 주소로 보내도록 마스터에게 요청합니다."""
        if not self.is_open():
            raise RuntimeError("Serial port is not open")

        # payload를 16진수 문자열로 변환
        hex_payload = payload.hex()
        # 명령어 형식: "line,주소,16진수데이터"
        command = f"line,{slave_addr},{hex_payload}"
        self.send(command)  # send 메서드가 세미콜론을 붙여줌

    def read_line(self, timeout: Optional[float] = None) -> Optional[str]:
        """한 줄 읽기. 타임아웃 시 None."""
        deadline = time.time() + (timeout if timeout is not None else self.timeout)
        buf = bytearray()
        while time.time() < deadline:
            with self._lock:
                if not self.is_open():
                    return None
                # 한번에 여러 바이트를 읽어 성능 향상
                if self._ser.in_waiting > 0:
                    chunk = self._ser.read(self._ser.in_waiting)
                    buf.extend(chunk)
                    if b'\n' in buf or b'\r' in buf:
                        break
            time.sleep(0.01)  # CPU 사용량 감소

        if not buf:
            return None
        try:
            # 개행 문자를 기준으로 첫번째 라인만 반환
            line = buf.splitlines()[0]
            return line.decode(self.encoding, errors="replace").strip()
        except Exception:
            return None

    def query(self, cmd: str, timeout: Optional[float] = None) -> Optional[str]:
        """
        명령을 보내고 한 줄 응답을 기다린다.
        """
        self.send(cmd)
        return self.read_line(timeout=timeout)

    @staticmethod
    def autodetect_openids_arduino(cmd="WHOAMI;", expect="openIDS", per_port_timeout=0.5):
        candidates = [p.device for p in serial.tools.list_ports.comports()]
        for dev in candidates:
            link = None
            try:
                # 기본값으로 ';' 추가, '\n' 미사용으로 생성
                link = ArduinoLink(dev, baudrate=115200, timeout=0.2, write_timeout=0.2)
                link.open()
                link.flush()
                # WHOAMI는 ';' 없이 보내야 할 수 있으므로 send 대신 직접 write
                link._ser.write(b'WHOAMI;')
                time.sleep(0.1)
                resp = link.read_line(timeout=per_port_timeout)
                if resp and expect in resp:
                    return link  # 연결된 객체 자체를 반환
                else:
                    link.close()
            except Exception:
                if link:
                    link.close()
        return None
