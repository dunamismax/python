#!/usr/bin/env python3

import atexit
import getpass
import logging
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

VERSION: str = "4.0.0"
APP_NAME: str = "PyDev Setup macOS (Minimal)"

DEFAULT_TIMEOUT: int = 3600
PYTHON_BUILD_TIMEOUT: int = 7200

PLATFORM_SYSTEM: str = platform.system().lower()

ORIGINAL_USER: str = os.environ.get("SUDO_USER", getpass.getuser())
try:
    ORIGINAL_UID: int = int(
        subprocess.check_output(["id", "-u", ORIGINAL_USER]).decode().strip()
    )
    ORIGINAL_GID: int = int(
        subprocess.check_output(["id", "-g", ORIGINAL_USER]).decode().strip()
    )
except Exception:
    ORIGINAL_UID = os.getuid() if ORIGINAL_USER == getpass.getuser() else os.stat(Path("~" + ORIGINAL_USER).expanduser()).st_uid
    ORIGINAL_GID = os.getgid() if ORIGINAL_USER == getpass.getuser() else os.stat(Path("~" + ORIGINAL_USER).expanduser()).st_gid

HOME_DIR: Path = Path("~" + ORIGINAL_USER).expanduser()
PYENV_ROOT: Path = HOME_DIR / ".pyenv"

SYSTEM_DEPENDENCIES: List[str] = ["tcl-tk", "wget"]

PIPX_TOOLS: List[str] = [
    "black", "isort", "flake8", "mypy", "pytest", "pre-commit", "ipython",
    "cookiecutter", "pylint", "sphinx", "httpie", "ruff", "yt-dlp",
    "bandit", "pipenv", "pip-audit", "nox", "awscli", "dvc", "uv",
    "pyupgrade", "watchfiles", "bump2version",
]

SHELL_CONFIG_FILES: Dict[str, str] = {
    "zsh": str(HOME_DIR / ".zshrc"),
    "bash": str(HOME_DIR / ".bash_profile"),
}

LOG_FILE_PATH = Path(__file__).resolve().parent / "pydev_setup_minimal.log"
log = logging.getLogger("pydev_setup")
log.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')

fh = logging.FileHandler(LOG_FILE_PATH)
fh.setFormatter(formatter)
log.addHandler(fh)

sh = logging.StreamHandler(sys.stdout)
sh.setFormatter(formatter)
log.addHandler(sh)

PYENV_BIN_PATH: Optional[str] = None
PIPX_BIN_PATH: Optional[str] = None

