import psutil
import socket

def network_info():
    # Получаем адреса (IP, MAC)
    stats_addrs = psutil.net_if_addrs()
    # Получаем статус (UP/DOWN, Скорость)
    stats_status = psutil.net_if_stats()

    for interface_name, addresses in stats_addrs.items():
        status = stats_status.get(interface_name)
        is_up = status.isup if status else False
        speed = status.speed if status else 0 # Скорость в Мбит/с

        print(f"Interface: {interface_name} | Status: {'UP' if is_up else 'DOWN'} | Speed: {speed} Mbps")
        for addr in addresses:
            if addr.family == socket.AF_INET: 
                print(f"  IPv4: {addr.address} | Mask: {addr.netmask}")
            elif addr.family == psutil.AF_LINK: 
                print(f"  MAC: {addr.address}")
