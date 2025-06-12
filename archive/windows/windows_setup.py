#!/usr/bin/env python3
"""
Windows Server Initialization and Hardening Utility

This utility automates the initialization, configuration, and security hardening
of a Windows 10/11 machine. It is divided into clear phases:
  1. Pre-flight Checks
  2. System Update & Basic Configuration
  3. Package Installation (using Chocolatey)
  4. User Environment Setup
  5. Security & Access Hardening
  6. Service Installations
  7. Maintenance Tasks
  8. System Tuning & Permissions
  9. Final Checks & Cleanup

Run this script as administrator. Use --help for command-line options.

License: MIT
Version: 1.0.0
"""

import atexit
import argparse
import datetime
import filecmp
import gzip
import json
import logging
import os
import re
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import signal
import winreg
import ctypes
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path

#####################################
# Global Configuration & Constants
#####################################

USERNAME = os.getenv("USERNAME", "Administrator")
USER_HOME = os.path.expanduser("~")
BACKUP_DIR = os.path.join(os.environ.get("PROGRAMDATA", "C:\\ProgramData"), "Backups")
TEMP_DIR = tempfile.gettempdir()
LOG_FILE = os.path.join(
    os.environ.get("PROGRAMDATA", "C:\\ProgramData"), "WindowsSetup.log"
)
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB

# Software Versions and URLs
FASTFETCH_URL = "https://github.com/fastfetch-cli/fastfetch/releases/download/2.37.0/fastfetch-windows-amd64.zip"

# List of configuration files to back up
CONFIG_FILES = [
    os.path.join(os.environ["WINDIR"], "System32", "drivers", "etc", "hosts"),
    os.path.join(os.environ["WINDIR"], "System32", "drivers", "etc", "services"),
    os.path.join(
        os.environ["WINDIR"], "System32", "WindowsPowerShell", "v1.0", "profile.ps1"
    ),
]

# TCP ports allowed through the firewall
ALLOWED_PORTS = ["80", "443", "3389", "22"]  # Default RDP port included

# Essential packages to be installed via Chocolatey
PACKAGES = [
    "7zip",
    "git",
    "vscode",
    "googlechrome",
    "firefox",
    "notepadplusplus",
    "putty",
    "curl",
    "wget",
    "python3",
    "nodejs",
    "openssh",
    "vim",
    "sysinternals",
    "powershell-core",
    "wsl2",
    "sudo",
    "terminals",
    "docker-desktop",
    "wireshark",
    "adobereader",
    "windirstat",
    "everything",
    "nmap",
    "tcping",
    "nssm",
    "filezilla",
    "tailscale",
    "powertoys",
    "microsoft-windows-terminal",
]

# Global task status dictionary
SETUP_STATUS: Dict[str, Dict[str, str]] = {
    "preflight": {"status": "pending", "message": ""},
    "system_update": {"status": "pending", "message": ""},
    "choco_install": {"status": "pending", "message": ""},
    "packages_install": {"status": "pending", "message": ""},
    "user_env": {"status": "pending", "message": ""},
    "security": {"status": "pending", "message": ""},
    "services": {"status": "pending", "message": ""},
    "maintenance": {"status": "pending", "message": ""},
    "tuning": {"status": "pending", "message": ""},
    "final": {"status": "pending", "message": ""},
}

#####################################
# ANSI Color Codes (Nord Palette)
#####################################

NORD0 = "\033[38;2;46;52;64m"
NORD1 = "\033[38;2;59;66;82m"
NORD8 = "\033[38;2;136;192;208m"
NORD9 = "\033[38;2;129;161;193m"
NORD10 = "\033[38;2;94;129;172m"
NORD11 = "\033[38;2;191;97;106m"
NORD13 = "\033[38;2;235;203;139m"
NORD14 = "\033[38;2;163;190;140m"
NC = "\033[0m"  # Reset color

#####################################
# Logging Setup with Nord Color Formatter
#####################################


class NordColorFormatter(logging.Formatter):
    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        use_colors: bool = True,
    ):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        if not self.use_colors:
            return message
        if record.levelname == "DEBUG":
            return f"{NORD9}{message}{NC}"
        elif record.levelname == "INFO":
            return f"{NORD14}{message}{NC}"
        elif record.levelname == "WARNING":
            return f"{NORD13}{message}{NC}"
        elif record.levelname in ("ERROR", "CRITICAL"):
            return f"{NORD11}{message}{NC}"
        return message


def setup_logging() -> logging.Logger:
    os.makedirs(os.path.dirname(LOG_FILE), mode=0o700, exist_ok=True)
    if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > MAX_LOG_SIZE:
        # Simple log rotation: archive the old log
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        rotated_file = f"{LOG_FILE}.{timestamp}.gz"
        try:
            with open(LOG_FILE, "rb") as fin, gzip.open(rotated_file, "wb") as fout:
                shutil.copyfileobj(fin, fout)
            open(LOG_FILE, "w").close()
        except Exception:
            pass
    logger = logging.getLogger("windows_setup")
    logger.setLevel(logging.DEBUG)
    # Remove existing handlers
    for h in list(logger.handlers):
        logger.removeHandler(h)
    formatter = NordColorFormatter(
        "[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger


logger = setup_logging()

#####################################
# Helper Functions
#####################################


def print_section(title: str) -> None:
    border = "─" * 60
    print(f"{NORD8}{border}{NC}")
    print(f"{NORD8}  {title}{NC}")
    print(f"{NORD8}{border}{NC}")
    logger.info(f"--- {title} ---")


def print_status_report() -> None:
    print_section("Setup Status Report")
    icons = {
        "success": "✓",
        "failed": "✗",
        "pending": "?",
        "in_progress": "⋯",
        "skipped": "⏭",
        "warning": "⚠",
    }
    colors = {
        "success": NORD14,
        "failed": NORD11,
        "pending": NORD13,
        "in_progress": NORD9,
        "skipped": NORD8,
        "warning": NORD13,
    }
    descriptions = {
        "preflight": "Pre-flight Checks",
        "system_update": "System Update",
        "choco_install": "Chocolatey Installation",
        "packages_install": "Package Installation",
        "user_env": "User Environment Setup",
        "security": "Security Hardening",
        "services": "Service Installation",
        "maintenance": "Maintenance Tasks",
        "tuning": "System Tuning",
        "final": "Final Checks & Cleanup",
    }
    for task, data in SETUP_STATUS.items():
        status = data["status"]
        msg = data["message"]
        task_desc = descriptions.get(task, task)
        icon = icons.get(status, "?")
        color = colors.get(status, "")
        print(f"{color}{icon} {task_desc}: {status.upper()}{NC} - {msg}")


def run_with_progress(
    description: str, func, *args, task_name: Optional[str] = None, **kwargs
) -> Any:
    if task_name:
        SETUP_STATUS[task_name] = {
            "status": "in_progress",
            "message": f"{description} in progress...",
        }
    print(f"{NORD8}[*] {description}...{NC}")
    start_time = time.time()
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            while not future.done():
                time.sleep(0.5)
            result = future.result()
        elapsed = time.time() - start_time
        print(f"{NORD14}[✓] {description} completed in {elapsed:.2f}s{NC}")
        if task_name:
            SETUP_STATUS[task_name] = {
                "status": "success",
                "message": f"{description} completed successfully.",
            }
        return result
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"{NORD11}[✗] {description} failed in {elapsed:.2f}s: {e}{NC}")
        if task_name:
            SETUP_STATUS[task_name] = {
                "status": "failed",
                "message": f"{description} failed: {e}",
            }
        raise


#####################################
# Signal Handling & Cleanup
#####################################


def signal_handler(signum: int, frame: Optional[Any]) -> None:
    sig_name = f"signal {signum}"
    logger.error(f"Script interrupted by {sig_name}.")
    try:
        cleanup()
    except Exception as e:
        logger.error(f"Error during cleanup after signal: {e}")
    sys.exit(128 + signum)


# Windows doesn't have SIGHUP, only registering SIGINT and SIGTERM
for s in (signal.SIGINT, signal.SIGTERM):
    signal.signal(s, signal_handler)


def cleanup() -> None:
    logger.info("Performing cleanup tasks before exit.")
    for fname in os.listdir(tempfile.gettempdir()):
        if fname.startswith("windows_setup_"):
            try:
                os.remove(os.path.join(tempfile.gettempdir(), fname))
            except Exception:
                pass
    if any(item["status"] != "pending" for item in SETUP_STATUS.values()):
        print_status_report()


atexit.register(cleanup)

#####################################
# Utility Class
#####################################


