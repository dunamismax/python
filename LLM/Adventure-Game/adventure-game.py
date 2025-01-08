#!/usr/bin/env python3

"""
An expanded Textual-based Python Adventure Game with text-based graphics and new features.

Key Notes:
- All references to Panel were removed.
- Borders & titles are assigned purely via CSS.
- 'border-title' contains the text (e.g. "Location").
- 'border-title-style' can only accept style flags (e.g., bold, dim, underline).
"""

import random
from typing import List, Dict, Optional

from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Header, Footer, Static


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
            (1, 0): "Blacksmith Forge",
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
                "a friendly blacksmith nearby, and a small fountain.\n"
                "[dim]The Village Elder might be here...[/dim]"
            ),
            "Blacksmith Forge": (
                "A small but sturdy workshop filled with the clanging of metal. "
                "The Blacksmith is busy hammering away at a glowing piece of iron."
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
                "A circular clearing with dead trees and an unsettling silence."
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
            (1, 0): ["Shiny Sword"],  # New item from the Blacksmith's Forge
        }

        # Quests
        # 1) deliver_letter: Completed if the player has "Strange Map" and visits "Village Center".
        # 2) find_amulet: Completed if the player picks up "Ancient Amulet".
        # 3) explore_castle: Completed if the player has "Skeleton Key" and visits "Haunted Castle".
        # 4) acquire_sword: Completed if the player picks up the "Shiny Sword" from the Blacksmith Forge.
        # 5) defeat_boss: Completed if the player defeats the "Haunted Knight" in the Haunted Castle.
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
            "acquire_sword": {
                "description": "Obtain a Shiny Sword from the Blacksmith Forge.",
                "completed": False,
                "completion_requirements": {
                    "item": "Shiny Sword",
                    "location": None,
                },
            },
            "defeat_boss": {
                "description": "Defeat the Haunted Knight in the Haunted Castle.",
                "completed": False,
                "completion_requirements": {
                    "boss_defeated": True,
                },
            },
        }

        # NPCs: location_name => npc_name
        self.npcs = {
            "Village Center": "Village Elder",
            "Blacksmith Forge": "Blacksmith",
        }

        # Boss data
        self.boss_name = "Haunted Knight"
        self.boss_location = "Haunted Castle"
        self.boss_defeated = False

    def describe_location(self) -> str:
        """Return a descriptive string for the player's current position."""
        position_tuple = tuple(self.player_position)
        loc_name = self.locations.get(position_tuple, "Uncharted Wilderness")
        desc = self.location_descriptions.get(loc_name, "")
        return f"You are at [bold yellow]{loc_name}[/bold yellow].\n{desc}"

    def pick_up_items(self) -> List[str]:
        """Pick up all items at the current location, if any."""
        pos_tuple = tuple(self.player_position)
        if pos_tuple in self.items_in_location and self.items_in_location[pos_tuple]:
            found_items = self.items_in_location[pos_tuple]
            self.inventory.extend(found_items)
            self.items_in_location[pos_tuple] = []
            return found_items
        return []

    def move_player(self, direction: str) -> bool:
        """Move the player in the specified direction (north, south, east, west)."""
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

    def check_quest_completion(self) -> List[str]:
        """
        Check if any active quests can be completed.
        If the requirements (item + location or boss_defeated) are met,
        the quest is marked as completed.
        Returns a list of messages for any newly completed quests.
        """
        position_tuple = tuple(self.player_position)
        current_location = self.locations.get(position_tuple, "Uncharted Wilderness")

        completion_messages = []
        for quest_key, quest_data in self.quests.items():
            if not quest_data["completed"]:
                req_item = quest_data["completion_requirements"].get("item")
                req_loc = quest_data["completion_requirements"].get("location")
                req_boss_defeated = quest_data["completion_requirements"].get(
                    "boss_defeated", False
                )

                # Check item requirement
                has_item = req_item in self.inventory if req_item else True
                # Check location requirement
                correct_loc = (req_loc == current_location) if req_loc else True
                # Check boss requirement
                boss_is_defeated = self.boss_defeated if req_boss_defeated else True

                if has_item and correct_loc and boss_is_defeated:
                    quest_data["completed"] = True
                    completion_messages.append(
                        f"[bold green]Quest completed:[/bold green] {quest_key} - {quest_data['description']}"
                    )
        return completion_messages

    def random_encounter(self) -> Optional[str]:
        """
        Random chance for a monster encounter (not the boss).
        Returns the monster name or None if no encounter.
        """
        # 25% chance of an encounter
        if random.random() < 0.25:
            monsters = ["Goblin", "Wild Wolf", "Cave Troll"]
            return random.choice(monsters)
        return None

    def initiate_boss_fight(self) -> bool:
        """Check if the player is in the boss location and if the boss is not yet defeated."""
        position_tuple = tuple(self.player_position)
        current_location = self.locations.get(position_tuple, "Uncharted Wilderness")
        if current_location == self.boss_location and not self.boss_defeated:
            return True
        return False

    def fight_monster(self, monster: str) -> str:
        """
        Simple fight logic for random monsters. The player attacks first;
        if the monster isn't defeated, it strikes back.
        """
        monster_hp = random.randint(5, 10)
        monster_attack = random.randint(1, 3)

        combat_log = [f"[bold red]A {monster} appears![/bold red]"]

        while self.hp > 0 and monster_hp > 0:
            # Player attacks
            monster_hp -= self.attack
            combat_log.append(
                f"You strike the [red]{monster}[/red] for [bold]{self.attack}[/bold] damage! "
                f"(Monster HP: {monster_hp})"
            )
            if monster_hp <= 0:
                break

            # Monster attacks
            self.hp -= monster_attack
            combat_log.append(
                f"The [red]{monster}[/red] hits you for [bold]{monster_attack}[/bold] damage! "
                f"(Your HP: {self.hp})"
            )

        if self.hp <= 0:
            return "\n".join(
                combat_log
                + ["[bold red]You have been defeated... Game Over![/bold red]"]
            )

        return "\n".join(
            combat_log + [f"[bold green]You defeated the {monster}![/bold green]"]
        )

    def fight_boss(self) -> str:
        """
        Special boss fight logic. The boss is tougher,
        and the Shiny Sword doubles damage vs. the boss.
        """
        boss_hp = 20
        boss_attack = 5
        boss_log = [
            f"[bold red]The {self.boss_name} stands before you, emanating dark power![/bold red]"
        ]

        while self.hp > 0 and boss_hp > 0:
            damage_dealt = self.attack
            if "Shiny Sword" in self.inventory:
                damage_dealt *= 2  # Double damage

            boss_hp -= damage_dealt
            boss_log.append(
                f"You strike the [bold magenta]{self.boss_name}[/bold magenta] for [bold]{damage_dealt}[/bold] damage! "
                f"(Boss HP: {boss_hp})"
            )
            if boss_hp <= 0:
                break

            # Boss attacks
            self.hp -= boss_attack
            boss_log.append(
                f"The [bold magenta]{self.boss_name}[/bold magenta] strikes you for [bold]{boss_attack}[/bold] damage! "
                f"(Your HP: {self.hp})"
            )

        if self.hp <= 0:
            return "\n".join(
                boss_log
                + [
                    "[bold red]You have been slain by the Haunted Knight... "
                    "Game Over![/bold red]"
                ]
            )

        self.boss_defeated = True
        return "\n".join(
            boss_log
            + [
                f"[bold green]You have defeated the {self.boss_name} "
                "and lifted the castle's curse![/bold green]"
            ]
        )

    def talk_to_npc(self) -> Optional[str]:
        """If there's an NPC at the current location, return what they say."""
        position_tuple = tuple(self.player_position)
        loc_name = self.locations.get(position_tuple, "Uncharted Wilderness")
        npc_name = self.npcs.get(loc_name)

        if npc_name == "Village Elder":
            return (
                "[bold cyan]Village Elder:[/bold cyan] Thank you for your help, traveler. "
                "Should you find a Strange Map, please bring it here. "
                "And beware of the Haunted Castle to the east!"
            )
        elif npc_name == "Blacksmith":
            return (
                "[bold cyan]Blacksmith:[/bold cyan] Aha! I've just finished forging a Shiny Sword. "
                "If you find it, it might help you against whatever lurks in that castle."
            )
        return None

    def try_flee(self) -> bool:
        """Attempt to flee from random encounters, 50% success chance."""
        if random.random() < 0.5:
            return True
        else:
            damage = random.randint(1, 2)
            self.hp -= damage
            return False


