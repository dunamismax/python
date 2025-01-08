#!/usr/bin/env python3
"""
A dramatically expanded dual-mode (Typer + curses) Python Adventure Game.

Enhancements:
- Expanded map with more locations and narrative descriptions.
- Player stats, random monster encounters, colored TUI.
- Quest system with CLI and TUI integration.
- Additional CLI commands: stats, quest-list, quest-complete.

Usage:
- No arguments or "tui": launches curses-based TUI mode.
- Other subcommands (e.g., "move", "inventory-list", "stats") run in Typer CLI mode.
"""

import sys
import time
import random
import curses
import typer
from typing import List, Dict, Optional
from rich.console import Console
from rich.table import Table

# ---------------------------------------------------------
# Globals
# ---------------------------------------------------------
app = typer.Typer(help="Adventure Game CLI")
console = Console()

# ---------------------------------------------------------
# Game Data & Models
# ---------------------------------------------------------


class Game:
    """
    Encapsulates the entire game state and logic.
    """

    def __init__(self):
        # Player stats
        self.hp = 20
        self.attack = 4
        self.player_position = [0, 0]
        self.inventory = []

        # Map layout (x, y): location_name
        self.locations = {
            (0, 0): "Village Center",
            (0, 1): "Old Forest",
            (1, 1): "Ancient Ruins",
            (-1, 1): "Tranquil Lake",
            (0, 2): "Dark Clearing",
            (2, 1): "Mountain Pass",
            (2, 2): "Snowy Peak",
        }

        # Descriptions for each location
        self.location_descriptions = {
            "Village Center": (
                "You stand amidst quaint houses, "
                "a friendly blacksmith, and a small fountain."
            ),
            "Old Forest": (
                "Tall, gnarled trees tower above you, "
                "their leaves whispering ancient secrets."
            ),
            "Ancient Ruins": (
                "Crumbling stone pillars stand in silent tribute "
                "to a lost civilization."
            ),
            "Tranquil Lake": (
                "Crystal-clear waters reflect the sky, "
                "and a gentle breeze stirs the reeds."
            ),
            "Dark Clearing": (
                "A circular clearing with dead trees " "and an unsettling silence."
            ),
            "Mountain Pass": (
                "A steep pass through rugged mountains, "
                "harsh winds biting at your face."
            ),
            "Snowy Peak": (
                "The peak is blanketed in snow, offering "
                "a breathtaking view of the lands below."
            ),
        }

        # Items in each location
        self.items_in_location: Dict[tuple, List[str]] = {
            (0, 1): ["Mysterious Key"],
            (1, 1): ["Glowing Gemstone"],
            (-1, 1): ["Healing Potion"],
            (0, 2): ["Strange Map"],
            (2, 1): ["Mountain Herb"],
            (2, 2): ["Ancient Amulet"],
        }

        # Quests
        # "deliver_letter" quest is completed if the player has "Strange Map" and visits "Village Center" again.
        self.quests = {
            "deliver_letter": {
                "description": "Deliver the Strange Map to the Village Elder.",
                "completed": False,
                "completion_requirements": {
                    "item": "Strange Map",
                    "location": "Village Center",
                },
            },
            "find_amulet": {
                "description": "Find the Ancient Amulet at the Snowy Peak.",
                "completed": False,
                "completion_requirements": {
                    "item": "Ancient Amulet",
                    "location": None,  # Some quests just require picking up the item
                },
            },
        }

    def describe_location(self) -> str:
        """
        Return a descriptive string for the player's current position.
        """
        position_tuple = tuple(self.player_position)
        loc_name = self.locations.get(position_tuple, "Uncharted Wilderness")
        desc = self.location_descriptions.get(loc_name, "")
        return f"You are at {loc_name}.\n{desc}"

    def pick_up_items(self) -> List[str]:
        """
        Pick up all items at the current location, if any.
        """
        pos_tuple = tuple(self.player_position)
        if pos_tuple in self.items_in_location and self.items_in_location[pos_tuple]:
            found_items = self.items_in_location[pos_tuple]
            self.inventory.extend(found_items)
            self.items_in_location[pos_tuple] = []
            return found_items
        return []

    def move_player(self, direction: str) -> bool:
        """
        Move the player in the specified direction (north, south, east, west).
        Return True if successful, False if invalid direction.
        """
        if direction == "north":
            self.player_position[1] += 1
        elif direction == "south":
            self.player_position[1] -= 1
        elif direction == "east":
            self.player_position[0] += 1
        elif direction == "west":
            self.player_position[0] -= 1
        else:
            return False
        return True

    def check_quest_completion(self):
        """
        Check if any active quests can be completed.
        For each quest, see if the requirements are met (player has the required item and/or location).
        """
        position_tuple = tuple(self.player_position)
        current_location = self.locations.get(position_tuple, "Uncharted Wilderness")

        for quest_key, quest_data in self.quests.items():
            if not quest_data["completed"]:
                req_item = quest_data["completion_requirements"].get("item")
                req_loc = quest_data["completion_requirements"].get("location")
                has_item = req_item in self.inventory if req_item else True
                correct_loc = (req_loc == current_location) if req_loc else True

                # If all conditions are met, mark quest as completed
                if has_item and correct_loc:
                    quest_data["completed"] = True

    def random_encounter(self) -> Optional[str]:
        """
        Random chance for a monster encounter. Returns the name of the monster or None if no encounter occurs.
        """
        # 25% chance of an encounter
        if random.random() < 0.25:
            # Choose a random monster
            monsters = ["Goblin", "Wild Wolf", "Cave Troll"]
            return random.choice(monsters)
        return None

    def fight_monster(self, monster: str) -> str:
        """
        Simple fight logic. The player attacks first. If the monster isn't defeated, it strikes back.
        Return a result string describing the outcome.
        """
        # For simplicity, give monsters random HP from 5 to 10
        monster_hp = random.randint(5, 10)
        monster_attack = random.randint(1, 3)

        # Round-based combat (player then monster)
        combat_log = []
        while self.hp > 0 and monster_hp > 0:
            # Player attack
            monster_hp -= self.attack
            combat_log.append(
                f"You strike the {monster} for {self.attack} damage! (Monster HP: {monster_hp})"
            )
            if monster_hp <= 0:
                break

            # Monster attacks back
            self.hp -= monster_attack
            combat_log.append(
                f"The {monster} hits you for {monster_attack} damage! (Your HP: {self.hp})"
            )

        if self.hp <= 0:
            return "\n".join(combat_log + ["You have been defeated... Game Over!"])

        return "\n".join(combat_log + [f"You defeated the {monster}!"])


