"""
Remote Server Log Viewer & Analyzer using Textual

Features:
- Interactive TUI for entering SSH credentials (host, user, password, port, log file)
- Asynchronous SSH log streaming using asyncssh
- Real-time filter by keyword, severity level, or date range
- Highlighting of matched text
- Split layout with a filter panel and live log view
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
from textual.containers import Vertical, Horizontal, Container
from textual.reactive import reactive
from textual.widgets import (
    Header,
    Footer,
    Label,
    Input,
    Button,
    Static,
    RichLog,
    Placeholder,
)
from textual.widget import Widget


class SSHLogStreamer:
    """
    A helper class to establish an SSH connection and stream logs.

    This class uses asyncssh to run a 'tail -f' command on the remote server.
    You can adapt this to run any log streaming command or custom script.
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

        # The SSH process object for the running command
        self.process = None

    async def connect_and_stream_logs(self):
        """
        Connect to remote host via SSH and yield new log lines as they arrive.
        """
        try:
            conn = await asyncssh.connect(
                self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                known_hosts=self.known_hosts,
            )
            # Tail the log file indefinitely
            self.process = await conn.create_process(f"tail -n 0 -f {self.log_file}")

            # Read lines until process ends (it shouldn't for tail -f)
            async for line in self.process.stdout:
                yield line.rstrip("\n")

        except (OSError, asyncssh.Error) as exc:
            yield f"ERROR: SSH connection failed: {exc}"
            traceback.print_exc()

    async def close(self):
        """Close the SSH process if it is still running."""
        try:
            if self.process and not self.process.stdout.at_eof():
                self.process.terminate()
        except Exception:
            pass


class FilterUpdated:
    """Message that is posted by the Filter panel when filters are updated."""

    def __init__(
        self,
        keyword: str,
        severity: str,
        date_from: str,
        date_to: str,
    ) -> None:
        self.keyword = keyword
        self.severity = severity
        self.date_from = date_from
        self.date_to = date_to


class LogFilterPanel(Widget):
    """
    A panel containing filter controls:
    - Keyword search (regex)
    - Severity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - Date range (start/end)

    The panel tracks the current filter state and communicates
    changes to the main application via FilterUpdated messages.
    """

    # Reactive state
    keyword: reactive[str] = reactive("")
    severity: reactive[str] = reactive("")
    date_from: reactive[str] = reactive("")
    date_to: reactive[str] = reactive("")

    def compose(self) -> ComposeResult:
        """
        Create the layout for the filter panel.
        """
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
        Handle the "Apply Filters" button click.
        """
        if event.button.id == "apply-filters-btn":
            # Extract current filter values from the Input widgets
            self.keyword = self.query_one("#keyword-input", Input).value
            self.severity = (
                self.query_one("#severity-input", Input).value.upper().strip()
            )
            self.date_from = self.query_one("#date-from-input", Input).value
            self.date_to = self.query_one("#date-to-input", Input).value

            # Post a message that filters have changed
            self.post_message(
                FilterUpdated(self.keyword, self.severity, self.date_from, self.date_to)
            )


class LiveLogPanel(Widget):
    """
    A panel to display incoming log lines in real-time.

    It handles highlighting matched text and color-coding based on severity.
    """

    # We keep a list of all lines so we can re-filter when the user changes filters
    lines: reactive[List[str]] = reactive([])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rich_log = RichLog()
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
        Insert a new line of text into the RichLog,
        applying filters and color-coding if needed.
        """
        # Check filters
        if not self.passes_filters(new_line):
            return

        # Apply highlighting and color coding
        severity_color = self.get_severity_color(new_line)
        if self.current_filters["keyword"]:
            new_line = self.highlight_keyword(new_line, self.current_filters["keyword"])

        # Write line to RichLog with optional style
        self.rich_log.write(new_line, style=severity_color)

    def passes_filters(self, line: str) -> bool:
        """
        Check if the line passes the current filters:
        - Regex keyword match
        - Severity
        - Date range (assuming logs contain date in some standard format)
        """
        keyword = self.current_filters["keyword"]
        severity = self.current_filters["severity"]
        date_from = self.current_filters["date_from"]
        date_to = self.current_filters["date_to"]

        # Keyword filter (regex or substring)
        if keyword:
            try:
                if not re.search(keyword, line):
                    return False
            except re.error:
                # If invalid regex, fallback to simple substring match
                if keyword not in line:
                    return False

        # Severity filter
        if severity and not self.check_severity_in_line(line, severity):
            return False

        # Date range filter example:
        # If your log lines have a datetime prefix like "2025-01-05 14:23:12"
        if date_from or date_to:
            if not self.check_date_in_line(line, date_from, date_to):
                return False

        return True

    def check_severity_in_line(self, line: str, severity: str) -> bool:
        """
        Simple example: check if the severity level is in the line,
        e.g. "ERROR", "INFO", etc.
        """
        return severity in line

    def check_date_in_line(self, line: str, date_from: str, date_to: str) -> bool:
        """
        Extract date from line (example: first 10 chars are YYYY-MM-DD).
        Compare with date_from and date_to if provided.
        Adjust logic according to your log date format.
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
            # If line doesn't start with a date or invalid format, skip date filter
            return True

    def highlight_keyword(self, line: str, keyword: str) -> str:
        """
        Surround matching keywords with `[bold red]...[/]` markup for highlighting.
        """
        try:
            pattern = re.compile(f"({keyword})", re.IGNORECASE)
            return pattern.sub(r"[bold red]\1[/]", line)
        except re.error:
            # Fallback to simple replace if the user typed an invalid regex
            return line.replace(keyword, f"[bold red]{keyword}[/]")

    def get_severity_color(self, line: str) -> str:
        """
        Return a textual style string based on severity.
        Example: "CRITICAL" => "bold red", "ERROR" => "red", "WARNING" => "yellow",
        "INFO" => "green", "DEBUG" => "dim".
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

    def update_filters(
        self, keyword: str, severity: str, date_from: str, date_to: str
    ) -> None:
        """
        Update internal filters. This triggers re-checking all lines or a fresh rendering
        based on your preference.
        """
        self.current_filters["keyword"] = keyword
        self.current_filters["severity"] = severity
        self.current_filters["date_from"] = date_from
        self.current_filters["date_to"] = date_to

        # Clear and re-display lines with new filters
        current_log = list(self.lines)
        self.rich_log.clear()
        for l in current_log:
            self.update_log(l)


