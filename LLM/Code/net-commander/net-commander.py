"""
net_commander_textual.py

A cross-platform, menu-driven "Swiss Army Knife" for basic network analysis
and troubleshooting, rewritten using the Textual TUI framework.

Features:
    1. Port Scanning (socket)
    2. Host Discovery (Scapy-based ICMP sweep)
    3. Ping (Scapy-based or system ping fallback)
    4. Traceroute (Scapy-based or system command fallback)
    5. DNS Lookup (dnspython)
    6. Show IP Configuration
    7. HTTP Check (requests)
    8. About
    9. Exit

Author: dunamismax
Version: 2.0.0 (Textual version)

Note:
    - Scapy operations may require elevated privileges.
    - For large subnets, ICMP sweeps/traceroutes can take noticeable time.
"""

import platform
import subprocess
import socket
import sys
import time
import ipaddress

# External libraries
import requests
import dns.resolver
from scapy.layers.inet import IP, ICMP, TCP, traceroute
from scapy.sendrecv import sr1, sr

# Textual imports
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Header,
    Footer,
    Button,
    Static,
    Input,
    TextLog,
    Label,
    MenuButton,
)

# ------------- Utility functions (same logic as original) ------------- #


def detect_os() -> str:
    """
    Detect the current operating system.

    Returns:
        str: A string representing the current OS ('Windows', 'Linux', 'Darwin', etc.).
    """
    return platform.system()


def run_command(command: str) -> str:
    """
    Execute a system command and return its output.

    Args:
        command (str): The command to execute.

    Returns:
        str: The standard output of the command, or an error message if the command fails.
    """
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Command failed with error: {e.stderr.strip()}"


def scapy_ping_sweep(cidr: str):
    """
    Perform an ICMP ping sweep of a network using Scapy.
    This can require elevated privileges (root or Administrator).

    Args:
        cidr (str): CIDR notation of the subnet to scan.
    """
    network = ipaddress.ip_network(cidr, strict=False)
    hosts = [str(ip) for ip in network.hosts()]

    answered, _unanswered = sr(
        IP(dst=hosts) / ICMP(), timeout=1, verbose=0  # Suppress Scapy's console output
    )
    active_hosts = []
    for snd, rcv in answered:
        active_hosts.append(rcv.src)

    return active_hosts


def fallback_host_discovery(cidr: str):
    """
    Fallback method for host discovery using system pings if Scapy is not available
    or insufficient privileges are encountered.

    Args:
        cidr (str): CIDR notation of the subnet to scan.
    """
    network = ipaddress.ip_network(cidr, strict=False)
    os_type = detect_os()
    active_hosts = []
    output_lines = []

    for ip in network.hosts():
        if os_type == "Windows":
            cmd = f"ping -n 1 -w 500 {ip}"
        else:
            cmd = f"ping -c 1 -W 1 {ip}"

        output = run_command(cmd)
        # Checking TTL or bytes received
        if "TTL=" in output.upper() or "BYTES=" in output.upper():
            active_hosts.append(str(ip))
            output_lines.append(f"[ACTIVE] {ip}")
        else:
            output_lines.append(f"[INACTIVE] {ip}")

    return active_hosts, "\n".join(output_lines)


def system_ping(target: str, count: int) -> str:
    """
    Fallback to system ping if Scapy-based ping is not possible.

    Args:
        target (str): The host or IP address to ping.
        count (int): Number of ping attempts.

    Returns:
        str: Command output from the ping operation.
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

    Args:
        target (str): The host/IP to traceroute.

    Returns:
        str: The output from the system traceroute command.
    """
    os_type = detect_os()
    if os_type == "Windows":
        cmd = f"tracert {target}"
    else:
        cmd = f"traceroute {target}"
    return run_command(cmd)


# ------------- Textual Screens for each operation ------------- #


