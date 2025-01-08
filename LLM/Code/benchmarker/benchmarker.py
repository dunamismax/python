#!/usr/bin/env python3
"""
benchmarker.py - An Interactive Typer CLI CPU and RAM benchmarker

Requirements:
    - Python 3.8+
    - typer (pip install typer)

Usage:
    # Method 1: Interactive Menu
    python benchmarker.py

    # Method 2: Direct Commands
    python benchmarker.py cpu
    python benchmarker.py ram --list-size 5000000
    python benchmarker.py both

Description:
    This application allows you to run:
      1) CPU Benchmark
      2) RAM Benchmark
      3) Both CPU & RAM

It runs benchmarks by:
    - Spinning up multiple CPU workers to keep CPU usage high for ~10 seconds.
    - Allocating and holding a large list of random data in memory for ~10 seconds (RAM test).

Press Ctrl+C to exit at any time.
"""

import sys
import math
import time
import random
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor

import typer

app = typer.Typer(help="A CPU and RAM benchmarking CLI using Typer.")


# ------------------------------------------------------------------------------
# Benchmark Logic
# ------------------------------------------------------------------------------


def cpu_stress_test(duration: float = 10.0, workers: int = None) -> None:
    """
    Keep CPU cores busy for 'duration' seconds by repeatedly performing math
    operations in multiple threads.

    :param duration: How many seconds to keep the CPU busy.
    :param workers:  Number of worker threads; defaults to the CPU count.
    """
    if workers is None:
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
        # Wait for all threads to finish and propagate any exceptions
        for t in tasks:
            t.result()


def ram_stress_test(duration: float = 10.0, list_size: int = 10_000_000) -> None:
    """
    Allocate a large list of random integers to consume RAM for 'duration' seconds.

    :param duration: How many seconds to hold allocated memory.
    :param list_size: Size of the allocated list (each element ~some bytes).
    """
    # Allocate
    big_list = [random.randint(0, 100) for _ in range(list_size)]

    # Hold for the specified duration
    time.sleep(duration)

    # Deallocate by letting big_list go out of scope


def do_benchmark(
    cpu: bool, ram: bool, duration: float = 10.0, list_size: int = 10_000_000
) -> None:
    """
    Execute CPU and/or RAM benchmarks, possibly in parallel.

    :param cpu:       Whether to run the CPU benchmark.
    :param ram:       Whether to run the RAM benchmark.
    :param duration:  Duration for each benchmark (CPU/RAM).
    :param list_size: Size of RAM list if RAM is tested.
    """
    threads = []

    if cpu:
        cpu_thread = threading.Thread(
            target=cpu_stress_test, kwargs={"duration": duration}
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
# Typer Commands
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
    typer.echo(f"Starting CPU benchmark for {duration} seconds...")
    cpu_stress_test(duration=duration, workers=workers)
    typer.echo("CPU benchmark finished!")


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
    mb_estimate = list_size * (
        24 / 1_000_000
    )  # rough estimate; each int can be ~24 bytes in CPython
    typer.echo(
        f"Starting RAM benchmark. Allocating ~{mb_estimate:.2f} MB for {duration} seconds..."
    )
    ram_stress_test(duration=duration, list_size=list_size)
    typer.echo("RAM benchmark finished!")


@app.command()
def both(
    duration: float = typer.Option(
        10.0, help="Number of seconds to stress CPU and hold allocated memory."
    ),
    list_size: int = typer.Option(
        10_000_000, help="Number of elements to allocate in a list."
    ),
):
    """
    Run both CPU and RAM benchmarks in parallel for the specified duration.
    """
    mb_estimate = list_size * (24 / 1_000_000)  # rough estimate
    typer.echo(f"Starting BOTH CPU & RAM benchmark...")
    typer.echo(f"  • CPU for {duration} seconds")
    typer.echo(f"  • RAM (~{mb_estimate:.2f} MB) for {duration} seconds")
    do_benchmark(cpu=True, ram=True, duration=duration, list_size=list_size)
    typer.echo("CPU & RAM benchmark finished!")


# ------------------------------------------------------------------------------
# Interactive Menu
# ------------------------------------------------------------------------------


def interactive_menu():
    """
    Presents the user with a simple text-based menu to select which benchmark to run.
    """
    typer.echo("Welcome to Benchmarker! Please select an option:")
    typer.echo("  1) CPU Benchmark")
    typer.echo("  2) RAM Benchmark")
    typer.echo("  3) Both CPU & RAM")
    typer.echo("  Q) Quit")

    choice = typer.prompt("Enter your choice")

    if choice.strip().lower() == "q":
        typer.echo("Exiting...")
        raise typer.Exit()

    if choice not in ("1", "2", "3"):
        typer.echo("Invalid choice. Please try again.")
        return interactive_menu()

    # Prompt for optional duration
    duration = typer.prompt("Enter benchmark duration in seconds", default="10.0")
    try:
        duration = float(duration)
    except ValueError:
        typer.echo("Invalid duration. Using default: 10.0.")
        duration = 10.0

    # If user selects RAM or both, optionally ask for list size
    list_size = 10_000_000
    if choice in ("2", "3"):
        try:
            list_size_input = typer.prompt(
                "Enter list size for RAM test", default="10000000"
            )
            list_size = int(list_size_input)
        except ValueError:
            typer.echo("Invalid list size. Using default: 10000000.")
            list_size = 10_000_000

    # Run the chosen benchmark
    if choice == "1":
        typer.echo(f"Running CPU benchmark for {duration} seconds...")
        do_benchmark(cpu=True, ram=False, duration=duration)
    elif choice == "2":
        typer.echo(
            f"Running RAM benchmark (list_size={list_size}) for {duration} seconds..."
        )
        do_benchmark(cpu=False, ram=True, duration=duration, list_size=list_size)
    else:  # '3'
        typer.echo(
            f"Running BOTH CPU & RAM for {duration} seconds, list_size={list_size}..."
        )
        do_benchmark(cpu=True, ram=True, duration=duration, list_size=list_size)

    typer.echo("Benchmark complete!")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    If no subcommand is provided, this function will show an interactive menu.
    """
    if ctx.invoked_subcommand is None:
        try:
            interactive_menu()
        except KeyboardInterrupt:
            typer.echo("\nInterrupted by user. Exiting...")
            raise typer.Exit()


# ------------------------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    # If desired, exit code from app can be used or simply called directly
    sys.exit(app(prog_name="benchmarker"))
