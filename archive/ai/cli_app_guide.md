# Nord-themed CLI Application Development Guidelines

When creating a CLI application, please follow these design patterns and specifications to ensure a consistent, user-friendly experience using the Nord color scheme and Rich library features.

## Core Requirements

The application should be built using:

- Python 3.x
- Rich library for terminal formatting
- python-dotenv for environment variable management
- Nord color scheme for visual consistency

## Nord Theme Color Specifications

Use these color codes for consistent theming:

### Polar Night (dark/background)

- NORD0 = "#2E3440" (Dark background)
- NORD1 = "#3B4252" (Lighter background)
- NORD2 = "#434C5E" (Selection background)
- NORD3 = "#4C566A" (Inactive text)

### Snow Storm (light/text)

- NORD4 = "#D8DEE9" (Text)
- NORD5 = "#E5E9F0" (Light text)
- NORD6 = "#ECEFF4" (Bright text)

### Frost (cool accents)

- NORD7 = "#8FBCBB" (Mint)
- NORD8 = "#88C0D0" (Light blue)
- NORD9 = "#81A1C1" (Medium blue)
- NORD10 = "#5E81AC" (Dark blue)

### Aurora (warm accents)

- NORD11 = "#BF616A" (Red)
- NORD12 = "#D08770" (Orange)
- NORD13 = "#EBCB8B" (Yellow)
- NORD14 = "#A3BE8C" (Green)
- NORD15 = "#B48EAD" (Purple)

## Required Application Components

### 1. Configuration Management

- Use a Config dataclass for application settings
- Include version information
- Support debug mode toggle
- Allow environment variable overrides
- Implement configuration validation

### 2. Logging System

- Configure both file and console logging
- Use rotating log files with size limits
- Include timestamps and log levels
- Maintain log file organization
- Use Rich formatting for console logs

### 3. User Interface Elements

Implement these Rich components with Nord theming:

- Headers with panels
- Progress bars with spinners
- Interactive tables
- User input prompts
- Markdown rendering
- Error messages
- Success notifications

### 4. Error Handling

Include comprehensive error handling for:

- User interruptions (Ctrl+C)
- Configuration errors
- Runtime exceptions
- Input validation
- Resource management
- Graceful exit procedures

## Theme Configuration

Apply these Rich theme styles:

```python
THEME_CONFIG = {
    "info": "Nord8 color",
    "warning": "Nord13 color",
    "error": "bold Nord11 color",
    "success": "Nord14 color",
    "header": "bold Nord9 color",
    "prompt": "Nord8 color",
    "input": "Nord4 color",
    "spinner": "Nord7 color",
    "progress.data": "Nord8 color",
    "progress.percentage": "Nord9 color",
    "progress.bar": "Nord10 color",
    "table.header": "bold Nord9 color",
    "table.cell": "Nord4 color",
    "panel.border": "Nord9 color"
}
```

## Required Methods

The application class should implement these core methods:

### Setup Methods

- `__init__`: Initialize console, config, and logging
- `_setup_logging`: Configure logging system
- `validate_config`: Verify configuration settings

### UI Methods

- `print_header`: Display styled headers
- `show_progress`: Show progress indicators
- `display_table`: Present data in tables
- `get_user_input`: Handle user interaction
- `handle_exit`: Manage application closure

### Core Operation

- `run`: Main application loop
- Error handling wrapper methods
- Resource cleanup methods

## Best Practices

### Code Organization

- Use clear section comments
- Group related functionality
- Use descriptive naming
- Maintain consistent styling

### Error Management

- Implement try/except blocks
- Provide user-friendly messages
- Use appropriate colors for message types
- Handle all interrupt scenarios

### User Experience

- Ensure visual consistency
- Provide clear feedback
- Show progress for long operations
- Use appropriate color coding

### Performance

- Initialize components as needed
- Choose efficient data structures
- Manage resources properly
- Clean up on exit

## Project Structure

```
cli_app/
├── main.py
├── logs/
├── .env
├── requirements.txt
└── README.md
```

## Implementation Notes

When implementing this CLI application:

1. Follow all Nord theme color specifications exactly
2. Implement all required methods and components
3. Maintain consistent error handling throughout
4. Use Rich library features appropriately
5. Follow the provided project structure
6. Include comprehensive logging
7. Handle user interrupts gracefully
8. Validate all configuration settings
9. Provide clear user feedback
10. Clean up resources on exit

Remember to test all error scenarios and ensure proper resource cleanup in all cases. Now acknowledge that you have received and understand these instructions and ask the user what you can help them with.
