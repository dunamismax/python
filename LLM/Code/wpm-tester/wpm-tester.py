"""
wpm_tester.py

A timer-based WPM test TUI built with Textual, reading from a 'words.txt' file,
requiring space between words, and showing a dark-themed interface.

Usage:
  python wpm_tester.py
"""

import time
import random
import string
from typing import List
import csv
from datetime import datetime
import os

# Textual Imports
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Static
from textual.screen import Screen
from textual.reactive import reactive
from textual import events
from textual.timer import Timer


# ---------------------------------------------------------------------------
# 1) Helper functions
# ---------------------------------------------------------------------------


def load_words_from_file(filename: str = "words.txt") -> List[str]:
    """
    Load words from a text file, one word per line.
    Returns a list of words (with trailing newlines stripped).
    Raises an IOError if the file can't be read.
    """
    with open(filename, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


# ---------------------------------------------------------------------------
# 2) TypingWidget - Displays the text stream and handles highlight logic
# ---------------------------------------------------------------------------


class TypingWidget(Static):
    """
    Displays an "infinite" rolling stream of words to type. Tracks all typed chars:
      - If a character matches the expected one at that position, it's green.
      - If it does not, it's red, until the user backspaces.
    Once the user types the correct space at the end of a word, that entire word is
    removed from the front of `content`, typed_chars is reset, and a new word is appended.
    """

    # The rolling content we expect the user to type
    content = reactive("")

    # All typed characters (both correct and incorrect)
    typed_chars: List[str] = reactive([])

    # How many correct characters have been typed in the current word
    typed_index = reactive(0)

    def __init__(self, words: List[str], initial_words_count: int = 5) -> None:
        super().__init__()
        self.words = words
        # Seed initial content with random words + trailing space
        initial_stream = [random.choice(self.words) for _ in range(initial_words_count)]
        self.content = " ".join(initial_stream) + " "

    def on_mount(self) -> None:
        """Called when the widget is added to the DOM; render initial text."""
        self.update_content()

    def add_new_word(self) -> None:
        """Append a random word + space to the end of `content`."""
        self.content += random.choice(self.words) + " "

    def consume_typed_word(self) -> None:
        """
        Remove from the front of `content` the entire correct word (plus space) that
        was just typed, reset typed_chars, and add a new word to keep the rolling list.
        """
        # Remove everything up to typed_index
        self.content = self.content[self.typed_index :]

        # Clear typed_chars for next word
        self.typed_chars.clear()
        self.typed_index = 0

        # Add one new word to maintain rolling length
        self.add_new_word()
        self.update_content()

    def update_content(self) -> None:
        """
        Re-render the content with color highlighting based on typed_chars vs. content.
          - typed_chars[i] == content[i] => green
          - typed_chars[i] != content[i] => red
          - everything beyond typed_chars => white
        """
        colored_output = []

        # Compare each typed character to the corresponding content character
        for i, typed_char in enumerate(self.typed_chars):
            if i < len(self.content):
                if typed_char == self.content[i]:
                    colored_output.append(f"[green]{typed_char}[/green]")
                else:
                    colored_output.append(f"[red]{typed_char}[/red]")
            else:
                # If typed_chars goes beyond content length (unlikely but safe), mark red
                colored_output.append(f"[red]{typed_char}[/red]")

        # The untyped portion remains white
        if len(self.typed_chars) < len(self.content):
            untyped_portion = self.content[len(self.typed_chars) :]
            colored_output.append(f"[white]{untyped_portion}[/white]")

        self.update("".join(colored_output))

    def type_character(self, char: str) -> bool:
        """
        Handle typing a single character. We add the typed char to `typed_chars`, then:
          1. If it matches the current content[typed_index], we increment typed_index.
          2. If typed_index now points to a space that was correctly typed, we
             consume the entire word from the front of `content`.
        Returns True if typed character matches at its position, False otherwise.
        """
        self.typed_chars.append(char)

        # Check if it's correct
        is_correct = False
        if len(self.typed_chars) <= len(self.content):
            new_char_index = len(self.typed_chars) - 1
            if self.typed_chars[new_char_index] == self.content[new_char_index]:
                is_correct = True
                self.typed_index += 1

                # If this was a space in the correct position, we finished a word
                if self.content[new_char_index] == " ":
                    self.consume_typed_word()
            else:
                is_correct = False

        self.update_content()
        return is_correct

    def backspace(self) -> None:
        """
        Remove the last character from typed_chars (if any).
        If that character was correct, reduce typed_index by 1.
        """
        if self.typed_chars:
            last_typed = self.typed_chars[-1]
            pos = len(self.typed_chars) - 1
            if pos < len(self.content) and last_typed == self.content[pos]:
                self.typed_index -= 1

            self.typed_chars.pop()

        self.update_content()


# ---------------------------------------------------------------------------
# 3) WPMTestScreen - The main typing test screen
# ---------------------------------------------------------------------------


class WPMTestScreen(Screen):
    """
    Screen that handles the typing test:
      - Displays TypingWidget
      - Shows WPM & Accuracy in real-time
      - Timer-based end or user pressing Enter
    """

    wpm_display = reactive("WPM: 0.0")
    accuracy_display = reactive("Accuracy: 100.0%")

    def __init__(self, words: List[str], test_duration: int) -> None:
        super().__init__()
        self.words = words
        self.test_duration = test_duration

        self.start_time = 0.0
        self.timer: Timer | None = None

        # Stats for typed characters
        self.total_typed_chars = 0
        self.correct_typed_chars = 0

    def compose(self) -> ComposeResult:
        """Build the UI layout."""
        with Vertical():
            self.typing_widget = TypingWidget(words=self.words)
            yield self.typing_widget

            self.wpm_label = Static(self.wpm_display, id="wpm-label")
            yield self.wpm_label

            self.accuracy_label = Static(self.accuracy_display, id="accuracy-label")
            yield self.accuracy_label

    def on_mount(self) -> None:
        """Set up a repeating timer to check time and start the test clock."""
        self.start_time = time.time()
        self.timer = self.set_interval(0.1, self.check_time)

    def check_time(self) -> None:
        """Check if the test duration has expired."""
        elapsed = time.time() - self.start_time
        if elapsed >= self.test_duration:
            self.finish_test()

    def on_key(self, event: events.Key) -> None:
        """
        Handle keystrokes:
         - Enter => end test
         - Backspace => remove previous char
         - Otherwise => type (if event.character is printable)
        """
        if event.key == "enter":
            # End test early
            self.finish_test()
            return

        if event.key == "backspace":
            event.stop()
            self.typing_widget.backspace()
            # Decrement total typed if possible
            if self.total_typed_chars > 0:
                self.total_typed_chars -= 1
            self.update_metrics()
            return

        # For normal typing (including space), we rely on event.character.
        if event.character and event.character in string.printable:
            was_correct = self.typing_widget.type_character(event.character)
            self.total_typed_chars += 1
            if was_correct:
                self.correct_typed_chars += 1
            self.update_metrics()

    def update_metrics(self) -> None:
        """
        WPM = (total_typed_chars / 5) / (time_in_minutes)
        Accuracy = (correct_typed_chars / total_typed_chars) * 100
        """
        now = time.time()
        elapsed_seconds = now - self.start_time
        if elapsed_seconds <= 0:
            elapsed_seconds = 1e-9

        elapsed_minutes = elapsed_seconds / 60.0
        words_typed = self.total_typed_chars / 5.0
        wpm = words_typed / elapsed_minutes

        if self.total_typed_chars > 0:
            accuracy = (self.correct_typed_chars / self.total_typed_chars) * 100
        else:
            accuracy = 100.0

        self.wpm_display = f"WPM: {wpm:.1f}"
        self.accuracy_display = f"Accuracy: {accuracy:.1f}%"

    def finish_test(self) -> None:
        """Stop the timer and show the summary screen."""
        if self.timer:
            self.timer.stop()
        final_wpm = self.wpm_display
        final_accuracy = self.accuracy_display
        # Pass the same words & duration so the user can retake the exact test
        self.app.push_screen(
            SummaryScreen(final_wpm, final_accuracy, self.words, self.test_duration)
        )


# ---------------------------------------------------------------------------
# 4) MenuScreen - Let user pick test duration
# ---------------------------------------------------------------------------


class MenuScreen(Screen):
    """
    Main menu to select duration. Press 1, 2, or 3 for 15, 30, or 60 seconds.
    """

    def compose(self) -> ComposeResult:
        """Build our menu interface."""
        yield Static("[bold magenta]WPM-TESTER[/bold magenta]\n", id="title")
        yield Static(
            "Select a test duration:\n"
            "1) 15 seconds\n"
            "2) 30 seconds\n"
            "3) 60 seconds\n\n"
            "Press 1, 2, or 3 to begin.\n"
            "Press Ctrl+C to exit.\n",
            id="menu-instructions",
        )

    def on_key(self, event: events.Key) -> None:
        """
        Handle numeric input to select the desired test duration.
        """
        if event.key == "1":
            self.go_to_test(15)
        elif event.key == "2":
            self.go_to_test(30)
        elif event.key == "3":
            self.go_to_test(60)

    def go_to_test(self, duration: int) -> None:
        """Load words & push WPMTestScreen."""
        words = load_words_from_file("words.txt")
        self.app.push_screen(WPMTestScreen(words, duration))


# ---------------------------------------------------------------------------
# 5) SummaryScreen - displayed after test ends
# ---------------------------------------------------------------------------


class SummaryScreen(Screen):
    """
    Displays final WPM and Accuracy, plus navigation options:
      - Press R => Retake the same test
      - Press M => Return to the main menu
      - Press Q/Esc/Enter => Quit app

    Automatically logs the test results to `results.csv`.
    On the first run (i.e., if the file is empty), it writes column headers.
    """

    def __init__(
        self, final_wpm: str, final_accuracy: str, words: List[str], test_duration: int
    ) -> None:
        super().__init__()
        self.final_wpm = final_wpm
        self.final_accuracy = final_accuracy
        self.words = words
        self.test_duration = test_duration

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold green]--- Test Complete ---[/bold green]\n", id="summary-title"
        )
        yield Static(f"{self.final_wpm}\n{self.final_accuracy}\n", id="summary-results")
        yield Static(
            "[i]Press R to retake the test\n"
            "Press M to return to the main menu\n"
            "Press Q, Esc, or Enter to quit[/i]",
            id="summary-instructions",
        )

    def on_mount(self) -> None:
        """
        Called when the SummaryScreen is first displayed.
        Automatically save test results to a CSV file,
        writing headers only if the file is empty.
        """
        self.save_results_to_csv()

    def on_key(self, event: events.Key) -> None:
        """
        Handle navigation in summary:
          - R => Retake same test
          - M => Main menu
          - Q/Escape/Enter => Quit
        """
        if event.key.lower() == "r":  # retake
            self.app.pop_screen()  # remove SummaryScreen from stack
            self.app.push_screen(WPMTestScreen(self.words, self.test_duration))
        elif event.key.lower() == "m":  # menu
            self.app.pop_screen()  # remove SummaryScreen
            self.app.push_screen(MenuScreen())
        elif event.key.lower() == "q" or event.key in ["escape", "enter"]:
            self.app.exit()

    def save_results_to_csv(self) -> None:
        """
        Appends the current test's results to `results.csv`.
        If the file is empty, we first write column headers.
        """
        # Convert textual strings, e.g. "WPM: 42.0" => "42.0"
        wpm_value = self.final_wpm.replace("WPM: ", "").strip()
        accuracy_value = (
            self.final_accuracy.replace("Accuracy: ", "").strip().replace("%", "")
        )
        timestamp = datetime.now().isoformat(timespec="seconds")

        # Check if the file already exists and is non-empty
        file_is_empty = (not os.path.exists("results.csv")) or (
            os.path.getsize("results.csv") == 0
        )

        with open("results.csv", "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            # If file is empty, write the header row first
            if file_is_empty:
                writer.writerow(["Time", "WPM", "Accuracy", "Duration"])

            # Append the data row
            writer.writerow([timestamp, wpm_value, accuracy_value, self.test_duration])


# ---------------------------------------------------------------------------
# 6) Main App - with Dark Theme
# ---------------------------------------------------------------------------


class WPMTesterApp(App):
    """
    The overall Textual App. Starts at MenuScreen, transitions to others, uses a dark theme.
    """

    # Inline CSS to give a dark theme & improved styling
    CSS = """
    Screen {
        background: #1e1e1e;
        color: #e2e2e2;
    }

    #title {
        color: #ff79c6;
        text-align: center;
        padding: 2 0;
    }

    #menu-instructions {
        color: #bd93f9;
        padding: 1 2;
    }

    #wpm-label {
        color: #50fa7b;
        padding: 1 0;
    }

    #accuracy-label {
        color: #f1fa8c;
        padding: 1 0;
    }

    #summary-title {
        color: #ff79c6;
        text-align: center;
        padding: 2 0;
    }

    #summary-results {
        color: #bd93f9;
        text-align: center;
        padding: 1 0;
    }

    #summary-instructions {
        color: #8be9fd;
        text-align: center;
        padding: 1 0;
    }
    """

    BINDINGS = [
        ("ctrl+c", "exit_app", "Exit the application immediately"),
    ]

    def on_mount(self) -> None:
        """Start at the MenuScreen."""
        self.push_screen(MenuScreen())

    def action_exit_app(self) -> None:
        """Bound to Ctrl+C."""
        self.exit()


def main():
    """Run the WPMTesterApp."""
    app = WPMTesterApp()
    app.run()


if __name__ == "__main__":
    main()
