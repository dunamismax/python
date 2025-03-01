#!/usr/bin/env python3
"""
Windows Python Development Environment Setup Tool
------------------------------------------------

A fully automated utility for setting up a Python development
environment on Windows 10/11 systems. This tool:
  • Installs Python tools and utilities
  • Sets up virtual environment capabilities
  • Configures development utilities like black, flake8, etc.

This script runs fully unattended without requiring CLI arguments.
All setup is performed automatically using only standard library.

Version: 1.0.0
"""

import os
import sys
import time
import subprocess
import platform
import ctypes
import shutil
import urllib.request
import zipfile
import winreg
import tempfile
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
log_file = os.path.join(os.path.expanduser("~"), "python_setup.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(log_file, encoding="utf-8")],
)
logger = logging.getLogger(__name__)

# Constants
APP_NAME = "Windows Python Dev Setup"
VERSION = "1.0.0"
HOME_DIR = os.path.expanduser("~")
SCRIPTS_DIR = os.path.join(
    HOME_DIR, "AppData", "Local", "Programs", "Python", "Python*", "Scripts"
)

# Python tools to install with pip
PIP_TOOLS = [
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
    "twine",
    "autopep8",
    "bandit",
    "poetry",
    "pydocstyle",
    "yapf",
    "httpie",
    "pipx",
]


def is_admin():
    """Check if script is run with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False


def print_header(text):
    """Print a formatted header."""
    border = "=" * (len(text) + 4)
    logger.info(f"\n{border}")
    logger.info(f"  {text}  ")
    logger.info(f"{border}\n")


def print_step(text):
    """Print a step description."""
    logger.info(f"STEP: {text}")


def print_success(message):
    """Print a success message."""
    logger.info(f"SUCCESS: {message}")


def print_warning(message):
    """Print a warning message."""
    logger.warning(f"WARNING: {message}")


def print_error(message):
    """Print an error message."""
    logger.error(f"ERROR: {message}")


def run_command(cmd, shell=False, check=True, capture_output=True):
    """Run a shell command and handle errors."""
    try:
        logger.debug(f"Executing: {' '.join(cmd) if not shell else cmd}")
        return subprocess.run(
            cmd, shell=shell, check=check, text=True, capture_output=capture_output
        )
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {' '.join(cmd) if not shell else cmd}")
        if hasattr(e, "stdout") and e.stdout:
            logger.debug(f"Stdout: {e.stdout.strip()}")
        if hasattr(e, "stderr") and e.stderr:
            logger.error(f"Error output: {e.stderr.strip()}")
        raise


def check_command_available(command):
    """Check if a command is available in PATH."""
    return shutil.which(command) is not None


def get_python_path():
    """Get the current Python executable path."""
    return sys.executable


def ensure_pip():
    """Ensure pip is installed and up to date."""
    print_step("Ensuring pip is installed and up to date...")
    python_path = get_python_path()

    try:
        # Try to import pip
        import pip

        print_success("pip is already installed")
    except ImportError:
        # If pip is not available, install it
        print_step("pip not found, installing...")
        try:
            # Download get-pip.py
            with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
                get_pip_path = f.name
            urllib.request.urlretrieve(
                "https://bootstrap.pypa.io/get-pip.py", get_pip_path
            )

            # Run get-pip.py
            run_command([python_path, get_pip_path])
            os.unlink(get_pip_path)
            print_success("pip installed successfully")
        except Exception as e:
            print_error(f"Failed to install pip: {e}")
            raise

    # Upgrade pip to latest version
    run_command([python_path, "-m", "pip", "install", "--upgrade", "pip"])
    print_success("pip is up to date")

    return True


def check_system():
    """Check system compatibility and requirements."""
    print_header("Checking System Compatibility")

    # Verify OS
    if platform.system().lower() != "windows":
        print_error(f"This script is designed for Windows, not {platform.system()}")
        return False

    # Verify Windows version
    win_ver = platform.win32_ver()[0]
    if win_ver not in ["10", "11"]:
        print_warning(f"This script is optimized for Windows 10/11, detected {win_ver}")

    # Verify Python version
    py_ver = platform.python_version_tuple()
    if int(py_ver[0]) < 3 or (int(py_ver[0]) == 3 and int(py_ver[1]) < 8):
        print_error(f"Python 3.8+ is required. Detected {platform.python_version()}")
        return False

    logger.info(f"System: {platform.system()} {platform.version()}")
    logger.info(f"Python Version: {platform.python_version()}")
    logger.info(f"Running as admin: {is_admin()}")

    print_success("System compatibility check passed")
    return True


def add_to_path(directory):
    """Add a directory to the user's PATH environment variable."""
    if not os.path.exists(directory):
        logger.warning(f"Directory does not exist, cannot add to PATH: {directory}")
        return False

    try:
        # Get the current PATH
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            "Environment",
            0,
            winreg.KEY_READ | winreg.KEY_WRITE,
        )

        try:
            path, _ = winreg.QueryValueEx(key, "PATH")
        except WindowsError:
            path = ""

        if directory.lower() not in [p.lower() for p in path.split(";") if p]:
            # Add the directory to PATH
            new_path = f"{path};{directory}" if path else directory
            winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)

            # Notify the system about the environment change
            import ctypes.wintypes

            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A
            SMTO_ABORTIFHUNG = 0x0002
            result = ctypes.windll.user32.SendMessageTimeoutW(
                HWND_BROADCAST,
                WM_SETTINGCHANGE,
                0,
                "Environment",
                SMTO_ABORTIFHUNG,
                5000,
                ctypes.byref(ctypes.wintypes.DWORD()),
            )

            print_success(f"Added {directory} to PATH")
        else:
            logger.info(f"{directory} is already in PATH")

        return True
    except Exception as e:
        print_error(f"Failed to add directory to PATH: {e}")
        return False
    finally:
        try:
            winreg.CloseKey(key)
        except:
            pass


