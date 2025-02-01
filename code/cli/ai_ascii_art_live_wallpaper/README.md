# Random ASCII Art Generator

Random ASCII Art Generator is a command-line interface (CLI) application that continuously creates unique, tech-themed ASCII art images using OpenAI's API. It leverages the [Rich](https://github.com/Textualize/rich) library to render stylish output with a smooth drop-down animation effect.

## Features

- **Tech-Themed ASCII Art**: Generates art inspired by modern IT, cybersecurity, hacker culture, and futuristic digital aesthetics.
- **Live CLI Output**: Displays the generated ASCII art with an eye-catching drop-down animation.
- **Automatic Generation**: Runs continuously without user input until interrupted (Ctrl+C).
- **Loading Spinners**: Shows engaging loading animations while waiting for API responses.
- **Robust Logging**: Logs detailed information using a rotating file handler for easy debugging.

## Prerequisites

- Python 3.8 or later
- An OpenAI API key

## Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/yourusername/random-ascii-art-generator.git
   cd random-ascii-art-generator
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

   Ensure your `requirements.txt` contains:

   ```bash
   openai
   python-dotenv
   rich
   ```

4. **Set Up Your OpenAI API Key**

   Create a `.env` file in the project root with the following content:

   ```dotenv
   OPENAI_API_KEY=your_openai_api_key_here
   ```

## Usage

Run the application with:

```bash
python ai_ascii_art.py
```

The app will continuously generate tech-themed ASCII art until you press `Ctrl+C` to exit.

## Configuration

- **API Model**: The code uses `chatgpt-4o-latest` by default. Modify this in the source code if needed.
- **Display Duration**: Each generated ASCII art is shown for 6 seconds before the next one appears.
- **Logging**: Detailed logs are written to `chat_history.log` in the project directory.

## Contributing

Contributions are welcome! Please open issues or submit pull requests with improvements, bug fixes, or new features.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Disclaimer

This project uses the OpenAI API, which may incur costs. Monitor your usage and adhere to OpenAI's terms of service.
