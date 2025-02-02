#!/usr/bin/env python3

"""
ASCII Art Generator
-----------------
A psychedelic ASCII art generator that creates abstract patterns using OpenAI's GPT model.
Features Nord color themes and rich terminal display formatting.
"""

import os
import sys
import time
import random
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Dict, List, Optional

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.spinner import Spinner
from rich.live import Live
from rich import box
from openai import OpenAI

# Load environment variables at startup
load_dotenv()


class ColorTheme:
    """Manages color themes for the ASCII art display."""

    NORD = {
        "frost": ["#8fbcbb", "#88c0d0", "#81a1c1", "#5e81ac"],
        "aurora": ["#bf616a", "#d08770", "#ebcb8b", "#a3be8c", "#b48ead"],
        "polar": ["#2e3440", "#3b4252", "#434c5e", "#4c566a"],
        "snow": ["#d8dee9", "#e5e9f0", "#eceff4"],
    }

    @classmethod
    def get_all_colors(cls) -> List[str]:
        """Returns a flattened list of all colors in the theme."""
        return [color for palette in cls.NORD.values() for color in palette]


class ArtPrompts:
    """Manages the creative elements used in generating art prompts."""

    ABSTRACT_ELEMENTS = [
        "fractals",
        "vortexes",
        "waves",
        "geometric patterns",
        "tessellations",
        "mandalas",
        "spirals",
        "labyrinths",
        "crystalline structures",
        "interference patterns",
        "quantum tunnels",
        "hypercubes",
        "möbius strips",
        "sacred geometry",
        "infinite recursion",
    ]

    ARTISTIC_MODIFIERS = [
        "dissolving into",
        "morphing through",
        "resonating with",
        "flowing through",
        "interweaving with",
        "pulsating between",
        "oscillating through",
        "transcending into",
        "emerging from",
        "folding into",
        "rippling across",
        "fragmenting into",
    ]

    AESTHETIC_STYLES = [
        "cyberdelic",
        "biomechanical",
        "ethereal",
        "quantum",
        "hypnotic",
        "psychedelic",
        "cosmic",
        "interdimensional",
        "holographic",
        "crystalline",
        "fractal",
        "astral",
    ]

    @classmethod
    def generate_concept(cls) -> str:
        """Generates a creative abstract concept combining various artistic elements."""
        patterns = [
            f"A {random.choice(cls.AESTHETIC_STYLES)} dimension where {random.choice(cls.ABSTRACT_ELEMENTS)} "
            f"are {random.choice(cls.ARTISTIC_MODIFIERS)} {random.choice(cls.ABSTRACT_ELEMENTS)}",
            f"{random.choice(cls.ABSTRACT_ELEMENTS).title()} {random.choice(cls.ARTISTIC_MODIFIERS)} "
            f"a {random.choice(cls.AESTHETIC_STYLES)} {random.choice(cls.ABSTRACT_ELEMENTS)}",
            f"Abstract {random.choice(cls.AESTHETIC_STYLES)} patterns of {random.choice(cls.ABSTRACT_ELEMENTS)} "
            f"{random.choice(cls.ARTISTIC_MODIFIERS)} {random.choice(cls.ABSTRACT_ELEMENTS)}",
        ]
        return random.choice(patterns)