class Utils:
    @staticmethod
    def run_command(
        cmd: Union[List[str], str],
        check: bool = True,
        capture_output: bool = False,
        text: bool = True,
        shell: bool = False,
        **kwargs,
    ) -> subprocess.CompletedProcess:
        cmd_str = " ".join(cmd) if isinstance(cmd, list) and not shell else cmd
        logger.debug(f"Executing command: {cmd_str}")
        try:
            result = subprocess.run(
                cmd,
                check=check,
                capture_output=capture_output,
                text=text,
                shell=shell,
                **kwargs,
            )
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {cmd_str} with exit code {e.returncode}")
            logger.debug(f"Error output: {getattr(e, 'stderr', 'N/A')}")
            raise

    @staticmethod
    def command_exists(cmd: str) -> bool:
        return shutil.which(cmd) is not None

    @staticmethod
    def backup_file(file_path: str) -> Optional[str]:
        if os.path.isfile(file_path):
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            backup = f"{file_path}.bak.{timestamp}"
            try:
                shutil.copy2(file_path, backup)
                logger.info(f"Backed up {file_path} to {backup}")
                return backup
            except Exception as e:
                logger.warning(f"Failed to backup {file_path}: {e}")
                return None
        else:
            logger.warning(f"File {file_path} not found; skipping backup.")
            return None

    @staticmethod
    def ensure_directory(path: str, mode: int = 0o755) -> bool:
        try:
            os.makedirs(path, mode=mode, exist_ok=True)
            logger.debug(f"Ensured directory exists: {path}")
            return True
        except Exception as e:
            logger.warning(f"Failed to ensure directory {path}: {e}")
            return False

    @staticmethod
    def is_port_open(port: int, host: str = "127.0.0.1") -> bool:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0

    @staticmethod
    def run_powershell_command(
        command: str,
        capture_output: bool = False,
        check: bool = True,
        text: bool = True,
    ) -> subprocess.CompletedProcess:
        """Run a PowerShell command and return the result."""
        cmd = ["powershell", "-Command", command]
        return Utils.run_command(
            cmd, capture_output=capture_output, check=check, text=text
        )

    @staticmethod
    def set_registry_value(
        key_path: str, name: str, value, value_type=winreg.REG_SZ
    ) -> bool:
        """Set a Windows registry value."""
        try:
            # Split the key_path into the root key and subkey parts
            if key_path.startswith("HKLM\\") or key_path.startswith(
                "HKEY_LOCAL_MACHINE\\"
            ):
                root_key = winreg.HKEY_LOCAL_MACHINE
                subkey = key_path.replace("HKLM\\", "").replace(
                    "HKEY_LOCAL_MACHINE\\", ""
                )
            elif key_path.startswith("HKCU\\") or key_path.startswith(
                "HKEY_CURRENT_USER\\"
            ):
                root_key = winreg.HKEY_CURRENT_USER
                subkey = key_path.replace("HKCU\\", "").replace(
                    "HKEY_CURRENT_USER\\", ""
                )
            else:
                logger.error(f"Unsupported registry key: {key_path}")
                return False

            # Open or create the registry key
            key = winreg.CreateKeyEx(root_key, subkey, 0, winreg.KEY_WRITE)

            # Set the value
            winreg.SetValueEx(key, name, 0, value_type, value)
            winreg.CloseKey(key)
            logger.info(f"Set registry value: {key_path}\\{name} = {value}")
            return True
        except Exception as e:
            logger.warning(f"Failed to set registry value {key_path}\\{name}: {e}")
            return False

    @staticmethod
    def get_registry_value(key_path: str, name: str, default=None):
        """Get a Windows registry value."""
        try:
            # Split the key_path into the root key and subkey parts
            if key_path.startswith("HKLM\\") or key_path.startswith(
                "HKEY_LOCAL_MACHINE\\"
            ):
                root_key = winreg.HKEY_LOCAL_MACHINE
                subkey = key_path.replace("HKLM\\", "").replace(
                    "HKEY_LOCAL_MACHINE\\", ""
                )
            elif key_path.startswith("HKCU\\") or key_path.startswith(
                "HKEY_CURRENT_USER\\"
            ):
                root_key = winreg.HKEY_CURRENT_USER
                subkey = key_path.replace("HKCU\\", "").replace(
                    "HKEY_CURRENT_USER\\", ""
                )
            else:
                logger.error(f"Unsupported registry key: {key_path}")
                return default

            # Open the registry key
            key = winreg.OpenKey(root_key, subkey, 0, winreg.KEY_READ)

            # Get the value
            value, value_type = winreg.QueryValueEx(key, name)
            winreg.CloseKey(key)
            return value
        except Exception as e:
            logger.debug(f"Failed to get registry value {key_path}\\{name}: {e}")
            return default


#####################################
# Phase 1: Pre-flight Checks
#####################################


class PreflightChecker:
    def check_admin(self) -> None:
        if not ctypes.windll.shell32.IsUserAnAdmin():
            print(f"{NORD11}Error: This script must be run as administrator.{NC}")
            print(f"Right-click the script and select 'Run as administrator'.")
            sys.exit(1)
        logger.info("Administrator privileges confirmed.")

    def check_network(self) -> bool:
        logger.info("Performing network connectivity check...")
        test_hosts = ["google.com", "cloudflare.com", "1.1.1.1"]
        for host in test_hosts:
            try:
                result = Utils.run_command(
                    ["ping", "-n", "1", "-w", "5000", host],
                    check=False,
                    capture_output=True,
                )
                if result.returncode == 0:
                    logger.info(f"Network connectivity verified via {host}.")
                    return True
            except Exception as e:
                logger.debug(f"Ping to {host} failed: {e}")
        logger.error("No network connectivity. Please verify your network settings.")
        return False

    def check_os_version(self) -> Optional[Tuple[str, str]]:
        logger.info("Checking OS version...")
        try:
            result = Utils.run_powershell_command(
                "(Get-WmiObject -Class Win32_OperatingSystem).Caption, (Get-WmiObject -Class Win32_OperatingSystem).Version",
                capture_output=True,
                text=True,
            )
            os_info = result.stdout.strip().split("\n")

            if (
                "Microsoft Windows 10" in os_info[0]
                or "Microsoft Windows 11" in os_info[0]
            ):
                logger.info(f"Detected OS: {os_info[0].strip()}")
                return ("windows", os_info[1].strip())
            else:
                logger.warning(
                    f"Detected non-Windows 10/11 system: {os_info[0].strip()}"
                )
                return None
        except Exception as e:
            logger.warning(f"Failed to determine OS version: {e}")
            return None

    def save_config_snapshot(self) -> Optional[str]:
        logger.info("Saving configuration snapshot...")
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        Utils.ensure_directory(BACKUP_DIR)
        snapshot_file = os.path.join(BACKUP_DIR, f"config_snapshot_{timestamp}.zip")
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                for cfg in CONFIG_FILES:
                    if os.path.isfile(cfg):
                        shutil.copy2(cfg, os.path.join(temp_dir, os.path.basename(cfg)))
                        logger.info(f"Included {cfg} in snapshot.")
                    else:
                        logger.debug(f"{cfg} not found; skipping.")

                # Create a manifest file
                with open(os.path.join(temp_dir, "MANIFEST.txt"), "w") as f:
                    f.write("Windows Configuration Backup\n")
                    f.write(f"Created: {datetime.datetime.now()}\n")
                    f.write(f"Computer Name: {socket.gethostname()}\n\n")
                    f.write("Files included:\n")
                    for cfg in CONFIG_FILES:
                        if os.path.isfile(cfg):
                            f.write(f"- {cfg}\n")

                # Export registry settings for Windows Firewall
                Utils.run_powershell_command(
                    f"reg export 'HKLM\\SYSTEM\\CurrentControlSet\\Services\\SharedAccess\\Parameters\\FirewallPolicy' '{os.path.join(temp_dir, 'FirewallPolicy.reg')}'",
                    check=False,
                )

                # Create the zip archive
                shutil.make_archive(snapshot_file.replace(".zip", ""), "zip", temp_dir)

            logger.info(f"Configuration snapshot saved to {snapshot_file}")
            return snapshot_file
        except Exception as e:
            logger.warning(f"Failed to create configuration snapshot: {e}")
            return None


#####################################
# Phase 2: System Update & Basic Configuration
#####################################


