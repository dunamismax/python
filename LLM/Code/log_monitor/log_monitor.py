#!/usr/bin/env python3
"""
Remote Server Log Viewer & Analyzer using Typer and Curses

By default, if no arguments are passed, the TUI is launched.
You can also explicitly run 'tui' or other subcommands (e.g., 'monitor').
"""

import asyncio
import curses
import queue
import re
import threading
import traceback
from datetime import datetime
from typing import Optional, List

import asyncssh
import typer
from rich.console import Console
from rich.theme import Theme
from rich.text import Text

###############################################################################
# Typer App Initialization
###############################################################################
app = typer.Typer(help="A tool to monitor remote logs via SSH with CLI or TUI modes.")


###############################################################################
# Rich Console Setup (for CLI mode)
###############################################################################
custom_theme = Theme(
    {
        "debug": "dim",
        "info": "green",
        "warning": "yellow",
        "error": "red",
        "critical": "bold red",
        "keyword": "bold red",
        "bold": "bold",
    }
)
console = Console(theme=custom_theme)


###############################################################################
# SSHLogStreamer
###############################################################################
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


###############################################################################
# LogFilter
###############################################################################
class LogFilter:
    """
    Handles filtering (keyword, severity, date range) and line highlighting.
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

    def highlight_line_rich(self, line: str) -> Text:
        """
        Converts the line into a Rich Text object with severity-based color
        and highlights the keyword in bold red.
        """
        styled_line = Text(line)

        # Apply severity styles
        if "CRITICAL" in line:
            styled_line.stylize("critical")
        elif "ERROR" in line:
            styled_line.stylize("error")
        elif "WARNING" in line:
            styled_line.stylize("warning")
        elif "INFO" in line:
            styled_line.stylize("info")
        elif "DEBUG" in line:
            styled_line.stylize("debug")

        # Highlight the keyword
        if self.keyword:
            try:
                pattern = re.compile(self.keyword, re.IGNORECASE)
                match_positions = []
                for match in pattern.finditer(line):
                    match_positions.append((match.start(), match.end()))
                for start, end in reversed(match_positions):
                    styled_line.stylize("keyword", start, end)
            except re.error:
                # If invalid regex, fallback to substring approach
                substr = self.keyword
                idx = line.lower().find(substr.lower())
                while idx != -1:
                    styled_line.stylize("keyword", idx, idx + len(substr))
                    idx = line.lower().find(substr.lower(), idx + len(substr))
        return styled_line


###############################################################################
# ASYNC INPUT HELPER (for CLI monitor)
###############################################################################
async def _async_input(prompt: str = "") -> str:
    """
    A helper to prompt the user for input in an async context without blocking.
    """
    console.print(prompt, end="", style="bold")
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, input)


###############################################################################
# MONITOR COMMAND (CLI MODE)
###############################################################################
@app.command()
def monitor():
    """
    Prompt for SSH credentials and log filter parameters, then start streaming logs.
    Real-time interactive filter updates (f) or quit (q).
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

    console.print("[bold]\n--- Optional Initial Filters ---[/bold]")
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

    lines_buffer: List[str] = []

    async def read_logs():
        async for line in streamer.connect_and_stream_logs():
            lines_buffer.append(line)
            if log_filter.passes_filters(line):
                console.print(log_filter.highlight_line_rich(line))

    async def user_input_loop():
        nonlocal log_filter

        while True:
            console.print("\nCommands: [bold][f][/bold]ilter, [bold][q][/bold]uit")
            choice = (await _async_input("Enter command: ")).strip().lower()

            if choice == "q":
                break
            elif choice == "f":
                new_keyword = await _async_input("Keyword (regex or plain text): ")
                new_severity = await _async_input(
                    "Severity (DEBUG/INFO/WARNING/ERROR/CRITICAL): "
                )
                new_date_from = await _async_input("Date from (YYYY-MM-DD): ")
                new_date_to = await _async_input("Date to (YYYY-MM-DD): ")

                log_filter = LogFilter(
                    keyword=new_keyword,
                    severity=new_severity,
                    date_from=new_date_from,
                    date_to=new_date_to,
                )

                console.print("[bold]\n--- Updating filters ---[/bold]")
                console.print("[bold]--- Matching logs ---[/bold]\n")
                for old_line in lines_buffer:
                    if log_filter.passes_filters(old_line):
                        console.print(log_filter.highlight_line_rich(old_line))
            else:
                console.print("Unknown command. Please enter 'f' or 'q'.")

        console.print("\n[bold]Shutting down log streaming...[/bold]")
        await streamer.close()

    async def main_loop():
        await asyncio.gather(read_logs(), user_input_loop())

    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        console.print(
            "[bold red]\nKeyboard interrupt detected. Closing connection...[/bold red]"
        )
        asyncio.run(streamer.close())


