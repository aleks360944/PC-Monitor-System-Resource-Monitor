import math

from cpu_monitor import get_cpu_data
from ram_monitor import get_ram_data
from disk_monitor import get_storage_list

WARNING_THRESHOLD = 80
CRITICAL_THRESHOLD = 95


def _get_usage(data):
    """Return a valid percentage or None when input data is missing/invalid."""
    if not isinstance(data, dict):
        return None
    usage = data.get("usage")
    if isinstance(usage, bool) or not isinstance(usage, (int, float)):
        return None
    try:
        usage = float(usage)
    except (OverflowError, ValueError):
        return None
    if not math.isfinite(usage) or not 0 <= usage <= 100:
        return None
    return usage


def _check_usage(component, data):
    usage = _get_usage(data)
    if usage is None:
        return [{
            "component": component,
            "level": "UNKNOWN",
            "message": f"{component} usage data is unavailable or invalid",
        }]
    if usage >= CRITICAL_THRESHOLD:
        message = f"{component} usage is critically high: {usage:.1f}%"
        level = "CRITICAL"
    elif usage >= WARNING_THRESHOLD:
        message = f"{component} usage is high: {usage:.1f}%"
        level = "WARNING"
    else:
        message = f"{component} usage is within normal limits"
        level = "OK"
    return [{"component": component, "level": level, "message": message}]


def check_cpu(data=None):
    if data is None:
        data = get_cpu_data()
    return _check_usage("CPU", data)


def check_ram(data=None):
    if data is None:
        data = get_ram_data()
    return _check_usage("RAM", data)


def check_storage(data=None):
    if data is None:
        data = get_storage_list()
    if not isinstance(data, list) or not data:
        return [{
            "component": "Storage",
            "level": "UNKNOWN",
            "message": "Storage data is unavailable or invalid",
        }]

    results = []
    for disk in data:
        if not isinstance(disk, dict):
            results.append({
                "component": "Storage",
                "level": "UNKNOWN",
                "message": "Storage device data is invalid",
            })
            continue

        device = disk.get("device", "Unknown Device")
        mountpoint = disk.get("mountpoint", "Unknown Mountpoint")
        usage = _get_usage(disk)
        if usage is None:
            level = "UNKNOWN"
            message = f"Disk {device} ({mountpoint}) usage data is missing or invalid"
        elif usage >= CRITICAL_THRESHOLD:
            level = "CRITICAL"
            message = f"Disk {device} ({mountpoint}) is critically full: {usage:.1f}%"
        elif usage >= WARNING_THRESHOLD:
            level = "WARNING"
            message = f"Disk {device} ({mountpoint}) is running low on space: {usage:.1f}%"
        else:
            level = "OK"
            message = f"Disk {device} ({mountpoint}) space is normal: {usage:.1f}%"
        results.append({"component": "Storage", "level": level, "message": message})
    return results


def check_system():
    combined_list = check_cpu() + check_ram() + check_storage()
    statuses = {item.get("level", "UNKNOWN") for item in combined_list}
    for level in ("CRITICAL", "WARNING", "UNKNOWN", "OK"):
        if level in statuses:
            return level
    return "UNKNOWN"
