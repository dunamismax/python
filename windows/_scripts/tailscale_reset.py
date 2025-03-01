#!/usr/bin/env python3
"""
Enhanced Tailscale Reset Utility for Windows
-------------------------------------------

A console-based utility for managing Tailscale on Windows systems.
This tool provides options to:
  • Stop the Tailscale service
  • Uninstall Tailscale and remove configuration directories
  • Install Tailscale via the official installer
  • Start the Tailscale service
  • Run Tailscale to bring the daemon up

All functionality is menu-driven with a clean console interface.

Note: Some operations require administrator privileges.

Version: 1.0.0
"""

import os
import sys
import time
import socket
import datetime
import subprocess
import shutil
import ctypes
import winreg
import urllib.request
import threading
import signal
import atexit
from pathlib import Path

# ==============================
# Configuration & Constants
# ==============================
APP_NAME = "Tailscale Reset Utility for Windows"
VERSION = "1.0.0"
HOSTNAME = socket.gethostname()
LOG_FILE = os.path.join(
    os.path.expanduser("~"), "tailscale_reset_logs", "tailscale_reset.log"
)
TAILSCALE_DOWNLOAD_URL = "https://pkgs.tailscale.com/stable/tailscale-setup-latest.exe"
TAILSCALE_INSTALLER_PATH = os.path.join(
    os.environ.get("TEMP", "."), "tailscale-installer.exe"
)
TAILSCALE_SERVICE_NAME = "Tailscale"

# Tailscale directories to clean
PROGRAM_DATA_DIR = os.path.join("C:\\ProgramData", "Tailscale")
USER_APPDATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Tailscale")


# ==============================
# Console Styling (without rich)
# ==============================
# ANSI color codes for Windows
# Note: These will only work if ANSI color is enabled
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"


# Enable ANSI colors in Windows console
def enable_ansi_colors():
    """Enable ANSI escape sequences for the Windows console."""
    kernel32 = ctypes.WinDLL("kernel32")
    hStdOut = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
    mode = ctypes.c_ulong()
    kernel32.GetConsoleMode(hStdOut, ctypes.byref(mode))
    # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
    kernel32.SetConsoleMode(hStdOut, mode.value | 0x0004)


# Try to enable ANSI colors
try:
    enable_ansi_colors()
    ANSI_ENABLED = True
except:
    ANSI_ENABLED = False


# ==============================
# UI Helper Functions
# ==============================
def print_header(text):
    """Print a styled header."""
    width = min(shutil.get_terminal_size().columns, 80)
    padding = (width - len(text)) // 2

    # Draw top border
    print()
    print("=" * width)

    # Print the text with padding
    if ANSI_ENABLED:
        print(
            f"{Colors.BOLD}{Colors.CYAN}{' ' * padding}{text}{' ' * padding}{Colors.RESET}"
        )
    else:
        print(f"{' ' * padding}{text}{' ' * padding}")

    # Draw bottom border
    print("=" * width)
    print()


def print_section(title):
    """Print a section header."""
    if ANSI_ENABLED:
        print(f"\n{Colors.BOLD}{Colors.CYAN}==== {title} ===={Colors.RESET}\n")
    else:
        print(f"\n==== {title} ====\n")


def print_info(message):
    """Print an informational message."""
    if ANSI_ENABLED:
        print(f"{Colors.BLUE}• {message}{Colors.RESET}")
    else:
        print(f"• {message}")


def print_success(message):
    """Print a success message."""
    if ANSI_ENABLED:
        print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")
    else:
        print(f"✓ {message}")


def print_warning(message):
    """Print a warning message."""
    if ANSI_ENABLED:
        print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")
    else:
        print(f"! {message}")


def print_error(message):
    """Print an error message."""
    if ANSI_ENABLED:
        print(f"{Colors.RED}✗ {message}{Colors.RESET}")
    else:
        print(f"X {message}")


def print_step(text):
    """Print a step description."""
    if ANSI_ENABLED:
        print(f"{Colors.CYAN}• {text}{Colors.RESET}")
    else:
        print(f"• {text}")


