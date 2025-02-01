#!/usr/bin/env python3
import os
import sys
import time
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from rich.console import Console
from rich.theme import Theme

load_dotenv()
nord_theme = Theme({"info": "#88C0D0", "warning": "#EBCB8B", "error": "#BF616A"})
console = Console(theme=nord_theme, width=100)


def setup_logger():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(script_dir, "chat_history.log")
    logger = logging.getLogger("ascii_art_generator")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


logger = setup_logger()
logger.info("=== Application started ===")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    console.print("[error]Error: OPENAI_API_KEY not found in environment.[/error]")
    logger.error("OPENAI_API_KEY not found in environment. Exiting.")
    sys.exit(1)

try:
    from openai import OpenAI
except ImportError as e:
    console.print(f"[error]Error importing OpenAI client: {e}[/error]")
    logger.exception("Error importing OpenAI client")
    sys.exit(1)

try:
    client = OpenAI(api_key=OPENAI_API_KEY)
except Exception as e:
    console.print(f"[error]Failed to instantiate OpenAI client: {e}[/error]")
    logger.exception("Failed to instantiate OpenAI client")
    sys.exit(1)


def get_random_ascii_prompt():
    request_text = (
        "Generate a prompt that instructs an AI to create a unique ASCII art image. "
        "The prompt should allow for complete creative freedom in style, theme, and genre, "
        "covering any subject matter or artistic method. "
        "For example, it might say 'Create a surreal ASCII art image' or "
        "'Generate an abstract ASCII art depiction of a dreamlike landscape'. "
        "Output only the prompt text with no additional commentary or confirmation."
    )
    try:
        with console.status(
            "[bold green]Generating art prompt...[/bold green]", spinner="dots"
        ):
            response = client.chat.completions.create(
                model="chatgpt-4o-latest",
                messages=[{"role": "user", "content": request_text}],
                stream=False,
            )
    except Exception as e:
        logger.exception("Error generating ASCII art prompt")
        return "Create a surreal ASCII art image"
    ascii_prompt = response.choices[0].message.content or ""
    return ascii_prompt.strip()


def get_ascii_art(prompt):
    try:
        with console.status(
            "[bold green]Generating ASCII art...[/bold green]", spinner="dots"
        ):
            response = client.chat.completions.create(
                model="chatgpt-4o-latest",
                messages=[{"role": "user", "content": prompt}],
                stream=False,
            )
    except Exception as e:
        logger.exception("Error generating ASCII art")
        return "Error generating ASCII art."
    ascii_art = response.choices[0].message.content or ""
    return ascii_art.strip()


def print_ascii_art(art):
    console.clear()
    console.print(art)


def main():
    while True:
        try:
            base_prompt = get_random_ascii_prompt()
            logger.info("Generated art prompt: %s", base_prompt)
            final_prompt = (
                "When you generate the ASCII, output only the art with no additional text or commentary. "
                + base_prompt
            )
            art = get_ascii_art(final_prompt)
            logger.info("ASCII art generated (truncated): %s", art[:100])
            print_ascii_art(art)
            with console.status("[bold green]Loading...[/bold green]", spinner="dots"):
                time.sleep(10)
        except KeyboardInterrupt:
            console.print("\n[info]Exiting...[/info]")
            logger.info("Application terminated by KeyboardInterrupt.")
            break
        except Exception as e:
            console.print(f"[error]Unexpected error: {e}[/error]")
            logger.exception("Unexpected error in main loop.")
            time.sleep(5)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        console.print(f"[error]A fatal error occurred: {e}[/error]")
        logger.exception("A fatal error occurred in the main loop.")
    finally:
        logger.info("=== Application terminated ===")
