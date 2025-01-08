#!/usr/bin/env python3
"""
A dual-mode (Typer + curses) Python Adventure Game.

- If run with no arguments or with "tui", launches a curses-based TUI game.
- Otherwise, runs in CLI mode with Rich-enhanced output for commands like "move" or "inventory".
"""

import sys
import curses
import time
import typer
from typing import Optional
from rich.console import Console
from rich.table import Table

# ---------------------------------------------------------
# Globals / Game State
# ---------------------------------------------------------
app = typer.Typer(help="Adventure Game CLI")
console = Console()

# The player’s position (simple x, y coordinate).
player_position = [0, 0]

# The player’s inventory.
inventory = []

# A simple dictionary for the map layout (you can expand or alter this).
locations = {
    (0, 0): "Forest Entrance",
    (0, 1): "Deep Forest",
    (1, 1): "Ancient Cave",
    (-1, 1): "Mystic Lake",
    (0, 2): "Dark Clearing",
}

# Items that can be found at given coordinates.
items_in_location = {
    (0, 1): ["Mysterious Key"],
    (1, 1): ["Glowing Gemstone"],
    (-1, 1): ["Healing Potion"],
    (0, 2): ["Strange Map"],
}


# ---------------------------------------------------------
# Utility Functions (Shared by TUI & CLI)
# ---------------------------------------------------------
def describe_location(position):
    """Return a string describing the location based on the position."""
    location_name = locations.get(tuple(position), "Uncharted Wilderness")
    return f"You are at the {location_name}."


def pick_up_items(position):
    """Pick up all items at the current location, if any."""
    pos_tuple = tuple(position)
    if pos_tuple in items_in_location and items_in_location[pos_tuple]:
        found_items = items_in_location[pos_tuple]
        inventory.extend(found_items)
        items_in_location[pos_tuple] = []  # Clear them from the map
        return found_items
    return []


def move_player(direction: str):
    """Move the player in the given direction if possible."""
    if direction == "north":
        player_position[1] += 1
    elif direction == "south":
        player_position[1] -= 1
    elif direction == "east":
        player_position[0] += 1
    elif direction == "west":
        player_position[0] -= 1
    else:
        return False
    return True


# ---------------------------------------------------------
# Curses-based TUI
# ---------------------------------------------------------
def adventure_tui(stdscr):
    """Main loop for the curses-based TUI adventure game."""
    curses.curs_set(0)  # Hide the cursor
    stdscr.nodelay(False)
    stdscr.clear()

    # Main game loop
    while True:
        stdscr.clear()

        # Print location description
        location_desc = describe_location(player_position)
        stdscr.addstr(1, 2, location_desc)

        # Check if any items are here
        found_items = pick_up_items(player_position)
        if found_items:
            stdscr.addstr(3, 2, f"You found: {', '.join(found_items)}!")

        # Show instructions
        stdscr.addstr(5, 2, "Move with N/S/E/W. Press 'i' for inventory, 'q' to quit.")

        # Refresh the screen to show updated content
        stdscr.refresh()

        # Get user input
        key = stdscr.getch()

        if key == ord("q"):
            # Quit the game
            break
        elif key in [ord("n"), ord("N")]:
            move_player("north")
        elif key in [ord("s"), ord("S")]:
            move_player("south")
        elif key in [ord("e"), ord("E")]:
            move_player("east")
        elif key in [ord("w"), ord("W")]:
            move_player("west")
        elif key in [ord("i"), ord("I")]:
            # Show inventory in TUI
            display_inventory_tui(stdscr)
        else:
            # Ignore unrecognized key
            pass

    stdscr.clear()
    stdscr.addstr(1, 2, "Thanks for playing the TUI Adventure!")
    stdscr.refresh()
    time.sleep(1)


def display_inventory_tui(stdscr):
    """Display the player inventory in TUI."""
    stdscr.clear()
    stdscr.addstr(1, 2, "Your Inventory:")

    if not inventory:
        stdscr.addstr(2, 4, "Empty.")
    else:
        for idx, item in enumerate(inventory, start=2):
            stdscr.addstr(idx, 4, f"- {item}")

    stdscr.addstr(len(inventory) + 4, 2, "Press any key to go back...")
    stdscr.refresh()
    stdscr.getch()  # Pause until keypress


def run_tui():
    """Launch the curses-based TUI adventure."""
    curses.wrapper(adventure_tui)


# ---------------------------------------------------------
# CLI Commands (Typer + Rich)
# ---------------------------------------------------------
@app.command()
def move(direction: str):
    """
    Move the player in a specified direction (north, south, east, west).
    """
    success = move_player(direction.lower())
    if not success:
        console.print("[bold red]Invalid direction![/bold red]")
        raise typer.Exit(code=1)

    # Describe new location
    console.print(f"[bold green]Moved {direction}![/bold green]")
    location_desc = describe_location(player_position)
    console.print(location_desc, style="cyan")

    # Pick up items automatically
    found_items = pick_up_items(player_position)
    if found_items:
        console.print(f"[yellow]You found: {', '.join(found_items)}![/yellow]")


@app.command()
def inventory_list():
    """
    Show the items in your inventory.
    """
    table = Table(title="Your Inventory", style="bold magenta")
    table.add_column("Item", justify="left")

    if inventory:
        for item in inventory:
            table.add_row(item)
    else:
        table.add_row("[dim]No items in inventory.[/dim]")

    console.print(table)


# ---------------------------------------------------------
# Default / TUI Subcommand Handler
# ---------------------------------------------------------
def main():
    """
    The entry point for our application.
    Automatically launches the TUI if no arguments or if the 'tui' command is provided.
    Otherwise, uses Typer for CLI mode.
    """
    if len(sys.argv) == 1:
        # No arguments provided -> launch TUI
        run_tui()
    elif len(sys.argv) >= 2 and sys.argv[1] == "tui":
        # "tui" subcommand -> launch TUI
        run_tui()
    else:
        # Otherwise, run in CLI mode
        app()


if __name__ == "__main__":
    main()
