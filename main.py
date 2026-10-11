from cpu_monitor import cpu_test
from ram_monitor import ram_test
from disk_monitor import scan_storage
from network_monitor import network_info

import keyboard

from ui import run_dashboard


def main():
    try:
        run_dashboard(
            cpu_fn=cpu_test,
            ram_fn=ram_test,
            disk_fn=scan_storage,
            network_fn=network_info,
            keyboard_module=keyboard,
        )
    except KeyboardInterrupt:
        # Позволяем завершить программу через Ctrl+C.
        pass


if __name__ == "__main__":
    main()
