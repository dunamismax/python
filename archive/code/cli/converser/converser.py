#!/usr/bin/env python3
"""

Terminal-based AI Bot Conversation
CLI chat interface with AI bots featuring a Nord theme, Rich UI, spinner,
typewriter-rendered responses, markdown logging, and adjustable delays.
Supports both user-provided and AI-generated conversation starters with bot selection.
Improvements: Uses the OpenAI v1.0 client with threaded API calls to maintain the spinner,
automatically converts system messages for models without native support, and offers robust,
modular, type-annotated code with production-grade rotating logs.

"""

import logging
import os
import sys
import threading
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Import the new OpenAI client from v1.0
from openai import OpenAI
from rich.console import Console
from rich.prompt import Prompt
from rich.status import Status
from rich.style import Style

# Load environment variables from .env file if available.
load_dotenv()


# -----------------------------------------------------------------------------
# Nord Color Theme Configuration
# -----------------------------------------------------------------------------
class NordTheme:
    NORD0 = "#2E3440"  # Dark background
    NORD1 = "#3B4252"  # Lighter background
    NORD2 = "#434C5E"  # Selection background
    NORD3 = "#4C566A"  # Inactive text

    # Snow Storm
    NORD4 = "#D8DEE9"  # Default text
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
    def style(cls, color: str, bg: Optional[str] = None) -> Style:
        """Return a Rich Style based on the provided text color and optional background."""
        return Style(color=color, bgcolor=bg) if bg else Style(color=color)


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
class Config:
    DEFAULT_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    # Delay parameters in seconds:
    FIRST_RESPONSE_DELAY: int = int(os.getenv("FIRST_RESPONSE_DELAY", "5"))
    SUBSEQUENT_RESPONSE_DELAY: int = int(os.getenv("SUBSEQUENT_RESPONSE_DELAY", "30"))

    BOT_1: Dict[str, Any] = {
        "name": os.getenv("BOT_1_NAME", "Bot Alpha"),
        "system_prompt": os.getenv(
            "BOT_1_PROMPT",
            "You are Bot Alpha – a thoughtful and engaging conversationalist. Never break character.",
        ),
        "style": NordTheme.NORD14,  # Green
    }
    BOT_2: Dict[str, Any] = {
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
    """
    Handles markdown-formatted logging of bot conversations.
    Logs are written to a rotating file inside a "logs" directory.
    """

    def __init__(self) -> None:
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Sets up a rotating file logger with markdown formatting."""

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
            os.makedirs("logs", exist_ok=True)
            now = datetime.now()
            date_str = (
                now.strftime("%m.%d.%Y_%I:%M%p").lstrip("0").replace("AM", "am").replace("PM", "pm")
            )
            bot1 = Config.BOT_1["name"]
            bot2 = Config.BOT_2["name"]
            file_name = f"{date_str}_ai_conversation_between_{bot1}_&_{bot2}.md"
            log_file = os.path.join("logs", file_name)

            # Initialize the log file with a header.
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
# Bot Conversation Interface
# -----------------------------------------------------------------------------
class BotConversationInterface:
    """
    Manages the bot conversation interface using Rich.
    Displays headers, handles user input, and renders bot responses
    using a typewriter effect, while logging the entire conversation.
    """

    def __init__(self) -> None:
        self.console = Console()
        # Instantiate the new OpenAI client.
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
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
        Display `message` character by character (a typewriter effect),
        prefixed with `speaker_label`.
        """
        self.console.print(f"{speaker_label}: ", style=self.theme.style(label_color), end="")
        for char in message:
            self.console.print(char, style=self.theme.style(self.theme.NORD4), end="")
            time.sleep(typing_speed)
        self.console.print("\n")

    def _adjust_message_roles(
        self, messages: List[Dict[str, str]], model: str
    ) -> List[Dict[str, str]]:
        """
        For models like "gpt-4o" that do not support messages with role 'system',
        convert any system message to a user message prefixed with "[SYSTEM]".
        """
        if model.lower().startswith("gpt-4o"):
            adjusted = []
            for msg in messages:
                if msg.get("role") == "system":
                    adjusted.append({"role": "user", "content": "[SYSTEM] " + msg["content"]})
                else:
                    adjusted.append(msg)
            return adjusted
        return messages

    def _get_completion(self, messages: List[Dict[str, str]], model: str, min_delay: int) -> str:
        """
        Make a single (non-streaming) call to the OpenAI ChatCompletion API and
        return the assistant's response.

        The spinner remains active until both the API call completes and
        at least `min_delay` seconds have elapsed.
        """
        result: Dict[str, Any] = {}
        exception_holder: List[Exception] = []

        def api_call():
            try:
                # Adjust message roles if needed.
                adjusted_messages = self._adjust_message_roles(messages, model)
                res = self.client.chat.completions.create(
                    model=model,
                    messages=adjusted_messages,
                    store=True,  # Use store=True per latest docs if desired
                )
                result["completion"] = res
            except Exception as e:
                exception_holder.append(e)

        thread = threading.Thread(target=api_call)
        thread.start()
        start_time = time.time()

        with Status(
            "Thinking...",
            spinner="dots",
            spinner_style=self.theme.style(self.theme.NORD3),
            console=self.console,
        ):
            # Keep the spinner active until both conditions are met:
            while thread.is_alive() or (time.time() - start_time < min_delay):
                time.sleep(0.1)
        thread.join()

        if exception_holder:
            exc = exception_holder[0]
            error_msg = f"OpenAI API error: {exc}"
            self.console.print(error_msg, style=self.theme.style(self.theme.NORD11))
            self.markdown_logger.log(error_msg, role="error")
            raise exc

        full_text = result["completion"].choices[0].message.content.strip()
        return full_text

    def _update_histories(
        self,
        sender_history: List[Dict[str, str]],
        receiver_history: List[Dict[str, str]],
        message: str,
        role_sent: str,
        role_received: str,
    ) -> None:
        """
        Update both bots’ message histories.
        Adds the message as the sender's assistant response and as the receiver's user prompt.
        """
        sender_history.append({"role": role_sent, "content": message})
        receiver_history.append({"role": role_received, "content": message})

    def run_conversation(self) -> None:
        """Main conversation loop between the two bots (non-streaming)."""
        title = f"AI Bot Conversation: {Config.BOT_1['name']} vs {Config.BOT_2['name']}"
        self._print_header(title)
        self.markdown_logger.log("Starting bot conversation")

        try:
            self.console.print(
                "\n[bold cyan]Enter a conversation starter to send to the first bot.[/bold cyan]"
            )
            user_starter = Prompt.ask("Or press Enter to let the AI generate one").strip()

            if user_starter:
                starter = user_starter
            else:
                self.console.print(
                    "\n[bold magenta]Generating conversation starter...[/bold magenta]"
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
                starter = self._get_completion(
                    ai_starter_messages, Config.DEFAULT_MODEL, min_delay=Config.FIRST_RESPONSE_DELAY
                )
                self._typed_output("System", starter, NordTheme.NORD7)
                self.markdown_logger.log(starter, role="system")

            self.console.print(
                "\n[bold yellow]Choose which bot should respond first:[/bold yellow]"
            )
            self.console.print(f"  1) {Config.BOT_1['name']}")
            self.console.print(f"  2) {Config.BOT_2['name']}")
            choice = Prompt.ask(
                "[bold green]Enter 1 or 2[/bold green]", choices=["1", "2"], default="1"
            )

            if choice == "1":
                first_bot = Config.BOT_1
                second_bot = Config.BOT_2
            else:
                first_bot = Config.BOT_2
                second_bot = Config.BOT_1

            self.console.print()

            # Initialize message histories.
            first_bot_msgs: List[Dict[str, str]] = [
                {"role": "system", "content": first_bot["system_prompt"]},
                {"role": "user", "content": starter},
            ]
            second_bot_msgs: List[Dict[str, str]] = [
                {"role": "system", "content": second_bot["system_prompt"]},
            ]

            # FIRST BOT responds to the starter with a FIRST_RESPONSE_DELAY.
            first_bot_response = self._get_completion(
                first_bot_msgs, Config.DEFAULT_MODEL, min_delay=Config.FIRST_RESPONSE_DELAY
            )
            self._typed_output(first_bot["name"], first_bot_response, first_bot["style"])
            self.markdown_logger.log(first_bot_response, role=first_bot["name"])
            self._update_histories(
                sender_history=first_bot_msgs,
                receiver_history=second_bot_msgs,
                message=first_bot_response,
                role_sent="assistant",
                role_received="user",
            )

            # Now alternate turns indefinitely:
            # Second bot and subsequent responses use the SUBSEQUENT_RESPONSE_DELAY.
            while True:
                second_bot_response = self._get_completion(
                    second_bot_msgs,
                    Config.DEFAULT_MODEL,
                    min_delay=Config.SUBSEQUENT_RESPONSE_DELAY,
                )
                self._typed_output(second_bot["name"], second_bot_response, second_bot["style"])
                self.markdown_logger.log(second_bot_response, role=second_bot["name"])
                self._update_histories(
                    sender_history=second_bot_msgs,
                    receiver_history=first_bot_msgs,
                    message=second_bot_response,
                    role_sent="assistant",
                    role_received="user",
                )

                first_bot_response = self._get_completion(
                    first_bot_msgs, Config.DEFAULT_MODEL, min_delay=Config.SUBSEQUENT_RESPONSE_DELAY
                )
                self._typed_output(first_bot["name"], first_bot_response, first_bot["style"])
                self.markdown_logger.log(first_bot_response, role=first_bot["name"])
                self._update_histories(
                    sender_history=first_bot_msgs,
                    receiver_history=second_bot_msgs,
                    message=first_bot_response,
                    role_sent="assistant",
                    role_received="user",
                )

        except KeyboardInterrupt:
            self.console.print(
                "\nConversation ended by user", style=self.theme.style(self.theme.NORD9)
            )
            self.markdown_logger.log("Conversation ended by user")
        except Exception as e:
            error_text = f"Fatal error: {e}"
            self.console.print(f"\n{error_text}", style=self.theme.style(self.theme.NORD11))
            self.markdown_logger.log(error_text)
            sys.exit(1)

    def close(self) -> None:
        """Perform any necessary cleanup before exiting."""
        self.console.print("\nGoodbye!", style=Style(color=NordTheme.NORD14))


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------
def main() -> None:
    """Main entry point for the AI Bot Conversation program."""
    if not os.getenv("OPENAI_API_KEY"):
        Console().print(
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