class SystemUpdater:
    def update_system(self) -> bool:
        logger.info("Checking for Windows Updates...")
        try:
            # Check for PSWindowsUpdate module
            module_check = Utils.run_powershell_command(
                "Get-Module -ListAvailable -Name PSWindowsUpdate",
                capture_output=True,
                check=False,
            )

            if "PSWindowsUpdate" not in module_check.stdout:
                logger.info("Installing PSWindowsUpdate module...")
                Utils.run_powershell_command(
                    "Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force; "
                    "Set-PSRepository -Name 'PSGallery' -InstallationPolicy Trusted; "
                    "Install-Module -Name PSWindowsUpdate -Force",
                    check=False,
                )

            # Check for available updates
            logger.info("Checking for updates...")
            update_check = Utils.run_powershell_command(
                "Import-Module PSWindowsUpdate; Get-WindowsUpdate",
                capture_output=True,
                check=False,
            )

            if "No updates found" in update_check.stdout:
                logger.info("No Windows updates found.")
                return True

            logger.info("Installing Windows Updates (this may take some time)...")
            Utils.run_powershell_command(
                "Import-Module PSWindowsUpdate; Install-WindowsUpdate -AcceptAll -AutoReboot:$false",
                check=False,
            )

            logger.info("Windows updates completed. Some updates may require a reboot.")
            return True
        except Exception as e:
            logger.error(f"Windows Update error: {e}")
            return False

    def configure_timezone(self, timezone: str = "Eastern Standard Time") -> bool:
        logger.info(f"Setting timezone to {timezone}...")
        try:
            Utils.run_powershell_command(f"Set-TimeZone -Id '{timezone}'")
            logger.info("Timezone configured.")
            return True
        except Exception as e:
            logger.error(f"Timezone configuration failed: {e}")
            return False

    def configure_locale(self, locale: str = "en-US") -> bool:
        logger.info(f"Setting locale to {locale}...")
        try:
            # Set system locale
            Utils.run_powershell_command(f"Set-WinSystemLocale -SystemLocale {locale}")

            # Set user locale
            Utils.run_powershell_command(
                f"Set-WinUserLanguageList -LanguageList {locale} -Force"
            )

            logger.info("Locale configured.")
            return True
        except Exception as e:
            logger.error(f"Locale configuration failed: {e}")
            return False

    def install_chocolatey(self) -> bool:
        logger.info("Installing Chocolatey package manager...")
        if Utils.command_exists("choco"):
            logger.info("Chocolatey already installed.")
            return True

        try:
            # Run PowerShell command to install Chocolatey
            installation_cmd = (
                "[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; "
                "iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))"
            )
            Utils.run_powershell_command(installation_cmd)

            # Refresh environment variables
            os.environ["PATH"] = (
                os.environ["PATH"] + os.pathsep + "C:\\ProgramData\\chocolatey\\bin"
            )

            # Verify installation
            if Utils.command_exists("choco"):
                logger.info("Chocolatey installed successfully.")
                return True
            else:
                logger.error("Chocolatey installation verification failed.")
                return False
        except Exception as e:
            logger.error(f"Chocolatey installation error: {e}")
            return False

    def install_packages(self, packages: Optional[List[str]] = None) -> bool:
        logger.info("Installing required packages...")
        packages = packages or PACKAGES

        if not Utils.command_exists("choco"):
            logger.error("Chocolatey not installed. Cannot install packages.")
            return False

        try:
            # Install packages in groups to avoid command line length issues
            group_size = 10
            success = True

            for i in range(0, len(packages), group_size):
                package_group = packages[i : i + group_size]
                logger.info(f"Installing package group: {', '.join(package_group)}")

                try:
                    Utils.run_command(
                        ["choco", "install", "-y"] + package_group, check=True
                    )
                except Exception as e:
                    logger.warning(f"Failed to install package group: {e}")
                    success = False

            # Refresh environment variables to include newly installed packages
            Utils.run_powershell_command("refreshenv")

            logger.info("Package installation completed.")
            return success
        except Exception as e:
            logger.error(f"Package installation error: {e}")
            return False


#####################################
# Phase 3: User Environment Setup
#####################################


class UserEnvironment:
    def setup_repos(self) -> bool:
        logger.info(f"Setting up GitHub repositories for user...")
        gh_dir = os.path.join(USER_HOME, "GitHub")
        Utils.ensure_directory(gh_dir)
        repos = ["windows", "web", "python", "go", "misc"]
        all_success = True

        for repo in repos:
            repo_dir = os.path.join(gh_dir, repo)
            if os.path.isdir(os.path.join(repo_dir, ".git")):
                logger.info(f"Repository '{repo}' exists; pulling latest changes...")
                try:
                    Utils.run_command(["git", "-C", repo_dir, "pull"], check=False)
                except Exception:
                    logger.warning(f"Failed to update repository '{repo}'.")
                    all_success = False
            else:
                logger.info(f"Cloning repository '{repo}'...")
                try:
                    Utils.run_command(
                        [
                            "git",
                            "clone",
                            f"https://github.com/dunamismax/{repo}.git",
                            repo_dir,
                        ],
                        check=False,
                    )
                    logger.info(f"Repository '{repo}' cloned.")
                except Exception:
                    logger.warning(f"Failed to clone repository '{repo}'.")
                    all_success = False
        return all_success

    def setup_powershell_profile(self) -> bool:
        logger.info("Setting up PowerShell profile...")

        # Define profile paths
        ps_profile_dir = os.path.join(USER_HOME, "Documents", "WindowsPowerShell")
        ps_profile_path = os.path.join(
            ps_profile_dir, "Microsoft.PowerShell_profile.ps1"
        )
        ps_core_profile_dir = os.path.join(USER_HOME, "Documents", "PowerShell")
        ps_core_profile_path = os.path.join(
            ps_core_profile_dir, "Microsoft.PowerShell_profile.ps1"
        )

        # Create profile directories if they don't exist
        Utils.ensure_directory(ps_profile_dir)
        Utils.ensure_directory(ps_core_profile_dir)

        # Backup existing profiles
        if os.path.exists(ps_profile_path):
            Utils.backup_file(ps_profile_path)
        if os.path.exists(ps_core_profile_path):
            Utils.backup_file(ps_core_profile_path)

        # Create profile content
        profile_content = """
# PowerShell Profile
# Setup by Windows Server Initialization Utility

# Set encoding to UTF-8
$OutputEncoding = [System.Text.Encoding]::UTF8

# Import modules
if (Get-Module -ListAvailable -Name PSReadLine) {
    Import-Module PSReadLine
    Set-PSReadLineOption -PredictionSource History
    Set-PSReadLineOption -HistorySearchCursorMovesToEnd
    Set-PSReadLineKeyHandler -Key UpArrow -Function HistorySearchBackward
    Set-PSReadLineKeyHandler -Key DownArrow -Function HistorySearchForward
}

# Set aliases
Set-Alias -Name ll -Value Get-ChildItem
Set-Alias -Name grep -Value Select-String
Set-Alias -Name which -Value Get-Command
Set-Alias -Name touch -Value New-Item

# Custom prompt
function prompt {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal] $identity
    $adminRole = [Security.Principal.WindowsBuiltInRole]::Administrator

    $prefix = if ($principal.IsInRole($adminRole)) { "[ADMIN] " } else { "" }
    $host.UI.RawUI.WindowTitle = "$prefix$env:USERNAME@$env:COMPUTERNAME : $(Get-Location)"
    
    return "PS $($executionContext.SessionState.Path.CurrentLocation)$('>' * ($nestedPromptLevel + 1)) "
}

# Helper functions
function Test-Administrator {
    $user = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal $user
    $principal.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
}

function Update-System {
    if (-not (Test-Administrator)) {
        Write-Warning "This function requires administrator privileges."
        return
    }
    
    Write-Host "Updating Windows..." -ForegroundColor Cyan
    if (Get-Module -ListAvailable -Name PSWindowsUpdate) {
        Import-Module PSWindowsUpdate
        Get-WindowsUpdate -Install -AcceptAll -AutoReboot:$false
    } else {
        Write-Warning "PSWindowsUpdate module not found. Please install it with: 'Install-Module PSWindowsUpdate -Force'"
    }
    
    Write-Host "Updating Chocolatey packages..." -ForegroundColor Cyan
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        choco upgrade all -y
    } else {
        Write-Warning "Chocolatey not found. Please install it first."
    }
}

# Welcome message
Write-Host "Welcome to PowerShell on $env:COMPUTERNAME" -ForegroundColor Green
$isAdmin = if (Test-Administrator) { "Yes" } else { "No" }
Write-Host "Admin: $isAdmin | PowerShell version: $($PSVersionTable.PSVersion)" -ForegroundColor Gray
"""

        try:
            # Write to both profile paths
            with open(ps_profile_path, "w") as f:
                f.write(profile_content)

            with open(ps_core_profile_path, "w") as f:
                f.write(profile_content)

            logger.info("PowerShell profiles created successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to create PowerShell profiles: {e}")
            return False

    def configure_windows_terminal(self) -> bool:
        logger.info("Configuring Windows Terminal...")

        # Check if Windows Terminal is installed
        terminal_settings_path = os.path.join(
            USER_HOME,
            "AppData",
            "Local",
            "Packages",
            "Microsoft.WindowsTerminal_8wekyb3d8bbwe",
            "LocalState",
            "settings.json",
        )

        # Also check for unpackaged Windows Terminal
        if not os.path.exists(terminal_settings_path):
            terminal_settings_path = os.path.join(
                USER_HOME,
                "AppData",
                "Local",
                "Microsoft",
                "Windows Terminal",
                "settings.json",
            )

        if not os.path.exists(terminal_settings_path):
            logger.warning(
                "Windows Terminal settings file not found. Skipping configuration."
            )
            return False

        # Backup existing settings
        if os.path.exists(terminal_settings_path):
            Utils.backup_file(terminal_settings_path)

        try:
            # Read existing settings
            with open(terminal_settings_path, "r") as f:
                settings = json.load(f)

            # Modify settings
            settings.setdefault("profiles", {}).setdefault("defaults", {}).update(
                {
                    "colorScheme": "Nord",
                    "font": {"face": "Cascadia Code PL", "size": 11},
                    "useAcrylic": True,
                    "acrylicOpacity": 0.8,
                    "padding": "8, 8, 8, 8",
                }
            )

            # Add Nord color scheme if it doesn't exist
            nord_scheme = {
                "name": "Nord",
                "background": "#2E3440",
                "foreground": "#D8DEE9",
                "cursorColor": "#D8DEE9",
                "black": "#3B4252",
                "blue": "#81A1C1",
                "cyan": "#88C0D0",
                "green": "#A3BE8C",
                "purple": "#B48EAD",
                "red": "#BF616A",
                "white": "#E5E9F0",
                "yellow": "#EBCB8B",
                "brightBlack": "#4C566A",
                "brightBlue": "#81A1C1",
                "brightCyan": "#8FBCBB",
                "brightGreen": "#A3BE8C",
                "brightPurple": "#B48EAD",
                "brightRed": "#BF616A",
                "brightWhite": "#ECEFF4",
                "brightYellow": "#EBCB8B",
            }

            # Check if Nord scheme already exists
            schemes = settings.setdefault("schemes", [])
            if not any(scheme.get("name") == "Nord" for scheme in schemes):
                schemes.append(nord_scheme)

            # Write updated settings
            with open(terminal_settings_path, "w") as f:
                json.dump(settings, f, indent=4)

            logger.info("Windows Terminal configured successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to configure Windows Terminal: {e}")
            return False


