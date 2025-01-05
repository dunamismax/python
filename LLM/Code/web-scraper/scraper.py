#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A robust web scraper using Requests and BeautifulSoup to discover subpages
within a given domain (e.g., /blog, /contact).

This script retrieves the HTML content from the provided URL, parses for
all anchor links (i.e., <a href="...">), and collects those that are internal
subpages starting with '/'.

Requirements:
  - requests
  - beautifulsoup4

Usage:
  python scraper.py [URL]

Example:
  python scraper.py https://example.com
"""

import sys
import logging
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="[%(levelname)s] %(asctime)s - %(message)s"
)


def scrape_subpages(url):
    """
    Fetches the given URL, parses the HTML, and extracts all internal links
    that resemble subpages (i.e., starting with '/').

    :param url: The base URL to scrape.
    :type url: str
    :return: A list of full URLs that point to subpages under the same domain.
    :rtype: list[str]
    :raises ValueError: If the response code indicates a client or server error.
    """
    logging.info("Starting subpage discovery for URL: %s", url)

    try:
        response = requests.get(url, timeout=10)  # 10-second timeout
        response.raise_for_status()  # Raise an exception for HTTP errors
    except requests.exceptions.RequestException as e:
        logging.error("Request failed: %s", e)
        raise ValueError(f"Failed to retrieve content from {url}") from e

    # Parse the HTML content
    soup = BeautifulSoup(response.text, "html.parser")

    # We'll store subpages in a set to avoid duplicates
    subpages = set()
    base_domain = urlparse(url).netloc

    # Find all anchors and process their href attribute
    for link_tag in soup.find_all("a", href=True):
        href = link_tag["href"]

        # If the link starts with '/', it's likely an internal subpage.
        # We'll create the absolute URL using urljoin.
        if href.startswith("/"):
            absolute_url = urljoin(url, href)

            # Ensure we're not crossing into other domains
            if urlparse(absolute_url).netloc == base_domain:
                subpages.add(absolute_url)

    logging.info("Found %d unique subpages", len(subpages))
    return sorted(subpages)


def main():
    """
    Main function to execute the web scraper as a standalone script.
    """
    if len(sys.argv) < 2:
        logging.error("Usage: python scraper.py [URL]")
        sys.exit(1)

    url = sys.argv[1]

    try:
        subpages = scrape_subpages(url)

        if subpages:
            logging.info("Printing extracted subpages:")
            for idx, sp in enumerate(subpages, start=1):
                print(f"{idx}. {sp}")
        else:
            logging.warning("No subpages found at the provided URL.")

    except ValueError as e:
        logging.error("Scraping process failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
