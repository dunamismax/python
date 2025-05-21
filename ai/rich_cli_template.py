#!/usr/bin/env python3
"""
Nord-themed Rich CLI Application Template
-------------------------------------------
A minimal but feature-rich CLI template using the Rich library with Nord theme.
Includes colored output, progress bars, tables, logging, interactive prompts,
and graceful error handling.
"""

import os
import sys
import time
import logging
from datetime import datetime
from enum import Enum
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


# -----------------------------------------------------------------------------
# Nord Color Theme Configuration using Enum
# -----------------------------------------------------------------------------
class NordColor(Enum):
    # Polar Night (dark / background)
    POLAR_NIGHT_0 = "#2E3440"  # Dark background
    POLAR_NIGHT_1 = "#3B4252"  # Lighter background
    POLAR_NIGHT_2 = "#434C5E"  # Selection background
    POLAR_NIGHT_3 = "#4C566A"  # Inactive text

    # Snow Storm (light / text)
    SNOW_STORM_4 = "#D8DEE9"  # Text
    SNOW_STORM_5 = "#E5E9F0"  # Light text
    SNOW_STORM_6 = "#ECEFF4"  # Bright text

    # Frost (cool accents)
    FROST_7 = "#8FBCBB"  # Mint
    FROST_8 = "#88C0D0"  # Light blue
    FROST_9 = "#81A1C1"  # Medium blue
    FROST_10 = "#5E81AC"  # Dark blue

    # Aurora (warm accents)
    AURORA_11 = "#BF616A"  # Red
    AURORA_12 = "#D08770"  # Orange
    AURORA_13 = "#EBCB8B"  # Yellow
    AURORA_14 = "#A3BE8C"  # Green
    AURORA_15 = "#B48EAD"  # Purple


# Build the Rich theme using the NordColor enum values.
NORD_THEME = Theme(
    {
        "info": NordColor.FROST_8.value,
        "warning": NordColor.AURORA_13.value,
        "error": f"bold {NordColor.AURORA_11.value}",
        "success": NordColor.AURORA_14.value,
        "header": f"bold {NordColor.FROST_9.value}",
        "prompt": NordColor.FROST_8.value,
        "input": NordColor.SNOW_STORM_4.value,
        "spinner": NordColor.FROST_7.value,
        "progress.data": NordColor.FROST_8.value,
        "progress.percentage": NordColor.FROST_9.value,
        "progress.bar": NordColor.FROST_10.value,
        "table.header": f"bold {NordColor.FROST_9.value}",
        "table.cell": NordColor.SNOW_STORM_4.value,
        "panel.border": NordColor.FROST_9.value,
    }
)


# -----------------------------------------------------------------------------
# Nord CLI Application Class
# -----------------------------------------------------------------------------
class NordCLIApp:
    """
    Nord-themed CLI application with Rich formatting.

    Provides colored output, progress bars, tables, interactive prompts,
    and robust logging.
    """

    def __init__(self) -> None:
        # Initialize the Rich console with the Nord theme.
        self.console = Console(theme=NORD_THEME)
        # Setup logging (single log file with rotation).
        self.setup_logging()
        self.logger = logging.getLogger("nord_cli_app")

    def setup_logging(self) -> None:
        """Configure logging with a rotating file handler and a Rich console handler."""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "app.log")

        # Configure the root logger.
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                RotatingFileHandler(
                    log_file,
                    maxBytes=2 * 1024 * 1024,  # 2MB
                    backupCount=3,
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
        """Print a styled header panel with Nord colors."""
        self.console.print()  # Blank line
        self.console.print(
            Panel(title, style="header", border_style="panel.border", expand=False)
        )
        self.console.print()  # Blank line

    def show_progress(self, tasks: List[str]) -> None:
        """Demonstrate a progress bar for multiple tasks using Nord colors."""
        with Progress(
            SpinnerColumn(style="spinner"),
            TextColumn("[progress.data]{task.description}"),
            BarColumn(complete_style="progress.bar"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console,
        ) as progress:
            for description in tasks:
                task_id = progress.add_task(description, total=100)
                # Simulate work in small increments.
                for _ in range(10):
                    time.sleep(0.1)
                    progress.advance(task_id, 10)

    def display_table(self, data: List[Dict]) -> None:
        """
        Display tabular data with Nord styling.

        Args:
            data (List[Dict]): List of dictionaries containing table data.
        """
        table = Table(
            show_header=True,
            header_style="table.header",
            border_style="panel.border",
            row_styles=["table.cell"],
        )

        if data:
            # Create table columns based on keys from the first data item.
            for key in data[0].keys():
                table.add_column(key.capitalize())

            # Populate table rows.
            for item in data:
                table.add_row(*[str(v) for v in item.values()])

            self.console.print(table)
        else:
            self.console.print("No data available to display.", style="warning")

    def get_user_input(
        self, prompt_text: str, choices: Optional[List[str]] = None
    ) -> str:
        """
        Prompt the user for input with validation and Nord-themed styling.

        Args:
            prompt_text (str): The text to display in the prompt.
            choices (Optional[List[str]]): Optional list of valid choices.

        Returns:
            str: The user's input.
        """
        try:
            if choices:
                return Prompt.ask(
                    prompt_text, choices=choices, console=self.console, style="prompt"
                )
            return Prompt.ask(prompt_text, console=self.console, style="prompt")
        except KeyboardInterrupt:
            self.handle_exit()

    def handle_exit(self) -> None:
        """Handle application exit gracefully using Nord-themed prompts."""
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

            # Demonstrate progress tracking.
            self.show_progress(
                [
                    "Initializing Nord environment...",
                    "Loading application data...",
                    "Completing setup process...",
                ]
            )

            # Display a sample table.
            sample_data = [
                {"name": "Nordic Task 1", "value": 100, "status": "Active"},
                {"name": "Nordic Task 2", "value": 200, "status": "Inactive"},
            ]
            self.display_table(sample_data)

            # Prompt for user input.
            choice = self.get_user_input(
                "Select an option", choices=["1", "2", "3", "q"]
            )
            if choice == "q":
                self.handle_exit()

            # Render example markdown.
            md_content = """
# Welcome to Nord CLI Template

This template features:
- Nord color scheme throughout
- Rich console output
- Progress bars and tables
- Interactive prompts and logging
- Graceful error handling
"""
            self.console.print(Markdown(md_content))
        except KeyboardInterrupt:
            self.handle_exit()
        except Exception as e:
            self.logger.exception("An error occurred")
            self.console.print(f"Error: {str(e)}", style="error")
            sys.exit(1)


def main() -> None:
    """Application entry point."""
    app = NordCLIApp()
    app.run()


if __name__ == "__main__":
    main()
