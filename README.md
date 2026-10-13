# PC Monitor

A lightweight, terminal-based system resource monitor written in Python. PC Monitor displays live system information in a dashboard powered by [Rich](https://github.com/Textualize/rich).

## Features

- **CPU monitoring** — processor information and current CPU usage.
- **RAM monitoring** — total, available, and used memory.
- **Storage monitoring** — disk capacity, free space, and usage for detected volumes.
- **Network information** — available network interfaces, IP and MAC addresses, and connection details.
- **Live terminal dashboard** — system information is refreshed while the application is running.
- **Usage history** — live CPU and RAM graphs.
- **System health checks** — identifies normal, warning, critical, and unavailable readings for CPU, RAM, and storage.
- **Keyboard controls** — press `Q` to exit the dashboard.

### Health status thresholds

PC Monitor uses the following default thresholds for CPU, RAM, and storage usage:

| Status | Usage |
| --- | --- |
| `OK` | Below 80% |
| `WARNING` | 80% to below 95% |
| `CRITICAL` | 95% or higher |
| `UNKNOWN` | Required usage data is unavailable |

The overall system status reflects the most severe status reported by the monitored components.

## Screenshot

![PC Monitor dashboard](screenshots/dashboard.png)

## Requirements

- Python 3.10 or newer
- `pip`
- A terminal that supports the output provided by Rich

The project uses `psutil`, `rich`, and `keyboard`. Keyboard handling and access to some system information can vary by operating system and permissions. The project is primarily developed and tested on Windows.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/aleks360944/PC-Monitor-System-Resource-Monitor.git
cd PC-Monitor-System-Resource-Monitor
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it in Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

## Usage

Start the application from the project directory:

```bash
python main.py
```

The dashboard will open in the terminal and refresh its system information while running. Press `Q` to exit. You can also use `Ctrl+C` in the terminal to interrupt the application.

## Project structure

```text
PC-Monitor-System-Resource-Monitor/
├── screenshots/
│   └── dashboard.png       # Dashboard screenshot
├── cpu_monitor.py          # CPU information and usage
├── disk_monitor.py         # Storage information
├── health_checker.py       # CPU, RAM, and storage health checks
├── main.py                 # Application entry point
├── network_monitor.py      # Network interface information
├── ram_monitor.py          # Memory information and usage
├── ui.py                   # Terminal dashboard and graphs
├── requirements.txt        # Python dependencies
├── LICENSE                 # MIT License
└── README.md               # Project documentation
```

## Technologies

- [Python](https://www.python.org/) — application logic
- [psutil](https://github.com/giampaolo/psutil) — system and process utilities
- [Rich](https://github.com/Textualize/rich) — terminal dashboard and live display
- [keyboard](https://github.com/boppreh/keyboard) — keyboard input handling

## Project purpose

PC Monitor is a practical learning project focused on Python, modular code organization, system resource monitoring, terminal interfaces, and Git-based development.

## License

This project is licensed under the [MIT License](LICENSE).
