#!/usr/bin/env python3
"""
Python Development Environment Setup
--------------------------------------------------

An automated tool for setting up a complete Python development environment
with a Nord-themed terminal interface. This script installs:
  • Essential system packages for Python development
  • pyenv for Python version management
  • The latest Python version via pyenv
  • pipx for isolated tool installation
  • A suite of essential Python development tools

This script runs fully unattended with no interactive prompts.

Version: 2.3.0
"""

import atexit
import getpass
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pyfiglet
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.style import Style
from rich.table import Table
from rich.text import Text
from rich.traceback import install as install_rich_traceback

# Install rich traceback handler for improved error reporting
install_rich_traceback(show_locals=True)

# ----------------------------------------------------------------
# Configuration & Constants
# ----------------------------------------------------------------
VERSION: str = "2.3.0"
APP_NAME: str = "PyDev Setup"
APP_SUBTITLE: str = "Development Environment Installer"

# Timeouts (in seconds)
DEFAULT_TIMEOUT: int = 3600  # 1 hour for general operations
PYTHON_BUILD_TIMEOUT: int = 7200  # 2 hours for building Python

# Determine the original (non-root) user when using sudo
ORIGINAL_USER: str = os.environ.get("SUDO_USER", getpass.getuser())
try:
    ORIGINAL_UID: int = int(
        subprocess.check_output(["id", "-u", ORIGINAL_USER]).decode().strip()
    )
    ORIGINAL_GID: int = int(
        subprocess.check_output(["id", "-g", ORIGINAL_USER]).decode().strip()
    )
except Exception:
    ORIGINAL_UID = os.getuid()
    ORIGINAL_GID = os.getgid()

# Determine home directory of the original user
if ORIGINAL_USER != "root":
    try:
        HOME_DIR: str = (
            subprocess.check_output(["getent", "passwd", ORIGINAL_USER])
            .decode()
            .split(":")[5]
        )
    except Exception:
        HOME_DIR = os.path.expanduser("~" + ORIGINAL_USER)
else:
    HOME_DIR = os.path.expanduser("~")

# pyenv installation paths
PYENV_DIR: str = os.path.join(HOME_DIR, ".pyenv")
PYENV_BIN: str = os.path.join(PYENV_DIR, "bin", "pyenv")

# List of system dependencies to be installed via apt-get
SYSTEM_DEPENDENCIES: List[str] = [
    "build-essential",
    "libssl-dev",
    "zlib1g-dev",
    "libbz2-dev",
    "libreadline-dev",
    "libsqlite3-dev",
    "libncurses5-dev",
    "libncursesw5-dev",
    "xz-utils",
    "tk-dev",
    "libffi-dev",
    "liblzma-dev",
    "python3-dev",
    "git",
    "curl",
    "wget",
]

# pipx tools to install via pipx
PIPX_TOOLS: List[str] = [
    "black",
    "isort",
    "flake8",
    "mypy",
    "pytest",
    "pre-commit",
    "ipython",
    "cookiecutter",
    "pylint",
    "sphinx",
    "httpie",
    "ruff",
    "yt-dlp",
    "bandit",
    "pipenv",
    "pip-audit",
    "nox",
    "awscli",
    "dvc",
    "uv",
    "pyupgrade",
    "watchfiles",
    "bump2version",
]

# Tool descriptions for display in summary
TOOL_DESCRIPTIONS: Dict[str, str] = {
    "black": "Code formatter that adheres to PEP 8",
    "isort": "Import statement organizer",
    "flake8": "Style guide enforcement tool",
    "mypy": "Static type checker",
    "pytest": "Testing framework",
    "pre-commit": "Git hook manager",
    "ipython": "Enhanced interactive Python shell",
    "cookiecutter": "Project template renderer",
    "pylint": "Code analysis tool",
    "sphinx": "Documentation generator",
    "httpie": "Command-line HTTP client",
    "ruff": "Fast Python linter",
    "yt-dlp": "Advanced video downloader",
    "bandit": "Security linter",
    "pipenv": "Virtual environment & dependency management",
    "pip-audit": "Scans for vulnerable dependencies",
    "nox": "Automation tool for testing",
    "awscli": "Official AWS CLI",
    "dvc": "Data version control for ML projects",
    "uv": "Unified package manager (Rust-based)",
    "pyupgrade": "Upgrades Python syntax",
    "watchfiles": "File change monitor",
    "bump2version": "Automates version bumping",
}


