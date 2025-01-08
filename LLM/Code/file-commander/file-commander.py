#!/usr/bin/env python3
"""
file_commander_typer.py

A cross-platform CLI-driven file operations utility rewritten using Typer.
Features:
1. List directory contents
2. Create files/folders
3. Rename items (single or batch)
4. Delete items (with optional trash)
5. Move/copy items
6. Change permissions
7. Create symlinks/hardlinks
8. Compress/decompress (ZIP/TAR)
9. Generate checksums (MD5, SHA1, SHA256)
10. FTP/SFTP transfers
11. Preview text files
12. Search files (glob or regex)
13. Optional interactive mode with menu-driven prompts
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
from typing import List, Optional

# Third-party imports (ensure they're installed)
from send2trash import send2trash
import paramiko
from tqdm import tqdm
import typer

##############################################################################
# 1. Helper Functions (ported from your original script)
##############################################################################


def list_items(path: str, detailed: bool = False, tree: bool = False) -> str:
    """
    List files/directories under `path`.
    :param path: Path to list.
    :param detailed: Show size, timestamp, and type info if True.
    :param tree: Show a recursive directory tree if True.
    :return: A formatted string of the directory contents or an error message.
    """
    p = Path(path).resolve()
    if not p.exists():
        return f"[ERROR] Path '{p}' does not exist."

    from io import StringIO

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
    :param item_type: 'file' or 'folder'
    :param path: The target path where to create the item.
    :return: Result message.
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
    :param source: Source path (file or directory).
    :param destination: Destination path for single rename.
    :param pattern: Regex pattern for batch rename.
    :param replacement: Replacement string for batch rename.
    :return: A string with the rename status.
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
    :param path: The path to delete.
    :param safe_delete: If True, move to trash. Otherwise, permanently delete.
    :return: A result message.
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
    :param path: Target path.
    :param mode_str: String representation of octal permissions (e.g., "755").
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
    :param target: Target path to link to.
    :param link_name: The name/path of the link to create.
    :param hard: If True, create a hard link (where supported).
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
    :param paths: List of file/directory paths to compress.
    :param archive_path: Destination archive file (e.g. "archive.zip").
    :param mode: "zip" or "tar".
    """
    try:
        if mode == "zip":
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
    :param archive_path: The archive file to decompress.
    :param extract_to: The directory where files will be extracted.
    :param mode: "zip" or "tar".
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
    :param path: File path.
    :param algorithm: Algorithm to use: "md5", "sha1", or "sha256".
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
    :param server: FTP server hostname/IP.
    :param port: FTP port (usually 21).
    :param username: FTP username.
    :param password: FTP password.
    :param local_path: Local file path (for upload or download destination).
    :param remote_path: Remote file path (for download or upload destination).
    :param upload: True to upload, False to download.
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
    :param server: SFTP server hostname/IP.
    :param port: SFTP port (usually 22).
    :param username: SFTP username.
    :param password: SFTP password.
    :param local_path: Local file path (for upload or download destination).
    :param remote_path: Remote file path (for download or upload destination).
    :param upload: True to upload, False to download.
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
    :param path: Path to a valid text file.
    :param max_lines: Maximum lines to read from the file.
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
    :param directory: Directory path to search in.
    :param pattern: Glob or regex pattern.
    :param use_regex: If True, interpret `pattern` as a regex.
    :return: String summarizing matched files.
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
# 2. Typer CLI App
##############################################################################

app = typer.Typer(help="A cross-platform CLI for file operations (Typer Edition).")


@app.command("list")
def cmd_list_items(
    path: str = typer.Argument(".", help="Directory path to list."),
    detailed: bool = typer.Option(
        False, "--detailed", "-d", help="Show extra details."
    ),
    tree: bool = typer.Option(
        False, "--tree", "-t", help="Show recursive directory tree."
    ),
):
    """List directory contents (optionally detailed or as a tree)."""
    typer.echo(list_items(path, detailed, tree))


