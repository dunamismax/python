#!/usr/bin/env python3
"""
Remote Server Log Viewer & Analyzer using Textual

Features:
- Interactive TUI for entering SSH credentials (host, user, password, port, log file)
- Asynchronous SSH log streaming using asyncssh
- Real-time filtering by keyword, severity level, or date range
- Highlighting of matched text
- Split layout with a filter panel and a live log view
- Color-coded log severity levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Mouse and keyboard interaction

Dependencies:
    pip install textual asyncssh

Usage:
    python log-monitor.py

When launched, the TUI will prompt you for:
  - Host
  - Username
  - Password
  - SSH Port
  - Log File

Click the "Connect" button (or press Enter on it) to establish the SSH connection
and begin streaming logs. Filters can be applied via the Filter Panel.
"""

import asyncio
import re
import traceback
from datetime import datetime
from typing import Optional, List

import asyncssh

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.reactive import reactive
from textual.widgets import (
    Header,
    Footer,
    Label,
    Input,
    Button,
    RichLog,
    ScrollView,  # Available in latest Textual releases
)


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
        self.process = None

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


class FilterUpdated:
    """
    Message passed from the filter panel when filters are changed.
    """

    def __init__(
        self, keyword: str, severity: str, date_from: str, date_to: str
    ) -> None:
        self.keyword = keyword
        self.severity = severity
        self.date_from = date_from
        self.date_to = date_to


