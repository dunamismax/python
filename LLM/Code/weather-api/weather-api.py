"""
weather-api.py

A production-ready TUI (Textual) application that fetches current weather data
from OpenWeatherMap, using an API key stored in a .env file.

Requirements:
    - Python 3.8+
    - `pip install textual python-dotenv requests`

Usage:
    $ python weather-api.py
"""

import os
import requests

from dotenv import load_dotenv
from typing import Any, Dict, Optional

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Header, Footer, Input, Static, Button, Label
from textual import events

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
# Utility Function to Fetch Weather
###############################################################################


def fetch_weather(city: str, api_key: str) -> Dict[str, Any]:
    """
    Fetch current weather data for a given city from OpenWeatherMap.

    :param city: Name of the city to fetch the weather for.
    :param api_key: Your OpenWeatherMap API key.
    :return: A dictionary containing weather information.
    :raises: requests.RequestException, ValueError
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


###############################################################################
# Textual App
###############################################################################


class WeatherApp(App):
    """
    A Textual TUI application to fetch and display weather information
    from the OpenWeatherMap API.
    """

    CSS_PATH = None  # We can set a custom CSS file path if desired

    def compose(self) -> ComposeResult:
        """
        Build and layout the TUI interface. Called automatically by Textual.
        """
        # Header & Footer provide default frames
        yield Header(show_clock=True)
        yield Container(
            Label("Enter City Name:", id="city_label"),
            Input(placeholder="City...", id="city_input"),
            Button("Get Weather", id="weather_button"),
            Static("Weather details will appear here.", id="weather_output"),
        )
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Event handler for button presses. Triggers a weather fetch for the
        city specified in the Input widget.
        """
        if event.button.id == "weather_button":
            city_input = self.query_one("#city_input", Input).value.strip()
            output_widget = self.query_one("#weather_output", Static)

            if not city_input:
                output_widget.update(
                    "[b red]Error:[/b red] Please enter a valid city name."
                )
                return

            try:
                weather_data = fetch_weather(city_input, API_KEY)
                formatted_weather = self._format_weather_output(weather_data)
                output_widget.update(formatted_weather)
            except requests.RequestException as req_exc:
                output_widget.update(f"[b red]Network error:[/b red] {req_exc}")
            except ValueError as val_exc:
                output_widget.update(f"[b red]Data error:[/b red] {val_exc}")
            except Exception as exc:
                output_widget.update(f"[b red]Unexpected error:[/b red] {exc}")

    def _format_weather_output(self, data: Dict[str, Any]) -> str:
        """
        Format the JSON response from OpenWeatherMap into a user-friendly string.
        """
        city_name = data.get("name", "Unknown City")
        main_info = data.get("main", {})
        weather_info = data.get("weather", [{}])[0]

        temp = main_info.get("temp", "N/A")
        feels_like = main_info.get("feels_like", "N/A")
        humidity = main_info.get("humidity", "N/A")
        description = weather_info.get("description", "N/A").title()

        return (
            f"[b]City:[/b] {city_name}\n"
            f"[b]Temperature:[/b] {temp} °C\n"
            f"[b]Feels Like:[/b] {feels_like} °C\n"
            f"[b]Humidity:[/b] {humidity}%\n"
            f"[b]Condition:[/b] {description}"
        )


###############################################################################
# Main Entry Point
###############################################################################

if __name__ == "__main__":
    # This starts the Textual app
    WeatherApp().run()
