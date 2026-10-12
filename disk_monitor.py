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

def get_storage_list():
    disks_info = []

    for part in psutil.disk_partitions():
        if "cdrom" in part.opts or not part.mountpoint:
            continue

        try:
            usage = psutil.disk_usage(part.mountpoint)

            disk_data = {
                "device": part.device,
                "mountpoint": part.mountpoint,
                "total_gb": round(usage.total / (2**30), 1),
                "free_gb": round(usage.free / (2**30), 1),
                "usage": usage.percent,
            }
            disks_info.append(disk_data)

        except OSError:
            continue

    return disks_info
