import time
import random
import curses
import typer
from typer import Context

app = typer.Typer(help="A bright and colorful Hello World TUI using Typer and curses.")

# Large ASCII art for "HELLO WORLD!", generated or adapted from Figlet-like tools
ASCII_ART = r"""
 _   _      _ _         __        __         _     _
| | | | ___| | | ___    \ \      / /__  _ __| | __| |
| |_| |/ _ \ | |/ _ \    \ \ /\ / / _ \| '__| |/ _` |
|  _  |  __/ | | (_) |    \ V  V / (_) | |  | | (_| |
|_| |_|\___|_|_|\___/      \_/\_/ \___/|_|  |_|\__,_|
              HELLO  WORLD!
"""


def curses_main(stdscr: "curses._CursesWindow"):
    """
    The main curses function that displays a large, colorful ASCII "Hello World!"
    with an animated starry background. Press 'q' to quit.
    """
    # Basic curses setup
    curses.curs_set(0)  # Hide the cursor
    curses.start_color()
    stdscr.nodelay(True)  # Non-blocking input

    # Define color pairs (foreground, background)
    curses.init_pair(1, curses.COLOR_BLUE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
    curses.init_pair(6, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLACK)

    # Convert ASCII art into a list of lines for easy printing
    ascii_lines = ASCII_ART.strip("\n").splitlines()

    while True:
        # Cycle through color pairs
        for color_id in range(1, 8):
            # Erase the screen for each color iteration
            stdscr.erase()

            # Get terminal dimensions
            height, width = stdscr.getmaxyx()

            # Draw a "starry" background
            draw_stars(stdscr, height, width)

            # Display the ASCII art in the center, using the current color pair
            for i, line in enumerate(ascii_lines):
                y = (height // 2 - len(ascii_lines) // 2) + i
                x = max(0, width // 2 - len(line) // 2)  # ensure it doesn't go negative
                stdscr.attron(curses.color_pair(color_id) | curses.A_BOLD)
                if 0 <= y < height:  # only print if within screen bounds
                    stdscr.addstr(y, x, line[: width - 1])  # slice to avoid wrapping
                stdscr.attroff(curses.color_pair(color_id) | curses.A_BOLD)

            # Display the quit hint
            hint = "Press 'q' to quit..."
            stdscr.attron(curses.color_pair(7))
            stdscr.addstr(height - 1, 0, hint[: width - 1])
            stdscr.attroff(curses.color_pair(7))

            # Refresh the screen
            stdscr.refresh()

            # Check for user input
            key = stdscr.getch()
            if key == ord("q"):
                return  # Exit the TUI loop

            # Pause briefly before the next color
            time.sleep(0.3)


def draw_stars(
    stdscr: "curses._CursesWindow", height: int, width: int, num_stars: int = 80
):
    """
    Draws a 'starry' background of random characters in random colors.
    """
    for _ in range(num_stars):
        star_y = random.randint(0, height - 2)  # leave last line for the hint
        star_x = random.randint(0, width - 1)
        star_char = random.choice([".", "*", "+", "·"])
        star_color = random.randint(1, 7)
        # Use bold for extra brightness
        stdscr.attron(curses.color_pair(star_color) | curses.A_BOLD)
        stdscr.addch(star_y, star_x, star_char)
        stdscr.attroff(curses.color_pair(star_color) | curses.A_BOLD)


@app.callback(invoke_without_command=True)
def main_callback(ctx: Context):
    """
    By default (no subcommands), launch the curses TUI.
    """
    if ctx.invoked_subcommand is None:
        curses.wrapper(curses_main)


if __name__ == "__main__":
    # Simply run "python hello-world.py" to see the TUI in action.
    app()
