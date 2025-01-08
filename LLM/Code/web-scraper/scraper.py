#!/usr/bin/env python3
"""
A dual-mode subpage scraper. Demonstrates:
- TUI (curses-based) vs. CLI (Typer + Rich)
- Basic HTTP GET using 'requests'
- HTML parsing with 'BeautifulSoup'
- Logging and error handling
- Concurrency using asyncio.to_thread
- Rich-based colorful output for the CLI
- Curses-based interactive UI for TUI mode

Usage:
    1. Install dependencies:
       pip install requests beautifulsoup4 typer[all] rich

    2. Run the script:
       python scraper.py       # Launches TUI by default
       python scraper.py tui   # Also launches TUI
       python scraper.py scrape  # Runs CLI subcommand

Example flow in TUI mode:
    - Press 's' to start scraping (enter URL).
    - Press 'q' at any point to quit.
"""

import sys
import logging
import asyncio
import requests
import curses
import typer

from typing import List
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table


###############################################################################
# Logging Configuration
###############################################################################
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


###############################################################################
# Scraping Logic
###############################################################################
def scrape_subpages(url: str) -> List[str]:
    """
    Given a URL, retrieve the HTML content and extract all unique subpages
    belonging to the same domain (base URL).

    Args:
        url (str): The target URL to scrape.

    Returns:
        List[str]: A sorted list of absolute URLs referencing subpages.
    """
    logging.info("Starting subpage discovery for URL: %s", url)

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        logging.error("Request failed: %s", exc)
        raise ValueError(f"Failed to retrieve content from {url}") from exc

    soup = BeautifulSoup(response.text, "html.parser")
    subpages = set()
    base_domain = urlparse(url).netloc

    for link_tag in soup.find_all("a", href=True):
        href = link_tag["href"].strip()
        # Convert relative path to absolute URL, and keep only same-domain links
        absolute_url = urljoin(url, href)
        if urlparse(absolute_url).netloc == base_domain:
            subpages.add(absolute_url)

    logging.info("Found %d unique subpages", len(subpages))
    return sorted(subpages)


###############################################################################
# TUI (curses) Implementation
###############################################################################
def tui_input(stdscr, prompt: str, row: int, col: int) -> str:
    """
    A simple curses-based input prompt for the TUI.
    Renders a prompt at (row, col) and collects user keystrokes until ENTER.
    """
    curses.echo()
    stdscr.addstr(row, col, prompt)
    stdscr.refresh()
    user_input = stdscr.getstr(row + 1, col, 60)  # read up to 60 chars
    curses.noecho()
    return user_input.decode("utf-8").strip()


def run_tui(stdscr):
    """
    Main curses-driven TUI. Provides an interactive menu to scrape a URL
    and display discovered subpages.
    """
    # Basic curses setup
    curses.curs_set(0)  # Hide cursor initially
    stdscr.nodelay(False)
    stdscr.clear()

    # Instructions
    stdscr.addstr(0, 0, "Subpage Scraper (TUI Mode)")
    stdscr.addstr(1, 0, "Press 's' to start scraping, or 'q' to quit.")
    stdscr.refresh()

    while True:
        key = stdscr.getch()
        if key == ord("q"):
            # Quit
            break
        elif key == ord("s"):
            # Scrape flow
            stdscr.clear()
            stdscr.addstr(0, 0, "You chose to scrape. Press ESC at any time to cancel.")
            # Prompt user for URL
            url = tui_input(stdscr, "Enter URL (e.g. https://example.com): ", 2, 0)
            # If user hits ESC, we might get an empty string or partial input
            if not url:
                stdscr.addstr(4, 0, "No URL provided. Returning to main menu.")
                stdscr.refresh()
                curses.napms(2000)
                stdscr.clear()
                stdscr.addstr(0, 0, "Subpage Scraper (TUI Mode)")
                stdscr.addstr(1, 0, "Press 's' to start scraping, or 'q' to quit.")
                stdscr.refresh()
                continue

            stdscr.addstr(4, 0, f"Scraping subpages from: {url}")
            stdscr.refresh()

            # Perform scraping in a background thread
            try:
                subpages = asyncio.run(asyncio.to_thread(scrape_subpages, url))
            except ValueError as exc:
                stdscr.addstr(6, 0, f"Error: {exc}")
                stdscr.addstr(8, 0, "Press any key to return to main menu.")
                stdscr.refresh()
                stdscr.getch()
                # Reset screen
                stdscr.clear()
                stdscr.addstr(0, 0, "Subpage Scraper (TUI Mode)")
                stdscr.addstr(1, 0, "Press 's' to start scraping, or 'q' to quit.")
                stdscr.refresh()
                continue

            # Show results
            if subpages:
                stdscr.addstr(6, 0, f"Success: Found {len(subpages)} subpage(s).")
                for idx, link in enumerate(subpages, start=1):
                    stdscr.addstr(6 + idx, 0, f"{idx}. {link}")
            else:
                stdscr.addstr(6, 0, "No subpages found.")
            stdscr.addstr(8 + len(subpages), 0, "Press any key to return to main menu.")
            stdscr.refresh()
            stdscr.getch()

            # Reset screen
            stdscr.clear()
            stdscr.addstr(0, 0, "Subpage Scraper (TUI Mode)")
            stdscr.addstr(1, 0, "Press 's' to start scraping, or 'q' to quit.")
            stdscr.refresh()


###############################################################################
# CLI (Typer + Rich) Implementation
###############################################################################
console = Console()
app = typer.Typer(
    help="A CLI for scraping subpages from a given URL. (Also has a TUI!)"
)


@app.command(help="Scrape subpages for a single URL via CLI.")
def scrape():
    """
    Prompt the user for a URL, scrape the subpages, and display the results in CLI mode.
    """
    url = typer.prompt("Please enter a URL (e.g., https://example.com)")

    # Basic validation
    url = url.strip()
    if not url:
        console.print("[bold red]Error: Invalid URL provided.[/bold red]", style="red")
        raise typer.Exit(code=1)

    console.print(f"[bold cyan]Scraping subpages from:[/bold cyan] {url}")

    try:
        subpages: List[str] = asyncio.run(asyncio.to_thread(scrape_subpages, url))
    except ValueError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1)

    if subpages:
        console.print(
            f"[bold green]Success:[/bold green] Found {len(subpages)} subpage(s)."
        )
        # Use a Rich table for a nice display
        table = Table(title="Discovered Subpages", show_lines=True)
        table.add_column("#", justify="right")
        table.add_column("URL", justify="left")

        for index, page in enumerate(subpages, start=1):
            table.add_row(str(index), page)
        console.print(table)
    else:
        console.print("[bold yellow]No subpages found.[/bold yellow]")


@app.command(help="Launch the TUI explicitly.")
def tui():
    """
    Explicitly launch the interactive TUI version of the scraper.
    """
    curses.wrapper(run_tui)


###############################################################################
# Main Entrypoint
###############################################################################
def main():
    """
    Decide whether to launch TUI or CLI based on arguments.
    """
    if len(sys.argv) == 1:
        # No arguments => launch TUI mode by default
        curses.wrapper(run_tui)
    else:
        # CLI mode
        app()


if __name__ == "__main__":
    main()