def clear_screen():
    """Clear the terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


def pause():
    """Pause execution until user presses Enter."""
    if ANSI_ENABLED:
        input(f"\n{Colors.MAGENTA}Press Enter to continue...{Colors.RESET}")
    else:
        input("\nPress Enter to continue...")


def get_user_input(prompt, default=""):
    """Get input from the user with a styled prompt."""
    if ANSI_ENABLED:
        user_input = input(f"{Colors.MAGENTA}{prompt}{Colors.RESET} ")
    else:
        user_input = input(f"{prompt} ")

    if not user_input and default:
        return default
    return user_input


def get_user_confirmation(prompt):
    """Get a yes/no confirmation from the user."""
    while True:
        if ANSI_ENABLED:
            choice = input(f"{Colors.MAGENTA}{prompt} (y/n) {Colors.RESET}").lower()
        else:
            choice = input(f"{prompt} (y/n) ").lower()

        if choice in ["y", "yes"]:
            return True
        elif choice in ["n", "no"]:
            return False
        print("Please enter 'y' or 'n'.")


def print_menu(title, options):
    """Print a menu with options."""
    print_section(title)

    # Calculate the padding needed for alignment
    max_key_len = max(len(key) for key, _ in options)

    for key, description in options:
        if ANSI_ENABLED:
            print(
                f"  {Colors.CYAN}{key.rjust(max_key_len)}{Colors.RESET} - {description}"
            )
        else:
            print(f"  {key.rjust(max_key_len)} - {description}")

    print()


# ==============================
# Logging Setup
# ==============================
def setup_logging(log_file=LOG_FILE):
    """Configure basic logging for the script."""
    import logging

    try:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        print_step(f"Logging configured to: {log_file}")
    except Exception as e:
        print_warning(f"Could not set up logging to {log_file}: {e}")
        print_step("Continuing without logging to file...")


# ==============================
# Signal Handling & Cleanup
# ==============================
def cleanup():
    """Perform cleanup tasks before exit."""
    print_step("Performing cleanup tasks...")
    # Remove temporary installer if it exists
    if os.path.exists(TAILSCALE_INSTALLER_PATH):
        try:
            os.remove(TAILSCALE_INSTALLER_PATH)
        except:
            pass


atexit.register(cleanup)


def signal_handler(signum, frame):
    """Handle termination signals gracefully."""
    print_warning("\nScript interrupted.")
    cleanup()
    sys.exit(1)


# Register signal handlers for SIGINT (Ctrl+C)
signal.signal(signal.SIGINT, signal_handler)


# ==============================
# Simple Spinner Class
# ==============================
class Spinner:
    """Thread-safe spinner for indeterminate progress."""

    def __init__(self, message):
        self.message = message
        self.spinner_chars = "|/-\\"
        self.current = 0
        self.spinning = False
        self.thread = None
        self.start_time = 0

    def _spin(self):
        """Internal method to update the spinner."""
        while self.spinning:
            elapsed = time.time() - self.start_time
            time_str = self._format_time(elapsed)

            # Build the spinner text
            if ANSI_ENABLED:
                spinner_text = f"\r{Colors.CYAN}{self.spinner_chars[self.current]}{Colors.RESET} {self.message} (elapsed: {time_str})"
            else:
                spinner_text = f"\r{self.spinner_chars[self.current]} {self.message} (elapsed: {time_str})"

            # Print and flush
            sys.stdout.write(spinner_text)
            sys.stdout.flush()

            self.current = (self.current + 1) % len(self.spinner_chars)
            time.sleep(0.1)  # Spinner update interval

    def _format_time(self, seconds):
        """Format seconds into a human-readable time string."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds / 60:.1f}m"
        else:
            return f"{seconds / 3600:.1f}h"

    def start(self):
        """Start the spinner."""
        self.spinning = True
        self.start_time = time.time()
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()

    def stop(self, success=True):
        """Stop the spinner and display completion message."""
        self.spinning = False
        if self.thread:
            self.thread.join()

        elapsed = time.time() - self.start_time
        time_str = self._format_time(elapsed)

        # Clear the spinner line
        sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.flush()

        if success:
            print_success(f"{self.message} completed in {time_str}")
        else:
            print_error(f"{self.message} failed after {time_str}")

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Context manager exit."""
        self.stop(success=exc_type is None)


# ==============================
# Admin Privileges Functions
# ==============================
def is_admin():
    """Check if the script is running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False


