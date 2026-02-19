# Contributing to Ollama Code Assistant (OCA)

Thank you for your interest in contributing to OCA! This document provides guidelines for contributing to the project.

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ollama-code-assistant.git
   cd ollama-code-assistant
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install in development mode**
   ```bash
   pip install -e ".[dev]"
   ```

## Development Workflow

### Running Tests

```bash
# Run all tests
make test

# Run tests with coverage
make test-cov

# Run specific test file
pytest tests/unit/test_ollama.py -v
```

### Code Style

We follow PEP 8 and use automated tools for consistency:

```bash
# Format code
make format

# Lint code
make lint

# Type checking
make typecheck
```

### Testing Guidelines

- **100% Test Coverage**: All new code must include tests
- **Mocked Ollama**: All Ollama interactions must be mocked in tests
- **Isolated Tests**: Tests should not depend on external services
- **Clear Test Names**: Use descriptive test method names

Example test structure:
```python
def test_command_with_specific_scenario(self):
    """Test command behavior in specific scenario."""
    # Arrange
    mock_setup()
    
    # Act
    result = command_under_test()
    
    # Assert
    assert expected_behavior
```

## Contribution Guidelines

### Pull Request Process

1. **Fork the repository** and create a feature branch
2. **Make your changes** with appropriate tests
3. **Ensure all tests pass** and coverage remains high
4. **Follow the coding standards** (PEP 8, type hints)
5. **Write clear commit messages** following conventional commits
6. **Submit a pull request** with a clear description

### Commit Message Format

We use conventional commits:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions/changes
- `refactor`: Code refactoring
- `style`: Code style changes
- `chore`: Build process or auxiliary tool changes

Examples:
```
feat(cli): add support for custom config files
fix(session): handle file permission errors gracefully
docs(readme): update installation instructions
```

### Code Requirements

1. **Type Hints**: All public functions must have type hints
2. **Docstrings**: All public functions and classes must have docstrings
3. **Error Handling**: Proper exception handling with specific error types
4. **Security**: No hardcoded secrets or unsafe operations
5. **Git Safety**: All Git operations must be sandboxed

### Areas for Contribution

We welcome contributions in these areas:

- **Additional Commands**: New OCA commands following existing patterns
- **Improved Error Handling**: Better error messages and recovery
- **Performance Optimizations**: Faster file operations and Git handling
- **Documentation**: Examples, tutorials, and API documentation
- **Testing**: Integration tests and edge case coverage
- **Security**: Enhanced sandboxing and validation

### Review Process

All contributions will be reviewed for:

1. **Functionality**: Does it work as intended?
2. **Tests**: Are there adequate tests with good coverage?
3. **Code Quality**: Is the code clean, readable, and maintainable?
4. **Security**: Are there any security implications?
5. **Documentation**: Is the code well-documented?

## Getting Help

- **Issues**: Open an issue for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: Check the README and docs/ directory

## Code of Conduct

We are committed to fostering a welcoming and inclusive community. Please:

- Be respectful and considerate
- Use inclusive language
- Focus on constructive feedback
- Help others learn and grow

Thank you for contributing to OCA! 🚀