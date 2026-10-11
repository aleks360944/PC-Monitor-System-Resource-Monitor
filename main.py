from test_cpu import cpu_test
from test_ram import ram_test
from test_disk import scan_storage
from test_net import network_info

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
