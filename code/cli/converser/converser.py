#!/usr/bin/env python3
"""
Terminal-based AI Bot Conversation
---------------------------------
A robust CLI chat interface that simulates conversations between AI bots with:
- Nord color theme integration
- *No Streaming from OpenAI*; we show a spinner while waiting,
  then type out the bot's response with a typewriter effect.
- Markdown logging for conversation history
- Thinking delay spinner
- User-provided or AI-generated conversation starter
- Bot selection
"""

import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Dict, List

import openai  # For openai>=1.0.0
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt
from rich.status import Status
from rich.style import Style

# Load environment variables
load_dotenv()


# -----------------------------------------------------------------------------
# Nord Color Theme Configuration
# -----------------------------------------------------------------------------
class NordTheme:
    NORD0 = "#2E3440"  # Dark bg
    NORD1 = "#3B4252"  # Lighter bg
    NORD2 = "#434C5E"  # Selection bg
    NORD3 = "#4C566A"  # Inactive text

    # Snow Storm
    NORD4 = "#D8DEE9"  # Text
    NORD5 = "#E5E9F0"  # Light text
    NORD6 = "#ECEFF4"  # Bright text

    # Frost
    NORD7 = "#8FBCBB"  # Mint
    NORD8 = "#88C0D0"  # Light blue
    NORD9 = "#81A1C1"  # Medium blue
    NORD10 = "#5E81AC"  # Dark blue

    # Aurora
    NORD11 = "#BF616A"  # Red
    NORD12 = "#D08770"  # Orange
    NORD13 = "#EBCB8B"  # Yellow
    NORD14 = "#A3BE8C"  # Green
    NORD15 = "#B48EAD"  # Purple

    @classmethod
    def style(cls, color: str, bg: str = None) -> Style:
        """Creates a Rich.Style object from color codes."""
        if bg:
            return Style(color=color, bgcolor=bg)
        return Style(color=color)


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
@dataclass
class Config:
    DEFAULT_MODEL: str = os.getenv("OPENAI_MODEL", "chatgpt-4o-latest")
    THINKING_DELAY: int = int(os.getenv("THINKING_DELAY", "5"))  # spinner time (secs)

    BOT_1 = {
        "name": os.getenv("BOT_1_NAME", "Bot Alpha"),
        "system_prompt": os.getenv(
            "BOT_1_PROMPT",
            "You are Bot Alpha – a thoughtful and engaging conversationalist. Never break character.",
        ),
        "style": NordTheme.NORD14,  # Green
    }

    BOT_2 = {
        "name": os.getenv("BOT_2_NAME", "Bot Beta"),
        "system_prompt": os.getenv(
            "BOT_2_PROMPT",
            "You are Bot Beta – a direct and analytical debater. Never break character.",
        ),
        "style": NordTheme.NORD11,  # Red
    }


# -----------------------------------------------------------------------------
# Markdown Logger
# -----------------------------------------------------------------------------
class MarkdownLogger:
    """Handles markdown-formatted logging of bot conversations."""

    def __init__(self):
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        class MarkdownFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                timestamp = self.formatTime(record, datefmt="%Y-%m-%d %H:%M:%S")
                role = getattr(record, "role", "system")
                message = (record.getMessage() or "").strip()

                if role == "system":
                    return f"\n### {timestamp} - System Message\n{message}\n"
                return f"\n#### {timestamp} - {role}\n{message}\n"

        logger = logging.getLogger("bot_conversation")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            # Create logs folder if needed
            os.makedirs("logs", exist_ok=True)

            now = datetime.now()
            month_str = str(now.month)
            day_str = str(now.day)
            hour_min = now.strftime("%I:%M%p").lstrip("0")  # e.g. "3:16PM"
            hour_min = hour_min[:-2] + hour_min[-2:].lower()  # "3:16pm"

            date_str = f"{month_str}.{day_str}.{now.year}_{hour_min}"
            bot1 = Config.BOT_1["name"]
            bot2 = Config.BOT_2["name"]
            file_name = f"{date_str}_ai_conversation_between_{bot1}_&_{bot2}.md"
            log_file = os.path.join("logs", file_name)

            # Initialize file with a heading
            with open(log_file, "w", encoding="utf-8") as f:
                f.write("# AI Bot Conversation Log\n\n")
                f.write(f"*Dialogue between {bot1} and {bot2}*\n\n")
                f.write("---\n")

            handler = RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=3,
                encoding="utf-8",
            )
            handler.setFormatter(MarkdownFormatter())
            logger.addHandler(handler)

        return logger

    def log(self, message: str, role: str = "system") -> None:
        """Log a message with the specified role."""
        self.logger.info(message, extra={"role": role})


