#!/usr/bin/env python3
"""
reminders.py

A Typer + curses-based CLI/TUI app for managing reminders and tasks.

Features:
- Classic CLI commands (list_all, add, done, remove, search) using Typer + Rich for output.
- A curses TUI with arrow-key navigation:
  - View tasks
  - Mark tasks as done
  - Remove tasks
  - Add new tasks
  - Search tasks by title substring
  - Quit with 'q' or 'Q'

Usage:
    python reminders.py  # launches TUI by default
    python reminders.py tui  # explicitly launch TUI
    python reminders.py --help  # show help
"""

from __future__ import annotations

import datetime
import curses
import time
import sys
from typing import Optional, List

import typer
from rich.console import Console
from rich.table import Table

# --------------------------------------------------------------------------
# GLOBALS & INITIALIZATIONS
# --------------------------------------------------------------------------

app = typer.Typer(help="A CLI/TUI application for managing reminders and tasks.")
console = Console()

# For simplicity, all tasks are stored in-memory in this list.
tasks: List["Task"] = []


# --------------------------------------------------------------------------
# MODELS
# --------------------------------------------------------------------------


class Task:
    """
    Model representing a single task in the reminders app.

    Attributes:
        title (str): A short descriptive title for the task.
        due_date (str): Optional due date in 'YYYY-MM-DD' format.
        priority (str): Priority string, defaults to 'Normal' if not provided.
        done (bool): Indicates whether the task has been completed.
        created_at (datetime.datetime): Timestamp for when the task was created.
    """

    def __init__(
        self,
        title: str,
        due_date: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> None:
        self.title = title
        self.due_date = due_date if due_date else "None"
        self.priority = priority if priority else "Normal"
        self.done = False
        self.created_at = datetime.datetime.now()

    def mark_done(self) -> None:
        """Mark this task as completed."""
        self.done = True

    def to_row(self, index: int) -> List[str]:
        """
        Return a list (row) representation suitable for display in a Rich Table.

        Args:
            index (int): The index of this task in the global 'tasks' list.

        Returns:
            A list of strings representing each column in a table row.
        """
        status = "Done" if self.done else "Pending"
        return [str(index), self.title, self.due_date, self.priority, status]


# --------------------------------------------------------------------------
# HELPER FUNCTIONS (CLI)
# --------------------------------------------------------------------------


def _print_tasks_table(filter_keyword: Optional[str] = None) -> None:
    """
    Print tasks in a formatted table using Rich.
    If `filter_keyword` is provided, only tasks whose title contains that keyword are displayed.

    Args:
        filter_keyword (str): Optional substring to filter tasks by title.
    """
    filtered_tasks = tasks
    if filter_keyword:
        filter_keyword_lower = filter_keyword.lower()
        filtered_tasks = [t for t in tasks if filter_keyword_lower in t.title.lower()]

    if not filtered_tasks:
        if filter_keyword:
            console.print(
                f"[bold magenta]No tasks found containing '{filter_keyword}'[/bold magenta]"
            )
        else:
            console.print("[bold magenta]No tasks found![/bold magenta]")
        return

    table = Table(title="Your Tasks", show_lines=True)
    table.add_column("Index", justify="right", style="cyan", no_wrap=True)
    table.add_column("Title", style="bold")
    table.add_column("Due Date", style="bold magenta")
    table.add_column("Priority", style="bold yellow")
    table.add_column("Status", style="bold green")

    for idx, task in enumerate(filtered_tasks):
        # Display the original index from the main 'tasks' list.
        # We look up the task's index in the global list so subcommands (e.g., done/remove) remain accurate.
        original_idx = tasks.index(task)
        row_content = task.to_row(original_idx)
        table.add_row(*row_content)

    console.print(table)


def _validate_task_index(index: int) -> bool:
    """
    Check if the given index is valid for the current task list.

    Args:
        index (int): Index to validate.

    Returns:
        bool: True if the index is valid, False otherwise.
    """
    if index < 0 or index >= len(tasks):
        console.print(f"[red]Invalid task index: {index}[/red]")
        return False
    return True


# --------------------------------------------------------------------------
# CLI COMMANDS
# --------------------------------------------------------------------------


@app.command()
def list_all() -> None:
    """
    List all tasks in a nicely formatted table (CLI).
    """
    _print_tasks_table()


@app.command()
def add(
    title: str = typer.Argument(..., help="Title for the new task."),
    due_date: str = typer.Option(
        None, "--due", "-d", help="Optional due date in 'YYYY-MM-DD' format."
    ),
    priority: str = typer.Option(
        None, "--priority", "-p", help="Optional priority for the task."
    ),
) -> None:
    """
    Add a new task with an optional due date and priority (CLI).
    """
    new_task = Task(title=title, due_date=due_date, priority=priority)
    tasks.append(new_task)
    console.print(
        f"[green]Task added:[/green] '{title}' with due date '{new_task.due_date}' "
        f"and priority '{new_task.priority}'."
    )


@app.command()
def done(index: int = typer.Argument(..., help="Index of the task to mark as done.")):
    """
    Mark a task as done by its index in the task list (CLI).
    """
    if not _validate_task_index(index):
        raise typer.Exit(code=1)
    tasks[index].mark_done()
    console.print(f"[green]Marked task {index} as done.[/green]")


@app.command()
def remove(index: int = typer.Argument(..., help="Index of the task to remove.")):
    """
    Remove a task from the list by its index (CLI).
    """
    if not _validate_task_index(index):
        raise typer.Exit(code=1)
    removed_task = tasks.pop(index)
    console.print(f"[red]Removed task '{removed_task.title}'[/red]")


@app.command()
def search(
    keyword: str = typer.Argument(..., help="Keyword to search in task titles.")
):
    """
    Search for tasks that contain the given keyword in their title (CLI).
    """
    console.print(f"[blue]Searching for tasks containing:[/blue] '{keyword}'")
    _print_tasks_table(filter_keyword=keyword)


# --------------------------------------------------------------------------
# TUI FUNCTIONS (curses)
# --------------------------------------------------------------------------


def _draw_header(stdscr) -> None:
    """
    Draw a simple header at the top of the screen.
    """
    stdscr.attron(curses.A_BOLD)
    stdscr.addstr(
        0,
        2,
        "Reminders TUI - Use ↑/↓ to navigate, 'n' to add, 'd' to mark done, "
        "'r' to remove, 's' to search, 'q' to quit",
    )
    stdscr.attroff(curses.A_BOLD)


def _draw_tasks_curses(stdscr, highlight_idx: int) -> None:
    """
    Draw the list of tasks in a curses window with the given highlighted index.
    Color-code tasks based on their status (done vs pending).
    """
    h, w = stdscr.getmaxyx()
    start_y = 2

    if not tasks:
        no_tasks_msg = "-- No tasks found --"
        stdscr.addstr(start_y, (w - len(no_tasks_msg)) // 2, no_tasks_msg)
        return

    for idx, task in enumerate(tasks):
        y_pos = start_y + idx
        if y_pos >= h - 1:
            break  # avoid drawing beyond the window's height

        row_str = (
            f"[{idx}] {task.title} | (Due: {task.due_date}) "
            f"[{task.priority}] -> {'Done' if task.done else 'Pending'}"
        )

        # Define a color pair based on the status
        color_pair = 2 if task.done else 1

        # Highlight if selected
        if idx == highlight_idx:
            stdscr.attron(curses.A_REVERSE)

        stdscr.addstr(y_pos, 2, row_str[: w - 4], curses.color_pair(color_pair))

        if idx == highlight_idx:
            stdscr.attroff(curses.A_REVERSE)


def _prompt_user_input(stdscr, prompt: str) -> str:
    """
    Prompt the user for a string input within the curses interface.

    Returns:
        str: The user's string or empty if canceled.
    """
    curses.echo()
    h, w = stdscr.getmaxyx()
    prompt_y = h - 1  # We'll prompt at the bottom
    stdscr.addstr(prompt_y, 0, " " * (w - 1))  # Clear the prompt line
    stdscr.addstr(prompt_y, 0, prompt)
    stdscr.refresh()

    user_input_bytes = stdscr.getstr(prompt_y, len(prompt), w - len(prompt) - 1)
    user_input = user_input_bytes.decode("utf-8").strip()
    curses.noecho()
    return user_input


def _mark_done(highlight_idx: int) -> None:
    """
    Mark the task at highlight_idx as done, if valid.
    """
    if 0 <= highlight_idx < len(tasks):
        tasks[highlight_idx].mark_done()


def _remove_task(highlight_idx: int) -> None:
    """
    Remove the task at highlight_idx, if valid.
    """
    if 0 <= highlight_idx < len(tasks):
        tasks.pop(highlight_idx)


def _search_tasks(stdscr) -> Optional[int]:
    """
    Prompt the user for a search term and return the index of the first matching
    task if found, otherwise None.
    """
    term = _prompt_user_input(stdscr, "Search term: ")
    if not term:
        return None

    # Return the index of the first match
    for idx, t in enumerate(tasks):
        if term.lower() in t.title.lower():
            return idx
    return None


def _tui_main(stdscr):
    """
    The main curses TUI loop. Manages keypresses and updates the screen.
    """
    curses.curs_set(False)  # Hide the cursor
    stdscr.nodelay(False)  # Make getch() block
    curses.start_color()  # Initialize color if possible

    # Define color pairs if the terminal supports color
    if curses.has_colors():
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)  # pending tasks
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)  # done tasks
    else:
        # Fallback if no color support
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)

    highlight_idx = 0

    while True:
        stdscr.clear()
        _draw_header(stdscr)
        _draw_tasks_curses(stdscr, highlight_idx)
        stdscr.refresh()

        key = stdscr.getch()

        if key == curses.KEY_UP:
            # Wrap around if at the top
            highlight_idx = (highlight_idx - 1) % len(tasks) if tasks else 0
        elif key == curses.KEY_DOWN:
            # Wrap around if at the bottom
            highlight_idx = (highlight_idx + 1) % len(tasks) if tasks else 0
        elif key in [ord("q"), ord("Q")]:
            # Quit the TUI
            break
        elif key == ord("n"):
            # Add a new task
            title = _prompt_user_input(stdscr, "Title for new task: ")
            if title:
                due_date = _prompt_user_input(
                    stdscr, "Due date (YYYY-MM-DD) or leave blank: "
                )
                priority = _prompt_user_input(stdscr, "Priority or leave blank: ")
                new_task = Task(title=title, due_date=due_date, priority=priority)
                tasks.append(new_task)
                highlight_idx = len(tasks) - 1  # Move highlight to the new task
        elif key == ord("d"):
            # Mark as done
            _mark_done(highlight_idx)
        elif key == ord("r"):
            # Remove task
            if tasks:
                _remove_task(highlight_idx)
                highlight_idx = min(highlight_idx, len(tasks) - 1)
        elif key == ord("s"):
            # Search tasks
            match_index = _search_tasks(stdscr)
            if match_index is not None:
                highlight_idx = match_index

        time.sleep(0.03)  # Slight delay to reduce CPU usage


@app.command()
def tui():
    """
    Launch the curses-based TUI for managing tasks interactively.
    """
    curses.wrapper(_tui_main)


# --------------------------------------------------------------------------
# ENTRY POINT
# --------------------------------------------------------------------------


def main():
    """
    If no arguments are passed, launch the TUI by default.
    Otherwise, parse and execute Typer CLI commands.
    """
    if len(sys.argv) == 1:
        # No arguments provided; launch the TUI.
        curses.wrapper(_tui_main)
    else:
        # Delegate to Typer commands.
        app()


if __name__ == "__main__":
    main()
