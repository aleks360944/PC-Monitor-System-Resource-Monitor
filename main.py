
import subprocess
from pathlib import Path

from cpu_monitor import get_cpu_data
from ram_monitor import get_ram_data
from disk_monitor import get_storage_list
from network_monitor import network_info
from gpu_monitor import get_gpu_data
from ui import run_dashboard


BASE_DIR = Path(__file__).resolve().parent
HW_SMI_PATH = BASE_DIR / "hw-smi.exe"


def start_hw_smi():
    """Start optional GPU telemetry without elevating the whole app."""
    if not HW_SMI_PATH.is_file():
        print(f"hw-smi.exe не найден: {HW_SMI_PATH}")
        return None

    try:
        return subprocess.Popen(
            [str(HW_SMI_PATH), "--log"],
            cwd=BASE_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError as error:
        print(f"Не удалось запустить hw-smi; остальные показатели продолжат работать: {error}")
        return None


def stop_hw_smi(process):
    """Stop hw-smi when the dashboard closes."""
    if process is None or process.poll() is not None:
        return

    process.terminate()

    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def main():
    hw_smi_process = None

    try:
        hw_smi_process = start_hw_smi()

        run_dashboard(
            cpu_fn=get_cpu_data,
            ram_fn=get_ram_data,
            disk_fn=get_storage_list,
            network_fn=network_info,
            gpu_fn=get_gpu_data,
        )

    except KeyboardInterrupt:
        pass

    finally:
        stop_hw_smi(hw_smi_process)


if __name__ == "__main__":
    main()
