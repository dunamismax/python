#!/usr/bin/env python3
"""
wpm_tester.py

A dual-mode WPM tester:
- By default (no subcommand) or with `tui`, launches an interactive curses-based TUI.
- With `run`, operates in a Rich-enhanced CLI mode.

Author: You
"""

import sys
import time
import random
import csv
import os
import string
import curses
from datetime import datetime
from typing import List

import typer
from rich import print as rprint

app = typer.Typer(
    help="A timed WPM Tester in dual-mode: curses TUI or Rich-enhanced CLI."
)


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

    def get_typed_content_segments(self):
        """
        Generator that yields (char, is_correct) for each typed character,
        and then yields the untyped remainder as (char, None).
        Useful for printing in color via curses or Rich.
        """
        for i, typed_char in enumerate(self.typed_chars):
            if i < len(self.content):
                yield typed_char, (typed_char == self.content[i])
            else:
                # If typed_chars goes beyond content length
                yield typed_char, False

        # Untyped portion
        if len(self.typed_chars) < len(self.content):
            for c in self.content[len(self.typed_chars) :]:
                yield c, None


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


def run_test_cli(duration: int) -> None:
    """
    CLI version of the test, using Typer for echo/prompts and normal stdout/tty single-char.
    """
    words = load_words_from_file("words.txt")
    game = TypingGame(words)
    total_typed_chars = 0
    correct_typed_chars = 0

    typer.echo(f"\nStarting a {duration}-second test. Type until time is up.\n")
    typer.echo("Press ENTER/ESC/Q to end early. Press BACKSPACE to correct mistakes.\n")
    typer.echo("----------------------------------------------------------\n")

    import tty
    import termios

    start_time = time.time()
    old_settings = termios.tcgetattr(sys.stdin)

    try:
        tty.setcbreak(sys.stdin.fileno())

        while True:
            elapsed = time.time() - start_time
            if elapsed >= duration:
                # Time's up
                break

            # Print color-coded content to CLI
            # We can quickly use ANSI codes (or Rich) for color:
            sys.stdout.write("\r" + " " * 120 + "\r")  # Clear line
            colored_line = []
            for c, is_correct in game.get_typed_content_segments():
                if is_correct is True:
                    colored_line.append(f"[green]{c}[/green]")
                elif is_correct is False:
                    colored_line.append(f"[red]{c}[/red]")
                else:
                    colored_line.append(f"[white]{c}[/white]")

            rprint("".join(colored_line), end="")

            # Print WPM, Accuracy, Time Left
            elapsed_minutes = max(elapsed / 60, 1e-9)
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

            ch = sys.stdin.read(1)
            if ch in ("\n", "\r", "\x1b", "q", "Q"):
                break

            # Backspace
            if ch == "\x7f":
                game.backspace()
                if total_typed_chars > 0:
                    total_typed_chars -= 1
                continue

            if ch in string.printable:
                was_correct = game.type_character(ch)
                total_typed_chars += 1
                if was_correct:
                    correct_typed_chars += 1

        # Final clear
        sys.stdout.write("\r" + " " * 120 + "\r")
        sys.stdout.flush()

    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

    final_elapsed = time.time() - start_time
    final_elapsed = max(final_elapsed, 1e-9)
    final_minutes = final_elapsed / 60.0
    final_words_typed = total_typed_chars / 5.0
    final_wpm = final_words_typed / final_minutes
    final_accuracy = (
        (correct_typed_chars / total_typed_chars) * 100
        if total_typed_chars > 0
        else 100.0
    )

    typer.echo("\n\n--- Test Complete ---")
    typer.echo(f"WPM: {final_wpm:.1f}")
    typer.echo(f"Accuracy: {final_accuracy:.1f}%")
    typer.echo(f"Time Elapsed: {int(final_elapsed)}s\n")

    save_results_to_csv(final_wpm, final_accuracy, duration)

    # Ask for next step
    choice = typer.prompt(
        "Press 'R' to retake, 'M' for new duration, or 'Q' to quit", default="Q"
    )
    if choice.lower() == "r":
        run_test_cli(duration)
    elif choice.lower() == "m":
        run_cli()
    else:
        typer.echo("Goodbye!")


def run_cli() -> None:
    """
    CLI menu to pick a test duration in Typer and run the WPM test in CLI mode.
    """
    typer.echo("Welcome to the WPM Tester (CLI mode)!")
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

    run_test_cli(duration)


def wpm_tui_menu(stdscr) -> int:
    """
    A small curses-based menu to pick a test duration.
    Returns the chosen duration in seconds.
    """
    curses.curs_set(0)
    stdscr.clear()
    stdscr.addstr(0, 0, "Welcome to the WPM Tester (TUI)!", curses.color_pair(3))
    stdscr.addstr(2, 0, "Select a test duration:", curses.color_pair(3))
    menu_items = ["15 seconds", "30 seconds", "60 seconds"]
    highlight = 0

    while True:
        for idx, item in enumerate(menu_items):
            mode = curses.A_REVERSE if idx == highlight else curses.A_NORMAL
            stdscr.addstr(4 + idx, 2, f"{idx+1}) {item}", mode)
        stdscr.addstr(
            8, 0, "Use UP/DOWN to move, ENTER to select.", curses.color_pair(3)
        )

        key = stdscr.getch()
        if key == curses.KEY_UP:
            highlight = (highlight - 1) % len(menu_items)
        elif key == curses.KEY_DOWN:
            highlight = (highlight + 1) % len(menu_items)
        elif key in (curses.KEY_ENTER, 10, 13):
            # Return the selected duration
            if highlight == 0:
                return 15
            elif highlight == 1:
                return 30
            else:
                return 60