class ASCIIArtGenerator:
    """Main class for generating and displaying ASCII art."""

    def __init__(self):
        """Initialize the ASCII art generator with necessary components."""
        self.console = Console()
        self.logger = self._setup_logging()
        self.client = self._setup_openai()
        self.spinner = Spinner("dots2", text="Creating abstract art...")
        self.colors = ColorTheme.get_all_colors()

    def _setup_logging(self) -> logging.Logger:
        """Configure rotating file logger."""
        logger = logging.getLogger("ascii_generator")
        logger.setLevel(logging.INFO)

        handler = RotatingFileHandler(
            "ascii_generator.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )

        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )

        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def _setup_openai(self) -> OpenAI:
        """Initialize OpenAI client with error handling."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            self._exit_with_error("OPENAI_API_KEY not found in environment")
        return OpenAI(api_key=api_key)

    def _exit_with_error(self, message: str) -> None:
        """Handle fatal errors and exit gracefully."""
        self.console.print(f"[red]Error: {message}[/red]")
        self.logger.error(message)
        sys.exit(1)

    def _create_gpt_prompt(self, concept: str) -> str:
        """Generate an art prompt using GPT model."""
        try:
            response = self.client.chat.completions.create(
                model="chatgpt-4o-latest",
                messages=[
                    {
                        "role": "system",
                        "content": """Create abstract ASCII art prompts that emphasize patterns, 
                        textures, and geometric forms. Focus on non-representational concepts 
                        that work well with ASCII characters. Respond with only the prompt.""",
                    },
                    {
                        "role": "user",
                        "content": f"Transform into ASCII art prompt: {concept}",
                    },
                ],
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            self.logger.error(f"Prompt generation error: {e}")
            return concept

    def _generate_art(self, prompt: str) -> str:
        """Generate ASCII art based on the prompt."""
        try:
            response = self.client.chat.completions.create(
                model="chatgpt-4o-latest",
                messages=[
                    {
                        "role": "system",
                        "content": """Create abstract ASCII art (chars 32-126) focusing on:
                        - Complex geometric patterns and textures
                        - Recursive and fractal-like structures
                        - Balanced negative space and visual flow
                        No emojis or words. Format with triple backticks.""",
                    },
                    {"role": "user", "content": f"Create abstract ASCII art: {prompt}"},
                ],
            )
            return response.choices[0].message.content.replace("```", "").strip()
        except Exception as e:
            self.logger.error(f"Art generation error: {e}")
            return "∞≈≋≋∞≈≋≋∞≈≋≋∞"

    def _apply_colors(self, art: str) -> str:
        """Apply random Nord colors to the ASCII art."""
        return "\n".join(
            f"[{random.choice(self.colors)}]{line}[/]" if line.strip() else line
            for line in art.splitlines()
        )

    def _display_art(self, art: str, prompt: str) -> None:
        """Display the ASCII art in a styled panel."""
        colored_art = self._apply_colors(art)
        title = f"・。゜☆。。{prompt}。。☆゜。・"

        panel = Panel(
            colored_art,
            title=title,
            title_align="center",
            box=box.DOUBLE,
            expand=True,
            padding=(1, 2),
            border_style="cyan",
        )

        # Ensure proper alignment by clearing and using full width
        self.console.clear()
        self.console.print(panel)

    def run(self) -> None:
        """Main execution loop for generating and displaying art."""
        # Setup initial display
        width = self.console.width
        title = "✧༺ Psychedelic ASCII Art Generator ༻✧"
        self.console.print("\n" + f"[bold cyan]{title:^{width}}[/bold cyan]")
        self.console.print(f"[dim]Press Ctrl+C to exit[/dim]".center(width))
        self.console.print()

        try:
            while True:
                with Live(self.spinner, refresh_per_second=20):
                    concept = ArtPrompts.generate_concept()
                    prompt = self._create_gpt_prompt(concept)
                    self.logger.info(f"Generated prompt: {prompt}")
                    art = self._generate_art(prompt)

                self._display_art(art, prompt)
                self.logger.info("Art displayed successfully")
                time.sleep(15)

        except KeyboardInterrupt:
            farewell = "✧ Thanks for experiencing the abstract ASCII realm! ✧"
            self.console.print(f"\n[bold cyan]{farewell:^{width}}[/bold cyan]")
            sys.exit(0)


def main():
    """Entry point for the ASCII art generator."""
    try:
        generator = ASCIIArtGenerator()
        generator.run()
    except Exception as e:
        console = Console()
        console.print(f"[red]Fatal error: {str(e)}[/red]")
        logging.getLogger("ascii_generator").exception("Fatal error occurred")
        sys.exit(1)


if __name__ == "__main__":
    main()
