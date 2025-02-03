#!/usr/bin/env python3
"""
Nord-themed Rich CLI Application Template
---------------------------------------
A minimal but feature-rich CLI template using the Rich library with Nord theme.
Includes core features like colored output, progress bars, tables,
logging, and interactive prompts.
"""

import os
import sys
import time
import logging
from datetime import datetime
from typing import Optional, List, Dict
from logging.handlers import RotatingFileHandler

from rich.console import Console
from rich.theme import Theme
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.style import Style


# Nord Color Theme Configuration
class NordTheme:
    # Polar Night (dark / background)
    NORD0 = "#2E3440"  # Dark bg
    NORD1 = "#3B4252"  # Lighter bg
    NORD2 = "#434C5E"  # Selection bg
    NORD3 = "#4C566A"  # Inactive text

    # Snow Storm (light / text)
    NORD4 = "#D8DEE9"  # Text
    NORD5 = "#E5E9F0"  # Light text
    NORD6 = "#ECEFF4"  # Bright text

    # Frost (cool accents)
    NORD7 = "#8FBCBB"  # Mint
    NORD8 = "#88C0D0"  # Light blue
    NORD9 = "#81A1C1"  # Medium blue
    NORD10 = "#5E81AC"  # Dark blue

    # Aurora (warm accents)
    NORD11 = "#BF616A"  # Red
    NORD12 = "#D08770"  # Orange
    NORD13 = "#EBCB8B"  # Yellow
    NORD14 = "#A3BE8C"  # Green
    NORD15 = "#B48EAD"  # Purple


# Nord theme configuration for Rich
NORD_THEME = Theme(
    {
        "info": NordTheme.NORD8,
        "warning": NordTheme.NORD13,
        "error": f"bold {NordTheme.NORD11}",
        "success": NordTheme.NORD14,
        "header": f"bold {NordTheme.NORD9}",
        "prompt": NordTheme.NORD8,
        "input": NordTheme.NORD4,
        "spinner": NordTheme.NORD7,
        "progress.data": NordTheme.NORD8,
        "progress.percentage": NordTheme.NORD9,
        "progress.bar": NordTheme.NORD10,
        "table.header": f"bold {NordTheme.NORD9}",
        "table.cell": NordTheme.NORD4,
        "panel.border": NordTheme.NORD9,
    }
)


class NordCLIApp:
    """Nord-themed CLI application class with Rich formatting capabilities."""

    def __init__(self):
        # Initialize Rich console with Nord theme
        self.console = Console(theme=NORD_THEME)

        # Setup logging
        self.setup_logging()

        # Initialize logger
        self.logger = logging.getLogger("nord_cli_app")

    def setup_logging(self) -> None:
        """Configure logging with both file and console handlers."""
        os.makedirs("logs", exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                RotatingFileHandler(
                    f"logs/app_{datetime.now():%Y%m%d_%H%M%S}.log",
                    maxBytes=10 * 1024 * 1024,  # 10MB
                    backupCount=5,
                    encoding="utf-8",
                ),
                RichHandler(
                    console=self.console,
                    rich_tracebacks=True,
                    tracebacks_theme=NORD_THEME,
                ),
            ],
        )

    def print_header(self, title: str) -> None:
        """Print a styled header with a panel using Nord colors."""
        self.console.print()
        self.console.print(
            Panel(title, style="header", border_style="panel.border", expand=False)
        )
        self.console.print()

    def show_progress(self, tasks: List[str]) -> None:
        """Demonstrate a progress bar with multiple tasks using Nord colors."""
        with Progress(
            SpinnerColumn(style="spinner"),
            TextColumn("[progress.data]{task.description}"),
            BarColumn(complete_style="progress.bar"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console,
        ) as progress:
            for task in tasks:
                with progress.enter_task(task) as task_id:
                    # Simulate some work
                    time.sleep(1)
                    progress.advance(task_id)

    def display_table(self, data: List[Dict]) -> None:
        """Display data in a Nord-themed formatted table."""
        table = Table(
            show_header=True,
            header_style="table.header",
            border_style="panel.border",
            row_styles=["table.cell"],
        )

        if data:
            # Add columns
            for key in data[0].keys():
                table.add_column(key.capitalize())

            # Add rows
            for item in data:
                table.add_row(*[str(v) for v in item.values()])

            self.console.print(table)

    def get_user_input(
        self, prompt_text: str, choices: Optional[List[str]] = None
    ) -> str:
        """Get validated user input with Nord-themed styling."""
        try:
            style = Style.parse("prompt")
            if choices:
                return Prompt.ask(
                    prompt_text, choices=choices, console=self.console, style=style
                )
            return Prompt.ask(prompt_text, console=self.console, style=style)
        except KeyboardInterrupt:
            self.handle_exit()

    def handle_exit(self) -> None:
        """Handle application exit gracefully with Nord-themed prompts."""
        self.console.print("\nExiting application...", style="warning")
        if Confirm.ask(
            "Are you sure you want to exit?", console=self.console, style="prompt"
        ):
            self.logger.info("Application closed by user")
            self.console.print("\nGoodbye! Thanks for using Nord CLI.", style="success")
            sys.exit(0)

    def run(self) -> None:
        """Main application loop with Nord-themed components."""
        try:
            self.print_header("Nord CLI Application Template")
            self.logger.info("Application started")

            # Example progress tracking
            self.show_progress(
                [
                    "Initializing Nord environment...",
                    "Loading application data...",
                    "Completing setup process...",
                ]
            )

            # Example table display
            sample_data = [
                {"name": "Nordic Task 1", "value": 100, "status": "Active"},
                {"name": "Nordic Task 2", "value": 200, "status": "Inactive"},
            ]
            self.display_table(sample_data)

            # Example user interaction
            choice = self.get_user_input(
                "Select an option", choices=["1", "2", "3", "q"]
            )

            if choice == "q":
                self.handle_exit()

            # Example markdown rendering with Nord styling
            md_content = """
            # Welcome to Nord CLI Template

            This template features:
            - Nord color scheme throughout
            - Rich console output
            - Progress bars
            - Tables
            - User input handling
            - Logging
            - Error handling
            """
            self.console.print(Markdown(md_content))

        except KeyboardInterrupt:
            self.handle_exit()
        except Exception as e:
            self.logger.exception("An error occurred")
            self.console.print(f"Error: {str(e)}", style="error")
            sys.exit(1)


def main():
    """Application entry point."""
    app = NordCLIApp()
    app.run()


if __name__ == "__main__":
    main()
