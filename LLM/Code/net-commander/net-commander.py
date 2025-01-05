#!/usr/bin/env python3
"""
net-commander.py

A cross-platform, menu-driven "Swiss Army Knife" for basic network analysis
and troubleshooting.

Features:
    1. Port Scanning (socket)
    2. Host Discovery (Scapy-based ICMP sweep)
    3. Ping (Scapy-based or system ping fallback)
    4. Traceroute (system command or Scapy-based fallback)
    5. DNS Lookup (dnspython)
    6. Show IP Configuration
    7. HTTP Check (requests)
    8. About
    9. Exit

Author: dunamismax
Version: 2.0.0
"""

import platform
import subprocess
import socket
import sys
import time
import ipaddress

# External libraries
import requests
from rich import print as rprint
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import dns.resolver
from scapy.layers.inet import IP, ICMP, TCP, traceroute
from scapy.sendrecv import sr1, sr

console = Console()


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


def port_scan():
    """
    Perform a basic TCP port scan on a specified target and ports
    using Python's built-in socket library.
    """
    target = input("Enter target hostname or IP: ").strip()
    port_str = input("Enter port(s) separated by spaces (e.g., 22 80 443): ").strip()

    if not port_str:
        rprint("[bold red]No ports provided. Returning to main menu.[/bold red]")
        return

    ports = []
    for p in port_str.split():
        try:
            ports.append(int(p))
        except ValueError:
            rprint(f"[italic yellow]Invalid port '{p}' skipped.[/italic yellow]")

    if not ports:
        rprint("[bold red]No valid ports to scan. Returning to main menu.[/bold red]")
        return

    rprint(f"\n[bold]Starting port scan on {target}...[/bold]\n")
    table = Table(title="Port Scan Results", show_lines=True)
    table.add_column("Port", justify="right")
    table.add_column("Status", justify="center")

    for port in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)  # Adjust timeout if needed
            try:
                result = s.connect_ex((target, port))
                if result == 0:
                    table.add_row(str(port), "[green]OPEN[/green]")
                else:
                    table.add_row(str(port), "[red]CLOSED[/red]")
            except KeyboardInterrupt:
                rprint("[bold red]\nUser interrupted scan.[/bold red]")
                return
            except Exception as e:
                table.add_row(str(port), f"[yellow]ERROR: {e}[/yellow]")

    console.print(table)
    rprint("\n[bold green]Port scan complete.[/bold green]")


def scapy_ping_sweep(cidr: str):
    """
    Perform an ICMP ping sweep of a network using Scapy.
    This can require elevated privileges (root or Administrator).

    Args:
        cidr (str): CIDR notation of the subnet to scan.
    """
    # Convert CIDR to ip_network object for iteration if needed
    network = ipaddress.ip_network(cidr, strict=False)
    hosts = [str(ip) for ip in network.hosts()]

    answered, unanswered = sr(
        IP(dst=hosts) / ICMP(), timeout=1, verbose=0  # Suppress Scapy's console output
    )
    active_hosts = []
    for snd, rcv in answered:
        active_hosts.append(rcv.src)

    return active_hosts


