import psutil

def scan_storage():
    for part in psutil.disk_partitions():
        # Пропускаем CD-ROM и служебные разделы без пути монтирования
        if 'cdrom' in part.opts or not part.mountpoint:
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
            print(f"Disk {part.device} ({part.mountpoint}): "
                f"Total: {usage.total / (2**30):.1f} GB | "
                f"Usage: {usage.percent}%")
        except OSError as e:
            error_msg = e.strerror if e.strerror else str(e)
            print(f"Disk {part.device} ({part.mountpoint}): [ERROR] -> {error_msg}")
    print("\n\n")