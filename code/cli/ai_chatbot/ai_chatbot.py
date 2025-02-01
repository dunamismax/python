import os
import sys
from openai import OpenAI  # Use the new client-based import.
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt
from rich.theme import Theme
from rich.panel import Panel

# Define Nord theme colors based on the Nord palette.
nord_theme = Theme(
    {
        "bot": "#81A1C1",  # nord9
        "user": "#A3BE8C",  # nord14
        "system": "#8FBCBB",  # nord7
        "info": "#88C0D0",  # nord8
        "warning": "#EBCB8B",  # nord13
        "error": "#BF616A",  # nord11
    }
)

console = Console(theme=nord_theme)

# Load environment variables from .env file.
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    console.print("[error]Error: OPENAI_API_KEY not found in environment.[/error]")
    sys.exit(1)

# Instantiate the client with your API key.
client = OpenAI(api_key=OPENAI_API_KEY)

# Define a list of chatbots with custom system prompts.
chatbots = [
    {
        "name": "ChatGPT Assistant",
        "system_prompt": "You are a helpful and friendly assistant. Provide concise and accurate answers.",
    },
    {
        "name": "Tech Guru",
        "system_prompt": "You are an expert in technology and programming. Answer technical questions in detail.",
    },
    {
        "name": "Creative Writer",
        "system_prompt": "You are a creative writer who crafts engaging stories and poetry. Respond imaginatively.",
    },
]


def select_chatbot() -> dict:
    """Display a menu of chatbots and return the selected bot configuration."""
    console.print(Panel("[info]Select a Chatbot:[/info]", expand=False))
    for idx, bot in enumerate(chatbots, start=1):
        console.print(f"[info]{idx}. {bot['name']}[/info]")
    while True:
        choice = Prompt.ask(
            "[user]Enter the number of the chatbot (or 'q' to quit)[/user]"
        )
        if choice.lower() in {"q", "quit", "exit"}:
            sys.exit(0)
        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(chatbots):
                return chatbots[index - 1]
        console.print("[warning]Invalid selection. Please try again.[/warning]")


def chat_session(bot_config: dict) -> None:
    """Start a chat session with the selected chatbot."""
    console.print(
        Panel(
            f"[system]Starting chat session with {bot_config['name']}[/system]",
            expand=False,
        )
    )
    # Initialize the conversation with the system prompt.
    messages = [{"role": "system", "content": bot_config["system_prompt"]}]
    while True:
        try:
            user_input = Prompt.ask("[user]You[/user]")
            if user_input.lower() in {"exit", "quit"}:
                console.print("[info]Exiting chat session...[/info]")
                break

            messages.append({"role": "user", "content": user_input})

            # Inform the user that the assistant is typing.
            console.print("[bot]Assistant:[/bot] ", end="", style="bot")
            response_text = ""

            try:
                # Use the new client-instance API for streaming.
                response = client.chat.completions.create(
                    model="chatgpt-4o-latest",
                    messages=messages,
                    stream=True,
                )
                # Stream tokens as they are generated.
                for chunk in response:
                    # Check if the token content exists and print it.
                    if chunk.choices[0].delta.content is not None:
                        token = chunk.choices[0].delta.content
                        response_text += token
                        console.print(token, end="", style="bot", soft_wrap=True)
                console.print()  # Newline after the streamed response.
            except Exception as e:
                console.print(f"\n[error]Error during API call: {e}[/error]")
                continue

            # Append the assistant's full reply to the message history.
            messages.append({"role": "assistant", "content": response_text})
        except KeyboardInterrupt:
            console.print("\n[info]Chat session terminated by user.[/info]")
            break


def main() -> None:
    """Main function that drives the chatbot CLI app."""
    console.print(Panel("[info]Welcome to the AI Chatbot CLI App[/info]", expand=False))
    while True:
        bot_config = select_chatbot()
        chat_session(bot_config)
        # After a session, ask the user if they want to choose another chatbot.
        cont = Prompt.ask(
            "[info]Do you want to choose another chatbot? (y/n)[/info]", default="y"
        )
        if cont.lower() not in {"y", "yes"}:
            console.print("[info]Goodbye![/info]")
            break


if __name__ == "__main__":
    main()