def run_as_admin():
    """Restart the script with administrator privileges."""
    if not is_admin():
        print_warning("This operation requires administrator privileges.")
        print_info("Attempting to restart with elevated privileges...")

        try:
            # Create a UAC prompt to run the script with admin rights
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
            sys.exit(0)
        except Exception as e:
            print_error(f"Failed to elevate privileges: {e}")
            print_info("Please run this script as administrator manually.")
            sys.exit(1)


# ==============================
# System Helper Functions
# ==============================
def run_command(
    cmd, shell=False, check=True, capture_output=True, timeout=60, verbose=False
):
    """Run a command and handle errors."""
    if verbose:
        if shell:
            print_step(f"Executing: {cmd}")
        else:
            print_step(f"Executing: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            check=check,
            text=True,
            capture_output=capture_output,
            timeout=timeout,
        )
        return result
    except subprocess.CalledProcessError as e:
        if shell:
            print_error(f"Command failed: {cmd}")
        else:
            print_error(f"Command failed: {' '.join(cmd)}")

        if hasattr(e, "stdout") and e.stdout:
            print(f"Output: {e.stdout.strip()}")
        if hasattr(e, "stderr") and e.stderr:
            print_error(f"Error: {e.stderr.strip()}")
        raise
    except subprocess.TimeoutExpired:
        print_error(f"Command timed out after {timeout} seconds")
        raise


def ensure_admin():
    """Ensure the script is run with administrator privileges."""
    if not is_admin():
        run_as_admin()


def get_tailscale_service_status():
    """Get the current status of the Tailscale service."""
    try:
        result = run_command(["sc", "query", TAILSCALE_SERVICE_NAME])

        # Parse the output to get service status
        for line in result.stdout.splitlines():
            if "STATE" in line:
                state_parts = line.strip().split()
                if len(state_parts) >= 4:
                    state_code = state_parts[3]

                    # State codes:
                    # 1 = stopped
                    # 2 = starting
                    # 3 = stopping
                    # 4 = running

                    if state_code == "4":
                        return "running"
                    elif state_code == "1":
                        return "stopped"
                    elif state_code == "2":
                        return "starting"
                    elif state_code == "3":
                        return "stopping"

        return "unknown"
    except Exception:
        return "not_installed"


def is_tailscale_installed():
    """Check if Tailscale is installed."""
    # Method 1: Check for service
    if get_tailscale_service_status() != "not_installed":
        return True

    # Method 2: Check for installation directory
    program_files = os.environ.get("PROGRAMFILES", "C:\\Program Files")
    tailscale_dir = os.path.join(program_files, "Tailscale")

    if os.path.exists(tailscale_dir):
        return True

    # Method 3: Check registry
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Tailscale") as key:
            return True
    except:
        pass

    return False


# ==============================
# Tailscale Operation Functions
# ==============================
def stop_tailscale_service():
    """Stop the Tailscale service."""
    ensure_admin()
    print_section("Stopping Tailscale Service")

    # Check if service exists and is running
    status = get_tailscale_service_status()

    if status == "not_installed":
        print_warning("Tailscale service is not installed.")
        return

    if status == "stopped":
        print_info("Tailscale service is already stopped.")
        return

    print_step("Stopping Tailscale service...")

    try:
        with Spinner("Stopping Tailscale service") as spinner:
            result = run_command(["sc", "stop", TAILSCALE_SERVICE_NAME])

            # Wait for service to stop (with timeout)
            max_wait = 30  # seconds
            start_time = time.time()

            while time.time() - start_time < max_wait:
                status = get_tailscale_service_status()
                if status in ["stopped", "not_installed"]:
                    break
                time.sleep(1)

            if status in ["stopped", "not_installed"]:
                spinner.stop(success=True)
            else:
                spinner.stop(success=False)
                print_warning("Service did not stop in the expected time frame.")
    except Exception as e:
        print_error(f"Failed to stop Tailscale service: {e}")


