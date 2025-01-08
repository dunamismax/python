#!/usr/bin/env python3
"""
benchmarker.py - A Typer + curses TUI/CLI CPU and RAM benchmarker,
with enhanced Rich-based output for CLI commands.

Requirements:
    - Python 3.8+
    - typer (pip install typer)
    - rich (pip install rich)
    - (No external dependencies for curses; part of stdlib on most systems.)

Usage:
    # Method 1: TUI (Interactive; default if no command is given)
    python benchmarker.py
    python benchmarker.py tui

    # Method 2: Direct Commands (Typer + Rich output)
    python benchmarker.py cpu
    python benchmarker.py ram --list-size 5000000
    python benchmarker.py both

Description:
    This application allows you to run CPU and/or RAM benchmarks either:
      - Via curses-based TUI (if no command is provided or via 'tui' subcommand).
      - Via Typer commands with Rich-based output.

Press Ctrl+C at any time to exit.
"""

import sys
import math
import time
import random
import curses
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor

import typer
from rich.console import Console
from rich.table import Table

# ------------------------------------------------------------------------------
# Create a Typer app and a Rich console
# ------------------------------------------------------------------------------
app = typer.Typer(
    help="A CPU and RAM benchmarking application with both CLI (Typer+Rich) and TUI (curses)."
)
console = Console()

# ------------------------------------------------------------------------------
# Benchmark Logic
# ------------------------------------------------------------------------------


def cpu_stress_test(duration: float = 10.0, workers: int = None) -> None:
    """
    Keep CPU cores busy for 'duration' seconds by repeatedly performing math
    operations in multiple threads.
    """
    if workers is None or workers <= 0:
        workers = multiprocessing.cpu_count()

    def cpu_heavy_task() -> None:
        end_time = time.time() + duration
        result = 0
        while time.time() < end_time:
            # Some semi-random math computations to keep the CPU busy
            for _ in range(50_000):
                x = random.random()
                result += int(math.sqrt(x**2))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        tasks = [executor.submit(cpu_heavy_task) for _ in range(workers)]
        for t in tasks:
            # Wait for all threads to finish and propagate any exceptions
            t.result()


def ram_stress_test(duration: float = 10.0, list_size: int = 10_000_000) -> None:
    """
    Allocate a large list of random integers to consume RAM for 'duration' seconds.
    """
    # Allocate
    big_list = [random.randint(0, 100) for _ in range(list_size)]
    # Hold for the specified duration
    time.sleep(duration)
    # Deallocate by going out of scope


def do_benchmark(
    cpu: bool,
    ram: bool,
    duration: float = 10.0,
    list_size: int = 10_000_000,
    workers: int = None,
) -> None:
    """
    Execute CPU and/or RAM benchmarks, possibly in parallel.
    """
    threads = []

    if cpu:
        cpu_thread = threading.Thread(
            target=cpu_stress_test, kwargs={"duration": duration, "workers": workers}
        )
        threads.append(cpu_thread)

    if ram:
        ram_thread = threading.Thread(
            target=ram_stress_test,
            kwargs={"duration": duration, "list_size": list_size},
        )
        threads.append(ram_thread)

    # Start all benchmarks in parallel
    for t in threads:
        t.start()

    # Wait for all benchmarks to complete
    for t in threads:
        t.join()


# ------------------------------------------------------------------------------
# Typer Commands (Rich Output)
# ------------------------------------------------------------------------------


@app.command()
def cpu(
    duration: float = typer.Option(10.0, help="Number of seconds to stress CPU."),
    workers: int = typer.Option(
        None, help="Number of CPU worker threads. Defaults to CPU count."
    ),
):
    """
    Run a CPU benchmark by keeping all cores busy for the specified duration.
    """
    console.rule("[bold magenta]CPU Benchmark[/bold magenta]")
    console.print(f"Starting CPU benchmark for [cyan]{duration}[/cyan] seconds...")
    cpu_stress_test(duration=duration, workers=workers)
    console.print("[green]CPU benchmark finished![/green]")


