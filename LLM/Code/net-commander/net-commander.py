#!/usr/bin/env python3
"""
net_commander.py

A cross-platform, menu-driven "Swiss Army Knife" for basic network analysis
and troubleshooting, supporting both Typer-based CLI subcommands (with Rich formatting)
and a curses-based interactive TUI.

Features:
    - By default, if no arguments are passed, the TUI is launched.
    - You can explicitly launch the TUI by running `./net_commander.py tui`.
    - Otherwise, invoke subcommands (port-scan, ping, etc.) for Rich CLI output.

Author: dunamismax
Version: 5.1.0 (Typer + curses + Rich + Default TUI mode)
"""

import sys
import time
import socket
import platform
import subprocess
import ipaddress

from typing import List, Optional

import typer
from rich.console import Console

import requests
import dns.resolver

try:
    from scapy.layers.inet import IP, ICMP, traceroute
    from scapy.sendrecv import sr1, sr
except ImportError:
    IP = None
    ICMP = None
    traceroute = None
    sr1 = None
    sr = None

import curses
import curses.textpad

# ------------------------------------------------------------------------------
#                          Typer App & Rich Console
# ------------------------------------------------------------------------------
app = typer.Typer(
    help="net-commander: A basic network analysis toolkit with CLI & TUI modes."
)
console = Console()

# ------------------------------------------------------------------------------
#                          Common/Utility Functions
# ------------------------------------------------------------------------------


def detect_os() -> str:
    """
    Detect the current operating system.
    """
    return platform.system()


def run_command(command: str) -> str:
    """
    Execute a system command and return its output.
    """
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Command failed with error: {e.stderr.strip()}"


def scapy_ping_sweep(cidr: str) -> List[str]:
    """
    Perform an ICMP ping sweep of a network using Scapy.
    """
    if not IP or not ICMP or not sr:
        raise ImportError("Scapy is not installed or not imported.")
    network = ipaddress.ip_network(cidr, strict=False)
    hosts = [str(ip) for ip in network.hosts()]

    answered, _unanswered = sr(IP(dst=hosts) / ICMP(), timeout=1, verbose=0)
    active_hosts = []
    for _, rcv in answered:
        active_hosts.append(rcv.src)

    return active_hosts


def fallback_host_discovery(cidr: str):
    """
    Fallback method for host discovery using system pings.
    Returns a tuple: (list_of_active_hosts, multiline_output_string).
    """
    network = ipaddress.ip_network(cidr, strict=False)
    os_type = detect_os()
    active_hosts = []
    output_lines = []

    for ip_obj in network.hosts():
        ip_str = str(ip_obj)
        if os_type == "Windows":
            cmd = f"ping -n 1 -w 500 {ip_str}"
        else:
            cmd = f"ping -c 1 -W 1 {ip_str}"

        output = run_command(cmd)

        # Checking TTL or bytes received in the output
        if "TTL=" in output.upper() or "BYTES=" in output.upper():
            active_hosts.append(ip_str)
            output_lines.append(f"[ACTIVE] {ip_str}")
        else:
            output_lines.append(f"[INACTIVE] {ip_str}")

    return active_hosts, "\n".join(output_lines)


def system_ping(target: str, count: int) -> str:
    """
    Fallback to system ping if Scapy-based ping is not possible.
    """
    os_type = detect_os()
    if os_type == "Windows":
        cmd = f"ping -n {count} {target}"
    else:
        cmd = f"ping -c {count} {target}"
    return run_command(cmd)


def system_traceroute(target: str) -> str:
    """
    Fallback to the system traceroute command.
    """
    os_type = detect_os()
    if os_type == "Windows":
        cmd = f"tracert {target}"
    else:
        cmd = f"traceroute {target}"
    return run_command(cmd)


# ------------------------------------------------------------------------------
#                   Network Action Functions (called by CLI/TUI)
# ------------------------------------------------------------------------------


def do_port_scan(target: str, ports: List[int], timeout: float = 0.5) -> str:
    """
    Perform a basic TCP port scan on the given target for specified ports.
    Returns a multiline string with results.
    """
    results = [f"Starting port scan on {target}..."]
    for port in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            try:
                result = s.connect_ex((target, port))
                if result == 0:
                    results.append(f"Port {port}: OPEN")
                else:
                    results.append(f"Port {port}: CLOSED")
            except Exception as exc:
                results.append(f"Port {port} ERROR: {exc}")
    results.append("Port scan complete.")
    return "\n".join(results)