# ---------------------------------------------------------
# Helper for Monster ASCII
# ---------------------------------------------------------
def get_monster_ascii(monster: str) -> List[str]:
    """Return a small ASCII representation of the monster as a list of strings."""
    if monster == "Goblin":
        return [
            r"   .-.",
            r"  (o.o)  < Goblin",
            r"   |=| ",
            r"  __|__",
        ]
    elif monster == "Wild Wolf":
        return [
            r"|\_/|   < Wolf",
            r"| @ @)",
            r"( > º < )",
        ]
    elif monster == "Cave Troll":
        return [
            r"   __,='```\"'-.,",
            r"  / __|       __ l",
            r" / /   @    @    l  < Troll",
            r"| |               |",
        ]
    else:
        # Generic
        return [
            r"  ??? ",
            r"  (??) ",
        ]


# ---------------------------------------------------------
# Textual-Based TUI
# ---------------------------------------------------------
class AdventureApp(App):
    """
    A Textual TUI application for the Python Adventure Game.
    """

    # Here is our multiline CSS definition
    CSS = """
    Screen {
        background: black;
        color: white;
    }

    #main_container {
        layout: grid;
        grid-size: 1;
        grid-rows: auto 1fr auto;
        padding: 1;
    }

    #top_bar, #bottom_bar {
        dock: top;
        height: auto;
    }

    /* "Panel-like" statics using CSS for borders. */
    #location_panel {
        margin: 1;
        width: 100%;
        border: round white;
        border-title: "Location";
        border-title-style: bold; 
    }

    #log_panel {
        margin: 1;
        width: 100%;
        height: 16;
        overflow-y: auto;
        border: round white;
        border-title: "Log";
        border-title-style: bold;
    }

    #inventory_panel {
        margin: 1;
        width: 40%;
        height: auto;
        border: round white;
        border-title: "Inventory";
        border-title-style: bold;
    }

    #help_panel {
        margin: 1;
        width: 40%;
        height: auto;
        padding: 1;
        border: round white;
        border-title: "Help";
        border-title-style: bold;
    }

    .monster-ascii {
        color: red;
    }
    """

    BINDINGS = [
        ("q", "quit_app", "Quit the game"),
        ("n", "move_north", "Move North"),
        ("s", "move_south", "Move South"),
        ("e", "move_east", "Move East"),
        ("w", "move_west", "Move West"),
        ("i", "toggle_inventory", "Show/Hide Inventory"),
        ("t", "talk_npc", "Talk to NPC (if present)"),
        ("r", "run_away", "Try to Run from combat"),
        ("h", "toggle_help", "Toggle Help Panel"),
    ]

    def __init__(self):
        super().__init__()
        self.game = Game()
        self.log_messages: List[str] = []
        self.inventory_visible = False
        self.help_visible = False
        self.current_monster: Optional[str] = None
        self.in_combat = False

    def compose(self) -> ComposeResult:
        """Compose the TUI layout."""
        yield Header()
        yield Footer()

        with Container(id="main_container"):
            # Top bar (location info)
            with Container(id="top_bar"):
                yield Static(
                    Static("", id="location_display"),
                    id="location_panel",
                )

            # Middle: log & monster or exploration messages
            with Container():
                yield Static(
                    VerticalScroll(Static("", id="log_content")),
                    id="log_panel",
                )

            # Bottom bar: stats, quest info, etc.
            with Container(id="bottom_bar"):
                yield Static("", id="stats_display")

        # Inventory panel (initially hidden)
        yield Static(
            Static("", id="inventory_content"),
            id="inventory_panel",
            visible=False,
        )

        # Help panel (initially hidden)
        yield Static(
            "",
            id="help_panel",
            visible=False,
        )

    def on_mount(self) -> None:
        """Called once the UI has been mounted."""
        self._refresh_ui()

    def _refresh_ui(self) -> None:
        """Update all widgets with the current game state."""
        # Describe current location
        location_text = self.game.describe_location()
        location_display = self.query_one("#location_display", Static)
        location_display.update(location_text)

        # If we're not in combat, handle encounters & item pickups
        if not self.in_combat:
            found_items = self.game.pick_up_items()
            if found_items:
                self.log_messages.append(
                    f"[bold green]You found: {', '.join(found_items)}![/bold green]"
                )

            # Check for quest completion
            quest_completion_msgs = self.game.check_quest_completion()
            for msg in quest_completion_msgs:
                self.log_messages.append(msg)

            # Possibly trigger a boss fight or random encounter
            if self.game.initiate_boss_fight():
                self.in_combat = True
                self.handle_boss_fight()
            else:
                monster = self.game.random_encounter()
                if monster:
                    self.in_combat = True
                    self.current_monster = monster
                    self._show_monster(monster)
                    self.handle_monster_fight(monster)
                else:
                    self.log_messages.append(
                        "[dim]No enemies around... this time.[/dim]"
                    )

        # Update the log panel
        self._update_log_panel()

        # Update stats panel
        active_quests = [k for (k, v) in self.game.quests.items() if not v["completed"]]
        quests_list = ", ".join(active_quests) if active_quests else "None"
        stats_text = (
            f"[bold]HP[/bold]: {self.game.hp}   "
            f"[bold]Attack[/bold]: {self.game.attack}   "
            f"[bold]Quests[/bold]: {quests_list}"
        )
        stats_display = self.query_one("#stats_display", Static)
        stats_display.update(stats_text)

        # Show/hide panels as needed
        if self.inventory_visible:
            self._show_inventory()
        if self.help_visible:
            self._show_help()

    def _update_log_panel(self) -> None:
        """Update the log content to display recent messages."""
        log_content = self.query_one("#log_content", Static)
        log_content.update("\n".join(self.log_messages[-50:]))

    def _show_inventory(self) -> None:
        """Show the inventory panel and display items."""
        inventory_panel = self.query_one("#inventory_panel", Static)
        inventory_content = self.query_one("#inventory_content", Static)

        if not self.game.inventory:
            inventory_content.update("You have nothing in your inventory.")
        else:
            lines = [f"- {item}" for item in self.game.inventory]
            inventory_content.update("\n".join(lines))

        inventory_panel.visible = True

    def _hide_inventory(self) -> None:
        """Hide the inventory panel."""
        inventory_panel = self.query_one("#inventory_panel", Static)
        inventory_panel.visible = False

    def _show_help(self) -> None:
        """Show the help panel."""
        help_panel = self.query_one("#help_panel", Static)
        help_text = (
            "[bold]Controls:[/bold]\n"
            "  [bright_cyan]n[/bright_cyan] - Move north\n"
            "  [bright_cyan]s[/bright_cyan] - Move south\n"
            "  [bright_cyan]e[/bright_cyan] - Move east\n"
            "  [bright_cyan]w[/bright_cyan] - Move west\n"
            "  [bright_cyan]i[/bright_cyan] - Toggle inventory panel\n"
            "  [bright_cyan]t[/bright_cyan] - Talk to NPC\n"
            "  [bright_cyan]r[/bright_cyan] - Run away from combat\n"
            "  [bright_cyan]h[/bright_cyan] - Toggle this help panel\n"
            "  [bright_cyan]q[/bright_cyan] - Quit the game\n"
        )
        help_panel.update(help_text)
        help_panel.visible = True

    def _hide_help(self) -> None:
        """Hide the help panel."""
        help_panel = self.query_one("#help_panel", Static)
        help_panel.visible = False

    def _show_monster(self, monster: str) -> None:
        """Display monster ASCII art in the log."""
        ascii_lines = get_monster_ascii(monster)
        for line in ascii_lines:
            self.log_messages.append(f"[red]{line}[/red]")

    def handle_monster_fight(self, monster: str) -> None:
        """Resolve a random monster encounter."""
        combat_result = self.game.fight_monster(monster)
        for line in combat_result.split("\n"):
            self.log_messages.append(line)

        # Check if player died
        if self.game.hp <= 0:
            self.log_messages.append("[bold red]Game Over![/bold red]")
            self.log_messages.append("Press [bold]'q'[/bold] to quit.")
        else:
            # If still alive, exit combat
            self.in_combat = False
            self.current_monster = None
            # Check if the monster fight completes any quests
            quest_msgs = self.game.check_quest_completion()
            for msg in quest_msgs:
                self.log_messages.append(msg)

    def handle_boss_fight(self) -> None:
        """Resolve a boss fight if initiated."""
        boss_result = self.game.fight_boss()
        for line in boss_result.split("\n"):
            self.log_messages.append(line)

        if self.game.hp <= 0:
            self.log_messages.append("[bold red]Game Over![/bold red]")
            self.log_messages.append("Press [bold]'q'[/bold] to quit.")
        else:
            self.log_messages.append("[bold]The castle grows silent...[/bold]")
            self.game.check_quest_completion()
        self.in_combat = False

    # -------------------------
    # Textual Action Bindings
    # -------------------------
    def action_quit_app(self) -> None:
        """Quit the game entirely."""
        self.exit()

    def action_move_north(self) -> None:
        """Move the player north if not in combat."""
        if self.in_combat:
            self.log_messages.append(
                "[bold yellow]You can't move away while in combat![/bold yellow]"
            )
        else:
            self.game.move_player("north")
        self._refresh_ui()

    def action_move_south(self) -> None:
        """Move the player south if not in combat."""
        if self.in_combat:
            self.log_messages.append(
                "[bold yellow]You can't move away while in combat![/bold yellow]"
            )
        else:
            self.game.move_player("south")
        self._refresh_ui()

    def action_move_east(self) -> None:
        """Move the player east if not in combat."""
        if self.in_combat:
            self.log_messages.append(
                "[bold yellow]You can't move away while in combat![/bold yellow]"
            )
        else:
            self.game.move_player("east")
        self._refresh_ui()

    def action_move_west(self) -> None:
        """Move the player west if not in combat."""
        if self.in_combat:
            self.log_messages.append(
                "[bold yellow]You can't move away while in combat![/bold yellow]"
            )
        else:
            self.game.move_player("west")
        self._refresh_ui()

    def action_toggle_inventory(self) -> None:
        """Show or hide the inventory panel."""
        self.inventory_visible = not self.inventory_visible
        if self.inventory_visible:
            self._show_inventory()
        else:
            self._hide_inventory()
        self._update_log_panel()

    def action_talk_npc(self) -> None:
        """Talk to an NPC if present."""
        if self.in_combat:
            self.log_messages.append(
                "[bold yellow]You can't talk in the middle of combat![/bold yellow]"
            )
        else:
            npc_dialogue = self.game.talk_to_npc()
            if npc_dialogue:
                self.log_messages.append(npc_dialogue)
            else:
                self.log_messages.append("[dim]No one here to talk to.[/dim]")
        self._refresh_ui()

    def action_run_away(self) -> None:
        """Attempt to flee from combat (not valid in boss fights)."""
        if not self.in_combat or self.current_monster is None:
            self.log_messages.append(
                "[dim]You're not currently fighting anyone to flee from.[/dim]"
            )
        else:
            success = self.game.try_flee()
            if success:
                self.log_messages.append(
                    "[bold green]You successfully fled the battle![/bold green]"
                )
                self.in_combat = False
                self.current_monster = None
            else:
                self.log_messages.append(
                    "[bold red]You failed to flee and took a small hit![/bold red]"
                )
                if self.game.hp <= 0:
                    self.log_messages.append(
                        "[bold red]You have been defeated... Game Over![/bold red]"
                    )
                    self.log_messages.append("Press [bold]'q'[/bold] to quit.")
                    self.in_combat = False
                else:
                    self.log_messages.append(f"(Your HP: {self.game.hp})")
        self._refresh_ui()

    def action_toggle_help(self) -> None:
        """Show or hide the help panel."""
        self.help_visible = not self.help_visible
        if self.help_visible:
            self._show_help()
        else:
            self._hide_help()
        # Ensure new log messages appear
        self._update_log_panel()


def main():
    """Run the Textual TUI adventure game."""
    AdventureApp().run()


if __name__ == "__main__":
    main()