def uninstall_tailscale():
    """Uninstall Tailscale and remove configuration directories."""
    ensure_admin()
    print_section("Uninstalling Tailscale")

    if not is_tailscale_installed():
        print_warning("Tailscale does not appear to be installed.")

        # Even if it's not installed, we'll still clean up the directories
        print_info("Proceeding with directory cleanup...")
    else:
        # First stop the service
        stop_tailscale_service()

        # Then uninstall using the Windows uninstaller
        print_step("Uninstalling Tailscale application...")

        try:
            # Try to find the uninstaller in the registry
            uninstaller_path = None

            try:
                with winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                ) as key:
                    # Enumerate all subkeys
                    subkey_count = winreg.QueryInfoKey(key)[0]

                    for i in range(subkey_count):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                try:
                                    display_name = winreg.QueryValueEx(
                                        subkey, "DisplayName"
                                    )[0]
                                    if "Tailscale" in display_name:
                                        uninstaller_path = winreg.QueryValueEx(
                                            subkey, "UninstallString"
                                        )[0]
                                        break
                                except:
                                    pass
                        except:
                            continue
            except:
                pass

            if uninstaller_path:
                print_step(f"Found uninstaller: {uninstaller_path}")
                with Spinner("Running Tailscale uninstaller") as spinner:
                    # Add /S for silent uninstall
                    run_command([uninstaller_path, "/S"], shell=True)
            else:
                # Fallback to direct program files check if registry approach fails
                program_files = os.environ.get("PROGRAMFILES", "C:\\Program Files")
                possible_uninstallers = [
                    os.path.join(program_files, "Tailscale", "uninstall.exe"),
                    os.path.join(program_files, "Tailscale", "Uninstall.exe"),
                ]

                uninstaller_found = False
                for uninstaller in possible_uninstallers:
                    if os.path.exists(uninstaller):
                        print_step(f"Found uninstaller: {uninstaller}")
                        with Spinner("Running Tailscale uninstaller") as spinner:
                            run_command([uninstaller, "/S"], shell=True)
                        uninstaller_found = True
                        break

                if not uninstaller_found:
                    print_warning(
                        "Could not find Tailscale uninstaller. Trying alternative methods."
                    )

                    # Try using wmic to uninstall (legacy method)
                    try:
                        with Spinner("Uninstalling Tailscale via wmic") as spinner:
                            run_command(
                                [
                                    "wmic",
                                    "product",
                                    "where",
                                    'name="Tailscale"',
                                    "call",
                                    "uninstall",
                                    "/nointeractive",
                                ],
                                check=False,
                            )
                    except Exception as e:
                        spinner.stop(success=False)
                        print_warning(f"WMIC uninstall attempt failed: {e}")

        except Exception as e:
            print_error(f"Error during uninstallation: {e}")
            if not get_user_confirmation("Continue with directory cleanup?"):
                return

    # Clean up configuration and data directories
    print_step("Removing Tailscale configuration and data directories...")

    dirs_to_remove = [
        PROGRAM_DATA_DIR,  # C:\ProgramData\Tailscale
        USER_APPDATA_DIR,  # C:\Users\%USERNAME%\AppData\Local\Tailscale
    ]

    for directory in dirs_to_remove:
        if os.path.exists(directory):
            try:
                print_step(f"Removing {directory}...")
                shutil.rmtree(directory)
                print_success(f"Successfully removed {directory}")
            except Exception as e:
                print_error(f"Failed to remove {directory}: {e}")
                print_warning("You may need to remove this directory manually.")
        else:
            print_info(
                f"Directory {directory} does not exist or has already been removed."
            )

    print_success("Tailscale uninstallation and cleanup completed.")


def download_tailscale():
    """Download the Tailscale installer."""
    print_section("Downloading Tailscale Installer")

    if os.path.exists(TAILSCALE_INSTALLER_PATH):
        if get_user_confirmation("Installer already exists. Download again?"):
            try:
                os.remove(TAILSCALE_INSTALLER_PATH)
            except Exception as e:
                print_error(f"Could not remove existing installer: {e}")
                return False
        else:
            print_info("Using existing installer.")
            return True

    print_step(f"Downloading from {TAILSCALE_DOWNLOAD_URL}...")

    try:
        with Spinner("Downloading Tailscale installer") as spinner:
            # Create a request with a proper User-Agent
            req = urllib.request.Request(
                TAILSCALE_DOWNLOAD_URL, headers={"User-Agent": "Mozilla/5.0"}
            )

            # Open the URL and download the file
            with (
                urllib.request.urlopen(req) as response,
                open(TAILSCALE_INSTALLER_PATH, "wb") as out_file,
            ):
                shutil.copyfileobj(response, out_file)

        if os.path.exists(TAILSCALE_INSTALLER_PATH):
            print_success(f"Downloaded installer to {TAILSCALE_INSTALLER_PATH}")
            return True
        else:
            print_error("Download completed but installer file was not created.")
            return False
    except Exception as e:
        print_error(f"Failed to download Tailscale installer: {e}")
        return False


