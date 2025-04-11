# CodeRefactor

**Advanced Code Analysis & Refactoring Tool**

[![PyPI version](https://img.shields.io/pypi/v/coderefactor.svg)](https://pypi.org/project/coderefactor/)
[![Python Versions](https://img.shields.io/pypi/pyversions/coderefactor.svg)](https://pypi.org/project/coderefactor/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI Status](https://github.com/Stonesalltheway1/coderefactor/workflows/tests/badge.svg)](https://github.com/Stonesalltheway1/coderefactor/actions)
[![Documentation Status](https://readthedocs.org/projects/coderefactor/badge/?version=latest)](https://coderefactor.readthedocs.io/en/latest/?badge=latest)

## Overview

CodeRefactor is a powerful code analysis and refactoring tool that integrates with established linters and analyzers while enhancing them with AI-powered suggestions. It supports multiple languages including Python, C#, and web technologies (HTML, CSS, JavaScript/TypeScript).

## Features

- **Multi-language Support**: Analyze Python, C#, and web technologies
- **Integrated Analysis**: Combines results from multiple established tools
- **AI-Enhanced Refactoring**: Uses Claude API for complex fix suggestions
- **Interactive Web Interface**: Monaco Editor with real-time analysis
- **Command Line Interface**: For automation and CI/CD integration
- **Extensible Architecture**: Easy to add support for new languages

## Installation

### Basic Installation

```bash
pip install coderefactor
```

### With Optional Components

```bash
# For web analysis tools
pip install coderefactor[web]

# For C# support
pip install coderefactor[csharp]

# For LLM integration
pip install coderefactor[llm]

# For everything
pip install coderefactor[all]
```

### Development Installation

```bash
git clone https://github.com/Stonesalltheway1/coderefactor.git
cd coderefactor
pip install -e .[dev]
```

## Quick Start

### Command Line Interface

```bash
# Analyze a file
coderefactor analyze path/to/file.py

# Analyze a directory
coderefactor analyze path/to/directory --recursive

# Get fix suggestions
coderefactor fix path/to/file.py issue-id-12345

# Start the web interface
coderefactor web
```

### Python API

```python
from coderefactor import CodeRefactorApp

# Initialize the app
app = CodeRefactorApp()

# Analyze a file
result = app.analyze_file("path/to/file.py")

# Process the results
for issue in result["issues"]:
    print(f"Line {issue['line']}: {issue['message']}")

# Get fix suggestions
import asyncio
fix = asyncio.run(app.get_fix_suggestion("path/to/file.py", "issue-id-12345"))
```

## Web Interface

The web interface provides a user-friendly way to interact with CodeRefactor:

- Monaco editor with real-time analysis
- Issue list with severity and category filtering
- Fix suggestions with preview
- AI-powered code explanations
- Support for multiple file types

To start the web interface:

```bash
coderefactor web
```

This will start the web interface at http://localhost:5000 by default.

## Configuration

CodeRefactor is highly configurable through YAML configuration files:

```yaml
python:
  enabled: true
  tools:
    - pylint
    - mypy
    - flake8

llm:
  enabled: true
  model: claude-3-7-sonnet-20250219
  temperature: 0.3

output:
  format: html
  colored: true
```

For more configuration options, see the [configuration guide](https://coderefactor.readthedocs.io/en/latest/configuration/).

## Documentation

For more detailed documentation, visit [coderefactor.readthedocs.io](https://coderefactor.readthedocs.io/).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please make sure to update tests as appropriate and ensure all tests pass before submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- The CodeRefactor team would like to thank all the developers of the static analysis tools that make this project possible.
- Special thanks to the Anthropic team for the Claude API which powers our AI-enhanced suggestions.