class PortScanScreen(Screen):
    """Screen for performing a basic TCP port scan."""

    def compose(self) -> ComposeResult:
        yield Label("Port Scan", id="menu-title")
        yield Label("Enter target hostname or IP:")
        self.target_input = Input(placeholder="e.g. 192.168.1.10")
        yield self.target_input

        yield Label("Enter ports (space separated):")
        self.port_input = Input(placeholder="e.g. 22 80 443")
        yield self.port_input

        yield Button("Start Scan", id="start-scan")
        yield Button("Return to Main Menu", id="return")

        self.output_log = TextLog()
        yield self.output_log

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-scan":
            target = self.target_input.value.strip()
            port_str = self.port_input.value.strip()

            if not target or not port_str:
                self.output_log.write("[bold red]Target/ports missing.[/bold red]")
                return

            # Parse ports
            ports = []
            for p in port_str.split():
                try:
                    ports.append(int(p))
                except ValueError:
                    self.output_log.write(
                        f"[italic yellow]Invalid port '{p}' skipped.[/italic yellow]"
                    )

            if not ports:
                self.output_log.write("[bold red]No valid ports to scan.[/bold red]")
                return

            self.output_log.write(f"[bold]Starting port scan on {target}...[/bold]")
            for port in ports:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.5)
                    try:
                        result = s.connect_ex((target, port))
                        if result == 0:
                            self.output_log.write(f"Port {port}: [green]OPEN[/green]")
                        else:
                            self.output_log.write(f"Port {port}: [red]CLOSED[/red]")
                    except Exception as e:
                        self.output_log.write(
                            f"Port {port} [yellow]ERROR: {e}[/yellow]"
                        )

            self.output_log.write("[bold green]Port scan complete.[/bold green]")

        elif event.button.id == "return":
            self.app.pop_screen()


class HostDiscoveryScreen(Screen):
    """Screen for performing a simple host discovery on a subnet via ICMP sweeps."""

    def compose(self) -> ComposeResult:
        yield Label("Host Discovery", id="menu-title")
        yield Label("Enter subnet in CIDR notation:")
        self.cidr_input = Input(placeholder="e.g. 192.168.1.0/24")
        yield self.cidr_input

        yield Button("Start Discovery", id="start-discovery")
        yield Button("Return to Main Menu", id="return")

        self.output_log = TextLog()
        yield self.output_log

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-discovery":
            cidr = self.cidr_input.value.strip()
            if not cidr:
                self.output_log.write("[bold red]CIDR is required.[/bold red]")
                return

            self.output_log.write(f"[bold]Scanning {cidr}...[/bold]")
            try:
                active_hosts = scapy_ping_sweep(cidr)
                if active_hosts:
                    self.output_log.write("[bold green]Active Hosts:[/bold green]")
                    for host in active_hosts:
                        self.output_log.write(f"  [green]{host}[/green]")
                else:
                    self.output_log.write(
                        "[bold yellow]No active hosts found.[/bold yellow]"
                    )
            except PermissionError:
                self.output_log.write(
                    "[bold red]Scapy requires elevated privileges. Using system ping fallback...[/bold red]"
                )
                hosts, output = fallback_host_discovery(cidr)
                self.output_log.write(output)
                if hosts:
                    self.output_log.write("\n[bold green]Active hosts:[/bold green]")
                    for host in hosts:
                        self.output_log.write(f"[green]  {host}[/green]")
                else:
                    self.output_log.write(
                        "[bold yellow]No active hosts found.[/bold yellow]"
                    )
            except Exception as e:
                self.output_log.write(
                    f"[bold red]Error using Scapy: {e}\nFalling back to system ping...[/bold red]"
                )
                hosts, output = fallback_host_discovery(cidr)
                self.output_log.write(output)
                if hosts:
                    self.output_log.write("\n[bold green]Active hosts:[/bold green]")
                    for host in hosts:
                        self.output_log.write(f"[green]  {host}[/green]")
                else:
                    self.output_log.write(
                        "[bold yellow]No active hosts found.[/bold yellow]"
                    )

        elif event.button.id == "return":
            self.app.pop_screen()


