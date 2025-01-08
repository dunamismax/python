#!/usr/bin/env python3
"""
py-top: An interactive CLI app using Typer that runs a Textual-based TUI
for displaying real-time CPU, memory, and process usage.

Usage:
  python py-top.py

Press 'q' or 'Ctrl+C' to exit the TUI.
"""

import curses
import time
import psutil
import typer
from typing import Any, List

app = typer.Typer(help="A Typer-based CLI for an interactive curses TUI.")


def draw_usage_bar(
    stdscr: "curses._CursesWindow",
    start_y: int,
    label: str,
    usage_percent: float,
    width: int,
    color_pair: int,
) -> None:
    """
    Draw a labeled bar to indicate a usage percentage (e.g., CPU or memory).

    :param stdscr: The curses screen.
    :param start_y: The Y-coordinate to start drawing.
    :param label: The label to print before the usage bar (e.g., "CPU", "MEM").
    :param usage_percent: The usage percentage to visualize (0-100).
    :param width: The total width for the bar.
    :param color_pair: A curses color pair to use for the filled portion.
    """
    # Clamp usage to [0, 100]
    usage = max(0.0, min(usage_percent, 100.0))
    # Format label
    label_str = f"{label}: {usage:.1f}%"
    stdscr.addstr(start_y, 0, label_str)

    # Calculate bar fill
    bar_fill = int((usage / 100.0) * width)
    bar_str = "[" + "#" * bar_fill + "-" * (width - bar_fill) + "]"
    # Color only the "#" region if colors are available
    if curses.has_colors():
        # Print the opening bracket
        stdscr.addstr(start_y, len(label_str) + 1, "[", curses.color_pair(0))
        # Print the filled portion
        stdscr.addstr(
            start_y, len(label_str) + 2, "#" * bar_fill, curses.color_pair(color_pair)
        )
        # Print the unfilled portion
        stdscr.addstr(
            start_y,
            len(label_str) + 2 + bar_fill,
            "-" * (width - bar_fill),
            curses.color_pair(0),
        )
        # Print the closing bracket
        stdscr.addstr(start_y, len(label_str) + 2 + width, "]", curses.color_pair(0))
    else:
        stdscr.addstr(start_y, len(label_str) + 1, bar_str)


def draw_process_list(
    process_pad: "curses._CursesWindow",
    procs: List[Any],
    max_y: int,
    max_x: int,
    highlight_line: int,
    pad_y_offset: int,
) -> None:
    """
    Render the process list inside a pad, which allows scrolling.

    :param process_pad: The curses pad to draw the process table.
    :param procs: A list of processes (dicts) sorted by CPU usage.
    :param max_y: The maximum visible height for the process area.
    :param max_x: The maximum visible width for the process area.
    :param highlight_line: The current highlight line offset (for scrolling).
    :param pad_y_offset: The vertical offset into the pad (topmost visible row).
    """
    # Clear the pad before drawing
    process_pad.erase()

    # Table header
    header = f"{'PID':<8}{'USER':<16}{'NAME':<25}{'CPU%':>8}{'MEM%':>8}"
    process_pad.addstr(0, 0, header, curses.A_BOLD)

    for i, proc in enumerate(procs, start=1):
        # Truncate or fill columns
        pid_str = f"{proc['pid']:<8}"
        user_str = f"{(proc['username'] or '-')[:15]:<16}"
        name_str = f"{(proc['name'] or '-')[:25]:<25}"
        cpu_str = f"{proc['cpu_percent']:.1f}".rjust(8)
        mem_str = f"{proc['memory_percent']:.1f}".rjust(8)

        line_str = f"{pid_str}{user_str}{name_str}{cpu_str}{mem_str}"

        process_pad.addstr(i, 0, line_str)

    # Refresh the pad to the screen in a scrollable manner
    # +1 because we used row 0 for the header.
    total_rows = len(procs) + 1
    process_pad.noutrefresh(
        pad_y_offset,
        0,
        highlight_line,
        0,
        max_y - 1,
        max_x - 1,
    )


def gather_processes() -> List[dict]:
    """
    Gather processes, sorted by CPU usage descending.

    :return: A list of process info dictionaries.
    """
    processes = []
    for proc in psutil.process_iter(
        ["pid", "name", "username", "cpu_percent", "memory_percent"]
    ):
        try:
            processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    processes.sort(key=lambda x: x["cpu_percent"], reverse=True)
    return processes


def curses_app(stdscr: "curses._CursesWindow", refresh_interval: float) -> None:
    """
    Main curses application loop.

    :param stdscr: The main curses window.
    :param refresh_interval: Seconds between data refreshes.
    """
    # Curses setup
    curses.curs_set(0)
    stdscr.nodelay(True)  # Non-blocking input
    stdscr.timeout(0)  # getch() returns immediately
    curses.noecho()
    curses.cbreak()

    # Optional color setup
    if curses.has_colors():
        curses.start_color()
        # We can define multiple color pairs if desired
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_RED)
        # Pair 0 is default (foreground, background)

    # Create a pad for the process list, which might be tall
    # Enough rows to potentially accommodate many processes
    max_process_rows = 10_000  # Arbitrary large number
    max_process_cols = curses.COLS
    process_pad = curses.newpad(max_process_rows, max_process_cols)

    pad_y_offset = 0  # Tracks the top row displayed in the pad
    highlight_line = 4  # Where we want to place the pad (below CPU/MEM usage lines)

    # Main loop
    try:
        while True:
            stdscr.erase()
            height, width = stdscr.getmaxyx()

            # Gather stats
            cpu_percent = psutil.cpu_percent(interval=None)
            mem_info = psutil.virtual_memory()
            processes = gather_processes()

            # Draw CPU & MEM usage bars
            draw_usage_bar(stdscr, 0, "CPU", cpu_percent, width // 4, 1)
            draw_usage_bar(stdscr, 1, "MEM", mem_info.percent, width // 4, 2)

            # Draw instructions
            instr = "[q] Quit | Up/Down arrows: Scroll processes"
            stdscr.addstr(2, 0, instr, curses.A_DIM)

            # Draw process list in a pad
            draw_process_list(
                process_pad=process_pad,
                procs=processes,
                max_y=height - highlight_line,
                max_x=width,
                highlight_line=highlight_line,
                pad_y_offset=pad_y_offset,
            )

            # Handle user input
            key = stdscr.getch()
            if key == ord("q") or key == ord("Q"):
                break
            elif key == curses.KEY_DOWN:
                # Scroll down (move the pad start row down)
                pad_y_offset = min(pad_y_offset + 1, len(processes))
            elif key == curses.KEY_UP:
                # Scroll up
                pad_y_offset = max(pad_y_offset - 1, 0)
            elif key == curses.ERR:
                # No key pressed
                pass

            # Update the screen
            curses.doupdate()

            # Sleep for refresh_interval seconds
            # We can use time.sleep or curses.napms
            # Using time.sleep is simpler for Pythonic code
            time.sleep(refresh_interval)

    except KeyboardInterrupt:
        # Graceful exit on Ctrl+C
        pass
    finally:
        # Restore terminal settings
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()


@app.command()
def run_tui(
    refresh_interval: float = typer.Option(1.0, help="Seconds between screen updates."),
):
    """
    Start the curses-based TUI for real-time system monitoring.
    Press 'q' or Ctrl+C to exit.
    """
    curses.wrapper(curses_app, refresh_interval)


if __name__ == "__main__":
    app()
