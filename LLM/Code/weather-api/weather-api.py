#!/usr/bin/env python3
"""
weather-api.py

An interactive CLI/TUI application (Typer + Curses + Rich) that fetches
current weather data from OpenWeatherMap, leveraging an API key stored
in a .env file.

Features:
    1. Default to TUI if no subcommand is given.
    2. `tui` subcommand explicitly launches curses-based TUI.
    3. `get-weather` subcommand for CLI usage with Rich formatting.

Requirements:
    - Python 3.8+
    - pip install typer python-dotenv requests rich
"""

import os
import sys
import time
import curses
import requests
import typer

from typing import Any, Dict
from dotenv import load_dotenv
from rich.console import Console
from rich import print as rprint

###############################################################################
# Load Environment & Setup Constants
###############################################################################

load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "No OpenWeatherMap API key found. "
        "Please set OPENWEATHER_API_KEY in your .env file."
    )

BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

###############################################################################
# Typer & Rich Setup
###############################################################################

# Typer app for CLI commands
app = typer.Typer(help="A CLI/TUI to fetch and display weather information.")

# Rich console for CLI mode output
console = Console()

###############################################################################
# Weather Fetching & Formatting
###############################################################################


def fetch_weather(city: str, api_key: str) -> Dict[str, Any]:
    """
    Fetch current weather data for a given city from OpenWeatherMap.

    :param city: Name of the city to fetch the weather for.
    :param api_key: Your OpenWeatherMap API key.
    :return: A dictionary containing weather information.
    :raises requests.RequestException: For any network-related errors.
    :raises ValueError: If the response data is missing expected fields.
    """
    params = {
        "q": city,
        "appid": api_key,
        "units": "metric",  # Use "imperial" for Fahrenheit
    }
    response = requests.get(BASE_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    # Basic validation to ensure required fields exist
    if "main" not in data or "weather" not in data:
        raise ValueError("Unexpected response format from OpenWeatherMap API.")

    return data


def format_weather_output(data: Dict[str, Any]) -> str:
    """
    Format the JSON response from OpenWeatherMap into a user-friendly string.

    :param data: Parsed JSON dictionary from the API response.
    :return: A formatted string of weather information.
    """
    city_name = data.get("name", "Unknown City")
    main_info = data.get("main", {})
    weather_info = data.get("weather", [{}])[0]

    temp = main_info.get("temp", "N/A")
    feels_like = main_info.get("feels_like", "N/A")
    humidity = main_info.get("humidity", "N/A")
    description = weather_info.get("description", "N/A").title()

    output = (
        f"[bold white]City:[/bold white] {city_name}\n"
        f"[bold white]Temperature:[/bold white] {temp} °C\n"
        f"[bold white]Feels Like:[/bold white] {feels_like} °C\n"
        f"[bold white]Humidity:[/bold white] {humidity}%\n"
        f"[bold white]Condition:[/bold white] {description}"
    )
    return output


###############################################################################
# CLI Commands
###############################################################################


@app.command("get-weather")
def get_weather(
    city: str = typer.Option(
        None,
        "--city",
        "-c",
        help="City name to fetch weather for. If omitted, a prompt appears.",
        prompt="Please enter a city name",
    )
) -> None:
    """
    Fetch and display current weather information for a specified city.
    """
    try:
        weather_data = fetch_weather(city, API_KEY)
        # Print using Rich to provide colorful, formatted output
        console.print(format_weather_output(weather_data), style="green")
    except requests.RequestException as req_exc:
        console.print(f"[red]Network error:[/red] {req_exc}", style="red")
    except ValueError as val_exc:
        console.print(f"[red]Data error:[/red] {val_exc}", style="red")
    except Exception as exc:
        console.print(f"[red]Unexpected error:[/red] {exc}", style="red")


@app.command("tui")
def launch_tui() -> None:
    """
    Explicitly launch the curses-based TUI.
    """
    curses.wrapper(run_tui)


###############################################################################
# TUI Implementation (Curses)
###############################################################################


def run_tui(stdscr: "curses._CursesWindow") -> None:
    """
    The main TUI function that initializes curses settings, handles user input,
    and updates the screen to fetch/display weather data in an interactive way.
    """

    # Basic curses setup
    curses.curs_set(0)  # Hide cursor
    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)

    # Main loop instructions
    instructions = "Weather TUI Controls:\n" " [g] to GET weather\n" " [q] to QUIT"

    def refresh_screen(selected_city: str = "", weather_output: str = ""):
        """Clear and redraw the screen with updated content."""
        stdscr.clear()
        # Title
        title = "Weather TUI"
        stdscr.addstr(0, 2, title, curses.color_pair(1) | curses.A_BOLD)

        # Instructions
        for i, line in enumerate(instructions.splitlines(), start=2):
            stdscr.addstr(i, 2, line)

        if selected_city:
            stdscr.addstr(6, 2, f"Selected City: {selected_city}", curses.color_pair(2))

        if weather_output:
            # Print weather output starting a few lines down
            output_lines = weather_output.split("\n")
            row_offset = 8
            for idx, line in enumerate(output_lines):
                stdscr.addstr(row_offset + idx, 2, line)

        stdscr.refresh()

    # Initial screen draw
    refresh_screen()

    # Main TUI loop
    while True:
        key = stdscr.getch()

        if key == ord("q"):
            # Quit TUI
            break

        elif key == ord("g"):
            # Prompt user for city name in curses
            curses.echo()
            stdscr.addstr(6, 2, "Enter city: ", curses.color_pair(2))
            stdscr.clrtoeol()
            stdscr.refresh()

            # Read city input
            city_input = stdscr.getstr(6, 14, 50)  # max 50 chars
            city_name = city_input.decode("utf-8").strip()
            curses.noecho()

            # Fetch weather
            try:
                weather_data = fetch_weather(city_name, API_KEY)
                weather_rich_str = format_weather_output(weather_data)
                # Convert Rich markup to plain text for curses display
                # or show only textual content in TUI
                # For simplicity, just remove Rich tags:
                # (In production, you might parse or colorize further within curses.)
                weather_plain_str = remove_rich_tags(weather_rich_str)
                refresh_screen(
                    selected_city=city_name, weather_output=weather_plain_str
                )

            except requests.RequestException as req_exc:
                error_message = f"Network error: {req_exc}"
                show_error(stdscr, error_message)
            except ValueError as val_exc:
                error_message = f"Data error: {val_exc}"
                show_error(stdscr, error_message)
            except Exception as exc:
                error_message = f"Unexpected error: {exc}"
                show_error(stdscr, error_message)

        # Update screen if needed
        refresh_screen()


def show_error(stdscr: "curses._CursesWindow", message: str) -> None:
    """
    Displays an error message at the bottom of the TUI.
    """
    stdscr.addstr(
        curses.LINES - 1,
        2,
        f"Error: {message} (Press any key to continue)",
        curses.color_pair(3),
    )
    stdscr.getch()  # Wait for user input
    # Clear error line
    stdscr.move(curses.LINES - 1, 0)
    stdscr.clrtoeol()


def remove_rich_tags(text: str) -> str:
    """
    Naive utility to remove Rich markup tags for displaying in curses.
    This is simple and won't handle all edge cases for Rich syntax.
    """
    import re

    # Remove anything in square brackets [like this]
    return re.sub(r"\[.*?\]", "", text)


###############################################################################
# Main Entry Point
###############################################################################


def main():
    """
    Main entry point:
      - Launches TUI if no arguments are passed.
      - Otherwise, runs Typer for CLI commands.
    """
    if len(sys.argv) == 1:
        curses.wrapper(run_tui)
    else:
        app()


if __name__ == "__main__":
    main()