class PingScreen(Screen):
    """Screen for pinging a specified host."""

    def compose(self) -> ComposeResult:
        yield Label("Ping Host", id="menu-title")
        yield Label("Enter host/IP to ping:")
        self.host_input = Input(placeholder="e.g. google.com")
        yield self.host_input

        yield Label("Number of pings (default 4):")
        self.count_input = Input()
        yield self.count_input

        yield Button("Start Ping", id="start-ping")
        yield Button("Return to Main Menu", id="return")

        self.output_log = TextLog()
        yield self.output_log

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-ping":
            target = self.host_input.value.strip()
            count_str = self.count_input.value.strip()

            try:
                count = int(count_str) if count_str else 4
            except ValueError:
                count = 4
                self.output_log.write(
                    "[bold yellow]Invalid count; using default of 4.[/bold yellow]"
                )

            if not target:
                self.output_log.write("[bold red]No target provided.[/bold red]")
                return

            self.output_log.write(f"[bold]Pinging {target}...[/bold]")
            try:
                # Attempt Scapy-based ping
                for i in range(count):
                    resp = sr1(IP(dst=target) / ICMP(), timeout=1, verbose=0)
                    if resp is None:
                        self.output_log.write(f"{i+1}. [red]Request timed out[/red]")
                    else:
                        self.output_log.write(
                            f"{i+1}. Reply from {resp.src} TTL={resp.ttl}"
                        )
            except PermissionError:
                self.output_log.write(
                    "[bold red]Scapy requires elevated privileges. Falling back to system ping.[/bold red]"
                )
                self.output_log.write(system_ping(target, count))
            except Exception as e:
                self.output_log.write(f"[bold red]Scapy ping error: {e}[/bold red]")
                self.output_log.write(system_ping(target, count))

        elif event.button.id == "return":
            self.app.pop_screen()


class TracerouteScreen(Screen):
    """Screen for performing a traceroute to a specified target."""

    def compose(self) -> ComposeResult:
        yield Label("Traceroute", id="menu-title")
        yield Label("Enter host/IP for traceroute:")
        self.host_input = Input(placeholder="e.g. google.com")
        yield self.host_input

        yield Button("Start Traceroute", id="start-traceroute")
        yield Button("Return to Main Menu", id="return")

        self.output_log = TextLog()
        yield self.output_log

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-traceroute":
            target = self.host_input.value.strip()
            if not target:
                self.output_log.write("[bold red]No target provided.[/bold red]")
                return

            self.output_log.write(f"[bold]Tracing route to {target}...[/bold]")
            try:
                ans, unans = traceroute(target, maxttl=20, verbose=0)
                for snd, rcv in ans:
                    self.output_log.write(f"[green]{snd.ttl} {rcv.src}[/green]")
            except PermissionError:
                self.output_log.write(
                    "[bold red]Scapy traceroute requires elevated privileges. Falling back to system traceroute.[/bold red]"
                )
                self.output_log.write(system_traceroute(target))
            except Exception as e:
                self.output_log.write(
                    f"[bold red]Scapy traceroute error: {e}[/bold red]"
                )
                self.output_log.write(system_traceroute(target))

        elif event.button.id == "return":
            self.app.pop_screen()


class DNSLookupScreen(Screen):
    """Screen for performing a DNS lookup using dnspython."""

    def compose(self) -> ComposeResult:
        yield Label("DNS Lookup", id="menu-title")
        yield Label("Enter domain (e.g. example.com):")
        self.domain_input = Input()
        yield self.domain_input

        yield Label("Enter DNS record type (default A):")
        self.record_type_input = Input()
        yield self.record_type_input

        yield Button("Lookup", id="lookup")
        yield Button("Return to Main Menu", id="return")

        self.output_log = TextLog()
        yield self.output_log

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "lookup":
            domain = self.domain_input.value.strip()
            record_type = self.record_type_input.value.strip()
            if not domain:
                self.output_log.write("[bold red]No domain provided.[/bold red]")
                return

            if not record_type:
                record_type = "A"

            self.output_log.write(
                f"[bold]Looking up {record_type} records for {domain}...[/bold]"
            )
            try:
                answers = dns.resolver.resolve(domain, record_type)
                for rdata in answers:
                    self.output_log.write(f"[green]{rdata.to_text()}[/green]")
            except dns.resolver.NXDOMAIN:
                self.output_log.write("[red]Domain does not exist.[/red]")
            except dns.resolver.NoAnswer:
                self.output_log.write(
                    f"[yellow]No {record_type} records found.[/yellow]"
                )
            except dns.exception.DNSException as e:
                self.output_log.write(f"[red]DNS lookup error: {e}[/red]")

        elif event.button.id == "return":
            self.app.pop_screen()


class IPConfigScreen(Screen):
    """Screen for displaying IP configuration."""

    def compose(self) -> ComposeResult:
        yield Label("Show IP Configuration", id="menu-title")
        yield Button("Retrieve Configuration", id="retrieve")
        yield Button("Return to Main Menu", id="return")

        self.output_log = TextLog()
        yield self.output_log

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "retrieve":
            os_type = detect_os()
            if os_type == "Windows":
                cmd = "ipconfig"
            else:
                cmd = "ip addr show"
            output = run_command(cmd)
            self.output_log.write(output)

        elif event.button.id == "return":
            self.app.pop_screen()


