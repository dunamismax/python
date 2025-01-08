#!/usr/bin/env python3
"""
A simple subpage scraper implemented as a Typer CLI application.

Usage:
    1. Install dependencies:
       pip install requests beautifulsoup4 typer[all]

    2. Run the CLI:
       python scraper.py

    3. Follow the on-screen prompt to enter a URL and begin scraping.

This script demonstrates:
- Basic HTTP GET requests with `requests`
- HTML parsing with `BeautifulSoup`
- Logging and error handling
- Interactive command-line interface with `Typer`
- Concurrency using `asyncio.to_thread`
"""

import logging
import requests
import asyncio
import typer

from typing import List
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

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
        # Convert relative path to absolute URL
        if href.startswith("/"):
            absolute_url = urljoin(url, href)
            # Only include links from the same domain
            if urlparse(absolute_url).netloc == base_domain:
                subpages.add(absolute_url)

    logging.info("Found %d unique subpages", len(subpages))
    return sorted(subpages)


###############################################################################
# Typer CLI Application
###############################################################################

app = typer.Typer(help="A CLI for scraping subpages from a given URL.")


@app.command(name="scrape", help="Scrape subpages for a single URL.")
def scrape_command():
    """
    Prompt the user for a URL, scrape the subpages, and display the results.
    """
    url = typer.prompt("Please enter a URL (e.g., https://example.com)")

    # Strip and basic validation
    url = url.strip()
    if not url:
        typer.secho("Error: Invalid URL provided.", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Scraping subpages from: {url}")
    # Use asyncio.to_thread to mirror the async scraping approach in the original
    try:
        subpages: List[str] = asyncio.run(asyncio.to_thread(scrape_subpages, url))
    except ValueError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    if subpages:
        typer.secho(
            f"Success: Found {len(subpages)} subpage(s).", fg=typer.colors.GREEN
        )
        for index, page in enumerate(subpages, start=1):
            typer.echo(f"{index}. {page}")
    else:
        typer.secho("No subpages found.", fg=typer.colors.YELLOW)


def main():
    """
    Entrypoint to the Typer CLI. Invokes Typer's application runner.
    """
    app()


if __name__ == "__main__":
    main()
