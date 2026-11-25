from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Grid, Horizontal, Vertical
from textual.widgets import Static

from cpu_monitor import get_cpu_data
from ram_monitor import get_ram_data
from disk_monitor import get_storage_list
from network_monitor import network_info
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


def _format_storage(disks) -> str:
    if not disks:
        return "No storage devices found."
    return "\n\n".join(
        f"{disk.get('device', 'Unknown')} ({disk.get('mountpoint', '?')})\n"
        f"  Used: {disk.get('usage', '?')}%   "
        f"Free: {disk.get('free_gb', '?')} GB   "
        f"Total: {disk.get('total_gb', '?')} GB"
        for disk in disks
    )


def _format_network(interfaces) -> str:
    if not interfaces:
        return "No network interfaces found."
    lines = []
    for interface in interfaces:
        state = "UP" if interface.get("is_up") else "DOWN"
        lines.append(f"{interface.get('name', 'Unknown')}  [{state}]  {interface.get('speed_mbps', 0)} Mbps")
        lines.extend(f"  IPv4: {addr['address']}  Mask: {addr.get('netmask')}" for addr in interface.get("ipv4", []))
        lines.extend(f"  IPv6: {addr}" for addr in interface.get("ipv6", []))
        lines.extend(f"  MAC: {addr}" for addr in interface.get("mac", []))
    return "\n".join(lines)


def _format_gpu(data) -> str:
    if data is None:
        return "GPU monitor is unavailable."
    return (
        f"GPU usage:       {_format_number(data.get('gpu_usage'), '%')}\n"
        f"VRAM used:       {_format_number(data.get('vram_used_mb'), ' MB')}\n"
        f"Temperature:     {_format_number(data.get('temperature'), ' °C')}\n"
        f"Core clock:      {_format_number(data.get('core_clock_mhz'), ' MHz')}\n"
        f"Memory clock:    {_format_number(data.get('memory_clock_mhz'), ' MHz')}"
    )


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
        self.cpu_fn = cpu_fn or get_cpu_data
        self.ram_fn = ram_fn or get_ram_data
        self.disk_fn = disk_fn or get_storage_list
        self.network_fn = network_fn or network_info
        self.gpu_fn = gpu_fn or get_gpu_data
        self.cpu_history = deque(maxlen=HISTORY_SIZE)
        self.ram_history = deque(maxlen=HISTORY_SIZE)
        self._last_health_results = []
        self._update_running = False

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

    async def on_mount(self) -> None:
        await self.update_dashboard()
        self.set_interval(REFRESH_INTERVAL, self.update_dashboard)

    def _set_text(self, selector: str, value: str) -> None:
        self.query_one(selector, Static).update(value)

    def _collect_data(self):
        """Run every potentially slow source away from Textual's UI thread."""
        data = {}
        errors = {}
        sources = {
            "cpu": (self.cpu_fn, {"usage": None}),
            "ram": (self.ram_fn, {"usage": None}),
            "storage": (self.disk_fn, []),
            "network": (self.network_fn, []),
            "gpu": (self.gpu_fn, None),
        }
        for name, (source, fallback) in sources.items():
            if source is None:
                data[name] = fallback
                continue
            try:
                data[name] = source()
            except Exception as exc:
                data[name] = fallback
                errors[name] = f"{type(exc).__name__}: {exc}"
        return data, errors

    async def update_dashboard(self) -> None:
        """Collect samples on a worker thread and only render them on the UI thread."""
        if self._update_running:
            return
        self._update_running = True
        self._set_text(
            "#time-block",
            f"{datetime.now():%Y-%m-%d %H:%M:%S}\n🟢 LIVE",
        )
        try:
            data, errors = await asyncio.to_thread(self._collect_data)
        finally:
            self._update_running = False

        cpu_data = data["cpu"]
        ram_data = data["ram"]
        storage_data = data["storage"]
        cpu_usage = cpu_data.get("usage") if isinstance(cpu_data, dict) else None
        ram_usage = ram_data.get("usage") if isinstance(ram_data, dict) else None
        if errors.get("cpu"):
            cpu_text = f"Unable to collect CPU data: {errors['cpu']}"
        elif not isinstance(cpu_data, dict):
            cpu_text = "CPU data source returned an invalid result."
        else:
            cpu_usage = cpu_data.get("usage")
            if isinstance(cpu_usage, (int, float)):
                self.cpu_history.append(float(cpu_usage))
            cpu_text = (
                f"Model: {cpu_data.get('model', 'Unknown')}\n"
                f"Physical cores: {cpu_data.get('physical_cores', 'N/S')}\n"
                f"Logical cores: {cpu_data.get('logical_cores', 'N/S')}\n"
                f"Usage: {_format_number(cpu_usage, '%')}"
            )
        if errors.get("ram"):
            ram_text = f"Unable to collect memory data: {errors['ram']}"
        elif not isinstance(ram_data, dict):
            ram_text = "Memory data source returned an invalid result."
        else:
            ram_usage = ram_data.get("usage")
            if isinstance(ram_usage, (int, float)):
                self.ram_history.append(float(ram_usage))
            ram_text = (
                f"Total memory: {_format_number(ram_data.get('total_gb'), ' GB')}\n"
                f"Available: {_format_number(ram_data.get('available_gb'), ' GB')}\n"
                f"In use: {_format_number(ram_usage, '%')}"
            )
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
        self._set_text(
            "#storage-content",
            f"Unable to collect storage data: {errors['storage']}" if errors.get("storage") else _format_storage(storage_data),
        )
        self._set_text(
            "#network-content",
            f"Unable to collect network data: {errors['network']}" if errors.get("network") else _format_network(data["network"]),
        )
        self._set_text(
            "#gpu-content",
            f"Unable to collect GPU data: {errors['gpu']}" if errors.get("gpu") else _format_gpu(data["gpu"]),
        )

        try:
            self._last_health_results = (
                check_cpu(cpu_data if isinstance(cpu_data, dict) else {"usage": None})
                + check_ram(ram_data if isinstance(ram_data, dict) else {"usage": None})
                + check_storage(storage_data if isinstance(storage_data, list) else [])
            )
            for component, key in (("CPU", "cpu"), ("RAM", "ram"), ("Storage", "storage")):
                if errors.get(key):
                    self._last_health_results.append({
                        "component": component,
                        "level": "UNKNOWN",
                        "message": f"Unable to collect data: {errors[key]}",
                    })
        except Exception as exc:
            self._last_health_results = [{
                "component": "System Health",
                "level": "UNKNOWN",
                "message": f"Unable to run checks: {type(exc).__name__}: {exc}",
            }]
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
