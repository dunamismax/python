#!/usr/bin/env python3

"""
file_commander_textual.py

A cross-platform TUI-driven file operations utility rewritten in Textual.
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

# Third-party imports (make sure they're installed)
from send2trash import send2trash
import paramiko
from tqdm import tqdm

# Textual imports
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container, ScrollableContainer
from textual.widgets import (
    Header,
    Footer,
    Static,
    Button,
    Input,
    ListView,
    ListItem,
    Label,
    TextLog,
    DataTable,
    Tree,
    TreeNode,
    SelectionList,
    RadioSet,
    RadioButton,
)
from textual.reactive import reactive
from textual.screen import Screen
from textual.message import Message
from textual.message_pump import MessagePump
from textual.widgets._header import HeaderTitle  # just for advanced usage

# ---------------------------------------------------------------------
# 1. Helper Functions (adapted from your original script)
# ---------------------------------------------------------------------


def list_items(path, detailed=False, tree=False):
    """
    List files/directories under path.
    Returns text output (string) suitable for printing in Textual, or an error.
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
                    f"{entry.name:<30} {ftype:<5} {size:>10} bytes  {mtime.strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
            else:
                buf.write(f"{entry.name}\n")

    return buf.getvalue()


def create_item(item_type, path):
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


def rename_item(source, destination=None, pattern=None, replacement=None):
    """
    Rename or batch-rename items.
    Returns a string with status.
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
    else:
        # Batch rename within a directory
        if not src_path.is_dir():
            return f"[ERROR] '{src_path}' must be a directory for batch rename."
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
                    return f"[ERROR] Could not rename '{child.name}': {e}"
        return f"[OK] Batch-renamed {count} items in '{src_path}'."


def delete_item(path, safe_delete=True):
    """
    Delete a file or folder with optional trash usage.
    Returns a string result.
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


def move_item(source, destination):
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


def copy_item(source, destination):
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


def chmod_item(path, mode_str):
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


def create_symlink(target, link_name, hard=False):
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


def compress_items(paths, archive_path, mode="zip"):
    """
    Compress multiple items into an archive.
    Returns a result string.
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


def decompress_item(archive_path, extract_to, mode="zip"):
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


def generate_checksum(path, algorithm="md5"):
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
    server, port, username, password, local_path, remote_path, upload=True
):
    """
    Simple FTP file transfer using ftplib.
    """
    local_path = Path(local_path).resolve()
    if upload and (not local_path.exists() or not local_path.is_file()):
        return f"[ERROR] Local file '{local_path}' does not exist for upload."

    try:
        with ftplib.FTP() as ftp:
            ftp.connect(server, port)
            ftp.login(username, password)
            if upload:
                with open(local_path, "rb") as f:
                    ftp.storbinary(f"STOR {remote_path}", f)
                return f"[OK] Uploaded '{local_path}' to '{server}:{remote_path}'"
            else:
                with open(local_path, "wb") as f:
                    ftp.retrbinary(f"RETR {remote_path}", f.write)
                return f"[OK] Downloaded '{server}:{remote_path}' to '{local_path}'"
    except Exception as e:
        return f"[ERROR] FTP transfer failed: {e}"


def sftp_transfer(
    server, port, username, password, local_path, remote_path, upload=True
):
    """
    Secure SFTP file transfer using Paramiko.
    """
    local_path = Path(local_path).resolve()
    if upload and (not local_path.exists() or not local_path.is_file()):
        return f"[ERROR] Local file '{local_path}' does not exist for upload."

    try:
        transport = paramiko.Transport((server, port))
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)

        if upload:
            sftp.put(str(local_path), remote_path)
            result = f"[OK] SFTP uploaded '{local_path}' -> '{server}:{remote_path}'"
        else:
            sftp.get(remote_path, str(local_path))
            result = f"[OK] SFTP downloaded '{server}:{remote_path}' -> '{local_path}'"

        sftp.close()
        transport.close()
        return result
    except Exception as e:
        return f"[ERROR] SFTP transfer failed: {e}"


def preview_file(path, max_lines=20):
    """
    Return the first `max_lines` lines of a text file as a string.
    """
    p = Path(path).resolve()
    if not p.is_file():
        return f"[ERROR] '{p}' is not a valid file."

    try:
        with p.open("r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        result = []
        result.append(f"--- Preview of {p} (first {max_lines} lines) ---\n")
        for line in lines[:max_lines]:
            result.append(line)
        if len(lines) > max_lines:
            result.append(
                f"\n--- File truncated. {len(lines) - max_lines} lines not shown. ---\n"
            )
        return "".join(result)
    except Exception as e:
        return f"[ERROR] Could not preview file: {e}"


def search_files(directory, pattern, use_regex=False):
    """
    Search for files by glob or regex pattern.
    Returns matching paths as a string.
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


