#!/usr/bin/env python3
"""
Remote Server Log Viewer & Analyzer using Typer

This version removes the Textual TUI in favor of an interactive Typer CLI app.

Features:
- Prompts for SSH credentials (host, user, password, port, log file)
- Asynchronous SSH log streaming using asyncssh
- Real-time filtering by keyword (regex or plain text), severity, and date range
- Color-coded severity levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Highlighting of matched text (via ANSI escape sequences)
- Interactive filter updates while logs are streaming

Dependencies:
    pip install asyncssh typer

Usage:
    python log-monitor.py monitor
"""

import asyncio
import re
import traceback
from datetime import datetime
from typing import Optional, List

import asyncssh
import typer

app = typer.Typer()


class SSHLogStreamer:
    """
    Helper class to establish SSH and stream logs via `tail -f`.
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        log_file: str = "/var/log/syslog",
        port: int = 22,
        known_hosts: Optional[str] = None,
    ):
        self.host = host
        self.username = username
        self.password = password
        self.log_file = log_file
        self.port = port
        self.known_hosts = known_hosts
        self.process: Optional[asyncssh.SSHClientProcess] = None

    async def connect_and_stream_logs(self):
        """
        Connect to the remote host via SSH and yield new log lines as they appear.
        """
        try:
            conn = await asyncssh.connect(
                self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                known_hosts=self.known_hosts,
            )
            # Use tail -n 0 -f to stream only new lines
            self.process = await conn.create_process(f"tail -n 0 -f {self.log_file}")

            async for line in self.process.stdout:
                yield line.rstrip("\n")

        except (OSError, asyncssh.Error) as exc:
            yield f"ERROR: SSH connection failed: {exc}"
            traceback.print_exc()

    async def close(self):
        """Terminate the SSH log process if it’s still running."""
        try:
            if self.process and not self.process.stdout.at_eof():
                self.process.terminate()
        except Exception:
            pass


class LogFilter:
    """
    Handles filtering (keyword, severity, date range) and text highlighting.
    """

    def __init__(
        self,
        keyword: str = "",
        severity: str = "",
        date_from: str = "",
        date_to: str = "",
    ):
        """
        :param keyword: Regex or substring to match
        :param severity: One of DEBUG/INFO/WARNING/ERROR/CRITICAL
        :param date_from: YYYY-MM-DD lower bound
        :param date_to: YYYY-MM-DD upper bound
        """
        self.keyword = keyword
        self.severity = severity.upper().strip()
        self.date_from = date_from.strip()
        self.date_to = date_to.strip()

    def passes_filters(self, line: str) -> bool:
        """
        Check if a log line satisfies the current filters.
        """
        # Keyword filter (regex or substring fallback)
        if self.keyword:
            try:
                if not re.search(self.keyword, line):
                    return False
            except re.error:
                # If invalid regex, fallback to a simple substring check
                if self.keyword not in line:
                    return False

        # Severity filter
        if self.severity and self.severity not in line:
            return False

        # Date range filter
        if (self.date_from or self.date_to) and not self._check_date_in_line(line):
            return False

        return True

    def _check_date_in_line(self, line: str) -> bool:
        """
        Basic date filter: parse the first 10 chars as YYYY-MM-DD.
        Adjust to your log format as needed.
        """
        try:
            log_date_str = line[:10]
            log_date = datetime.strptime(log_date_str, "%Y-%m-%d").date()

            if self.date_from:
                df = datetime.strptime(self.date_from, "%Y-%m-%d").date()
                if log_date < df:
                    return False

            if self.date_to:
                dt = datetime.strptime(self.date_to, "%Y-%m-%d").date()
                if log_date > dt:
                    return False

            return True
        except (ValueError, IndexError):
            # If we can’t parse a date, skip the filter
            return True

    def highlight_line(self, line: str) -> str:
        """
        Applies severity-based color and highlights keywords in red.
        """
        severity_color = self._get_severity_color(line)

        # Optionally highlight the keyword
        highlighted = (
            self._highlight_keyword(line, self.keyword) if self.keyword else line
        )

        if severity_color:
            # Wrap the entire line in the color
            highlighted = f"{severity_color}{highlighted}\033[0m"
        return highlighted

    def _highlight_keyword(self, line: str, keyword: str) -> str:
        """
        Highlight matched keywords with ANSI escape sequences for red + bold.
        """
        try:
            pattern = re.compile(f"({keyword})", re.IGNORECASE)
            return pattern.sub(r"\033[1;31m\1\033[0m", line)
        except re.error:
            # If invalid regex, fallback to simple substring replace
            return line.replace(keyword, f"\033[1;31m{keyword}\033[0m")

    def _get_severity_color(self, line: str) -> str:
        """
        Return an ANSI escape code based on severity tokens in the line.
        """
        if "CRITICAL" in line:
            return "\033[1;31m"  # Bold Red
        elif "ERROR" in line:
            return "\033[31m"  # Red
        elif "WARNING" in line:
            return "\033[33m"  # Yellow
        elif "INFO" in line:
            return "\033[32m"  # Green
        elif "DEBUG" in line:
            return "\033[2m"  # Dim
        return ""


async def _stream_logs_and_interact(
    streamer: SSHLogStreamer,
    initial_filter: LogFilter,
):
    """
    - Opens the SSH connection, streams logs asynchronously.
    - Concurrently listens for user commands to update filters.
    - Prints logs that pass the active filters.
    """
    # Maintain a buffer of all incoming lines so we can re-print when filters change
    lines_buffer: List[str] = []

    current_filter = initial_filter

    # Task that reads the logs
    async def read_logs():
        async for line in streamer.connect_and_stream_logs():
            lines_buffer.append(line)
            if current_filter.passes_filters(line):
                typer.echo(current_filter.highlight_line(line))

    # Task that interacts with user in the foreground
    async def user_input_loop():
        nonlocal current_filter

        while True:
            # Prompt user for possible commands
            typer.echo("\nCommands: [f]ilter, [q]uit")
            choice = await _async_input("Enter command: ").strip().lower()
            if choice == "q":
                # Quit
                break
            elif choice == "f":
                # Prompt for new filter values
                new_keyword = await _async_input("Keyword (regex or plain text): ")
                new_severity = await _async_input(
                    "Severity (DEBUG/INFO/WARNING/ERROR/CRITICAL): "
                )
                new_date_from = await _async_input("Date from (YYYY-MM-DD): ")
                new_date_to = await _async_input("Date to (YYYY-MM-DD): ")

                # Update current_filter
                current_filter = LogFilter(
                    keyword=new_keyword,
                    severity=new_severity,
                    date_from=new_date_from,
                    date_to=new_date_to,
                )

                # Clear screen or do a separator
                typer.echo(
                    "\n--- Updating filters and re-displaying matching logs ---\n"
                )

                # Re-print all lines in the buffer that pass the new filter
                for old_line in lines_buffer:
                    if current_filter.passes_filters(old_line):
                        typer.echo(current_filter.highlight_line(old_line))
            else:
                typer.echo("Unknown command. Please enter 'f' or 'q'.")

        # After user decides to quit, we can exit
        typer.echo("\nShutting down log streaming...")
        await streamer.close()

    # Start both tasks concurrently
    await asyncio.gather(read_logs(), user_input_loop())


async def _async_input(prompt: str = "") -> str:
    """
    A helper to prompt the user for input in an async context without blocking.
    """
    # Print the prompt, then read from stdin in a thread pool
    typer.echo(prompt, nl=False)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, input)


@app.command()
def monitor():
    """
    Prompt for SSH credentials and log filter parameters, then start streaming logs.
    You can interactively change filters or quit at any time.
    """
    host = typer.prompt("Host (Hostname or IP)")
    user = typer.prompt("Username")
    password = typer.prompt("Password", hide_input=True)
    port_str = typer.prompt("Port", default="22")
    logfile = typer.prompt("Log file", default="/var/log/syslog")

    try:
        port = int(port_str)
    except ValueError:
        port = 22

    typer.echo("--- Optional Initial Filters ---")
    keyword = typer.prompt("Keyword (regex or plain text)", default="")
    severity = typer.prompt("Severity (DEBUG/INFO/WARNING/ERROR/CRITICAL)", default="")
    date_from = typer.prompt("Date from (YYYY-MM-DD)", default="")
    date_to = typer.prompt("Date to (YYYY-MM-DD)", default="")

    # Initialize SSH streamer and filter
    streamer = SSHLogStreamer(
        host=host,
        username=user,
        password=password,
        port=port,
        log_file=logfile,
    )
    log_filter = LogFilter(
        keyword=keyword,
        severity=severity,
        date_from=date_from,
        date_to=date_to,
    )

    # Start the asyncio event loop
    try:
        asyncio.run(_stream_logs_and_interact(streamer, log_filter))
    except KeyboardInterrupt:
        typer.echo("\nKeyboard interrupt detected. Closing connection...")
        asyncio.run(streamer.close())


if __name__ == "__main__":
    app()
