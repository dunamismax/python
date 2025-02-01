#!/usr/bin/env python3
"""
dunamismax ai ascii generator

This application continuously generates unique ASCII art images using OpenAI's API.
The user is prompted to select the AI model and pause duration between generations.
The generated art is displayed along with a live loading indicator for the chosen pause period.
If interrupted (Ctrl+C), the user is given an option to return to the main menu or quit.
The application leverages the Rich library for an enhanced CLI experience.
"""

import os
import sys
import time
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from rich.console import Console, Group
from rich.theme import Theme
from rich.prompt import Prompt
from rich.spinner import Spinner
from rich.live import Live
from rich.panel import Panel

# Load environment variables from .env file
load_dotenv()

# Define a Nord-inspired theme and apply it globally
nord_theme = Theme(
    {"info": "#88C0D0", "warning": "#EBCB8B", "error": "#BF616A", "header": "#81A1C1"}
)
console = Console(theme=nord_theme, width=100)


# Set up a rotating logger to record application events
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

# Verify the OpenAI API key is set
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    console.print("[error]Error: OPENAI_API_KEY not found in environment.[/error]")
    logger.error("OPENAI_API_KEY not found in environment. Exiting.")
    sys.exit(1)

# Import and instantiate the OpenAI client
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

# Define available models and pause options
AVAILABLE_MODELS = [
    "o3-mini",
    "chatgpt-4o-latest",
    "gpt-4o-mini",
    "o1-mini",
    "o1",
    "gpt-4o",
]
PAUSE_OPTIONS = [3, 5, 10, 15, 30, 60, 180, 360]


# Display a persistent header at the top of the CLI
def display_header():
    header_text = "dunamismax ai ascii generator"
    # Using a Panel to display the header aligned to the left
    header_panel = Panel(
        header_text,
        style="header",
        padding=(0, 1),
        title="",
        border_style="header",
        expand=False,
    )
    console.print(header_panel, justify="left")


# Prompt the user to select an AI model from the available list
def select_model():
    console.print("\n[bold green]Select a model:[/bold green]")
    for index, model in enumerate(AVAILABLE_MODELS, start=1):
        console.print(f"{index}. {model}", style="info")
    choice = Prompt.ask(
        "Enter the number of your chosen model",
        choices=[str(i) for i in range(1, len(AVAILABLE_MODELS) + 1)],
    )
    return AVAILABLE_MODELS[int(choice) - 1]


# Prompt the user to select the pause duration (in seconds) between art generations
def select_pause_duration():
    console.print(
        "\n[bold green]Select pause duration between art generations (in seconds):[/bold green]"
    )
    for index, seconds in enumerate(PAUSE_OPTIONS, start=1):
        console.print(f"{index}. {seconds} seconds", style="info")
    choice = Prompt.ask(
        "Enter the number of your choice",
        choices=[str(i) for i in range(1, len(PAUSE_OPTIONS) + 1)],
    )
    return PAUSE_OPTIONS[int(choice) - 1]


# Request the AI to generate a creative prompt for ASCII art with full creative freedom
def get_random_ascii_prompt(model):
    request_text = (
        "Generate a prompt that instructs an AI to create a unique ASCII art image. "
        "The prompt should allow for complete creative freedom in style, theme, and genre, "
        "covering any subject matter or artistic method. For example, it might say "
        "'Create a surreal ASCII art image' or 'Generate an abstract ASCII art depiction of a dreamlike landscape'. "
        "Output only the prompt text with no additional commentary or confirmation."
    )
    try:
        with console.status(
            "[bold green]Generating art prompt...[/bold green]", spinner="dots"
        ):
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": request_text}],
                stream=False,
            )
    except Exception as e:
        logger.exception("Error generating ASCII art prompt")
        return "Create a surreal ASCII art image"
    ascii_prompt = response.choices[0].message.content or ""
    return ascii_prompt.strip()


# Request the AI to generate ASCII art using the provided prompt
def get_ascii_art(model, prompt):
    try:
        with console.status(
            "[bold green]Generating ASCII art...[/bold green]", spinner="dots"
        ):
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                stream=False,
            )
    except Exception as e:
        logger.exception("Error generating ASCII art")
        return "Error generating ASCII art."
    ascii_art = response.choices[0].message.content or ""
    return ascii_art.strip()


# Display the generated art along with a continuously updating loading indicator
def display_art_with_loading(art, pause_duration):
    console.clear()
    display_header()
    # Group the static art and the dynamic loading spinner using Rich's Group
    group = Group(
        Panel(art, border_style="info", title="Generated ASCII Art", padding=(1, 2)),
        Spinner("dots", text="Loading..."),
    )
    # Live updates the display while the spinner animates during the pause period
    with Live(group, console=console, refresh_per_second=10):
        time.sleep(pause_duration)


# Prompt the user after a KeyboardInterrupt whether to return to the main menu or quit
def prompt_exit_or_menu():
    choice = Prompt.ask(
        "Return to main menu or quit? (m/q)", choices=["m", "q"], default="m"
    )
    return choice


# Main execution loop
def main():
    # Initial interactive configuration
    display_header()
    selected_model = select_model()
    selected_pause = select_pause_duration()
    # Main loop for continuous ASCII art generation
    while True:
        try:
            base_prompt = get_random_ascii_prompt(selected_model)
            logger.info("Generated art prompt: %s", base_prompt)
            final_prompt = (
                "When you generate the ASCII, output only the art with no additional text or commentary. "
                + base_prompt
            )
            art = get_ascii_art(selected_model, final_prompt)
            logger.info("ASCII art generated (truncated): %s", art[:100])
            display_art_with_loading(art, selected_pause)
        except KeyboardInterrupt:
            console.print("\n[info]Interrupt detected.[/info]")
            # Ask user if they want to return to main menu or quit upon interruption
            user_choice = prompt_exit_or_menu()
            if user_choice == "q":
                console.print("\n[info]Exiting...[/info]")
                logger.info("User chose to quit.")
                sys.exit(0)
            else:
                console.print("\n[info]Returning to main menu...[/info]")
                # Re-prompt for model and pause duration
                selected_model = select_model()
                selected_pause = select_pause_duration()
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
