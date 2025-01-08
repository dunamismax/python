#!/usr/bin/env python3
"""
secure-notes.py
---------------
A production-ready encrypted notes CLI application in Python using Typer.

Features:
- Asks for an encryption password at startup; if first run, creates a new encrypted file.
- Displays a list of notes and allows the user to create, view, and edit notes—all through a CLI menu.
- Uses Typer for an interactive command-line interface.
- Encrypts/decrypts notes using the Fernet (AES 128-bit in CBC mode + HMAC) scheme from the 'cryptography' package.
- Demonstrates best practices for password-based key derivation (using PBKDF2).
- Error handling, docstrings, and a straightforward design for production usage.

Usage:
    Run `python secure-notes.py` to start the interactive CLI.
"""

import os
import json
import base64
import hashlib
import secrets
from typing import List, Dict, Optional

import typer
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet, InvalidToken

# ---------------------------------------------------------------------------
# Constants and helper functions
# ---------------------------------------------------------------------------

app = typer.Typer(help="Secure Notes - An encrypted notes CLI application.")

DEFAULT_ENC_FILE = "secure_notes.enc"
PBKDF2_ITERATIONS = 200_000  # Reasonably strong iteration count


def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """
    Derive a Fernet-compatible key from a user-provided password and salt.

    :param password: The password string input by the user.
    :param salt: Random bytes used as a salt for PBKDF2.
    :return: A URL-safe base64-encoded key suitable for Fernet.
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
    """
    Encrypt the given plaintext using the provided Fernet object.

    :param plaintext: The raw bytes to encrypt.
    :param fernet: A Fernet object initialized with the appropriate key.
    :return: Encrypted ciphertext as bytes.
    """
    return fernet.encrypt(plaintext)


def decrypt_data(ciphertext: bytes, fernet: Fernet) -> bytes:
    """
    Decrypt the given ciphertext using the provided Fernet object.

    :param ciphertext: The encrypted bytes.
    :param fernet: A Fernet object initialized with the appropriate key.
    :return: Decrypted plaintext as bytes.
    """
    return fernet.decrypt(ciphertext)


def load_notes_file(
    password: str, filename: str = DEFAULT_ENC_FILE
) -> List[Dict[str, str]]:
    """
    Load notes from an encrypted file. If file doesn't exist, return an empty list.
    If the file is corrupted or the password is incorrect, raise an InvalidToken.

    :param password: The user-entered password.
    :param filename: The encrypted file path.
    :return: A list of note dictionaries.
    """
    if not os.path.isfile(filename):
        # File does not exist -> new data
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
    Save notes to an encrypted file. Generates a salt if none exists, or uses the
    existing file's salt to maintain consistency.

    :param password: The user-entered password.
    :param notes: A list of dictionaries representing notes.
    :param filename: The encrypted file path.
    """
    # If file doesn't exist, generate a new salt.
    # If it exists, reuse the salt so the user can continue using the same password.
    if os.path.isfile(filename):
        with open(filename, "rb") as f:
            old_data = f.read()
        salt = old_data[:16]
    else:
        salt = secrets.token_bytes(16)  # 16 bytes salt

    fernet = Fernet(derive_key_from_password(password, salt))
    data_to_store = {"notes": notes}
    encrypted_notes = encrypt_data(json.dumps(data_to_store).encode("utf-8"), fernet)

    # Write salt + encrypted data
    with open(filename, "wb") as f:
        f.write(salt + encrypted_notes)


# ---------------------------------------------------------------------------
# Global state (populated after user enters password)
# ---------------------------------------------------------------------------

NOTES: List[Dict[str, str]] = []
PASSWORD: Optional[str] = None


# ---------------------------------------------------------------------------
# Interactive CLI
# ---------------------------------------------------------------------------


