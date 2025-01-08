#!/usr/bin/env python3
"""
net_commander_typer.py

A cross-platform, menu-driven "Swiss Army Knife" for basic network analysis
and troubleshooting, rewritten using the Typer CLI framework.

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
Version: 3.0.0 (Typer version)

Notes:
    - Scapy operations may require elevated privileges.
    - For large subnets, ICMP sweeps/traceroutes can take noticeable time.
    - This script provides both subcommands (e.g. `./net_commander_typer.py port-scan`)
      and an interactive mode (`./net_commander_typer.py interactive`).

Usage Examples:
    - Interactive mode:
        $ python net_commander_typer.py interactive

    - Direct subcommands:
        $ python net_commander_typer.py port-scan --target 192.168.1.10 --ports 22 80 443
"""

import sys
import time
import socket
import platform
import subprocess
import ipaddress
from typing import List, Optional

import typer
import requests
import dns.resolver

try:
    from scapy.layers.inet import IP, ICMP, traceroute
    from scapy.sendrecv import sr1, sr
except ImportError:
    # If scapy is not installed, we'll fallback where needed.
    pass

app = typer.Typer(help="net-commander: A basic network analysis toolkit.")


#
# ------------- Utility functions -------------
#


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

    Returns:
        List[str]: A list of active hosts in the subnet.
    """
    network = ipaddress.ip_network(cidr, strict=False)
    hosts = [str(ip) for ip in network.hosts()]

    answered, _unanswered = sr(
        IP(dst=hosts) / ICMP(), timeout=1, verbose=0  # Suppress Scapy's console output
    )
    active_hosts = []
    for _, rcv in answered:
        active_hosts.append(rcv.src)

    return active_hosts


def fallback_host_discovery(cidr: str):
    """
    Fallback method for host discovery using system pings if Scapy is not available
    or insufficient privileges are encountered.

    Args:
        cidr (str): CIDR notation of the subnet to scan.

    Returns:
        Tuple[List[str], str]: (list of active hosts, multiline output string)
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
        # Checking TTL or bytes received in the output
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


#
# ------------- Typer Subcommands -------------
#


@app.command("port-scan")
def port_scan(
    target: str = typer.Option(
        ..., prompt="Target hostname or IP", help="Host to scan."
    ),
    ports: List[int] = typer.Option(
        ..., prompt="Space-separated ports", help="One or more TCP ports."
    ),
    timeout: float = typer.Option(
        0.5, help="Socket timeout for each port connection attempt."
    ),
):
    """
    Perform a basic TCP port scan on the given target for the specified ports.
    """
    typer.echo(f"Starting port scan on {target}...")
    for port in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            try:
                result = s.connect_ex((target, port))
                if result == 0:
                    typer.echo(f"Port {port}: OPEN")
                else:
                    typer.echo(f"Port {port}: CLOSED")
            except Exception as exc:
                typer.echo(f"Port {port} ERROR: {exc}")
    typer.echo("Port scan complete.")


@app.command("host-discovery")
def host_discovery(
    cidr: str = typer.Option(
        ..., prompt="CIDR (e.g. 192.168.1.0/24)", help="Subnet to scan."
    )
):
    """
    Perform a simple host discovery on a subnet via ICMP sweeps (Scapy) or system ping fallback.
    """
    typer.echo(f"Scanning {cidr}...")

    # Attempt Scapy-based approach
    try:
        active_hosts = scapy_ping_sweep(cidr)
        if active_hosts:
            typer.secho("Active Hosts:", fg=typer.colors.GREEN, bold=True)
            for host in active_hosts:
                typer.echo(f"  {host}")
        else:
            typer.secho("No active hosts found.", fg=typer.colors.YELLOW, bold=True)
    except PermissionError:
        typer.secho(
            "Scapy requires elevated privileges. Using system ping fallback...",
            fg=typer.colors.RED,
            bold=True,
        )
        hosts, output = fallback_host_discovery(cidr)
        typer.echo(output)
        if hosts:
            typer.secho("\nActive hosts:", fg=typer.colors.GREEN, bold=True)
            for host in hosts:
                typer.echo(f"  {host}")
        else:
            typer.secho("No active hosts found.", fg=typer.colors.YELLOW, bold=True)
    except Exception as exc:
        typer.secho(
            f"Error using Scapy: {exc}\nFalling back to system ping...",
            fg=typer.colors.RED,
            bold=True,
        )
        hosts, output = fallback_host_discovery(cidr)
        typer.echo(output)
        if hosts:
            typer.secho("\nActive hosts:", fg=typer.colors.GREEN, bold=True)
            for host in hosts:
                typer.echo(f"  {host}")
        else:
            typer.secho("No active hosts found.", fg=typer.colors.YELLOW, bold=True)


