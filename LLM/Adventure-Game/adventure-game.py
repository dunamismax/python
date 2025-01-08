#!/usr/bin/env python3

"""
A purely curses-based Python Adventure Game with text-based graphics.

Features & Improvements:
- Entirely TUI: no CLI mode.
- Expanded map with more locations, including a "Haunted Castle."
- ASCII borders around the main game UI.
- Basic monster drawings during encounters.
- Additional items and a new "explore_castle" quest.
- Color usage for emphasis (location info, items, combat messages).
"""

import time
import random
import curses
from typing import List, Dict, Optional


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
        self.inventory: List[str] = []

        # Map layout (x, y) : location_name
        self.locations = {
            (0, 0): "Village Center",
            (0, 1): "Old Forest",
            (1, 1): "Ancient Ruins",
            (-1, 1): "Tranquil Lake",
            (0, 2): "Dark Clearing",
            (2, 1): "Mountain Pass",
            (2, 2): "Snowy Peak",
            (3, 2): "Haunted Castle",
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
            "Haunted Castle": (
                "A looming castle shrouded in mist. "
                "Creaking doors and eerie whispers echo within."
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
            (3, 2): ["Skeleton Key"],
        }

        # Quests
        # 1) deliver_letter: Completed if the player has "Strange Map" and visits "Village Center".
        # 2) find_amulet: Completed if the player picks up "Ancient Amulet".
        # 3) explore_castle: Completed if the player has "Skeleton Key" and visits "Haunted Castle".
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
                    "location": None,
                },
            },
            "explore_castle": {
                "description": "Use the Skeleton Key to enter the Haunted Castle.",
                "completed": False,
                "completion_requirements": {
                    "item": "Skeleton Key",
                    "location": "Haunted Castle",
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
        If the requirements (item + location) are met, the quest is marked as completed.
        """
        position_tuple = tuple(self.player_position)
        current_location = self.locations.get(position_tuple, "Uncharted Wilderness")

        for quest_key, quest_data in self.quests.items():
            if not quest_data["completed"]:
                req_item = quest_data["completion_requirements"].get("item")
                req_loc = quest_data["completion_requirements"].get("location")
                has_item = req_item in self.inventory if req_item else True
                correct_loc = (req_loc == current_location) if req_loc else True

                if has_item and correct_loc:
                    quest_data["completed"] = True

    def random_encounter(self) -> Optional[str]:
        """
        Random chance for a monster encounter. Returns the monster name or None if no encounter.
        """
        # 25% chance of an encounter
        if random.random() < 0.25:
            monsters = ["Goblin", "Wild Wolf", "Cave Troll"]
            return random.choice(monsters)
        return None

    def fight_monster(self, monster: str) -> str:
        """
        Simple fight logic. The player attacks first; if the monster isn't defeated, it strikes back.
        Return a string describing the outcome of the fight.
        """
        # For simplicity, monsters have random HP from 5 to 10
        monster_hp = random.randint(5, 10)
        monster_attack = random.randint(1, 3)

        combat_log = []
        while self.hp > 0 and monster_hp > 0:
            # Player attacks monster
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


# Global Game instance
game = Game()


# ---------------------------------------------------------
# Curses-Based TUI
# ---------------------------------------------------------


def draw_borders(stdscr):
    height, width = stdscr.getmaxyx()
    # Set a minimum for safe drawing:
    if height < 3 or width < 3:
        # Not enough space to draw a border safely
        stdscr.addstr(0, 0, "Terminal too small to draw borders!")
        return

    # Corners
    stdscr.addch(0, 0, "+")
    stdscr.addch(0, width - 1, "+")
    stdscr.addch(height - 1, 0, "+")
    stdscr.addch(height - 1, width - 1, "+")

    # Top and bottom
    for x in range(1, width - 1):
        stdscr.addch(0, x, "-")
        stdscr.addch(height - 1, x, "-")

    # Left and right
    for y in range(1, height - 1):
        stdscr.addch(y, 0, "|")
        stdscr.addch(y, width - 1, "|")


def display_monster(stdscr, monster: str, start_y: int, start_x: int):
    """
    Display a small ASCII representation of the monster in the TUI.
    Different ASCII for each monster type.
    """
    if monster == "Goblin":
        art = [
            r"   .-.",
            r"  (o.o)  < Goblin",
            r"   |=| ",
            r"  __|__",
        ]
    elif monster == "Wild Wolf":
        art = [
            r"|\_/|   < Wolf",
            r"| @ @)",
            r"( > º < )",
        ]
    else:  # "Cave Troll"
        art = [
            r"   __,='```\"'-.,",
            r"  / __|       __ l",
            r" / /   @    @    l  < Troll",
            r"| |               |",
        ]

    for i, line in enumerate(art):
        stdscr.addstr(start_y + i, start_x, line)


def display_inventory_tui(stdscr):
    """
    Display the player's inventory in TUI.
    Press any key to return.
    """
    stdscr.clear()
    draw_borders(stdscr)
    stdscr.addstr(1, 2, "Your Inventory:")

    if not game.inventory:
        stdscr.addstr(3, 4, "Empty.")
        y_offset = 4
    else:
        y_offset = 3
        for item in game.inventory:
            stdscr.addstr(y_offset, 4, f"- {item}")
            y_offset += 1

    stdscr.addstr(y_offset + 2, 2, "Press any key to go back...")
    stdscr.refresh()
    stdscr.getch()


def adventure_tui(stdscr):
    """
    Main loop for the curses-based TUI adventure game.
    """

    # Setup color pairs for different text categories
    curses.start_color()
    curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # location/info
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)  # item pick-up
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)  # combat

    curses.curs_set(0)  # Hide the cursor
    stdscr.nodelay(False)

    while True:
        stdscr.clear()
        draw_borders(stdscr)

        # Describe location
        location_info = game.describe_location().split("\n")
        stdscr.addstr(1, 2, location_info[0], curses.color_pair(1) | curses.A_BOLD)
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
        combat_log_lines = []
        if monster:
            # Display monster ASCII
            display_monster(stdscr, monster, 6, 2)
            # Fight
            combat_result = game.fight_monster(monster)
            combat_log_lines = combat_result.split("\n")

            # Show fight log below monster ASCII
            row = 10
            for line in combat_log_lines:
                stdscr.addstr(row, 2, line, curses.color_pair(3))
                row += 1

            # Check if the player died
            if game.hp <= 0:
                stdscr.refresh()
                stdscr.addstr(row + 1, 2, "Press any key to exit.")
                stdscr.getch()
                return
        else:
            stdscr.addstr(6, 2, "No enemies around... this time.")

        # Display instructions & status
        stdscr.addstr(14, 2, "[N/S/E/W] Move   [i] Inventory   [q] Quit")
        stdscr.addstr(16, 2, f"HP: {game.hp}")
        stdscr.addstr(16, 12, f"Attack: {game.attack}")

        # Show active quests
        active_quests = [k for (k, v) in game.quests.items() if not v["completed"]]
        stdscr.addstr(
            16, 25, "Quests: " + (", ".join(active_quests) if active_quests else "None")
        )

        stdscr.refresh()

        # Get user input
        key = stdscr.getch()
        if key == ord("q"):
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
            # Ignore unrecognized keys
            pass

    # End screen
    stdscr.clear()
    draw_borders(stdscr)
    stdscr.addstr(1, 2, "Thanks for playing this TUI Adventure!")
    stdscr.refresh()
    time.sleep(1)


def main():
    """
    Run the curses TUI adventure game.
    """
    curses.wrapper(adventure_tui)


if __name__ == "__main__":
    main()
