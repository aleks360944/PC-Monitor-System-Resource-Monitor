import csv
from datetime import datetime
from pathlib import Path

def to_number(value):
    value = value.strip()

    if value == "?":
        return None

    return float(value)


def get_gpu_data():
    default_record = {
        "gpu_usage": "N/S",
        "vram_used_mb": "N/S",
        "temperature": "N/S",
        "core_clock_mhz": "N/S",
        "memory_clock_mhz": "N/S",
    }

    LOG_DIR = Path(".")
    LOG_FILES = list(LOG_DIR.glob("hw-smi-*.log"))

    if not LOG_FILES:
        return default_record

    if LOG_FILES:
        LOG_FILE = max(LOG_FILES, key=lambda file: file.stat().st_mtime)

    last_record = None

    try:
        with LOG_FILE.open(encoding="utf-8", newline="") as file:
            reader = csv.reader(file, skipinitialspace=True)

            for row in reader:
                if not row:
                    continue

                try:
                    datetime.strptime(
                        row[0].strip(),
                        "%Y-%m-%d %H:%M:%S.%f"
                    )
                except ValueError:
                    continue

                if len(row) < 26:
                    continue

                last_record = {
                    "gpu_usage": to_number(row[18]),
                    "vram_used_mb": to_number(row[20]),
                    "temperature": to_number(row[21]),
                    "core_clock_mhz": to_number(row[24]),
                    "memory_clock_mhz": to_number(row[25]),
                }

        if last_record is None:
            return default_record

        return {k: (v if v is not None else "N/S") for k, v in last_record.items()}

    except FileNotFoundError:
        # На случай, если файл удалили прямо во время работы скрипта
        return default_record

def gpu_test():
    data = get_gpu_data()

    print(f"GPU Usage: {data['gpu_usage']}%")
    print(f"VRAM Used: {data['vram_used_mb']} MB")
    print(f"Temperature: {data['temperature']} °C")
    print(f"Core Clock: {data['core_clock_mhz']} MHz")
    print(f"Memory Clock: {data['memory_clock_mhz']} MHz")