def install_python_tools():
    """Install core Python development tools."""
    print_header("Installing Python Development Tools")

    python_path = get_python_path()
    pip_path = os.path.join(os.path.dirname(python_path), "Scripts", "pip.exe")

    # Check if pip path exists, if not use -m pip
    if not os.path.exists(pip_path):
        pip_cmd = [python_path, "-m", "pip"]
    else:
        pip_cmd = [pip_path]

    # First, ensure pip is updated
    print_step("Upgrading pip...")
    run_command(pip_cmd + ["install", "--upgrade", "pip"])

    # Check for pipx and install it first if not present
    if not check_command_available("pipx"):
        print_step("Installing pipx...")
        run_command(pip_cmd + ["install", "pipx"])

        # Add pipx bin directory to PATH
        pipx_bin = os.path.join(HOME_DIR, ".local", "bin")
        os.makedirs(pipx_bin, exist_ok=True)
        add_to_path(pipx_bin)

        # Run pipx ensurepath
        run_command([os.path.join(os.path.dirname(pip_path), "pipx"), "ensurepath"])

        print_success("pipx installed")

    # Install tools using pipx where possible (for isolation)
    for tool in PIP_TOOLS:
        if tool != "pipx":  # Skip pipx as we've already installed it
            print_step(f"Installing {tool}...")
            try:
                # Use pipx for CLI tools to isolate them
                pipx_path = shutil.which("pipx") or os.path.join(
                    os.path.dirname(pip_path), "pipx.exe"
                )
                if os.path.exists(pipx_path):
                    run_command([pipx_path, "install", tool, "--force"], check=False)
                    print_success(f"{tool} installed via pipx")
                else:
                    # Fall back to pip if pipx not available
                    run_command(pip_cmd + ["install", tool])
                    print_success(f"{tool} installed via pip")
            except Exception as e:
                print_warning(f"Failed to install {tool}: {e}")

    print_success("Python development tools installation completed")
    return True


def setup_virtualenv():
    """Setup Python virtual environment capabilities."""
    print_header("Setting up Virtual Environment Support")

    python_path = get_python_path()

    # Ensure venv is available (it's part of standard library but just to be sure)
    print_step("Setting up virtual environment support...")
    try:
        import venv

        print_success("Python venv module is available")
    except ImportError:
        print_warning("venv module not available, attempting to install...")
        try:
            run_command([python_path, "-m", "pip", "install", "virtualenv"])
            print_success("virtualenv installed as alternative")
        except Exception as e:
            print_error(f"Failed to setup virtual environment support: {e}")
            return False

    # Also install virtualenvwrapper-win for better venv management on Windows
    print_step("Installing virtualenvwrapper-win...")
    try:
        run_command([python_path, "-m", "pip", "install", "virtualenvwrapper-win"])
        print_success("virtualenvwrapper-win installed")
    except Exception as e:
        print_warning(f"Failed to install virtualenvwrapper-win: {e}")

    return True