@app.command("create")
def cmd_create_item(
    item_type: str = typer.Argument(..., help="'file' or 'folder'"),
    path: str = typer.Argument(..., help="Path to create."),
):
    """Create a new file or directory."""
    typer.echo(create_item(item_type, path))


@app.command("rename")
def cmd_rename_item(
    source: str = typer.Argument(
        ..., help="Source file/folder or directory for batch rename."
    ),
    destination: str = typer.Option(
        None, "--dest", "-d", help="Destination path for single rename."
    ),
    pattern: str = typer.Option(
        None, "--pattern", "-p", help="Regex pattern for batch rename."
    ),
    replacement: str = typer.Option(
        None, "--replacement", "-r", help="Replacement string for batch rename."
    ),
):
    """
    Rename an item or batch-rename items using regex.
    If --pattern and --replacement are provided, batch rename is performed in a directory.
    Otherwise, a single rename is attempted if --dest is given.
    """
    typer.echo(rename_item(source, destination, pattern, replacement))


@app.command("delete")
def cmd_delete_item(
    path: str = typer.Argument(..., help="Path to delete."),
    safe_delete: bool = typer.Option(
        True, "--safe/--force", help="Use trash (safe) or permanently delete (force)."
    ),
):
    """Delete a file or folder, optionally sending to trash first."""
    typer.echo(delete_item(path, safe_delete=safe_delete))


@app.command("move")
def cmd_move_item(
    source: str = typer.Argument(..., help="Source path."),
    destination: str = typer.Argument(..., help="Destination path."),
):
    """Move a file or folder from source to destination."""
    typer.echo(move_item(source, destination))


@app.command("copy")
def cmd_copy_item(
    source: str = typer.Argument(..., help="Source path."),
    destination: str = typer.Argument(..., help="Destination path."),
):
    """Copy a file or folder from source to destination."""
    typer.echo(copy_item(source, destination))


@app.command("chmod")
def cmd_chmod_item(
    path: str = typer.Argument(..., help="Path to file/folder."),
    mode: str = typer.Argument(..., help="Octal permission (e.g. 755)."),
):
    """Change file or folder permissions in octal format."""
    typer.echo(chmod_item(path, mode))


@app.command("link")
def cmd_create_link(
    target: str = typer.Argument(..., help="Existing target path."),
    link_name: str = typer.Argument(..., help="Name/path of the link to create."),
    hard: bool = typer.Option(
        False, "--hard", "-h", help="Create a hard link instead of symlink."
    ),
):
    """Create a symbolic or hard link."""
    typer.echo(create_symlink(target, link_name, hard))


@app.command("compress")
def cmd_compress_items(
    paths: List[str] = typer.Argument(
        ..., help="Paths to compress (multiple values allowed)."
    ),
    archive_path: str = typer.Argument(..., help="Output archive path."),
    mode: str = typer.Option(
        "zip", "--mode", "-m", help="Compression mode: zip or tar."
    ),
):
    """Compress multiple files/folders into a single ZIP or TAR archive."""
    typer.echo(compress_items(paths, archive_path, mode))


@app.command("decompress")
def cmd_decompress_item(
    archive_path: str = typer.Argument(..., help="Archive file path."),
    extract_to: str = typer.Argument(".", help="Directory to extract files into."),
    mode: str = typer.Option(
        "zip", "--mode", "-m", help="Decompression mode: zip or tar."
    ),
):
    """Decompress a ZIP or TAR archive into the specified directory."""
    typer.echo(decompress_item(archive_path, extract_to, mode))


@app.command("checksum")
def cmd_generate_checksum(
    path: str = typer.Argument(..., help="File path for checksum."),
    algorithm: str = typer.Option(
        "md5", "--algo", "-a", help="Algorithm: md5, sha1, or sha256."
    ),
):
    """Generate a file checksum (MD5, SHA1, or SHA256)."""
    typer.echo(generate_checksum(path, algorithm))