@app.command()
def main() -> None:
    """
    Secure Notes interactive CLI.

    Prompts for an encryption password on startup and enters an interactive menu
    to list, create, view, and edit notes.
    """
    global NOTES, PASSWORD

    # Prompt the user for their password, hiding input for security
    typer.echo("Welcome to Secure Notes!")
    PASSWORD = typer.prompt("Please enter your encryption password", hide_input=True)

    # Attempt to load existing notes. If file doesn't exist, an empty list is returned.
    try:
        NOTES = load_notes_file(PASSWORD, DEFAULT_ENC_FILE)
        typer.echo("Notes loaded successfully.")
    except InvalidToken as e:
        typer.secho(str(e), fg=typer.colors.RED)
        typer.echo("Exiting...")
        raise typer.Exit(code=1)

    # Enter an interactive loop
    while True:
        typer.echo("\nActions:")
        typer.echo("[1] List Notes")
        typer.echo("[2] Create New Note")
        typer.echo("[3] View Note by Index")
        typer.echo("[4] Edit Note by Index")
        typer.echo("[5] Quit\n")

        choice = typer.prompt("Choose an action", default="5")

        if choice == "1":
            list_notes()
        elif choice == "2":
            create_note()
        elif choice == "3":
            view_note()
        elif choice == "4":
            edit_note()
        elif choice == "5":
            typer.echo("Goodbye!")
            break
        else:
            typer.echo("Invalid choice. Please try again.")


def list_notes() -> None:
    """
    List all notes in the current session.
    """
    if not NOTES:
        typer.echo("No notes found.")
        return

    typer.echo("\nYour Secure Notes:")
    for idx, note in enumerate(NOTES):
        title = note["title"] if note["title"] else f"Untitled ({idx})"
        typer.echo(f"{idx}: {title}")


def create_note() -> None:
    """
    Prompt the user to create a new note, then save it.
    """
    global NOTES, PASSWORD

    title = typer.prompt("Note Title (optional, press ENTER to skip)", default="")
    content = typer.prompt(
        "Note Content (multi-line supported, press ENTER to finish)", default=""
    )

    NOTES.append({"title": title, "content": content})
    save_notes_file(PASSWORD, NOTES, DEFAULT_ENC_FILE)
    typer.echo("New note saved successfully!")


def view_note() -> None:
    """
    Prompt the user for an index, then display the corresponding note.
    """
    if not NOTES:
        typer.echo("No notes to view.")
        return

    try:
        idx = typer.prompt("Enter the note index to view", type=int)
        if idx < 0 or idx >= len(NOTES):
            typer.echo("Invalid note index.")
            return

        selected_note = NOTES[idx]
        typer.echo(f"\n--- Note {idx} ---")
        typer.echo(f"Title: {selected_note['title']}")
        typer.echo("-" * 40)
        typer.echo(f"{selected_note['content']}\n")

    except ValueError:
        typer.echo("Please enter a valid integer index.")


def edit_note() -> None:
    """
    Prompt the user for an index, then allow editing of the existing note.
    """
    global NOTES, PASSWORD

    if not NOTES:
        typer.echo("No notes to edit.")
        return

    try:
        idx = typer.prompt("Enter the note index to edit", type=int)
        if idx < 0 or idx >= len(NOTES):
            typer.echo("Invalid note index.")
            return

        # Show current title/content for reference
        current_title = NOTES[idx]["title"]
        current_content = NOTES[idx]["content"]

        typer.echo(f"\nCurrent Title: {current_title}")
        new_title = typer.prompt(
            "New Title (press ENTER to keep current)", default=current_title
        )

        typer.echo(f"\nCurrent Content:\n{current_content}")
        new_content = typer.prompt(
            "New Content (press ENTER to keep current)", default=current_content
        )

        # Update the note
        NOTES[idx] = {"title": new_title, "content": new_content}
        save_notes_file(PASSWORD, NOTES, DEFAULT_ENC_FILE)
        typer.echo(f"Note {idx} updated successfully!")

    except ValueError:
        typer.echo("Please enter a valid integer index.")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
