#!/usr/bin/env python3
"""
weather_api.py

An interactive CLI/TUI application (Typer + Curses + Rich) that fetches
current weather data from OpenWeatherMap, leveraging an API key stored
in a .env file.

Features:
    1. Default to TUI if no subcommand is given.
    2. `tui` subcommand explicitly launches curses-based TUI.
    3. `get-weather` subcommand for CLI usage with Rich formatting.

Press 'g' in TUI to enter city/zip; press Enter to fetch weather.
Press 'q' to quit TUI.

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

from datetime import datetime
from typing import Any, Dict
from dotenv import load_dotenv
from rich.console import Console

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

app = typer.Typer(help="A CLI/TUI to fetch and display weather information.")
console = Console()

###############################################################################
# Weather Fetching & Formatting
###############################################################################


def fetch_weather(location: str, api_key: str) -> Dict[str, Any]:
    """
    Fetch current weather data from OpenWeatherMap using either city name
    or ZIP code. Zip codes default to US (e.g. 33948,us).
    """
    if location.isdigit():
        params = {
            "zip": f"{location},us",
            "appid": api_key,
            "units": "imperial",  # Use imperial units (F, mph)
        }
    else:
        params = {
            "q": location,
            "appid": api_key,
            "units": "imperial",  # Use imperial units (F, mph)
        }

    response = requests.get(BASE_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    if "main" not in data or "weather" not in data:
        raise ValueError("Unexpected response format from OpenWeatherMap API.")

    return data


def format_weather_output(data: Dict[str, Any]) -> str:
    """
    Format the JSON response from OpenWeatherMap into a Rich-friendly string
    for CLI usage or for TUI display (after removing Rich tags).
    """
    city_name = data.get("name", "Unknown City")
    main_info = data.get("main", {})
    weather_info = data.get("weather", [{}])[0]
    wind_info = data.get("wind", {})
    sys_info = data.get("sys", {})

    # Main weather data
    temp = main_info.get("temp", "N/A")
    feels_like = main_info.get("feels_like", "N/A")
    temp_min = main_info.get("temp_min", "N/A")
    temp_max = main_info.get("temp_max", "N/A")
    pressure = main_info.get("pressure", "N/A")
    humidity = main_info.get("humidity", "N/A")

    # Description and wind
    description = weather_info.get("description", "N/A").title()
    wind_speed = wind_info.get("speed", "N/A")  # mph
    wind_gust = wind_info.get("gust", "N/A")

    # Visibility (convert meters to miles if available)
    visibility_meters = data.get("visibility", "N/A")
    if visibility_meters != "N/A":
        visibility_miles = round(visibility_meters / 1609.34, 2)
    else:
        visibility_miles = "N/A"

    # Cloudiness
    cloudiness = data.get("clouds", {}).get("all", "N/A")

    # Convert sunrise/sunset from UNIX to local time
    sunrise_unix = sys_info.get("sunrise")
    sunset_unix = sys_info.get("sunset")
    timezone_offset = data.get("timezone", 0)
    sunrise_str = _format_unix_time(sunrise_unix, timezone_offset)
    sunset_str = _format_unix_time(sunset_unix, timezone_offset)

    # Build Rich output
    output = (
        f"[bold magenta]City:[/bold magenta] [yellow]{city_name}[/yellow]\n"
        f"[bold white]Temperature:[/bold white] {temp} °F\n"
        f"[bold white]Feels Like:[/bold white] {feels_like} °F\n"
        f"[bold white]Min Temp:[/bold white] {temp_min} °F\n"
        f"[bold white]Max Temp:[/bold white] {temp_max} °F\n"
        f"[bold white]Pressure:[/bold white] {pressure} hPa\n"
        f"[bold white]Humidity:[/bold white] {humidity}%\n"
        f"[bold white]Condition:[/bold white] {description}\n"
        f"[bold white]Wind Speed:[/bold white] {wind_speed} mph\n"
        f"[bold white]Wind Gust:[/bold white] {wind_gust if wind_gust != 'N/A' else 'N/A'} mph\n"
        f"[bold white]Visibility:[/bold white] {visibility_miles} miles\n"
        f"[bold white]Cloudiness:[/bold white] {cloudiness}%\n"
        f"[bold white]Sunrise:[/bold white] {sunrise_str}\n"
        f"[bold white]Sunset:[/bold white] {sunset_str}"
    )
    return output


def _format_unix_time(unix_time: Any, timezone_offset: int) -> str:
    if not unix_time:
        return "N/A"
    local_ts = unix_time + timezone_offset
    local_time = datetime.utcfromtimestamp(local_ts)
    return local_time.strftime("%Y-%m-%d %H:%M:%S")


###############################################################################
# CLI Commands
###############################################################################


@app.command("get-weather")
def get_weather(
    location: str = typer.Option(
        None,
        "--location",
        "-l",
        help="City name or ZIP code to fetch weather for. If omitted, a prompt appears.",
        prompt="Please enter a city name or zip code",
    )
) -> None:
    """
    Fetch and display current weather information for a specified location
    (either a city or a zip code).
    """
    try:
        weather_data = fetch_weather(location, API_KEY)
        console.print(format_weather_output(weather_data))
    except requests.RequestException as req_exc:
        console.print(f"[red]Network error:[/red] {req_exc}")
    except ValueError as val_exc:
        console.print(f"[red]Data error:[/red] {val_exc}")
    except Exception as exc:
        console.print(f"[red]Unexpected error:[/red] {exc}")


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
    The main TUI function: initializes curses, handles user input, and
    fetches/displays weather data.
    """
    curses.curs_set(0)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)

    instructions = (
        "Weather TUI Controls:\n"
        " [g] to GET weather (enter city or zip)\n"
        " [q] to QUIT"
    )

    def refresh_screen(selected_location: str = "", weather_output: str = ""):
        stdscr.clear()
        title = "Weather TUI"
        stdscr.addstr(0, 2, title, curses.color_pair(1) | curses.A_BOLD)

        # Instructions
        lines = instructions.splitlines()
        for i, line in enumerate(lines, start=2):
            stdscr.addstr(i, 2, line)

        if selected_location:
            stdscr.addstr(
                6, 2, f"Last query: {selected_location}", curses.color_pair(2)
            )

        # Weather content
        if weather_output:
            output_lines = weather_output.split("\n")
            row_offset = 8
            for idx, line in enumerate(output_lines):
                stdscr.addstr(row_offset + idx, 2, line)

        stdscr.refresh()

    # Initial screen
    refresh_screen()

    while True:
        key = stdscr.getch()
        if key == ord("q"):
            break  # Quit TUI

        elif key == ord("g"):
            # Prompt user for location
            curses.echo()
            stdscr.addstr(6, 2, "Enter city or zip: ", curses.color_pair(2))
            stdscr.clrtoeol()
            stdscr.refresh()

            location_input = stdscr.getstr(6, 22, 50)
            location = location_input.decode("utf-8").strip()
            curses.noecho()

            # Clear old weather output lines
            weather_plain_str = ""
            try:
                weather_data = fetch_weather(location, API_KEY)
                weather_rich_str = format_weather_output(weather_data)
                weather_plain_str = remove_rich_tags(weather_rich_str)
            except requests.RequestException as req_exc:
                weather_plain_str = f"Network error: {req_exc}"
            except ValueError as val_exc:
                weather_plain_str = f"Data error: {val_exc}"
            except Exception as exc:
                weather_plain_str = f"Unexpected error: {exc}"

            refresh_screen(selected_location=location, weather_output=weather_plain_str)

        else:
            refresh_screen()


def show_error(stdscr: "curses._CursesWindow", message: str) -> None:
    stdscr.addstr(
        curses.LINES - 1,
        2,
        f"Error: {message} (Press any key to continue)",
        curses.color_pair(3),
    )
    stdscr.getch()
    stdscr.move(curses.LINES - 1, 0)
    stdscr.clrtoeol()


def remove_rich_tags(text: str) -> str:
    """
    Naive utility to remove Rich markup tags for displaying in curses.
    This is simple and won't handle all edge cases for Rich syntax.
    """
    import re

    return re.sub(r"\[.*?\]", "", text)


###############################################################################
# Main Entry Point
###############################################################################


def main():
    if len(sys.argv) == 1:
        curses.wrapper(run_tui)
    else:
        app()


if __name__ == "__main__":
    main()
