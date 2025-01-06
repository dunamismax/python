#!/usr/bin/env python3
"""
py-top.py
A Textual-based TUI that displays real-time CPU, memory, and process usage.

Usage:
  python py-top.py

Press 'q' or 'Ctrl+C' to exit.
"""

import asyncio
import psutil
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, DataTable, Header, Footer, ProgressBar
from textual.reactive import reactive

REFRESH_INTERVAL = 1.0  # seconds between refreshes


class SystemStats(Static):
    """
    A widget displaying system-wide CPU and memory usage as progress bars.
    """

    cpu_usage: reactive[float] = reactive(0.0)
    mem_usage: reactive[float] = reactive(0.0)

    def compose(self) -> ComposeResult:
        """Compose the child widgets (two progress bars)."""
        with Vertical():
            yield ProgressBar(total=100, show_percentage=True, name="cpu_bar")
            yield ProgressBar(total=100, show_percentage=True, name="mem_bar")

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

        # Define columns (stretch=False uses minimal width, can adjust as needed)
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
        We kick off the auto-refresh task here.
        """
        self.system_stats = self.query_one(SystemStats)
        self.process_table = self.query_one(ProcessTable)
        self.set_interval(REFRESH_INTERVAL, self.refresh_data)

    def refresh_data(self) -> None:
        """
        Fetch latest CPU, Memory, and Process stats; update widgets.
        """
        # Gather CPU & memory stats
        cpu_percent = psutil.cpu_percent(interval=None)
        mem_info = psutil.virtual_memory()
        mem_percent = mem_info.percent

        # Update reactive fields in SystemStats widget
        self.system_stats.cpu_usage = cpu_percent
        self.system_stats.mem_usage = mem_percent

        # Gather processes, sorted by CPU usage
        processes = []
        for proc in psutil.process_iter(
            ["pid", "name", "username", "cpu_percent", "memory_percent"]
        ):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Sort by CPU usage descending
        processes.sort(key=lambda x: x["cpu_percent"], reverse=True)

        # Update the data table
        self.process_table.update_process_data(processes)

    def action_quit(self) -> None:
        """
        Action for the 'q' binding. Exits the application cleanly.
        """
        self.exit()


if __name__ == "__main__":
    asyncio.run(PyTop().run())
