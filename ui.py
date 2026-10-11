from collections import deque
from contextlib import redirect_stdout
from datetime import datetime
from io import StringIO
import textwrap
import time

import psutil
from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


REFRESH_INTERVAL = 0.5  # обновление примерно 2 раза в секунду
HISTORY_SIZE = int(60 / REFRESH_INTERVAL)  # храним историю примерно за 60 секунд


class MonitorHistory:
    """Keep a bounded history of CPU and RAM percentages."""

    def __init__(self, maxlen=HISTORY_SIZE):
        self.cpu = deque(maxlen=maxlen)
        self.ram = deque(maxlen=maxlen)

    def sample(self):
        self.cpu.append(psutil.cpu_percent(interval=None))
        self.ram.append(psutil.virtual_memory().percent)


def _capture_output(function, max_line_width=48):
    """Capture module output and wrap long lines to avoid layout jumps."""
    buffer = StringIO()
    try:
        with redirect_stdout(buffer):
            function()
    except Exception as exc:
        return Text(
            f"Unable to collect data: {type(exc).__name__}: {exc}",
            style="bold red",
        )

    output = buffer.getvalue().strip()
    if not output:
        return Text("No data available", style="white")

    # Keep long network/disk lines from forcing panels to recalculate their width.
    wrapped_lines = []
    for line in output.splitlines():
        if not line:
            wrapped_lines.append("")
            continue
        wrapped_lines.extend(
            textwrap.wrap(
                line,
                width=max_line_width,
                break_long_words=True,
                break_on_hyphens=False,
                replace_whitespace=False,
                drop_whitespace=True,
            ) or [""]
        )
    return Text("\n".join(wrapped_lines), style="white")


def _sparkline(values, width=24, minimum=0, maximum=100):
    """Render a compact terminal chart using Unicode block characters."""
    if not values:
        return Text("Collecting samples...", style="grey62")

    blocks = "▁▂▃▄▅▆▇█"
    recent = list(values)[-width:]
    result = Text()

    for value in recent:
        value = max(minimum, min(maximum, value))
        scaled = (value - minimum) / (maximum - minimum)
        index = min(len(blocks) - 1, int(scaled * (len(blocks) - 1)))
        result.append(blocks[index], style="bright_cyan")

    if len(recent) < width:
        result = Text(" " * (width - len(recent))) + result

    return result


def _graph_panel(title, values, accent, current_value, chart_width):
    # Фиксируем ширину графика относительно окна терминала.
    content = Table.grid(expand=True, padding=(0, 1))
    content.add_column(width=23, no_wrap=True)
    content.add_column(ratio=1, justify="right", no_wrap=True)

    left_info = Group(
        Text("CURRENT", style="grey62"),
        Text(f"{current_value:.1f}%", style=f"bold {accent}"),
        Text("RECENT SAMPLES", style="grey62"),
        Text("Scale: 0–100%", style="grey62"),
    )
    chart = Align.right(_sparkline(values, width=chart_width))
    content.add_row(left_info, chart)

    return Panel(
        content,
        title=f"[bold {accent}]{title}[/bold {accent}]",
        title_align="left",
        border_style="grey50",
        box=box.ROUNDED,
        padding=(1, 2),
    )


def _make_panel(content, title, accent="bright_cyan"):
    return Panel(
        content,
        title=f"[bold {accent}]{title}[/bold {accent}]",
        title_align="left",
        border_style="grey50",
        box=box.ROUNDED,
        padding=(1, 2),
    )


def build_dashboard(cpu_fn, ram_fn, disk_fn, network_fn, history, terminal_width=120):
    cpu_now = history.cpu[-1] if history.cpu else 0.0
    ram_now = history.ram[-1] if history.ram else 0.0

    # Подстраиваем графики и текст под ширину окна, чтобы панели не распирало.
    chart_width = max(8, min(36, (terminal_width - 76) // 2))
    detail_line_width = max(30, min(64, (terminal_width - 16) // 2))

    cpu_content = _capture_output(cpu_fn, detail_line_width)
    ram_content = _capture_output(ram_fn, detail_line_width)
    disk_content = _capture_output(disk_fn, detail_line_width)
    network_content = _capture_output(network_fn, detail_line_width)

    header_grid = Table.grid(expand=True)
    header_grid.add_column(ratio=3, no_wrap=True)
    header_grid.add_column(ratio=2, justify="right", no_wrap=True)
    header_grid.add_row(
        Text("PC MONITOR", style="bold white"),
        Text(datetime.now().strftime("%Y-%m-%d  %H:%M:%S"), style="grey70"),
    )
    header_grid.add_row(
        Text("SYSTEM OVERVIEW", style="grey70"),
        Text("● LIVE", style="bold green"),
    )

    header = Panel(
        header_grid,
        border_style="grey50",
        box=box.ROUNDED,
        padding=(1, 2),
    )

    graphs = Table.grid(expand=True, padding=(0, 1))
    graphs.add_column(ratio=1, min_width=1)
    graphs.add_column(ratio=1, min_width=1)
    graphs.add_row(
        _graph_panel("CPU HISTORY", history.cpu, "bright_cyan", cpu_now, chart_width),
        _graph_panel("RAM HISTORY", history.ram, "bright_cyan", ram_now, chart_width),
    )

    details = Table.grid(expand=True, padding=(0, 1))
    details.add_column(ratio=1, min_width=1)
    details.add_column(ratio=1, min_width=1)
    details.add_row(
        _make_panel(cpu_content, "CPU DETAILS"),
        _make_panel(ram_content, "MEMORY DETAILS"),
    )
    details.add_row(
        _make_panel(disk_content, "STORAGE"),
        _make_panel(network_content, "NETWORK"),
    )

    footer = Align.center(
        Text("Q  Exit     •     History: last 60 seconds", style="grey62"),
        vertical="middle",
    )

    return Group(header, graphs, details, footer)


def run_dashboard(cpu_fn, ram_fn, disk_fn, network_fn, keyboard_module):
    console = Console()
    history = MonitorHistory()

    # Первый вызов задаёт базу для последующих измерений CPU.
    psutil.cpu_percent(interval=None)

    initial_view = Panel(
        Align.center("Initializing system monitor...", vertical="middle"),
        title="[bold white]PC MONITOR[/bold white]",
        border_style="grey50",
        box=box.ROUNDED,
    )

    # Отключаем фоновую перерисовку: обновляем экран только после сборки
    # целого нового кадра, чтобы избежать визуальных скачков.
    with Live(
        initial_view,
        console=console,
        screen=True,
        auto_refresh=False,
        vertical_overflow="crop",
    ) as live:
        while True:
            if keyboard_module.is_pressed("q"):
                break

            history.sample()
            frame = build_dashboard(
                cpu_fn,
                ram_fn,
                disk_fn,
                network_fn,
                history,
                terminal_width=console.size.width,
            )
            live.update(frame, refresh=True)

            # Ждём до следующего обновления, регулярно проверяя клавишу выхода.
            next_update = time.monotonic() + REFRESH_INTERVAL
            while True:
                if keyboard_module.is_pressed("q"):
                    return
                remaining = next_update - time.monotonic()
                if remaining <= 0:
                    break
                time.sleep(min(0.05, remaining))
