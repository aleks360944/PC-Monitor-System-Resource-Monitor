import psutil
import platform

PROCESSOR_MODEL = platform.processor()
PHYSICAL_CORES = psutil.cpu_count(logical=False)
LOGICAL_CORES = psutil.cpu_count(logical=True)

def cpu_test():
    usage = psutil.cpu_percent(interval=0.1) #получаем данные о загрузке CPU
    
    print(f"Processor Model: {PROCESSOR_MODEL}\n")  #выводим модель процессора
    
    print(f"Physical cores: {PHYSICAL_CORES}") #выводим физическия ядра
    print(f"Logical cores: {LOGICAL_CORES}\n") #выводим логические ядра
    
    print(f"CPU Usage: {usage}%\n\n")