def run_test_tui(stdscr, duration: int) -> None:
    """
    TUI version of the test, using curses for input and color highlighting.
    """
    curses.cbreak()
    curses.noecho()
    stdscr.nodelay(False)

    words = load_words_from_file("words.txt")
    game = TypingGame(words)
    total_typed_chars = 0
    correct_typed_chars = 0

    start_time = time.time()

    while True:
        stdscr.clear()
        elapsed = time.time() - start_time
        if elapsed >= duration:
            # Time's up
            break

        # Print instructions at top
        stdscr.addstr(
            0, 0, f"Time Left: {duration - int(elapsed)}s", curses.color_pair(3)
        )
        stdscr.addstr(
            1,
            0,
            "Press [ENTER]/[ESC]/[Q] to end early. BACKSPACE to correct mistakes.",
            curses.color_pair(3),
        )

        # Calculate WPM & Accuracy
        elapsed_minutes = max(elapsed / 60, 1e-9)
        words_typed = total_typed_chars / 5.0
        wpm = words_typed / elapsed_minutes
        accuracy = (
            (correct_typed_chars / total_typed_chars) * 100
            if total_typed_chars > 0
            else 100.0
        )
        stdscr.addstr(
            2, 0, f"WPM: {wpm:.1f} | Accuracy: {accuracy:.1f}%", curses.color_pair(3)
        )

        # Print the color-coded content
        # We'll display from row 4 onward.
        row = 4
        col = 0
        for c, is_correct in game.get_typed_content_segments():
            if is_correct is True:
                stdscr.addch(row, col, c, curses.color_pair(1))
            elif is_correct is False:
                stdscr.addch(row, col, c, curses.color_pair(2))
            else:
                stdscr.addch(row, col, c, curses.color_pair(3))
            col += 1

        stdscr.refresh()

        ch = stdscr.getch()
        if ch in (curses.KEY_ENTER, 10, 13, 27, ord("q"), ord("Q")):
            # ENTER, ESC, 'q' => end test
            break
        elif ch == curses.KEY_BACKSPACE or ch == 127:
            game.backspace()
            if total_typed_chars > 0:
                total_typed_chars -= 1
        elif 32 <= ch <= 126:
            # Printable ASCII
            typed_char = chr(ch)
            was_correct = game.type_character(typed_char)
            total_typed_chars += 1
            if was_correct:
                correct_typed_chars += 1

    # Final stats
    final_elapsed = time.time() - start_time
    final_elapsed = max(final_elapsed, 1e-9)
    final_minutes = final_elapsed / 60.0
    final_words_typed = total_typed_chars / 5.0
    final_wpm = final_words_typed / final_minutes
    final_accuracy = (
        (correct_typed_chars / total_typed_chars) * 100
        if total_typed_chars > 0
        else 100.0
    )

    # Show summary screen
    stdscr.clear()
    summary_lines = [
        "--- Test Complete ---",
        f"WPM: {final_wpm:.1f}",
        f"Accuracy: {final_accuracy:.1f}%",
        f"Time Elapsed: {int(final_elapsed)}s",
    ]
    for idx, line in enumerate(summary_lines):
        stdscr.addstr(idx, 0, line, curses.color_pair(3))

    # Save results
    save_results_to_csv(final_wpm, final_accuracy, duration)

    # Ask for next action
    prompt_line = "Press 'R' to retake, 'M' for menu, or 'Q' to quit."
    stdscr.addstr(len(summary_lines) + 2, 0, prompt_line, curses.color_pair(3))
    stdscr.refresh()

    while True:
        ch = stdscr.getch()
        if ch in (ord("r"), ord("R")):
            run_test_tui(stdscr, duration)
            break
        elif ch in (ord("m"), ord("M")):
            break
        elif ch in (ord("q"), ord("Q")):
            break


def tui_main(stdscr) -> None:
    """
    The main curses TUI controller that shows a menu, runs tests, etc.
    """
    # Initialize color pairs
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)  # correct = green
    curses.init_pair(2, curses.COLOR_RED, -1)  # incorrect = red
    curses.init_pair(3, curses.COLOR_WHITE, -1)  # default = white

    # Show a menu to select duration
    duration = wpm_tui_menu(stdscr)
    run_test_tui(stdscr, duration)


@app.callback(invoke_without_command=True)
def default_action(ctx: typer.Context):
    """
    If no subcommand is invoked, launch TUI by default.
    """
    if not ctx.invoked_subcommand:
        # Launch curses TUI
        curses.wrapper(tui_main)


@app.command()
def tui():
    """
    Explicit subcommand to launch the TUI.
    """
    curses.wrapper(tui_main)


@app.command()
def run():
    """
    CLI subcommand to launch the WPM test in a Rich/Typer environment.
    """
    run_cli()


def main():
    """
    Entry point for the program.
    """
    app()


if __name__ == "__main__":
    main()
