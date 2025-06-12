#!/usr/bin/env python3
"""
Automated Tailscale Reset Utility for Windows
---------------------------------------------

A streamlined utility that performs a complete reset of Tailscale on Windows 10/11 systems.
This tool automatically:
  • Stops the Tailscale service
  • Uninstalls Tailscale and removes configuration directories
  • Downloads and installs the latest Tailscale version
  • Starts the Tailscale service
  • Initiates the Tailscale authentication process

Note: This script requires administrator privileges.

Version: 2.0.0
"""

import os
import sys
import time
import ctypes
import shutil
import signal
import socket
import urllib.request
import subprocess
import threading
import winreg
import atexit
from pathlib import Path

# ==============================
# Configuration & Constants
# ==============================
APP_NAME = "Automated Tailscale Reset Utility"
VERSION = "2.0.0"
HOSTNAME = socket.gethostname()
LOG_DIR = os.path.join(os.path.expanduser("~"), "tailscale_reset_logs")
LOG_FILE = os.path.join(LOG_DIR, "tailscale_reset.log")
TAILSCALE_DOWNLOAD_URL = "https://pkgs.tailscale.com/stable/tailscale-setup-latest.exe"
TAILSCALE_INSTALLER_PATH = os.path.join(
    os.environ.get("TEMP", "."), "tailscale-installer.exe"
)
TAILSCALE_SERVICE_NAME = "Tailscale"

# Tailscale directories to clean
PROGRAM_DATA_DIR = os.path.join("C:\\ProgramData", "Tailscale")
USER_APPDATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Tailscale")


# ANSI color codes for Windows
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"


# ==============================
# Console Styling Setup
# ==============================
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

    # Print the header with border
    print("\n" + "=" * width)

    if ANSI_ENABLED:
        print(f"{Colors.BOLD}{Colors.CYAN}{text.center(width)}{Colors.RESET}")
    else:
        print(text.center(width))

    print("=" * width + "\n")


def print_step(text):
    """Print a step description."""
    if ANSI_ENABLED:
        print(f"{Colors.BLUE}[*] {text}{Colors.RESET}")
    else:
        print(f"[*] {text}")


def print_success(text):
    """Print a success message."""
    if ANSI_ENABLED:
        print(f"{Colors.GREEN}[+] {text}{Colors.RESET}")
    else:
        print(f"[+] {text}")


def print_warning(text):
    """Print a warning message."""
    if ANSI_ENABLED:
        print(f"{Colors.YELLOW}[!] {text}{Colors.RESET}")
    else:
        print(f"[!] {text}")


def print_error(text):
    """Print an error message."""
    if ANSI_ENABLED:
        print(f"{Colors.RED}[-] {text}{Colors.RESET}")
    else:
        print(f"[-] {text}")


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


