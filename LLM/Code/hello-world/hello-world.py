import time
import curses
import typer

app = typer.Typer(help="A bright and colorful Hello World app using Typer and curses.")


def main(stdscr: "curses._CursesWindow"):
    """
    The main curses function that draws an animated, colorful "Hello, World!" message.
    Press 'q' to quit.
    """

    # Hide the cursor and enable color mode
    curses.curs_set(0)
    curses.start_color()

    # Create some color pairs (foreground, background)
    curses.init_pair(1, curses.COLOR_BLUE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
    curses.init_pair(6, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLACK)

    # Non-blocking input: we can catch keyboard presses while animating
    stdscr.nodelay(True)

    text = "Hello, World!"
    height, width = stdscr.getmaxyx()

    while True:
        # Cycle through the color pairs 1 to 7
        for color_id in range(1, 8):
            # Clear the screen
            stdscr.erase()

            # Centered position for the text
            y = height // 2
            x = width // 2 - len(text) // 2

            # Draw the text with the current color pair, in bold
            stdscr.attron(curses.color_pair(color_id) | curses.A_BOLD)
            stdscr.addstr(y, x, text)
            stdscr.attroff(curses.color_pair(color_id) | curses.A_BOLD)

            # Add a small hint to quit
            hint = "Press 'q' to quit..."
            stdscr.addstr(height - 1, 0, hint)

            # Refresh the screen to show the changes
            stdscr.refresh()

            # Check if the user pressed 'q' to quit
            key = stdscr.getch()
            if key == ord("q"):
                return  # Exit the TUI loop

            # Short delay between color changes
            time.sleep(0.3)


@app.command()
def greet():
    """
    Launch the TUI "Hello, World!" application.
    """
    curses.wrapper(main)


if __name__ == "__main__":
    app()
