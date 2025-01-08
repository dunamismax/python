#!/usr/bin/env python3
"""
py-top: An interactive CLI app using Typer that runs a Textual-based TUI
for displaying real-time CPU, memory, and process usage.

Usage:
  python py-top.py run-tui

Optional arguments:
  --refresh-interval FLOAT  Seconds between screen updates (default: 1.0)

Press 'q' or 'Ctrl+C' to exit the TUI.
"""

import asyncio
import psutil
import typer

from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.reactive import reactive
from textual.widgets import Static, DataTable, Header, Footer, ProgressBar

app = typer.Typer(help="A Typer-based CLI for an interactive Textual TUI.")


class SystemStats(Static):
    """
    A widget displaying system-wide CPU and memory usage as progress bars.
    """

    cpu_usage: reactive[float] = reactive(0.0)
    mem_usage: reactive[float] = reactive(0.0)

    def compose(self) -> ComposeResult:
        """Compose the child widgets (two progress bars)."""
        with Vertical():
            yield ProgressBar(total=100, show_percentage=True, id="cpu_bar")
            yield ProgressBar(total=100, show_percentage=True, id="mem_bar")

    def watch_cpu_usage(self, usage: float) -> None:
        """Called automatically when cpu_usage is updated."""
        cpu_bar = self.query_one("#cpu_bar", ProgressBar)
        cpu_bar.update(int(usage))

    def watch_mem_usage(self, usage: float) -> None:
        """Called automatically when mem_usage is updated."""
        mem_bar = self.query_one("#mem_bar", ProgressBar)
        mem_bar.update(int(usage))


class ProcessTable(DataTable):
    """
    A table widget that displays processes in descending order by CPU usage.
    """

    async def on_mount(self) -> None:
        """
        Set up the table columns after mounting.
        """
        self.show_header = True
        self.show_footer = False
        self.zebra_stripes = True

        self.add_column("PID", width=8)
        self.add_column("USER", width=16)
        self.add_column("NAME", width=25)
        self.add_column("CPU%", width=8, justify="right")
        self.add_column("MEM%", width=8, justify="right")

    def update_process_data(self, procs: list) -> None:
        """
        Clear the table and re-populate with new process information.
        """
        self.clear(rows=True)
        for proc in procs:
            self.add_row(
                str(proc["pid"]),
                proc["username"][:15] if proc["username"] else "-",
                proc["name"][:25] if proc["name"] else "-",
                f"{proc['cpu_percent']:.1f}",
                f"{proc['memory_percent']:.1f}",
            )


class PyTop(App):
    """
    Main Textual Application for monitoring system stats and processes.
    """

    CSS = """
    Screen {
        layout: vertical;
    }
    #top_container {
        dock: top;
        height: 5;
    }
    #process_container {
        dock: fill;
    }
    """

    BINDINGS = [("q", "quit", "Quit the application")]

    def __init__(self, refresh_interval: float = 1.0) -> None:
        """
        Initialize the PyTop application.

        Args:
            refresh_interval (float): Seconds between data refreshes.
        """
        super().__init__()
        self.refresh_interval = refresh_interval

    def compose(self) -> ComposeResult:
        """
        Compose the layout:
        A header at the top, system stats right below,
        and a scrollable container with a process table at the bottom.
        A footer is docked at the bottom for help text.
        """
        yield Header(show_clock=True)
        with Horizontal(id="top_container"):
            yield SystemStats()
        with ScrollableContainer(id="process_container"):
            yield ProcessTable()
        yield Footer()

    async def on_mount(self) -> None:
        """
        Called when the app is first mounted.
        We schedule the auto-refresh task here.
        """
        self.system_stats = self.query_one(SystemStats)
        self.process_table = self.query_one(ProcessTable)
        self.set_interval(self.refresh_interval, self.refresh_data)

    def refresh_data(self) -> None:
        """
        Fetch latest CPU, Memory, and Process stats; update widgets.
        """
        cpu_percent = psutil.cpu_percent(interval=None)
        mem_info = psutil.virtual_memory()

        self.system_stats.cpu_usage = cpu_percent
        self.system_stats.mem_usage = mem_info.percent

        # Gather processes, sorted by CPU usage
        processes = []
        for proc in psutil.process_iter(
            ["pid", "name", "username", "cpu_percent", "memory_percent"]
        ):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        processes.sort(key=lambda x: x["cpu_percent"], reverse=True)
        self.process_table.update_process_data(processes)

    def action_quit(self) -> None:
        """Action for the 'q' binding. Exits the application cleanly."""
        self.exit()


@app.command()
def run_tui(
    refresh_interval: float = typer.Option(1.0, help="Seconds between screen updates")
):
    """
    Start the Textual TUI for real-time system monitoring.
    """
    asyncio.run(PyTop(refresh_interval=refresh_interval).run())


if __name__ == "__main__":
    app()