# Single instance of our game
game = Game()

# ---------------------------------------------------------
# Curses-based TUI
# ---------------------------------------------------------


def adventure_tui(stdscr):
    """
    Main loop for the curses-based TUI adventure game.
    """

    # Setup color pairs
    curses.start_color()
    curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # location/info
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)  # item pick-up
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)  # combat

    curses.curs_set(0)  # Hide the cursor
    stdscr.nodelay(False)
    stdscr.clear()

    while True:
        stdscr.clear()

        # Describe location
        location_info = game.describe_location().split("\n")
        stdscr.addstr(1, 2, location_info[0], curses.color_pair(1))
        stdscr.addstr(2, 2, location_info[1])

        # Pick up items
        found_items = game.pick_up_items()
        if found_items:
            stdscr.addstr(
                4, 2, f"You found: {', '.join(found_items)}!", curses.color_pair(2)
            )

        # Check for quest completion
        game.check_quest_completion()

        # Random encounter?
        monster = game.random_encounter()
        if monster:
            # Fight sequence
            combat_result = game.fight_monster(monster)
            lines = combat_result.split("\n")
            row = 6
            for line in lines:
                stdscr.addstr(row, 2, line, curses.color_pair(3))
                row += 1
            # If the player dies, end the game
            if game.hp <= 0:
                stdscr.refresh()
                stdscr.addstr(row + 1, 2, "Press any key to exit.")
                stdscr.getch()
                return
        else:
            stdscr.addstr(6, 2, "No enemies around... this time.")

        # Display instructions & status
        stdscr.addstr(8, 2, "[N/S/E/W] Move  [i] Inventory  [q] Quit")
        stdscr.addstr(10, 2, f"HP: {game.hp}")
        stdscr.addstr(10, 12, f"Attack: {game.attack}")

        # Show active quests
        active_quests = [k for (k, v) in game.quests.items() if not v["completed"]]
        stdscr.addstr(
            10, 25, "Quests: " + (", ".join(active_quests) if active_quests else "None")
        )

        stdscr.refresh()

        # Get user input
        key = stdscr.getch()

        if key == ord("q"):
            # Quit the game
            break
        elif key in [ord("n"), ord("N")]:
            game.move_player("north")
        elif key in [ord("s"), ord("S")]:
            game.move_player("south")
        elif key in [ord("e"), ord("E")]:
            game.move_player("east")
        elif key in [ord("w"), ord("W")]:
            game.move_player("west")
        elif key in [ord("i"), ord("I")]:
            display_inventory_tui(stdscr)
        else:
            # Ignore unrecognized key
            pass

    stdscr.clear()
    stdscr.addstr(1, 2, "Thanks for playing the TUI Adventure!")
    stdscr.refresh()
    time.sleep(1)