@app.command()
def ram(
    duration: float = typer.Option(
        10.0, help="Number of seconds to hold allocated memory."
    ),
    list_size: int = typer.Option(
        10_000_000, help="Number of elements to allocate in a list."
    ),
):
    """
    Run a RAM benchmark by allocating a large list for the specified duration.
    """
    mb_estimate = list_size * (24 / 1_000_000)  # rough estimate in MB
    console.rule("[bold magenta]RAM Benchmark[/bold magenta]")
    console.print(
        f"Allocating approximately [cyan]{mb_estimate:.2f} MB[/cyan] "
        f"for [cyan]{duration}[/cyan] seconds..."
    )
    ram_stress_test(duration=duration, list_size=list_size)
    console.print("[green]RAM benchmark finished![/green]")


@app.command()
def both(
    duration: float = typer.Option(
        10.0, help="Number of seconds to stress CPU and hold allocated memory."
    ),
    list_size: int = typer.Option(
        10_000_000, help="Number of elements to allocate in a list."
    ),
    workers: int = typer.Option(
        None, help="Number of CPU worker threads. Defaults to CPU count."
    ),
):
    """
    Run both CPU and RAM benchmarks in parallel for the specified duration.
    """
    mb_estimate = list_size * (24 / 1_000_000)  # rough estimate in MB
    console.rule("[bold magenta]CPU & RAM Benchmark[/bold magenta]")
    console.print(
        f"  • CPU for [cyan]{duration}[/cyan] seconds (workers=[cyan]{workers or 'CPU count'}[/cyan])"
    )
    console.print(
        f"  • RAM (~[cyan]{mb_estimate:.2f} MB[/cyan]) for [cyan]{duration}[/cyan] seconds"
    )
    do_benchmark(
        cpu=True, ram=True, duration=duration, list_size=list_size, workers=workers
    )
    console.print("[green]CPU & RAM benchmark finished![/green]")


@app.command()
def tui():
    """
    Launch the curses-based interactive TUI.
    """
    console.print("[bold green]Launching TUI...[/bold green]")
    try:
        curses.wrapper(run_curses_app)
    except KeyboardInterrupt:
        console.print("\n[red]Interrupted by user. Exiting...[/red]")
        raise typer.Exit()


# ------------------------------------------------------------------------------
# curses-based TUI
# ------------------------------------------------------------------------------