def run_command(
    cmd: Union[List[str], str],
    shell: bool = False,
    check: bool = True,
    capture_output: bool = True,
    timeout: int = DEFAULT_TIMEOUT,
    as_user: bool = False,
    env: Optional[Dict[str, str]] = None,
    cwd: Optional[str] = None,
) -> subprocess.CompletedProcess:
    final_cmd: Union[List[str], str]
    if as_user and ORIGINAL_USER != "root":
        user_env = (env or os.environ).copy()
        user_env["HOME"] = str(HOME_DIR)
        user_local_bin = str(HOME_DIR / ".local" / "bin")
        brew_prefix_bin = ""
        try:
            brew_prefix_output = subprocess.check_output(["brew", "--prefix"], text=True, env=user_env).strip()
            brew_prefix_bin = f"{brew_prefix_output}/bin"
        except Exception:
            pass

        current_path = user_env.get("PATH", "")
        paths_to_add = [user_local_bin]
        if brew_prefix_bin:
            paths_to_add.append(brew_prefix_bin)

        for p_add in paths_to_add:
            if p_add not in current_path:
                current_path = f"{p_add}:{current_path}"
        user_env["PATH"] = current_path
        env = user_env

        if isinstance(cmd, list):
            final_cmd = ["sudo", "-E", "-u", ORIGINAL_USER] + cmd
        else:
            final_cmd = f"sudo -E -u {ORIGINAL_USER} {cmd}"
            if not shell:
                 final_cmd = ["sudo", "-E", "-u", ORIGINAL_USER] + cmd.split()
    else:
        final_cmd = cmd
        if env is None:
            env = os.environ.copy()
        if ORIGINAL_USER != "root" and "HOME" not in env:
            env["HOME"] = str(HOME_DIR)

    cmd_str = " ".join(final_cmd) if isinstance(final_cmd, list) else final_cmd
    log.info(f"Running: {cmd_str[:100]}{'...' if len(cmd_str) > 100 else ''}")

    try:
        result = subprocess.run(
            final_cmd,
            shell=shell,
            check=check,
            text=True,
            capture_output=capture_output,
            timeout=timeout,
            env=env,
            cwd=cwd,
        )
        if result.stdout and capture_output and log.level == logging.DEBUG:
            log.debug(f"Cmd stdout: {result.stdout.strip()}")
        if result.stderr and capture_output and log.level == logging.DEBUG:
            log.debug(f"Cmd stderr: {result.stderr.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        log.error(f"Command failed: {cmd_str}")
        log.error(f"Return code: {e.returncode}")
        if e.stdout: log.error(f"Stdout: {e.stdout.strip()}")
        if e.stderr: log.error(f"Stderr: {e.stderr.strip()}")
        raise
    except FileNotFoundError:
        log.error(f"Command not found: {cmd_str.split()[0] if isinstance(cmd_str, str) else cmd_str[0]}")
        raise
    except Exception as e:
        log.error(f"An unexpected error occurred while running command: {cmd_str}")
        log.error(f"Error: {e}")
        raise

def fix_ownership(path: Path, recursive: bool = True) -> None:
    if ORIGINAL_USER == "root" or not path.exists():
        return
    log.info(f"Adjusting ownership of {path} for user {ORIGINAL_USER}...")
    try:
        if recursive and path.is_dir():
            for item in path.rglob("*"):
                os.chown(item, ORIGINAL_UID, ORIGINAL_GID)
        os.chown(path, ORIGINAL_UID, ORIGINAL_GID)
    except Exception as e:
        log.warning(f"Failed to fix ownership of {path}: {e}")

def check_command_available(command: str, as_user: bool = False) -> bool:
    try:
        if as_user and ORIGINAL_USER != "root":
            run_command(["which", command], as_user=True, capture_output=True, check=True)
        else:
            if not shutil.which(command):
                 return False
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def add_to_shell_config(content: str, marker: str, shell_file_path: Path) -> None:
    log.info(f"Updating shell configuration: {shell_file_path}")
    if not shell_file_path.parent.exists():
        shell_file_path.parent.mkdir(parents=True, exist_ok=True)
        fix_ownership(shell_file_path.parent, recursive=False)

    if shell_file_path.name == ".bash_profile" and not shell_file_path.exists():
        log.info(f"Creating {shell_file_path}...")
        default_bash_profile_content = ""
        bashrc_path = HOME_DIR / ".bashrc"
        if bashrc_path.exists():
            default_bash_profile_content = (
                f'if [ -f "{bashrc_path}" ]; then\n'
                f'  . "{bashrc_path}"\n'
                f'fi\n'
            )
        shell_file_path.write_text(default_bash_profile_content)
        fix_ownership(shell_file_path, recursive=False)

    file_content = ""
    if shell_file_path.exists():
        file_content = shell_file_path.read_text()

    if marker not in file_content:
        with shell_file_path.open("a") as f:
            f.write(f"\n# {marker}\n{content}\n")
        log.info(f"Added configuration to {shell_file_path}")
        fix_ownership(shell_file_path, recursive=False)
    else:
        log.info(f"Configuration already exists in {shell_file_path} (marker: {marker})")

def check_prerequisites() -> bool:
    log.info("Checking prerequisites (Homebrew, Xcode Command Line Tools)...")
    if not check_command_available("brew", as_user=True):
        log.error("Homebrew is not installed or not in PATH for the user. Please install Homebrew first: https://brew.sh/")
        return False
    log.info("Homebrew found.")
    try:
        run_command(["xcode-select", "-p"], capture_output=True, check=True)
        log.info("Xcode Command Line Tools found.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        log.error("Xcode Command Line Tools are not installed. Please install them by running: xcode-select --install")
        return False
    return True

def display_system_info() -> None:
    log.info("System Information:")
    log.info(f"  Script Version: {VERSION}")
    log.info(f"  Python for Script: {platform.python_version()}")
    log.info(f"  Operating System: {platform.platform()}")
    log.info(f"  Running as: {getpass.getuser()}")
    log.info(f"  Target User: {ORIGINAL_USER}")
    log.info(f"  User Home Directory: {str(HOME_DIR)}")

def install_system_dependencies() -> bool:
    log.info("Updating Homebrew...")
    try:
        run_command(["brew", "update"], as_user=True)
        log.info("Homebrew updated successfully.")
    except Exception as e:
        log.warning(f"Failed to update Homebrew: {e}. Proceeding...")

    if not SYSTEM_DEPENDENCIES:
        log.info("No additional system dependencies to install via Homebrew.")
        return True

    log.info(f"Installing system dependencies via Homebrew: {', '.join(SYSTEM_DEPENDENCIES)}")
    installed_count = 0
    for package in SYSTEM_DEPENDENCIES:
        log.info(f"Attempting to install {package}...")
        try:
            run_command(["brew", "install", package], as_user=True, check=True)
            log.info(f"Successfully installed/updated {package}.")
            installed_count +=1
        except Exception as e:
            log.warning(f"Could not install {package} via Homebrew: {e}.")
    if installed_count == len(SYSTEM_DEPENDENCIES):
        log.info("All system dependencies processed successfully.")
    else:
        log.warning("Some system dependencies might not have been installed/updated correctly.")
    return True

def install_pyenv() -> bool:
    global PYENV_BIN_PATH
    log.info("Checking for pyenv...")
    if check_command_available("pyenv", as_user=True):
        log.info("pyenv is already installed.")
        if not PYENV_ROOT.exists():
            PYENV_ROOT.mkdir(parents=True, exist_ok=True)
        fix_ownership(PYENV_ROOT)
    else:
        log.info("pyenv not found. Installing via Homebrew...")
        try:
            run_command(["brew", "install", "pyenv"], as_user=True, check=True)
            log.info("pyenv installed successfully via Homebrew.")
            if not PYENV_ROOT.exists():
                 PYENV_ROOT.mkdir(parents=True, exist_ok=True)
            fix_ownership(PYENV_ROOT)
        except Exception as e:
            log.error(f"Failed to install pyenv via Homebrew: {e}")
            return False

    pyenv_init_script = (
        f'export PYENV_ROOT="{PYENV_ROOT}"\n'
        'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"\n'
        'eval "$(pyenv init -)"\n'
        'eval "$(pyenv virtualenv-init -)"\n'
    )
    marker = "pyenv initialization"
    add_to_shell_config(pyenv_init_script, marker, Path(SHELL_CONFIG_FILES["zsh"]))
    add_to_shell_config(pyenv_init_script, marker, Path(SHELL_CONFIG_FILES["bash"]))
    
    PYENV_BIN_PATH = shutil.which("pyenv", path=f"{os.environ.get('PATH', '')}:{str(PYENV_ROOT / 'bin')}:{str(HOME_DIR / '.local' / 'bin')}")
    if not PYENV_BIN_PATH:
       common_brew_paths = ["/opt/homebrew/bin", "/usr/local/bin"]
       for bp in common_brew_paths:
           if (Path(bp) / "pyenv").exists():
               PYENV_BIN_PATH = str(Path(bp) / "pyenv")
               break
    if not PYENV_BIN_PATH:
        log.warning("pyenv command path could not be determined. Using default.")
        PYENV_BIN_PATH = str(PYENV_ROOT / "bin" / "pyenv")
    return True

def install_latest_python_with_pyenv() -> bool:
    if not PYENV_BIN_PATH or not Path(PYENV_BIN_PATH).exists():
        log.error("pyenv command not found. Cannot install Python.")
        return False

    log.info("Finding latest available Python version with pyenv...")
    try:
        versions_output = run_command([PYENV_BIN_PATH, "install", "--list"], as_user=True).stdout
        stable_versions = re.findall(r"^\s*(\d+\.\d+\.\d+)$", versions_output, re.MULTILINE)
        if not stable_versions:
            log.error("Could not find any stable Python versions to install via pyenv.")
            return False
        latest_version = sorted(stable_versions, key=lambda v: [int(p) for p in v.split(".")])[-1]
        log.info(f"Latest stable Python version found: {latest_version}")
    except Exception as e:
        log.error(f"Error finding Python versions with pyenv: {e}")
        return False

    log.info(f"Installing Python {latest_version} using pyenv. This may take a long time.")
    install_cmd = [PYENV_BIN_PATH, "install", "--skip-existing", latest_version]
    try:
        run_command(install_cmd, as_user=True, timeout=PYTHON_BUILD_TIMEOUT, capture_output=True)
        log.info(f"Python {latest_version} installed successfully.")
    except Exception as e:
        log.error(f"Error installing Python {latest_version} with pyenv: {e}")
        return False

    log.info(f"Setting Python {latest_version} as global default for user {ORIGINAL_USER}...")
    try:
        run_command([PYENV_BIN_PATH, "global", latest_version], as_user=True)
        pyenv_python_exe = str(PYENV_ROOT / "shims" / "python")
        version_info = run_command([pyenv_python_exe, "--version"], as_user=True).stdout.strip()
        log.info(f"Successfully set {version_info} as pyenv global default.")
        return True
    except Exception as e:
        log.error(f"Error setting Python {latest_version} as global: {e}")
        return False

def install_pipx() -> bool:
    global PIPX_BIN_PATH
    log.info("Checking for pipx...")
    if check_command_available("pipx", as_user=True):
        log.info("pipx is already installed.")
    else:
        log.info("pipx not found. Installing via Homebrew...")
        try:
            run_command(["brew", "install", "pipx"], as_user=True, check=True)
            log.info("pipx installed successfully via Homebrew.")
        except Exception as e:
            log.error(f"Failed to install pipx via Homebrew: {e}")
            return False

    log.info(f"Ensuring pipx paths are configured for user {ORIGINAL_USER}...")
    try:
        run_command(["pipx", "ensurepath"], as_user=True, check=True)
        log.info("pipx paths configured.")
    except Exception as e:
        log.warning(f"pipx ensurepath command encountered an issue: {e}. This might be okay.")

    PIPX_BIN_PATH = shutil.which("pipx")
    if not PIPX_BIN_PATH:
        user_local_bin_pipx = HOME_DIR / ".local" / "bin" / "pipx"
        if user_local_bin_pipx.exists():
            PIPX_BIN_PATH = str(user_local_bin_pipx)
        else:
            common_brew_paths = ["/opt/homebrew/bin", "/usr/local/bin"]
            for bp in common_brew_paths:
                if (Path(bp) / "pipx").exists():
                    PIPX_BIN_PATH = str(Path(bp) / "pipx")
                    break
    if not PIPX_BIN_PATH:
        log.error("pipx command path could not be determined. Tool installation will fail.")
        return False
    return True

def install_pipx_tools() -> bool:
    if not PIPX_BIN_PATH or not Path(PIPX_BIN_PATH).exists():
        log.error("pipx command not found. Cannot install Python tools.")
        return False

    log.info(f"Installing {len(PIPX_TOOLS)} Python development tools using pipx for user {ORIGINAL_USER}.")
    installed_tools, failed_tools = [], []
    for tool in PIPX_TOOLS:
        log.info(f"Installing {tool} with pipx...")
        try:
            run_command([PIPX_BIN_PATH, "install", tool, "--force"], as_user=True, check=True)
            installed_tools.append(tool)
            log.info(f"Successfully installed {tool}.")
        except Exception as e:
            log.warning(f"Failed to install {tool} using pipx: {e}")
            failed_tools.append(tool)

    log.info("--- Pipx Tool Installation Summary ---")
    if installed_tools:
        log.info(f"Successfully installed/updated {len(installed_tools)} tools: {', '.join(installed_tools)}")
    if failed_tools:
        log.error(f"Failed to install {len(failed_tools)} tools: {', '.join(failed_tools)}")
    log.info("--------------------------------------")
    return len(failed_tools) == 0

def run_setup_components() -> List[str]:
    components = [
        ("System Dependencies (Homebrew)", install_system_dependencies),
        ("pyenv (Python Version Manager)", install_pyenv),
        ("Latest Stable Python (via pyenv)", install_latest_python_with_pyenv),
        ("pipx (CLI Tool Manager)", install_pipx),
        ("Python Development Tools (via pipx)", install_pipx_tools),
    ]
    successes = []
    for name, func in components:
        log.info(f"--- Starting: {name} ---")
        try:
            if func():
                log.info(f"--- Completed: {name} ---")
                successes.append(name)
            else:
                log.error(f"--- Failed: {name} ---")
        except Exception as e:
            log.error(f"--- Critical error during {name}: {e} ---")
        log.info("-" * 40)
    return successes

def display_summary(successes: List[str]) -> None:
    all_components = [
        "System Dependencies (Homebrew)", "pyenv (Python Version Manager)",
        "Latest Stable Python (via pyenv)", "pipx (CLI Tool Manager)",
        "Python Development Tools (via pipx)",
    ]
    log.info("\n--- Overall Setup Summary ---")
    has_failures = False
    for comp_name in all_components:
        status = "Success" if comp_name in successes else "Failed/Partial"
        if status != "Success":
            has_failures = True
        log.info(f"  {comp_name}: {status}")
    log.info("-----------------------------")

    user_shell = Path(os.environ.get("SHELL", "/bin/bash")).name
    shell_rc_name = ".zshrc" if "zsh" in user_shell else ".bash_profile"

    log.info(f"\nNext Steps for User '{ORIGINAL_USER}':")
    log.info("1. Restart your terminal session to apply all shell configuration changes.")
    log.info(f"   Alternatively, run: source ~/{shell_rc_name}")
    log.info("2. Verify installations, e.g., run 'pyenv versions' or 'black --version'.")

    if has_failures:
         log.warning(f"Some setup steps encountered issues. Review logs above and in {LOG_FILE_PATH}")
    else:
        log.info(f"Python development environment setup completed successfully for user {ORIGINAL_USER}!")
    log.info(f"A detailed log is available at: {LOG_FILE_PATH}")

def cleanup() -> None:
    log.info("Cleanup finished. Exiting.")

def signal_handler(sig: int, frame: Any) -> None:
    sig_name = signal.Signals(sig).name
    log.warning(f"\nProcess interrupted by {sig_name} (signal {sig}).")
    sys.exit(128 + sig) # cleanup will be called by atexit

def main() -> None:
    if PLATFORM_SYSTEM != "darwin":
        print(f"Error: This script is designed for macOS, not {platform.system()}.")
        sys.exit(1)
        
    print(f"\n{APP_NAME} v{VERSION}")
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hostname = platform.node()
    print(f"Current Time: {current_time} | Host: {hostname}")
    print("-" * 40)

    if os.geteuid() != 0:
        log.error("This script must be run with root privileges (e.g., using 'sudo python3 script.py').")
        sys.exit(1)
    log.info(f"Script running as root. Operations for user '{ORIGINAL_USER}' will use 'sudo -u {ORIGINAL_USER}'.")

    display_system_info()
    print("-" * 40)

    if not check_prerequisites():
        log.error("Prerequisite checks failed. Aborting setup.")
        sys.exit(1)
    log.info("All prerequisites met.")
    print("-" * 40)

    log.info(f"Welcome to the Automated Python Development Environment Setup for macOS!")
    log.info(f"This script will configure the environment for user: {ORIGINAL_USER}")
    log.info(f"Make sure user {ORIGINAL_USER} has a password set if required for 'sudo -u' operations.")
    print("-" * 40)

    successes = run_setup_components()
    display_summary(successes)

if __name__ == "__main__":
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    try:
        main()
    except Exception as e:
        log.exception("An unhandled exception occurred in the main execution flow.")
        print(f"\nA critical error occurred. Check the log file at {LOG_FILE_PATH} for details.")
        sys.exit(1)