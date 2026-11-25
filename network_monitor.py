import psutil
import socket


def network_info():
    """Return network interface details for the dashboard."""
    interfaces = []
    stats_addrs = psutil.net_if_addrs()
    stats_status = psutil.net_if_stats()

    for interface_name, addresses in stats_addrs.items():
        status = stats_status.get(interface_name)
        interface = {
            "name": interface_name,
            "is_up": bool(status and status.isup),
            "speed_mbps": status.speed if status else 0,
            "ipv4": [],
            "ipv6": [],
            "mac": [],
        }
        for addr in addresses:
            if addr.family == socket.AF_INET:
                interface["ipv4"].append({"address": addr.address, "netmask": addr.netmask})
            elif addr.family == socket.AF_INET6:
                interface["ipv6"].append(addr.address)
            elif addr.family == psutil.AF_LINK:
                interface["mac"].append(addr.address)
        interfaces.append(interface)

    return interfaces
