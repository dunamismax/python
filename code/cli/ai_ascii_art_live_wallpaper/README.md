# Random ASCII Art Generator

Random ASCII Art Generator is a command-line interface (CLI) application that continuously creates unique ASCII art images using OpenAI's API. The app prints the generated art to the terminal and then displays a loading spinner with a "Loading..." message below the art for 10 seconds before generating the next piece. The entire process runs automatically until interrupted.

## Features

- **Unique ASCII Art**: Generates creative ASCII art images with complete artistic freedom.
- **Loading Indicator**: Displays a dynamic loading spinner and message beneath the art during a 5-second pause.
- **Continuous Operation**: Runs in an endless loop without requiring any user input.
- **Production-Grade Code**: Includes robust error handling, detailed logging, and a polished CLI interface using the [Rich](https://github.com/Textualize/rich) library.

## Prerequisites

- Python 3.8 or later
- An OpenAI API key

## Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/dunamismax/random-ascii-art-generator.git
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

   Ensure your `requirements.txt` includes:

   ```bash
   openai
   python-dotenv
   rich
   ```

4. **Configure Your OpenAI API Key**

   Create a `.env` file in the project root with the following content:

   ```dotenv
   OPENAI_API_KEY=your_openai_api_key_here
   ```

## Usage

Run the application with:

```bash
python ai_ascii_art.py
```

The app will continuously generate and display random ASCII art images with a loading spinner until you press `Ctrl+C` to exit.

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests. For any questions or suggestions, contact me at [dunamismax@tutamail.com](mailto:dunamismax@tutamail.com).

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
