"""
reminders.py

A simple Textual-based TUI app for managing reminders and tasks.

Features:
- List tasks in a table (Title, Due Date, Priority, Status).
- Add a new task with optional due date and priority.
- Mark tasks as 'Done'.
- Remove tasks completely.

Usage:
    python reminders.py
"""

from __future__ import annotations

import datetime
from typing import Optional, List

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Grid
from textual.widget import Widget
from textual.widgets import (
    Header,
    Footer,
    Static,
    Input,
    Button,
    DataTable,
    Label,
    TextLog,
)
from textual.reactive import reactive


class Task:
    """Model representing a single task in the reminders app."""

    def __init__(
        self, title: str, due_date: Optional[str] = None, priority: Optional[str] = None
    ) -> None:
        self.title = title
        self.due_date = due_date if due_date else "None"
        self.priority = priority if priority else "Normal"
        self.done = False
        self.created_at = datetime.datetime.now()

    def mark_done(self) -> None:
        """Mark the task as completed."""
        self.done = True

    def to_row(self) -> list[str]:
        """Return a list representation suitable for DataTable display."""
        status = "Done" if self.done else "Pending"
        return [self.title, self.due_date, self.priority, status]


class TaskList(Widget):
    """
    A widget that holds and displays tasks in a DataTable.
    Provides methods to add, remove, and update tasks.
    """

    tasks: reactive[List[Task]] = reactive([])

    def compose(self) -> ComposeResult:
        yield DataTable(id="task_table")

    def on_mount(self) -> None:
        """Initialize the DataTable columns and load existing tasks."""
        table = self.query_one("#task_table", DataTable)
        table.show_header = True
        table.show_cursor = True
        table.cursor_type = "row"
        table.zebra_stripes = True

        # Define our columns
        table.add_columns("Title", "Due", "Priority", "Status")

    def watch_tasks(self, old_value: List[Task], new_value: List[Task]) -> None:
        """Refresh the table when tasks change."""
        table = self.query_one("#task_table", DataTable)
        table.clear()
        for task in new_value:
            table.add_row(*task.to_row())

    def add_task(self, task: Task) -> None:
        """Add a new task to the list."""
        self.tasks.append(task)

    def remove_task(self, index: int) -> None:
        """Remove a task by its index."""
        if 0 <= index < len(self.tasks):
            del self.tasks[index]
            self.refresh()

    def mark_done(self, index: int) -> None:
        """Mark a specific task as done."""
        if 0 <= index < len(self.tasks):
            self.tasks[index].mark_done()
            self.refresh()

    def refresh(self) -> None:
        """Trigger the table to refresh its contents."""
        self.tasks = self.tasks[:]  # reassigning to trigger the reactive watch


class AddTaskForm(Widget):
    """
    A form for creating a new task.
    Emits a 'submit' message with the title, due_date, and priority.
    """

    def compose(self) -> ComposeResult:
        yield Label("Task Title:")
        yield Input(placeholder="Enter task title...", id="task_title_input")
        yield Label("Due Date (optional):")
        yield Input(placeholder="YYYY-MM-DD or leave blank", id="due_date_input")
        yield Label("Priority (optional):")
        yield Input(placeholder="e.g., High, Medium, Low", id="priority_input")
        yield Button(label="Add Task", id="add_task_btn")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle the Add Task button press."""
        if event.button.id == "add_task_btn":
            title_input = self.query_one("#task_title_input", Input).value.strip()
            due_date_input = self.query_one("#due_date_input", Input).value.strip()
            priority_input = self.query_one("#priority_input", Input).value.strip()

            # Reset form fields
            self.query_one("#task_title_input", Input).value = ""
            self.query_one("#due_date_input", Input).value = ""
            self.query_one("#priority_input", Input).value = ""

            # Emit a custom event message with form data
            if title_input:
                await self.emit(
                    self.Submit(
                        self,
                        title_input,
                        due_date_input or None,
                        priority_input or None,
                    )
                )

    class Submit(Message):
        """A custom message signifying form submission."""

        def __init__(
            self,
            sender: AddTaskForm,
            title: str,
            due_date: Optional[str],
            priority: Optional[str],
        ):
            super().__init__()
            self.sender = sender
            self.title = title
            self.due_date = due_date
            self.priority = priority


class RemindersApp(App):
    """Main application for managing reminders and tasks using Textual."""

    CSS_PATH = None  # Optionally specify a CSS file here if desired.

    BINDINGS = [
        ("q", "quit", "Quit Reminders App"),
        ("a", "add_task_mode", "Switch to Add Task Mode"),
        ("l", "list_mode", "Switch to Task List Mode"),
        ("d", "mark_done", "Mark Selected Task as Done"),
        ("r", "remove_task", "Remove Selected Task"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Header()
        yield Footer()

        with Horizontal():
            with Vertical():
                yield Static("[b]Reminders & Tasks[/b]", id="app_title", classes="bold")
                # Main content area with a DataTable of tasks
                yield TaskList(id="task_list")

            # A side panel for adding new tasks
            with Vertical(id="sidebar"):
                yield AddTaskForm(id="add_task_form")

    def on_mount(self) -> None:
        """Perform setup tasks on application startup."""
        self.query_one("#add_task_form", AddTaskForm).visible = False
        self.set_focus(self.query_one("#task_list", TaskList).query_one("#task_table"))

    def on_add_task_form_submit(self, event: AddTaskForm.Submit) -> None:
        """Receive submitted data from the AddTaskForm and add the task."""
        new_task = Task(
            title=event.title, due_date=event.due_date, priority=event.priority
        )
        self.query_one("#task_list", TaskList).add_task(new_task)

    def action_add_task_mode(self) -> None:
        """Show the add task form and hide the task list table."""
        self.query_one("#task_list", TaskList).visible = False
        self.query_one("#add_task_form", AddTaskForm).visible = True
        self.set_focus(self.query_one("#add_task_form", AddTaskForm).query_one(Input))

    def action_list_mode(self) -> None:
        """Show the task list and hide the add task form."""
        self.query_one("#add_task_form", AddTaskForm).visible = False
        self.query_one("#task_list", TaskList).visible = True
        self.set_focus(self.query_one("#task_list", TaskList).query_one("#task_table"))

    def action_mark_done(self) -> None:
        """
        Mark the currently selected task as done.
        Only works in 'list_mode'.
        """
        task_list_widget = self.query_one("#task_list", TaskList)
        if task_list_widget.visible:
            table = task_list_widget.query_one("#task_table", DataTable)
            if table.cursor_row is not None:
                task_list_widget.mark_done(table.cursor_row)

    def action_remove_task(self) -> None:
        """
        Remove the currently selected task.
        Only works in 'list_mode'.
        """
        task_list_widget = self.query_one("#task_list", TaskList)
        if task_list_widget.visible:
            table = task_list_widget.query_one("#task_table", DataTable)
            if table.cursor_row is not None:
                task_list_widget.remove_task(table.cursor_row)

    def on_key(self, event: App.Key) -> None:
        """
        Capture additional key events to gracefully handle transitions
        and common usage patterns.
        """
        if event.key == "escape":
            # Switch back to list mode if in add-task mode
            if not self.query_one("#task_list", TaskList).visible:
                self.action_list_mode()


if __name__ == "__main__":
    RemindersApp().run()
