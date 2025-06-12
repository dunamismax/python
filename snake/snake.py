#!/usr/bin/env python3
"""
A feature-rich Snake game implementation in Python using curses for terminal graphics.

Features:
- Dynamic terminal size detection with minimum size enforcement
- Smooth, consistent movement in all directions
- Colorful ASCII-based graphics
- Score tracking and high score system
- Pause functionality
- Game speed adjustments
- Multiple difficulty levels
- Obstacles mode
- Wall collision toggle
- Detailed in-game help
- Attractive game over screen with restart option
"""

import curses
import random
import time
import os
import json
from pathlib import Path
from typing import List, Tuple, Dict, Optional

# Game configuration constants
INITIAL_SPEED = 150  # Milliseconds between moves
SPEED_INCREMENT = 5  # Speed increase per food eaten
MIN_SPEED = 50  # Maximum speed cap
HIGH_SCORE_FILE = "snake_highscores.json"
MIN_WIDTH = 30  # Minimum terminal width
MIN_HEIGHT = 20  # Minimum terminal height

# Color pairs (curses color pairs start at 1)
COLOR_SNAKE_HEAD = 1
COLOR_SNAKE_BODY = 2
COLOR_FOOD = 3
COLOR_WALL = 4
COLOR_OBSTACLE = 5
COLOR_SCORE = 6
COLOR_GAME_OVER = 7
COLOR_MENU = 8
COLOR_HIGHLIGHT = 9


class Direction:
    """Enum-like class for movement directions"""
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @staticmethod
    def opposite(direction: Tuple[int, int]) -> Tuple[int, int]:
        """Return the opposite direction"""
        opposites = {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT
        }
        return opposites[direction]


class Point:
    """Represents a point in 2D space"""
    __slots__ = ('x', 'y')

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def __eq__(self, other) -> bool:
        return self.x == other.x and self.y == other.y

    def __add__(self, other: Tuple[int, int]) -> "Point":
        dx, dy = other
        return Point(self.x + dx, self.y + dy)

    def __str__(self) -> str:
        return f"({self.x}, {self.y})"


class Snake:
    """Represents the snake in the game"""

    def __init__(self, start_pos: Point, start_dir: Tuple[int, int]):
        self.body: List[Point] = [start_pos]
        self.direction: Tuple[int, int] = start_dir
        self.next_direction: Optional[Tuple[int, int]] = None
        self.growth_pending = 0

    def change_direction(self, new_dir: Tuple[int, int]):
        """Change direction if not moving in the opposite direction"""
        if new_dir != Direction.opposite(self.direction):
            self.next_direction = new_dir

    def move(self):
        """Move the snake in the current direction"""
        # Update direction if a new one is queued
        if self.next_direction:
            self.direction = self.next_direction
            self.next_direction = None

        # Calculate new head position
        head = self.body[0]
        new_head = head + self.direction

        # Add new head to body
        self.body.insert(0, new_head)

        # Remove tail if no growth is pending
        if self.growth_pending > 0:
            self.growth_pending -= 1
        else:
            self.body.pop()

    def grow(self, amount: int = 1):
        """Increase snake length"""
        self.growth_pending += amount

    def check_collision(self, point: Point) -> bool:
        """Check if snake collides with a point"""
        return any(segment == point for segment in self.body)

    def check_self_collision(self) -> bool:
        """Check if snake collides with itself"""
        head = self.body[0]
        return any(segment == head for segment in self.body[1:])