def display_inventory_tui(stdscr):
    """
    Display the player inventory in TUI.
    """
    stdscr.clear()
    stdscr.addstr(1, 2, "Your Inventory:")

    if not game.inventory:
        stdscr.addstr(2, 4, "Empty.")
    else:
        row = 2
        for item in game.inventory:
            stdscr.addstr(row, 4, f"- {item}")
            row += 1

    stdscr.addstr(row + 2, 2, "Press any key to go back...")
    stdscr.refresh()
    stdscr.getch()


def run_tui():
    """
    Launch the curses-based TUI adventure.
    """
    curses.wrapper(adventure_tui)


# ---------------------------------------------------------
# CLI Commands (Typer + Rich)
# ---------------------------------------------------------


@app.command()
def move(direction: str):
    """
    Move the player in a specified direction (north, south, east, west).
    """
    success = game.move_player(direction.lower())
    if not success:
        console.print("[bold red]Invalid direction![/bold red]")
        raise typer.Exit(code=1)

    console.print(f"[bold green]Moved {direction}![/bold green]")
    location_desc = game.describe_location()
    console.print(location_desc, style="cyan")

    # Auto pick up items
    found_items = game.pick_up_items()
    if found_items:
        console.print(f"[yellow]You found: {', '.join(found_items)}![/yellow]")

    # Check for quest completion
    game.check_quest_completion()


@app.command()
def inventory_list():
    """
    Show the items in your inventory.
    """
    table = Table(title="Your Inventory", style="bold magenta")
    table.add_column("Item", justify="left")

    if game.inventory:
        for item in game.inventory:
            table.add_row(item)
    else:
        table.add_row("[dim]No items in inventory.[/dim]")

    console.print(table)


@app.command()
def stats():
    """
    Display your current stats (HP, Attack).
    """
    table = Table(title="Player Stats", style="bold green")
    table.add_column("Stat", justify="left")
    table.add_column("Value", justify="right")

    table.add_row("HP", str(game.hp))
    table.add_row("Attack", str(game.attack))
    console.print(table)


@app.command()
def quest_list():
    """
    Display all quests and their completion status.
    """
    table = Table(title="Quests", style="bold yellow")
    table.add_column("Quest", justify="left")
    table.add_column("Description", justify="left")
    table.add_column("Status", justify="left")

    for quest_key, quest_data in game.quests.items():
        status = "Completed" if quest_data["completed"] else "In Progress"
        table.add_row(quest_key, quest_data["description"], status)

    console.print(table)


@app.command()
def quest_complete(quest_key: str):
    """
    Try to manually complete a given quest if its conditions are met.
    """
    if quest_key not in game.quests:
        console.print("[bold red]Invalid quest name![/bold red]")
        raise typer.Exit(code=1)

    quest_data = game.quests[quest_key]
    if quest_data["completed"]:
        console.print("[bold cyan]Quest already completed![/bold cyan]")
        raise typer.Exit()

    # Attempt to see if the requirements are met
    req_item = quest_data["completion_requirements"].get("item")
    req_loc = quest_data["completion_requirements"].get("location")

    # Current location
    position_tuple = tuple(game.player_position)
    current_location = game.locations.get(position_tuple, "Uncharted Wilderness")

    has_item = (req_item in game.inventory) if req_item else True
    correct_loc = (req_loc == current_location) if req_loc else True

    if has_item and correct_loc:
        quest_data["completed"] = True
        console.print(f"[bold green]Quest '{quest_key}' completed![/bold green]")
    else:
        console.print("[bold red]Conditions for this quest are not yet met.[/bold red]")


# ---------------------------------------------------------
# Default / TUI Subcommand Handler
# ---------------------------------------------------------


def main():
    """
    Entry point for our application.
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