class LogFilterPanel(Vertical):
    """
    A panel containing filter controls (keyword, severity, date range).
    """

    # Reactive states (optional if you want to track them in real-time)
    keyword: reactive[str] = reactive("")
    severity: reactive[str] = reactive("")
    date_from: reactive[str] = reactive("")
    date_to: reactive[str] = reactive("")

    def compose(self) -> ComposeResult:
        yield Label("Filters", id="filter-panel-title")

        yield Label("Keyword:")
        yield Input(placeholder="Regex or text", id="keyword-input")

        yield Label("Severity (DEBUG/INFO/WARNING/ERROR/CRITICAL):")
        yield Input(placeholder="Severity level", id="severity-input")

        yield Label("Date From (YYYY-MM-DD):")
        yield Input(placeholder="YYYY-MM-DD", id="date-from-input")

        yield Label("Date To (YYYY-MM-DD):")
        yield Input(placeholder="YYYY-MM-DD", id="date-to-input")

        yield Button("Apply Filters", id="apply-filters-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        When "Apply Filters" is clicked, gather filter inputs and post FilterUpdated.
        """
        if event.button.id == "apply-filters-btn":
            self.keyword = self.query_one("#keyword-input", Input).value
            self.severity = (
                self.query_one("#severity-input", Input).value.upper().strip()
            )
            self.date_from = self.query_one("#date-from-input", Input).value
            self.date_to = self.query_one("#date-to-input", Input).value

            self.post_message(
                FilterUpdated(self.keyword, self.severity, self.date_from, self.date_to)
            )


class LiveLogPanel(Vertical):
    """
    Displays incoming log lines in a RichLog, with filtering and highlighting.
    """

    # Keep all lines stored so we can re-filter them as needed
    lines: reactive[List[str]] = reactive([])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rich_log = RichLog()
        # Current filter criteria
        self.current_filters = {
            "keyword": "",
            "severity": "",
            "date_from": None,
            "date_to": None,
        }

    def compose(self) -> ComposeResult:
        yield self.rich_log

    def update_log(self, new_line: str) -> None:
        """
        Insert a new line into the RichLog, applying filters and any highlighting.
        """
        if not self.passes_filters(new_line):
            return

        # Determine color from severity
        severity_color = self.get_severity_color(new_line)

        # Highlight the keyword, if any
        if self.current_filters["keyword"]:
            new_line = self.highlight_keyword(new_line, self.current_filters["keyword"])

        self.rich_log.write(new_line, style=severity_color)

    def passes_filters(self, line: str) -> bool:
        """
        Check if a log line satisfies the current filters.
        """
        keyword = self.current_filters["keyword"]
        severity = self.current_filters["severity"]
        date_from = self.current_filters["date_from"]
        date_to = self.current_filters["date_to"]

        # Keyword filter (regex or substring fallback)
        if keyword:
            try:
                if not re.search(keyword, line):
                    return False
            except re.error:
                if keyword not in line:
                    return False

        # Severity filter
        if severity and severity not in line:
            return False

        # Date filter
        if date_from or date_to:
            if not self.check_date_in_line(line, date_from, date_to):
                return False

        return True

    def check_date_in_line(self, line: str, date_from: str, date_to: str) -> bool:
        """
        Basic date filter: parse the first 10 chars as YYYY-MM-DD.
        Adjust to your log format as needed.
        """
        try:
            log_date_str = line[:10]
            log_date = datetime.strptime(log_date_str, "%Y-%m-%d").date()

            if date_from:
                df = datetime.strptime(date_from, "%Y-%m-%d").date()
                if log_date < df:
                    return False

            if date_to:
                dt = datetime.strptime(date_to, "%Y-%m-%d").date()
                if log_date > dt:
                    return False

            return True
        except (ValueError, IndexError):
            # If we can’t parse a date, skip the filter
            return True

    def highlight_keyword(self, line: str, keyword: str) -> str:
        """
        Highlight matched keywords with markup (e.g., `[bold red]word[/]`).
        """
        try:
            pattern = re.compile(f"({keyword})", re.IGNORECASE)
            return pattern.sub(r"[bold red]\1[/]", line)
        except re.error:
            # If invalid regex, fallback to a simple substring replace
            return line.replace(keyword, f"[bold red]{keyword}[/]")

    def get_severity_color(self, line: str) -> str:
        """
        Return a textual style based on severity tokens in the line.
        """
        if "CRITICAL" in line:
            return "bold red"
        elif "ERROR" in line:
            return "red"
        elif "WARNING" in line:
            return "yellow"
        elif "INFO" in line:
            return "green"
        elif "DEBUG" in line:
            return "dim"
        return ""

    def update_filters(self, keyword: str, severity: str, date_from: str, date_to: str):
        """
        Update filters, then re-check all lines to refresh the display.
        """
        self.current_filters["keyword"] = keyword
        self.current_filters["severity"] = severity
        self.current_filters["date_from"] = date_from
        self.current_filters["date_to"] = date_to

        # Re-run filtering on all existing lines
        current_log = list(self.lines)
        self.rich_log.clear()
        for existing_line in current_log:
            self.update_log(existing_line)


class ConnectionPanel(Vertical):
    """
    Panel for SSH connection inputs (host, user, pass, port, log file).
    """

    def compose(self) -> ComposeResult:
        yield Label("Connection Details", id="connection-panel-title")

        yield Label("Host:")
        yield Input(placeholder="Hostname or IP", id="host-input")

        yield Label("Username:")
        yield Input(placeholder="SSH Username", id="user-input")

        yield Label("Password:")
        yield Input(placeholder="SSH Password", password=True, id="password-input")

        yield Label("Port:")
        yield Input(placeholder="22", id="port-input")

        yield Label("Log File:")
        yield Input(placeholder="/var/log/syslog", id="logfile-input")

        yield Button("Connect", id="connect-btn")


class LogMonitorApp(App):
    """
    Main Textual app. Sets up:
      - Header, Footer
      - A horizontal split:
          - Left side (scrollable) with connection & filter panels
          - Right side for the log panel
    """

    CSS = """
    Screen {
        layout: horizontal;
    }

    /* Left pane: scrollable */
    #left_pane {
        width: 35%;
        min-width: 25%;
        max-width: 45%;
        border-right: solid 1px #666;
    }

    #right_pane {
        width: 65%;
        min-width: 55%;
    }

    /* Titles */
    #connection-panel-title,
    #filter-panel-title {
        content-align: center middle;
        text-style: bold;
        margin: 0.5 1 0.5 1; /* top, right, bottom, left */
    }

    Label {
        margin: 0.5;
    }

    Input {
        width: 95%;
        margin: 0.5 0 0 0;
    }

    Button {
        margin: 0.5;
        width: 50%;
        dock: left;
    }
    """

    connection_error: reactive[str] = reactive("")
    connected: reactive[bool] = reactive(False)

    def __init__(self):
        super().__init__()
        self.connection_panel = ConnectionPanel()
        self.filter_panel = LogFilterPanel()
        self.live_log_panel = LiveLogPanel()

        # SSH streamer references
        self.streamer: Optional[SSHLogStreamer] = None
        self._fetch_logs_task: Optional[asyncio.Task] = None

    def compose(self) -> ComposeResult:
        """
        Build the layout:
        - Header + Footer
        - Left side (scrollable) with connection & filter
        - Right side for log output
        """
        yield Header("Log Monitor (Latest Textual)")
        yield Footer()

        # A ScrollView so the left side scrolls if there's overflow
        left_side = ScrollView(
            Vertical(
                self.connection_panel,
                self.filter_panel,
                id="left_container",
            ),
            id="left_pane",
            scrollbars=True,
        )

        # The live logs on the right side
        right_side = Container(self.live_log_panel, id="right_pane")

        yield left_side
        yield right_side

    async def on_mount(self) -> None:
        """Called when the app is first displayed."""
        pass

    async def on_unmount(self) -> None:
        """Gracefully shut down the SSH process on exit."""
        if self.streamer:
            await self.streamer.close()
        if self._fetch_logs_task:
            self._fetch_logs_task.cancel()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle the Connect button click."""
        if event.button.id == "connect-btn":
            host = self.connection_panel.query_one("#host-input", Input).value
            user = self.connection_panel.query_one("#user-input", Input).value
            password = self.connection_panel.query_one("#password-input", Input).value
            port_str = (
                self.connection_panel.query_one("#port-input", Input).value or "22"
            )
            logfile = (
                self.connection_panel.query_one("#logfile-input", Input).value
                or "/var/log/syslog"
            )

            try:
                port = int(port_str)
            except ValueError:
                port = 22

            self.handle_connection_request(host, user, password, port, logfile)

    def handle_connection_request(
        self, host: str, user: str, password: str, port: int, logfile: str
    ) -> None:
        """
        Called once user hits "Connect". Creates the SSHLogStreamer and starts streaming.
        """
        # Close any previous stream
        if self.streamer:
            asyncio.create_task(self.streamer.close())
        if self._fetch_logs_task:
            self._fetch_logs_task.cancel()

        self.streamer = SSHLogStreamer(
            host=host,
            username=user,
            password=password,
            port=port,
            log_file=logfile,
        )
        # Background task to fetch logs
        self._fetch_logs_task = asyncio.create_task(self.fetch_logs())

    async def fetch_logs(self) -> None:
        """
        Reads lines from SSH stream and appends them to the log panel.
        """
        if not self.streamer:
            return

        self.connected = True  # Could be used to update UI state

        async for line in self.streamer.connect_and_stream_logs():
            self.live_log_panel.lines.append(line)
            self.live_log_panel.update_log(line)

    def on_filter_updated(self, message: FilterUpdated) -> None:
        """
        When filters are updated, pass them to the log panel for re-filtering.
        """
        self.live_log_panel.update_filters(
            keyword=message.keyword,
            severity=message.severity,
            date_from=message.date_from,
            date_to=message.date_to,
        )


if __name__ == "__main__":
    LogMonitorApp().run()