def install_tailscale():
    """Install Tailscale using the downloaded installer."""
    ensure_admin()
    print_section("Installing Tailscale")

    # First, download the installer if needed
    if not download_tailscale():
        print_error("Could not proceed with installation due to download failure.")
        return

    print_step("Running Tailscale installer...")

    try:
        with Spinner("Installing Tailscale") as spinner:
            # Run the installer silently
            result = run_command([TAILSCALE_INSTALLER_PATH, "/S"], check=False)

            # Wait a bit for installation to take effect
            time.sleep(5)

            # Check if installation was successful
            if is_tailscale_installed():
                spinner.stop(success=True)
            else:
                spinner.stop(success=False)
                print_warning(
                    "Installation seemed to complete but Tailscale is not detected."
                )
                print_info("You may need to install Tailscale manually.")
    except Exception as e:
        print_error(f"Installation failed: {e}")


def start_tailscale_service():
    """Start the Tailscale service."""
    ensure_admin()
    print_section("Starting Tailscale Service")

    # Check if service exists
    status = get_tailscale_service_status()

    if status == "not_installed":
        print_warning("Tailscale service is not installed.")
        return

    if status == "running":
        print_info("Tailscale service is already running.")
        return

    print_step("Starting Tailscale service...")

    try:
        with Spinner("Starting Tailscale service") as spinner:
            result = run_command(["sc", "start", TAILSCALE_SERVICE_NAME])

            # Wait for service to start (with timeout)
            max_wait = 30  # seconds
            start_time = time.time()

            while time.time() - start_time < max_wait:
                status = get_tailscale_service_status()
                if status == "running":
                    break
                time.sleep(1)

            if status == "running":
                spinner.stop(success=True)
            else:
                spinner.stop(success=False)
                print_warning("Service did not start in the expected time frame.")
    except Exception as e:
        print_error(f"Failed to start Tailscale service: {e}")


def tailscale_up():
    """Run 'tailscale up' to authenticate and connect the node."""
    ensure_admin()
    print_section("Running Tailscale Up")

    if not is_tailscale_installed():
        print_error("Tailscale is not installed. Please install it first.")
        return

    # Ensure service is running
    status = get_tailscale_service_status()
    if status != "running":
        print_warning("Tailscale service is not running. Attempting to start it...")
        start_tailscale_service()

        # Check again after attempting to start
        status = get_tailscale_service_status()
        if status != "running":
            print_error(
                "Could not start Tailscale service. Cannot proceed with tailscale up."
            )
            return

    print_step("Running 'tailscale up'...")

    program_files = os.environ.get("PROGRAMFILES", "C:\\Program Files")
    tailscale_exe = os.path.join(program_files, "Tailscale", "tailscale.exe")

    if not os.path.exists(tailscale_exe):
        print_error(f"Could not find tailscale.exe at {tailscale_exe}")
        return

    print_info("This will launch Tailscale login in your browser.")
    if not get_user_confirmation(
        "Do you want to proceed with Tailscale authentication?"
    ):
        print_info("Tailscale authentication cancelled.")
        return

    try:
        # Run tailscale up
        print_info("Launching Tailscale authentication...")
        result = run_command([tailscale_exe, "up"], capture_output=False, check=False)

        print_success("Tailscale authentication process completed.")
    except Exception as e:
        print_error(f"Error during Tailscale up: {e}")