def create_completion_script():
    """Create script for command completion and editor integration."""
    print_header("Creating Helper Scripts")

    # Create a PowerShell profile directory if it doesn't exist
    ps_profile_dir = os.path.join(HOME_DIR, "Documents", "WindowsPowerShell")
    os.makedirs(ps_profile_dir, exist_ok=True)

    ps_profile_path = os.path.join(ps_profile_dir, "Microsoft.PowerShell_profile.ps1")

    # Check if profile already exists and append to it
    if os.path.exists(ps_profile_path):
        with open(ps_profile_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = ""

    # Only add if not already there
    if "# Python development environment setup" not in content:
        with open(ps_profile_path, "a", encoding="utf-8") as f:
            f.write("""
# Python development environment setup
function New-PythonVenv {
    param(
        [string]$Name = "venv",
        [switch]$Install,
        [string]$Requirements = "requirements.txt"
    )
    
    python -m venv $Name
    & "./$Name/Scripts/Activate.ps1"
    
    if ($Install -and (Test-Path $Requirements)) {
        pip install -r $Requirements
    }
    
    Write-Host "Virtual environment '$Name' created and activated."
}

function Start-PythonProject {
    param(
        [string]$Name,
        [switch]$Git
    )
    
    if (-not $Name) {
        $Name = Split-Path -Leaf (Get-Location)
    }
    
    # Create project directory
    New-Item -ItemType Directory -Force -Path $Name | Out-Null
    Set-Location $Name
    
    # Create virtual environment
    New-PythonVenv
    
    # Create basic project structure
    New-Item -ItemType Directory -Force -Path "src/$Name" | Out-Null
    New-Item -ItemType Directory -Force -Path "tests" | Out-Null
    
    # Create __init__.py files
    "" | Out-File -FilePath "src/$Name/__init__.py"
    "" | Out-File -FilePath "tests/__init__.py"
    
    # Create setup.py
    @"
from setuptools import setup, find_packages

setup(
    name='$Name',
    version='0.1.0',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
)
"@ | Out-File -FilePath "setup.py"
    
    # Create README.md
    @"
# $Name

Project description goes here.

## Installation

```
pip install -e .
```

## Usage

```python
import $Name
```
"@ | Out-File -FilePath "README.md"
    
    # Initialize Git if requested
    if ($Git) {
        git init
        @"
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
venv/
.venv/
env/
ENV/
.env
"@ | Out-File -FilePath ".gitignore"
        git add .
        git commit -m "Initial project structure"
    }
    
    Write-Host "Python project '$Name' initialized successfully."
}

# Tab completion for Python interpreters
Register-ArgumentCompleter -CommandName python, python3, py -Native
""")
        print_success("Added Python helper functions to PowerShell profile")
    else:
        logger.info("PowerShell profile already contains Python helper functions")

    # Create a batch file for CMD users
    cmd_script_path = os.path.join(HOME_DIR, "python_helpers.bat")
    with open(cmd_script_path, "w", encoding="utf-8") as f:
        f.write("""@echo off
:: Python development helpers for Command Prompt
:: Add this to your path or create shortcuts

if "%1"=="venv" (
    if "%2"=="" (
        python -m venv venv
        echo Virtual environment 'venv' created.
        echo To activate, run: venv\\Scripts\\activate
    ) else (
        python -m venv %2
        echo Virtual environment '%2' created.
        echo To activate, run: %2\\Scripts\\activate
    )
    exit /b
)

if "%1"=="project" (
    if "%2"=="" (
        echo Error: Please provide a project name.
        exit /b 1
    )
    
    mkdir %2
    cd %2
    python -m venv venv
    mkdir src\\%2
    mkdir tests
    echo. > src\\%2\\__init__.py
    echo. > tests\\__init__.py
    
    echo from setuptools import setup, find_packages > setup.py
    echo. >> setup.py
    echo setup( >> setup.py
    echo     name='%2', >> setup.py
    echo     version='0.1.0', >> setup.py
    echo     packages=find_packages(where='src'), >> setup.py
    echo     package_dir={'': 'src'}, >> setup.py
    echo ) >> setup.py
    
    echo # %2 > README.md
    echo. >> README.md
    echo Project description goes here. >> README.md
    
    echo Python project '%2' initialized.
    exit /b
)

echo Unknown command: %1
echo Available commands:
echo   python_helpers venv [name] - Create a virtual environment
echo   python_helpers project [name] - Initialize a new Python project
""")
    print_success(f"Created CMD helper script at {cmd_script_path}")

    return True


def configure_git():
    """Configure Git with Python-specific settings."""
    print_header("Configuring Git for Python Development")

    if not check_command_available("git"):
        print_warning("Git is not installed. Skipping Git configuration.")
        return False

    # Create global gitignore for Python
    git_ignore_path = os.path.join(HOME_DIR, ".gitignore_global_python")
    with open(git_ignore_path, "w", encoding="utf-8") as f:
        f.write("""# Python gitignore
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
*.egg-info/
.installed.cfg
*.egg

# Virtualenv
venv/
ENV/
.venv/

# Unit test / coverage reports
htmlcov/
.tox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis/

# Jupyter Notebook
.ipynb_checkpoints

# PyCharm
.idea/

# VS Code
.vscode/

# Spyder
.spyderproject
.spyproject

# Rope
.ropeproject

# mypy
.mypy_cache/
""")

    try:
        # Set up Git to use this global gitignore for Python projects
        run_command(["git", "config", "--global", "core.excludesfile", git_ignore_path])

        # Configure Git for Python line endings
        run_command(["git", "config", "--global", "core.autocrlf", "true"])

        # Add some helpful Git aliases for Python development
        run_command(
            [
                "git",
                "config",
                "--global",
                "alias.cleanup",
                "!git clean -xdf -e venv -e .venv",
            ]
        )

        print_success("Git configured for Python development")
        return True
    except Exception as e:
        print_warning(f"Failed to fully configure Git: {e}")
        return False


def generate_summary():
    """Generate and display a summary of the setup."""
    print_header("Setup Summary")

    python_path = get_python_path()
    python_version = platform.python_version()

    summary = [
        f"Python Version: {python_version}",
        f"Python Path: {python_path}",
        f"Scripts Path: {os.path.join(os.path.dirname(python_path), 'Scripts')}",
        f"Pip Version: {run_command([python_path, '-m', 'pip', '--version']).stdout.strip()}",
        "Installed Tools:",
    ]

    for tool in PIP_TOOLS:
        tool_path = shutil.which(tool)
        if tool_path:
            summary.append(f"  {tool} ({tool_path})")
        else:
            summary.append(f"  {tool} (not found in PATH)")

    # Log the summary
    # Log the summary
    for line in summary:
        logger.info(line.replace("✓", "").replace("✗", ""))

    # Create a report file in the user's home directory
    report_path = os.path.join(HOME_DIR, "python_setup_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(
            f"Python Development Environment Setup - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        f.write("=" * 80 + "\n\n")
        f.write("\n".join(summary))
        f.write("\n\n")
        f.write("Post-Setup Steps:\n")
        f.write(
            "1. Restart your terminal/command prompt for PATH changes to take effect\n"
        )
        f.write("2. Run 'pipx list' to verify installed tools\n")
        f.write(
            "3. Helper functions are available in PowerShell or cmd via the python_helpers.bat script\n"
        )

    print_success(f"Setup completed! Report saved to {report_path}")
    return True


def main():
    """Main entry point for the script."""
    try:
        # Print welcome banner
        print_header(f"{APP_NAME} v{VERSION}")
        logger.info(f"Starting setup at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Check if run as admin
        if not is_admin():
            print_warning("This script is not running with administrator privileges.")
            print_warning("Some operations may fail without admin rights.")
            time.sleep(2)

        # Check system compatibility
        if not check_system():
            print_error("System check failed. Setup cannot continue.")
            return 1

        # Ensure pip is installed
        if not ensure_pip():
            print_error("Pip installation failed. Setup cannot continue.")
            return 1

        # Install Python development tools
        if not install_python_tools():
            print_warning("Some Python tools may not have been installed.")

        # Setup virtual environment support
        if not setup_virtualenv():
            print_warning("Virtual environment setup may not be complete.")

        # Create helper scripts
        if not create_completion_script():
            print_warning("Helper scripts may not have been created properly.")

        # Configure Git (optional, doesn't fail if Git isn't installed)
        configure_git()

        # Generate and display summary
        generate_summary()

        return 0

    except KeyboardInterrupt:
        print_warning("\nProcess interrupted by user.")
        return 130
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        logger.exception("Unhandled exception")
        return 1


if __name__ == "__main__":
    sys.exit(main())