#####################################
# Phase 4: Security & Access Hardening
#####################################


class SecurityHardener:
    def configure_windows_firewall(self) -> bool:
        logger.info("Configuring Windows Firewall...")
        try:
            # Enable Windows Firewall for all profiles
            Utils.run_powershell_command(
                "Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True"
            )

            # Allow specific ports
            for port in ALLOWED_PORTS:
                tcp_rule_name = f"Allow-TCP-{port}"
                check_rule = Utils.run_powershell_command(
                    f"Get-NetFirewallRule -DisplayName '{tcp_rule_name}' -ErrorAction SilentlyContinue",
                    capture_output=True,
                    check=False,
                )

                if not check_rule.stdout.strip():
                    Utils.run_powershell_command(
                        f"New-NetFirewallRule -DisplayName '{tcp_rule_name}' -Direction Inbound -Protocol TCP -LocalPort {port} -Action Allow"
                    )
                    logger.info(f"Created firewall rule to allow TCP port {port}.")

            # Enable logging
            Utils.run_powershell_command(
                "Set-NetFirewallProfile -Profile Domain,Public,Private -LogBlocked True -LogMaxSize 4096"
            )

            logger.info("Windows Firewall configured successfully.")
            return True
        except Exception as e:
            logger.error(f"Windows Firewall configuration error: {e}")
            return False

    def configure_windows_defender(self) -> bool:
        logger.info("Configuring Windows Defender...")
        try:
            # Enable real-time monitoring
            Utils.run_powershell_command(
                "Set-MpPreference -DisableRealtimeMonitoring $false"
            )

            # Enable cloud-based protection
            Utils.run_powershell_command("Set-MpPreference -MAPSReporting Advanced")

            # Enable behavior monitoring
            Utils.run_powershell_command(
                "Set-MpPreference -DisableBehaviorMonitoring $false"
            )

            # Enable script scanning
            Utils.run_powershell_command(
                "Set-MpPreference -DisableScriptScanning $false"
            )

            # Enable archive scanning
            Utils.run_powershell_command(
                "Set-MpPreference -DisableArchiveScanning $false"
            )

            # Set scan schedule to daily
            Utils.run_powershell_command("Set-MpPreference -ScanScheduleDay Everyday")

            # Run a quick scan
            logger.info("Running a quick Windows Defender scan...")
            Utils.run_powershell_command(
                "Start-MpScan -ScanType QuickScan", check=False
            )

            logger.info("Windows Defender configured successfully.")
            return True
        except Exception as e:
            logger.error(f"Windows Defender configuration error: {e}")
            return False

    def harden_user_account_control(self) -> bool:
        logger.info("Hardening User Account Control (UAC)...")
        try:
            # Registry path for UAC settings
            uac_key = (
                "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System"
            )

            # Set UAC to the highest level
            Utils.set_registry_value(uac_key, "EnableLUA", 1, winreg.REG_DWORD)
            Utils.set_registry_value(
                uac_key, "ConsentPromptBehaviorAdmin", 2, winreg.REG_DWORD
            )
            Utils.set_registry_value(
                uac_key, "ConsentPromptBehaviorUser", 1, winreg.REG_DWORD
            )
            Utils.set_registry_value(
                uac_key, "PromptOnSecureDesktop", 1, winreg.REG_DWORD
            )

            logger.info("User Account Control hardened successfully.")
            return True
        except Exception as e:
            logger.error(f"UAC hardening error: {e}")
            return False

    def configure_secure_boot(self) -> bool:
        logger.info("Checking Secure Boot status...")
        try:
            result = Utils.run_powershell_command(
                "Confirm-SecureBootUEFI -ErrorAction SilentlyContinue",
                capture_output=True,
                check=False,
            )

            if "True" in result.stdout:
                logger.info("Secure Boot is enabled.")
                return True
            else:
                logger.warning(
                    "Secure Boot is not enabled. Please enable it in your BIOS/UEFI settings."
                )
                return False
        except Exception as e:
            logger.error(f"Secure Boot check error: {e}")
            return False

    def configure_bitlocker(self) -> bool:
        logger.info("Checking BitLocker status...")
        try:
            # Check if BitLocker is available
            bitlocker_check = Utils.run_powershell_command(
                "Get-Command -Module BitLocker -ErrorAction SilentlyContinue",
                capture_output=True,
                check=False,
            )

            if not bitlocker_check.stdout.strip():
                logger.warning(
                    "BitLocker commands not available. Installing BitLocker feature..."
                )
                Utils.run_powershell_command(
                    "Install-WindowsFeature -Name BitLocker -IncludeAllSubFeature -IncludeManagementTools",
                    check=False,
                )

            # Check C: drive status
            status = Utils.run_powershell_command(
                "Get-BitLockerVolume -MountPoint 'C:' -ErrorAction SilentlyContinue",
                capture_output=True,
                check=False,
            )

            if (
                "FullyEncrypted" in status.stdout
                or "EncryptionInProgress" in status.stdout
            ):
                logger.info("BitLocker is already enabled on drive C:.")
                return True
            else:
                logger.warning(
                    "BitLocker is not enabled on drive C:. Please enable it manually using BitLocker Drive Encryption in Control Panel."
                )
                return False
        except Exception as e:
            logger.error(f"BitLocker check error: {e}")
            return False


#####################################
# Phase 5: Service Installations
#####################################


