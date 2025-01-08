#!/usr/bin/env python3
"""
file_commander.py (Typer + curses + Rich)

A cross-platform TUI/CLI-driven file operations utility.

By default, running `python file_commander.py` with no arguments
will launch the curses-based TUI.

Explicitly launch the TUI via the `tui` command:
    python file_commander.py tui

Otherwise, you may invoke any of the subcommands (list, create, move, copy, etc.)
with normal CLI arguments.
"""

import os
import sys
import shutil
import stat
import hashlib
import re
import zipfile
import tarfile
import ftplib
import curses
import paramiko
from send2trash import send2trash
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Typer and Rich
import typer
from rich import print as rprint
from rich.console import Console

app = typer.Typer(help="File Commander: CLI + TUI file manager.")

##############################################################################
# 1. Helper Functions
##############################################################################


def _richify(text: str) -> str:
    """
    Convert bracket-based tags ([OK], [ERROR], [INFO]) to Rich color styling.
    """
    replacements = [
        ("[OK]", "[bold green][OK][/bold green]"),
        ("[ERROR]", "[bold red][ERROR][/bold red]"),
        ("[INFO]", "[bold cyan][INFO][/bold cyan]"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def list_items(path: str, detailed: bool = False, tree: bool = False) -> str:
    """
    List files/directories under `path`.
    """
    from io import StringIO

    p = Path(path).resolve()
    if not p.exists():
        return f"[ERROR] Path '{p}' does not exist."

    buf = StringIO()
    if tree:
        buf.write(f"Directory Tree for {p}:\n")
        for root, dirs, files in os.walk(p):
            level = root.replace(str(p), "").count(os.sep)
            indent = " " * (4 * level)
            buf.write(f"{indent}{os.path.basename(root)}/\n")
            subindent = " " * (4 * (level + 1))
            for f in files:
                buf.write(f"{subindent}{f}\n")
    else:
        buf.write(f"Listing contents of {p}:\n")
        for entry in p.iterdir():
            if detailed:
                size = entry.stat().st_size
                mtime = datetime.fromtimestamp(entry.stat().st_mtime)
                ftype = "DIR " if entry.is_dir() else "FILE"
                buf.write(
                    f"{entry.name:<30} {ftype:<5} {size:>10} bytes  "
                    f"{mtime.strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
            else:
                buf.write(f"{entry.name}\n")
    return buf.getvalue()


def create_item(item_type: str, path: str) -> str:
    """
    Create a new file or directory at the given path.
    """
    p = Path(path).resolve()
    if p.exists():
        return f"[ERROR] '{p}' already exists."

    try:
        if item_type == "file":
            p.touch()
            return f"[OK] Created file: {p}"
        elif item_type == "folder":
            p.mkdir(parents=True, exist_ok=True)
            return f"[OK] Created folder: {p}"
        else:
            return "[ERROR] Unknown item_type. Use 'file' or 'folder'."
    except Exception as e:
        return f"[ERROR] Could not create {item_type}: {e}"


def rename_item(
    source: str,
    destination: Optional[str] = None,
    pattern: Optional[str] = None,
    replacement: Optional[str] = None,
) -> str:
    """
    Rename or batch-rename items.
    """
    src_path = Path(source).resolve()

    # Single rename
    if not pattern and not replacement:
        if not src_path.exists():
            return f"[ERROR] Source '{src_path}' does not exist."
        if not destination:
            return "[ERROR] Destination not provided for single rename."

        dst_path = Path(destination).resolve()
        try:
            src_path.rename(dst_path)
            return f"[OK] Renamed '{src_path}' to '{dst_path}'"
        except Exception as e:
            return f"[ERROR] Could not rename: {e}"

    # Batch rename
    else:
        if not src_path.is_dir():
            return f"[ERROR] '{src_path}' must be a directory for batch rename."
        count = 0
        regex = re.compile(pattern or "")
        for child in src_path.iterdir():
            new_name = regex.sub(replacement or "", child.name)
            if new_name != child.name:
                new_path = child.parent / new_name
                try:
                    child.rename(new_path)
                    count += 1
                except Exception as e:
                    return f"[ERROR] Could not rename '{child.name}': {e}"
        return f"[OK] Batch-renamed {count} items in '{src_path}'."


def delete_item(path: str, safe_delete: bool = True) -> str:
    """
    Delete a file or folder with optional trash usage.
    """
    p = Path(path).resolve()
    if not p.exists():
        return f"[ERROR] '{p}' does not exist."

    try:
        if safe_delete:
            send2trash(p)
            return f"[OK] Moved '{p}' to trash."
        else:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            return f"[OK] Permanently deleted '{p}'."
    except Exception as e:
        return f"[ERROR] Could not delete '{p}': {e}"


def move_item(source: str, destination: str) -> str:
    """
    Move a file or folder.
    """
    src_path = Path(source).resolve()
    dst_path = Path(destination).resolve()
    if not src_path.exists():
        return f"[ERROR] Source '{src_path}' does not exist."
    try:
        shutil.move(str(src_path), str(dst_path))
        return f"[OK] Moved '{src_path}' -> '{dst_path}'"
    except Exception as e:
        return f"[ERROR] Could not move '{src_path}': {e}"


def copy_item(source: str, destination: str) -> str:
    """
    Copy a file or folder.
    """
    src_path = Path(source).resolve()
    dst_path = Path(destination).resolve()
    if not src_path.exists():
        return f"[ERROR] Source '{src_path}' does not exist."
    try:
        if src_path.is_dir():
            shutil.copytree(src_path, dst_path)
        else:
            shutil.copy2(src_path, dst_path)
        return f"[OK] Copied '{src_path}' -> '{dst_path}'"
    except Exception as e:
        return f"[ERROR] Could not copy '{src_path}': {e}"


def chmod_item(path: str, mode_str: str) -> str:
    """
    Change file/folder permissions in a chmod-like fashion.
    """
    p = Path(path).resolve()
    if not p.exists():
        return f"[ERROR] '{p}' does not exist."
    try:
        mode = int(mode_str, 8)
        os.chmod(p, mode)
        return f"[OK] Changed mode of '{p}' to {mode_str}"
    except Exception as e:
        return f"[ERROR] Could not change permissions: {e}"


def create_symlink(target: str, link_name: str, hard: bool = False) -> str:
    """
    Create a symbolic link (or hard link if specified).
    """
    t = Path(target).resolve()
    l = Path(link_name).resolve()

    if not t.exists():
        return f"[ERROR] Target '{t}' does not exist."
    try:
        if hard:
            if os.name == "nt":
                return "[ERROR] Hard links not fully supported on all Windows versions."
            os.link(t, l)
            return f"[OK] Created hard link '{l}' -> '{t}'"
        else:
            os.symlink(t, l)
            return f"[OK] Created symbolic link '{l}' -> '{t}'"
    except Exception as e:
        return f"[ERROR] Could not create link: {e}"


def compress_items(paths: List[str], archive_path: str, mode: str = "zip") -> str:
    """
    Compress multiple items into an archive.
    """
    try:
        if mode == "zip":
            import zlib  # ensure we have compression

            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
                all_files = []
                for p_str in paths:
                    p = Path(p_str).resolve()
                    if p.is_dir():
                        for root, dirs, files in os.walk(p):
                            for file in files:
                                file_path = Path(root) / file
                                all_files.append(
                                    (file_path, file_path.relative_to(p.parent))
                                )
                    else:
                        all_files.append((p, p.name))

                for file_path, arcname in all_files:
                    zf.write(file_path, arcname)
            return f"[OK] Created ZIP archive '{archive_path}'"

        elif mode == "tar":
            with tarfile.open(archive_path, "w") as tf:
                for p_str in paths:
                    p = Path(p_str).resolve()
                    tf.add(p, arcname=p.name)
            return f"[OK] Created TAR archive '{archive_path}'"

        else:
            return "[ERROR] Unsupported compression mode. Use 'zip' or 'tar'."
    except Exception as e:
        return f"[ERROR] Could not compress: {e}"


def decompress_item(archive_path: str, extract_to: str, mode: str = "zip") -> str:
    """
    Decompress an archive into a specified directory.
    """
    ap = Path(archive_path).resolve()
    if not ap.exists():
        return f"[ERROR] Archive '{ap}' does not exist."

    try:
        if mode == "zip":
            with zipfile.ZipFile(ap, "r") as zf:
                zf.extractall(extract_to)
            return f"[OK] Extracted ZIP archive to '{extract_to}'"

        elif mode == "tar":
            with tarfile.open(ap, "r") as tf:
                tf.extractall(extract_to)
            return f"[OK] Extracted TAR archive to '{extract_to}'"

        else:
            return "[ERROR] Unsupported decompression mode. Use 'zip' or 'tar'."
    except Exception as e:
        return f"[ERROR] Could not extract: {e}"


def generate_checksum(path: str, algorithm: str = "md5") -> str:
    """
    Generate a file checksum (md5, sha1, sha256).
    """
    p = Path(path).resolve()
    if not p.exists() or not p.is_file():
        return f"[ERROR] '{p}' is not a valid file."

    if algorithm not in ("md5", "sha1", "sha256"):
        return "[ERROR] Unsupported algorithm. Use 'md5', 'sha1', or 'sha256'."

    try:
        if algorithm == "md5":
            hash_func = hashlib.md5()
        elif algorithm == "sha1":
            hash_func = hashlib.sha1()
        else:
            hash_func = hashlib.sha256()

        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        return f"[OK] {algorithm.upper()} checksum for '{p}': {hash_func.hexdigest()}"
    except Exception as e:
        return f"[ERROR] Could not compute checksum: {e}"


def ftp_transfer(
    server: str,
    port: int,
    username: str,
    password: str,
    local_path: str,
    remote_path: str,
    upload: bool = True,
) -> str:
    """
    Simple FTP file transfer using ftplib.
    """
    local_path_p = Path(local_path).resolve()
    if upload and (not local_path_p.exists() or not local_path_p.is_file()):
        return f"[ERROR] Local file '{local_path_p}' does not exist for upload."

    try:
        with ftplib.FTP() as ftp:
            ftp.connect(server, port)
            ftp.login(username, password)
            if upload:
                with open(local_path_p, "rb") as f:
                    ftp.storbinary(f"STOR {remote_path}", f)
                return f"[OK] Uploaded '{local_path_p}' to '{server}:{remote_path}'"
            else:
                with open(local_path_p, "wb") as f:
                    ftp.retrbinary(f"RETR {remote_path}", f.write)
                return f"[OK] Downloaded '{server}:{remote_path}' to '{local_path_p}'"
    except Exception as e:
        return f"[ERROR] FTP transfer failed: {e}"


def sftp_transfer(
    server: str,
    port: int,
    username: str,
    password: str,
    local_path: str,
    remote_path: str,
    upload: bool = True,
) -> str:
    """
    Secure SFTP file transfer using Paramiko.
    """
    local_path_p = Path(local_path).resolve()
    if upload and (not local_path_p.exists() or not local_path_p.is_file()):
        return f"[ERROR] Local file '{local_path_p}' does not exist for upload."

    try:
        transport = paramiko.Transport((server, port))
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)

        if upload:
            sftp.put(str(local_path_p), remote_path)
            result = f"[OK] SFTP uploaded '{local_path_p}' -> '{server}:{remote_path}'"
        else:
            sftp.get(remote_path, str(local_path_p))
            result = (
                f"[OK] SFTP downloaded '{server}:{remote_path}' -> '{local_path_p}'"
            )

        sftp.close()
        transport.close()
        return result
    except Exception as e:
        return f"[ERROR] SFTP transfer failed: {e}"


def preview_file(path: str, max_lines: int = 20) -> str:
    """
    Return the first `max_lines` lines of a text file as a string.
    """
    p = Path(path).resolve()
    if not p.is_file():
        return f"[ERROR] '{p}' is not a valid file."

    try:
        with p.open("r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        result = [f"--- Preview of {p} (first {max_lines} lines) ---\n"]
        result += lines[:max_lines]
        if len(lines) > max_lines:
            result.append(
                f"\n--- File truncated. {len(lines) - max_lines} lines not shown. ---\n"
            )
        return "".join(result)
    except Exception as e:
        return f"[ERROR] Could not preview file: {e}"


def search_files(directory: str, pattern: str, use_regex: bool = False) -> str:
    """
    Search for files by glob or regex pattern.
    """
    dir_path = Path(directory).resolve()
    if not dir_path.exists() or not dir_path.is_dir():
        return f"[ERROR] '{dir_path}' is not a valid directory."

    matches = []
    if use_regex:
        regex = re.compile(pattern)
        for root, dirs, files in os.walk(dir_path):
            for f in files:
                if regex.search(f):
                    matches.append(Path(root) / f)
    else:
        matches = list(dir_path.rglob(pattern))

    if matches:
        lines = [f"[OK] Found matches:"]
        lines += [str(m) for m in matches]
        return "\n".join(lines)
    else:
        return "[INFO] No matches found."


##############################################################################
# 2. curses-based TUI
##############################################################################

main_menu = [
    ("List directory contents", "menu_list_items"),
    ("Create file/folder", "menu_create_item"),
    ("Rename item(s)", "menu_rename_item"),
    ("Delete item", "menu_delete_item"),
    ("Move item", "menu_move_item"),
    ("Copy item", "menu_copy_item"),
    ("Change permissions (chmod)", "menu_chmod_item"),
    ("Create link (symbolic/hard)", "menu_link_item"),
    ("Compress items (ZIP/TAR)", "menu_compress_item"),
    ("Decompress archive (ZIP/TAR)", "menu_decompress_item"),
    ("Generate checksum (MD5/SHA1/SHA256)", "menu_checksum_item"),
    ("FTP transfer", "menu_ftp_item"),
    ("SFTP transfer", "menu_sftp_item"),
    ("Preview text file", "menu_preview_file"),
    ("Search files", "menu_search_files"),
    ("Exit", "menu_exit"),
]


def curses_app(stdscr: "curses._CursesWindow") -> None:
    """
    The main curses TUI loop.
    """
    curses.curs_set(0)  # Hide cursor
    curses.start_color()
    curses.use_default_colors()

    curses.init_pair(1, curses.COLOR_CYAN, -1)  # highlight color
    curses.init_pair(2, curses.COLOR_WHITE, -1)  # normal text

    current_index = 0

    while True:
        stdscr.clear()
        stdscr.addstr(
            0, 0, "=== File Commander (curses + Typer Edition) ===\n", curses.A_BOLD
        )

        # Draw menu
        for idx, (label, _) in enumerate(main_menu):
            if idx == current_index:
                stdscr.attron(curses.color_pair(1))
                stdscr.addstr(idx + 2, 2, f"> {label}")
                stdscr.attroff(curses.color_pair(1))
            else:
                stdscr.attron(curses.color_pair(2))
                stdscr.addstr(idx + 2, 2, f"  {label}")
                stdscr.attroff(curses.color_pair(2))

        key = stdscr.getch()

        # Basic navigation with arrow keys or j/k
        if key in (curses.KEY_UP, ord("k")):
            current_index = (current_index - 1) % len(main_menu)
        elif key in (curses.KEY_DOWN, ord("j")):
            current_index = (current_index + 1) % len(main_menu)
        elif key in (curses.KEY_ENTER, ord("\n"), ord("\r")):
            fn_name = main_menu[current_index][1]
            if fn_name == "menu_exit":
                return
            else:
                handle_menu_action(stdscr, fn_name)
        elif key in (ord("q"), 27):  # ESC
            return


def handle_menu_action(stdscr: "curses._CursesWindow", action: str) -> None:
    action_map = {
        "menu_list_items": menu_list_items,
        "menu_create_item": menu_create_item,
        "menu_rename_item": menu_rename_item,
        "menu_delete_item": menu_delete_item,
        "menu_move_item": menu_move_item,
        "menu_copy_item": menu_copy_item,
        "menu_chmod_item": menu_chmod_item,
        "menu_link_item": menu_link_item,
        "menu_compress_item": menu_compress_item,
        "menu_decompress_item": menu_decompress_item,
        "menu_checksum_item": menu_checksum_item,
        "menu_ftp_item": menu_ftp_item,
        "menu_sftp_item": menu_sftp_item,
        "menu_preview_file": menu_preview_file,
        "menu_search_files": menu_search_files,
    }
    if action in action_map:
        action_map[action](stdscr)


def get_user_input(
    stdscr: "curses._CursesWindow", prompt_text: str, default: str = ""
) -> str:
    curses.echo()
    stdscr.clear()
    stdscr.addstr(0, 0, f"{prompt_text} (default: {default})\n")
    stdscr.addstr(1, 0, "> ")
    stdscr.refresh()
    user_input = stdscr.getstr(1, 2).decode("utf-8").strip()
    curses.noecho()
    return user_input if user_input else default


def confirm_choice(
    stdscr: "curses._CursesWindow", prompt_text: str, default: bool = False
) -> bool:
    choices = "[y/N]" if not default else "[Y/n]"
    curses.echo()
    stdscr.clear()
    stdscr.addstr(0, 0, f"{prompt_text} {choices}\n")
    stdscr.addstr(1, 0, "> ")
    stdscr.refresh()
    choice = stdscr.getstr(1, 2).decode("utf-8").strip().lower()
    curses.noecho()
    if not choice:
        return default
    return choice.startswith("y")


def display_output(stdscr: "curses._CursesWindow", text: str) -> None:
    stdscr.clear()
    lines = text.split("\n")
    h, w = stdscr.getmaxyx()

    # Simple pager if content exceeds screen height
    if len(lines) <= (h - 1):
        for idx, line in enumerate(lines):
            if idx < h - 1:
                stdscr.addstr(idx, 0, line)
    else:
        page_start = 0
        while True:
            stdscr.clear()
            page_end = page_start + (h - 1)
            page_lines = lines[page_start:page_end]
            for idx, line in enumerate(page_lines):
                stdscr.addstr(idx, 0, line[: w - 1])

            stdscr.addstr(h - 1, 0, "[PgUp/PgDn or q to quit display]")
            key = stdscr.getch()
            if key == curses.KEY_PPAGE:  # Page Up
                page_start = max(0, page_start - (h - 1))
            elif key == curses.KEY_NPAGE:  # Page Down
                if page_end < len(lines):
                    page_start += h - 1
            elif key in [ord("q"), 27]:
                break
    stdscr.addstr(h - 1, 0, "\nPress any key to continue...")
    stdscr.getch()


##############################################################################
# 3. Menu Functions (curses)
##############################################################################


def menu_list_items(stdscr: "curses._CursesWindow"):
    path = get_user_input(stdscr, "Path to list?", ".")
    detailed = confirm_choice(stdscr, "Detailed listing?", False)
    tree = confirm_choice(stdscr, "Tree view?", False)
    result = list_items(path, detailed=detailed, tree=tree)
    display_output(stdscr, result)


def menu_create_item(stdscr: "curses._CursesWindow"):
    item_type = get_user_input(stdscr, "Item type (file/folder)?", "file")
    path = get_user_input(stdscr, "Path to create?", "./new_file.txt")
    result = create_item(item_type, path)
    display_output(stdscr, result)


def menu_rename_item(stdscr: "curses._CursesWindow"):
    src = get_user_input(stdscr, "Source path?")
    batch = confirm_choice(stdscr, "Batch rename using regex?", False)
    if batch:
        pattern = get_user_input(stdscr, "Regex pattern?")
        replacement = get_user_input(stdscr, "Replacement string?", "")
        result = rename_item(src, pattern=pattern, replacement=replacement)
    else:
        dest = get_user_input(stdscr, "Destination path?")
        result = rename_item(src, destination=dest)
    display_output(stdscr, result)


def menu_delete_item(stdscr: "curses._CursesWindow"):
    path = get_user_input(stdscr, "Path to delete?")
    safe = confirm_choice(stdscr, "Safe delete (to trash)?", True)
    result = delete_item(path, safe_delete=safe)
    display_output(stdscr, result)


def menu_move_item(stdscr: "curses._CursesWindow"):
    src = get_user_input(stdscr, "Source path?")
    dst = get_user_input(stdscr, "Destination path?")
    result = move_item(src, dst)
    display_output(stdscr, result)


def menu_copy_item(stdscr: "curses._CursesWindow"):
    src = get_user_input(stdscr, "Source path?")
    dst = get_user_input(stdscr, "Destination path?")
    result = copy_item(src, dst)
    display_output(stdscr, result)


def menu_chmod_item(stdscr: "curses._CursesWindow"):
    path = get_user_input(stdscr, "Path?")
    mode_str = get_user_input(stdscr, "Octal permission? (e.g., 755)", "755")
    result = chmod_item(path, mode_str)
    display_output(stdscr, result)


def menu_link_item(stdscr: "curses._CursesWindow"):
    target = get_user_input(stdscr, "Target path?")
    link_name = get_user_input(stdscr, "Link name/path?")
    hard = confirm_choice(stdscr, "Create a hard link?", False)
    result = create_symlink(target, link_name, hard=hard)
    display_output(stdscr, result)


def menu_compress_item(stdscr: "curses._CursesWindow"):
    items_raw = get_user_input(stdscr, "Items to compress (comma-separated)?", "")
    items = [item.strip() for item in items_raw.split(",") if item.strip()]
    archive = get_user_input(
        stdscr, "Output archive path? (e.g. archive.zip)", "archive.zip"
    )
    mode = get_user_input(stdscr, "Mode (zip/tar)?", "zip")
    result = compress_items(items, archive, mode)
    display_output(stdscr, result)


def menu_decompress_item(stdscr: "curses._CursesWindow"):
    archive = get_user_input(stdscr, "Archive path?", "archive.zip")
    extract_to = get_user_input(stdscr, "Extract to directory?", ".")
    mode = get_user_input(stdscr, "Mode (zip/tar)?", "zip")
    result = decompress_item(archive, extract_to, mode)
    display_output(stdscr, result)


def menu_checksum_item(stdscr: "curses._CursesWindow"):
    fpath = get_user_input(stdscr, "File path?")
    algo = get_user_input(stdscr, "Algorithm (md5/sha1/sha256)?", "md5")
    result = generate_checksum(fpath, algo)
    display_output(stdscr, result)


def menu_ftp_item(stdscr: "curses._CursesWindow"):
    server = get_user_input(stdscr, "FTP server?")
    port_str = get_user_input(stdscr, "FTP port?", "21")
    username = get_user_input(stdscr, "Username?")
    password = get_user_input(stdscr, "Password?", "")
    local = get_user_input(stdscr, "Local file path?")
    remote = get_user_input(stdscr, "Remote file path?")
    up = confirm_choice(stdscr, "Upload instead of download?", True)
    try:
        port_int = int(port_str)
    except ValueError:
        port_int = 21
    result = ftp_transfer(server, port_int, username, password, local, remote, up)
    display_output(stdscr, result)


def menu_sftp_item(stdscr: "curses._CursesWindow"):
    server = get_user_input(stdscr, "SFTP server?")
    port_str = get_user_input(stdscr, "SFTP port?", "22")
    username = get_user_input(stdscr, "Username?")
    password = get_user_input(stdscr, "Password?", "")
    local = get_user_input(stdscr, "Local file path?")
    remote = get_user_input(stdscr, "Remote file path?")
    up = confirm_choice(stdscr, "Upload instead of download?", True)
    try:
        port_int = int(port_str)
    except ValueError:
        port_int = 22
    result = sftp_transfer(server, port_int, username, password, local, remote, up)
    display_output(stdscr, result)


def menu_preview_file(stdscr: "curses._CursesWindow"):
    fpath = get_user_input(stdscr, "File path?")
    lines_str = get_user_input(stdscr, "Max lines?", "20")
    try:
        max_lines = int(lines_str)
    except ValueError:
        max_lines = 20
    result = preview_file(fpath, max_lines)
    display_output(stdscr, result)


def menu_search_files(stdscr: "curses._CursesWindow"):
    directory = get_user_input(stdscr, "Directory to search?", ".")
    pattern = get_user_input(stdscr, "Pattern (glob or regex)?", "*.txt")
    regex = confirm_choice(stdscr, "Use regex?", False)
    result = search_files(directory, pattern, regex)
    display_output(stdscr, result)


def menu_exit(stdscr: "curses._CursesWindow"):
    pass  # Exits in the main loop when selected


##############################################################################
# 4. Typer Commands (CLI usage)
##############################################################################


# We add a top-level callback so that if no subcommand is invoked,
# we launch the curses TUI.
@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    """
    By default, if no arguments/subcommands are passed, launch the TUI.
    """
    if ctx.invoked_subcommand is None:
        curses.wrapper(curses_app)
        raise typer.Exit()  # Ensure no further Typer processing after TUI


@app.command()
def tui():
    """
    Explicitly launch the interactive curses-based TUI.
    """
    curses.wrapper(curses_app)


@app.command()
def list(
    path: str = typer.Argument(".", help="Path to list"),
    detailed: bool = typer.Option(False, "--detailed", help="Show detailed listing."),
    tree: bool = typer.Option(False, "--tree", help="Show a recursive directory tree."),
):
    """
    List directory contents.
    """
    result = list_items(path, detailed, tree)
    rprint(_richify(result))


@app.command()
def create(
    item_type: str = typer.Argument(..., help="file or folder"),
    path: str = typer.Argument(..., help="Path to create."),
):
    """
    Create a new file or folder.
    """
    result = create_item(item_type, path)
    rprint(_richify(result))


@app.command()
def rename(
    source: str = typer.Argument(..., help="Source path (file or directory)."),
    destination: Optional[str] = typer.Option(None, "--dest", help="Destination path."),
    pattern: Optional[str] = typer.Option(
        None, "--pattern", help="Regex pattern for batch rename."
    ),
    replacement: Optional[str] = typer.Option(
        "", "--replacement", help="Regex replacement string."
    ),
):
    """
    Rename or batch-rename items.
    """
    result = rename_item(source, destination, pattern, replacement)
    rprint(_richify(result))


@app.command()
def delete(
    path: str = typer.Argument(..., help="File/folder path to delete."),
    safe_delete: bool = typer.Option(
        True, "--safe/--no-safe", help="Move to trash if safe is True."
    ),
):
    """
    Delete a file or folder (safe delete by default).
    """
    result = delete_item(path, safe_delete)
    rprint(_richify(result))


@app.command()
def move(
    source: str = typer.Argument(..., help="Path to move from."),
    destination: str = typer.Argument(..., help="Path to move to."),
):
    """
    Move a file or folder.
    """
    result = move_item(source, destination)
    rprint(_richify(result))


@app.command()
def copy(
    source: str = typer.Argument(..., help="Path to copy from."),
    destination: str = typer.Argument(..., help="Path to copy to."),
):
    """
    Copy a file or folder.
    """
    result = copy_item(source, destination)
    rprint(_richify(result))


@app.command()
def chmod(
    path: str = typer.Argument(..., help="Path for chmod."),
    mode_str: str = typer.Argument("755", help="Octal permission string (e.g., 755)."),
):
    """
    Change file/folder permissions.
    """
    result = chmod_item(path, mode_str)
    rprint(_richify(result))


@app.command()
def link(
    target: str = typer.Argument(..., help="Existing target path."),
    link_name: str = typer.Argument(..., help="Symlink (or hardlink) name/path."),
    hard: bool = typer.Option(
        False, "--hard/--no-hard", help="Create a hard link if True."
    ),
):
    """
    Create a symbolic or hard link.
    """
    result = create_symlink(target, link_name, hard)
    rprint(_richify(result))


@app.command()
def compress(
    paths: List[str] = typer.Argument(
        ..., help="One or more files/folders to compress."
    ),
    archive_path: str = typer.Argument(
        ..., help="Output archive path (e.g. archive.zip)"
    ),
    mode: str = typer.Option("zip", "--mode", help="Compression mode: zip or tar"),
):
    """
    Compress multiple items into an archive.
    """
    result = compress_items(paths, archive_path, mode)
    rprint(_richify(result))


@app.command()
def decompress(
    archive_path: str = typer.Argument(..., help="Path to archive file."),
    extract_to: str = typer.Argument(".", help="Directory to extract into."),
    mode: str = typer.Option("zip", "--mode", help="Decompression mode: zip or tar"),
):
    """
    Decompress an archive into a specified directory.
    """
    result = decompress_item(archive_path, extract_to, mode)
    rprint(_richify(result))


@app.command()
def checksum(
    path: str = typer.Argument(..., help="Path to file."),
    algorithm: str = typer.Option(
        "md5", "--algo", help="Algorithm: md5, sha1, or sha256."
    ),
):
    """
    Generate a file checksum.
    """
    result = generate_checksum(path, algorithm)
    rprint(_richify(result))


@app.command()
def ftp(
    server: str = typer.Option(..., help="FTP server address."),
    port: int = typer.Option(21, help="FTP server port."),
    username: str = typer.Option(..., help="FTP username."),
    password: str = typer.Option("", help="FTP password."),
    local_path: str = typer.Option(..., help="Local file path."),
    remote_path: str = typer.Option(..., help="Remote file path on server."),
    upload: bool = typer.Option(
        True, "--upload/--download", help="Upload (True) or download (False)."
    ),
):
    """
    FTP transfer (upload or download).
    """
    result = ftp_transfer(
        server, port, username, password, local_path, remote_path, upload
    )
    rprint(_richify(result))


@app.command()
def sftp(
    server: str = typer.Option(..., help="SFTP server address."),
    port: int = typer.Option(22, help="SFTP server port."),
    username: str = typer.Option(..., help="SFTP username."),
    password: str = typer.Option("", help="SFTP password."),
    local_path: str = typer.Option(..., help="Local file path."),
    remote_path: str = typer.Option(..., help="Remote file path on server."),
    upload: bool = typer.Option(
        True, "--upload/--download", help="Upload (True) or download (False)."
    ),
):
    """
    SFTP transfer (upload or download).
    """
    result = sftp_transfer(
        server, port, username, password, local_path, remote_path, upload
    )
    rprint(_richify(result))


@app.command()
def preview(
    path: str = typer.Argument(..., help="Path to file to preview."),
    max_lines: int = typer.Option(20, "--max-lines", help="Max lines to read."),
):
    """
    Preview the first N lines of a text file.
    """
    result = preview_file(path, max_lines)
    rprint(_richify(result))


@app.command()
def search(
    directory: str = typer.Argument(".", help="Directory to search."),
    pattern: str = typer.Argument("*.txt", help="Glob or regex pattern."),
    use_regex: bool = typer.Option(
        False, "--regex/--glob", help="Interpret 'pattern' as regex."
    ),
):
    """
    Search for files by glob or regex pattern.
    """
    result = search_files(directory, pattern, use_regex)
    rprint(_richify(result))


##############################################################################
# 5. Main Entry
##############################################################################

if __name__ == "__main__":
    # If no arguments were provided, Typer's callback will handle launching the TUI.
    # Otherwise, it will proceed with the usual CLI subcommands.
    app()
