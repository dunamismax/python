#!/usr/bin/env python3
"""
ASCII Art Generator
-------------------
A simple ASCII art generator that uses OpenAI's GPT model to create art.
A spinner from Rich is shown for 10 seconds (the configured pause) while the art is generated.
"""

import os
import sys
import time
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner

from openai import OpenAI

# Load environment variables
load_dotenv()

# Configuration: pause duration (in seconds) between ASCII art generations
GENERATION_PAUSE = 10


class ASCIIArtGenerator:
    """Main class for generating and displaying ASCII art."""

    def __init__(self):
        self.console = Console()
        self.logger = self._setup_logging()
        self.client = self._setup_openai()
        self.spinner = Spinner("dots", text="Generating ASCII art...")

    def _setup_logging(self) -> logging.Logger:
        """Configure a rotating file logger."""
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
        self.console.print(f"Error: {message}")
        self.logger.error(message)
        sys.exit(1)

    def _generate_art(self, prompt: str) -> str:
        """Generate ASCII art based on a fixed prompt."""
        try:
            response = self.client.chat.completions.create(
                model="chatgpt-4o-latest",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Create ASCII art using characters only. "
                            "Do not include extra text or formatting markers."
                        ),
                    },
                    {"role": "user", "content": f"{prompt}"},
                ],
            )
            # Remove any triple backticks if present and return a clean result.
            art = response.choices[0].message.content.replace("```", "").strip()
            return art
        except Exception as e:
            self.logger.error(f"Art generation error: {e}")
            return "Error generating art."

    def _display_art(self, art: str, prompt: str) -> None:
        """Clear the terminal and output the ASCII art along with the prompt."""
        self.console.clear()
        # Output the art and the prompt in a clean format.
        self.console.print(art)
        self.console.print(f"\nPrompt used: {prompt}")
        # Also log the output for record keeping.
        self.logger.info("ASCII Art generated:")
        self.logger.info(art)
        self.logger.info(f"Prompt: {prompt}")

    def run(self) -> None:
        """Main execution loop for generating and displaying art."""
        self.console.print("ASCII Art Generator")
        self.console.print("Press Ctrl+C to exit.")
        fixed_prompt = "Create abstract ASCII art using ASCII characters only."
        try:
            while True:
                # Show spinner for the configured pause duration
                with Live(
                    self.spinner,
                    console=self.console,
                    refresh_per_second=10,
                    transient=True,
                ):
                    time.sleep(GENERATION_PAUSE)
                # Generate art using the fixed prompt
                art = self._generate_art(fixed_prompt)
                self._display_art(art, fixed_prompt)
                time.sleep(GENERATION_PAUSE)
        except KeyboardInterrupt:
            self.console.print("Exiting ASCII Art Generator.")
            sys.exit(0)


def main():
    try:
        generator = ASCIIArtGenerator()
        generator.run()
    except Exception as e:
        Console().print(f"Fatal error: {str(e)}")
        logging.getLogger("ascii_generator").exception("Fatal error occurred")
        sys.exit(1)


if __name__ == "__main__":
    main()