class ServiceInstaller:
    def install_fastfetch(self) -> bool:
        logger.info("Installing Fastfetch...")
        # Check if already installed via Chocolatey
        if Utils.command_exists("fastfetch"):
            logger.info("Fastfetch already installed; skipping.")
            return True

        try:
            # Try installing via Chocolatey
            Utils.run_command(["choco", "install", "fastfetch", "-y"], check=False)

            # Check if installation succeeded
            if Utils.command_exists("fastfetch"):
                logger.info("Fastfetch installed successfully via Chocolatey.")
                return True

            # If not, download manually
            temp_zip = os.path.join(TEMP_DIR, "fastfetch.zip")
            temp_extract = os.path.join(TEMP_DIR, "fastfetch")
            install_dir = os.path.join(
                os.environ.get("PROGRAMFILES", "C:\\Program Files"), "Fastfetch"
            )

            Utils.run_command(["curl", "-L", "-o", temp_zip, FASTFETCH_URL])

            # Create directory if it doesn't exist
            Utils.ensure_directory(temp_extract)
            Utils.ensure_directory(install_dir)

            # Extract using PowerShell
            Utils.run_powershell_command(
                f"Expand-Archive -Path '{temp_zip}' -DestinationPath '{temp_extract}' -Force"
            )

            # Copy files to install directory
            for file in os.listdir(temp_extract):
                src = os.path.join(temp_extract, file)
                dst = os.path.join(install_dir, file)
                shutil.copy2(src, dst)

            # Add to PATH if it's not already there
            path_key = (
                "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment"
            )
            current_path = Utils.get_registry_value(path_key, "Path", "")

            if install_dir not in current_path:
                new_path = current_path + ";" + install_dir
                Utils.set_registry_value(path_key, "Path", new_path)
                # Update current process PATH
                os.environ["PATH"] = os.environ["PATH"] + os.pathsep + install_dir

            # Clean up
            if os.path.exists(temp_zip):
                os.remove(temp_zip)
            if os.path.exists(temp_extract):
                shutil.rmtree(temp_extract)

            logger.info("Fastfetch installed successfully.")
            return True
        except Exception as e:
            logger.error(f"Fastfetch installation error: {e}")
            return False

    def docker_config(self) -> bool:
        logger.info("Configuring Docker...")

        # Check if Docker is installed
        docker_installed = Utils.command_exists("docker")

        if not docker_installed:
            logger.info("Docker not installed; attempting to install via Chocolatey...")
            try:
                Utils.run_command(
                    ["choco", "install", "docker-desktop", "-y"], check=False
                )
                # Refresh environment to find docker command
                os.environ["PATH"] = os.environ["PATH"]
                docker_installed = Utils.command_exists("docker")
            except Exception as e:
                logger.error(f"Docker installation failed: {e}")
                return False

        if not docker_installed:
            logger.error(
                "Docker is not installed and could not be installed automatically."
            )
            return False

        logger.info("Docker is installed. Checking if Docker service is running...")

        try:
            # Check if Docker service is running
            docker_status = Utils.run_powershell_command(
                "Get-Service -Name 'com.docker.service' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status",
                capture_output=True,
                check=False,
            )

            if "Running" not in docker_status.stdout:
                logger.warning(
                    "Docker service is not running. Starting Docker service..."
                )
                Utils.run_powershell_command(
                    "Start-Service -Name 'com.docker.service' -ErrorAction SilentlyContinue",
                    check=False,
                )
                time.sleep(10)  # Give Docker some time to start

            # Create docker config directory
            docker_config_dir = os.path.join(USER_HOME, ".docker")
            Utils.ensure_directory(docker_config_dir)

            # Create daemon.json if it doesn't exist
            daemon_json_path = os.path.join(docker_config_dir, "daemon.json")
            daemon_config = {
                "log-driver": "json-file",
                "log-opts": {"max-size": "10m", "max-file": "3"},
                "features": {"buildkit": True},
            }

            if not os.path.exists(daemon_json_path):
                with open(daemon_json_path, "w") as f:
                    json.dump(daemon_config, f, indent=4)
                logger.info("Created Docker daemon configuration file.")

            # Test Docker
            logger.info("Testing Docker installation...")
            docker_test = Utils.run_command(
                ["docker", "info"], capture_output=True, check=False
            )

            if docker_test.returncode == 0:
                logger.info("Docker is running correctly.")
                return True
            else:
                logger.warning("Docker service may not be running correctly.")
                return False
        except Exception as e:
            logger.error(f"Docker configuration error: {e}")
            return False

    def install_enable_tailscale(self) -> bool:
        logger.info("Installing and configuring Tailscale...")

        # Check if Tailscale is installed
        tailscale_installed = Utils.command_exists("tailscale")

        if not tailscale_installed:
            logger.info(
                "Tailscale not installed; attempting to install via Chocolatey..."
            )
            try:
                Utils.run_command(["choco", "install", "tailscale", "-y"], check=False)
                # Refresh environment to find tailscale command
                os.environ["PATH"] = os.environ["PATH"]
                tailscale_installed = Utils.command_exists("tailscale")
            except Exception as e:
                logger.error(f"Tailscale installation failed: {e}")
                return False

        if not tailscale_installed:
            logger.error(
                "Tailscale is not installed and could not be installed automatically."
            )
            return False

        logger.info(
            "Tailscale is installed. Checking if Tailscale service is running..."
        )

        try:
            # Check if Tailscale service is running
            tailscale_status = Utils.run_powershell_command(
                "Get-Service -Name 'Tailscale*' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status",
                capture_output=True,
                check=False,
            )

            if "Running" not in tailscale_status.stdout:
                logger.warning(
                    "Tailscale service is not running. Starting Tailscale service..."
                )
                Utils.run_powershell_command(
                    "Get-Service -Name 'Tailscale*' -ErrorAction SilentlyContinue | Start-Service",
                    check=False,
                )

            # Check Tailscale status
            try:
                tailscale_info = Utils.run_command(
                    ["tailscale", "status"], capture_output=True, check=False
                )

                logger.info("Tailscale is running. To authenticate, run: tailscale up")
                return True
            except Exception:
                logger.warning("Could not verify Tailscale status.")
                return tailscale_installed
        except Exception as e:
            logger.error(f"Tailscale service error: {e}")
            return tailscale_installed

    def deploy_user_scripts(self) -> bool:
        logger.info("Deploying user scripts...")

        # Create scripts directory
        scripts_dir = os.path.join(USER_HOME, "Scripts")
        Utils.ensure_directory(scripts_dir)

        # Create a sample script
        sample_script = os.path.join(scripts_dir, "update-system.ps1")

        script_content = """
# Windows System Update Script
# Created by Windows Server Initialization Utility

param (
    [switch]$ForceReboot = $false
)

function Test-Administrator {
    $user = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal $user
    $principal.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
}

if (-not (Test-Administrator)) {
    Write-Error "This script must be run as an administrator."
    exit 1
}

# Update Windows
Write-Host "Checking for Windows updates..." -ForegroundColor Cyan
if (Get-Module -ListAvailable -Name PSWindowsUpdate) {
    Import-Module PSWindowsUpdate
    $updates = Get-WindowsUpdate
    if ($updates.Count -gt 0) {
        Write-Host "Installing $($updates.Count) Windows updates..." -ForegroundColor Yellow
        Install-WindowsUpdate -AcceptAll -AutoReboot:$ForceReboot
    } else {
        Write-Host "No Windows updates available." -ForegroundColor Green
    }
} else {
    Write-Warning "PSWindowsUpdate module not found. Please install it with: Install-Module PSWindowsUpdate -Force"
}

# Update Chocolatey packages
if (Get-Command choco -ErrorAction SilentlyContinue) {
    Write-Host "Updating Chocolatey packages..." -ForegroundColor Cyan
    choco upgrade all -y
} else {
    Write-Warning "Chocolatey not found. Please install it first."
}

# Cleanup
Write-Host "Cleaning up temporary files..." -ForegroundColor Cyan
Remove-Item -Path $env:TEMP\* -Force -Recurse -ErrorAction SilentlyContinue
cleanmgr /sagerun:1

Write-Host "System update complete!" -ForegroundColor Green
"""

        try:
            with open(sample_script, "w") as f:
                f.write(script_content)

            # Create a batch file to run the script as admin
            batch_file = os.path.join(scripts_dir, "update-system.bat")
            batch_content = """@echo off
powershell -ExecutionPolicy Bypass -Command "Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass -File \"%~dp0update-system.ps1\"' -Verb RunAs"
"""

            with open(batch_file, "w") as f:
                f.write(batch_content)

            logger.info("User scripts deployed successfully.")
            return True
        except Exception as e:
            logger.error(f"User scripts deployment error: {e}")
            return False


#####################################
# Phase 6: Maintenance Tasks
#####################################


class MaintenanceManager:
    def configure_scheduled_tasks(self) -> bool:
        logger.info("Setting up scheduled maintenance tasks...")

        try:
            # Create a scheduled task for system updates
            script_path = os.path.join(USER_HOME, "Scripts", "update-system.ps1")

            # Make sure the script exists
            if not os.path.exists(script_path):
                logger.warning(
                    f"Script not found at {script_path}. Creating scripts directory..."
                )
                ServiceInstaller().deploy_user_scripts()

            # Check if the task already exists
            task_check = Utils.run_powershell_command(
                "Get-ScheduledTask -TaskName 'SystemMaintenance' -ErrorAction SilentlyContinue",
                capture_output=True,
                check=False,
            )

            if task_check.stdout.strip():
                logger.info("Maintenance task already exists.")
            else:
                # Create the task
                Utils.run_powershell_command(
                    f"""
                    $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-ExecutionPolicy Bypass -File "{script_path}"'
                    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 3am
                    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable -WakeToRun
                    $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
                    Register-ScheduledTask -TaskName 'SystemMaintenance' -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'Weekly system maintenance'
                    """
                )
                logger.info("Scheduled maintenance task created successfully.")

            # Create disk cleanup task
            disk_cleanup_check = Utils.run_powershell_command(
                "Get-ScheduledTask -TaskName 'DiskCleanup' -ErrorAction SilentlyContinue",
                capture_output=True,
                check=False,
            )

            if disk_cleanup_check.stdout.strip():
                logger.info("Disk cleanup task already exists.")
            else:
                # First, set up disk cleanup settings
                Utils.run_powershell_command(
                    """
                    # Set up disk cleanup settings
                    $cleanMgrKey = 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\VolumeCaches'
                    $cleanMgrItems = @(
                        'Active Setup Temp Folders', 'BranchCache', 'Downloaded Program Files', 'Internet Cache Files',
                        'Old ChkDsk Files', 'Previous Installations', 'Recycle Bin', 'Setup Log Files',
                        'System error memory dump files', 'System error minidump files', 'Temporary Files',
                        'Temporary Setup Files', 'Thumbnail Cache', 'Update Cleanup', 'Upgrade Discarded Files',
                        'User file versions', 'Windows Defender', 'Windows Error Reporting Archive Files',
                        'Windows Error Reporting Queue Files', 'Windows Error Reporting System Archive Files',
                        'Windows Error Reporting System Queue Files', 'Windows ESD installation files',
                        'Windows Upgrade Log Files'
                    )
                    
                    foreach ($item in $cleanMgrItems) {
                        $itemKey = Join-Path $cleanMgrKey $item
                        if (Test-Path $itemKey) {
                            Set-ItemProperty -Path $itemKey -Name 'StateFlags0001' -Value 2 -Type DWord -Force
                        }
                    }
                    """
                )

                # Create the task
                Utils.run_powershell_command(
                    """
                    $action = New-ScheduledTaskAction -Execute 'cleanmgr.exe' -Argument '/sagerun:1'
                    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Saturday -At 2am
                    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfIdle -IdleSettings (New-ScheduledTaskIdleSettings -IdleDuration 00:10:00 -WaitTimeout 01:00:00)
                    $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
                    Register-ScheduledTask -TaskName 'DiskCleanup' -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'Weekly disk cleanup'
                    """
                )
                logger.info("Scheduled disk cleanup task created successfully.")

            return True
        except Exception as e:
            logger.error(f"Failed to configure scheduled tasks: {e}")
            return False

    def backup_configs(self) -> bool:
        logger.info("Backing up critical configuration files...")
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        backup_dir = os.path.join(BACKUP_DIR, f"windows_config_{timestamp}")
        os.makedirs(backup_dir, exist_ok=True)
        success = True

        # Back up the registry
        registry_backup = os.path.join(backup_dir, "registry_backup.reg")
        try:
            Utils.run_powershell_command(
                f"reg export HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies '{registry_backup}'",
                check=False,
            )
            logger.info("Registry policies backed up.")
        except Exception as e:
            logger.warning(f"Failed to export registry: {e}")
            success = False

        # Backup files in CONFIG_FILES list
        for file in CONFIG_FILES:
            if os.path.isfile(file):
                try:
                    dest = os.path.join(backup_dir, os.path.basename(file))
                    shutil.copy2(file, dest)
                    logger.info(f"Backed up {file}")
                except Exception as e:
                    logger.warning(f"Failed to backup {file}: {e}")
                    success = False

        # Backup firewall rules
        firewall_backup = os.path.join(backup_dir, "firewall_rules.wfw")
        try:
            Utils.run_powershell_command(
                f"Export-NetFirewallRule -PolicyStore ActiveStore -File '{firewall_backup}'",
                check=False,
            )
            logger.info("Firewall rules backed up.")
        except Exception as e:
            logger.warning(f"Failed to export firewall rules: {e}")

        # Create a manifest file
        try:
            manifest = os.path.join(backup_dir, "MANIFEST.txt")
            with open(manifest, "w") as f:
                f.write("Windows Configuration Backup\n")
                f.write(f"Created: {datetime.datetime.now()}\n")
                f.write(f"Computer Name: {socket.gethostname()}\n\n")
                f.write("Files included:\n")
                for file in os.listdir(backup_dir):
                    f.write(f"- {file}\n")
            logger.info(f"Backup manifest created at {manifest}")
        except Exception as e:
            logger.warning(f"Failed to create backup manifest: {e}")

        return success