def do_host_discovery(cidr: str) -> str:
    """
    Perform host discovery on a CIDR. Tries Scapy-based approach first,
    then system ping fallback. Returns a multiline string with results.
    """
    messages = [f"Scanning {cidr}..."]
    try:
        active_hosts = scapy_ping_sweep(cidr)
        if active_hosts:
            messages.append("[ACTIVE HOSTS]")
            messages.extend(active_hosts)
        else:
            messages.append("No active hosts found.")
    except PermissionError:
        messages.append(
            "Scapy requires elevated privileges. Using system ping fallback..."
        )
        hosts, output = fallback_host_discovery(cidr)
        messages.append(output)
        if hosts:
            messages.append("\n[ACTIVE HOSTS]")
            messages.extend(hosts)
        else:
            messages.append("No active hosts found.")
    except Exception as exc:
        messages.append(f"Error using Scapy: {exc}\nFalling back to system ping...")
        hosts, output = fallback_host_discovery(cidr)
        messages.append(output)
        if hosts:
            messages.append("\n[ACTIVE HOSTS]")
            messages.extend(hosts)
        else:
            messages.append("No active hosts found.")
    return "\n".join(messages)


def do_ping(target: str, count: int = 4) -> str:
    """
    Ping a target using Scapy if possible, otherwise fallback to system ping.
    Returns a multiline string with ping results.
    """
    messages = [f"Pinging {target}..."]
    if IP and ICMP and sr1:
        try:
            for i in range(count):
                resp = sr1(IP(dst=target) / ICMP(), timeout=1, verbose=0)
                if resp is None:
                    messages.append(f"{i+1}. Request timed out")
                else:
                    messages.append(f"{i+1}. Reply from {resp.src} TTL={resp.ttl}")
        except PermissionError:
            messages.append(
                "Scapy requires elevated privileges. Falling back to system ping..."
            )
            messages.append(system_ping(target, count))
        except Exception as exc:
            messages.append(f"Scapy ping error: {exc}")
            messages.append(system_ping(target, count))
    else:
        messages.append("Scapy is unavailable; using system ping fallback...")
        messages.append(system_ping(target, count))
    return "\n".join(messages)


def do_tracer(target: str) -> str:
    """
    Perform a traceroute using Scapy if possible, otherwise fallback.
    Returns a multiline string with traceroute steps.
    """
    messages = [f"Tracing route to {target}..."]
    if traceroute:
        try:
            ans, _unans = traceroute(target, maxttl=20, verbose=0)
            for snd, rcv in ans:
                messages.append(f"{snd.ttl}. {rcv.src}")
        except PermissionError:
            messages.append(
                "Scapy traceroute requires elevated privileges. Falling back..."
            )
            messages.append(system_traceroute(target))
        except Exception as exc:
            messages.append(f"Scapy traceroute error: {exc}")
            messages.append(system_traceroute(target))
    else:
        messages.append("Scapy traceroute is unavailable; using system fallback.")
        messages.append(system_traceroute(target))
    return "\n".join(messages)


def do_dns_lookup(domain: str, record_type: str = "A") -> str:
    """
    Perform a DNS lookup using dnspython. Returns multiline string with results.
    """
    messages = [f"Looking up {record_type} record(s) for {domain}..."]
    try:
        answers = dns.resolver.resolve(domain, record_type)
        for rdata in answers:
            messages.append(rdata.to_text())
    except dns.resolver.NXDOMAIN:
        messages.append("Domain does not exist.")
    except dns.resolver.NoAnswer:
        messages.append(f"No {record_type} records found.")
    except dns.exception.DNSException as exc:
        messages.append(f"DNS lookup error: {exc}")
    return "\n".join(messages)


def do_ip_config() -> str:
    """
    Display IP configuration via system commands.
    """
    os_type = detect_os()
    if os_type == "Windows":
        cmd = "ipconfig"
    else:
        cmd = "ip addr show"
    return run_command(cmd)


def do_http_check(url: str) -> str:
    """
    Perform a basic HTTP GET request. Returns multiline string with results.
    """
    if not (url.startswith("http://") or url.startswith("https://")):
        url = f"http://{url}"

    messages = [f"Checking {url}..."]
    start_time = time.time()
    try:
        response = requests.get(url, timeout=5)
        elapsed = time.time() - start_time
        messages.append(
            f"HTTP GET {url} - Status: {response.status_code}, "
            f"Time: {elapsed:.2f} seconds"
        )
    except requests.exceptions.RequestException as exc:
        messages.append(f"HTTP check failed: {exc}")
    return "\n".join(messages)


