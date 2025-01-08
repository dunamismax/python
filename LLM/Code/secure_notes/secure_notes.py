#!/usr/bin/env python3
"""
secure_notes.py
---------------
A production-ready encrypted notes application in Python using Typer (for CLI),
Rich (for styled console output), and curses (for interactive TUI).

Features:
- Asks for an encryption password upon first command usage or TUI start.
- Encrypted notes file with AES 128-bit encryption via cryptography (Fernet).
- Password-based key derivation (PBKDF2).
- Full CLI usage with Typer + Rich formatting.
- Optional interactive TUI via curses (launched by default with no arguments, or `tui` command).
- Demonstrates best practices for Python CLI/TUI design.

Usage:
    # Basic CLI usage (lists notes)
    python secure_notes.py list

    # Create a new note
    python secure_notes.py create --title "My Title" --content "Hello world!"

    # View an existing note (by index)
    python secure_notes.py view 0

    # Edit a note
    python secure_notes.py edit 0 --new-title "Updated Title"

    # Launch the curses TUI (also the default if no arguments provided)
    python secure_notes.py tui
"""

import os
import json
import base64
import hashlib
import secrets
import curses
import time
from typing import List, Dict, Optional

import typer
from typer import Option, Argument, Context
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet, InvalidToken

from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.panel import Panel

# ---------------------------------------------------------------------------
# Constants and configuration
# ---------------------------------------------------------------------------

app = typer.Typer(help="Secure Notes - Encrypted notes CLI & TUI application.")
console = Console()

DEFAULT_ENC_FILE = "secure_notes.enc"
PBKDF2_ITERATIONS = 200_000  # Reasonable PBKDF2 iteration count

# Global state (populated once the user provides a password)
NOTES: List[Dict[str, str]] = []
PASSWORD: Optional[str] = None


# ---------------------------------------------------------------------------
# Encryption & decryption helpers
# ---------------------------------------------------------------------------