#####################################
# Phase 7: System Tuning & Permissions
#####################################


class SystemTuner:
    def tune_system(self) -> bool:
        logger.info("Applying system performance tuning...")

        try:
            # Disable visual effects for performance
            Utils.set_registry_value(
                "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\VisualEffects",
                "VisualFXSetting",
                2,
                winreg.REG_DWORD,
            )

            # Set power plan to high performance
            Utils.run_powershell_command(
                "powercfg -setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c", check=False
            )

            # Optimize disk performance
            Utils.run_powershell_command(
                """
                # Disable SuperFetch/SysMain service for SSDs
                $drives = Get-PhysicalDisk | Where-Object MediaType -eq SSD
                if ($drives.Count -gt 0) {
                    Stop-Service -Name SysMain -Force -ErrorAction SilentlyContinue
                    Set-Service -Name SysMain -StartupType Disabled -ErrorAction SilentlyContinue
                }
                
                # Disable disk indexing for all drives
                $drives = Get-WmiObject -Class Win32_Volume -Filter "DriveType = 3"
                foreach ($drive in $drives) {
                    $indexing = $drive.IndexingEnabled
                    if ($indexing) {
                        $drive.IndexingEnabled = $false
                        $drive.Put() | Out-Null
                    }
                }
                """,
                check=False,
            )

            # Optimize network settings
            Utils.set_registry_value(
                "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters",
                "DefaultTTL",
                64,
                winreg.REG_DWORD,
            )
            Utils.set_registry_value(
                "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters",
                "GlobalMaxTcpWindowSize",
                65535,
                winreg.REG_DWORD,
            )
            Utils.set_registry_value(
                "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters",
                "TcpWindowSize",
                65535,
                winreg.REG_DWORD,
            )

            # Optimize virtual memory
            Utils.run_powershell_command(
                """
                # Set virtual memory to system-managed
                $computerSystem = Get-WmiObject -Class Win32_ComputerSystem
                $computerSystem.AutomaticManagedPagefile = $true
                $computerSystem.Put() | Out-Null
                """,
                check=False,
            )

            # Speed up startup
            Utils.run_powershell_command("bcdedit /timeout 5", check=False)

            # Disable hibernation to free up disk space
            Utils.run_powershell_command("powercfg -h off", check=False)

            logger.info("System performance tuning applied successfully.")
            return True
        except Exception as e:
            logger.error(f"System tuning failed: {e}")
            return False

    def secure_permissions(self) -> bool:
        logger.info("Securing file system permissions...")

        try:
            # Secure Documents folder
            Utils.run_powershell_command(
                f"""
                $acl = Get-Acl -Path "$env:USERPROFILE\\Documents"
                $accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
                    "$env:USERDOMAIN\\$env:USERNAME", 
                    "FullControl", 
                    "ContainerInherit,ObjectInherit", 
                    "None", 
                    "Allow"
                )
                $acl.SetAccessRule($accessRule)
                $acl | Set-Acl -Path "$env:USERPROFILE\\Documents"
                """,
                check=False,
            )

            # Secure Scripts folder
            scripts_dir = os.path.join(USER_HOME, "Scripts")
            if os.path.exists(scripts_dir):
                Utils.run_powershell_command(
                    f"""
                    $acl = Get-Acl -Path "{scripts_dir}"
                    $accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
                        "$env:USERDOMAIN\\$env:USERNAME", 
                        "FullControl", 
                        "ContainerInherit,ObjectInherit", 
                        "None", 
                        "Allow"
                    )
                    $acl.SetAccessRule($accessRule)
                    $acl | Set-Acl -Path "{scripts_dir}"
                    """,
                    check=False,
                )

            logger.info("File system permissions secured.")
            return True
        except Exception as e:
            logger.error(f"Failed to secure permissions: {e}")
            return False


#####################################
# Phase 8: Final Checks & Cleanup
#####################################


