#!/usr/bin/env python3
"""
Rich-based ASCII Art Generator
-----------------------------
A modern CLI ASCII art generator using OpenAI's GPT model with:
- Rich UI components and styling
- Nord color theme integration
- Streaming responses with proper formatting
- Automated art generation with configurable intervals
"""

import os
import sys
import time
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.live import Live
from rich.text import Text
from rich.panel import Panel
from rich.style import Style
from rich.status import Status
from rich.spinner import Spinner
from rich.prompt import Prompt

# Load environment variables
load_dotenv()


# -----------------------------------------------------------------------------
# Nord Color Theme Configuration
# -----------------------------------------------------------------------------
class NordTheme:
    # Polar Night
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
    GENERATION_PAUSE: int = int(os.getenv("GENERATION_PAUSE", "10"))
    MAX_ART_WIDTH: int = 60
    MAX_ART_HEIGHT: int = 20

    PROMPTS = [
        "Create a detailed landscape scene with mountains and trees",
        "Generate a portrait of a cat using ASCII characters",
        "Design an abstract geometric pattern",
        "Create a cityscape with buildings and clouds",
        "Draw a sailing ship on waves",
    ]


class ASCIIArtGenerator:
    """Manages the ASCII art generation interface using Rich."""

    def __init__(self):
        self.console = Console()
        self.client = OpenAI()
        self.theme = NordTheme
        self.setup_logging()

    def setup_logging(self) -> None:
        """Configure rotating file logger."""
        logger = logging.getLogger("ascii_generator")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            os.makedirs("logs", exist_ok=True)
            log_file = f"logs/ascii_art_{datetime.now():%Y%m%d_%H%M%S}.log"

            handler = RotatingFileHandler(
                log_file,
                maxBytes=5 * 1024 * 1024,  # 5MB
                backupCount=3,
                encoding="utf-8",
            )
            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        self.logger = logger

    def _print_header(self) -> None:
        """Print styled header."""
        self.console.print()
        self.console.print(
            "ASCII Art Generator",
            style=self.theme.style(self.theme.NORD8),
            justify="center",
        )
        self.console.print(
            "Press Ctrl+C to exit",
            style=self.theme.style(self.theme.NORD3),
            justify="center",
        )
        self.console.print()

    def generate_art(self, prompt: str) -> str:
        """Generate ASCII art using GPT-4."""
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an ASCII art generator. Create ASCII art with these guidelines:\n"
                        f"- Maximum width: {Config.MAX_ART_WIDTH} characters\n"
                        f"- Maximum height: {Config.MAX_ART_HEIGHT} lines\n"
                        "- Use only ASCII characters (no Unicode)\n"
                        "- Focus on visual clarity and artistic detail\n"
                        "- Provide ONLY the ASCII art itself, no comments or explanations\n"
                        "- Do not include triple quotes in your response\n"
                        "- Ensure consistent line lengths\n"
                        "- Center the art horizontally"
                    ),
                },
                {"role": "user", "content": prompt},
            ]

            response_text = Text()

            with Status(
                "Generating ASCII art...",
                spinner="dots",
                spinner_style=self.theme.style(self.theme.NORD13),
                console=self.console,
            ):
                response = self.client.chat.completions.create(
                    model=Config.DEFAULT_MODEL, messages=messages, stream=True
                )

                art = []
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        art.append(chunk.choices[0].delta.content)

            return "".join(art).strip()

        except Exception as e:
            self.logger.error(f"Art generation error: {e}")
            return "Error generating art."

    def display_art(self, art: str, prompt: str) -> None:
        """Display ASCII art with decorative formatting."""
        # Format with triple quotes
        formatted_art = f'"""\n{art}\n"""'

        # Create panel with art
        panel = Panel(
            Text(formatted_art, style=self.theme.style(self.theme.NORD4)),
            title="[bold]ASCII Art[/bold]",
            subtitle=f"Prompt: {prompt}",
            border_style=self.theme.style(self.theme.NORD8),
            padding=(1, 2),
        )

        self.console.print(panel)

    def run(self) -> None:
        """Main execution loop."""
        self._print_header()
        self.logger.info("Starting ASCII art generator")
        prompt_idx = 0
        last_generation_time = 0

        try:
            while True:
                current_time = time.time()

                if current_time - last_generation_time >= Config.GENERATION_PAUSE:
                    prompt = Config.PROMPTS[prompt_idx]
                    prompt_idx = (prompt_idx + 1) % len(Config.PROMPTS)

                    # Clear screen for new art
                    self.console.clear()
                    self._print_header()

                    # Generate and display new art
                    art = self.generate_art(prompt)
                    self.display_art(art, prompt)

                    self.logger.info(f"Generated new art with prompt: {prompt}")
                    last_generation_time = current_time

                time.sleep(0.1)  # Prevent CPU hogging

        except KeyboardInterrupt:
            self.console.print(
                "\nExiting ASCII Art Generator",
                style=self.theme.style(self.theme.NORD9),
                justify="center",
            )
            self.logger.info("Generator stopped by user")


def main():
    """Entry point with error handling."""
    if not os.getenv("OPENAI_API_KEY"):
        console = Console()
        console.print(
            "Error: OPENAI_API_KEY environment variable not set",
            style=Style(color=NordTheme.NORD11),
        )
        sys.exit(1)

    generator = ASCIIArtGenerator()
    try:
        generator.run()
    except Exception as e:
        generator.console.print(
            f"\nError: {str(e)}", style=Style(color=NordTheme.NORD11)
        )
        generator.logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)
    finally:
        generator.console.print("\nGoodbye!", style=Style(color=NordTheme.NORD14))


if __name__ == "__main__":
    main()
