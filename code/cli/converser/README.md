# Converser: Terminal-Based AI Bot Conversation

Converser is a robust, terminal-based chat interface that simulates conversations between AI bots. It leverages the latest OpenAI API (v1.0+), the Rich CLI library, and a custom Nord color theme to deliver a visually engaging and interactive experience in your Linux terminal. Out-of-the-box, Converser includes an example conversation between two archetypal bots—**God** and **Satan**—but it is completely customizable to suit your own scenarios.

## Features

- **Interactive CLI:**
  Built using [Rich](https://github.com/willmcgugan/rich) to create a visually appealing and responsive terminal interface.

- **Nord Color Theme:**
  Enjoy a consistent and modern visual style using the popular Nord color palette throughout the UI.

- **Typewriter Effect:**
  Bot responses are rendered character-by-character to simulate a dynamic, human-like conversation.

- **Thinking Spinner:**
  A spinner continuously indicates that the AI is "thinking" (with a configurable delay) before printing the response.

- **Markdown Logging:**
  Every conversation is logged in Markdown format to rotating files for easy review and traceability.

- **Customizable Bot Prompts:**
  Easily adjust bot names, system prompts, and behavior via the provided `.env` file.

- **Production-Grade Code:**
  Designed with threading, robust error handling, and modular architecture for maintainability and extensibility.

## Installation

### Prerequisites

- Linux (or any Unix-like OS)
- Python 3.8 or higher
- pip

### Steps

1. **Clone the Repository**

   ```bash
   git clone https://github.com/yourusername/converser.git
   cd converser
   ```

2. **Create a Virtual Environment**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Dependencies**

   Install required packages using pip:

   ```bash
   pip install openai python-dotenv rich
   ```

   Alternatively, if a `requirements.txt` is provided:

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**

   Rename the example environment file to `.env` (or create your own) and customize the values as needed. See [Configuration](#configuration) below.

## Usage

After installation and configuration, run the program with:

```bash
python converser.py
```

Follow the on-screen prompts to begin a conversation. You can either enter your own conversation starter or let the AI generate one for you.

## Configuration

Converser is highly customizable through the `.env` file. Key configuration settings include:

- **OpenAI Credentials and Model:**
  - `OPENAI_API_KEY`: Your OpenAI API key.
  - `OPENAI_MODEL`: The model to use (default is `o3-mini`).

- **Thinking Delay Settings (in seconds):**
  - `FIRST_RESPONSE_DELAY`: Delay before the first bot response.
  - `SUBSEQUENT_RESPONSE_DELAY`: Delay before each subsequent response.

- **Bot Configuration:**
  - **BOT_1 (Example: God)**
    - `BOT_1_NAME`: Name for the first bot.
    - `BOT_1_PROMPT`: The system prompt defining the personality and behavior of the first bot.
  - **BOT_2 (Example: Satan)**
    - `BOT_2_NAME`: Name for the second bot.
    - `BOT_2_PROMPT`: The system prompt defining the personality and behavior of the second bot.

## Customization

The provided `.env` file gives you a starting point with two sample bots:

### Example: God vs Satan

- **God:**
  Portrayed as an unyielding, brutal arbiter of cosmic truth and order. God’s responses are delivered with raw, uncompromising authority, dispensing harsh judgment without mercy.

- **Satan:**
  Embodied as a relentless, merciless challenger who spares no one from the harsh truths of existence. Satan’s language is unfiltered and brutally realistic, provoking critical reflection through savage candor.

You can easily change these personas by editing the following keys in the `.env` file:

```dotenv
BOT_1_NAME=God
BOT_1_PROMPT="Your custom prompt for God – the unyielding arbiter of cosmic truth and order. [Customize with your own tone and principles.] Never break character."

BOT_2_NAME=Satan
BOT_2_PROMPT="Your custom prompt for Satan – the relentless, merciless challenger who exposes the raw truths of existence. [Customize with your own tone and principles.] Never break character."
```

You are free to define any number of personalities or scenarios. Simply modify the names, prompts, and even the delay settings to suit your conversation simulation needs.

## Contributing

Contributions are welcome! Please fork the repository and open a pull request with your improvements or bug fixes. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the [MIT License](LICENSE).

## Acknowledgements

- [Rich](https://github.com/willmcgugan/rich) for the beautiful terminal UI.
- [Nord Theme](https://www.nordtheme.com/) for the inspiring color palette.
- [OpenAI](https://openai.com/) for their cutting-edge AI models and APIs.

## Running on Linux

To run Converser on a Linux system, follow these commands in your terminal:

```bash
# Clone the repository
git clone https://github.com/yourusername/converser.git
cd converser

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install openai python-dotenv rich

# Configure your environment variables (edit the .env file)
nano .env

# Run the application
python converser.py
```python

Enjoy your terminal-based AI bot conversation experience!
```