class FinalChecker:
    def system_health_check(self) -> Dict[str, Any]:
        logger.info("Performing system health check...")
        health_data: Dict[str, Any] = {}

        try:
            # System uptime
            uptime_result = Utils.run_powershell_command(
                "(Get-CimInstance -ClassName Win32_OperatingSystem).LastBootUpTime",
                capture_output=True,
            )
            last_boot = uptime_result.stdout.strip()
            health_data["last_boot"] = last_boot
            logger.info(f"Last boot time: {last_boot}")

            # Disk space
            disk_result = Utils.run_powershell_command(
                "Get-PSDrive -PSProvider FileSystem | Where-Object {$_.Free -ne $null} | Select-Object Name, @{Name='UsedGB';Expression={[math]::Round(($_.Used / 1GB), 2)}}, @{Name='FreeGB';Expression={[math]::Round(($_.Free / 1GB), 2)}}, @{Name='TotalGB';Expression={[math]::Round((($_.Used + $_.Free) / 1GB), 2)}}, @{Name='PercentUsed';Expression={[math]::Round(($_.Used / ($_.Used + $_.Free) * 100), 2)}} | ConvertTo-Json",
                capture_output=True,
            )
            try:
                disk_info = json.loads(disk_result.stdout)
                health_data["disks"] = (
                    disk_info if isinstance(disk_info, list) else [disk_info]
                )

                for disk in health_data["disks"]:
                    disk_letter = disk.get("Name", "?")
                    percent_used = disk.get("PercentUsed", 0)
                    free_gb = disk.get("FreeGB", 0)
                    logger.info(
                        f"Disk {disk_letter}: {percent_used}% used, {free_gb} GB free"
                    )

                    if percent_used > 90:
                        logger.warning(
                            f"Critical disk usage on {disk_letter}: {percent_used}% used!"
                        )
                    elif percent_used > 75:
                        logger.warning(
                            f"Disk usage warning on {disk_letter}: {percent_used}% used."
                        )
            except Exception as e:
                logger.warning(f"Error parsing disk info: {e}")

            # Memory usage
            memory_result = Utils.run_powershell_command(
                """
                $os = Get-CimInstance -ClassName Win32_OperatingSystem
                [PSCustomObject]@{
                    TotalMemoryGB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
                    FreeMemoryGB = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
                    UsedMemoryGB = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / 1MB, 2)
                    PercentUsed = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / $os.TotalVisibleMemorySize * 100, 2)
                } | ConvertTo-Json
                """,
                capture_output=True,
            )

            try:
                memory_info = json.loads(memory_result.stdout)
                health_data["memory"] = memory_info
                logger.info(
                    f"Memory: {memory_info['PercentUsed']}% used, {memory_info['FreeMemoryGB']} GB free"
                )
            except Exception as e:
                logger.warning(f"Error parsing memory info: {e}")

            # CPU load
            cpu_result = Utils.run_powershell_command(
                "Get-CimInstance -ClassName Win32_Processor | Measure-Object -Property LoadPercentage -Average | Select-Object -ExpandProperty Average",
                capture_output=True,
            )

            try:
                cpu_load = float(cpu_result.stdout.strip())
                health_data["cpu_load"] = cpu_load
                logger.info(f"CPU Load: {cpu_load}%")

                if cpu_load > 90:
                    logger.warning(f"High CPU load: {cpu_load}%")
            except Exception as e:
                logger.warning(f"Error parsing CPU load: {e}")

            # Windows Update status
            update_result = Utils.run_powershell_command(
                "Get-HotFix | Sort-Object -Property InstalledOn -Descending | Select-Object -First 5 | ConvertTo-Json",
                capture_output=True,
                check=False,
            )

            try:
                if update_result.stdout.strip():
                    recent_updates = json.loads(update_result.stdout)
                    health_data["recent_updates"] = (
                        recent_updates
                        if isinstance(recent_updates, list)
                        else [recent_updates]
                    )
                    logger.info(
                        f"Most recent update: {health_data['recent_updates'][0].get('InstalledOn', 'Unknown')}"
                    )
            except Exception as e:
                logger.warning(f"Error parsing update info: {e}")

            return health_data
        except Exception as e:
            logger.error(f"System health check error: {e}")
            return health_data

    def verify_firewall_rules(self) -> bool:
        logger.info("Verifying firewall rules...")
        all_correct = True

        try:
            # Check if Windows Firewall is enabled
            firewall_result = Utils.run_powershell_command(
                "Get-NetFirewallProfile | Select-Object Name, Enabled | ConvertTo-Json",
                capture_output=True,
            )

            try:
                firewall_profiles = json.loads(firewall_result.stdout)
                if not isinstance(firewall_profiles, list):
                    firewall_profiles = [firewall_profiles]

                for profile in firewall_profiles:
                    name = profile.get("Name", "Unknown")
                    enabled = profile.get("Enabled", False)
                    logger.info(
                        f"Firewall profile {name}: {'Enabled' if enabled else 'Disabled'}"
                    )

                    if not enabled:
                        logger.warning(f"Firewall profile {name} is disabled!")
                        all_correct = False
            except Exception as e:
                logger.warning(f"Error parsing firewall profile info: {e}")
                all_correct = False

            # Check allowed ports
            for port in ALLOWED_PORTS:
                tcp_rule_name = f"Allow-TCP-{port}"
                rule_check = Utils.run_powershell_command(
                    f"Get-NetFirewallRule -DisplayName '{tcp_rule_name}' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Enabled",
                    capture_output=True,
                    check=False,
                )

                if "True" in rule_check.stdout:
                    logger.info(f"Firewall rule for port {port} is enabled.")
                else:
                    logger.warning(
                        f"Firewall rule for port {port} is missing or disabled!"
                    )
                    all_correct = False

            return all_correct
        except Exception as e:
            logger.error(f"Firewall verification error: {e}")
            return False

    def final_checks(self) -> bool:
        logger.info("Performing final system checks...")
        all_passed = True

        try:
            # Get system information
            system_info = Utils.run_powershell_command(
                """
                [PSCustomObject]@{
                    ComputerName = $env:COMPUTERNAME
                    OSVersion = (Get-CimInstance -ClassName Win32_OperatingSystem).Caption
                    LastBootTime = (Get-CimInstance -ClassName Win32_OperatingSystem).LastBootUpTime
                    Processor = (Get-CimInstance -ClassName Win32_Processor).Name
                    TotalMemoryGB = [math]::Round((Get-CimInstance -ClassName Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 2)
                    IPAddress = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "*Ethernet*", "*Wi-Fi*" | Where-Object { $_.IPAddress -notmatch "^169" -and $_.IPAddress -ne "127.0.0.1" }).IPAddress
                } | ConvertTo-Json
                """,
                capture_output=True,
            )

            try:
                info = json.loads(system_info.stdout)
                logger.info(f"Computer Name: {info.get('ComputerName', 'Unknown')}")
                logger.info(f"OS Version: {info.get('OSVersion', 'Unknown')}")
                logger.info(f"Last Boot Time: {info.get('LastBootTime', 'Unknown')}")
                logger.info(f"Processor: {info.get('Processor', 'Unknown')}")
                logger.info(f"Total Memory: {info.get('TotalMemoryGB', 'Unknown')} GB")
                logger.info(f"IP Address: {info.get('IPAddress', 'Unknown')}")
            except Exception as e:
                logger.warning(f"Error parsing system info: {e}")
                all_passed = False

            # Check Windows Defender status
            defender_status = Utils.run_powershell_command(
                "Get-MpComputerStatus | Select-Object AntivirusEnabled, RealTimeProtectionEnabled, IoavProtectionEnabled, AntispywareEnabled | ConvertTo-Json",
                capture_output=True,
                check=False,
            )

            try:
                if defender_status.stdout.strip():
                    status = json.loads(defender_status.stdout)
                    logger.info(f"Windows Defender: {status}")

                    if not status.get("AntivirusEnabled", False) or not status.get(
                        "RealTimeProtectionEnabled", False
                    ):
                        logger.warning("Windows Defender is not fully enabled!")
                        all_passed = False
            except Exception as e:
                logger.warning(f"Error checking Windows Defender: {e}")

            # Check running services
            services = [
                "LanmanServer",
                "EventLog",
                "Schedule",
                "BITS",
                "Wcmsvc",
                "lmhosts",
                "WinDefend",
                "WSearch",
            ]
            for svc in services:
                svc_status = Utils.run_powershell_command(
                    f"Get-Service -Name {svc} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status",
                    capture_output=True,
                    check=False,
                )

                if "Running" in svc_status.stdout:
                    logger.info(f"Service {svc}: Running")
                else:
                    logger.warning(f"Service {svc}: Not running or not found")
                    if svc in ["LanmanServer", "EventLog", "Schedule"]:
                        all_passed = False

            # Check Windows Update status
            try:
                update_status = Utils.run_powershell_command(
                    "Import-Module PSWindowsUpdate -ErrorAction SilentlyContinue; Get-WindowsUpdate -ErrorAction SilentlyContinue | Measure-Object | Select-Object -ExpandProperty Count",
                    capture_output=True,
                    check=False,
                )

                if (
                    update_status.stdout.strip()
                    and int(update_status.stdout.strip()) > 0
                ):
                    update_count = int(update_status.stdout.strip())
                    logger.warning(f"There are {update_count} pending Windows updates!")
                    all_passed = False
            except Exception:
                logger.debug("Could not check Windows Update status.")

            return all_passed
        except Exception as e:
            logger.error(f"Final checks error: {e}")
            return False

    def cleanup_system(self) -> bool:
        logger.info("Performing system cleanup...")
        success = True

        try:
            # Clean up temporary files
            Utils.run_powershell_command(
                """
                # Clean temp files
                Remove-Item -Path $env:TEMP\* -Force -Recurse -ErrorAction SilentlyContinue
                Remove-Item -Path "C:\\Windows\\Temp\\*" -Force -Recurse -ErrorAction SilentlyContinue
                
                # Clean WinSxS folder (cautiously)
                if ((Get-CimInstance -ClassName Win32_OperatingSystem).Version -ge "10.0") {
                    Dism.exe /Online /Cleanup-Image /StartComponentCleanup /NoRestart
                }
                """,
                check=False,
            )

            # Run disk cleanup silently
            Utils.run_powershell_command(
                """
                # Set up disk cleanup settings if not already configured
                $cleanMgrKey = 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\VolumeCaches'
                if (-not (Test-Path "$cleanMgrKey\\Temporary Files\\StateFlags0001")) {
                    $cleanMgrItems = @(
                        'Active Setup Temp Folders', 'Temporary Files', 'Thumbnail Cache',
                        'Internet Cache Files', 'Old ChkDsk Files', 'Recycle Bin'
                    )
                    
                    foreach ($item in $cleanMgrItems) {
                        $itemKey = Join-Path $cleanMgrKey $item
                        if (Test-Path $itemKey) {
                            Set-ItemProperty -Path $itemKey -Name 'StateFlags0001' -Value 2 -Type DWord -Force
                        }
                    }
                }
                
                # Run disk cleanup
                Start-Process -FilePath "cleanmgr.exe" -ArgumentList "/sagerun:1" -Wait -WindowStyle Hidden
                """,
                check=False,
            )

            # Check for large log files
            Utils.run_powershell_command(
                """
                # Compact large log files
                $largeLogFiles = Get-ChildItem -Path "C:\\Windows\\Logs", "C:\\Windows\\System32\\LogFiles" -Include *.log, *.etl -Recurse -ErrorAction SilentlyContinue |
                    Where-Object { $_.Length -gt 50MB } |
                    Sort-Object -Property Length -Descending
                
                foreach ($logFile in $largeLogFiles) {
                    try {
                        $backupFile = "$($logFile.FullName).bak"
                        Copy-Item -Path $logFile.FullName -Destination $backupFile -Force -ErrorAction SilentlyContinue
                        Clear-Content -Path $logFile.FullName -Force -ErrorAction SilentlyContinue
                        Write-Host "Cleared log file: $($logFile.FullName)" -ForegroundColor Yellow
                    } catch {
                        # Ignore errors for files in use
                    }
                }
                """,
                check=False,
            )

            logger.info("System cleanup completed.")
            return success
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            return False

    def prompt_reboot(self) -> None:
        logger.info("Prompting for reboot...")
        print(
            f"{NORD14}Setup completed! A reboot is recommended to apply all changes.{NC}"
        )
        answer = input("Reboot now? [y/N]: ").strip().lower()
        if answer == "y":
            logger.info("Rebooting system...")
            try:
                Utils.run_powershell_command("Restart-Computer -Force")
            except Exception as e:
                logger.warning(f"Reboot failed: {e}")
                print(
                    f"{NORD11}Reboot failed. Please restart your computer manually.{NC}"
                )
        else:
            logger.info("Reboot canceled. Please reboot later.")


#####################################
# Main Orchestrator
#####################################


