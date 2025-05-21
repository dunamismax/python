#!/usr/bin/env python3
"""
ASCII Art Generator
-----------------------------------
A CLI-based ASCII art generator using GPT models.
"""

import os
import sys
import time
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.style import Style
from rich.text import Text
from rich.status import Status

# -----------------------------------------------------------------------------
# 1. Environment & Nord Theme
# -----------------------------------------------------------------------------
load_dotenv()


class NordTheme:
    NORD0 = "#2E3440"
    NORD1 = "#3B4252"
    NORD2 = "#434C5E"
    NORD3 = "#4C566A"
    NORD4 = "#D8DEE9"
    NORD5 = "#E5E9F0"
    NORD6 = "#ECEFF4"
    NORD7 = "#8FBCBB"
    NORD8 = "#88C0D0"
    NORD9 = "#81A1C1"
    NORD10 = "#5E81AC"
    NORD11 = "#BF616A"
    NORD12 = "#D08770"
    NORD13 = "#EBCB8B"
    NORD14 = "#A3BE8C"
    NORD15 = "#B48EAD"

    @classmethod
    def style(cls, color: str, bg: Optional[str] = None) -> Style:
        if bg:
            return Style(color=color, bgcolor=bg)
        return Style(color=color)


# -----------------------------------------------------------------------------
# 2. Configuration
# -----------------------------------------------------------------------------
@dataclass
class Config:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    DEFAULT_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4")
    GENERATION_PAUSE: int = int(os.getenv("GENERATION_PAUSE", "20"))

    MAX_ART_WIDTH: int = 80
    MAX_ART_HEIGHT: int = 40

    PROMPTS = [
        "Create a detailed landscape scene with mountains and trees",
        "Generate a portrait of a cat using ASCII characters",
        "Design an abstract geometric pattern",
        "Create a cityscape with buildings and clouds",
        "Draw a sailing ship on waves",
    ]


# -----------------------------------------------------------------------------
# 3. ASCII Art Application
# -----------------------------------------------------------------------------
class ASCIIArtApp:
    """Generates ASCII art in a single request, ensuring triple quotes are included."""

    def __init__(self):
        self.config = Config()
        self.theme = NordTheme
        self.console = Console()
        self.client = self._init_openai()
        self.logger = self._setup_logging()

    def _init_openai(self) -> OpenAI:
        api_key = self.config.OPENAI_API_KEY
        if not api_key:
            self.console.print(
                "[bold red]Error:[/bold red] OPENAI_API_KEY environment variable not set.",
                style=self.theme.style(self.theme.NORD11),
            )
            sys.exit(1)
        return OpenAI(api_key=api_key)

    def _setup_logging(self) -> logging.Logger:
        logger = logging.getLogger("ascii_art_app")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            os.makedirs("logs", exist_ok=True)
            log_file = f"logs/ascii_art_{datetime.now():%Y%m%d_%H%M%S}.log"
            handler = RotatingFileHandler(
                log_file,
                maxBytes=5 * 1024 * 1024,  # 5 MB
                backupCount=3,
                encoding="utf-8",
            )
            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def print_header(self) -> None:
        self.console.print()
        self.console.print(
            "ASCII Art Generator (Triple-Quoted)",
            style=self.theme.style(self.theme.NORD8),
            justify="center",
        )
        self.console.print(
            "Press Ctrl+C to exit at any time.\n",
            style=self.theme.style(self.theme.NORD3),
            justify="center",
        )

    def generate_art(self, prompt: str) -> str:
        """
        Non-streaming GPT request that instructs GPT to enclose its ASCII in triple quotes.
        Returns the entire text (including triple quotes).
        """
        system_prompt = (
            "You are an ASCII art generator. Please enclose your entire ASCII art between triple quotes:\n"
            '""" on its own line at the top, and """ on its own line at the bottom.\n'
            "Do NOT add blank lines before or after the triple quotes.\n"
            "Follow these guidelines for the ASCII art:\n"
            f"- Maximum width: {self.config.MAX_ART_WIDTH} characters\n"
            f"- Maximum height: {self.config.MAX_ART_HEIGHT} lines\n"
            "- Use only ASCII characters (no Unicode)\n"
            "- Provide only the ASCII art, no additional commentary.\n"
            "- Keep line lengths consistent.\n"
            "- Indent or center the art as you see fit, but ensure top line is the triple quotes.\n"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        try:
            with self.console.status(
                "Generating ASCII art...",
                spinner="dots",
                spinner_style=self.theme.style(self.theme.NORD13),
            ):
                completion = self.client.chat.completions.create(
                    model=self.config.DEFAULT_MODEL, messages=messages, stream=False
                )
            # Grab the entire text (with triple quotes)
            return completion.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Art generation error: {e}", exc_info=True)
            return '"""\nError generating art.\n"""'

    def display_art(self, art: str, prompt: str) -> None:
        """
        Show ASCII including triple quotes in a Rich panel. We do not strip them.
        """
        # Put the GPT response directly into a Rich Text object.
        panel_content = Text(art, style=self.theme.style(self.theme.NORD4))
        panel = Panel(
            panel_content,
            title="[bold]ASCII Art[/bold]",
            subtitle=f"Prompt: {prompt}",
            border_style=self.theme.style(self.theme.NORD8),
            padding=(1, 2),
        )
        self.console.print(panel)

    def run(self) -> None:
        """Loop over prompts at intervals, showing new triple-quoted ASCII each time."""
        self.print_header()
        self.logger.info("Starting ASCII art generator (triple-quoted).")

        prompts = self.config.PROMPTS
        idx = 0
        last_time = time.time()

        try:
            while True:
                current_time = time.time()
                if current_time - last_time >= self.config.GENERATION_PAUSE:
                    prompt = prompts[idx]
                    idx = (idx + 1) % len(prompts)

                    # Clear terminal to show fresh art
                    self.console.clear()
                    self.print_header()

                    art = self.generate_art(prompt)
                    self.display_art(art, prompt)
                    self.logger.info(f"Generated art for prompt: '{prompt}'")

                    last_time = time.time()

                time.sleep(0.1)

        except KeyboardInterrupt:
            self.console.print(
                "\nExiting ASCII Art Generator...",
                style=self.theme.style(self.theme.NORD9),
                justify="center",
            )
            self.logger.info("Generator stopped by user.")


# -----------------------------------------------------------------------------
# 4. Entry Point
# -----------------------------------------------------------------------------
def main():
    app = ASCIIArtApp()
    if not app.config.OPENAI_API_KEY:
        app.console.print(
            "\n[bold red]Error:[/bold red] OPENAI_API_KEY not set. Exiting.",
            style=Style(color=NordTheme.NORD11),
        )
        sys.exit(1)

    try:
        app.run()
    except Exception as e:
        app.console.print(
            f"\n[red]Error:[/red] {str(e)}", style=Style(color=NordTheme.NORD11)
        )
        app.logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        app.console.print("\nGoodbye!", style=Style(color=NordTheme.NORD14))


if __name__ == "__main__":
    main()
