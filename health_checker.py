from cpu_monitor import get_cpu_data
from ram_monitor import get_ram_data
from disk_monitor import get_storage_list

WARNING_THRESHOLD = 80
CRITICAL_THRESHOLD = 95

def check_cpu(data = None):
    if data is None:
        data = get_cpu_data()

    usage = data.get("usage")

    if usage is None:
        return [{
            "component": "CPU",
            "level": "UNKNOWN",
            "message": "CPU usage data is unavailable",
        }]

    if usage >= CRITICAL_THRESHOLD:
        return [{
            "component": "CPU",
            "level": "CRITICAL",
            "message": f"CPU usage is critically high: {usage:.1f}%",
        }]

    if usage >= WARNING_THRESHOLD:
        return [{
            "component": "CPU",
            "level": "WARNING",
            "message": f"CPU usage is high: {usage:.1f}%",
        }]

    return [{
        "component": "CPU",
        "level": "OK",
        "message": "CPU usage is within normal limits",
    }]

def check_ram(data = None):
    if data is None:
        data = get_ram_data()

    usage = data.get("usage")

    if usage is None:
        return [{
            "component": "RAM",
            "level": "UNKNOWN",
            "message": "RAM usage data is unavailable",
        }]

    if usage >= CRITICAL_THRESHOLD:
        return [{
            "component": "RAM",
            "level": "CRITICAL",
            "message": f"RAM usage is critically high: {usage:.1f}%",
        }]

    if usage >= WARNING_THRESHOLD:
        return [{
            "component": "RAM",
            "level": "WARNING",
            "message": f"RAM usage is high: {usage:.1f}%",
        }]

    return [{
        "component": "RAM",
        "level": "OK",
        "message": "RAM usage is within normal limits",
    }]

def check_storage(data=None):
    if data is None:
        data = get_storage_list()

    results = []

    if not data:
        results.append(
            {
                "component": "Storage",
                "level": "UNKNOWN",
                "message": "Storage data is unavailable",
            }
        )
        return results

    for disk in data:
        usage = disk.get("usage")
        device = disk.get("device", "Unknown Device")
        mountpoint = disk.get("mountpoint", "Unknown Mountpoint")

        if usage is None:
            results.append(
                {
                    "component": "Storage",
                    "level": "UNKNOWN",
                    "message": f"Disk {device} ({mountpoint}) usage data is missing",
                }
            )
        elif usage >= CRITICAL_THRESHOLD:
            results.append(
                {
                    "component": "Storage",
                    "level": "CRITICAL",
                    "message": f"Disk {device} ({mountpoint}) is critically full: {usage}%",
                }
            )
        elif usage >= WARNING_THRESHOLD:
            results.append(
                {
                    "component": "Storage",
                    "level": "WARNING",
                    "message": f"Disk {device} ({mountpoint}) is running low on space: {usage}%",
                }
            )
        else:
            results.append(
                {
                    "component": "Storage",
                    "level": "OK",
                    "message": f"Disk {device} ({mountpoint}) space is normal: {usage}%",
                }
            )

    return results

def check_system():
    combined_list = check_cpu() + check_ram() + check_storage()

    if not combined_list:
        return "UNKNOWN"

    # Переводим в множество для быстрой проверки
    statuses = {item["level"] for item in combined_list}

    # 1. Если хотя бы один компонент имеет CRITICAL — вернуть CRITICAL
    if "CRITICAL" in statuses:
        return "CRITICAL"

    # 2. Иначе, если хотя бы один имеет WARNING — вернуть WARNING
    elif "WARNING" in statuses:
        return "WARNING"

    # 3. Иначе, если хотя бы один имеет UNKNOWN — вернуть UNKNOWN
    elif "UNKNOWN" in statuses:
        return "UNKNOWN"

    # 4. Если все компоненты имеют OK — вернуть OK (или в списке только OK и другие некритичные статусы)
    elif "OK" in statuses:
        return "OK"

    # На случай, если в списке оказались другие непредусмотренные строки
    return "UNKNOWN"
