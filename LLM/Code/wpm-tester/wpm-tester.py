#!/usr/bin/env python3
"""
wpm_tester.py

A timer-based WPM test CLI built with Typer, reading words from a 'words.txt' file,
requiring space between words, and printing color-coded feedback directly to the console.

Usage:
  python wpm_tester.py
  or
  python wpm_tester.py run
"""

import sys
import time
import random
import csv
import os
import string
from datetime import datetime
from typing import List, Optional

import typer

# For single-character input (Unix-like only).
# Windows support would need msvcrt or another approach.
import tty
import termios


app = typer.Typer(help="A timed WPM Tester using Typer for a CLI interface.")


def load_words_from_file(filename: str = "words.txt") -> List[str]:
    """
    Load words from a text file, one word per line.
    Returns a list of words (with trailing newlines stripped).
    Raises an IOError if the file can't be read.
    """
    with open(filename, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


class TypingGame:
    """
    Manages the rolling stream of words to type, tracking typed characters,
    correctness, and adding new words as we progress.
    """

    def __init__(self, words: List[str], initial_words_count: int = 5) -> None:
        """
        :param words: The list of possible words to randomly choose from.
        :param initial_words_count: Number of words to seed in the rolling stream.
        """
        self.words = words
        initial_stream = [random.choice(self.words) for _ in range(initial_words_count)]
        # The rolling content that the user must type
        self.content = " ".join(initial_stream) + " "

        # All typed characters (including incorrect)
        self.typed_chars: List[str] = []
        # How many characters match exactly at their position
        self.typed_index = 0

    def add_new_word(self) -> None:
        """Append a random word + space to the end of self.content."""
        self.content += random.choice(self.words) + " "

    def consume_typed_word(self) -> None:
        """
        Remove from the front of self.content the entire correct word (plus space)
        that was just typed, reset typed_chars, typed_index,
        and add a new word to maintain the rolling list.
        """
        self.content = self.content[self.typed_index :]
        self.typed_chars.clear()
        self.typed_index = 0
        self.add_new_word()

    def type_character(self, char: str) -> bool:
        """
        Handle typing a single character:
          1. Append 'char' to typed_chars.
          2. If typed_chars[i] matches content[i], typed_index is incremented.
          3. If the matched character is a space in the correct position,
             we consume the typed word and refresh content.
        Returns True if typed character at this position is correct, else False.
        """
        self.typed_chars.append(char)
        is_correct = False

        # If we haven't exceeded content length, check correctness
        if len(self.typed_chars) <= len(self.content):
            new_char_index = len(self.typed_chars) - 1
            if self.typed_chars[new_char_index] == self.content[new_char_index]:
                is_correct = True
                self.typed_index += 1

                # If this was a space in the correct position, we've finished typing a word
                if self.content[new_char_index] == " ":
                    self.consume_typed_word()
            else:
                is_correct = False
        return is_correct

    def backspace(self) -> None:
        """
        Remove the last character from typed_chars (if any).
        If that character was correct at its position, reduce typed_index by 1.
        """
        if not self.typed_chars:
            return

        last_typed = self.typed_chars[-1]
        pos = len(self.typed_chars) - 1
        if pos < len(self.content) and last_typed == self.content[pos]:
            self.typed_index -= 1

        self.typed_chars.pop()

    def get_colored_content(self) -> str:
        """
        Return a color-coded representation of the rolling content based on typed_chars:
          - Correctly typed characters: green
          - Incorrectly typed characters: red
          - Untyped: default (white)
        """
        colored_output = []
        for i, typed_char in enumerate(self.typed_chars):
            if i < len(self.content):
                if typed_char == self.content[i]:
                    # Green for correct
                    colored_output.append(f"\033[92m{typed_char}\033[0m")
                else:
                    # Red for incorrect
                    colored_output.append(f"\033[91m{typed_char}\033[0m")
            else:
                # If typed_chars goes beyond content length
                colored_output.append(f"\033[91m{typed_char}\033[0m")

        if len(self.typed_chars) < len(self.content):
            # Untyped portion remains in default color
            untyped_portion = self.content[len(self.typed_chars) :]
            colored_output.append(untyped_portion)

        return "".join(colored_output)


def save_results_to_csv(wpm_value: float, accuracy_value: float, duration: int) -> None:
    """
    Append the current test's results to results.csv. If the file is empty,
    write the header row first.
    """
    timestamp = datetime.now().isoformat(timespec="seconds")
    file_is_empty = (not os.path.exists("results.csv")) or (
        os.path.getsize("results.csv") == 0
    )

    with open("results.csv", "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if file_is_empty:
            writer.writerow(["Time", "WPM", "Accuracy", "Duration"])
        writer.writerow(
            [timestamp, f"{wpm_value:.1f}", f"{accuracy_value:.1f}", duration]
        )


def run_test(duration: int) -> None:
    """
    Perform a timed WPM test for 'duration' seconds in an interactive manner.
    Captures single-character input (Unix-like only), shows partial correctness,
    calculates WPM/accuracy, and saves results to CSV upon completion.
    """
    # Load words
    words = load_words_from_file("words.txt")

    # Set up the typing game and stats
    game = TypingGame(words)
    total_typed_chars = 0
    correct_typed_chars = 0

    # Start the test
    start_time = time.time()

    typer.echo(f"\nStarting a {duration}-second test. Type until time is up.\n")
    typer.echo("Press ENTER/ESC/Q to end early. Press BACKSPACE to correct mistakes.\n")
    typer.echo("----------------------------------------------------------\n")

    # Configure stdin for single-character reads
    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())

        while True:
            # Check elapsed time
            elapsed = time.time() - start_time
            if elapsed >= duration:
                # Time's up
                break

            # Print the color-coded content
            sys.stdout.write("\r" + " " * 120 + "\r")  # Clear line
            sys.stdout.write(game.get_colored_content())
            sys.stdout.flush()

            # Calculate and show WPM & Accuracy
            elapsed_seconds = max(elapsed, 1e-9)  # Avoid division by zero
            elapsed_minutes = elapsed_seconds / 60
            words_typed = total_typed_chars / 5.0
            wpm = words_typed / elapsed_minutes
            accuracy = (
                (correct_typed_chars / total_typed_chars) * 100
                if total_typed_chars > 0
                else 100.0
            )
            sys.stdout.write(
                f"\nWPM: {wpm:.1f} | Accuracy: {accuracy:.1f}% | Time Left: {duration - int(elapsed)}s"
            )
            sys.stdout.flush()

            # Read a single character from stdin (non-blocking)
            ch = sys.stdin.read(1)

            # If user pressed ENTER, ESC, or Q => end test early
            if ch in ("\n", "\r", "\x1b", "q", "Q"):
                break

            # Handle backspace
            if ch == "\x7f":  # Backspace on many systems
                game.backspace()
                if total_typed_chars > 0:
                    total_typed_chars -= 1
                # If we removed a correct char, reduce correct_typed_chars
                # However, we don't strictly know if the last char was correct or not,
                # so we recalc carefully if desired. For now, let's do a simpler approach:
                # We'll just do approximate. A more precise approach would store correctness per char.
                continue

            # For normal typing (including space), if it's a printable ASCII char
            if ch in string.printable:
                was_correct = game.type_character(ch)
                total_typed_chars += 1
                if was_correct:
                    correct_typed_chars += 1

        # Final redraw to clear line after loop
        sys.stdout.write("\r" + " " * 120 + "\r")
        sys.stdout.flush()

    finally:
        # Restore terminal settings
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

    # Compute final stats
    final_elapsed = time.time() - start_time
    if final_elapsed < 1e-9:
        final_elapsed = 1e-9
    final_minutes = final_elapsed / 60.0
    final_words_typed = total_typed_chars / 5.0
    final_wpm = final_words_typed / final_minutes
    final_accuracy = (
        (correct_typed_chars / total_typed_chars) * 100
        if total_typed_chars > 0
        else 100.0
    )

    # Show summary
    typer.echo("\n\n--- Test Complete ---")
    typer.echo(f"WPM: {final_wpm:.1f}")
    typer.echo(f"Accuracy: {final_accuracy:.1f}%")
    typer.echo(f"Time Elapsed: {int(final_elapsed)}s\n")

    # Save to CSV
    save_results_to_csv(final_wpm, final_accuracy, duration)

    # Prompt user for next action
    choice = typer.prompt(
        "Press 'R' to retake the same test, 'M' to pick another duration, or 'Q' to quit",
        default="Q",
    )
    if choice.lower() == "r":
        run_test(duration)
    elif choice.lower() == "m":
        run()
    else:
        typer.echo("Goodbye!")


@app.command()
def run() -> None:
    """
    Interactive menu to select a test duration and start the WPM test.
    """
    typer.echo("Welcome to the WPM Tester!")
    typer.echo("Select a test duration:")
    typer.echo("1) 15 seconds")
    typer.echo("2) 30 seconds")
    typer.echo("3) 60 seconds\n")
    selection = typer.prompt("Enter choice (1/2/3)", default="3")

    if selection == "1":
        duration = 15
    elif selection == "2":
        duration = 30
    else:
        duration = 60

    run_test(duration)


def main() -> None:
    """
    Entry point to run the Typer app.
    """
    app()


if __name__ == "__main__":
    main()
