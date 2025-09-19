# Contributing to Deep Cleaner

Thank you for your interest in contributing to Deep Cleaner! This document provides guidelines and information to help make the contribution process smooth and effective.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/Destroyer-official/deep-cleaner.git`
3. Create a new branch for your feature or bug fix: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test your changes
6. Commit your changes: `git commit -am "Add your feature"`
7. Push to your fork: `git push origin feature/your-feature-name`
8. Create a pull request

## Development Setup

1. Create a virtual environment: `python -m venv venv`
2. Activate it:
   - On Windows: `venv\Scripts\activate`
   - On Unix/macOS: `source venv/bin/activate`
3. Install the package in development mode: `pip install -e .[dev]`

## Code Standards

### Python Style

- Follow PEP 8 style guide
- Use type hints for function parameters and return values
- Write docstrings for all public functions, classes, and modules
- Keep functions small and focused on a single responsibility
- Use descriptive variable and function names

### Testing

- Write tests for new functionality
- Ensure all tests pass before submitting a pull request
- Use pytest for testing
- Maintain good test coverage

Run tests with:
```bash
pytest
```

### Code Quality Tools

This project uses several tools to maintain code quality:

- **Black** for code formatting
- **Flake8** for linting
- **MyPy** for type checking

Run all checks with:
```bash
# Format code
black .

# Lint code
flake8 .

# Type check
mypy .
```

## Pull Request Process

1. Ensure your code follows the style guidelines
2. Add tests for new functionality
3. Update documentation as needed
4. Verify all tests pass
5. Submit a pull request with a clear title and description

## Reporting Issues

When reporting issues, please include:

1. A clear and descriptive title
2. Steps to reproduce the issue
3. Expected behavior
4. Actual behavior
5. Environment information (OS, Python version, etc.)
6. Any relevant logs or error messages

## Feature Requests

We welcome feature requests! Please open an issue describing:

1. The problem the feature would solve
2. How the feature would work
3. Any implementation considerations

## Code of Conduct

Please note that this project is released with a Contributor Code of Conduct. By participating in this project you agree to abide by its terms.

## Questions?

If you have any questions about contributing, feel free to open an issue asking for clarification.