@app.command()
def ping(
    target: str = typer.Option(
        ..., prompt="Target host/IP", help="Host or IP to ping."
    ),
    count: int = typer.Option(4, help="Number of ping attempts."),
):
    """
    Ping a specified host using Scapy-based ping if possible, else system ping.
    """
    typer.echo(f"Pinging {target}...")
    try:
        # Attempt Scapy-based ping
        for i in range(count):
            resp = sr1(IP(dst=target) / ICMP(), timeout=1, verbose=0)
            if resp is None:
                typer.secho(f"{i+1}. Request timed out", fg=typer.colors.RED)
            else:
                typer.echo(f"{i+1}. Reply from {resp.src} TTL={resp.ttl}")
    except PermissionError:
        typer.secho(
            "Scapy requires elevated privileges. Falling back to system ping...",
            fg=typer.colors.RED,
        )
        typer.echo(system_ping(target, count))
    except Exception as exc:
        typer.secho(f"Scapy ping error: {exc}", fg=typer.colors.RED)
        typer.echo(system_ping(target, count))


@app.command()
def tracer(
    target: str = typer.Option(
        ..., prompt="Target host/IP", help="Host or IP to traceroute."
    )
):
    """
    Perform a traceroute to a specified target using Scapy if possible, else system traceroute.
    """
    typer.echo(f"Tracing route to {target}...")
    try:
        ans, _unans = traceroute(target, maxttl=20, verbose=0)
        for snd, rcv in ans:
            typer.echo(f"{snd.ttl}. {rcv.src}")
    except PermissionError:
        typer.secho(
            "Scapy traceroute requires elevated privileges. Falling back to system traceroute...",
            fg=typer.colors.RED,
        )
        typer.echo(system_traceroute(target))
    except Exception as exc:
        typer.secho(f"Scapy traceroute error: {exc}", fg=typer.colors.RED)
        typer.echo(system_traceroute(target))


@app.command("dns-lookup")
def dns_lookup(
    domain: str = typer.Option(
        ..., prompt="Domain (e.g. example.com)", help="Domain to query."
    ),
    record_type: str = typer.Option("A", help="DNS record type (default=A)."),
):
    """
    Perform a DNS lookup using dnspython.
    """
    typer.echo(f"Looking up {record_type} record(s) for {domain}...")
    try:
        answers = dns.resolver.resolve(domain, record_type)
        for rdata in answers:
            typer.secho(rdata.to_text(), fg=typer.colors.GREEN)
    except dns.resolver.NXDOMAIN:
        typer.secho("Domain does not exist.", fg=typer.colors.RED)
    except dns.resolver.NoAnswer:
        typer.secho(f"No {record_type} records found.", fg=typer.colors.YELLOW)
    except dns.exception.DNSException as exc:
        typer.secho(f"DNS lookup error: {exc}", fg=typer.colors.RED)


@app.command("ipconfig")
def ip_config():
    """
    Display IP configuration using system commands.
    """
    os_type = detect_os()
    if os_type == "Windows":
        cmd = "ipconfig"
    else:
        cmd = "ip addr show"
    typer.echo(run_command(cmd))