def do_about() -> str:
    """
    Return a string with about information.
    """
    info = (
        "net-commander: A cross-platform, menu-driven network toolkit.\n\n"
        "Features:\n"
        "  1) Port Scanning\n"
        "  2) Host Discovery (Scapy-based ICMP sweeps)\n"
        "  3) Ping (Scapy-based)\n"
        "  4) Traceroute (Scapy-based)\n"
        "  5) DNS Lookup (dnspython)\n"
        "  6) Show IP Configuration\n"
        "  7) HTTP Check\n\n"
        "Author: dunamismax\n"
        "Version: 5.1.0 (Typer + curses + Rich + Default TUI mode)\n"
    )
    return info


# ------------------------------------------------------------------------------
#                          curses-based TUI
# ------------------------------------------------------------------------------

MENU_ITEMS = [
    "Port Scan",
    "Host Discovery",
    "Ping Host",
    "Traceroute",
    "DNS Lookup",
    "Show IP Configuration",
    "HTTP Check",
    "About",
    "Exit",
]


def curses_text_input(stdscr, prompt: str) -> str:
    """
    Display a prompt and collect text input from the user in curses.
    Returns the entered string.
    """
    stdscr.clear()
    curses.echo()
    stdscr.addstr(0, 0, prompt)
    stdscr.refresh()
    user_input = stdscr.getstr(1, 0, 60).decode("utf-8").strip()
    curses.noecho()
    return user_input


def curses_menu(stdscr):
    """
    Main loop for the curses-based menu. Handles user navigation and actions.
    """
    curses.curs_set(0)  # Hide the cursor
    current_row = 0
    max_row = len(MENU_ITEMS) - 1

    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        title_str = "--- net-commander (Interactive Mode) ---"
        stdscr.addstr(0, 0, title_str, curses.color_pair(0) | curses.A_BOLD)

        # Render menu items
        for idx, item in enumerate(MENU_ITEMS):
            x = 2
            y = idx + 2
            if idx == current_row:
                stdscr.attron(curses.A_REVERSE)
                stdscr.addstr(y, x, f"{idx+1}) {item}")
                stdscr.attroff(curses.A_REVERSE)
            else:
                stdscr.addstr(y, x, f"{idx+1}) {item}")

        stdscr.refresh()

        # Wait for user input
        key = stdscr.getch()

        if key == curses.KEY_UP:
            current_row = (current_row - 1) % (max_row + 1)
        elif key == curses.KEY_DOWN:
            current_row = (current_row + 1) % (max_row + 1)
        elif key in (curses.KEY_ENTER, 10, 13):
            action_result = handle_menu_action(stdscr, current_row)
            if action_result == "EXIT":
                break
        else:
            # Ignore other keys
            pass


def handle_menu_action(stdscr, index: int):
    """
    Execute the chosen menu action. If 'Exit' is chosen, return 'EXIT'.
    """
    if index == 0:
        # Port Scan
        target = curses_text_input(stdscr, "Enter target hostname or IP: ")
        ports_str = curses_text_input(
            stdscr, "Enter space-separated ports (e.g. 22 80 443): "
        )
        try:
            ports = [int(p.strip()) for p in ports_str.split()]
        except ValueError:
            show_output(stdscr, "Invalid ports. Please enter numeric values.")
            return
        result = do_port_scan(target, ports)
        show_output(stdscr, result)

    elif index == 1:
        # Host Discovery
        cidr = curses_text_input(stdscr, "Enter CIDR notation (e.g. 192.168.1.0/24): ")
        result = do_host_discovery(cidr)
        show_output(stdscr, result)

    elif index == 2:
        # Ping Host
        target = curses_text_input(stdscr, "Enter host/IP to ping: ")
        count_str = curses_text_input(stdscr, "Number of pings (default=4): ")
        try:
            count_num = int(count_str) if count_str else 4
        except ValueError:
            count_num = 4
        result = do_ping(target, count_num)
        show_output(stdscr, result)

    elif index == 3:
        # Traceroute
        target = curses_text_input(stdscr, "Enter host/IP for traceroute: ")
        result = do_tracer(target)
        show_output(stdscr, result)

    elif index == 4:
        # DNS Lookup
        domain = curses_text_input(stdscr, "Enter domain (e.g. example.com): ")
        record_type = curses_text_input(stdscr, "Enter record type (default=A): ")
        record_type = record_type if record_type else "A"
        result = do_dns_lookup(domain, record_type)
        show_output(stdscr, result)

    elif index == 5:
        # IP Config
        result = do_ip_config()
        show_output(stdscr, result)

    elif index == 6:
        # HTTP Check
        url = curses_text_input(stdscr, "Enter URL (e.g. https://www.google.com): ")
        result = do_http_check(url)
        show_output(stdscr, result)

    elif index == 7:
        # About
        result = do_about()
        show_output(stdscr, result)

    elif index == 8:
        # Exit
        return "EXIT"