# ==============================
# Logging Setup
# ==============================
def setup_logging():
    """Configure logging for the script."""
    import logging

    try:
        # Create log directory if it doesn't exist
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR, exist_ok=True)

        # Configure logging
        logging.basicConfig(
            filename=LOG_FILE,
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        print_step(f"Logging to: {LOG_FILE}")
        logging.info(f"=== {APP_NAME} v{VERSION} started ===")
        return logging
    except Exception as e:
        print_warning(f"Could not set up logging: {e}")
        print_step("Continuing without logging...")
        return None


# ==============================
# Signal Handling & Cleanup
# ==============================
def cleanup():
    """Perform cleanup tasks before exit."""
    # Remove temporary installer if it exists
    if os.path.exists(TAILSCALE_INSTALLER_PATH):
        try:
            os.remove(TAILSCALE_INSTALLER_PATH)
            print_step("Removed temporary installer file")
        except:
            pass


atexit.register(cleanup)


def signal_handler(signum, frame):
    """Handle termination signals gracefully."""
    print_warning("\nProcess interrupted.")
    cleanup()
    sys.exit(1)


# Register signal handlers for SIGINT (Ctrl+C)
signal.signal(signal.SIGINT, signal_handler)


# ==============================
# Simple Spinner Class
# ==============================
class Spinner:
    """Thread-safe spinner for progress indication."""

    def __init__(self, message):
        self.message = message
        self.spinner_chars = "|/-\\"
        self.current = 0
        self.spinning = False
        self.thread = None
        self.start_time = time.time()

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
            time.sleep(0.1)

    def _format_time(self, seconds):
        """Format seconds into a readable time string."""
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
    """Check if script is running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False


def run_as_admin():
    """Restart the script with administrator privileges."""
    if not is_admin():
        print_warning("Administrator privileges required.")
        print_step("Attempting to restart with elevated privileges...")

        try:
            # Create a UAC prompt to run the script with admin rights
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
            sys.exit(0)
        except Exception as e:
            print_error(f"Failed to elevate privileges: {e}")
            print_step("Please run this script as administrator manually.")
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
        error_cmd = cmd if shell else " ".join(cmd)
        print_error(f"Command failed: {error_cmd}")

        if hasattr(e, "stdout") and e.stdout:
            print(f"Output: {e.stdout.strip()}")
        if hasattr(e, "stderr") and e.stderr:
            print_error(f"Error: {e.stderr.strip()}")
        raise
    except subprocess.TimeoutExpired:
        print_error(f"Command timed out after {timeout} seconds")
        raise


def get_tailscale_service_status():
    """Get the current status of the Tailscale service."""
    try:
        result = run_command(["sc", "query", TAILSCALE_SERVICE_NAME], check=False)

        # If the command returned non-zero, service might not exist
        if result.returncode != 0:
            return "not_installed"

        # Parse the output to get service status
        for line in result.stdout.splitlines():
            if "STATE" in line:
                state_parts = line.strip().split()
                if len(state_parts) >= 4:
                    state_code = state_parts[3]

                    # State codes: 1=stopped, 2=starting, 3=stopping, 4=running
                    states = {
                        "1": "stopped",
                        "2": "starting",
                        "3": "stopping",
                        "4": "running",
                    }
                    return states.get(state_code, "unknown")

        return "unknown"
    except Exception:
        return "not_installed"


def is_tailscale_installed():
    """Check if Tailscale is installed using multiple methods."""
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
    print_step("Stopping Tailscale service...")

    # Check if service exists and is running
    status = get_tailscale_service_status()

    if status == "not_installed":
        print_warning("Tailscale service is not installed.")
        return

    if status == "stopped":
        print_step("Tailscale service is already stopped.")
        return

    try:
        with Spinner("Stopping Tailscale service") as spinner:
            run_command(["sc", "stop", TAILSCALE_SERVICE_NAME], check=False)

            # Wait for service to stop (with timeout)
            max_wait = 30  # seconds
            start_time = time.time()

            while time.time() - start_time < max_wait:
                status = get_tailscale_service_status()
                if status in ["stopped", "not_installed"]:
                    break
                time.sleep(1)

            if status not in ["stopped", "not_installed"]:
                spinner.stop(success=False)
                print_warning("Service did not stop in the expected time frame.")
    except Exception as e:
        print_error(f"Failed to stop Tailscale service: {e}")


def uninstall_tailscale():
    """Uninstall Tailscale and remove configuration directories."""
    print_step("Uninstalling Tailscale...")

    # Check if installed
    if not is_tailscale_installed():
        print_warning("Tailscale does not appear to be installed.")
        print_step("Proceeding with directory cleanup only...")
    else:
        # First stop the service
        stop_tailscale_service()

        # Then uninstall using the Windows uninstaller
        try:
            # Try to find the uninstaller in the registry
            uninstaller_path = None

            try:
                # Search in HKLM uninstall registry
                with winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                ) as key:
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
                print_step(f"Running uninstaller: {uninstaller_path}")
                with Spinner("Running Tailscale uninstaller") as spinner:
                    # Add /S for silent uninstall
                    run_command([uninstaller_path, "/S"], shell=True, check=False)
            else:
                # Fallback to direct program files check
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
                            run_command([uninstaller, "/S"], shell=True, check=False)
                        uninstaller_found = True
                        break

                if not uninstaller_found:
                    print_warning(
                        "Could not find Tailscale uninstaller. Trying wmic..."
                    )

                    # Try using wmic to uninstall
                    try:
                        with Spinner("Uninstalling via wmic") as spinner:
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
                        print_warning(f"WMIC uninstall attempt failed: {e}")
        except Exception as e:
            print_error(f"Error during uninstallation: {e}")

    # Clean up configuration and data directories
    print_step("Removing Tailscale configuration directories...")

    dirs_to_remove = [
        PROGRAM_DATA_DIR,  # C:\ProgramData\Tailscale
        USER_APPDATA_DIR,  # C:\Users\%USERNAME%\AppData\Local\Tailscale
    ]

    for directory in dirs_to_remove:
        if os.path.exists(directory):
            try:
                print_step(f"Removing {directory}...")
                shutil.rmtree(directory)
                print_success(f"Removed {directory}")
            except Exception as e:
                print_error(f"Failed to remove {directory}: {e}")
                try:
                    # Try removing with rd /s /q as fallback
                    os.system(f'rd /s /q "{directory}"')
                except:
                    print_warning(f"Directory {directory} may need manual removal")
        else:
            print_step(f"Directory {directory} already removed or doesn't exist")

    print_success("Tailscale uninstallation and cleanup completed")


def download_tailscale():
    """Download the latest Tailscale installer."""
    print_step("Downloading Tailscale installer...")

    # Remove existing installer if present
    if os.path.exists(TAILSCALE_INSTALLER_PATH):
        try:
            os.remove(TAILSCALE_INSTALLER_PATH)
        except Exception as e:
            print_error(f"Could not remove existing installer: {e}")
            return False

    try:
        with Spinner("Downloading Tailscale installer") as spinner:
            # Create a request with a proper User-Agent
            req = urllib.request.Request(
                TAILSCALE_DOWNLOAD_URL, headers={"User-Agent": "Mozilla/5.0"}
            )

            # Download the file
            with (
                urllib.request.urlopen(req) as response,
                open(TAILSCALE_INSTALLER_PATH, "wb") as out_file,
            ):
                shutil.copyfileobj(response, out_file)

        if os.path.exists(TAILSCALE_INSTALLER_PATH):
            print_success(f"Downloaded installer to {TAILSCALE_INSTALLER_PATH}")
            return True
        else:
            print_error("Download completed but installer file was not created")
            return False
    except Exception as e:
        print_error(f"Failed to download Tailscale installer: {e}")
        return False


def install_tailscale():
    """Install Tailscale using the downloaded installer."""
    print_step("Installing Tailscale...")

    # First, download the installer
    if not download_tailscale():
        print_error("Could not proceed with installation due to download failure")
        return False

    try:
        with Spinner("Installing Tailscale") as spinner:
            # Run the installer silently
            run_command([TAILSCALE_INSTALLER_PATH, "/S"], check=False)

            # Wait for installation to complete
            time.sleep(5)

            # Verify installation
            max_wait = 30  # seconds
            start_time = time.time()
            installed = False

            while time.time() - start_time < max_wait:
                if is_tailscale_installed():
                    installed = True
                    break
                time.sleep(1)

            if installed:
                return True
            else:
                spinner.stop(success=False)
                print_warning(
                    "Installation seemed to complete but Tailscale is not detected"
                )
                return False
    except Exception as e:
        print_error(f"Installation failed: {e}")
        return False


def start_tailscale_service():
    """Start the Tailscale service."""
    print_step("Starting Tailscale service...")

    # Check if service exists
    status = get_tailscale_service_status()

    if status == "not_installed":
        print_warning("Tailscale service is not installed.")
        return False

    if status == "running":
        print_step("Tailscale service is already running.")
        return True

    try:
        with Spinner("Starting Tailscale service") as spinner:
            run_command(["sc", "start", TAILSCALE_SERVICE_NAME], check=False)

            # Wait for service to start (with timeout)
            max_wait = 30  # seconds
            start_time = time.time()

            while time.time() - start_time < max_wait:
                status = get_tailscale_service_status()
                if status == "running":
                    return True
                time.sleep(1)

            spinner.stop(success=False)
            print_warning("Service did not start in the expected time frame")
            return False
    except Exception as e:
        print_error(f"Failed to start Tailscale service: {e}")
        return False


def tailscale_up():
    """Run 'tailscale up' to authenticate and connect the node."""
    print_step("Running Tailscale authentication...")

    if not is_tailscale_installed():
        print_error("Tailscale is not installed. Cannot proceed with authentication.")
        return False

    # Ensure service is running
    status = get_tailscale_service_status()
    if status != "running":
        print_warning("Tailscale service is not running. Attempting to start it...")
        if not start_tailscale_service():
            print_error(
                "Could not start Tailscale service. Cannot proceed with authentication."
            )
            return False

    program_files = os.environ.get("PROGRAMFILES", "C:\\Program Files")
    tailscale_exe = os.path.join(program_files, "Tailscale", "tailscale.exe")

    if not os.path.exists(tailscale_exe):
        print_error(f"Could not find tailscale.exe at {tailscale_exe}")
        return False

    print_step("This will launch Tailscale login in your browser")
    if not get_user_confirmation(
        "Do you want to proceed with Tailscale authentication?"
    ):
        print_step("Tailscale authentication skipped")
        return True  # Not an error, user choice

    try:
        # Run tailscale up
        print_step("Launching Tailscale authentication...")
        run_command([tailscale_exe, "up"], capture_output=False, check=False)

        print_success("Tailscale authentication process completed")
        return True
    except Exception as e:
        print_error(f"Error during Tailscale authentication: {e}")
        return False


def perform_full_reset():
    """Perform a complete reset of Tailscale."""
    print_header(f"{APP_NAME} v{VERSION}")
    print_step(f"Starting Tailscale reset on {HOSTNAME}")

    # Check for admin rights
    if not is_admin():
        run_as_admin()  # This will restart the script with admin rights

    # Confirm with user
    if not get_user_confirmation("This will completely reset Tailscale. Continue?"):
        print_step("Reset cancelled by user.")
        return

    # Set up logging
    logger = setup_logging()
    if logger:
        logger.info("Starting Tailscale reset process")

    # Step 1: Uninstall and clean up
    print_step("STEP 1/4: Uninstalling Tailscale and cleaning up...")
    uninstall_tailscale()

    # Small pause between operations
    time.sleep(2)

    # Step 2: Install Tailscale
    print_step("STEP 2/4: Installing Tailscale...")
    if not install_tailscale():
        print_error("Installation failed. Tailscale reset process incomplete.")
        if logger:
            logger.error("Tailscale installation failed")
        return

    # Small pause between operations
    time.sleep(2)

    # Step 3: Start Tailscale service
    print_step("STEP 3/4: Starting Tailscale service...")
    if not start_tailscale_service():
        print_error(
            "Failed to start Tailscale service. Tailscale reset process incomplete."
        )
        if logger:
            logger.error("Failed to start Tailscale service")
        return

    # Small pause between operations
    time.sleep(2)

    # Step 4: Run Tailscale up
    print_step("STEP 4/4: Tailscale authentication...")
    tailscale_up()  # Not failing on this step since user might choose to skip

    # Final status message
    print_success("Tailscale reset process completed!")
    if logger:
        logger.info("Tailscale reset process completed successfully")


# ==============================
# Main Entry Point
# ==============================
if __name__ == "__main__":
    try:
        perform_full_reset()
    except KeyboardInterrupt:
        print_warning("\nProcess interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
