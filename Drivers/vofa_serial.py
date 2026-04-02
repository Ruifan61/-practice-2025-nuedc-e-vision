from dataclasses import dataclass
from threading import Lock, Thread
from typing import Optional

import time
import serial


@dataclass(slots=True)
class VofaSerialConfig:
    port: str = "/dev/serial0"
    baudrate: int = 115200
    timeout: float = 0.0
    send_hz: float = 20.0


class VofaSerial:
    def __init__(self, config: Optional[VofaSerialConfig] = None):
        self.config = config or VofaSerialConfig()
        self.ser: Optional[serial.Serial] = None
        self.is_opened = False
        self.is_running = False
        self._thread: Optional[Thread] = None
        self._lock = Lock()
        self._latest_line = "0,0,0\n"

    def open(self):
        if self.is_opened:
            return True

        try:
            self.ser = serial.Serial(
                port=self.config.port,
                baudrate=self.config.baudrate,
                timeout=self.config.timeout,
            )
            self.is_opened = True
            return True
        except Exception as exc:
            print(f"VOFA Serial Open Failed: {exc}")
            self.ser = None
            self.is_opened = False
            return False

    def close(self):
        self.stop()
        if self.ser is not None:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None
        self.is_opened = False

    def start(self):
        if self.is_running:
            return True

        if not self.is_opened and not self.open():
            return False

        self.is_running = True
        self._thread = Thread(target=self._send_loop, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self.is_running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self._thread = None

    def send_values(self, *values):
        if not self.is_opened or self.ser is None:
            return False

        line = self._format_values(*values)
        try:
            self.ser.write(line.encode("utf-8"))
            return True
        except Exception as exc:
            print(f"VOFA Serial Write Failed: {exc}")
            return False

    def update_latest(self, *values):
        line = self._format_values(*values)
        with self._lock:
            self._latest_line = line

    def _format_values(self, *values):
        return ",".join(str(value) for value in values) + "\n"

    def _send_loop(self):
        interval = 1.0 / self.config.send_hz if self.config.send_hz > 0 else 0.1
        while self.is_running:
            if not self.is_opened or self.ser is None:
                time.sleep(interval)
                continue

            with self._lock:
                line = self._latest_line

            try:
                self.ser.write(line.encode("utf-8"))
            except Exception as exc:
                print(f"VOFA Serial Write Failed: {exc}")
                time.sleep(interval)
                continue

            time.sleep(interval)

    def __del__(self):
        self.close()