###############################################################################
# TUI COMMAND (Curses Mode)
###############################################################################
@app.command()
def tui():
    """
    Launch a curses-based TUI to view and filter logs in real time.
    Press 'f' to update filters, 'q' to quit.
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

    typer.echo("\n--- Optional Initial Filters ---")
    keyword = typer.prompt("Keyword (regex or plain text)", default="")
    severity = typer.prompt("Severity (DEBUG/INFO/WARNING/ERROR/CRITICAL)", default="")
    date_from = typer.prompt("Date from (YYYY-MM-DD)", default="")
    date_to = typer.prompt("Date to (YYYY-MM-DD)", default="")

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

    # Thread-safe queue to receive lines from asyncio
    log_queue = queue.Queue()
    lines_buffer: List[str] = []
    stop_event = threading.Event()  # to signal the streaming thread to stop

    # ----------------------------
    # 1) Async log fetcher thread
    # ----------------------------
    def start_asyncio_loop_in_thread():
        async def fetch_logs():
            async for line in streamer.connect_and_stream_logs():
                log_queue.put(line)
            # If the streamer finishes or fails, put None
            log_queue.put(None)

        async def main_loop():
            await fetch_logs()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(main_loop())
        except Exception as e:
            log_queue.put(f"ERROR: {e}")
        finally:
            loop.run_until_complete(streamer.close())
            loop.close()

    reader_thread = threading.Thread(target=start_asyncio_loop_in_thread, daemon=True)
    reader_thread.start()

    # ----------------------------
    # 2) Curses UI
    # ----------------------------
    def curses_main(stdscr):
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(True)  # Non-blocking input

        max_y, max_x = stdscr.getmaxyx()
        log_win = curses.newwin(max_y - 1, max_x, 0, 0)
        status_win = curses.newwin(1, max_x, max_y - 1, 0)

        scroll_pos = 0
        while not stop_event.is_set():
            # Receive new lines from queue
            try:
                while True:
                    line = log_queue.get_nowait()
                    if line is None:
                        stop_event.set()
                        break
                    lines_buffer.append(line)
            except queue.Empty:
                pass

            # Clear the log window
            log_win.erase()

            height = max_y - 1
            visible_lines = lines_buffer[
                -(height + scroll_pos) : len(lines_buffer) - scroll_pos
            ]

            row = 0
            for ln in visible_lines:
                if log_filter.passes_filters(ln):
                    text_str = format_for_curses(log_filter, ln, max_x)
                    log_win.addstr(row, 0, text_str)
                    row += 1
                    if row >= height:
                        break

            log_win.refresh()

            status_win.erase()
            status_msg = (
                "[q] Quit  |  [f] Filter  |  Use Up/Down to scroll\n"
                f"Filters: keyword={log_filter.keyword}, severity={log_filter.severity},"
                f" date_from={log_filter.date_from}, date_to={log_filter.date_to}"
            )
            status_win.addstr(0, 0, status_msg[: max_x - 1])
            status_win.refresh()

            # Handle user input
            try:
                ch = stdscr.getch()
                if ch == curses.KEY_UP:
                    if scroll_pos < len(lines_buffer):
                        scroll_pos += 1
                elif ch == curses.KEY_DOWN:
                    if scroll_pos > 0:
                        scroll_pos -= 1
                elif ch in [ord("q"), ord("Q")]:
                    stop_event.set()
                elif ch in [ord("f"), ord("F")]:
                    update_filters_curses(stdscr, log_filter)
                    scroll_pos = 0
            except:
                pass

            curses.napms(100)  # Sleep 100ms to reduce CPU usage

    def format_for_curses(log_filter_obj: LogFilter, line: str, max_width: int) -> str:
        """
        Convert the line into a curses-friendly color-coded string (simple approach).
        """
        prefix = ""
        if "CRITICAL" in line:
            prefix = "[CRITICAL] "
        elif "ERROR" in line:
            prefix = "[ERROR] "
        elif "WARNING" in line:
            prefix = "[WARNING] "
        elif "INFO" in line:
            prefix = "[INFO] "
        elif "DEBUG" in line:
            prefix = "[DEBUG] "

        highlighted_line = line
        if log_filter_obj.keyword:
            try:
                pattern = re.compile(log_filter_obj.keyword, re.IGNORECASE)
                highlighted_line = pattern.sub(r"<<\1>>", line)
            except re.error:
                substr = log_filter_obj.keyword
                highlighted_line = line.replace(substr, f"<<{substr}>>")

        display_str = prefix + highlighted_line
        if len(display_str) > max_width:
            display_str = display_str[: max_width - 1]
        return display_str

    def update_filters_curses(stdscr, log_filter_obj: LogFilter):
        curses.echo()
        max_y, max_x = stdscr.getmaxyx()
        popup_height = 7
        popup_width = max_x - 4
        start_y = (max_y - popup_height) // 2
        start_x = (max_x - popup_width) // 2

        popup = curses.newwin(popup_height, popup_width, start_y, start_x)
        popup.border()
        popup.addstr(1, 2, "Update Filters (leave blank to keep current)")
        popup.refresh()

        def prompt_line(row, label, current_value):
            popup.addstr(row, 2, f"{label} (current: {current_value}): ")
            popup.clrtoeol()
            popup.refresh()
            val = popup.getstr(
                row, len(label) + len(" (current: )") + 3 + len(str(current_value))
            )
            return val.decode("utf-8").strip()

        new_keyword = prompt_line(2, "Keyword", log_filter_obj.keyword)
        new_severity = prompt_line(3, "Severity", log_filter_obj.severity)
        new_date_from = prompt_line(4, "Date from YYYY-MM-DD", log_filter_obj.date_from)
        new_date_to = prompt_line(5, "Date to YYYY-MM-DD", log_filter_obj.date_to)

        if new_keyword:
            log_filter_obj.keyword = new_keyword
        if new_severity:
            log_filter_obj.severity = new_severity.upper().strip()
        if new_date_from:
            log_filter_obj.date_from = new_date_from.strip()
        if new_date_to:
            log_filter_obj.date_to = new_date_to.strip()

        curses.noecho()
        popup.clear()
        popup.refresh()
        del popup

    curses.wrapper(curses_main)
    stop_event.set()
    reader_thread.join()


###############################################################################
# DEFAULT BEHAVIOR: If no subcommand is provided, launch TUI
###############################################################################
@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    """
    By default (no arguments passed), launch TUI.
    Otherwise, run the requested subcommand (e.g., 'monitor').
    """
    if ctx.invoked_subcommand is None:
        # No subcommand means user just ran "python log-monitor.py"
        ctx.invoke(tui)
        raise typer.Exit()


###############################################################################
# MAIN
###############################################################################
if __name__ == "__main__":
    app()
