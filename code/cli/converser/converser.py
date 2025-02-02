import os
import time
import logging
from logging.handlers import RotatingFileHandler
from typing import Dict, List, Optional

from dotenv import load_dotenv
from rich.console import Console
from rich.theme import Theme
from rich.panel import Panel
from rich.status import Status
from rich.text import Text
from openai import OpenAI

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
load_dotenv()

# OpenAI Configuration
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "chatgpt-4o-latest")

# Timing Configuration
THINKING_DELAY = int(os.getenv("THINKING_DELAY", "20"))

# Logging Configuration
MAX_LOG_SIZE = int(os.getenv("MAX_LOG_SIZE", "10485760"))  # 10MB
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "3"))

# -----------------------------------------------------------------------------
# Bot Configurations
# -----------------------------------------------------------------------------
BOT_1 = {
    "name": os.getenv("BOT_1_NAME", "bot-1"),
    "system_prompt": os.getenv(
        "BOT_1_PROMPT",
        """You are bot-1 – a thoughtful and engaging conversationalist. Never break character.

Core Psychology:
- Believes that every conversation is an opportunity to learn and grow.
""",
    ),
    "style": os.getenv("BOT_1_STYLE", "bot-1"),
}

BOT_2 = {
    "name": os.getenv("BOT_2_NAME", "bot-2"),
    "system_prompt": os.getenv(
        "BOT_2_PROMPT",
        """You are bot-2 – a direct and analytical debater. Never break character.

Core Psychology:
- Believes that truth is best uncovered through rigorous questioning.
""",
    ),
    "style": os.getenv("BOT_2_STYLE", "bot-2"),
}

# -----------------------------------------------------------------------------
# Rich Console Setup with Nord Theme
# -----------------------------------------------------------------------------
nord_theme = Theme(
    {
        "bot-1": "#A3BE8C bold",
        "bot-2": "#BF616A bold",
        "system": "#81A1C1",
        "status": "#B48EAD",
        "title": "#88C0D0 bold",
        "muted": "#4C566A",
        "error": "#BF616A",
    }
)

console = Console(theme=nord_theme, width=100)