@app.command("http-check")
def http_check(
    url: str = typer.Option(
        ..., prompt="URL (e.g. https://www.google.com)", help="URL to check."
    )
):
    """
    Perform a basic HTTP GET request using the 'requests' library.
    """
    # Ensure URL starts with http:// or https://
    if not (url.startswith("http://") or url.startswith("https://")):
        url = f"http://{url}"

    typer.echo(f"Checking {url}...")
    start_time = time.time()
    try:
        response = requests.get(url, timeout=5)
        elapsed = time.time() - start_time
        typer.secho(
            f"HTTP GET {url} - Status: {response.status_code}, "
            f"Time: {elapsed:.2f} seconds",
            fg=typer.colors.GREEN,
        )
    except requests.exceptions.RequestException as exc:
        typer.secho(f"HTTP check failed: {exc}", fg=typer.colors.RED)


@app.command()
def about():
    """
    Display information about net-commander.
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
        "Version: 3.0.0 (Typer version)\n"
    )
    typer.echo(info)


#
# ------------- Interactive Menu -------------
#


def interactive_menu():
    """
    Provide an interactive, menu-driven CLI using Typer prompts.
    """
    while True:
        typer.secho(
            "\n--- net-commander (Interactive Mode) ---",
            fg=typer.colors.CYAN,
            bold=True,
        )
        typer.echo(
            "1) Port Scan\n"
            "2) Host Discovery\n"
            "3) Ping Host\n"
            "4) Traceroute\n"
            "5) DNS Lookup\n"
            "6) Show IP Configuration\n"
            "7) HTTP Check\n"
            "8) About\n"
            "9) Exit\n"
        )
        choice = typer.prompt("Enter your choice", default="9")

        if choice == "1":
            _port_scan_interactive()
        elif choice == "2":
            _host_discovery_interactive()
        elif choice == "3":
            _ping_interactive()
        elif choice == "4":
            _tracer_interactive()
        elif choice == "5":
            _dns_lookup_interactive()
        elif choice == "6":
            typer.run(ip_config)  # or just call ip_config() directly
        elif choice == "7":
            _http_check_interactive()
        elif choice == "8":
            about()
        elif choice == "9":
            typer.echo("Exiting net-commander.")
            sys.exit(0)
        else:
            typer.secho("Invalid choice. Please try again.", fg=typer.colors.RED)


@app.command()
def interactive():
    """
    Launch an interactive menu-driven CLI mode.
    """
    interactive_menu()


#
# ------------- Helper functions for interactive mode -------------
#


def _port_scan_interactive():
    target = typer.prompt("Enter target hostname or IP")
    ports_str = typer.prompt("Enter space-separated ports (e.g. 22 80 443)")
    try:
        ports = [int(p.strip()) for p in ports_str.split()]
    except ValueError:
        typer.secho(
            "Invalid port(s). Please enter numeric values.", fg=typer.colors.RED
        )
        return
    port_scan.callback(
        target=target, ports=ports
    )  # Directly call the Typer subcommand logic


def _host_discovery_interactive():
    cidr = typer.prompt("Enter CIDR notation (e.g. 192.168.1.0/24)")
    host_discovery.callback(cidr=cidr)


def _ping_interactive():
    target = typer.prompt("Enter the host/IP to ping")
    count = typer.prompt("Number of pings (default 4)", default="4")
    try:
        count_num = int(count)
    except ValueError:
        count_num = 4
    ping.callback(target=target, count=count_num)


def _tracer_interactive():
    target = typer.prompt("Enter the host/IP for traceroute")
    tracer.callback(target=target)


def _dns_lookup_interactive():
    domain = typer.prompt("Enter domain (e.g. example.com)")
    record_type = typer.prompt("Enter record type (default A)", default="A")
    dns_lookup.callback(domain=domain, record_type=record_type)


def _http_check_interactive():
    url = typer.prompt("Enter URL (e.g. https://www.google.com)")
    http_check.callback(url=url)


#
# ------------- Main entry point -------------
#


def main():
    app()


if __name__ == "__main__":
    main()
