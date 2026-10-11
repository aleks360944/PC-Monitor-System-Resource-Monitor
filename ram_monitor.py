import psutil

def ram_test():
    memory = psutil.virtual_memory()
    total_gb = memory.total / (1024 ** 3)
    available_gb = memory.available / (1024 ** 3)
    
    print(f"Total memory: {total_gb:.2f} GB")
    print(f"Memory available: {available_gb:.2f} GB\n")
    print(f"Memory in use: {memory.percent}%\n\n")