# -----------------------------------------------------------------------------
# Logging Setup
# -----------------------------------------------------------------------------
def setup_markdown_logger() -> logging.Logger:
    """Configure markdown logging with timestamps and bot formatting."""

    class MarkdownFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            timestamp = self.formatTime(record, datefmt="%Y-%m-%d %H:%M:%S")
            persona = getattr(record, "persona", "system")
            message = (record.getMessage() or "").strip()
            if persona == "system":
                return f"\n### {timestamp} - System Message\n{message}\n"
            elif persona == BOT_1["name"]:
                return f"\n#### {timestamp} - {BOT_1['name']}\n{message}\n"
            elif persona == BOT_2["name"]:
                return f"\n#### {timestamp} - {BOT_2['name']}\n{message}\n"
            else:
                return f"\n#### {timestamp} - {persona}\n{message}\n"

    logger = logging.getLogger("conversation")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        os.makedirs("logs", exist_ok=True)
        log_path = "logs/conversation_log.md"
        handler = RotatingFileHandler(
            log_path,
            maxBytes=MAX_LOG_SIZE,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        if not os.path.exists(log_path) or os.path.getsize(log_path) == 0:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("# AI Personality Dialogue Log\n\n")
                f.write(
                    f"*An eternal conversation between {BOT_1['name']} and {BOT_2['name']}*\n\n"
                )
                f.write("---\n")
        handler.setFormatter(MarkdownFormatter())
        logger.addHandler(handler)
    return logger


# -----------------------------------------------------------------------------
# OpenAI API Helper
# -----------------------------------------------------------------------------
def get_ai_response(
    client: OpenAI, messages: List[Dict[str, str]], status_message: Optional[str] = None
) -> str:
    """Get response from OpenAI API with robust error handling."""
    try:
        completion = client.chat.completions.create(
            model=DEFAULT_MODEL, messages=messages
        )
        content = completion.choices[0].message.content
        return (
            content.strip()
            if content is not None
            else "I need a moment to collect my thoughts."
        )
    except Exception as e:
        console.print(f"[error]API Error: {str(e)}[/error]")
        return "I encountered an error in generating my response."


# -----------------------------------------------------------------------------
# Display Utilities
# -----------------------------------------------------------------------------
def display_message(speaker: str, message: Optional[str], style: str) -> None:
    """Display a message using a Rich panel with null safety."""
    try:
        cleaned_message = str(
            message or "I need a moment to collect my thoughts."
        ).strip()
        panel = Panel(
            Text(cleaned_message),
            title=f"[{style}]{speaker}[/{style}]",
            border_style=style,
            subtitle=f"[{style}]{time.strftime('%H:%M:%S')}[/{style}]",
        )
        console.print(panel)
    except Exception as e:
        console.print(f"[error]Display error: {str(e)}[/error]")
        console.print(f"[{style}]{speaker}[/{style}]: {cleaned_message}")


def get_response_with_delay(
    client: OpenAI,
    messages: List[Dict[str, str]],
    delay: int,
    status_message: str,
    speaker: str,
    style: str,
) -> str:
    """
    Wait for the thinking delay (with a spinner), get the AI response,
    and then display it.
    """
    try:
        with Status(f"[status]{status_message}[/status]", spinner="dots"):
            time.sleep(delay)
            response = get_ai_response(client, messages)
        display_message(speaker, response, style)
        return response
    except Exception as e:
        console.print(f"[error]Error in get_response_with_delay: {str(e)}[/error]")
        fallback = "I encountered an error in processing."
        display_message(speaker, fallback, style)
        return fallback


# -----------------------------------------------------------------------------
# Core Conversation Logic
# -----------------------------------------------------------------------------
def run_conversation() -> None:
    """Run the endless conversation between two AI bot personas."""
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")

        client = OpenAI(api_key=api_key)
        logger = setup_markdown_logger()

        # Initialize display
        console.clear()
        console.print("[title]AI Personality Dialogue[/title]")
        console.print(
            f"[muted]An eternal conversation between {BOT_1['name']} and {BOT_2['name']}[/muted]\n"
        )

        # Generate conversation starter
        with Status(
            "[status]Generating conversation starter...[/status]", spinner="dots"
        ):
            current_topic = get_ai_response(
                client,
                [
                    {
                        "role": "system",
                        "content": (
                            "You are a master of creating engaging conversation starters that:\n"
                            "1. Are thought-provoking but not controversial\n"
                            "2. Include specific, relatable examples\n"
                            "3. Allow for multiple perspectives\n"
                            "4. Are 2-3 sentences maximum\n"
                            "5. Avoid rhetorical questions\n"
                            "6. Use natural, conversational language\n\n"
                            "Respond ONLY with the conversation starter itself."
                        ),
                    },
                    {
                        "role": "user",
                        "content": "Generate an engaging conversation starter.",
                    },
                ],
            )

        # Display and log the initial topic
        console.print(
            Panel(Text(current_topic), title="[title]Conversation Starter[/title]")
        )
        logger.info(current_topic, extra={"persona": "system"})

        # Initialize message histories for both bots
        bot1_messages = [
            {"role": "system", "content": BOT_1["system_prompt"]},
            {"role": "user", "content": current_topic},
        ]
        bot2_messages = [
            {"role": "system", "content": BOT_2["system_prompt"]},
        ]

        # Main conversation loop
        while True:
            # Bot 1 cycle
            bot1_response = get_response_with_delay(
                client,
                bot1_messages,
                THINKING_DELAY,
                f"{BOT_1['name']} is thinking...",
                BOT_1["name"],
                BOT_1["style"],
            )
            logger.info(bot1_response, extra={"persona": BOT_1["name"]})
            bot1_messages.append({"role": "assistant", "content": bot1_response})
            bot2_messages.append({"role": "user", "content": bot1_response})
            time.sleep(1)

            # Bot 2 cycle
            bot2_response = get_response_with_delay(
                client,
                bot2_messages,
                THINKING_DELAY,
                f"{BOT_2['name']} is thinking...",
                BOT_2["name"],
                BOT_2["style"],
            )
            logger.info(bot2_response, extra={"persona": BOT_2["name"]})
            bot2_messages.append({"role": "assistant", "content": bot2_response})
            bot1_messages.append({"role": "user", "content": bot2_response})
            time.sleep(1)

    except KeyboardInterrupt:
        console.print("\n[system]Conversation ended by user[/system]")
        logger.info("Conversation ended by user", extra={"persona": "system"})
    except Exception as e:
        console.print(f"\n[error]Critical error: {str(e)}[/error]")
        logger.error(str(e), exc_info=True)


if __name__ == "__main__":
    try:
        run_conversation()
    except Exception as e:
        console = Console(theme=nord_theme)
        console.print(f"[error]Error: {str(e)}[/error]")
        logging.error(str(e), exc_info=True)