# ----------------------------------------------------------------
# Nord-Themed Colors & Console Setup
# ----------------------------------------------------------------
class NordColors:
    """Nord color palette for consistent theming."""

    POLAR_NIGHT_1: str = "#2E3440"
    POLAR_NIGHT_4: str = "#4C566A"
    SNOW_STORM_1: str = "#D8DEE9"
    SNOW_STORM_2: str = "#E5E9F0"
    FROST_1: str = "#8FBCBB"
    FROST_2: str = "#88C0D0"
    FROST_3: str = "#81A1C1"
    FROST_4: str = "#5E81AC"
    RED: str = "#BF616A"
    ORANGE: str = "#D08770"
    YELLOW: str = "#EBCB8B"
    GREEN: str = "#A3BE8C"


console: Console = Console()


# ----------------------------------------------------------------
# Utility Functions
# ----------------------------------------------------------------
def create_header() -> Panel:
    """
    Create a styled ASCII art header using Pyfiglet and Nord colors.
    """
    try:
        fig = pyfiglet.Figlet(font="slant", width=60)
        ascii_art = fig.renderText(APP_NAME)
    except Exception:
        ascii_art = APP_NAME

    ascii_lines = [line for line in ascii_art.splitlines() if line.strip()]
    colors = [
        NordColors.FROST_1,
        NordColors.FROST_2,
        NordColors.FROST_3,
        NordColors.FROST_4,
    ]
    styled_text = ""
    for i, line in enumerate(ascii_lines):
        color = colors[i % len(colors)]
        styled_text += f"[bold {color}]{line}[/]\n"
    border = f"[{NordColors.FROST_3}]" + "━" * 50 + "[/]"
    styled_text = border + "\n" + styled_text + border

    header_panel = Panel(
        Text.from_markup(styled_text),
        border_style=Style(color=NordColors.FROST_1),
        padding=(1, 2),
        title=f"[bold {NordColors.SNOW_STORM_2}]v{VERSION}[/]",
        title_align="right",
        subtitle=f"[bold {NordColors.SNOW_STORM_1}]{APP_SUBTITLE}[/]",
        subtitle_align="center",
    )
    return header_panel


def print_message(
    text: str, style: str = NordColors.FROST_2, prefix: str = "•"
) -> None:
    console.print(f"[{style}]{prefix} {text}[/{style}]")