@app.command("ftp")
def cmd_ftp_transfer(
    server: str = typer.Argument(..., help="FTP server address."),
    port: int = typer.Option(21, "--port", "-P", help="FTP port, default=21."),
    username: str = typer.Option(..., "--user", "-u", help="FTP username."),
    password: str = typer.Option(
        ..., "--pass", "-p", help="FTP password.", prompt=True, hide_input=True
    ),
    local_path: str = typer.Argument(..., help="Local file path."),
    remote_path: str = typer.Argument(..., help="Remote file path."),
    upload: bool = typer.Option(
        True, "--upload/--download", help="Upload or download?"
    ),
):
    """Transfer files via FTP."""
    typer.echo(
        ftp_transfer(server, port, username, password, local_path, remote_path, upload)
    )


@app.command("sftp")
def cmd_sftp_transfer(
    server: str = typer.Argument(..., help="SFTP server address."),
    port: int = typer.Option(22, "--port", "-P", help="SFTP port, default=22."),
    username: str = typer.Option(..., "--user", "-u", help="SFTP username."),
    password: str = typer.Option(
        ..., "--pass", "-p", help="SFTP password.", prompt=True, hide_input=True
    ),
    local_path: str = typer.Argument(..., help="Local file path."),
    remote_path: str = typer.Argument(..., help="Remote file path."),
    upload: bool = typer.Option(
        True, "--upload/--download", help="Upload or download?"
    ),
):
    """Transfer files via SFTP (secure) using Paramiko."""
    typer.echo(
        sftp_transfer(server, port, username, password, local_path, remote_path, upload)
    )


@app.command("preview")
def cmd_preview_file(
    path: str = typer.Argument(..., help="Path to a text file."),
    max_lines: int = typer.Option(
        20, "--max-lines", "-m", help="Number of lines to preview."
    ),
):
    """Show the first N lines of a text file."""
    typer.echo(preview_file(path, max_lines))


@app.command("search")
def cmd_search_files(
    directory: str = typer.Argument(".", help="Directory to search."),
    pattern: str = typer.Argument("*.txt", help="Glob or regex pattern."),
    use_regex: bool = typer.Option(
        False, "--regex", "-r", help="Treat pattern as a regex."
    ),
):
    """Search for files using a glob or regex pattern."""
    typer.echo(search_files(directory, pattern, use_regex))


##############################################################################
# 3. Optional Interactive Mode
##############################################################################


