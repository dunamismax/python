#!/usr/bin/env python3
"""
reminders.py

A simple Typer-based CLI app for managing reminders and tasks.

Features:
- List tasks in a table (Title, Due Date, Priority, Status).
- Add a new task with optional due date and priority.
- Mark tasks as 'Done'.
- Remove tasks completely.

Usage:
    python reminders.py --help
"""

from __future__ import annotations

import datetime
from typing import Optional, List

import typer
from rich.console import Console
from rich.table import Table

# ------------------------------------------------------------------------------
# GLOBALS & INITIALIZATIONS
# ------------------------------------------------------------------------------

app = typer.Typer(help="A CLI application for managing reminders and tasks.")
console = Console()

# In a real-world scenario, you might store tasks in a file or database.
# For simplicity, we keep tasks in memory as a global list here.
tasks: List["Task"] = []


# ------------------------------------------------------------------------------
# MODELS
# ------------------------------------------------------------------------------


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
        self, title: str, due_date: Optional[str] = None, priority: Optional[str] = None
    ) -> None:
        self.title = title
        self.due_date = due_date if due_date else "None"
        self.priority = priority if priority else "Normal"
        self.done = False
        self.created_at = datetime.datetime.now()

    def mark_done(self) -> None:
        """
        Mark the task as completed.
        """
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


# ------------------------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------------------------


def _print_tasks_table() -> None:
    """
    Print all tasks in a nicely formatted table using Rich.
    """
    if not tasks:
        console.print("[bold magenta]No tasks found![/bold magenta]")
        return

    table = Table(title="Your Tasks", show_lines=True)
    table.add_column("Index", justify="right", style="cyan", no_wrap=True)
    table.add_column("Title", style="bold")
    table.add_column("Due Date", style="bold magenta")
    table.add_column("Priority", style="bold yellow")
    table.add_column("Status", style="bold green")

    for idx, task in enumerate(tasks):
        table.add_row(*task.to_row(idx))

    console.print(table)


def _validate_task_index(index: int) -> bool:
    """
    Check if the given index is valid for the current task list.

    Args:
        index (int): Index to validate.

    Returns:
        True if the index is valid, False otherwise.
    """
    if index < 0 or index >= len(tasks):
        console.print(f"[red]Invalid task index: {index}[/red]")
        return False
    return True


# ------------------------------------------------------------------------------
# CLI COMMANDS
# ------------------------------------------------------------------------------


@app.command()
def list_all() -> None:
    """
    List all tasks in a nicely formatted table.
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
    Add a new task with an optional due date and priority.
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
    Mark a task as done by its index in the task list.
    """
    if not _validate_task_index(index):
        raise typer.Exit(code=1)
    tasks[index].mark_done()
    console.print(f"[green]Marked task {index} as done.[/green]")


@app.command()
def remove(index: int = typer.Argument(..., help="Index of the task to remove.")):
    """
    Remove a task from the list by its index.
    """
    if not _validate_task_index(index):
        raise typer.Exit(code=1)
    removed_task = tasks.pop(index)
    console.print(f"[red]Removed task '{removed_task.title}'[/red]")


@app.command()
def interactive():
    """
    Enter an interactive loop where you can list, add, mark done, or remove tasks
    by responding to prompts. This allows a more "guided" experience.
    """
    console.print("[bold green]Entering interactive mode[/bold green].")
    while True:
        console.print("\n[bold]Options:[/bold] list, add, done, remove, quit")
        choice = console.input(
            "[bold magenta]What would you like to do? [/bold magenta]"
        )

        if choice.lower() == "list":
            _print_tasks_table()

        elif choice.lower() == "add":
            # Prompt user for details
            title = console.input("[bold green]Enter task title: [/bold green]")
            if not title.strip():
                console.print("[red]Title cannot be empty.[/red]")
                continue
            due_date = console.input(
                "[bold green]Enter due date (optional): [/bold green]"
            )
            priority = console.input(
                "[bold green]Enter priority (optional): [/bold green]"
            )
            new_task = Task(title=title, due_date=due_date, priority=priority)
            tasks.append(new_task)
            console.print(f"[green]Task '{title}' added.[/green]")

        elif choice.lower() == "done":
            if not tasks:
                console.print("[red]No tasks to mark as done.[/red]")
                continue
            _print_tasks_table()
            index_str = console.input(
                "[bold green]Enter task index to mark done: [/bold green]"
            )
            if not index_str.isdigit():
                console.print("[red]Invalid index.[/red]")
                continue
            index = int(index_str)
            if _validate_task_index(index):
                tasks[index].mark_done()
                console.print(f"[green]Marked task {index} as done.[/green]")

        elif choice.lower() == "remove":
            if not tasks:
                console.print("[red]No tasks to remove.[/red]")
                continue
            _print_tasks_table()
            index_str = console.input(
                "[bold green]Enter task index to remove: [/bold green]"
            )
            if not index_str.isdigit():
                console.print("[red]Invalid index.[/red]")
                continue
            index = int(index_str)
            if _validate_task_index(index):
                removed_task = tasks.pop(index)
                console.print(f"[red]Removed task '{removed_task.title}'.[/red]")

        elif choice.lower() in {"quit", "exit"}:
            console.print(
                "[bold yellow]Exiting interactive mode. Goodbye![/bold yellow]"
            )
            break

        else:
            console.print(
                "[red]Invalid option. Please choose from list, add, done, remove, or quit.[/red]"
            )


# ------------------------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    app()