def check_tailscale_status():
    """Check and display the current Tailscale status."""
    print_section("Tailscale Status")

    if not is_tailscale_installed():
        print_warning("Tailscale is not installed.")
        return

    # Check service status
    service_status = get_tailscale_service_status()
    print_info(f"Tailscale service status: {service_status}")

    # Check tailscale CLI status if service is running
    if service_status == "running":
        program_files = os.environ.get("PROGRAMFILES", "C:\\Program Files")
        tailscale_exe = os.path.join(program_files, "Tailscale", "tailscale.exe")

        if os.path.exists(tailscale_exe):
            try:
                print_step("Checking Tailscale connection status...")
                result = run_command([tailscale_exe, "status"])

                if result.stdout.strip():
                    print("\nTailscale Status Output:")
                    print("------------------------")
                    print(result.stdout)
                    print("------------------------")
                else:
                    print_warning("No status information available.")
            except Exception as e:
                print_error(f"Failed to check Tailscale status: {e}")
        else:
            print_warning(f"Could not find tailscale.exe at {tailscale_exe}")

    # Check for data directories
    print_step("Checking Tailscale data directories...")

    dirs_to_check = [
        PROGRAM_DATA_DIR,
        USER_APPDATA_DIR,
    ]

    for directory in dirs_to_check:
        if os.path.exists(directory):
            print_info(f"Directory exists: {directory}")
        else:
            print_info(f"Directory does not exist: {directory}")


def reset_tailscale():
    """Perform a complete reset of Tailscale: uninstall, install, start, up."""
    ensure_admin()
    print_section("Complete Tailscale Reset")

    if not get_user_confirmation("This will completely reset Tailscale. Continue?"):
        print_info("Reset cancelled.")
        return

    try:
        # Step 1: Uninstall and clean up
        uninstall_tailscale()
        time.sleep(2)

        # Step 2: Install
        install_tailscale()
        time.sleep(2)

        # Step 3: Start service
        start_tailscale_service()
        time.sleep(2)

        # Step 4: Run tailscale up
        tailscale_up()

        print_success("Tailscale has been completely reset!")
    except Exception as e:
        print_error(f"Reset process failed: {e}")
        print_warning("Tailscale may be in an inconsistent state.")


# ==============================
# Main Entry Point
# ==============================
def main():
    """Main entry point for the script."""
    try:
        # Initial setup
        setup_logging()

        # Check for admin privileges
        if not is_admin():
            print_warning("Some operations require administrator privileges.")
            print_info("The script will request elevation when needed.")

        # Launch the main menu
        main_menu()

    except KeyboardInterrupt:
        print_warning("\nProcess interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


# ==============================
# Menu System
# ==============================
def main_menu():
    """Display the main menu and handle user selection."""
    while True:
        clear_screen()
        print_header(APP_NAME)
        print_info(f"Version: {VERSION}")
        print_info(f"System: {platform.system()} {platform.release()}")
        print_info(f"User: {os.environ.get('USERNAME', 'Unknown')}")
        print_info(f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print_info(f"Admin privileges: {'Yes' if is_admin() else 'No'}")

        # Display Tailscale service status
        tailscale_status = get_tailscale_service_status()
        if tailscale_status != "not_installed":
            status_color = (
                Colors.GREEN if tailscale_status == "running" else Colors.YELLOW
            )
            if ANSI_ENABLED:
                print_info(
                    f"Tailscale service: {status_color}{tailscale_status}{Colors.RESET}"
                )
            else:
                print_info(f"Tailscale service: {tailscale_status}")

        # Main menu options
        menu_options = [
            ("1", "Complete Tailscale Reset (uninstall, reinstall, restart)"),
            ("2", "Uninstall Tailscale and Remove Configuration"),
            ("3", "Install Tailscale"),
            ("4", "Start Tailscale Service"),
            ("5", "Run 'tailscale up'"),
            ("6", "Check Tailscale Status"),
            ("0", "Exit"),
        ]

        print_menu("Main Menu", menu_options)

        # Get user selection
        choice = get_user_input("Enter your choice (0-6):")

        if choice == "1":
            reset_tailscale()
            pause()
        elif choice == "2":
            uninstall_tailscale()
            pause()
        elif choice == "3":
            install_tailscale()
            pause()
        elif choice == "4":
            start_tailscale_service()
            pause()
        elif choice == "5":
            tailscale_up()
            pause()
        elif choice == "6":
            check_tailscale_status()
            pause()
        elif choice == "0":
            clear_screen()
            print_header("Goodbye!")
            print_info("Thank you for using the Tailscale Reset Utility.")
            time.sleep(1)
            sys.exit(0)
        else:
            print_error("Invalid selection. Please try again.")
            time.sleep(1)