def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """
    Derive a Fernet-compatible key from a user-provided password and salt.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    key = kdf.derive(password.encode("utf-8"))
    return base64.urlsafe_b64encode(key)


def encrypt_data(plaintext: bytes, fernet: Fernet) -> bytes:
    """Encrypt the given plaintext using the provided Fernet object."""
    return fernet.encrypt(plaintext)


def decrypt_data(ciphertext: bytes, fernet: Fernet) -> bytes:
    """Decrypt the given ciphertext using the provided Fernet object."""
    return fernet.decrypt(ciphertext)


def load_notes_file(
    password: str, filename: str = DEFAULT_ENC_FILE
) -> List[Dict[str, str]]:
    """
    Load notes from an encrypted file. If file doesn't exist, return an empty list.
    If the file is corrupted or the password is incorrect, raise InvalidToken.
    """
    if not os.path.isfile(filename):
        # File doesn't exist -> treat as new/empty
        return []

    with open(filename, "rb") as f:
        raw_data = f.read()

    # The first 16 bytes are the salt; the rest is the encrypted notes.
    salt, encrypted_notes = raw_data[:16], raw_data[16:]
    fernet = Fernet(derive_key_from_password(password, salt))

    try:
        decrypted = decrypt_data(encrypted_notes, fernet)
        data = json.loads(decrypted.decode("utf-8"))
        return data.get("notes", [])
    except InvalidToken:
        raise InvalidToken("Incorrect password or corrupted file.")


def save_notes_file(
    password: str, notes: List[Dict[str, str]], filename: str = DEFAULT_ENC_FILE
) -> None:
    """
    Save notes to an encrypted file. Generates a salt if none exists, or uses
    the existing file's salt to keep the same password valid.
    """
    if os.path.isfile(filename):
        with open(filename, "rb") as f:
            old_data = f.read()
        salt = old_data[:16]
    else:
        salt = secrets.token_bytes(16)  # 16 bytes of salt

    fernet = Fernet(derive_key_from_password(password, salt))
    data_to_store = {"notes": notes}
    encrypted_notes = encrypt_data(json.dumps(data_to_store).encode("utf-8"), fernet)

    with open(filename, "wb") as f:
        f.write(salt + encrypted_notes)


# ---------------------------------------------------------------------------
# Password handling & lazy-loading
# ---------------------------------------------------------------------------


def ensure_password_loaded() -> None:
    """
    Ensure a global password is set. If not, prompt the user (hide input).
    Then load the global NOTES from file.
    """
    global PASSWORD, NOTES

    if PASSWORD is not None:
        return

    console.print(Panel("[bold magenta]Welcome to Secure Notes![/bold magenta]"))
    PASSWORD = Prompt.ask(
        "[bold green]Please enter your encryption password[/bold green]", password=True
    )

    try:
        NOTES = load_notes_file(PASSWORD, DEFAULT_ENC_FILE)
        console.print("[green]Notes loaded successfully.[/green]")
    except InvalidToken as e:
        console.print(f"[red]{e} Exiting...[/red]")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# CLI / TUI Dual-Mode Logic
# ---------------------------------------------------------------------------


@app.callback(invoke_without_command=True)
def main(ctx: Context):
    """
    If no subcommand is provided, automatically launch the TUI.
    """
    if ctx.invoked_subcommand is None:
        ensure_password_loaded()
        curses.wrapper(_run_tui)
        raise typer.Exit()


# ---------------------------------------------------------------------------
# CLI Commands (Rich-formatted)
# ---------------------------------------------------------------------------


@app.command()
def tui() -> None:
    """
    Explicit command to launch the interactive curses-based TUI.
    """
    ensure_password_loaded()
    curses.wrapper(_run_tui)


@app.command()
def list():
    """
    List all notes in the encrypted file (by index).
    """
    ensure_password_loaded()
    if not NOTES:
        console.print("[yellow]No notes found.[/yellow]")
        raise typer.Exit()

    console.print(Panel("[bold blue]Your Secure Notes[/bold blue]"))
    for idx, note in enumerate(NOTES):
        title = note["title"] or f"Untitled (#{idx})"
        console.print(f"[cyan]{idx}[/cyan]: [bold]{title}[/bold]")


@app.command()
def create(
    title: str = Option("", "--title", "-t", help="Title of the note"),
    content: str = Option("", "--content", "-c", help="Content of the note"),
):
    """
    Create a new note. Title and content can be passed as options,
    or if empty, you'll be prompted interactively.
    """
    ensure_password_loaded()

    final_title = title or Prompt.ask("[bold cyan]Note Title[/bold cyan]", default="")
    console.print(
        "[bold cyan]Note Content[/bold cyan] (Enter your text below; press CTRL+D or CTRL+Z to finish):"
    )
    final_content = content or _read_multiline_input()

    NOTES.append({"title": final_title, "content": final_content})
    save_notes_file(PASSWORD, NOTES, DEFAULT_ENC_FILE)
    console.print("[green]New note saved successfully![/green]")


@app.command()
def view(idx: int = Argument(..., help="Index of the note to view")):
    """
    View a note by its index.
    """
    ensure_password_loaded()
    if idx < 0 or idx >= len(NOTES):
        console.print("[red]Invalid note index.[/red]")
        raise typer.Exit(code=1)

    selected_note = NOTES[idx]
    title = selected_note["title"]
    content = selected_note["content"]

    console.print(Panel(f"[bold]Note {idx}[/bold]", style="blue"))
    console.print(f"[bold]Title:[/bold] {title}")
    console.print(Markdown("---"))
    console.print(content)


@app.command()
def edit(
    idx: int = Argument(..., help="Index of the note to edit"),
    new_title: str = Option(None, "--new-title", "-nt", help="New title of the note"),
    new_content: str = Option(
        None, "--new-content", "-nc", help="New content of the note"
    ),
):
    """
    Edit an existing note by its index.
    """
    ensure_password_loaded()
    if idx < 0 or idx >= len(NOTES):
        console.print("[red]Invalid note index.[/red]")
        raise typer.Exit(code=1)

    current_title = NOTES[idx]["title"]
    current_content = NOTES[idx]["content"]

    # If user didn't provide new_title/new_content on the CLI, prompt interactively
    console.print(f"[bold cyan]Current Title:[/bold cyan] {current_title}")
    final_title = new_title or Prompt.ask(
        "New Title (press ENTER to keep current)", default=current_title
    )

    console.print(f"[bold cyan]Current Content:[/bold cyan]\n{current_content}")
    console.print("Enter new content below; press CTRL+D or CTRL+Z to finish.")
    final_content = new_content or _read_multiline_input(default=current_content)

    NOTES[idx] = {"title": final_title, "content": final_content}
    save_notes_file(PASSWORD, NOTES, DEFAULT_ENC_FILE)
    console.print(f"[green]Note {idx} updated successfully![/green]")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_multiline_input(default: str = "") -> str:
    """
    Read multi-line input from the user until EOF (CTRL+D/CTRL+Z).
    Returns the input as a single string.
    """
    console.print("(Press CTRL+D or CTRL+Z on a new line to finish input)")

    lines = []
    if default:
        # If a default is provided, start the buffer with the default content
        lines = default.splitlines()

    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        # End of multiline input
        pass

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# curses-based TUI
# ---------------------------------------------------------------------------


def _run_tui(stdscr):
    """
    The main TUI loop, invoked by curses.wrapper().
    """
    global NOTES, PASSWORD

    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.keypad(True)

    if curses.has_colors():
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_MAGENTA, curses.COLOR_BLACK)

    # A simple TUI menu:
    while True:
        stdscr.clear()
        _render_title(stdscr, "Secure Notes TUI")

        stdscr.addstr(2, 0, "[1] List Notes", curses.color_pair(2))
        stdscr.addstr(3, 0, "[2] Create New Note", curses.color_pair(2))
        stdscr.addstr(4, 0, "[3] View Note by Index", curses.color_pair(2))
        stdscr.addstr(5, 0, "[4] Edit Note by Index", curses.color_pair(2))
        stdscr.addstr(6, 0, "[5] Quit", curses.color_pair(2))

        stdscr.addstr(8, 0, "Choose an action: ", curses.color_pair(3))
        stdscr.refresh()

        choice = stdscr.getch()
        if choice == ord("1"):
            _tui_list_notes(stdscr)
        elif choice == ord("2"):
            _tui_create_note(stdscr)
        elif choice == ord("3"):
            _tui_view_note(stdscr)
        elif choice == ord("4"):
            _tui_edit_note(stdscr)
        elif choice == ord("5"):
            break
        else:
            _tui_message(stdscr, "Invalid choice. Press a valid number key.")
            continue

    _tui_message(stdscr, "Goodbye! Press any key to exit.")
    stdscr.getch()


def _render_title(stdscr, title: str):
    """
    Renders a title at the top of the screen with optional color.
    """
    max_y, max_x = stdscr.getmaxyx()
    title_str = f"{title}".center(max_x)
    stdscr.addstr(0, 0, title_str, curses.color_pair(1) | curses.A_BOLD)


def _tui_message(stdscr, message: str):
    """
    Display a single-line message and wait for any key press.
    """
    stdscr.clear()
    max_y, max_x = stdscr.getmaxyx()
    msg_x = max_x // 2 - len(message) // 2
    msg_y = max_y // 2
    stdscr.addstr(msg_y, msg_x, message, curses.color_pair(1))
    stdscr.refresh()
    stdscr.getch()


def _tui_list_notes(stdscr):
    """
    List all notes in curses.
    """
    global NOTES
    stdscr.clear()
    _render_title(stdscr, "All Notes")

    if not NOTES:
        _tui_message(stdscr, "No notes found.")
        return

    max_y, max_x = stdscr.getmaxyx()
    for idx, note in enumerate(NOTES):
        line = f"{idx}: {note['title'] or f'Untitled ({idx})'}"
        stdscr.addstr(idx + 2, 2, line[: max_x - 4], curses.color_pair(2))
    stdscr.refresh()

    _tui_message(stdscr, "Press any key to continue.")


def _tui_create_note(stdscr):
    """
    Create a new note in curses mode.
    """
    global NOTES, PASSWORD
    title = _tui_input(stdscr, "Note Title (press ENTER for none):")
    content = _tui_input(stdscr, "Note Content (press ENTER for none):")

    NOTES.append({"title": title, "content": content})
    save_notes_file(PASSWORD, NOTES)
    _tui_message(stdscr, "New note saved successfully!")


def _tui_view_note(stdscr):
    """
    Prompt the user for an index in curses and display the note.
    """
    global NOTES
    if not NOTES:
        _tui_message(stdscr, "No notes to view.")
        return

    idx_str = _tui_input(stdscr, "Enter the note index to view:")
    try:
        idx = int(idx_str)
        if idx < 0 or idx >= len(NOTES):
            _tui_message(stdscr, "Invalid note index.")
            return
    except ValueError:
        _tui_message(stdscr, "Please enter a valid integer index.")
        return

    note = NOTES[idx]
    stdscr.clear()
    _render_title(stdscr, f"Note {idx}")

    max_y, max_x = stdscr.getmaxyx()
    stdscr.addstr(2, 2, f"Title: {note['title']}", curses.color_pair(2))
    stdscr.addstr(4, 2, "Content:", curses.color_pair(2))

    # Print multiline content with basic wrapping
    lines = note["content"].splitlines()
    row = 5
    for line in lines:
        for chunk in _wrap_text(line, max_x - 4):
            if row >= max_y - 2:
                break
            stdscr.addstr(row, 2, chunk, curses.color_pair(2))
            row += 1

    stdscr.refresh()
    _tui_message(stdscr, "Press any key to continue.")


def _tui_edit_note(stdscr):
    """
    Prompt the user for an index in curses and allow editing of the note.
    """
    global NOTES, PASSWORD
    if not NOTES:
        _tui_message(stdscr, "No notes to edit.")
        return

    idx_str = _tui_input(stdscr, "Enter the note index to edit:")
    try:
        idx = int(idx_str)
        if idx < 0 or idx >= len(NOTES):
            _tui_message(stdscr, "Invalid note index.")
            return
    except ValueError:
        _tui_message(stdscr, "Please enter a valid integer index.")
        return

    current_title = NOTES[idx]["title"]
    current_content = NOTES[idx]["content"]

    new_title = _tui_input(
        stdscr, f"New Title (leave blank to keep '{current_title}'):"
    )
    new_content = _tui_input(stdscr, "New Content (leave blank to keep current):")

    NOTES[idx]["title"] = new_title if new_title else current_title
    NOTES[idx]["content"] = new_content if new_content else current_content
    save_notes_file(PASSWORD, NOTES)
    _tui_message(stdscr, f"Note {idx} updated successfully!")


def _tui_input(stdscr, prompt_str: str) -> str:
    """
    Basic line input in curses for short fields (title, single-line content).
    """
    stdscr.clear()
    _render_title(stdscr, "Input Required")

    max_y, max_x = stdscr.getmaxyx()
    stdscr.addstr(2, 2, prompt_str, curses.color_pair(2))
    stdscr.refresh()

    curses.echo()
    input_str = stdscr.getstr(3, 2).decode("utf-8")
    curses.noecho()
    return input_str.strip()


def _wrap_text(line: str, width: int):
    """
    Simple text wrapper for curses, yielding chunks of up to 'width' characters.
    """
    for i in range(0, len(line), width):
        yield line[i : i + width]


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------


def run():
    """
    Entry point for our dual-mode CLI/TUI application:
    - If no arguments, TUI is launched by default (see @app.callback).
    - If user calls `tui`, TUI is launched.
    - Otherwise, standard CLI commands.
    """
    app()


if __name__ == "__main__":
    run()
