# PC Monitor

A lightweight, terminal-based system monitoring tool written in Python.

PC Monitor provides a live overview of your computer's resources through a clean terminal dashboard powered by Rich.

## Features

- **CPU Monitoring** — processor information, core count, and CPU usage.
- **Memory Monitoring** — total, available, and used RAM.
- **Storage Monitoring** — disk capacity and usage information.
- **Network Monitoring** — network interfaces, IP addresses, MAC addresses, and connection status.
- **Live Dashboard** — a structured terminal interface with automatically refreshed system information.
- **Usage History** — real-time CPU and RAM usage graphs.
- **Keyboard Controls** — press `Q` to exit the dashboard.

## Technologies

- Python
- [psutil](https://github.com/giampaolo/psutil) — system and process utilities.
- [Rich](https://github.com/Textualize/rich) — terminal interface and live dashboard.
- [keyboard](https://github.com/boppreh/keyboard) — keyboard input handling.

## Requirements

- Python 3.10 or newer
- Windows, Linux, or another platform supported by the required dependencies.

Some features and keyboard controls may behave differently depending on the operating system and permissions.

## Installation

Clone the repository:

```bash
git clone https://github.com/aleks360944/PC-Monitor.git
cd PC-Monitor
```

Create and activate a virtual environment (optional but recommended):

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

## Usage

Run the application:

```bash
python main.py
```

The dashboard will display your system information and update continuously.

Press `Q` to exit.

## Project Structure

```text
PC-Monitor/
├── main.py          # Application entry point
├── ui.py            # Terminal dashboard and graphs
├── test_cpu.py      # CPU information
├── test_ram.py      # Memory information
├── test_disk.py     # Storage information
├── test_net.py      # Network information
├── requirements.txt # Python dependencies
├── .gitignore       # Git exclusions
└── README.md        # Project documentation
```

## Project Goals

This project was created as a practical Python learning project to explore system monitoring, modular application design, terminal interfaces, and working with hardware-related information.

Future improvements may include hardware temperature monitoring, disk health diagnostics, and a standalone Windows executable.

## License

No license has been specified yet. All rights reserved by default until a license is added.