# -----------------------------------------------------------------------------
# BotConversationInterface
# -----------------------------------------------------------------------------
class BotConversationInterface:
    """Manages the bot conversation interface using Rich (no streaming)."""

    def __init__(self):
        self.console = Console()
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.markdown_logger = MarkdownLogger()
        self.theme = NordTheme

    def _print_header(self, title: str) -> None:
        """Print a styled header at the start."""
        self.console.print()
        self.console.print(title, style=self.theme.style(self.theme.NORD8))
        self.console.print("Press Ctrl+C to exit", style=self.theme.style(self.theme.NORD3))
        self.console.print()

    def _typed_output(
        self,
        speaker_label: str,
        message: str,
        label_color: str,
        typing_speed: float = 0.02,
    ) -> None:
        """
        Type out `message` character by character, prefixed by speaker_label.
        Example: "Bot Alpha: Hello world"
        """
        # Print the speaker label in color first
        self.console.print(
            f"{speaker_label}: ",
            style=self.theme.style(label_color),
            end="",  # no newline
        )

        # Then type out the message
        for char in message:
            self.console.print(char, style=self.theme.style(self.theme.NORD4), end="")
            time.sleep(typing_speed)
        self.console.print("")  # Print empty string to force line break
        self.console.print("")  # Print another empty line for spacing

    def _get_completion(self, messages: List[Dict], model: str) -> str:
        """
        Makes a single (non-stream) call to the ChatCompletion API
        and returns the assistant's text.

        Also ensures the spinner remains visible at least Config.THINKING_DELAY seconds.
        """
        start_time = time.time()
        with Status(
            "Thinking...",
            spinner="dots",
            spinner_style=self.theme.style(self.theme.NORD3),
            console=self.console,
        ):
            # Single call (no streaming)
            completion = openai.chat.completions.create(
                model=model,
                messages=messages,
            )
            end_time = time.time()

            # If the API call finishes quickly, we continue "thinking" until
            # we've reached at least Config.THINKING_DELAY seconds.
            api_time = end_time - start_time
            if api_time < Config.THINKING_DELAY:
                time.sleep(Config.THINKING_DELAY - api_time)

        # Extract the text from completion
        full_text = completion.choices[0].message.content
        return full_text

    def run_conversation(self) -> None:
        """Main conversation loop between the two bots (no streaming)."""
        self._print_header(f"AI Bot Conversation: {Config.BOT_1['name']} vs {Config.BOT_2['name']}")
        self.markdown_logger.log("Starting bot conversation")

        try:
            # Prompt user for conversation starter
            self.console.print(
                "\n[bold cyan]Please input a conversation starter which will be sent "
                "to the first bot (chosen next).[/bold cyan]"
            )
            user_starter = Prompt.ask(
                "If you would rather have the AI generate a random conversation starter, just press Enter"
            ).strip()

            # If user left it blank, let AI generate a conversation starter
            if user_starter:
                starter = user_starter
            else:
                self.console.print(
                    "\n[bold magenta]Generating conversation starter from AI...[/bold magenta]"
                )
                ai_starter_messages = [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that specializes in generating conversation openers.",
                    },
                    {
                        "role": "user",
                        "content": "Please produce an engaging conversation starter now.",
                    },
                ]
                starter = self._get_completion(ai_starter_messages, Config.DEFAULT_MODEL)
                # Show typed output for system's generated starter
                self._typed_output("System", starter, NordTheme.NORD7)
                self.markdown_logger.log(starter, "system")

            # Choose which bot goes first
            self.console.print(
                "\n[bold yellow]Choose which bot should respond first:[/bold yellow]"
            )
            self.console.print(f"  1) {Config.BOT_1['name']}")
            self.console.print(f"  2) {Config.BOT_2['name']}")

            choice = Prompt.ask(
                "[bold green]Enter 1 or 2[/bold green]",
                choices=["1", "2"],
                default="1",
            )
            if choice == "1":
                first_bot = Config.BOT_1
                second_bot = Config.BOT_2
            else:
                first_bot = Config.BOT_2
                second_bot = Config.BOT_1

            # Just one blank line here after the output
            self.console.print()

            # Initialize message histories
            first_bot_msgs = [
                {"role": "system", "content": first_bot["system_prompt"]},
                {"role": "user", "content": starter},
            ]
            second_bot_msgs = [
                {"role": "system", "content": second_bot["system_prompt"]},
            ]

            # FIRST BOT RESPONDS to the starter
            first_bot_response = self._get_completion(first_bot_msgs, Config.DEFAULT_MODEL)
            # Show typed output
            self._typed_output(first_bot["name"], first_bot_response, first_bot["style"])
            self.markdown_logger.log(first_bot_response, first_bot["name"])

            # Update histories
            first_bot_msgs.append({"role": "assistant", "content": first_bot_response})
            second_bot_msgs.append({"role": "user", "content": first_bot_response})

            # Now alternate forever
            while True:
                # SECOND BOT turn
                second_bot_response = self._get_completion(second_bot_msgs, Config.DEFAULT_MODEL)
                self._typed_output(second_bot["name"], second_bot_response, second_bot["style"])
                self.markdown_logger.log(second_bot_response, second_bot["name"])

                second_bot_msgs.append({"role": "assistant", "content": second_bot_response})
                first_bot_msgs.append({"role": "user", "content": second_bot_response})

                # FIRST BOT turn
                first_bot_response = self._get_completion(first_bot_msgs, Config.DEFAULT_MODEL)
                self._typed_output(first_bot["name"], first_bot_response, first_bot["style"])
                self.markdown_logger.log(first_bot_response, first_bot["name"])

                first_bot_msgs.append({"role": "assistant", "content": first_bot_response})
                second_bot_msgs.append({"role": "user", "content": first_bot_response})

        except KeyboardInterrupt:
            self.console.print(
                "\nConversation ended by user",
                style=self.theme.style(self.theme.NORD9),
            )
            self.markdown_logger.log("Conversation ended by user")
        except Exception as e:
            self.console.print(
                f"\nError: {str(e)}",
                style=Style(color=NordTheme.NORD11),
            )
            self.markdown_logger.log(f"Fatal error: {str(e)}")
            sys.exit(1)

    def close(self):
        """Any final cleanup."""
        self.console.print("\nGoodbye!", style=Style(color=NordTheme.NORD14))


# -----------------------------------------------------------------------------
# main()
# -----------------------------------------------------------------------------
def main():
    """Main entry point."""
    if not os.getenv("OPENAI_API_KEY"):
        console = Console()
        console.print(
            "Error: OPENAI_API_KEY environment variable not set",
            style=Style(color=NordTheme.NORD11),
        )
        sys.exit(1)

    interface = BotConversationInterface()
    try:
        interface.run_conversation()
    finally:
        interface.close()


if __name__ == "__main__":
    main()