# ---------------------------------------------------------------------
# 2. Textual Screens & App
# ---------------------------------------------------------------------


class MainMenu(Screen):
    """
    Main menu screen with a ListView of operations.
    When a user selects an operation, we transition to another screen.
    """

    BINDINGS = [
        ("q", "quit_app", "Quit"),
        ("b", "pop_screen", "Go Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Static(
            "=== file-commander Main Menu ===",
            id="main-menu-title",
            classes="bold underline",
        )
        menu_list = ListView(
            ListItem(Label("1. List directory contents"), id="menu-list"),
            ListItem(Label("2. Create file/folder"), id="menu-create"),
            ListItem(Label("3. Rename file/folder"), id="menu-rename"),
            ListItem(Label("4. Delete file/folder"), id="menu-delete"),
            ListItem(Label("5. Move file/folder"), id="menu-move"),
            ListItem(Label("6. Copy file/folder"), id="menu-copy"),
            ListItem(Label("7. Change permissions"), id="menu-chmod"),
            ListItem(Label("8. Create link"), id="menu-link"),
            ListItem(Label("9. Compress items"), id="menu-compress"),
            ListItem(Label("10. Decompress archive"), id="menu-decompress"),
            ListItem(Label("11. Generate checksum"), id="menu-checksum"),
            ListItem(Label("12. FTP transfer"), id="menu-ftp"),
            ListItem(Label("13. SFTP transfer"), id="menu-sftp"),
            ListItem(Label("14. Preview text file"), id="menu-preview"),
            ListItem(Label("15. Search files"), id="menu-search"),
            ListItem(Label("0. Exit"), id="menu-exit"),
        )
        yield menu_list

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """
        Handle menu selection by ID.
        """
        selected_id = event.item.id
        if selected_id == "menu-list":
            self.app.push_screen(ListDirScreen())
        elif selected_id == "menu-create":
            self.app.push_screen(CreateItemScreen())
        elif selected_id == "menu-rename":
            self.app.push_screen(RenameItemScreen())
        elif selected_id == "menu-delete":
            self.app.push_screen(DeleteItemScreen())
        elif selected_id == "menu-move":
            self.app.push_screen(MoveItemScreen())
        elif selected_id == "menu-copy":
            self.app.push_screen(CopyItemScreen())
        elif selected_id == "menu-chmod":
            self.app.push_screen(ChmodItemScreen())
        elif selected_id == "menu-link":
            self.app.push_screen(LinkItemScreen())
        elif selected_id == "menu-compress":
            self.app.push_screen(CompressItemsScreen())
        elif selected_id == "menu-decompress":
            self.app.push_screen(DecompressItemsScreen())
        elif selected_id == "menu-checksum":
            self.app.push_screen(ChecksumScreen())
        elif selected_id == "menu-ftp":
            self.app.push_screen(FtpScreen())
        elif selected_id == "menu-sftp":
            self.app.push_screen(SftpScreen())
        elif selected_id == "menu-preview":
            self.app.push_screen(PreviewScreen())
        elif selected_id == "menu-search":
            self.app.push_screen(SearchFilesScreen())
        elif selected_id == "menu-exit":
            self.app.exit()


class BaseOperationScreen(Screen):
    """
    A base screen for simple input -> output flow.
    Subclasses should override `title` and `perform_operation()` as needed.
    """

    title = "Operation"

    def compose(self) -> ComposeResult:
        yield Static(self.title, classes="bold underline")
        yield self.operation_form()
        yield Button(label="Run", id="run-op", variant="success")
        yield Button(label="Back", id="back-op", variant="primary")
        yield TextLog(id="output-log", highlight=True)

    def operation_form(self):
        """
        Subclasses should return a Container (or similar) with Input fields, etc.
        """
        return Container(Static("Override operation_form() in subclass."))

    def perform_operation(self) -> str:
        """
        Subclasses implement their logic here, returning a result string.
        """
        return "[ERROR] Operation not implemented."

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run-op":
            output_widget = self.query_one("#output-log", TextLog)
            result = self.perform_operation()
            output_widget.write(result)
        elif event.button.id == "back-op":
            self.app.pop_screen()


# Below are a few examples of specific operations.
# Each is a Screen that collects the required input and calls the helper functions.


class ListDirScreen(BaseOperationScreen):
    title = "List Directory Contents"

    def operation_form(self):
        return Vertical(
            Static("Path:", classes="label"),
            Input(placeholder=".", id="path-input"),
            Static("Detailed? (y/n):", classes="label"),
            Input(placeholder="n", id="detailed-input"),
            Static("Tree? (y/n):", classes="label"),
            Input(placeholder="n", id="tree-input"),
        )

    def perform_operation(self) -> str:
        path = self.query_one("#path-input", Input).value or "."
        detailed_str = self.query_one("#detailed-input", Input).value or "n"
        tree_str = self.query_one("#tree-input", Input).value or "n"
        detailed = detailed_str.lower() == "y"
        tree = tree_str.lower() == "y"
        return list_items(path, detailed, tree)


class CreateItemScreen(BaseOperationScreen):
    title = "Create File/Folder"

    def operation_form(self):
        return Vertical(
            Static("Item type (file/folder):", classes="label"),
            Input(placeholder="file", id="type-input"),
            Static("Path to create:", classes="label"),
            Input(placeholder="./new_file.txt", id="path-input"),
        )

    def perform_operation(self):
        item_type = self.query_one("#type-input", Input).value or "file"
        path = self.query_one("#path-input", Input).value or "./new_file.txt"
        return create_item(item_type, path)


class RenameItemScreen(BaseOperationScreen):
    title = "Rename/Bulk Rename"

    def operation_form(self):
        return Vertical(
            Static("Source path:", classes="label"),
            Input(id="src-input"),
            Static(
                "Destination (for single) or leave blank for batch:", classes="label"
            ),
            Input(id="dest-input"),
            Static("Regex pattern (for batch) or leave blank:", classes="label"),
            Input(id="pattern-input"),
            Static("Replacement (for batch) or leave blank:", classes="label"),
            Input(id="replace-input"),
        )

    def perform_operation(self):
        src = self.query_one("#src-input", Input).value
        dest = self.query_one("#dest-input", Input).value
        pat = self.query_one("#pattern-input", Input).value
        rep = self.query_one("#replace-input", Input).value

        if pat and rep:
            return rename_item(src, pattern=pat, replacement=rep)
        else:
            return rename_item(src, destination=dest)


class DeleteItemScreen(BaseOperationScreen):
    title = "Delete File/Folder"

    def operation_form(self):
        return Vertical(
            Static("Path to delete:", classes="label"),
            Input(id="path-input"),
            Static("Safe delete to trash? (y/n):", classes="label"),
            Input(placeholder="y", id="safe-input"),
        )

    def perform_operation(self):
        path = self.query_one("#path-input", Input).value
        safe_str = self.query_one("#safe-input", Input).value or "y"
        safe = safe_str.lower() == "y"
        return delete_item(path, safe_delete=safe)


class MoveItemScreen(BaseOperationScreen):
    title = "Move File/Folder"

    def operation_form(self):
        return Vertical(
            Static("Source path:", classes="label"),
            Input(id="src-input"),
            Static("Destination path:", classes="label"),
            Input(id="dst-input"),
        )

    def perform_operation(self):
        src = self.query_one("#src-input", Input).value
        dst = self.query_one("#dst-input", Input).value
        return move_item(src, dst)


class CopyItemScreen(BaseOperationScreen):
    title = "Copy File/Folder"

    def operation_form(self):
        return Vertical(
            Static("Source path:", classes="label"),
            Input(id="src-input"),
            Static("Destination path:", classes="label"),
            Input(id="dst-input"),
        )

    def perform_operation(self):
        src = self.query_one("#src-input", Input).value
        dst = self.query_one("#dst-input", Input).value
        return copy_item(src, dst)


class ChmodItemScreen(BaseOperationScreen):
    title = "Change Permissions"

    def operation_form(self):
        return Vertical(
            Static("Path:", classes="label"),
            Input(id="path-input"),
            Static("Octal permission (e.g. 755):", classes="label"),
            Input(id="mode-input"),
        )

    def perform_operation(self):
        path = self.query_one("#path-input", Input).value
        mode_str = self.query_one("#mode-input", Input).value or "755"
        return chmod_item(path, mode_str)


class LinkItemScreen(BaseOperationScreen):
    title = "Create Link (Symbolic/Hard)"

    def operation_form(self):
        return Vertical(
            Static("Target path:", classes="label"),
            Input(id="target-input"),
            Static("Link name/path:", classes="label"),
            Input(id="link-input"),
            Static("Hard link? (y/n):", classes="label"),
            Input(placeholder="n", id="hard-input"),
        )

    def perform_operation(self):
        target = self.query_one("#target-input", Input).value
        link_path = self.query_one("#link-input", Input).value
        hard_str = self.query_one("#hard-input", Input).value or "n"
        hard = hard_str.lower() == "y"
        return create_symlink(target, link_path, hard=hard)


class CompressItemsScreen(BaseOperationScreen):
    title = "Compress (ZIP/TAR)"

    def operation_form(self):
        return Vertical(
            Static("Items to compress (comma-separated):", classes="label"),
            Input(id="items-input"),
            Static("Archive path (e.g. archive.zip):", classes="label"),
            Input(id="archive-input"),
            Static("Mode (zip/tar):", classes="label"),
            Input(placeholder="zip", id="mode-input"),
        )

    def perform_operation(self):
        items_raw = self.query_one("#items-input", Input).value
        items = [item.strip() for item in items_raw.split(",") if item.strip()]
        archive = self.query_one("#archive-input", Input).value
        mode = self.query_one("#mode-input", Input).value or "zip"
        return compress_items(items, archive, mode)


class DecompressItemsScreen(BaseOperationScreen):
    title = "Decompress (ZIP/TAR)"

    def operation_form(self):
        return Vertical(
            Static("Archive path:", classes="label"),
            Input(id="archive-input"),
            Static("Extract to directory:", classes="label"),
            Input(placeholder=".", id="extract-input"),
            Static("Mode (zip/tar):", classes="label"),
            Input(placeholder="zip", id="mode-input"),
        )

    def perform_operation(self):
        archive = self.query_one("#archive-input", Input).value
        extract_to = self.query_one("#extract-input", Input).value or "."
        mode = self.query_one("#mode-input", Input).value or "zip"
        return decompress_item(archive, extract_to, mode)


class ChecksumScreen(BaseOperationScreen):
    title = "Generate Checksum (MD5/SHA1/SHA256)"

    def operation_form(self):
        return Vertical(
            Static("File path:", classes="label"),
            Input(id="file-input"),
            Static("Algorithm (md5/sha1/sha256):", classes="label"),
            Input(placeholder="md5", id="algo-input"),
        )

    def perform_operation(self):
        fpath = self.query_one("#file-input", Input).value
        algo = self.query_one("#algo-input", Input).value or "md5"
        return generate_checksum(fpath, algo)


class FtpScreen(BaseOperationScreen):
    title = "FTP Transfer"

    def operation_form(self):
        return Vertical(
            Static("FTP server:", classes="label"),
            Input(id="server-input"),
            Static("Port:", classes="label"),
            Input(placeholder="21", id="port-input"),
            Static("Username:", classes="label"),
            Input(id="user-input"),
            Static("Password:", classes="label"),
            Input(password=True, id="pass-input"),
            Static("Local file path:", classes="label"),
            Input(id="local-input"),
            Static("Remote path:", classes="label"),
            Input(id="remote-input"),
            Static("Upload? (y/n):", classes="label"),
            Input(placeholder="y", id="upload-input"),
        )

    def perform_operation(self):
        server = self.query_one("#server-input", Input).value
        port_str = self.query_one("#port-input", Input).value or "21"
        username = self.query_one("#user-input", Input).value
        password = self.query_one("#pass-input", Input).value
        local = self.query_one("#local-input", Input).value
        remote = self.query_one("#remote-input", Input).value
        upload_str = self.query_one("#upload-input", Input).value or "y"

        try:
            port = int(port_str)
        except ValueError:
            port = 21

        upload = upload_str.lower() == "y"
        return ftp_transfer(server, port, username, password, local, remote, upload)


class SftpScreen(BaseOperationScreen):
    title = "SFTP Transfer"

    def operation_form(self):
        return Vertical(
            Static("SFTP server:", classes="label"),
            Input(id="server-input"),
            Static("Port:", classes="label"),
            Input(placeholder="22", id="port-input"),
            Static("Username:", classes="label"),
            Input(id="user-input"),
            Static("Password:", classes="label"),
            Input(password=True, id="pass-input"),
            Static("Local file path:", classes="label"),
            Input(id="local-input"),
            Static("Remote path:", classes="label"),
            Input(id="remote-input"),
            Static("Upload? (y/n):", classes="label"),
            Input(placeholder="y", id="upload-input"),
        )

    def perform_operation(self):
        server = self.query_one("#server-input", Input).value
        port_str = self.query_one("#port-input", Input).value or "22"
        username = self.query_one("#user-input", Input).value
        password = self.query_one("#pass-input", Input).value
        local = self.query_one("#local-input", Input).value
        remote = self.query_one("#remote-input", Input).value
        upload_str = self.query_one("#upload-input", Input).value or "y"

        try:
            port = int(port_str)
        except ValueError:
            port = 22

        upload = upload_str.lower() == "y"
        return sftp_transfer(server, port, username, password, local, remote, upload)


class PreviewScreen(BaseOperationScreen):
    title = "Preview Text File"

    def operation_form(self):
        return Vertical(
            Static("File path:", classes="label"),
            Input(id="file-input"),
            Static("Max lines:", classes="label"),
            Input(placeholder="20", id="lines-input"),
        )

    def perform_operation(self):
        fpath = self.query_one("#file-input", Input).value
        lines_str = self.query_one("#lines-input", Input).value or "20"
        try:
            max_lines = int(lines_str)
        except ValueError:
            max_lines = 20
        return preview_file(fpath, max_lines)


class SearchFilesScreen(BaseOperationScreen):
    title = "Search Files (Glob or Regex)"

    def operation_form(self):
        return Vertical(
            Static("Directory to search:", classes="label"),
            Input(placeholder=".", id="dir-input"),
            Static("Pattern (glob/regex):", classes="label"),
            Input(placeholder="*.txt", id="pattern-input"),
            Static("Use regex? (y/n):", classes="label"),
            Input(placeholder="n", id="regex-input"),
        )

    def perform_operation(self):
        directory = self.query_one("#dir-input", Input).value or "."
        pattern = self.query_one("#pattern-input", Input).value or "*.txt"
        regex_str = self.query_one("#regex-input", Input).value or "n"
        use_regex = regex_str.lower() == "y"
        return search_files(directory, pattern, use_regex)


# ---------------------------------------------------------------------
# 3. The Main App
# ---------------------------------------------------------------------


class FileCommander(App):

    CSS = """
    Screen {
        padding: 1 2;
    }
    #main-menu-title {
        margin-bottom: 1;
    }
    .label {
        margin-top: 1;
    }
    #output-log {
        margin-top: 1;
        height: 10;
    }
    """

    TITLE = "file-commander (Textual Edition)"
    SUB_TITLE = "A cross-platform TUI for file operations"

    def on_ready(self) -> None:
        # Immediately show the main menu
        self.push_screen(MainMenu())

    def action_quit_app(self):
        self.exit()


def main():
    app = FileCommander()
    app.run()


if __name__ == "__main__":
    main()
