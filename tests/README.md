# CodeRefactor Test Suite

This directory contains the test suite for the CodeRefactor application, which provides advanced code analysis and refactoring capabilities.

## Test Structure

The test suite is organized by component and follows the structure of the main application:

```
tests/
│
├── __init__.py                      # Package initialization
├── conftest.py                      # Shared pytest fixtures
│
├── test_python_analyzer.py          # Tests for Python analyzer
├── test_csharp_analyzer.py          # Tests for C# analyzer
├── test_web_analyzer.py             # Tests for HTML/CSS/JS analyzer
│
├── test_python_fixer.py             # Tests for Python fixer
├── test_csharp_fixer.py             # Tests for C# fixer
├── test_web_fixer.py                # Tests for HTML/CSS/JS fixer
│
├── test_llm.py                      # Tests for LLM integration
├── test_cli.py                      # Tests for command-line interface
├── test_web_interface.py            # Tests for web interface
├── test_utils.py                    # Tests for utility modules
│
├── test_base.py                     # Tests for base classes
├── test_integration.py              # Integration tests
│
└── fixtures/                        # Test fixtures
    ├── python/                      # Python test files
    ├── csharp/                      # C# test files
    └── web/                         # HTML/CSS/JS test files
```

## Running Tests

### Running All Tests

To run the complete test suite:

```bash
pytest
```

### Running Tests for a Specific Component

To run tests for a specific component:

```bash
# Run Python analyzer tests
pytest test_python_analyzer.py

# Run C# analyzer tests
pytest test_csharp_analyzer.py

# Run web analyzer tests
pytest test_web_analyzer.py
```

### Running Tests with Coverage

To run tests with coverage reporting:

```bash
pytest --cov=coderefactor
```

## Test Fixtures

The test suite uses fixtures defined in `conftest.py` to provide shared resources for tests. These include:

- Sample code snippets for each supported language
- Temporary directories for file-based tests
- Preconfigured analyzer and fixer instances

## Test Categories

The test suite includes:

1. **Unit Tests**: Tests for individual components (analyzers, fixers, utilities)
2. **Integration Tests**: Tests for interactions between components
3. **End-to-End Tests**: Tests for complete workflows

## Mock LLM Integration

Tests for the LLM integration use mocking to avoid actual API calls:

```python
with patch('coderefactor.llm.claude_api.ClaudeAPI') as mock_api:
    # Test code using mocked LLM API
```

## Adding New Tests

When adding new tests:

1. Follow the existing pattern of test organization
2. Use appropriate fixtures from `conftest.py`
3. Add both positive and negative test cases
4. Include docstrings explaining the purpose of each test

## Test Dependencies

The tests have the following dependencies:

- pytest
- pytest-cov (for coverage reporting)
- mock (for mocking external dependencies)

Install all dependencies with:

```bash
pip install -r requirements/test.txt
```

## CI Integration

The test suite is integrated with CI/CD workflows in `.github/workflows/tests.yml` to automatically run tests on push and pull requests.