def run_command(
    cmd: Union[List[str], str],
    shell: bool = False,
    check: bool = True,
    capture_output: bool = True,
    timeout: int = DEFAULT_TIMEOUT,
    as_user: bool = False,
    env: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    """
    Execute a system command and return its result.
    Optionally runs the command as the original (non-root) user.
    """
    if as_user and ORIGINAL_USER != "root":
        # Prepend sudo to run as the original user
        cmd = ["sudo", "-u", ORIGINAL_USER] + (cmd if isinstance(cmd, list) else [cmd])
    cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
    print_message(
        f"Running: {cmd_str[:80]}{'...' if len(cmd_str) > 80 else ''}",
        NordColors.SNOW_STORM_1,
        "→",
    )
    result = subprocess.run(
        cmd,
        shell=shell,
        check=check,
        text=True,
        capture_output=capture_output,
        timeout=timeout,
        env=env or os.environ.copy(),
    )
    return result


def fix_ownership(path: str, recursive: bool = True) -> None:
    """Fix file ownership for the original (non-root) user."""
    if ORIGINAL_USER == "root":
        return
    try:
        if recursive and os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for d in dirs:
                    os.chown(os.path.join(root, d), ORIGINAL_UID, ORIGINAL_GID)
                for f in files:
                    os.chown(os.path.join(root, f), ORIGINAL_UID, ORIGINAL_GID)
        elif os.path.exists(path):
            os.chown(path, ORIGINAL_UID, ORIGINAL_GID)
    except Exception as e:
        print_message(f"Failed to fix ownership of {path}: {e}", NordColors.YELLOW, "⚠")


def check_command_available(command: str) -> bool:
    """Return True if the command is available in the system PATH."""
    return shutil.which(command) is not None


# ----------------------------------------------------------------
# Core Setup Functions
# ----------------------------------------------------------------
def check_system() -> bool:
    """
    Check system compatibility, privileges, and basic required tools.
    Displays system information using a Rich table.
    """
    with console.status("[bold blue]Checking system compatibility...", spinner="dots"):
        if os.geteuid() != 0:
            print_message(
                "This script must be run with root privileges.", NordColors.RED, "✗"
            )
            return False

        os_name = platform.system().lower()
        if os_name != "linux":
            print_message(
                f"Warning: This script is designed for Linux, not {os_name}.",
                NordColors.YELLOW,
                "⚠",
            )

        table = Table(
            show_header=False, box=None, border_style=NordColors.FROST_3, padding=(0, 2)
        )
        table.add_column("Property", style=f"bold {NordColors.FROST_2}")
        table.add_column("Value", style=NordColors.SNOW_STORM_1)
        table.add_row("Python Version", platform.python_version())
        table.add_row("Operating System", platform.platform())
        table.add_row("Running as", "root")
        table.add_row("Target User", ORIGINAL_USER)
        table.add_row("User Home Directory", HOME_DIR)
        console.print(
            Panel(
                table,
                title="[bold]System Information[/bold]",
                border_style=NordColors.FROST_1,
                padding=(1, 2),
            )
        )
        # Check for basic required tools
        required_tools = ["git", "curl", "gcc"]
        missing = [tool for tool in required_tools if not check_command_available(tool)]
        if missing:
            print_message(
                f"Missing required tools: {', '.join(missing)}. They will be installed.",
                NordColors.YELLOW,
                "⚠",
            )
        else:
            print_message(
                "All basic required tools are present.", NordColors.GREEN, "✓"
            )
        return True


def install_system_dependencies() -> bool:
    """
    Update package lists and install required system packages via apt-get.
    Uses a Rich progress bar for feedback.
    """
    try:
        with console.status("[bold blue]Updating package lists...", spinner="dots"):
            run_command(["apt-get", "update"])
        print_message("Package lists updated.", NordColors.GREEN, "✓")
        with Progress(
            SpinnerColumn("dots", style=f"bold {NordColors.FROST_1}"),
            TextColumn(f"[bold {NordColors.FROST_2}]Installing system packages"),
            BarColumn(
                bar_width=40,
                style=NordColors.FROST_4,
                complete_style=NordColors.FROST_2,
            ),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Installing", total=len(SYSTEM_DEPENDENCIES))
            for package in SYSTEM_DEPENDENCIES:
                try:
                    run_command(["apt-get", "install", "-y", package], check=False)
                except Exception as e:
                    print_message(
                        f"Error installing {package}: {e}", NordColors.YELLOW, "⚠"
                    )
                progress.advance(task)
        print_message(
            "System dependencies installed successfully.", NordColors.GREEN, "✓"
        )
        return True
    except Exception as e:
        print_message(
            f"Failed to install system dependencies: {e}", NordColors.RED, "✗"
        )
        return False


def install_pyenv() -> bool:
    """
    Install pyenv for Python version management.
    If already installed, it is skipped.
    """
    if os.path.exists(PYENV_DIR) and os.path.isfile(PYENV_BIN):
        print_message("pyenv is already installed.", NordColors.GREEN, "✓")
        return True
    try:
        with console.status(
            "[bold blue]Downloading pyenv installer...", spinner="dots"
        ):
            installer_script = "/tmp/pyenv_installer.sh"
            run_command(["curl", "-fsSL", "https://pyenv.run", "-o", installer_script])
            os.chmod(installer_script, 0o755)
        print_message("Running pyenv installer...", NordColors.FROST_3, "➜")
        if ORIGINAL_USER != "root":
            run_command([installer_script], as_user=True)
        else:
            run_command([installer_script])
        if os.path.exists(PYENV_DIR) and os.path.isfile(PYENV_BIN):
            print_message("pyenv installed successfully.", NordColors.GREEN, "✓")
            # Append pyenv initialization to shell RC files
            shell_rc_files = [
                os.path.join(HOME_DIR, ".bashrc"),
                os.path.join(HOME_DIR, ".zshrc"),
            ]
            pyenv_init = '\n# pyenv initialization\nexport PYENV_ROOT="$HOME/.pyenv"\ncommand -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"\neval "$(pyenv init -)"\neval "$(pyenv virtualenv-init -)"\n'
            for rc in shell_rc_files:
                if os.path.exists(rc):
                    with open(rc, "r") as f:
                        content = f.read()
                    if "pyenv init" not in content:
                        with open(rc, "a") as f:
                            f.write(pyenv_init)
                        print_message(
                            f"Added pyenv initialization to {rc}.",
                            NordColors.GREEN,
                            "✓",
                        )
            fix_ownership(PYENV_DIR)
            return True
        else:
            print_message("pyenv installation failed.", NordColors.RED, "✗")
            return False
    except Exception as e:
        print_message(f"Error installing pyenv: {e}", NordColors.RED, "✗")
        return False


def install_latest_python_with_pyenv() -> bool:
    """
    Install the latest available Python version using pyenv.
    Sets the installed version as the global default.
    """
    if not os.path.exists(PYENV_BIN):
        print_message(
            "pyenv is not installed. Aborting Python installation.", NordColors.RED, "✗"
        )
        return False
    try:
        pyenv_cmd = [PYENV_BIN]
        if ORIGINAL_USER != "root":
            pyenv_cmd = ["sudo", "-u", ORIGINAL_USER, PYENV_BIN]
        with console.status("[bold blue]Updating pyenv repository...", spinner="dots"):
            pyenv_root = os.path.dirname(os.path.dirname(PYENV_BIN))
            git_dir = os.path.join(pyenv_root, ".git")
            if os.path.exists(git_dir):
                run_command(
                    ["git", "-C", pyenv_root, "pull"], as_user=(ORIGINAL_USER != "root")
                )
            else:
                print_message(
                    "pyenv repository not a git repository. Skipping update.",
                    NordColors.YELLOW,
                    "⚠",
                )
        print_message("Finding available Python versions...", NordColors.FROST_3, "➜")
        versions_output = run_command(
            pyenv_cmd + ["install", "--list"], as_user=(ORIGINAL_USER != "root")
        ).stdout
        versions = re.findall(r"^\s*(\d+\.\d+\.\d+)$", versions_output, re.MULTILINE)
        if not versions:
            print_message(
                "Could not find any Python versions to install.", NordColors.RED, "✗"
            )
            return False
        sorted_versions = sorted(versions, key=lambda v: [int(i) for i in v.split(".")])
        latest_version = sorted_versions[-1]
        print_message(
            f"Latest Python version found: {latest_version}", NordColors.GREEN, "✓"
        )
        # Informative panel about Python installation process
        console.print(
            Panel(
                f"Installing Python {latest_version}.\nThis process may take 20-60 minutes.",
                style=NordColors.FROST_3,
                title="Python Installation",
            )
        )
        install_cmd = pyenv_cmd + ["install", "--skip-existing", latest_version]
        with console.status(
            f"[bold blue]Building Python {latest_version}...", spinner="dots"
        ):
            run_command(
                install_cmd,
                as_user=(ORIGINAL_USER != "root"),
                timeout=PYTHON_BUILD_TIMEOUT,
            )
        print_message(
            f"Setting Python {latest_version} as global default...",
            NordColors.FROST_3,
            "➜",
        )
        run_command(
            pyenv_cmd + ["global", latest_version], as_user=(ORIGINAL_USER != "root")
        )
        pyenv_python = os.path.join(PYENV_DIR, "shims", "python")
        if os.path.exists(pyenv_python):
            version_info = run_command(
                [pyenv_python, "--version"], as_user=(ORIGINAL_USER != "root")
            ).stdout.strip()
            print_message(
                f"Successfully installed {version_info}", NordColors.GREEN, "✓"
            )
            return True
        else:
            print_message("Python installation with pyenv failed.", NordColors.RED, "✗")
            return False
    except Exception as e:
        print_message(f"Error installing Python with pyenv: {e}", NordColors.RED, "✗")
        return False


def install_pipx() -> bool:
    """
    Ensure pipx is installed for the target user.
    Attempts installation via apt-get first, then falls back to pip.
    """
    if check_command_available("pipx"):
        print_message("pipx is already installed.", NordColors.GREEN, "✓")
        return True
    try:
        with console.status("[bold blue]Installing pipx...", spinner="dots"):
            try:
                run_command(["apt-get", "install", "-y", "pipx"], check=False)
                if check_command_available("pipx"):
                    print_message("pipx installed via apt.", NordColors.GREEN, "✓")
                    return True
            except Exception:
                print_message(
                    "Failed to install pipx via apt, trying pip...",
                    NordColors.YELLOW,
                    "⚠",
                )
            # Use pip installation if apt fails
            python_cmd = (
                os.path.join(PYENV_DIR, "shims", "python")
                if os.path.exists(os.path.join(PYENV_DIR, "shims", "python"))
                else "python3"
            )
            if ORIGINAL_USER != "root":
                run_command(
                    [
                        "sudo",
                        "-u",
                        ORIGINAL_USER,
                        python_cmd,
                        "-m",
                        "pip",
                        "install",
                        "--user",
                        "pipx",
                    ],
                    as_user=True,
                )
                run_command(
                    [
                        "sudo",
                        "-u",
                        ORIGINAL_USER,
                        python_cmd,
                        "-m",
                        "pipx",
                        "ensurepath",
                    ],
                    as_user=True,
                )
            else:
                run_command([python_cmd, "-m", "pip", "install", "pipx"])
                run_command([python_cmd, "-m", "pipx", "ensurepath"])
        user_bin_dir = os.path.join(HOME_DIR, ".local", "bin")
        if os.path.exists(
            os.path.join(user_bin_dir, "pipx")
        ) or check_command_available("pipx"):
            print_message("pipx installed successfully.", NordColors.GREEN, "✓")
            return True
        else:
            print_message(
                "pipx installation completed but may not be in PATH.",
                NordColors.YELLOW,
                "⚠",
            )
            return True
    except Exception as e:
        print_message(f"Error installing pipx: {e}", NordColors.RED, "✗")
        return False


def install_pipx_tools() -> bool:
    """
    Install essential Python development tools via pipx.
    Displays progress using a Rich progress bar.
    """
    pipx_cmd = shutil.which("pipx")
    if not pipx_cmd:
        user_bin_dir = os.path.join(HOME_DIR, ".local", "bin")
        pipx_cmd = (
            os.path.join(user_bin_dir, "pipx") if os.path.exists(user_bin_dir) else None
        )
        if not pipx_cmd:
            print_message("Could not find pipx executable.", NordColors.RED, "✗")
            return False
    console.print(
        Panel(
            f"Automatically installing {len(PIPX_TOOLS)} Python development tools.",
            style=NordColors.FROST_3,
            title="Development Tools",
        )
    )
    env = os.environ.copy()
    if ORIGINAL_USER != "root":
        user_bin_dir = os.path.join(HOME_DIR, ".local", "bin")
        env["PATH"] = f"{user_bin_dir}:{env.get('PATH', '')}"
    installed_tools = []
    failed_tools = []
    with Progress(
        SpinnerColumn("dots", style=f"bold {NordColors.FROST_1}"),
        TextColumn(f"[bold {NordColors.FROST_2}]Installing Python tools"),
        BarColumn(
            bar_width=40, style=NordColors.FROST_4, complete_style=NordColors.FROST_2
        ),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Installing", total=len(PIPX_TOOLS))
        for tool in PIPX_TOOLS:
            try:
                if ORIGINAL_USER != "root":
                    result = run_command(
                        [
                            "sudo",
                            "-u",
                            ORIGINAL_USER,
                            pipx_cmd,
                            "install",
                            tool,
                            "--force",
                        ],
                        as_user=True,
                        env=env,
                    )
                else:
                    result = run_command(
                        [pipx_cmd, "install", tool, "--force"], env=env
                    )
                if result.returncode == 0:
                    installed_tools.append(tool)
                else:
                    failed_tools.append(tool)
            except Exception as e:
                print_message(f"Failed to install {tool}: {e}", NordColors.YELLOW, "⚠")
                failed_tools.append(tool)
            finally:
                progress.advance(task)
    if installed_tools:
        print_message(
            f"Successfully installed {len(installed_tools)} tools.",
            NordColors.GREEN,
            "✓",
        )
    if failed_tools:
        print_message(
            f"Failed to install {len(failed_tools)} tools: {', '.join(failed_tools)}",
            NordColors.RED,
            "✗",
        )
    # Display a summary table of installed tools
    tools_table = Table(
        show_header=True,
        header_style=f"bold {NordColors.FROST_1}",
        border_style=NordColors.FROST_3,
        title=f"[bold {NordColors.FROST_2}]Installed Python Tools[/]",
        title_justify="center",
    )
    tools_table.add_column("Tool", style=f"bold {NordColors.FROST_2}")
    tools_table.add_column("Status", style=NordColors.SNOW_STORM_1)
    tools_table.add_column("Description", style=NordColors.SNOW_STORM_1)
    for tool in PIPX_TOOLS:
        status = (
            "[green]✓ Installed[/]" if tool in installed_tools else "[red]× Failed[/]"
        )
        desc = TOOL_DESCRIPTIONS.get(tool, "")
        tools_table.add_row(tool, status, desc)
    console.print(tools_table)
    return len(installed_tools) > 0


# ----------------------------------------------------------------
# Setup Components Execution & Summary
# ----------------------------------------------------------------
def run_setup_components() -> List[str]:
    """
    Execute all setup components sequentially and return the list of successful installations.
    """
    components = [
        ("System Dependencies", install_system_dependencies),
        ("pyenv", install_pyenv),
        ("Latest Python", install_latest_python_with_pyenv),
        ("pipx", install_pipx),
        ("Python Tools", install_pipx_tools),
    ]
    successes = []
    for name, func in components:
        print_message(f"Installing {name}...", NordColors.FROST_3, "➜")
        try:
            if func():
                print_message(f"{name} installed successfully.", NordColors.GREEN, "✓")
                successes.append(name)
            else:
                print_message(f"Failed to install {name}.", NordColors.RED, "✗")
        except Exception as e:
            print_message(f"Error installing {name}: {e}", NordColors.RED, "✗")
    return successes


def display_summary(successes: List[str]) -> None:
    """
    Display a summary table showing the installation status of each component.
    """
    table = Table(
        show_header=True,
        header_style=f"bold {NordColors.FROST_1}",
        border_style=NordColors.FROST_3,
        title="[bold]Setup Summary[/]",
        title_style=f"bold {NordColors.FROST_2}",
        title_justify="center",
        expand=True,
    )
    table.add_column("Component", style=f"bold {NordColors.FROST_2}")
    table.add_column("Status", style=NordColors.SNOW_STORM_1)
    components = [
        "System Dependencies",
        "pyenv",
        "Latest Python",
        "pipx",
        "Python Tools",
    ]
    for comp in components:
        status = "[green]✓ Installed[/]" if comp in successes else "[red]× Failed[/]"
        table.add_row(comp, status)
    console.print("\n")
    console.print(Panel(table, border_style=NordColors.FROST_1, padding=(1, 2)))
    shell = os.path.basename(os.environ.get("SHELL", "bash"))
    console.print("\n[bold]Next Steps:[/bold]")
    console.print(
        f"To apply all changes, {ORIGINAL_USER} should restart their terminal or run:"
    )
    console.print(f"[bold {NordColors.FROST_3}]source ~/.{shell}rc[/]")
    console.print("\n[bold green]✓ Setup process completed![/bold green]")


# ----------------------------------------------------------------
# Signal Handling and Cleanup
# ----------------------------------------------------------------
def cleanup() -> None:
    """Perform cleanup tasks before exiting."""
    print_message("Cleaning up...", NordColors.FROST_3)


def signal_handler(sig: int, frame: Any) -> None:
    """Handle termination signals gracefully."""
    sig_name = signal.Signals(sig).name
    print_message(f"Process interrupted by {sig_name}", NordColors.YELLOW, "⚠")
    cleanup()
    sys.exit(128 + sig)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
atexit.register(cleanup)


# ----------------------------------------------------------------
# Main Entry Point
# ----------------------------------------------------------------
def main() -> None:
    """
    Main entry point for the automated setup process.
    Displays the header, checks system compatibility, runs all installation components,
    and then displays a summary.
    """
    console.print("\n")
    console.print(create_header())
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hostname = platform.node()
    console.print(
        Align.center(
            f"[{NordColors.SNOW_STORM_1}]Current Time: {current_time}[/] | "
            f"[{NordColors.SNOW_STORM_1}]Host: {hostname}[/]"
        )
    )
    console.print("\n")
    if os.geteuid() != 0:
        print_message(
            "This script must be run with root privileges. Please run with sudo.",
            NordColors.RED,
            "✗",
        )
        sys.exit(1)
    if not check_system():
        print_message("System check failed. Aborting setup.", NordColors.RED, "✗")
        sys.exit(1)
    console.print(
        Panel(
            "Welcome to the Automated Python Development Environment Setup!\n\n"
            "The tool will now automatically install all required components.",
            style=NordColors.FROST_3,
            title="Welcome",
        )
    )
    successes = run_setup_components()
    display_summary(successes)


if __name__ == "__main__":
    main()
