#!/usr/bin/env python3
"""
Production-Quality Chat CLI Application with OpenAI API v1.0 Integration,
Rich CLI with Nord Color Palette, Markdown Logging, and Robust Error Handling.
"""

import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, List

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

# Import OpenAI client for v1.0 changes
try:
    from openai import OpenAI
except ImportError:
    print("Error: openai package not installed. Please install it with 'pip install openai'")
    sys.exit(1)

from pydantic import BaseModel

# =============================================================================
# Nord Color Palette Constants
# =============================================================================
NORD_COLORS = {
    "nord0": "#2E3440",
    "nord1": "#3B4252",
    "nord2": "#434C5E",
    "nord3": "#4C566A",
    "nord4": "#D8DEE9",
    "nord5": "#E5E9F0",
    "nord6": "#ECEFF4",
    "nord7": "#8FBCBB",
    "nord8": "#88C0D0",
    "nord9": "#81A1C1",
    "nord10": "#5E81AC",
    "nord11": "#BF616A",
    "nord12": "#D08770",
    "nord13": "#EBCB8B",
    "nord14": "#A3BE8C",
    "nord15": "#B48EAD",
}


# =============================================================================
# Markdown Logger: Logs messages in Markdown format to rotating files.
# =============================================================================
class MarkdownLogger:
    """
    Logger that outputs markdown-formatted logs into rotating files.
    """

    def __init__(
        self,
        log_dir: str = "logs",
        log_file: str = "app.log",
        max_bytes: int = 10 * 1024,
        backup_count: int = 5,
    ) -> None:
        """
        Initialize the MarkdownLogger.

        Args:
            log_dir (str): Directory where logs will be stored.
            log_file (str): Name of the log file.
            max_bytes (int): Maximum size of a log file in bytes before rotating.
            backup_count (int): Number of backup files to keep.
        """
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.logger = logging.getLogger("MarkdownLogger")
        self.logger.setLevel(logging.DEBUG)
        log_path = os.path.join(self.log_dir, log_file)
        handler = RotatingFileHandler(log_path, maxBytes=max_bytes, backupCount=backup_count)
        formatter = logging.Formatter(
            "[%(asctime)s] **%(levelname)s** - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log(self, level: str, message: str) -> None:
        """
        Log a message with a given level.

        Args:
            level (str): Logging level (e.g., INFO, ERROR).
            message (str): The message to log.
        """
        if level.upper() == "INFO":
            self.logger.info(message)
        elif level.upper() == "ERROR":
            self.logger.error(message)
        elif level.upper() == "DEBUG":
            self.logger.debug(message)
        else:
            self.logger.warning(message)


# =============================================================================
# Pydantic Response Model for OpenAI Chat Completion
# =============================================================================
class OpenAIChatResponse(BaseModel):
    """
    Pydantic model for OpenAI Chat Completion response.
    """

    choices: List[Any]  # In production, a more precise type definition is recommended


# =============================================================================
# OpenAI Client Wrapper: Encapsulates API calls using v1.0 changes.
# =============================================================================
class OpenAIClientWrapper:
    """
    Wrapper for the OpenAI client using v1.0 API changes.
    """

    def __init__(self, api_key: str, logger: MarkdownLogger) -> None:
        """
        Initialize the OpenAI client.

        Args:
            api_key (str): API key for OpenAI.
            logger (MarkdownLogger): Logger instance for logging errors.
        """
        self.logger = logger
        try:
            # Explicit instantiation of the client (synchronous version)
            self.client = OpenAI(api_key=api_key)
        except Exception as e:
            self.logger.log("ERROR", f"Failed to instantiate OpenAI client: {e}")
            raise

    def chat_completion(self, model: str, messages: List[Dict[str, str]]) -> OpenAIChatResponse:
        """
        Call the OpenAI chat completion endpoint.

        Args:
            model (str): The model to use (e.g., "gpt-4").
            messages (List[Dict[str, str]]): List of message dictionaries.

        Returns:
            OpenAIChatResponse: Parsed response from OpenAI.
        """
        try:
            response = self.client.chat.completions.create(model=model, messages=messages)
            # Convert the Pydantic model to our defined response model.
            return OpenAIChatResponse(**response.model_dump())
        except Exception as e:
            self.logger.log("ERROR", f"Chat completion failed: {e}")
            raise


# =============================================================================
# Rich CLI: Provides interactive CLI using the Nord color theme.
# =============================================================================
class RichCLI:
    """
    Rich CLI interface with Nord color theme, typewriter effects, and spinners.
    """

    def __init__(
        self, logger: MarkdownLogger, first_delay: int = 5, subsequent_delay: int = 30
    ) -> None:
        """
        Initialize the RichCLI.

        Args:
            logger (MarkdownLogger): Logger instance.
            first_delay (int): Delay for the first bot response in seconds.
            subsequent_delay (int): Delay for subsequent responses in seconds.
        """
        self.console = Console()
        self.logger = logger
        self.first_delay = first_delay
        self.subsequent_delay = subsequent_delay
        self.response_count = 0

    def typewriter_print(self, text: str, delay: float = 0.05) -> None:
        """
        Print text with a typewriter effect.

        Args:
            text (str): The text to print.
            delay (float): Delay between characters in seconds.
        """
        for char in text:
            self.console.print(char, end="", style=f"bold {NORD_COLORS['nord8']}")
            time.sleep(delay)
        self.console.print("")  # Ensure a new line at the end

    def show_spinner(self, message: str, duration: int) -> None:
        """
        Display a spinner with a message for a specified duration.

        Args:
            message (str): Message to display alongside the spinner.
            duration (int): Duration in seconds for the spinner.
        """
        with self.console.status(
            f"[{NORD_COLORS['nord9']}] {message}...", spinner="dots"
        ) as status:
            time.sleep(duration)

    def prompt_user(self, prompt_message: str) -> str:
        """
        Prompt the user for input.

        Args:
            prompt_message (str): The prompt message.

        Returns:
            str: User input.
        """
        return Prompt.ask(Text(prompt_message, style=NORD_COLORS["nord10"]))

    def display_header(self, header: str) -> None:
        """
        Display a styled header.

        Args:
            header (str): Header text.
        """
        panel = Panel(header, style=f"bold {NORD_COLORS['nord7']}", expand=False)
        self.console.print(panel)

    def display_response(self, response: str) -> None:
        """
        Display a response using a typewriter effect.

        Args:
            response (str): The response text.
        """
        self.typewriter_print(response)

    def get_delay(self) -> int:
        """
        Determine the delay based on the number of responses.

        Returns:
            int: Delay duration in seconds.
        """
        self.response_count += 1
        return self.first_delay if self.response_count == 1 else self.subsequent_delay


# =============================================================================
# Main Application Logic
# =============================================================================
def main() -> None:
    """
    Main function to run the CLI application.
    """
    # Initialize markdown logger
    logger = MarkdownLogger()

    # Display startup header using the Nord-themed CLI
    cli = RichCLI(logger)
    cli.display_header("Welcome to the Nord Chat CLI Application")

    # Retrieve the OpenAI API key from environment variables
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        cli.console.print(
            "[bold red]Error:[/bold red] OPENAI_API_KEY environment variable is not set.",
            style=NORD_COLORS["nord11"],
        )
        logger.log("ERROR", "OPENAI_API_KEY environment variable is not set.")
        sys.exit(1)

    # Instantiate the OpenAI client wrapper
    try:
        openai_client = OpenAIClientWrapper(api_key=api_key, logger=logger)
    except Exception as e:
        cli.console.print(
            f"[bold red]Failed to initialize OpenAI client:[/bold red] {e}",
            style=NORD_COLORS["nord11"],
        )
        sys.exit(1)

    # Main conversation loop
    while True:
        try:
            user_input = cli.prompt_user("Enter your message (or type 'exit' to quit)")
            if user_input.strip().lower() == "exit":
                cli.console.print("[bold green]Goodbye![/bold green]", style=NORD_COLORS["nord14"])
                break

            # Log the user's input
            logger.log("INFO", f"User: {user_input}")

            # Build the message payload for the chat completion
            messages = [{"role": "user", "content": user_input}]

            # Determine the delay (first response vs. subsequent responses)
            delay_duration = cli.get_delay()

            # Show spinner to indicate processing with the configured delay
            cli.show_spinner("Processing your message", delay_duration)

            # Call OpenAI's chat completion endpoint
            response_model = openai_client.chat_completion(model="o3-mini", messages=messages)
            # Extract the response text.
            # (Assumes that response.choices[0].message.content exists in the API response.)
            response_text = (
                response_model.choices[0].get("message", {}).get("content", "No content received.")
            )
            logger.log("INFO", f"Bot: {response_text}")

            # Display the bot's response with a typewriter effect.
            cli.display_response(response_text)

        except Exception as e:
            cli.console.print(
                f"[bold red]An error occurred:[/bold red] {e}",
                style=NORD_COLORS["nord11"],
            )
            logger.log("ERROR", f"An error occurred: {e}")


if __name__ == "__main__":
    main()
