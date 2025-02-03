#!/usr/bin/env python3
"""
Terminal-based AI Bot Conversation
---------------------------------
A robust CLI chat interface that simulates conversations between AI bots with:
- Nord color theme integration
- Streaming responses with proper formatting
- Markdown logging for conversation history
- Thinking delay with spinner animation
"""

import os
import sys
import time
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Dict, List, Optional
from dataclasses import dataclass

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.live import Live
from rich.text import Text
from rich.prompt import Prompt
from rich.style import Style
from rich.spinner import Spinner
from rich.status import Status

# Load environment variables
load_dotenv()


# -----------------------------------------------------------------------------
# Nord Color Theme Configuration
# -----------------------------------------------------------------------------
class NordTheme:
    # [Previous theme code remains exactly the same...]
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
        if bg:
            return Style(color=color, bgcolor=bg)
        return Style(color=color)


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
@dataclass
class Config:
    DEFAULT_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4")
    THINKING_DELAY: int = int(os.getenv("THINKING_DELAY", "20"))  # 20 seconds

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
            os.makedirs("logs", exist_ok=True)
            log_file = f"logs/bot_conversation_{datetime.now():%Y%m%d_%H%M%S}.md"

            with open(log_file, "w", encoding="utf-8") as f:
                f.write("# AI Bot Conversation Log\n\n")
                f.write(
                    f"*Dialogue between {Config.BOT_1['name']} and {Config.BOT_2['name']}*\n\n"
                )
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


class BotConversationInterface:
    """Manages the bot conversation interface using Rich."""

    def __init__(self):
        self.console = Console()
        self.client = OpenAI()
        self.markdown_logger = MarkdownLogger()
        self.theme = NordTheme

    def thinking_delay(self, bot_name: str, style_color: str) -> None:
        """Display thinking animation with delay."""
        with Status(
            f"{bot_name} is thinking...",
            spinner="dots",
            spinner_style=self.theme.style(style_color),
            console=self.console,
        ) as status:
            time.sleep(Config.THINKING_DELAY)

    def _print_header(self, title: str) -> None:
        """Print a styled header."""
        self.console.print()
        self.console.print(title, style=self.theme.style(self.theme.NORD8))
        self.console.print(
            "Press Ctrl+C to exit", style=self.theme.style(self.theme.NORD3)
        )
        self.console.print()

    def _stream_response(
        self, messages: List[Dict], speaker: str, model: str = "gpt-4"
    ) -> str:
        """Stream the bot's response with proper formatting."""
        full_response = []
        response_text = Text()

        # Add the speaker label with appropriate color
        style_color = (
            Config.BOT_1["style"]
            if speaker == Config.BOT_1["name"]
            else Config.BOT_2["style"]
        )
        response_text.append(f"{speaker}: ", style=self.theme.style(style_color))

        with Live(response_text, console=self.console, refresh_per_second=15) as live:
            stream = self.client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full_response.append(token)
                    response_text.append(
                        token, style=self.theme.style(self.theme.NORD4)
                    )
                    live.update(response_text)

        self.console.print()
        return "".join(full_response)

    def run_conversation(self) -> None:
        """Main conversation loop between the two bots."""
        self._print_header(
            f"AI Bot Conversation: {Config.BOT_1['name']} vs {Config.BOT_2['name']}"
        )
        self.markdown_logger.log("Starting bot conversation")

        try:
            # Generate conversation starter
            self.console.print(
                "Generating conversation starter...",
                style=self.theme.style(self.theme.NORD8),
            )

            starter_messages = [
                {
                    "role": "system",
                    "content": "Generate an engaging conversation starter about AI ethics.",
                }
            ]

            starter = self._stream_response(
                starter_messages, "System", Config.DEFAULT_MODEL
            )
            self.markdown_logger.log(starter)

            # Initialize message histories for both bots
            bot1_msgs = [
                {"role": "system", "content": Config.BOT_1["system_prompt"]},
                {"role": "user", "content": starter},
            ]

            bot2_msgs = [
                {"role": "system", "content": Config.BOT_2["system_prompt"]},
                {"role": "user", "content": starter},
            ]

            # First response doesn't need thinking delay
            response = self._stream_response(
                bot1_msgs, Config.BOT_1["name"], Config.DEFAULT_MODEL
            )
            self.markdown_logger.log(response, Config.BOT_1["name"])
            bot1_msgs.append({"role": "assistant", "content": response})
            bot2_msgs.append({"role": "user", "content": response})

            while True:
                # Bot 2's turn (with thinking delay)
                self.thinking_delay(Config.BOT_2["name"], Config.BOT_2["style"])

                response = self._stream_response(
                    bot2_msgs, Config.BOT_2["name"], Config.DEFAULT_MODEL
                )
                self.markdown_logger.log(response, Config.BOT_2["name"])
                bot2_msgs.append({"role": "assistant", "content": response})
                bot1_msgs.append({"role": "user", "content": response})

                # Bot 1's turn (with thinking delay)
                self.thinking_delay(Config.BOT_1["name"], Config.BOT_1["style"])

                response = self._stream_response(
                    bot1_msgs, Config.BOT_1["name"], Config.DEFAULT_MODEL
                )
                self.markdown_logger.log(response, Config.BOT_1["name"])
                bot1_msgs.append({"role": "assistant", "content": response})
                bot2_msgs.append({"role": "user", "content": response})

        except KeyboardInterrupt:
            self.console.print(
                "\nConversation ended by user", style=self.theme.style(self.theme.NORD9)
            )
            self.markdown_logger.log("Conversation ended by user")


def main():
    """Main application entry point."""
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
    except Exception as e:
        interface.console.print(
            f"\nError: {str(e)}", style=Style(color=NordTheme.NORD11)
        )
        interface.markdown_logger.log(f"Fatal error: {str(e)}")
        sys.exit(1)
    finally:
        interface.console.print("\nGoodbye!", style=Style(color=NordTheme.NORD14))


if __name__ == "__main__":
    main()