class ConnectionPanel(Widget):
    """
    A panel to enter SSH credentials and connect:
    - Host
    - Username
    - Password
    - Port
    - Log file path

    Once the user clicks Connect, it will post a ConnectionRequested message.
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


class ConnectionRequested:
    """Message posted by ConnectionPanel when the user clicks Connect."""

    def __init__(self, host: str, user: str, password: str, port: int, logfile: str):
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.logfile = logfile


class LogMonitorApp(App):
    """
    The main Textual application class.

    It sets up:
    - Header at the top, Footer at the bottom.
    - A Horizontal split with:
        Left side: Connection Panel + Filter Panel
        Right side: Live Log Panel

    Steps to use:
    1. Fill out connection details on the left (host, user, pass, port, log file)
    2. Click "Connect". The app tries to establish SSH connection and starts streaming logs.
    3. Use the filter panel (on the left, below connection fields) to filter logs in real-time.
    """

    CSS = """
    #connection-panel-title,
    #filter-panel-title {
        content-align: center middle;
        text-style: bold;
        margin: 0.5 0;
    }

    #connect-btn,
    #apply-filters-btn {
        margin: 1 0;
    }

    #host-input,
    #user-input,
    #password-input,
    #port-input,
    #logfile-input,
    #keyword-input,
    #severity-input,
    #date-from-input,
    #date-to-input {
        width: 90%;
        margin: 1 0;
    }
    """

    # Reactive so we can display error messages or connection statuses
    connection_error: reactive[str] = reactive("")
    connected: reactive[bool] = reactive(False)

    def __init__(self):
        super().__init__()

        # Panels
        self.connection_panel = ConnectionPanel()
        self.filter_panel = LogFilterPanel()
        self.live_log_panel = LiveLogPanel()

        # SSH streamer references
        self.streamer: Optional[SSHLogStreamer] = None
        self._fetch_logs_task: Optional[asyncio.Task] = None

    def compose(self) -> ComposeResult:
        """
        Top-level layout with a header, footer, and horizontal split:
        - Left side: connection panel + filter panel
        - Right side: live log panel
        """
        yield Header(name="Log Monitor (Interactive)")
        yield Footer()

        # Left container with connection panel + filter panel in a Vertical layout
        left_pane = Vertical(
            Container(self.connection_panel, id="connection_panel"),
            Container(self.filter_panel, id="filter_panel"),
            id="left_pane",
        )

        # Right container with the live log panel
        right_pane = Container(self.live_log_panel, id="log_panel")

        # Horizontal layout: left pane (connection + filter), right pane (log output)
        main_area = Horizontal(
            left_pane,
            right_pane,
        )

        yield main_area

    async def on_mount(self) -> None:
        """
        Called after the UI has been composed and is ready.
        """
        # Nothing special to do on mount in this example
        pass

    async def on_unmount(self) -> None:
        """
        Called when the application is shutting down.
        """
        # Attempt to close the SSH process gracefully
        if self.streamer:
            await self.streamer.close()
        if self._fetch_logs_task:
            self._fetch_logs_task.cancel()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button clicks within the entire app.
        We detect the "Connect" button from the connection panel here.
        """
        if event.button.id == "connect-btn":
            # Gather fields from the connection panel
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

            # Post a ConnectionRequested message for clarity (optional)
            # or just handle it here directly:
            self.handle_connection_request(host, user, password, port, logfile)

    def handle_connection_request(
        self, host: str, user: str, password: str, port: int, logfile: str
    ) -> None:
        """
        Called when the user clicks "Connect". Attempts to create the SSHLogStreamer
        and start the background task to fetch logs.
        """
        # If there's a previous streamer, close it
        if self.streamer:
            asyncio.create_task(self.streamer.close())
        if self._fetch_logs_task:
            self._fetch_logs_task.cancel()

        # Create a new SSHLogStreamer with user inputs
        self.streamer = SSHLogStreamer(
            host=host,
            username=user,
            password=password,
            port=port,
            log_file=logfile,
        )

        # Start a background task to fetch logs
        self._fetch_logs_task = asyncio.create_task(self.fetch_logs())

    async def fetch_logs(self) -> None:
        """
        Background task that continuously reads log lines from the remote server
        and updates the LiveLogPanel.
        """
        if not self.streamer:
            return

        self.connected = True  # Potentially used to track UI states

        async for line in self.streamer.connect_and_stream_logs():
            # Each line from the SSH stream is appended, and displayed if it passes filters
            self.live_log_panel.lines.append(line)
            self.live_log_panel.update_log(line)

    def on_filter_updated(self, message: FilterUpdated) -> None:
        """
        Invoked when the Filter panel updates the filters.
        """
        self.live_log_panel.update_filters(
            keyword=message.keyword,
            severity=message.severity,
            date_from=message.date_from,
            date_to=message.date_to,
        )
