from __future__ import annotations

from collections import deque
from datetime import datetime
import time

import psutil
from textual.app import App, ComposeResult
from textual.containers import Grid, Horizontal, Vertical
from textual.widgets import Static

from cpu_monitor import get_cpu_data
from ram_monitor import get_ram_data
from disk_monitor import get_storage_list
from health_checker import check_cpu, check_ram, check_storage

try:
    from gpu_monitor import get_gpu_data
except ImportError:
    get_gpu_data = None


REFRESH_INTERVAL = 1.0
HISTORY_SIZE = 60


def _format_number(value, suffix="") -> str:
    if isinstance(value, (int, float)):
        return f"{value:.1f}{suffix}"
    return str(value)


def _sparkline(values, width=48) -> str:
    """Render recent percentages as a compact text graph."""
    if not values:
        return "Collecting samples..."
    # ASCII-only characters avoid missing-glyph boxes in Windows terminal fonts.
    levels = "⠤⠶⠿"
    result = []
    for value in list(values)[-width:]:
        value = max(0.0, min(100.0, float(value)))
        index = min(len(levels) - 1, int(value / 100 * (len(levels) - 1)))
        result.append(levels[index])
    return "".join(result).rjust(width)


def _health_summary(results) -> tuple[str, str]:
    if not results:
        return "UNKNOWN", "No health-check results are available."
    levels = {item.get("level", "UNKNOWN") for item in results}
    for level in ("CRITICAL", "WARNING", "UNKNOWN"):
        if level in levels:
            return level, "At least one component needs attention."
    if levels == {"OK"}:
        return "OK", "No issues detected by the current checks."
    return "UNKNOWN", "System health could not be fully determined."


def _format_health(results) -> str:
    status, description = _health_summary(results)
    lines = [f"● {status}  {description}", "", "COMPONENT             STATUS      DIAGNOSTIC"]
    for item in results:
        component = str(item.get("component", "Unknown"))[:20]
        level = str(item.get("level", "UNKNOWN"))
        message = str(item.get("message", "No diagnostic message"))
        lines.append(f"{component:<21} {level:<11} {message}")
    return "\n".join(lines)


def _format_storage() -> str:
    try:
        disks = get_storage_list()
        if not disks:
            return "No storage devices found."
        lines = []
        for disk in disks:
            lines.append(
                f"{disk.get('device', 'Unknown')} ({disk.get('mountpoint', '?')})\n"
                f"  Used: {disk.get('usage', '?')}%   "
                f"Free: {disk.get('free_gb', '?')} GB   "
                f"Total: {disk.get('total_gb', '?')} GB"
            )
        return "\n\n".join(lines)
    except Exception as exc:
        return f"Unable to collect storage data: {type(exc).__name__}: {exc}"


def _format_network() -> str:
    """Render network interfaces using psutil directly."""
    try:
        addresses = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        lines = []
        for name, addrs in addresses.items():
            status = stats.get(name)
            state = "UP" if status and status.isup else "DOWN"
            speed = status.speed if status else 0
            lines.append(f"{name}  [{state}]  {speed} Mbps")
            for addr in addrs:
                if addr.family == psutil.AF_LINK:
                    lines.append(f"  MAC: {addr.address}")
                elif getattr(addr.family, "name", "") == "AF_INET" or addr.family == 2:
                    lines.append(f"  IPv4: {addr.address}  Mask: {addr.netmask}")
                elif getattr(addr.family, "name", "") == "AF_INET6" or addr.family == 23:
                    lines.append(f"  IPv6: {addr.address}")
        return "\n".join(lines) if lines else "No network interfaces found."
    except Exception as exc:
        return f"Unable to collect network data: {type(exc).__name__}: {exc}"


def _format_gpu() -> str:
    if get_gpu_data is None:
        return "GPU monitor is unavailable."
    try:
        data = get_gpu_data()
        return (
            f"GPU usage:       {_format_number(data.get('gpu_usage'), '%')}\n"
            f"VRAM used:       {_format_number(data.get('vram_used_mb'), ' MB')}\n"
            f"Temperature:     {_format_number(data.get('temperature'), ' В°C')}\n"
            f"Core clock:      {_format_number(data.get('core_clock_mhz'), ' MHz')}\n"
            f"Memory clock:    {_format_number(data.get('memory_clock_mhz'), ' MHz')}"
        )
    except Exception as exc:
        return f"Unable to collect GPU data: {type(exc).__name__}: {exc}"


