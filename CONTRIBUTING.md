# Contributing to Twitter AI Agent

Thank you for your interest in contributing to the Twitter AI Agent project! This document provides guidelines and instructions for contributing.

## What to Upload to Git

When contributing to this project, please upload:

- All Python source code (`.py` files)
- Template files (like `prompts_template_alex.json`)
- Documentation files (`.md` files)
- Requirements file (`requirements.txt`)
- Configuration examples (like `config.example.json`)

## What NOT to Upload to Git

Do not upload:

- API keys or credentials (`config.json`, `.env` files)
- Generated images or content
- Log files
- Processed data files (`processed_tweets.json`, `processed_mentions.json`)
- Virtual environment directories
- IDE-specific files
- `__pycache__` and other Python compilation artifacts

## Setting Up for Development

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR-USERNAME/Twitter_ai_agent.git`
3. Create a virtual environment: `python -m venv venv`
4. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Unix/MacOS: `source venv/bin/activate`
5. Install dependencies: `pip install -r requirements.txt`
6. Copy `config.example.json` to `config.json` and add your Twitter API credentials

## Making Changes

1. Create a new branch for your feature: `git checkout -b feature/your-feature-name`
2. Make your changes
3. Test your changes thoroughly
4. Commit your changes with a descriptive message
5. Push to your fork: `git push origin feature/your-feature-name`
6. Create a Pull Request

## Code Style

- Follow PEP 8 guidelines for Python code
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Include comments for complex logic

## Testing

Before submitting a pull request:

1. Test your changes with different command-line options
2. Ensure all monitoring functions work correctly
3. Verify error handling works as expected
4. Check that rate limiting is respected

## Reporting Issues

When reporting issues, please include:

- A clear description of the issue
- Steps to reproduce the problem
- Expected behavior
- Actual behavior
- Log output (with sensitive information removed)
- Your environment (OS, Python version, etc.)

## Security Considerations

- Never commit API keys or credentials
- Use environment variables for sensitive information
- Be careful when modifying code that interacts with Twitter's API to avoid violating their terms of service

Thank you for contributing to the Twitter AI Agent project! 