#!/usr/bin/env python3
"""
file-commander: A cross-platform, menu-driven file operations utility.

Features Included:
------------------
1. Interactive Menu (with colorized output via Rich)
2. List contents of a directory
3. Create a file or folder
4. Rename items (single or batch)
5. Delete items (optionally sends to trash via send2trash)
6. Move or copy items
7. Change permissions (chmod-like)
8. Create symbolic or hard links
9. Compress/decompress (ZIP/TAR) with progress bars via tqdm
10. Generate checksums (MD5, SHA1, SHA256)
11. FTP transfer (upload/download via ftplib)
12. SFTP transfer (via paramiko)
13. Preview text files
14. Search files (glob or regex)
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
from pathlib import Path
from datetime import datetime

# === Third-party imports (install via requirements.txt) ===
from rich import print  # colorized replacement for built-in print
from rich.console import Console
from rich.prompt import Prompt
from rich.traceback import install as rich_traceback
from rich.panel import Panel
from rich.table import Table
from tqdm import tqdm
from send2trash import send2trash
import paramiko

# Initialize Rich console and traceback for nicer error messages
console = Console()
rich_traceback()


def list_items(path, detailed=False, tree=False):
    """
    List files and directories at the given path.

    :param path: Path to list contents of.
    :param detailed: If True, show more info (size, modification time).
    :param tree: If True, display a directory tree (recursive listing).
    """
    p = Path(path).resolve()
    if not p.exists():
        console.print(f"[bold red][ERROR][/bold red] Path '{p}' does not exist.")
        return

    if tree:
        console.print(Panel.fit(f"Directory Tree for [bold]{p}[/bold]:"))
        for root, dirs, files in os.walk(p):
            level = root.replace(str(p), "").count(os.sep)
            indent = " " * (4 * level)
            console.print(f"{indent}[bold cyan]{os.path.basename(root)}/[/bold cyan]")
            subindent = " " * (4 * (level + 1))
            for f in files:
                console.print(f"{subindent}{f}")
    else:
        console.print(Panel.fit(f"Listing contents of: [bold]{p}[/bold]"))
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Name", justify="left")
        if detailed:
            table.add_column("Type", justify="center")
            table.add_column("Size (bytes)", justify="right")
            table.add_column("Modified", justify="center")

        for entry in p.iterdir():
            if detailed:
                size = entry.stat().st_size
                mtime = datetime.fromtimestamp(entry.stat().st_mtime)
                ftype = "DIR" if entry.is_dir() else "FILE"
                table.add_row(
                    entry.name,
                    ftype,
                    str(size),
                    mtime.strftime("%Y-%m-%d %H:%M:%S"),
                )
            else:
                table.add_row(entry.name)
        console.print(table)


def create_item(item_type, path):
    """
    Create a new file or directory at the given path.

    :param item_type: 'file' or 'folder'
    :param path: Where to create the item.
    """
    p = Path(path).resolve()
    if p.exists():
        console.print(f"[bold red][ERROR][/bold red] '{p}' already exists.")
        return

    try:
        if item_type == "file":
            p.touch()
            console.print(
                f"[bold green][OK][/bold green] Created file: [bold]{p}[/bold]"
            )
        elif item_type == "folder":
            p.mkdir(parents=True, exist_ok=True)
            console.print(
                f"[bold green][OK][/bold green] Created folder: [bold]{p}[/bold]"
            )
        else:
            console.print(
                "[bold red][ERROR][/bold red] Unknown item_type. Use 'file' or 'folder'."
            )
    except Exception as e:
        console.print(f"[bold red][ERROR][/bold red] Could not create {item_type}: {e}")


def rename_item(source, destination=None, pattern=None, replacement=None):
    """
    Rename or batch-rename items.

    :param source: Path to source file/folder or directory for batch renaming.
    :param destination: New name or destination path for a single rename (if pattern is None).
    :param pattern: Regex pattern to find (batch rename).
    :param replacement: String replacement (batch rename).
    """
    src_path = Path(source).resolve()

    # Single rename
    if pattern is None or replacement is None:
        if not src_path.exists():
            console.print(
                f"[bold red][ERROR][/bold red] Source '{src_path}' does not exist."
            )
            return
        if destination is None:
            console.print(
                "[bold red][ERROR][/bold red] Destination not provided for single rename."
            )
            return

        dst_path = Path(destination).resolve()
        try:
            src_path.rename(dst_path)
            console.print(
                f"[bold green][OK][/bold green] Renamed '{src_path}' to '{dst_path}'"
            )
        except Exception as e:
            console.print(f"[bold red][ERROR][/bold red] Could not rename: {e}")
    else:
        # Batch rename within a directory
        if not src_path.is_dir():
            console.print(
                f"[bold red][ERROR][/bold red] '{src_path}' must be a directory for batch rename."
            )
            return
        count = 0
        regex = re.compile(pattern)
        for child in src_path.iterdir():
            new_name = regex.sub(replacement, child.name)
            if new_name != child.name:
                new_path = child.parent / new_name
                try:
                    child.rename(new_path)
                    count += 1
                except Exception as e:
                    console.print(
                        f"[bold red][ERROR][/bold red] Could not rename '{child.name}': {e}"
                    )
        console.print(
            f"[bold green][OK][/bold green] Batch-renamed {count} items in '{src_path}'."
        )


def delete_item(path, safe_delete=True):
    """
    Delete a file or folder with confirmation.
    By default, uses send2trash for safe_delete; set safe_delete=False to remove permanently.

    :param path: Path to the file or folder to delete.
    :param safe_delete: If True, move to trash. Otherwise, permanently delete.
    """
    p = Path(path).resolve()
    if not p.exists():
        console.print(f"[bold red][ERROR][/bold red] '{p}' does not exist.")
        return

    confirm = Prompt.ask(
        f"[yellow]Are you sure you want to delete '{p}'?[/yellow]",
        choices=["y", "n"],
        default="n",
    )
    if confirm.lower() == "y":
        try:
            if safe_delete:
                # Move to trash
                send2trash(p)
                console.print(f"[bold green][OK][/bold green] Moved '{p}' to trash.")
            else:
                # Permanently delete
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()
                console.print(
                    f"[bold green][OK][/bold green] Permanently deleted '{p}'."
                )
        except Exception as e:
            console.print(f"[bold red][ERROR][/bold red] Could not delete '{p}': {e}")
    else:
        console.print("[bold cyan][INFO][/bold cyan] Deletion canceled.")


def move_item(source, destination):
    """
    Move a file or folder to a new location.

    :param source: Path to the file/folder to move.
    :param destination: Target path or directory.
    """
    src_path = Path(source).resolve()
    dst_path = Path(destination).resolve()

    if not src_path.exists():
        console.print(
            f"[bold red][ERROR][/bold red] Source '{src_path}' does not exist."
        )
        return

    try:
        shutil.move(str(src_path), str(dst_path))
        console.print(
            f"[bold green][OK][/bold green] Moved '{src_path}' -> '{dst_path}'"
        )
    except Exception as e:
        console.print(f"[bold red][ERROR][/bold red] Could not move '{src_path}': {e}")


def copy_item(source, destination):
    """
    Copy a file or folder to a new location.

    :param source: Path to file/folder.
    :param destination: Target path.
    """
    src_path = Path(source).resolve()
    dst_path = Path(destination).resolve()

    if not src_path.exists():
        console.print(
            f"[bold red][ERROR][/bold red] Source '{src_path}' does not exist."
        )
        return

    try:
        if src_path.is_dir():
            shutil.copytree(src_path, dst_path)
        else:
            shutil.copy2(src_path, dst_path)
        console.print(
            f"[bold green][OK][/bold green] Copied '{src_path}' -> '{dst_path}'"
        )
    except Exception as e:
        console.print(f"[bold red][ERROR][/bold red] Could not copy '{src_path}': {e}")


def chmod_item(path, mode_str):
    """
    Change file/folder permissions in a chmod-like fashion.

    :param path: Path to file/folder.
    :param mode_str: String representing octal permission (e.g., '755').
    """
    p = Path(path).resolve()
    if not p.exists():
        console.print(f"[bold red][ERROR][/bold red] '{p}' does not exist.")
        return

    try:
        mode = int(mode_str, 8)
        os.chmod(p, mode)
        console.print(
            f"[bold green][OK][/bold green] Changed mode of '{p}' to {mode_str}"
        )
    except Exception as e:
        console.print(f"[bold red][ERROR][/bold red] Could not change permissions: {e}")


def create_symlink(target, link_name, hard=False):
    """
    Create a symbolic link (or hard link if specified).

    :param target: The target file/folder path.
    :param link_name: The path where the link should be created.
    :param hard: If True, create a hard link instead of a symbolic link.
    """
    t = Path(target).resolve()
    l = Path(link_name).resolve()

    if not t.exists():
        console.print(f"[bold red][ERROR][/bold red] Target '{t}' does not exist.")
        return

    try:
        if hard and os.name == "nt":
            console.print(
                "[bold red][ERROR][/bold red] Hard links not fully supported on all Windows versions."
            )
            return
        if hard:
            os.link(t, l)
            console.print(
                f"[bold green][OK][/bold green] Created hard link '{l}' -> '{t}'"
            )
        else:
            os.symlink(t, l)
            console.print(
                f"[bold green][OK][/bold green] Created symbolic link '{l}' -> '{t}'"
            )
    except Exception as e:
        console.print(f"[bold red][ERROR][/bold red] Could not create link: {e}")


def compress_items(paths, archive_path, mode="zip"):
    """
    Compress multiple items into an archive.

    :param paths: List of file/folder paths to compress.
    :param archive_path: Destination archive file path.
    :param mode: 'zip' or 'tar'
    """
    if mode == "zip":
        try:
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # Use tqdm for a progress bar, especially if there are many files
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

                for file_path, arcname in tqdm(
                    all_files, desc="Compressing", unit="file"
                ):
                    zf.write(file_path, arcname)

            console.print(
                f"[bold green][OK][/bold green] Created ZIP archive '[bold]{archive_path}[/bold]'"
            )
        except Exception as e:
            console.print(
                f"[bold red][ERROR][/bold red] Could not compress to ZIP: {e}"
            )

    elif mode == "tar":
        try:
            with tarfile.open(archive_path, "w") as tf:
                # Similarly, use tqdm for a progress bar
                all_paths = [Path(p_str).resolve() for p_str in paths]
                for p in tqdm(all_paths, desc="Compressing", unit="file"):
                    tf.add(p, arcname=p.name)

            console.print(
                f"[bold green][OK][/bold green] Created TAR archive '[bold]{archive_path}[/bold]'"
            )
        except Exception as e:
            console.print(
                f"[bold red][ERROR][/bold red] Could not compress to TAR: {e}"
            )

    else:
        console.print(
            "[bold red][ERROR][/bold red] Unsupported compression mode. Use 'zip' or 'tar'."
        )


def decompress_item(archive_path, extract_to, mode="zip"):
    """
    Decompress an archive into a specified directory.

    :param archive_path: Path to the archive file.
    :param extract_to: Destination directory.
    :param mode: 'zip' or 'tar'
    """
    ap = Path(archive_path).resolve()
    if not ap.exists():
        console.print(f"[bold red][ERROR][/bold red] Archive '{ap}' does not exist.")
        return

    if mode == "zip":
        try:
            with zipfile.ZipFile(ap, "r") as zf:
                # Use a tqdm progress bar to show extraction progress
                members = zf.namelist()
                for member in tqdm(members, desc="Extracting", unit="file"):
                    zf.extract(member, extract_to)
            console.print(
                f"[bold green][OK][/bold green] Extracted ZIP archive to '[bold]{extract_to}[/bold]'"
            )
        except Exception as e:
            console.print(f"[bold red][ERROR][/bold red] Could not extract ZIP: {e}")

    elif mode == "tar":
        try:
            with tarfile.open(ap, "r") as tf:
                # We can’t easily get the full member list as a single list for all tar files,
                # so we’ll iterate. For large archives, consider a more advanced progress approach.
                members = tf.getmembers()
                for member in tqdm(members, desc="Extracting", unit="file"):
                    tf.extract(member, extract_to)
            console.print(
                f"[bold green][OK][/bold green] Extracted TAR archive to '[bold]{extract_to}[/bold]'"
            )
        except Exception as e:
            console.print(f"[bold red][ERROR][/bold red] Could not extract TAR: {e}")
    else:
        console.print(
            "[bold red][ERROR][/bold red] Unsupported decompression mode. Use 'zip' or 'tar'."
        )


def generate_checksum(path, algorithm="md5"):
    """
    Generate a file checksum (md5, sha1, sha256).

    :param path: Path to the file.
    :param algorithm: The hash algorithm ('md5', 'sha1', 'sha256').
    """
    p = Path(path).resolve()
    if not p.exists() or not p.is_file():
        console.print(f"[bold red][ERROR][/bold red] '{p}' is not a valid file.")
        return

    if algorithm not in ("md5", "sha1", "sha256"):
        console.print(
            "[bold red][ERROR][/bold red] Unsupported algorithm. Use 'md5', 'sha1', or 'sha256'."
        )
        return

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
        console.print(
            f"[bold green][OK][/bold green] {algorithm.upper()} checksum for '[bold]{p}[/bold]': {hash_func.hexdigest()}"
        )
    except Exception as e:
        console.print(f"[bold red][ERROR][/bold red] Could not compute checksum: {e}")


def ftp_transfer(
    server, port, username, password, local_path, remote_path, upload=True
):
    """
    Simple FTP file transfer using the standard library ftplib.

    :param server: FTP server address.
    :param port: FTP server port.
    :param username: FTP username.
    :param password: FTP password.
    :param local_path: Path to local file.
    :param remote_path: Destination path on FTP server.
    :param upload: If True, upload. If False, download.
    """
    local_path = Path(local_path).resolve()
    if upload and (not local_path.exists() or not local_path.is_file()):
        console.print(
            f"[bold red][ERROR][/bold red] Local file '{local_path}' does not exist for upload."
        )
        return

    try:
        with ftplib.FTP() as ftp:
            ftp.connect(server, port)
            ftp.login(username, password)
            if upload:
                with open(local_path, "rb") as f:
                    ftp.storbinary(f"STOR {remote_path}", f)
                console.print(
                    f"[bold green][OK][/bold green] Uploaded '{local_path}' to '{server}:{remote_path}'"
                )
            else:
                with open(local_path, "wb") as f:
                    ftp.retrbinary(f"RETR {remote_path}", f.write)
                console.print(
                    f"[bold green][OK][/bold green] Downloaded '{server}:{remote_path}' to '{local_path}'"
                )
    except Exception as e:
        console.print(f"[bold red][ERROR][/bold red] FTP transfer failed: {e}")


def sftp_transfer(
    server, port, username, password, local_path, remote_path, upload=True
):
    """
    Secure SFTP file transfer using Paramiko.

    :param server: SFTP server address.
    :param port: SFTP server port.
    :param username: SFTP username.
    :param password: SFTP password.
    :param local_path: Path to local file.
    :param remote_path: Destination path on SFTP server.
    :param upload: If True, upload. If False, download.
    """
    local_path = Path(local_path).resolve()
    if upload and (not local_path.exists() or not local_path.is_file()):
        console.print(
            f"[bold red][ERROR][/bold red] Local file '{local_path}' does not exist for upload."
        )
        return

    try:
        transport = paramiko.Transport((server, port))
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)

        if upload:
            sftp.put(str(local_path), remote_path)
            console.print(
                f"[bold green][OK][/bold green] SFTP uploaded '{local_path}' -> '{server}:{remote_path}'"
            )
        else:
            sftp.get(remote_path, str(local_path))
            console.print(
                f"[bold green][OK][/bold green] SFTP downloaded '{server}:{remote_path}' -> '{local_path}'"
            )

        sftp.close()
        transport.close()

    except Exception as e:
        console.print(f"[bold red][ERROR][/bold red] SFTP transfer failed: {e}")


def preview_file(path, max_lines=20):
    """
    Preview a text file directly in the CLI.

    :param path: Path to the text file.
    :param max_lines: Maximum number of lines to preview.
    """
    p = Path(path).resolve()
    if not p.is_file():
        console.print(f"[bold red][ERROR][/bold red] '{p}' is not a valid file.")
        return

    try:
        with p.open("r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        console.print(
            Panel.fit(f"--- Preview of [bold]{p}[/bold] (first {max_lines} lines) ---")
        )
        for line in lines[:max_lines]:
            # Using Rich's print to preserve color if needed
            console.print(line, end="")

        if len(lines) > max_lines:
            console.print(
                f"\n[bold cyan]--- File truncated. {len(lines) - max_lines} lines not shown. ---[/bold cyan]"
            )
    except Exception as e:
        console.print(f"[bold red][ERROR][/bold red] Could not preview file: {e}")


def search_files(directory, pattern, use_regex=False):
    """
    Search for files by name (glob or regex).

    :param directory: Directory to search in.
    :param pattern: Glob pattern (e.g., '*.txt') or regex if use_regex=True.
    :param use_regex: If True, interpret pattern as a regular expression.
    """
    dir_path = Path(directory).resolve()
    if not dir_path.exists() or not dir_path.is_dir():
        console.print(
            f"[bold red][ERROR][/bold red] '{dir_path}' is not a valid directory."
        )
        return

    console.print(
        f"[bold cyan][INFO][/bold cyan] Searching in '[bold]{dir_path}[/bold]' using {'regex' if use_regex else 'glob'}: {pattern}"
    )

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
        console.print("[bold green][OK][/bold green] Found matches:")
        for m in matches:
            console.print(m)
    else:
        console.print("[bold cyan][INFO][/bold cyan] No matches found.")


def interactive_menu():
    """
    Provide an interactive menu-driven interface for file-commander.
    Utilizes Rich for colorized prompts and outputs.
    """
    while True:
        console.print(
            "\n[bold magenta]=== file-commander Interactive Menu ===[/bold magenta]"
        )
        console.print("1. List directory contents")
        console.print("2. Create file/folder")
        console.print("3. Rename file/folder")
        console.print("4. Delete file/folder")
        console.print("5. Move file/folder")
        console.print("6. Copy file/folder")
        console.print("7. Change permissions")
        console.print("8. Create link")
        console.print("9. Compress items")
        console.print("10. Decompress archive")
        console.print("11. Generate checksum")
        console.print("12. FTP transfer")
        console.print("13. SFTP transfer")
        console.print("14. Preview text file")
        console.print("15. Search files")
        console.print("0. Exit")

        choice = Prompt.ask("[bold]Select an option[/bold]", default="0")

        if choice == "0":
            console.print("[bold cyan]Exiting interactive mode.[/bold cyan]")
            break

        elif choice == "1":
            path = Prompt.ask("Enter path to list", default=".")
            detailed = Prompt.ask("Detailed listing? (y/N)", default="n").lower() == "y"
            tree = Prompt.ask("Tree view? (y/N)", default="n").lower() == "y"
            list_items(path, detailed, tree)

        elif choice == "2":
            item_type = Prompt.ask(
                "Create file or folder? (file/folder)", default="file"
            )
            path = Prompt.ask("Path to create")
            create_item(item_type, path)

        elif choice == "3":
            source = Prompt.ask("Source path")
            pattern = Prompt.ask(
                "Batch rename? Enter regex pattern (or leave blank for single rename)",
                default="",
            )
            if pattern:
                replacement = Prompt.ask("Enter replacement string")
                rename_item(source, pattern=pattern, replacement=replacement)
            else:
                destination = Prompt.ask("New name/destination")
                rename_item(source, destination=destination)

        elif choice == "4":
            path = Prompt.ask("Path to delete")
            safe = Prompt.ask("Safe delete to trash? (y/N)", default="y").lower() == "y"
            delete_item(path, safe_delete=safe)

        elif choice == "5":
            source = Prompt.ask("Source path")
            destination = Prompt.ask("Destination path")
            move_item(source, destination)

        elif choice == "6":
            source = Prompt.ask("Source path")
            destination = Prompt.ask("Destination path")
            copy_item(source, destination)

        elif choice == "7":
            path = Prompt.ask("Path to change permissions")
            mode = Prompt.ask("Octal permission (e.g. 755)")
            chmod_item(path, mode)

        elif choice == "8":
            target = Prompt.ask("Target path")
            link_name = Prompt.ask("Link name/path")
            hard = Prompt.ask("Hard link? (y/N)", default="n").lower() == "y"
            create_symlink(target, link_name, hard)

        elif choice == "9":
            archive_path = Prompt.ask("Output archive path")
            mode = Prompt.ask("Mode (zip/tar)", default="zip").lower()
            items_input = Prompt.ask("Enter file/folder paths (comma-separated)")
            items = [item.strip() for item in items_input.split(",")]
            compress_items(items, archive_path, mode)

        elif choice == "10":
            archive_path = Prompt.ask("Archive path")
            extract_to = Prompt.ask("Extract to directory", default=".")
            mode = Prompt.ask("Mode (zip/tar)", default="zip").lower()
            decompress_item(archive_path, extract_to, mode)

        elif choice == "11":
            path = Prompt.ask("File path")
            algo = Prompt.ask("Algorithm (md5/sha1/sha256)", default="md5").lower()
            generate_checksum(path, algo)

        elif choice == "12":
            server = Prompt.ask("FTP server address")
            port_str = Prompt.ask("FTP server port (default 21)", default="21")
            try:
                port = int(port_str)
            except ValueError:
                port = 21
            username = Prompt.ask("Username")
            password = Prompt.ask("Password", password=True)
            local_path = Prompt.ask("Local file path")
            remote_path = Prompt.ask("Remote path")
            direction = Prompt.ask("Upload or Download? (u/d)", default="u").lower()
            upload = direction == "u"
            ftp_transfer(
                server, port, username, password, local_path, remote_path, upload
            )

        elif choice == "13":
            server = Prompt.ask("SFTP server address")
            port_str = Prompt.ask("SFTP server port (default 22)", default="22")
            try:
                port = int(port_str)
            except ValueError:
                port = 22
            username = Prompt.ask("Username")
            password = Prompt.ask("Password", password=True)
            local_path = Prompt.ask("Local file path")
            remote_path = Prompt.ask("Remote path")
            direction = Prompt.ask("Upload or Download? (u/d)", default="u").lower()
            upload = direction == "u"
            sftp_transfer(
                server, port, username, password, local_path, remote_path, upload
            )

        elif choice == "14":
            path = Prompt.ask("Text file path")
            try:
                max_lines = int(
                    Prompt.ask("Max lines to preview (default 20)", default="20")
                )
            except ValueError:
                max_lines = 20
            preview_file(path, max_lines)

        elif choice == "15":
            directory = Prompt.ask("Directory to search", default=".")
            pattern = Prompt.ask("Pattern (glob or regex)", default="*.txt")
            use_regex = (
                Prompt.ask("Is this a regex pattern? (y/N)", default="n").lower() == "y"
            )
            search_files(directory, pattern, use_regex)

        else:
            console.print(
                "[bold cyan][INFO][/bold cyan] Invalid choice. Please try again."
            )


def main():
    """
    Main entry point: Start in interactive mode directly.
    """
    interactive_menu()


if __name__ == "__main__":
    main()