class PCMonitor(App):
    """Textual terminal dashboard for PC Monitor."""

    TITLE = "PC Monitor"
    SUB_TITLE = "System overview"

    CSS = """
    Screen {
        background: #101319;
        color: #E7EAF0;
        padding: 1 2;
    }

    #custom-header {
        height: 5;
        border: round #777F8C;
        padding: 0 2;
        margin-bottom: 1;
    }

    #title-block {
        width: 1fr;
        height: 3;
        content-align: left middle;
        text-style: bold;
        color: #F4F6FA;
    }

    #time-block {
        width: auto;
        min-width: 22;
        height: 3;
        content-align: right middle;
        color: #A9B2C0;
        text-style: bold;
    }

    .panel {
        border: round #454D5B;
        padding: 0 1;
        height: auto;
        min-height: 5;
        margin-bottom: 1;
        margin-right: 1;
    }

    .panel-title {
        text-style: bold;
        height: 1;
        margin-bottom: 1;
    }

    #health-panel {
        border: round #697386;
        padding: 0 1;
        height: auto;
        min-height: 5;
        margin-bottom: 1;
    }

    #graphs-row {
        height: 7;
        margin-bottom: 1;
    }

    #cpu-graph, #ram-graph {
        width: 1fr;
        border: round #454D5B;
        padding: 0 1;
        margin-right: 1;
    }

    #cpu-title { color: #8DADE0; }
    #ram-title, #gpu-title { color: #B5A0DC; }
    #health-title, #network-title { color: #85C4B1; }
    #storage-title { color: #D7B77E; }

    #details-grid {
        grid-size: 2 3;
        grid-columns: 1fr 1fr;
        grid-rows: auto auto auto;
        grid-gutter: 0 1;
        height: auto;
    }

    #cpu-details, #ram-details, #storage-panel, #network-panel, #gpu-panel {
        height: auto;
        min-height: 7;
    }

    /* Let NETWORK fill the right column while GPU sits under STORAGE. */
    #network-panel {
        row-span: 2;
    }

    #storage-panel {
        height: auto;
        min-height: 10;
        overflow-y: auto;
    }

    #footer {
        height: 1;
        content-align: center middle;
        color: #929AA8;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "quit", "Quit"),
    ]

    def __init__(
        self,
        cpu_fn=None,
        ram_fn=None,
        disk_fn=None,
        network_fn=None,
        gpu_fn=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        # Keep compatibility with the existing main.py entry point.
        self.cpu_fn = cpu_fn
        self.ram_fn = ram_fn
        self.disk_fn = disk_fn
        self.network_fn = network_fn
        self.gpu_fn = gpu_fn
        self.cpu_history = deque(maxlen=HISTORY_SIZE)
        self.ram_history = deque(maxlen=HISTORY_SIZE)
        self._last_health_results = []
        self._last_health_refresh = 0.0

    def compose(self) -> ComposeResult:
        with Horizontal(id="custom-header"):
            yield Static("PC MONITOR\nSYSTEM OVERVIEW", id="title-block")
            yield Static("", id="time-block")

        with Vertical(id="health-panel"):
            yield Static("SYSTEM HEALTH", classes="panel-title", id="health-title")
            yield Static("Initializing health checks...", id="health-content")

        with Horizontal(id="graphs-row"):
            with Vertical(id="cpu-graph"):
                yield Static("CPU HISTORY", classes="panel-title", id="cpu-title")
                yield Static("Collecting samples...", id="cpu-graph-content")
            with Vertical(id="ram-graph"):
                yield Static("RAM HISTORY", classes="panel-title", id="ram-title")
                yield Static("Collecting samples...", id="ram-graph-content")

        with Grid(id="details-grid"):
            with Vertical(classes="panel", id="cpu-details"):
                yield Static("CPU DETAILS", classes="panel-title", id="cpu-details-title")
                yield Static("Loading CPU data...", id="cpu-content")
            with Vertical(classes="panel", id="ram-details"):
                yield Static("MEMORY DETAILS", classes="panel-title", id="ram-title-details")
                yield Static("Loading memory data...", id="ram-content")
            with Vertical(classes="panel", id="storage-panel"):
                yield Static("STORAGE", classes="panel-title", id="storage-title")
                yield Static("Loading storage data...", id="storage-content")
            with Vertical(classes="panel", id="network-panel"):
                yield Static("NETWORK", classes="panel-title", id="network-title")
                yield Static("Loading network data...", id="network-content")
            with Vertical(classes="panel", id="gpu-panel"):
                yield Static("GPU DETAILS", classes="panel-title", id="gpu-title")
                yield Static("Loading GPU data...", id="gpu-content")

        yield Static("ctrl + Q     •     History: last 60 seconds", id="footer")

    def on_mount(self) -> None:
        psutil.cpu_percent(interval=None)
        self.update_dashboard()
        self.set_interval(REFRESH_INTERVAL, self.update_dashboard)

    def _set_text(self, selector: str, value: str) -> None:
        self.query_one(selector, Static).update(value)

    def update_dashboard(self) -> None:
        """Update existing widgets without rebuilding the layout."""
        self._set_text(
            "#time-block",
            f"{datetime.now():%Y-%m-%d %H:%M:%S}\n🟢 LIVE",
        )

        cpu_usage = None
        ram_usage = None
        try:
            cpu_data = get_cpu_data()
            cpu_usage = cpu_data.get("usage")
            if isinstance(cpu_usage, (int, float)):
                self.cpu_history.append(float(cpu_usage))
            cpu_text = (
                f"Model: {cpu_data.get('model', 'Unknown')}\n"
                f"Physical cores: {cpu_data.get('physical_cores', 'N/S')}\n"
                f"Logical cores: {cpu_data.get('logical_cores', 'N/S')}\n"
                f"Usage: {_format_number(cpu_usage, '%')}"
            )
        except Exception as exc:
            cpu_text = f"Unable to collect CPU data: {type(exc).__name__}: {exc}"

        try:
            ram_data = get_ram_data()
            ram_usage = ram_data.get("usage")
            if isinstance(ram_usage, (int, float)):
                self.ram_history.append(float(ram_usage))
            ram_text = (
                f"Total memory: {_format_number(ram_data.get('total_gb'), ' GB')}\n"
                f"Available: {_format_number(ram_data.get('available_gb'), ' GB')}\n"
                f"In use: {_format_number(ram_usage, '%')}"
            )
        except Exception as exc:
            ram_text = f"Unable to collect memory data: {type(exc).__name__}: {exc}"

        self._set_text("#cpu-content", cpu_text)
        self._set_text("#ram-content", ram_text)
        self._set_text(
            "#cpu-graph-content",
            f"{_format_number(cpu_usage, '%')}\n{_sparkline(self.cpu_history)}",
        )
        self._set_text(
            "#ram-graph-content",
            f"{_format_number(ram_usage, '%')}\n{_sparkline(self.ram_history)}",
        )
        self._set_text("#storage-content", _format_storage())
        self._set_text("#network-content", _format_network())
        self._set_text("#gpu-content", _format_gpu())

        # Health checks run every three seconds to avoid unnecessary work.
        monotonic_now = time.monotonic()
        if monotonic_now - self._last_health_refresh >= 3.0:
            try:
                self._last_health_results = check_cpu() + check_ram() + check_storage()
            except Exception as exc:
                self._last_health_results = [{
                    "component": "System Health",
                    "level": "UNKNOWN",
                    "message": f"Unable to run checks: {type(exc).__name__}: {exc}",
                }]
            self._last_health_refresh = monotonic_now
        self._set_text("#health-content", _format_health(self._last_health_results))


def run_dashboard(
    cpu_fn=None,
    ram_fn=None,
    disk_fn=None,
    network_fn=None,
    keyboard_module=None,
    gpu_fn=None,
) -> None:
    """Backward-compatible entry point used by the existing main.py."""
    PCMonitor(
        cpu_fn=cpu_fn,
        ram_fn=ram_fn,
        disk_fn=disk_fn,
        network_fn=network_fn,
        gpu_fn=gpu_fn,
    ).run()


if __name__ == "__main__":
    PCMonitor().run()