@app.command("interactive")
def interactive():
    """
    Launch an interactive menu-driven CLI in the terminal.
    Users can select operations step by step.
    """
    while True:
        typer.echo("\n=== file-commander (Typer Edition) ===")
        typer.echo("1. List directory contents")
        typer.echo("2. Create file/folder")
        typer.echo("3. Rename item(s)")
        typer.echo("4. Delete item")
        typer.echo("5. Move item")
        typer.echo("6. Copy item")
        typer.echo("7. Change permissions (chmod)")
        typer.echo("8. Create link (symbolic/hard)")
        typer.echo("9. Compress items (ZIP/TAR)")
        typer.echo("10. Decompress archive (ZIP/TAR)")
        typer.echo("11. Generate checksum (MD5/SHA1/SHA256)")
        typer.echo("12. FTP transfer")
        typer.echo("13. SFTP transfer")
        typer.echo("14. Preview text file")
        typer.echo("15. Search files")
        typer.echo("0. Exit")

        choice = typer.prompt("\nChoose an operation")

        if choice == "1":
            path = typer.prompt("Path to list", default=".")
            detailed = typer.confirm("Detailed listing?", default=False)
            tree = typer.confirm("Tree view?", default=False)
            typer.echo(list_items(path, detailed, tree))

        elif choice == "2":
            item_type = typer.prompt("Item type (file/folder)", default="file")
            path = typer.prompt("Path to create", default="./new_file.txt")
            typer.echo(create_item(item_type, path))

        elif choice == "3":
            src = typer.prompt("Source path")
            batch = typer.confirm("Batch rename using regex?", default=False)
            if batch:
                pattern = typer.prompt("Regex pattern")
                replacement = typer.prompt("Replacement string", default="")
                typer.echo(rename_item(src, pattern=pattern, replacement=replacement))
            else:
                dest = typer.prompt("Destination path")
                typer.echo(rename_item(src, destination=dest))

        elif choice == "4":
            path = typer.prompt("Path to delete")
            safe = typer.confirm("Safe delete (to trash)?", default=True)
            typer.echo(delete_item(path, safe_delete=safe))

        elif choice == "5":
            src = typer.prompt("Source path")
            dst = typer.prompt("Destination path")
            typer.echo(move_item(src, dst))

        elif choice == "6":
            src = typer.prompt("Source path")
            dst = typer.prompt("Destination path")
            typer.echo(copy_item(src, dst))

        elif choice == "7":
            path = typer.prompt("Path")
            mode_str = typer.prompt("Octal permission (e.g. 755)", default="755")
            typer.echo(chmod_item(path, mode_str))

        elif choice == "8":
            target = typer.prompt("Target path")
            link_name = typer.prompt("Link name/path")
            hard = typer.confirm("Hard link?", default=False)
            typer.echo(create_symlink(target, link_name, hard=hard))

        elif choice == "9":
            items_raw = typer.prompt("Items to compress (comma-separated)")
            items = [item.strip() for item in items_raw.split(",") if item.strip()]
            archive = typer.prompt(
                "Output archive path (e.g. archive.zip)", default="archive.zip"
            )
            mode = typer.prompt("Mode (zip/tar)", default="zip")
            typer.echo(compress_items(items, archive, mode))

        elif choice == "10":
            archive = typer.prompt("Archive path")
            extract_to = typer.prompt("Extract to directory", default=".")
            mode = typer.prompt("Mode (zip/tar)", default="zip")
            typer.echo(decompress_item(archive, extract_to, mode))

        elif choice == "11":
            fpath = typer.prompt("File path")
            algo = typer.prompt("Algorithm (md5/sha1/sha256)", default="md5")
            typer.echo(generate_checksum(fpath, algo))

        elif choice == "12":
            server = typer.prompt("FTP server")
            port = typer.prompt("FTP port", default="21")
            username = typer.prompt("Username")
            password = typer.prompt("Password", hide_input=True)
            local = typer.prompt("Local file path")
            remote = typer.prompt("Remote path")
            up = typer.confirm("Upload?", default=True)
            try:
                port_int = int(port)
            except ValueError:
                port_int = 21
            typer.echo(
                ftp_transfer(server, port_int, username, password, local, remote, up)
            )

        elif choice == "13":
            server = typer.prompt("SFTP server")
            port = typer.prompt("SFTP port", default="22")
            username = typer.prompt("Username")
            password = typer.prompt("Password", hide_input=True)
            local = typer.prompt("Local file path")
            remote = typer.prompt("Remote path")
            up = typer.confirm("Upload?", default=True)
            try:
                port_int = int(port)
            except ValueError:
                port_int = 22
            typer.echo(
                sftp_transfer(server, port_int, username, password, local, remote, up)
            )

        elif choice == "14":
            fpath = typer.prompt("File path")
            lines_str = typer.prompt("Max lines", default="20")
            try:
                max_lines = int(lines_str)
            except ValueError:
                max_lines = 20
            typer.echo(preview_file(fpath, max_lines))

        elif choice == "15":
            directory = typer.prompt("Directory to search", default=".")
            pattern = typer.prompt("Pattern (glob/regex)", default="*.txt")
            regex = typer.confirm("Use regex?", default=False)
            typer.echo(search_files(directory, pattern, regex))

        elif choice == "0":
            typer.echo("Exiting interactive mode.")
            break

        else:
            typer.echo("Invalid choice. Please try again.")


def main():
    """
    Entry point for file_commander_typer.py.
    """
    app()


if __name__ == "__main__":
    main()