def run_curses_app(stdscr):
    """
    Primary entry point for the curses-based TUI. This handles:
        - Displaying a menu for benchmark selection (CPU, RAM, BOTH).
        - Allowing the user to enter custom duration/list_size if needed.
        - Running the benchmark and showing the result on screen.
    """
    curses.curs_set(0)  # Hide the cursor in the menu
    stdscr.keypad(True)
    menu_items = ["CPU Benchmark", "RAM Benchmark", "Both CPU & RAM", "Exit"]
    current_idx = 0

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        title = "Benchmarker - Select an option:"
        stdscr.addstr(1, max(0, (w - len(title)) // 2), title, curses.A_BOLD)

        for i, item in enumerate(menu_items):
            # Calculate row/column for item
            row = (h // 2 - len(menu_items)) + (i * 2)
            col = max(0, (w - 30) // 2)
            if i == current_idx:
                stdscr.attron(curses.A_REVERSE)
                stdscr.addstr(row, col, f"{item}", curses.A_BOLD)
                stdscr.attroff(curses.A_REVERSE)
            else:
                stdscr.addstr(row, col, f"{item}")

        stdscr.refresh()
        key = stdscr.getch()

        if key in (curses.KEY_UP, ord("k")):
            current_idx = (current_idx - 1) % len(menu_items)
        elif key in (curses.KEY_DOWN, ord("j")):
            current_idx = (current_idx + 1) % len(menu_items)
        elif key in (curses.KEY_ENTER, ord("\n")):
            selection = menu_items[current_idx]
            if selection == "Exit":
                break
            else:
                handle_benchmark_selection(stdscr, selection)
        elif key in (ord("q"), 27):  # 'q' or ESC to exit
            break


def prompt_float(stdscr, prompt_msg: str, default_val: float) -> float:
    """
    Prompt the user for a float value in curses; fallback to default if invalid.
    """
    curses.echo()
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    stdscr.addstr(h // 2, max(0, (w - len(prompt_msg) - 10) // 2), prompt_msg)
    stdscr.addstr(h // 2 + 1, max(0, (w // 2) - 5), f"[default: {default_val}] ")
    stdscr.refresh()

    inp = stdscr.getstr(
        h // 2 + 1, (w // 2) - 5 + len(f"[default: {default_val}] "), 20
    )
    curses.noecho()

    try:
        val = float(inp.decode().strip())
        return val
    except ValueError:
        return default_val


def prompt_int(stdscr, prompt_msg: str, default_val: int) -> int:
    """
    Prompt the user for an integer value in curses; fallback to default if invalid.
    """
    curses.echo()
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    stdscr.addstr(h // 2, max(0, (w - len(prompt_msg) - 10) // 2), prompt_msg)
    stdscr.addstr(h // 2 + 1, max(0, (w // 2) - 5), f"[default: {default_val}] ")
    stdscr.refresh()

    inp = stdscr.getstr(
        h // 2 + 1, (w // 2) - 5 + len(f"[default: {default_val}] "), 20
    )
    curses.noecho()

    try:
        val = int(inp.decode().strip())
        return val
    except ValueError:
        return default_val


def handle_benchmark_selection(stdscr, selection: str):
    """
    Based on user selection, prompt for relevant data (duration, list_size, workers)
    and perform the benchmark with curses-based UI feedback.
    """
    if selection == "CPU Benchmark":
        duration = prompt_float(stdscr, "Enter CPU benchmark duration (seconds):", 10.0)
        workers = prompt_int(stdscr, "Enter number of CPU workers (0 for default):", 0)

        stdscr.clear()
        stdscr.addstr(0, 0, f"Running CPU Benchmark for {duration}s ...")
        stdscr.refresh()

        if workers <= 0:
            workers = None
        cpu_stress_test(duration=duration, workers=workers)

        stdscr.addstr(2, 0, "CPU Benchmark finished! Press any key to continue...")
        stdscr.getch()

    elif selection == "RAM Benchmark":
        duration = prompt_float(stdscr, "Enter RAM benchmark duration (seconds):", 10.0)
        list_size = prompt_int(stdscr, "Enter list size for RAM test:", 10_000_000)

        stdscr.clear()
        mb_estimate = list_size * (24 / 1_000_000)
        stdscr.addstr(
            0, 0, f"Running RAM Benchmark (~{mb_estimate:.2f} MB) for {duration}s ..."
        )
        stdscr.refresh()

        ram_stress_test(duration=duration, list_size=list_size)

        stdscr.addstr(2, 0, "RAM Benchmark finished! Press any key to continue...")
        stdscr.getch()

    else:  # "Both CPU & RAM"
        duration = prompt_float(stdscr, "Enter benchmark duration (seconds):", 10.0)
        list_size = prompt_int(stdscr, "Enter list size for RAM test:", 10_000_000)
        workers = prompt_int(stdscr, "Enter number of CPU workers (0 for default):", 0)

        stdscr.clear()
        mb_estimate = list_size * (24 / 1_000_000)
        worker_msg = workers if workers > 0 else "CPU count"
        stdscr.addstr(
            0,
            0,
            f"Running BOTH CPU & RAM:\n"
            f"  - CPU for {duration}s (workers={worker_msg})\n"
            f"  - RAM (~{mb_estimate:.2f} MB) for {duration}s ...",
        )
        stdscr.refresh()

        if workers <= 0:
            workers = None
        do_benchmark(
            cpu=True, ram=True, duration=duration, list_size=list_size, workers=workers
        )

        stdscr.addstr(4, 0, "BOTH Benchmark finished! Press any key to continue...")
        stdscr.getch()


# ------------------------------------------------------------------------------
# Typer Callback for No Subcommand => Launch curses TUI
# ------------------------------------------------------------------------------


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    If no subcommand is provided, launch the curses-based TUI.
    Otherwise, proceed with the chosen CLI command.
    """
    if ctx.invoked_subcommand is None:
        # Equivalent to calling "benchmarker.py tui"
        ctx.invoke(tui)


# ------------------------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(app(prog_name="benchmarker"))
