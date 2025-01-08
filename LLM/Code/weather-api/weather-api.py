#!/usr/bin/env python3
"""
weather-api.py

A production-ready interactive CLI application (using Typer) that fetches
current weather data from OpenWeatherMap, leveraging an API key stored
in a .env file.

Requirements:
    - Python 3.8+
    - pip install typer python-dotenv requests

Usage:
    # Display available commands
    $ python weather-api.py --help

    # Prompt for city name and retrieve weather
    $ python weather-api.py get-weather

    # Or specify the city directly
    $ python weather-api.py get-weather --city "London"
"""

import os
import requests
import typer

from dotenv import load_dotenv
from typing import Any, Dict

###############################################################################
# Load Environment & Setup Constants
###############################################################################

load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "No OpenWeatherMap API key found. Please set OPENWEATHER_API_KEY in your .env file."
    )

BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

###############################################################################
# Typer Application
###############################################################################

app = typer.Typer(help="A CLI to fetch and display weather information.")


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

    return (
        f"\nCity: {city_name}\n"
        f"Temperature: {temp} °C\n"
        f"Feels Like: {feels_like} °C\n"
        f"Humidity: {humidity}%\n"
        f"Condition: {description}\n"
    )


@app.command("get-weather")
def get_weather(
    city: str = typer.Option(
        None,
        "--city",
        "-c",
        help="City name to fetch weather for. If omitted, a prompt will appear.",
        prompt="Please enter a city name",
    )
) -> None:
    """
    Fetch and display current weather information for a specified city.
    """
    try:
        weather_data = fetch_weather(city, API_KEY)
        typer.secho(format_weather_output(weather_data), fg=typer.colors.GREEN)
    except requests.RequestException as req_exc:
        typer.secho(f"Network error: {req_exc}", fg=typer.colors.RED, err=True)
    except ValueError as val_exc:
        typer.secho(f"Data error: {val_exc}", fg=typer.colors.RED, err=True)
    except Exception as exc:
        typer.secho(f"Unexpected error: {exc}", fg=typer.colors.RED, err=True)


if __name__ == "__main__":
    app()