def host_discovery():
    """
    Perform a simple host discovery on a subnet using Scapy-based ICMP sweeps.
    Falls back to system ping if Scapy fails or user lacks privileges.
    """
    cidr = input("Enter a subnet in CIDR notation (e.g., 192.168.1.0/24): ").strip()
    try:
        ipaddress.ip_network(cidr, strict=False)
    except ValueError:
        rprint("[bold red]Invalid CIDR format. Returning to main menu.[/bold red]")
        return

    rprint(
        f"[bold]\nPerforming host discovery on {cidr} (this may take a while)...[/bold]"
    )
    try:
        active_hosts = scapy_ping_sweep(cidr)
        if active_hosts:
            rprint("[bold green]Active Hosts:[/bold green]")
            for host in active_hosts:
                rprint(f"  [green]{host}[/green]")
        else:
            rprint(
                "[bold yellow]No active hosts found using Scapy ping sweep.[/bold yellow]"
            )
    except PermissionError:
        rprint(
            "[bold red]Scapy requires elevated privileges for raw socket operations.\n"
            "Falling back to basic system ping sweep...[/bold red]\n"
        )
        fallback_host_discovery(cidr)
    except Exception as e:
        rprint(
            f"[bold red]Error using Scapy: {e}\nFalling back to basic system ping sweep...[/bold red]"
        )
        fallback_host_discovery(cidr)


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

    for ip in network.hosts():
        if os_type == "Windows":
            cmd = f"ping -n 1 -w 500 {ip}"
        else:
            cmd = f"ping -c 1 -W 1 {ip}"

        output = run_command(cmd)
        # Checking TTL or bytes received
        if "TTL=" in output.upper() or "BYTES=" in output.upper():
            active_hosts.append(str(ip))
            rprint(f"[green]  [ACTIVE] {ip}[/green]")
        else:
            rprint(f"[red]  [INACTIVE] {ip}[/red]")

    if not active_hosts:
        rprint("[bold yellow]\nNo active hosts found.[/bold yellow]")
    else:
        rprint("\n[bold green]Active hosts:[/bold green]")
        for host in active_hosts:
            rprint(f"  [green]{host}[/green]")


def ping_host():
    """
    Ping a given host a specified number of times using Scapy (preferred).
    Falls back to OS-native ping if Scapy fails.
    """
    target = input("Enter host/IP to ping: ").strip()
    count_str = input("Number of pings (default 4): ").strip()
    if not count_str:
        count = 4
    else:
        try:
            count = int(count_str)
        except ValueError:
            rprint(
                "[bold yellow]Invalid number of pings, using default (4).[/bold yellow]"
            )
            count = 4

    rprint(f"\n[bold]Pinging {target}...[/bold]\n")
    try:
        # Attempt Scapy-based ping
        for i in range(count):
            resp = sr1(IP(dst=target) / ICMP(), timeout=1, verbose=0)
            if resp is None:
                rprint(f"[red]{i+1}. Request timed out[/red]")
            else:
                rprint(f"[green]{i+1}. Reply from {resp.src} TTL={resp.ttl}[/green]")
    except PermissionError:
        rprint(
            "[bold red]Scapy requires elevated privileges. Falling back to system ping.[/bold red]"
        )
        system_ping(target, count)
    except Exception as e:
        rprint(f"[bold red]Scapy ping error: {e}[/bold red]")
        system_ping(target, count)


def system_ping(target: str, count: int):
    """
    Fallback to system ping if Scapy-based ping is not possible.

    Args:
        target (str): The host or IP address to ping.
        count (int): Number of ping attempts.
    """
    os_type = detect_os()
    if os_type == "Windows":
        cmd = f"ping -n {count} {target}"
    else:
        cmd = f"ping -c {count} {target}"

    output = run_command(cmd)
    rprint(output)


def traceroute_host():
    """
    Perform a traceroute to a specified target.
    Tries Scapy-based traceroute first, then falls back to OS-native commands.
    """
    target = input("Enter host/IP for traceroute: ").strip()
    rprint(f"\n[bold]Tracing route to {target}...[/bold]\n")

    try:
        # Attempt Scapy-based traceroute (requires privileges)
        # This will print scapy's traceroute result.
        ans, unans = traceroute(target, maxttl=20, verbose=0)
        # Format output
        for snd, rcv in ans:
            rprint(f"[green]{snd.ttl} {rcv.src}[/green]")
    except PermissionError:
        rprint(
            "[bold red]Scapy traceroute requires elevated privileges. Falling back to system traceroute.[/bold red]"
        )
        system_traceroute(target)
    except Exception as e:
        rprint(f"[bold red]Scapy traceroute error: {e}[/bold red]")
        system_traceroute(target)


def system_traceroute(target: str):
    """
    Fallback to the system traceroute command.

    Args:
        target (str): The host/IP to traceroute.
    """
    os_type = detect_os()
    if os_type == "Windows":
        cmd = f"tracert {target}"
    else:
        cmd = f"traceroute {target}"

    output = run_command(cmd)
    rprint(output)