class WindowsServerSetup:
    def __init__(self) -> None:
        self.logger = logger
        self.success = True
        self.start_time = time.time()
        self.preflight = PreflightChecker()
        self.updater = SystemUpdater()
        self.user_env = UserEnvironment()
        self.security = SecurityHardener()
        self.services = ServiceInstaller()
        self.maintenance = MaintenanceManager()
        self.tuner = SystemTuner()
        self.final_checker = FinalChecker()

    def run(self) -> int:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{NORD8}{'-' * 40}{NC}")
        print(f"{NORD8}  Starting Windows Server Setup v1.0.0{NC}")
        print(f"{NORD8}  {now}{NC}")
        print(f"{NORD8}{'-' * 40}{NC}")
        logger.info(
            f"Starting Windows Server Setup v1.0.0 at {datetime.datetime.now()}"
        )

        # Phase 1: Pre-flight Checks
        print_section("Phase 1: Pre-flight Checks")
        try:
            run_with_progress(
                "Running Pre-flight Checks...",
                self.preflight.check_admin,
                task_name="preflight",
            )
            if not self.preflight.check_network():
                logger.error("Network check failed. Aborting.")
                SETUP_STATUS["preflight"] = {
                    "status": "failed",
                    "message": "Network check failed",
                }
                sys.exit(1)
            if not self.preflight.check_os_version():
                logger.warning("OS version check failed; proceeding with caution.")
            self.preflight.save_config_snapshot()
        except Exception as e:
            logger.error(f"Preflight phase error: {e}")
            self.success = False

        # Phase 2: System Update & Basic Configuration
        print_section("Phase 2: System Update & Basic Configuration")
        try:
            if not run_with_progress(
                "Installing Chocolatey...",
                self.updater.install_chocolatey,
                task_name="choco_install",
            ):
                logger.error("Chocolatey installation failed. Proceeding with caution.")
                self.success = False
        except Exception as e:
            logger.error(f"Chocolatey installation error: {e}")
            self.success = False

        try:
            if not run_with_progress(
                "Updating system...",
                self.updater.update_system,
                task_name="system_update",
            ):
                logger.warning("System update failed; continuing.")
                self.success = False
        except Exception as e:
            logger.error(f"System update error: {e}")
            self.success = False

        try:
            if not run_with_progress(
                "Installing packages...",
                self.updater.install_packages,
                task_name="packages_install",
            ):
                logger.warning("Package installation encountered issues.")
                self.success = False
        except Exception as e:
            logger.error(f"Package installation error: {e}")
            self.success = False

        try:
            if not run_with_progress(
                "Configuring timezone...", self.updater.configure_timezone
            ):
                logger.warning("Timezone configuration failed.")
                self.success = False
        except Exception as e:
            logger.error(f"Timezone configuration error: {e}")
            self.success = False

        try:
            if not run_with_progress(
                "Configuring locale...", self.updater.configure_locale
            ):
                logger.warning("Locale configuration failed.")
                self.success = False
        except Exception as e:
            logger.error(f"Locale configuration error: {e}")
            self.success = False

        # Phase 3: User Environment Setup
        print_section("Phase 3: User Environment Setup")
        try:
            if not run_with_progress(
                "Setting up user repositories...",
                self.user_env.setup_repos,
                task_name="user_env",
            ):
                logger.warning("Repository setup failed.")
                self.success = False
        except Exception as e:
            logger.error(f"Repository setup error: {e}")
            self.success = False

        try:
            if not run_with_progress(
                "Setting up PowerShell profile...",
                self.user_env.setup_powershell_profile,
            ):
                logger.warning("PowerShell profile setup failed.")
                self.success = False
        except Exception as e:
            logger.error(f"PowerShell profile error: {e}")
            self.success = False

        try:
            if not run_with_progress(
                "Configuring Windows Terminal...",
                self.user_env.configure_windows_terminal,
            ):
                logger.warning("Windows Terminal configuration failed.")
                self.success = False
        except Exception as e:
            logger.error(f"Windows Terminal configuration error: {e}")
            self.success = False

        # Phase 4: Security & Access Hardening
        print_section("Phase 4: Security & Access Hardening")
        try:
            if not run_with_progress(
                "Configuring Windows Firewall...",
                self.security.configure_windows_firewall,
                task_name="security",
            ):
                logger.warning("Windows Firewall configuration failed.")
                self.success = False
        except Exception as e:
            logger.error(f"Windows Firewall configuration error: {e}")
            self.success = False

        try:
            if not run_with_progress(
                "Configuring Windows Defender...",
                self.security.configure_windows_defender,
            ):
                logger.warning("Windows Defender configuration failed.")
                self.success = False
        except Exception as e:
            logger.error(f"Windows Defender error: {e}")
            self.success = False

        try:
            if not run_with_progress(
                "Hardening User Account Control...",
                self.security.harden_user_account_control,
            ):
                logger.warning("UAC configuration failed.")
                self.success = False
        except Exception as e:
            logger.error(f"UAC error: {e}")
            self.success = False

        try:
            if not run_with_progress(
                "Checking Secure Boot...", self.security.configure_secure_boot
            ):
                logger.warning("Secure Boot check failed.")
                self.success = False
        except Exception as e:
            logger.error(f"Secure Boot error: {e}")
            self.success = False

        try:
            if not run_with_progress(
                "Checking BitLocker...", self.security.configure_bitlocker
            ):
                logger.warning("BitLocker check failed.")
                self.success = False
        except Exception as e:
            logger.error(f"BitLocker error: {e}")
            self.success = False

        # Phase 5: Service Installations
        print_section("Phase 5: Service Installations")
        try:
            if not run_with_progress(
                "Installing Fastfetch...",
                self.services.install_fastfetch,
                task_name="services",
            ):
                logger.warning("Fastfetch installation failed.")
                self.success = False
        except Exception as e:
            logger.error(f"Fastfetch error: {e}")
            self.success = False

        try:
            if not run_with_progress(
                "Configuring Docker...", self.services.docker_config
            ):
                logger.warning("Docker configuration failed.")
                self.success = False
        except Exception as e:
            logger.error(f"Docker error: {e}")
            self.success = False

        try:
            if not run_with_progress(
                "Installing Tailscale...", self.services.install_enable_tailscale
            ):
                logger.warning("Tailscale installation failed.")
                self.success = False
        except Exception as e:
            logger.error(f"Tailscale error: {e}")
            self.success = False

        try:
            if not run_with_progress(
                "Deploying user scripts...", self.services.deploy_user_scripts
            ):
                logger.warning("User scripts deployment failed.")
                self.success = False
        except Exception as e:
            logger.error(f"User scripts error: {e}")
            self.success = False

        # Phase 6: Maintenance Tasks
        print_section("Phase 6: Maintenance Tasks")
        try:
            if not run_with_progress(
                "Configuring scheduled tasks...",
                self.maintenance.configure_scheduled_tasks,
                task_name="maintenance",
            ):
                logger.warning("Scheduled tasks configuration failed.")
                self.success = False
        except Exception as e:
            logger.error(f"Scheduled tasks error: {e}")
            self.success = False

        try:
            if not run_with_progress(
                "Backing up configurations...", self.maintenance.backup_configs
            ):
                logger.warning("Configuration backup failed.")
                self.success = False
        except Exception as e:
            logger.error(f"Backup configs error: {e}")
            self.success = False
        except Exception as e:
            logger.error(f"Backup configs error: {e}")
            self.success = False

        # Phase 7: System Tuning & Permissions
        print_section("Phase 7: System Tuning & Permissions")
        try:
            if not run_with_progress(
                "Applying system tuning...", self.tuner.tune_system, task_name="tuning"
            ):
                logger.warning("System tuning failed.")
                self.success = False
        except Exception as e:
            logger.error(f"System tuning error: {e}")
            self.success = False

        try:
            if not run_with_progress(
                "Securing permissions...", self.tuner.secure_permissions
            ):
                logger.warning("Permission setup failed.")
                self.success = False
        except Exception as e:
            logger.error(f"Permission error: {e}")
            self.success = False

        # Phase 8: Final Checks & Cleanup
        print_section("Phase 8: Final Checks & Cleanup")
        SETUP_STATUS["final"] = {
            "status": "in_progress",
            "message": "Running final checks...",
        }
        try:
            self.final_checker.system_health_check()
        except Exception as e:
            logger.error(f"System health check error: {e}")
            self.success = False

        try:
            if not self.final_checker.verify_firewall_rules():
                logger.warning("Firewall rule verification failed.")
                self.success = False
        except Exception as e:
            logger.error(f"Firewall verification error: {e}")
            self.success = False

        final_result = True
        try:
            final_result = self.final_checker.final_checks()
        except Exception as e:
            logger.error(f"Final checks error: {e}")
            self.success = False
            final_result = False

        try:
            self.final_checker.cleanup_system()
        except Exception as e:
            logger.error(f"System cleanup error: {e}")
            self.success = False

        duration = time.time() - self.start_time
        minutes, seconds = divmod(duration, 60)
        if self.success and final_result:
            logger.info(
                f"Setup completed successfully in {int(minutes)}m {int(seconds)}s."
            )
            SETUP_STATUS["final"] = {
                "status": "success",
                "message": f"Completed in {int(minutes)}m {int(seconds)}s.",
            }
        else:
            logger.warning(
                f"Setup completed with warnings in {int(minutes)}m {int(seconds)}s."
            )
            SETUP_STATUS["final"] = {
                "status": "warning",
                "message": f"Completed with warnings in {int(minutes)}m {int(seconds)}s.",
            }
        try:
            print_status_report()
        except Exception as e:
            logger.error(f"Error printing status report: {e}")
        try:
            self.final_checker.prompt_reboot()
        except Exception as e:
            logger.error(f"Reboot prompt error: {e}")
        return 0 if self.success and final_result else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Windows Server Initialization and Hardening Utility"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run (simulate actions without making changes)",
    )
    args = parser.parse_args()
    # For this example, dry-run is not implemented separately.
    setup_instance = WindowsServerSetup()
    return setup_instance.run()


if __name__ == "__main__":
    sys.exit(main())