class Game:
    """Main game class containing all game logic and state"""

    def __init__(self, stdscr: curses.window):
        self.stdscr = stdscr
        self.score = 0
        self.high_score = 0
        self.speed = INITIAL_SPEED
        self.game_over = False
        self.paused = False
        self.walls_enabled = True
        self.obstacles_enabled = False
        self.difficulty = "Normal"
        self.obstacles: List[Point] = []

        # Initialize color pairs
        self.init_colors()

        # Load high scores
        self.high_scores = self.load_high_scores()

        # Set up game board
        self.init_game()

    def init_colors(self):
        """Initialize color pairs for curses"""
        curses.start_color()
        curses.init_pair(COLOR_SNAKE_HEAD, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(COLOR_SNAKE_BODY, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(COLOR_FOOD, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(COLOR_WALL, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(COLOR_OBSTACLE, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        curses.init_pair(COLOR_SCORE, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(COLOR_GAME_OVER, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(COLOR_MENU, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(COLOR_HIGHLIGHT, curses.COLOR_YELLOW, curses.COLOR_BLACK)

    def load_high_scores(self) -> Dict[str, int]:
        """Load high scores from file"""
        try:
            if Path(HIGH_SCORE_FILE).exists():
                with open(HIGH_SCORE_FILE, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {"Player": 0}

    def save_high_scores(self):
        """Save high scores to file"""
        try:
            with open(HIGH_SCORE_FILE, 'w') as f:
                json.dump(self.high_scores, f)
        except Exception:
            pass

    def update_high_score(self):
        """Update high score if current score is higher"""
        self.high_score = max(self.high_score, self.score)
        if self.score > self.high_scores.get("Player", 0):
            self.high_scores["Player"] = self.score
            self.save_high_scores()

    def init_game(self):
        """Initialize or reset game state"""
        # Get terminal dimensions
        self.height, self.width = self.stdscr.getmaxyx()

        # Ensure minimum terminal size
        if self.width < MIN_WIDTH or self.height < MIN_HEIGHT:
            self.show_size_warning()
            return

        # Define playable area (leave space for score and borders)
        self.play_height = self.height - 3
        self.play_width = self.width - 2

        # Initialize snake in center of screen
        start_x = self.play_width // 2
        start_y = self.play_height // 2
        self.snake = Snake(Point(start_x, start_y), Direction.RIGHT)

        # Place first food
        self.food = self.place_food()

        # Place obstacles if enabled
        self.obstacles = []
        if self.obstacles_enabled:
            self.generate_obstacles()

        # Reset game state
        self.score = 0
        self.speed = INITIAL_SPEED
        self.game_over = False
        self.paused = False

    def show_size_warning(self):
        """Display terminal size warning"""
        self.stdscr.clear()
        warning = "Terminal too small! Please resize to at least {}x{}".format(MIN_WIDTH, MIN_HEIGHT)
        self.stdscr.addstr(self.height // 2, (self.width - len(warning)) // 2, warning)
        self.stdscr.addstr(self.height // 2 + 1, (self.width - 20) // 2, "Press any key to retry...")
        self.stdscr.refresh()
        self.stdscr.getch()
        self.init_game()

    def place_food(self) -> Point:
        """Place food at a random location not occupied by snake or obstacles"""
        while True:
            x = random.randint(1, self.play_width - 2)
            y = random.randint(1, self.play_height - 2)
            food_pos = Point(x, y)

            # Check for collisions with snake and obstacles
            if not self.snake.check_collision(food_pos) and not any(
                    obs == food_pos for obs in self.obstacles
            ):
                return food_pos

    def generate_obstacles(self):
        """Generate obstacles in the play area"""
        num_obstacles = min(self.play_width * self.play_height // 20, 15)

        for _ in range(num_obstacles):
            while True:
                x = random.randint(1, self.play_width - 2)
                y = random.randint(1, self.play_height - 2)
                obstacle = Point(x, y)

                # Make sure obstacle doesn't spawn on snake or food
                if (not self.snake.check_collision(obstacle) and
                        obstacle != self.food and
                        all(obs != obstacle for obs in self.obstacles)):
                    self.obstacles.append(obstacle)
                    break

    def process_input(self):
        """Process keyboard input"""
        # Non-blocking key input
        self.stdscr.nodelay(True)
        key = self.stdscr.getch()

        # Direction controls
        if key == curses.KEY_UP or key == ord('w'):
            self.snake.change_direction(Direction.UP)
        elif key == curses.KEY_DOWN or key == ord('s'):
            self.snake.change_direction(Direction.DOWN)
        elif key == curses.KEY_LEFT or key == ord('a'):
            self.snake.change_direction(Direction.LEFT)
        elif key == curses.KEY_RIGHT or key == ord('d'):
            self.snake.change_direction(Direction.RIGHT)
        # Game controls
        elif key == ord('p'):
            self.paused = not self.paused
        elif key == ord('+') or key == ord('='):
            self.speed = max(MIN_SPEED, self.speed - 10)
        elif key == ord('-'):
            self.speed += 10
        elif key == ord('r'):
            self.init_game()
        elif key == ord('q'):
            self.game_over = True
        elif key == ord('?'):
            self.show_help()

    def update(self):
        """Update game state"""
        if self.paused or self.game_over:
            return

        # Move snake
        self.snake.move()

        # Get snake head position
        head = self.snake.body[0]

        # Check for collisions with walls if enabled
        if self.walls_enabled and (
                head.x <= 0 or head.x >= self.play_width or
                head.y <= 0 or head.y >= self.play_height
        ):
            self.game_over = True
            self.update_high_score()
            return

        # Check for collisions with obstacles
        if any(obs == head for obs in self.obstacles):
            self.game_over = True
            self.update_high_score()
            return

        # Check for self-collision
        if self.snake.check_self_collision():
            self.game_over = True
            self.update_high_score()
            return

        # Check for food collision
        if head == self.food:
            # Grow snake and place new food
            self.snake.grow(1 + (self.difficulty == "Hard"))
            self.food = self.place_food()

            # Increase score and speed
            self.score += 10
            self.speed = max(MIN_SPEED, self.speed - SPEED_INCREMENT)

    def draw(self):
        """Draw the game state to the screen"""
        self.stdscr.clear()

        # Draw borders
        self.stdscr.attron(curses.color_pair(COLOR_WALL))
        for x in range(0, self.play_width + 1):
            self.stdscr.addch(0, x, '#')
            self.stdscr.addch(self.play_height, x, '#')
        for y in range(0, self.play_height + 1):
            self.stdscr.addch(y, 0, '#')
            self.stdscr.addch(y, self.play_width, '#')
        self.stdscr.attroff(curses.color_pair(COLOR_WALL))

        # Draw obstacles
        if self.obstacles_enabled:
            self.stdscr.attron(curses.color_pair(COLOR_OBSTACLE))
            for obstacle in self.obstacles:
                self.stdscr.addch(obstacle.y, obstacle.x, '▓')
            self.stdscr.attroff(curses.color_pair(COLOR_OBSTACLE))

        # Draw food
        self.stdscr.attron(curses.color_pair(COLOR_FOOD))
        self.stdscr.addch(self.food.y, self.food.x, '*')
        self.stdscr.attroff(curses.color_pair(COLOR_FOOD))

        # Draw snake
        for i, segment in enumerate(self.snake.body):
            if i == 0:  # Snake head
                self.stdscr.attron(curses.color_pair(COLOR_SNAKE_HEAD))
                self.stdscr.addch(segment.y, segment.x, '@')
                self.stdscr.attroff(curses.color_pair(COLOR_SNAKE_HEAD))
            else:  # Snake body
                self.stdscr.attron(curses.color_pair(COLOR_SNAKE_BODY))
                self.stdscr.addch(segment.y, segment.x, 'o')
                self.stdscr.attroff(curses.color_pair(COLOR_SNAKE_BODY))

        # Draw score
        self.stdscr.attron(curses.color_pair(COLOR_SCORE))
        score_text = f"Score: {self.score} | High Score: {self.high_score} | Speed: {INITIAL_SPEED - self.speed + MIN_SPEED}"
        self.stdscr.addstr(self.play_height + 1, 1, score_text)

        # Draw difficulty
        diff_text = f"Difficulty: {self.difficulty}"
        self.stdscr.addstr(self.play_height + 1, self.width - len(diff_text) - 1, diff_text)

        # Draw controls hint
        controls_text = "P: Pause  ?: Help  +/-: Speed  Q: Quit  R: Restart"
        self.stdscr.addstr(self.play_height + 2, (self.width - len(controls_text)) // 2, controls_text)
        self.stdscr.attroff(curses.color_pair(COLOR_SCORE))

        # Draw pause indicator
        if self.paused:
            pause_text = "*** PAUSED ***"
            self.stdscr.attron(curses.color_pair(COLOR_HIGHLIGHT))
            self.stdscr.addstr(self.play_height // 2, (self.play_width - len(pause_text)) // 2, pause_text)
            self.stdscr.attroff(curses.color_pair(COLOR_HIGHLIGHT))

        # Draw game over screen
        if self.game_over:
            self.draw_game_over()

        self.stdscr.refresh()

    def draw_game_over(self):
        """Draw game over screen"""
        # Semi-transparent overlay
        for y in range(self.play_height // 2 - 5, self.play_height // 2 + 6):
            for x in range(self.play_width // 2 - 15, self.play_width // 2 + 16):
                if 0 <= x < self.play_width and 0 <= y < self.play_height:
                    self.stdscr.addch(y, x, ' ', curses.A_REVERSE)

        # Game over text
        game_over_text = "GAME OVER"
        self.stdscr.attron(curses.color_pair(COLOR_GAME_OVER) | curses.A_BOLD)
        self.stdscr.addstr(self.play_height // 2 - 3, (self.play_width - len(game_over_text)) // 2, game_over_text)

        # Score display
        score_text = f"Final Score: {self.score}"
        self.stdscr.addstr(self.play_height // 2 - 1, (self.play_width - len(score_text)) // 2, score_text)

        # High score display
        high_score_text = f"High Score: {self.high_score}"
        self.stdscr.addstr(self.play_height // 2, (self.play_width - len(high_score_text)) // 2, high_score_text)

        # Restart prompt
        restart_text = "Press 'R' to restart or 'Q' to quit"
        self.stdscr.addstr(self.play_height // 2 + 3, (self.play_width - len(restart_text)) // 2, restart_text)
        self.stdscr.attroff(curses.color_pair(COLOR_GAME_OVER) | curses.A_BOLD)

    def show_help(self):
        """Show help screen"""
        # Darken the game area
        for y in range(1, self.play_height):
            for x in range(1, self.play_width):
                self.stdscr.addch(y, x, ' ', curses.A_DIM)

        # Help content
        help_lines = [
            "SNAKE GAME CONTROLS",
            "",
            "Direction: Arrow Keys or WASD",
            "Pause/Resume: P",
            "Increase Speed: +",
            "Decrease Speed: -",
            "Restart Game: R",
            "Quit Game: Q",
            "Show Help: ?",
            "",
            "GAME OPTIONS",
            "",
            "Difficulty:",
            "  Easy   - Snake grows slowly",
            "  Normal - Standard growth",
            "  Hard   - Snake grows faster",
            "",
            "Obstacles:",
            "  Enable/Disable with O key",
            "",
            "Walls:",
            "  Enable/Disable with W key",
            "",
            "Press any key to continue..."
        ]

        # Draw help box
        box_height = len(help_lines) + 4
        box_width = max(len(line) for line in help_lines) + 4

        start_y = (self.play_height - box_height) // 2
        start_x = (self.play_width - box_width) // 2

        # Draw box border
        self.stdscr.attron(curses.color_pair(COLOR_MENU))
        for y in range(start_y, start_y + box_height):
            for x in range(start_x, start_x + box_width):
                if y == start_y or y == start_y + box_height - 1:
                    self.stdscr.addch(y, x, '-')
                elif x == start_x or x == start_x + box_width - 1:
                    self.stdscr.addch(y, x, '|')

        # Draw corners
        self.stdscr.addch(start_y, start_x, '+')
        self.stdscr.addch(start_y, start_x + box_width - 1, '+')
        self.stdscr.addch(start_y + box_height - 1, start_x, '+')
        self.stdscr.addch(start_y + box_height - 1, start_x + box_width - 1, '+')

        # Draw help text
        for i, line in enumerate(help_lines):
            self.stdscr.addstr(start_y + i + 2, start_x + 2, line)

        self.stdscr.attroff(curses.color_pair(COLOR_MENU))
        self.stdscr.refresh()

        # Wait for key press
        self.stdscr.nodelay(False)
        self.stdscr.getch()

    def main_menu(self):
        """Show main menu and handle game settings"""
        selection = 0
        options = [
            "Start Game",
            f"Difficulty: {self.difficulty}",
            f"Obstacles: {'On' if self.obstacles_enabled else 'Off'}",
            f"Walls: {'On' if self.walls_enabled else 'Off'}",
            "Quit"
        ]

        while True:
            self.stdscr.clear()
            self.stdscr.attron(curses.color_pair(COLOR_MENU))

            # Draw title
            title = "PYTHON SNAKE GAME"
            self.stdscr.addstr(2, (self.width - len(title)) // 2, title)

            # Draw subtitle
            subtitle = "Use Arrow Keys and Enter to select"
            self.stdscr.addstr(4, (self.width - len(subtitle)) // 2, subtitle)

            # Draw options
            for i, option in enumerate(options):
                x = (self.width - len(option)) // 2
                y = self.height // 2 - len(options) // 2 + i

                if i == selection:
                    self.stdscr.attron(curses.color_pair(COLOR_HIGHLIGHT) | curses.A_BOLD)
                    self.stdscr.addstr(y, x - 2, "> ")
                    self.stdscr.addstr(y, x, option)
                    self.stdscr.addstr(y, x + len(option), " <")
                    self.stdscr.attroff(curses.color_pair(COLOR_HIGHLIGHT) | curses.A_BOLD)
                else:
                    self.stdscr.addstr(y, x, option)

            self.stdscr.attroff(curses.color_pair(COLOR_MENU))
            self.stdscr.refresh()

            # Handle input
            key = self.stdscr.getch()
            if key == curses.KEY_UP:
                selection = (selection - 1) % len(options)
            elif key == curses.KEY_DOWN:
                selection = (selection + 1) % len(options)
            elif key == curses.KEY_LEFT or key == curses.KEY_RIGHT:
                if selection == 1:  # Difficulty
                    difficulties = ["Easy", "Normal", "Hard"]
                    current_index = difficulties.index(self.difficulty)
                    new_index = (current_index + (1 if key == curses.KEY_RIGHT else -1)) % len(difficulties)
                    self.difficulty = difficulties[new_index]
                    options[1] = f"Difficulty: {self.difficulty}"
                elif selection == 2:  # Obstacles
                    self.obstacles_enabled = not self.obstacles_enabled
                    options[2] = f"Obstacles: {'On' if self.obstacles_enabled else 'Off'}"
                elif selection == 3:  # Walls
                    self.walls_enabled = not self.walls_enabled
                    options[3] = f"Walls: {'On' if self.walls_enabled else 'Off'}"
            elif key in [curses.KEY_ENTER, 10, 13]:  # Enter key
                if selection == 0:  # Start Game
                    return True
                elif selection == 4:  # Quit
                    return False

            time.sleep(0.1)

    def run(self):
        """Main game loop"""
        if not self.main_menu():
            return

        self.init_game()
        last_update_time = time.time()

        while not self.game_over:
            current_time = time.time()

            # Process input
            self.process_input()

            # Update game state at appropriate intervals
            if current_time - last_update_time >= self.speed / 1000.0:
                self.update()
                last_update_time = current_time

            # Draw game state
            self.draw()

            # Small delay to prevent CPU overuse
            time.sleep(0.001)

        # Keep showing game over screen until restart or quit
        while self.game_over:
            self.process_input()
            self.draw()
            time.sleep(0.05)

        # Restart game if requested
        self.run()


def main(stdscr: curses.window):
    """Main function to initialize and run the game"""
    # Set up terminal
    curses.curs_set(0)  # Hide cursor
    stdscr.keypad(True)  # Enable keypad input
    stdscr.timeout(0)  # Non-blocking input

    # Initialize and run game
    game = Game(stdscr)
    game.run()


if __name__ == "__main__":
    # Initialize curses and run main function
    curses.wrapper(main)