"""
benchmarker.py - A Textual TUI CPU and RAM benchmarker

Requirements:
    - Python 3.8+
    - textual (pip install textual)

Usage:
    python benchmarker.py

This application provides a menu to select between:
    1) CPU Benchmark
    2) RAM Benchmark
    3) Both CPU & RAM

When a benchmark starts, it will:
    - Spin up multiple CPU workers to keep CPU usage high for ~10 seconds.
    - Allocate and hold a large list of random data in memory for ~10 seconds (RAM test).

Press Ctrl+C to exit at any time.
"""

import sys
import math
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Static, Header, Footer
from textual.containers import Vertical, Horizontal, Container
from textual.reactive import reactive

# ---------------------------
# Helpers for Benchmark Logic
# ---------------------------


def cpu_stress_test(duration: float = 10.0, workers: int = None) -> None:
    """
    Keep CPU cores busy for 'duration' seconds by repeatedly performing
    math operations in multiple threads.
    """
    if workers is None:
        # By default, use the number of available logical CPUs
        import multiprocessing

        workers = multiprocessing.cpu_count()

    def cpu_heavy_task() -> None:
        end_time = time.time() + duration
        result = 0
        while time.time() < end_time:
            # Some semi-random math computations
            # to keep the CPU busy
            for _ in range(50000):
                x = random.random()
                result += int(math.sqrt(x**2))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        tasks = [executor.submit(cpu_heavy_task) for _ in range(workers)]
        # Wait for all threads to finish
        for t in tasks:
            t.result()  # Just to make sure exceptions, if any, propagate


def ram_stress_test(duration: float = 10.0, list_size: int = 10_000_000) -> None:
    """
    Allocate a large list of random integers to consume RAM for 'duration' seconds.
    list_size determines how large the allocated list will be.

    Note: This can quickly consume hundreds of MBs of RAM depending on list_size.
          Adjust with caution if you have limited memory.
    """
    # Allocate
    big_list = [random.randint(0, 100) for _ in range(list_size)]

    # Hold for the specified duration
    time.sleep(duration)

    # Deallocate by letting big_list go out of scope at function exit


def do_benchmark(cpu: bool, ram: bool, callback=None) -> None:
    """
    Executes CPU and/or RAM benchmarks in parallel (if both are selected).
    'callback' is optionally called after each test (useful to update TUI).
    """
    threads = []

    if cpu:
        t_cpu = threading.Thread(target=cpu_stress_test, kwargs={"duration": 10})
        threads.append(t_cpu)

    if ram:
        t_ram = threading.Thread(target=ram_stress_test, kwargs={"duration": 10})
        threads.append(t_ram)

    for t in threads:
        t.start()

    # Optionally update TUI or show progress while benchmarks are running
    if callback:
        # Example: simple spinner or textual update
        while any(t.is_alive() for t in threads):
            callback()
            time.sleep(0.5)

    for t in threads:
        t.join()


# ---------------------------
# Textual TUI Application
# ---------------------------


class BenchmarkMenuScreen(Screen):
    """
    Main menu screen where the user can choose CPU, RAM, or BOTH.
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Welcome to Benchmarker! Select an option:\n", id="welcome-text")
        # Container to hold buttons
        with Vertical():
            yield Button("CPU Benchmark", id="cpu")
            yield Button("RAM Benchmark", id="ram")
            yield Button("Both CPU & RAM", id="both")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button presses from the main menu.
        """
        if event.button.id == "cpu":
            self.app.push_screen(RunBenchmarkScreen(cpu=True, ram=False))
        elif event.button.id == "ram":
            self.app.push_screen(RunBenchmarkScreen(cpu=False, ram=True))
        elif event.button.id == "both":
            self.app.push_screen(RunBenchmarkScreen(cpu=True, ram=True))


class RunBenchmarkScreen(Screen):
    """
    Screen that runs the requested benchmark(s) and displays status updates.
    """

    BENCHMARK_INTERVAL = 0.5  # seconds between updates

    # Reactive attribute to store status
    status_text: reactive[str] = reactive("Initializing benchmark...")

    def __init__(self, cpu: bool, ram: bool):
        super().__init__()
        self.cpu = cpu
        self.ram = ram
        self.running = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Benchmark in progress...", id="benchmark-title")
        yield Static(self.status_text, id="status")
        yield Footer()

    def on_mount(self) -> None:
        """
        When this screen is first mounted, start the benchmark in a background thread
        to keep the UI responsive.
        """
        self.running = True

        def update_callback():
            # Called while the benchmark is running - we can update some spinner, etc.
            self.status_text = "Running benchmark..."

        def run_benchmark():
            # Perform benchmark
            do_benchmark(self.cpu, self.ram, callback=update_callback)
            # Once done, update status and return to the main menu automatically
            self.status_text = "Benchmark complete! Returning to menu..."
            time.sleep(2.0)
            self.app.pop_screen()

        thread = threading.Thread(target=run_benchmark, daemon=True)
        thread.start()


class BenchmarkerApp(App):
    """
    Main App class to manage the TUI for Benchmarker.
    """

    CSS_PATH = None  # You can specify a .css file for styling if desired
    BINDINGS = [
        ("ctrl+c", "quit", "Exit Benchmarker"),
    ]

    def on_mount(self) -> None:
        """
        Called after the app has initialized and is ready to display content.
        We push the main menu screen here.
        """
        self.push_screen(BenchmarkMenuScreen())


def main():
    """
    Main entry point for the Benchmarker TUI.
    """
    app = BenchmarkerApp()
    app.run()


if __name__ == "__main__":
    sys.exit(main())
