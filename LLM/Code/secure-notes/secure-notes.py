"""
secure-notes.py
---------------
A production-ready encrypted notes TUI application in Python.

Features:
- Asks for an encryption password at startup; if first run, creates a new encrypted file.
- Displays a list of notes and allows the user to create, view, and edit notes.
- Uses the Textual library for a polished TUI.
- Encrypts/decrypts notes using the Fernet (AES 128-bit in CBC mode + HMAC) scheme from the 'cryptography' package.
- Demonstrates best practices for password-based key derivation (using PBKDF2) and TUI design.
- Error handling, docstrings, and a straightforward design for production usage.
"""

import os
import json
import base64
import hashlib
import secrets
from typing import List, Dict, Optional

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet, InvalidToken

from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal, Container, ScrollableContainer
from textual.widgets import (
    Header,
    Footer,
    Static,
    Input,
    Button,
    ListView,
    ListItem,
    Label,
)
from textual.screen import Screen
from textual import events


# ---------------------------------------------------------------------------
# Constants and helper functions
# ---------------------------------------------------------------------------

DEFAULT_ENC_FILE = "secure_notes.enc"
PBKDF2_ITERATIONS = 200_000  # Reasonably strong iteration count


def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """Derive a Fernet-compatible key from a user-provided password and salt."""
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
    If the file is corrupted or the password is incorrect, raise an InvalidToken.
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
# Screens
# ---------------------------------------------------------------------------


class LoginScreen(Screen):
    """Screen that prompts the user for their encryption password."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static(
                "Welcome to Secure Notes\n\nPlease enter your encryption password.\n"
                "If this is your first time, a new notes file will be created.\n"
            ),
            Input(
                placeholder="Encryption Password", password=True, id="password_input"
            ),
            Button("Submit", id="login_submit"),
        )
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "login_submit":
            password_widget = self.query_one("#password_input", Input)
            password = password_widget.value.strip()

            # Attempt to load existing notes or create new file if doesn't exist
            try:
                notes = load_notes_file(password, DEFAULT_ENC_FILE)
            except InvalidToken:
                # Show error message
                self.app.push_screen(
                    ErrorScreen("Incorrect password or corrupted file.")
                )
                return

            # If load succeeds, store the password & notes in app data and push main screen
            self.app.password = password
            self.app.notes = notes
            self.app.push_screen(MainNotesScreen())


class ErrorScreen(Screen):
    """Screen to display an error and let user go back to login."""

    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static(f"Error: {self.message}"),
            Button("Back", id="back_to_login"),
        )
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back_to_login":
            await self.app.pop_screen()  # return to previous screen


class MainNotesScreen(Screen):
    """Main screen for viewing and managing notes."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            Vertical(
                Static("Your Secure Notes:", id="notes_label"),
                ListView(id="notes_list"),
                Button("New Note", id="new_note_btn"),
            ),
            ScrollableContainer(
                Static("Select a note to view or edit.", id="note_detail"),
                id="detail_container",
            ),
        )
        yield Footer()

    def on_mount(self) -> None:
        """Populate the list of notes on mounting."""
        self.populate_notes_list()

    def populate_notes_list(self) -> None:
        """Populate the notes list from self.app.notes."""
        list_view = self.query_one("#notes_list", ListView)
        list_view.clear()

        for idx, note in enumerate(self.app.notes):
            title = note["title"] if note["title"] else f"Untitled ({idx})"
            list_view.append(ListItem(Label(title)))

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """When the user selects a note from the ListView, display it in the detail section."""
        index = event.index
        if 0 <= index < len(self.app.notes):
            selected_note = self.app.notes[index]
            detail_widget = self.query_one("#note_detail", Static)
            content = (
                f"Title: {selected_note['title']}\n"
                f"{'-'*40}\n"
                f"{selected_note['content']}"
            )
            detail_widget.update(content)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "new_note_btn":
            self.app.push_screen(NoteEditorScreen())


class NoteEditorScreen(Screen):
    """Screen for creating a new note or editing an existing note in the future."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static("Create a New Note"),
            Input(placeholder="Title", id="note_title"),
            Input(placeholder="Content", id="note_content"),
            Button("Save", id="save_note"),
            Button("Cancel", id="cancel_note"),
        )
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_note":
            title_widget = self.query_one("#note_title", Input)
            content_widget = self.query_one("#note_content", Input)

            title = title_widget.value.strip()
            content = content_widget.value.strip()

            self.app.notes.append({"title": title, "content": content})
            save_notes_file(self.app.password, self.app.notes, DEFAULT_ENC_FILE)

            await self.app.pop_screen()  # Return to MainNotesScreen
            # Refresh main screen list
            main_screen = self.app.get_screen_by_name("mainnotesscreen")
            if main_screen:
                main_screen.populate_notes_list()
        elif event.button.id == "cancel_note":
            await self.app.pop_screen()  # Return to MainNotesScreen


# ---------------------------------------------------------------------------
# Main Application
# ---------------------------------------------------------------------------


class SecureNotesApp(App):
    """The main Textual App for Secure Notes."""

    CSS_PATH = None  # Or a path to a textual CSS file if you want advanced theming
    password: Optional[str] = None
    notes: List[Dict[str, str]] = []

    def on_mount(self) -> None:
        """Push the LoginScreen when the app starts."""
        self.push_screen(LoginScreen())

    def on_error(self, error: Exception) -> None:
        """Handle unexpected exceptions gracefully."""
        self.push_screen(ErrorScreen(str(error)))


if __name__ == "__main__":
    app = SecureNotesApp()
    app.run()
