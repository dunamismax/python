import logging
import requests
import asyncio

from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import (
    Header,
    Footer,
    Static,
    Button,
    Input,
    ListView,
    ListItem,
    Label,
    LoadingIndicator,
)

logging.basicConfig(
    level=logging.INFO, format="[%(levelname)s] %(asctime)s - %(message)s"
)


def scrape_subpages(url: str) -> list[str]:
    logging.info("Starting subpage discovery for URL: %s", url)
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error("Request failed: %s", e)
        raise ValueError(f"Failed to retrieve content from {url}") from e

    soup = BeautifulSoup(response.text, "html.parser")
    subpages = set()
    base_domain = urlparse(url).netloc

    for link_tag in soup.find_all("a", href=True):
        href = link_tag["href"]
        if href.startswith("/"):
            absolute_url = urljoin(url, href)
            if urlparse(absolute_url).netloc == base_domain:
                subpages.add(absolute_url)

    logging.info("Found %d unique subpages", len(subpages))
    return sorted(subpages)


class ScraperApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }

    #controls {
        layout: horizontal;
        height: auto;
        padding: 1 2;
    }

    #results-panel {
        layout: vertical;
        padding: 1 2;
        border: solid $accent-darken-3;
    }

    #results-list {
        height: 1fr;
        overflow-y: auto;
        border: solid $accent-darken-3;
    }

    #status {
        padding: 1;
        color: green;
    }

    /* Minimal Input styling */
    Input {
        color: black;
        background: white;
        border: none;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(
            Static("Enter URL:", id="prompt-label"),
            Input(placeholder="https://example.com", id="url_input"),
            Button("Scrape", id="scrape_button"),
            id="controls",
        )
        yield Container(
            Static("Discovered Subpages:", id="results-label"),
            ListView(id="results-list"),
            id="results-panel",
        )
        yield Static("Idle", id="status")
        yield Footer()

    def on_ready(self) -> None:
        self.status = self.query_one("#status", Static)
        self.url_input = self.query_one("#url_input", Input)
        self.results_list = self.query_one("#results-list", ListView)
        self.url_input.focus()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "scrape_button":
            await self._start_scraping()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "url_input":
            await self._start_scraping()

    async def _start_scraping(self) -> None:
        url = self.url_input.value.strip()
        if not url:
            await self._update_status("[red]Error: Please provide a valid URL.")
            return

        self.results_list.clear()
        loading_item = ListItem(LoadingIndicator())
        self.results_list.append(loading_item)

        await self._update_status(f"Scraping {url} ...")
        self.refresh()

        try:
            subpages = await asyncio.to_thread(scrape_subpages, url)
            self.results_list.clear()

            if subpages:
                for idx, sp in enumerate(subpages, start=1):
                    self.results_list.append(ListItem(Label(f"{idx}. {sp}")))
                await self._update_status(
                    f"[green]Success: Found {len(subpages)} subpages."
                )
            else:
                await self._update_status("[yellow]No subpages found.")
        except ValueError as e:
            self.results_list.clear()
            await self._update_status(f"[red]Error: {e}")

    async def _update_status(self, message: str) -> None:
        self.status.update(message)
        self.refresh()


def main() -> None:
    ScraperApp().run()


if __name__ == "__main__":
    main()