def dns_lookup():
    """
    Perform a DNS lookup for a given domain name using dnspython.
    This approach does not depend on nslookup.
    """
    domain = input("Enter domain to lookup (e.g., example.com): ").strip()
    record_type = input("Enter DNS record type (default A): ").strip()
    if not record_type:
        record_type = "A"

    rprint(f"\n[bold]Looking up {record_type} records for {domain}...[/bold]\n")
    try:
        answers = dns.resolver.resolve(domain, record_type)
        for rdata in answers:
            rprint(f"[green]{rdata.to_text()}[/green]")
    except dns.resolver.NXDOMAIN:
        rprint("[red]Domain does not exist.[/red]")
    except dns.resolver.NoAnswer:
        rprint(f"[yellow]No {record_type} records found for {domain}.[/yellow]")
    except dns.exception.DNSException as e:
        rprint(f"[red]DNS lookup error: {e}[/red]")


def show_ip_config():
    """
    Display IP configuration using OS commands (ipconfig on Windows, ip addr show on Unix).
    """
    os_type = detect_os()
    if os_type == "Windows":
        cmd = "ipconfig"
    else:
        cmd = "ip addr show"
    rprint("\n[bold]Retrieving IP configuration...[/bold]\n")
    output = run_command(cmd)
    rprint(output)


def http_check():
    """
    Perform a basic HTTP check for a given URL using the requests library.
    Returns status code and response time.
    """
    url = input("Enter a URL (e.g., https://www.google.com): ").strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = f"http://{url}"

    try:
        start_time = time.time()
        response = requests.get(url, timeout=5)
        elapsed = time.time() - start_time
        rprint(
            f"[bold green]HTTP GET {url} - Status: {response.status_code}, "
            f"Time: {elapsed:.2f} seconds[/bold green]"
        )
    except requests.exceptions.RequestException as e:
        rprint(f"[bold red]HTTP check failed: {e}[/bold red]")


def about():
    """
    Display information about net-commander.
    """
    panel_text = (
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
        "Version: 2.0.0"
    )
    console.print(Panel(panel_text, title="About net-commander", expand=False))


def main_menu():
    """
    Show the main menu and handle user input in a loop.
    """
    while True:
        console.rule("[bold cyan]net-commander - Main Menu[/bold cyan]", align="left")
        rprint("[bold]1)[/bold] Port Scan")
        rprint("[bold]2)[/bold] Host Discovery")
        rprint("[bold]3)[/bold] Ping Host")
        rprint("[bold]4)[/bold] Traceroute")
        rprint("[bold]5)[/bold] DNS Lookup")
        rprint("[bold]6)[/bold] Show IP Configuration")
        rprint("[bold]7)[/bold] HTTP Check")
        rprint("[bold]8)[/bold] About net-commander")
        rprint("[bold]9)[/bold] Exit")
        console.rule()

        choice = input("Enter choice: ").strip()

        if choice == "1":
            port_scan()
            input("\nPress Enter to return to the main menu...")
        elif choice == "2":
            host_discovery()
            input("\nPress Enter to return to the main menu...")
        elif choice == "3":
            ping_host()
            input("Press Enter to return to the main menu...")
        elif choice == "4":
            traceroute_host()
            input("Press Enter to return to the main menu...")
        elif choice == "5":
            dns_lookup()
            input("Press Enter to return to the main menu...")
        elif choice == "6":
            show_ip_config()
            input("Press Enter to return to the main menu...")
        elif choice == "7":
            http_check()
            input("Press Enter to return to the main menu...")
        elif choice == "8":
            about()
            input("Press Enter to return to the main menu...")
        elif choice == "9":
            rprint("[bold magenta]Exiting net-commander.[/bold magenta]")
            sys.exit(0)
        else:
            rprint("[bold red]Invalid choice. Please try again.[/bold red]\n")


if __name__ == "__main__":
    main_menu()
