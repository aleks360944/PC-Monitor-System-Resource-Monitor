import csv
from datetime import datetime
import math
from pathlib import Path
import threading
import time


def to_number(value):
    value = value.strip()
    if value in {"", "?"}:
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def parse_gpu_csv_line(line):
    """Parse one hw-smi CSV line; return None for malformed or incomplete rows."""
    try:
        row = next(csv.reader([line.decode("utf-8")], skipinitialspace=True))
        datetime.strptime(row[0].strip(), "%Y-%m-%d %H:%M:%S.%f")
        if len(row) < 26:
            return None
        values = {
            "gpu_usage": to_number(row[18]),
            "vram_used_mb": to_number(row[20]),
            "temperature": to_number(row[21]),
            "core_clock_mhz": to_number(row[24]),
            "memory_clock_mhz": to_number(row[25]),
        }
        return {key: value if value is not None else "N/S" for key, value in values.items()}
    except (UnicodeDecodeError, ValueError, IndexError, csv.Error, AttributeError):
        return None


class GPULogReader:
    """Read appended hw-smi log bytes instead of reparsing old samples."""

    def __init__(self, log_dir=None, discovery_interval=5.0):
        self.log_dir = Path(log_dir) if log_dir else Path(__file__).resolve().parent
        self.discovery_interval = discovery_interval
        self._next_discovery = 0.0
        self._log_path = None
        self._offset = 0
        self._partial_line = b""
        self._lock = threading.Lock()
        self._record = self._empty_record()

    @staticmethod
    def _empty_record():
        return {
            "gpu_usage": "N/S",
            "vram_used_mb": "N/S",
            "temperature": "N/S",
            "core_clock_mhz": "N/S",
            "memory_clock_mhz": "N/S",
        }

    def _find_log(self, now):
        if self._log_path and self._log_path.exists() and now < self._next_discovery:
            return self._log_path
        self._next_discovery = now + self.discovery_interval
        try:
            logs = self.log_dir.glob("hw-smi-*.log")
            path = max(logs, key=lambda item: item.stat().st_mtime, default=None)
        except OSError:
            path = None
        if path != self._log_path:
            self._log_path = path
            self._offset = 0
            self._partial_line = b""
        return path

    def _parse_line(self, line):
        record = parse_gpu_csv_line(line)
        if record is not None:
            self._record = record

    def get_data(self):
        with self._lock:
            now = time.monotonic()
            path = self._find_log(now)
            if path is None:
                return self._record.copy()
            try:
                with path.open("rb") as file:
                    if file.seek(0, 2) < self._offset:
                        self._offset = 0
                        self._partial_line = b""
                    file.seek(self._offset)
                    chunk = file.read()
                    self._offset = file.tell()
            except (OSError, ValueError):
                return self._record.copy()

            lines = (self._partial_line + chunk).splitlines(keepends=True)
            self._partial_line = b""
            if lines and not lines[-1].endswith((b"\n", b"\r")):
                self._partial_line = lines.pop()
            for line in lines:
                if line.strip():
                    self._parse_line(line)
            return self._record.copy()


_default_reader = GPULogReader()


def get_gpu_data():
    return _default_reader.get_data()


def gpu_test():
    data = get_gpu_data()
    print(f"GPU Usage: {data['gpu_usage']}%")
    print(f"VRAM Used: {data['vram_used_mb']} MB")
    print(f"Temperature: {data['temperature']} °C")
    print(f"Core Clock: {data['core_clock_mhz']} MHz")
    print(f"Memory Clock: {data['memory_clock_mhz']} MHz")
