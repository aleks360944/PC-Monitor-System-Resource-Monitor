
import ctypes
import subprocess
import sys
from pathlib import Path

import keyboard

from cpu_monitor import cpu_test
from ram_monitor import ram_test
from disk_monitor import scan_storage
from network_monitor import network_info
from gpu_monitor import gpu_test
from ui import run_dashboard


BASE_DIR = Path(__file__).resolve().parent
HW_SMI_PATH = BASE_DIR / "hw-smi.exe"


def is_admin():
    """Check whether the current process has administrator privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False


def restart_as_admin():
    """Restart this script with administrator privileges."""
    script_path = Path(__file__).resolve()

    arguments = subprocess.list2cmdline(
        [str(script_path), *sys.argv[1:]]
    )

    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        sys.executable,
        arguments,
        str(BASE_DIR),
        1,
    )

    if result <= 32:
        raise RuntimeError(
            f"Не удалось запустить приложение от администратора. "
            f"Код Windows: {result}"
        )


def start_hw_smi():
    """Start hw-smi in the background."""
    if not HW_SMI_PATH.is_file():
        print(f"hw-smi.exe не найден: {HW_SMI_PATH}")
        return None

    return subprocess.Popen(
        [str(HW_SMI_PATH), "--log"],
        cwd=BASE_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


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
            cpu_fn=cpu_test,
            ram_fn=ram_test,
            disk_fn=scan_storage,
            network_fn=network_info,
            gpu_fn=gpu_test,
            keyboard_module=keyboard,
        )

    except KeyboardInterrupt:
        pass

    finally:
        stop_hw_smi(hw_smi_process)


if __name__ == "__main__":
    if not is_admin():
        try:
            restart_as_admin()
        except (OSError, RuntimeError) as error:
            print(f"Error: {error}")
        sys.exit(0)

    main()
