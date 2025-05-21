# Random ASCII Art Live Wallpaper

**dunamismax ai ascii generator** is a command-line application that continuously creates unique ASCII art images using OpenAI's API. The app features interactive configuration at startup, letting you choose the AI model and the pause duration between art generations. The generated art is displayed with a persistent header and a live loading spinner beneath it during the pause period. If you interrupt the process (Ctrl+C), you'll have the option to return to the main menu for reconfiguration or to exit gracefully.

## Features

- **Interactive Configuration:**
  Select from several AI models (`o3-mini`, `chatgpt-4o-latest`, `gpt-4o-mini`, `o1-mini`, `o1`, `gpt-4o`) and choose a pause duration (in seconds) from preset options (3, 5, 10, 15, 30, 60, 180, 360).

- **Dynamic ASCII Art Generation:**
  Generates creative and unique ASCII art images with complete artistic freedom.

- **Enhanced CLI Experience:**
  Displays a persistent left-aligned header ("dunamismax ai ascii generator") and uses Rich's advanced features—including live loading indicators and animated transitions—for a polished terminal interface.

- **Resilient Operation:**
  Runs continuously with robust error handling and detailed logging. When interrupted (Ctrl+C), the app prompts whether to return to the main menu for reconfiguration or quit.

## Prerequisites

- Python 3.8 or later
- An OpenAI API key

## Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/dunamismax/random-ascii-art-generator.git
   cd random-ascii-art-generator/python/code/cli/ai_ascii_art_live_wallpaper
   ```

2. **Create a Virtual Environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # On Windows: .venv\Scripts\activate
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

   Your `requirements.txt` should include:
   ```
   openai
   python-dotenv
   rich
   ```

4. **Configure Your OpenAI API Key**

   Create a `.env` file in the project root (within the `ai_ascii_art_live_wallpaper` folder) with the following content:

   ```dotenv
   OPENAI_API_KEY=your_openai_api_key_here
   ```

## Usage

Run the application with:

```bash
python ai_ascii_live.py
```

At startup, you'll be prompted to select an AI model and a pause duration between art generations. The app will then continuously generate and display ASCII art, showing a live loading spinner beneath the art for the chosen pause duration. If you press `Ctrl+C`, you'll be asked whether to return to the main menu for reconfiguration or to quit.

## Project Structure

```
└── 📁python
    └── 📁code
        └── 📁cli
            └── 📁ai_ascii_art_live_wallpaper
                ├── .env
                ├── ai_ascii_live.py
                ├── chat_history.log
                ├── README.md
                └── requirements.txt
            └── 📁ai_chatbot
                ├── .env
                ├── ai_chatbot.py
                ├── chat_history.log
                └── requirements.txt
            └── 📁weather
        └── 📁games
        └── 📁gui
        └── 📁tui
    └── .gitignore
    └── LICENSE
    └── README.md
```

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests. For any questions or suggestions, contact me at [dunamismax@tutamail.com](mailto:dunamismax@tutamail.com).

## License

This project is licensed under the MIT License. See the [LICENSE](../LICENSE) file for details.