def show_output(stdscr, text: str):
    """
    Display multiline output to the user. Wait for a keypress to return.
    """
    stdscr.clear()
    lines = text.split("\n")
    max_y, max_x = stdscr.getmaxyx()

    row = 0
    for line in lines:
        if row >= max_y - 2:
            break
        stdscr.addstr(row, 0, line[: max_x - 1])  # Crop line if needed
        row += 1

    stdscr.addstr(row + 1, 0, "Press any key to return to menu...")
    stdscr.refresh()
    stdscr.getch()


# ------------------------------------------------------------------------------
#                       Callback to Launch TUI if No Args
# ------------------------------------------------------------------------------
@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    If no subcommand is invoked, launch the curses-based TUI by default.
    """
    if not ctx.invoked_subcommand:
        curses.wrapper(curses_menu)


# ------------------------------------------------------------------------------
#                          TUI Command
# ------------------------------------------------------------------------------
@app.command("tui")
def tui_command():
    """
    Explicitly launch the full-screen, interactive curses menu.
    """
    curses.wrapper(curses_menu)


# ------------------------------------------------------------------------------
#                          Other CLI Subcommands
# ------------------------------------------------------------------------------
@app.command("port-scan")
def port_scan_cli(
    target: str = typer.Argument(..., help="Target hostname or IP to scan"),
    ports: List[int] = typer.Argument(..., help="List of ports to scan"),
    timeout: float = typer.Option(0.5, help="Socket timeout (seconds)"),
):
    """
    Perform a basic TCP port scan on the given target.
    """
    console.print(f"[bold magenta]Starting port scan on[/bold magenta] {target}")
    result = do_port_scan(target, ports, timeout)
    console.print(result, style="green")


@app.command("host-discovery")
def host_discovery_cli(
    cidr: str = typer.Argument(..., help="CIDR notation, e.g. 192.168.1.0/24")
):
    """
    Perform an ICMP ping sweep (Scapy if available, else system ping).
    """
    console.print(f"[bold magenta]Discovering hosts in[/bold magenta] {cidr}")
    result = do_host_discovery(cidr)
    console.print(result, style="green")


@app.command("ping")
def ping_cli(
    target: str = typer.Argument(..., help="Host/IP to ping"),
    count: int = typer.Option(4, help="Number of ping attempts"),
):
    """
    Ping a target host. Uses Scapy if available, else system ping.
    """
    console.print(f"[bold magenta]Pinging[/bold magenta] {target}")
    result = do_ping(target, count)
    console.print(result, style="green")


@app.command("traceroute")
def traceroute_cli(
    target: str = typer.Argument(..., help="Host/IP for traceroute"),
):
    """
    Perform a traceroute (Scapy if available, else system traceroute).
    """
    console.print(f"[bold magenta]Tracing route to[/bold magenta] {target}")
    result = do_tracer(target)
    console.print(result, style="green")


@app.command("dns-lookup")
def dns_lookup_cli(
    domain: str = typer.Argument(..., help="Domain, e.g. example.com"),
    record_type: str = typer.Option("A", help="Record type (A, MX, NS, etc.)"),
):
    """
    Perform a DNS lookup using dnspython.
    """
    console.print(
        f"[bold magenta]Looking up {record_type} record(s) for[/bold magenta] {domain}"
    )
    result = do_dns_lookup(domain, record_type)
    console.print(result, style="green")


@app.command("ip-config")
def ip_config_cli():
    """
    Show the IP configuration of the current system.
    """
    console.print("[bold magenta]Showing IP Configuration...[/bold magenta]")
    result = do_ip_config()
    console.print(result, style="green")


@app.command("http-check")
def http_check_cli(
    url: str = typer.Argument(..., help="URL to check, e.g. http://www.google.com")
):
    """
    Perform a simple HTTP GET check on a URL.
    """
    console.print(f"[bold magenta]HTTP check for[/bold magenta] {url}")
    result = do_http_check(url)
    console.print(result, style="green")


@app.command("about")
def about_cli():
    """
    Display 'About' information for net-commander.
    """
    result = do_about()
    console.print(result, style="green")


# ------------------------------------------------------------------------------
#                          Main Entry Point
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    app()