class HTTPCheckScreen(Screen):
    """Screen for performing a basic HTTP check via requests."""

    def compose(self) -> ComposeResult:
        yield Label("HTTP Check", id="menu-title")
        yield Label("Enter a URL (e.g., https://www.google.com):")
        self.url_input = Input()
        yield self.url_input

        yield Button("Check", id="check")
        yield Button("Return to Main Menu", id="return")

        self.output_log = TextLog()
        yield self.output_log

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "check":
            url = self.url_input.value.strip()
            if not url:
                self.output_log.write("[bold red]No URL provided.[/bold red]")
                return

            if not (url.startswith("http://") or url.startswith("https://")):
                url = f"http://{url}"

            start_time = time.time()
            try:
                response = requests.get(url, timeout=5)
                elapsed = time.time() - start_time
                self.output_log.write(
                    f"[bold green]HTTP GET {url} - Status: {response.status_code}, "
                    f"Time: {elapsed:.2f} seconds[/bold green]"
                )
            except requests.exceptions.RequestException as e:
                self.output_log.write(f"[bold red]HTTP check failed: {e}[/bold red]")

        elif event.button.id == "return":
            self.app.pop_screen()


class AboutScreen(Screen):
    """Screen displaying information about the net-commander tool."""

    def compose(self) -> ComposeResult:
        yield Label("About net-commander", id="menu-title")
        about_text = (
            "[bold]net-commander:[/bold] A cross-platform, menu-driven network toolkit.\n\n"
            "Features:\n"
            "  1) Port Scanning\n"
            "  2) Host Discovery (Scapy-based ICMP sweeps)\n"
            "  3) Ping (Scapy-based)\n"
            "  4) Traceroute (Scapy-based)\n"
            "  5) DNS Lookup (dnspython)\n"
            "  6) Show IP Configuration\n"
            "  7) HTTP Check\n\n"
            "Author: dunamismax\n"
            "Version: 2.0.0\n"
        )
        yield Label(about_text)
        yield Button("Return to Main Menu", id="return")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "return":
            self.app.pop_screen()


# ------------- Main Menu Screen ------------- #


class MainMenu(Screen):
    """Main menu screen for net-commander."""

    def compose(self) -> ComposeResult:
        yield Label("net-commander - Main Menu", id="menu-title")
        yield Button("1) Port Scan", id="1")
        yield Button("2) Host Discovery", id="2")
        yield Button("3) Ping Host", id="3")
        yield Button("4) Traceroute", id="4")
        yield Button("5) DNS Lookup", id="5")
        yield Button("6) Show IP Configuration", id="6")
        yield Button("7) HTTP Check", id="7")
        yield Button("8) About net-commander", id="8")
        yield Button("9) Exit", id="9")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        choice = event.button.id
        if choice == "1":
            self.app.push_screen(PortScanScreen())
        elif choice == "2":
            self.app.push_screen(HostDiscoveryScreen())
        elif choice == "3":
            self.app.push_screen(PingScreen())
        elif choice == "4":
            self.app.push_screen(TracerouteScreen())
        elif choice == "5":
            self.app.push_screen(DNSLookupScreen())
        elif choice == "6":
            self.app.push_screen(IPConfigScreen())
        elif choice == "7":
            self.app.push_screen(HTTPCheckScreen())
        elif choice == "8":
            self.app.push_screen(AboutScreen())
        elif choice == "9":
            self.app.exit()
        else:
            pass


# ------------- Main Application Class ------------- #


class NetCommander(App):
    """
    Textual TUI app for net-commander.
    Press 'q' at any time to exit from any screen (Textual default key binding).
    """

    CSS = """
    #menu-title {
        color: cyan;
        text-align: center;
        padding: 1 0;
    }

    TextLog {
        height: 1fr;
        margin-top: 1;
        border: tall $accent;
        overflow: auto;
    }

    Button {
        margin: 1;
    }

    Label {
        margin: 1 0 0 0;
    }
    """

    def on_mount(self) -> None:
        """Called once the app is ready; load the main menu screen."""
        self.push_screen(MainMenu())

    def compose(self) -> ComposeResult:
        """Build the app layout: a vertical stack with Header, main container, and Footer."""
        yield Header()
        # A container for screens will be rendered in the middle automatically.
        yield Footer()


if __name__ == "__main__":
    NetCommander().run()
