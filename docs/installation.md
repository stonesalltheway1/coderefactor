# CodeRefactor: Installation and Usage Guide

## Installation

### Prerequisites

CodeRefactor requires:

- Python 3.8 or higher
- Node.js 16+ (for web-based analysis tools)
- .NET SDK 7.0+ (for C# analysis, optional)

### Install from PyPI

```bash
pip install coderefactor
```

### Installing Development Version

```bash
git clone https://github.com/username/coderefactor.git
cd coderefactor
pip install -e .
```

### Installing Optional Dependencies

For full functionality, install the optional components:

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

### NPM Dependencies for Web Analysis

If you're using web analysis features, install the required NPM packages:

```bash
npm install -g eslint stylelint htmlhint
```

### Setting Up Claude API for LLM Integration

To use Claude LLM integration:

1. Sign up for Anthropic API access at [https://anthropic.com](https://anthropic.com)
2. Get your API key from the dashboard
3. Set your API key as an environment variable:

```bash
export ANTHROPIC_API_KEY=your_api_key_here
```

## Basic Usage

### Command Line Interface

CodeRefactor provides a command-line interface for easy usage.

#### Analyzing a Single File

```bash
coderefactor analyze path/to/file.py
```

#### Analyzing a Directory

```bash
coderefactor analyze path/to/directory --recursive
```

#### Filtering Files

```bash
coderefactor analyze path/to/directory --pattern "*.py"
```

#### Outputting Results

```bash
# Output to terminal (default)
coderefactor analyze path/to/file.py

# Output to file in JSON format
coderefactor analyze path/to/file.py --format json --output results.json

# Output to HTML report
coderefactor analyze path/to/file.py --format html --output report.html
```

#### Using a Custom Configuration

```bash
coderefactor analyze path/to/file.py --config my_config.yaml
```

### Getting Fix Suggestions

```bash
# First analyze and note the issue ID
coderefactor analyze path/to/file.py

# Then get a fix suggestion for a specific issue
coderefactor fix path/to/file.py issue-id-12345
```

### Starting the Web Interface

```bash
coderefactor web
```

This will start the web interface at http://localhost:5000 by default.

```bash
# Specify a different host and port
coderefactor web --host 127.0.0.1 --port 8080
```

## Configuration

### Default Configuration

CodeRefactor comes with sensible defaults, but you can customize its behavior.

### Custom Configuration File

Create a YAML file with your settings:

```yaml
# my_config.yaml
python:
  enabled: true
  tools:
    - pylint
    - mypy
    - flake8
  pylint_args:
    - "--disable=C0111,C0103"

llm:
  enabled: true
  model: claude-3-7-sonnet-20250219
  use_extended_thinking: true

output:
  format: html
  colored: true
```

### In-File Configuration

You can also include configuration in your source files to customize analysis:

```python
# coderefactor: disable=unused-import
import os

# coderefactor: enable=complexity
def complex_function():
    # Complex function body...
    pass
```

## Web Interface

### Overview

The web interface provides a user-friendly way to interact with CodeRefactor:

- Monaco editor with real-time analysis
- Issue list with severity and category filtering
- Fix suggestions with preview
- AI-powered code explanations
- Support for multiple file types

### Files and Projects

- Open individual files
- Open entire directories or projects
- Save and share analysis results

### Analysis and Fixing

1. Open a file or paste code into the editor
2. Select the language from the dropdown
3. Click "Analyze" to run analysis
4. Review issues in the results panel
5. Click "Fix" on an issue to see fix suggestions
6. Apply suggestions directly to the code

## Python API

You can also use CodeRefactor programmatically in your Python code:

```python
from coderefactor import CodeRefactorApp

# Initialize the app
app = CodeRefactorApp()

# Analyze a file
result = app.analyze_file("path/to/file.py")

# Process the results
for issue in result["issues"]:
    print(f"Line {issue['line']}: {issue['message']}")

# Analyze a directory
project_result = app.analyze_directory("path/to/project", recursive=True)

# Get fix suggestions
import asyncio
fix = asyncio.run(app.get_fix_suggestion("path/to/file.py", "issue-id-12345"))

# Output results to file
app.output_results(result, output_format="html", output_file="report.html")
```

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/coderefactor.yml
name: CodeRefactor Analysis

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install CodeRefactor
        run: pip install coderefactor[all]
      - name: Run analysis
        run: coderefactor analyze . --recursive --format json --output analysis.json
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: analysis-results
          path: analysis.json
```

### GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - analyze

code-analysis:
  stage: analyze
  image: python:3.10
  script:
    - pip install coderefactor[all]
    - coderefactor analyze . --recursive --format html --output report.html
  artifacts:
    paths:
      - report.html
```

## Troubleshooting

### Common Issues

#### Missing LLM Features

If LLM features aren't working, check:

- You've set the `ANTHROPIC_API_KEY` environment variable
- You have internet connectivity to reach the API
- The `llm.enabled` setting is `true` in your config

#### C# Analysis Not Working

If C# analysis isn't working:

- Ensure .NET SDK is installed and in PATH
- Check that C# support is installed: `pip install coderefactor[csharp]`
- Verify the `csharp.enabled` setting is `true` in your config

#### Web Analysis Problems

If web analysis tools aren't working:

- Ensure Node.js is installed and in PATH
- Verify that ESLint, Stylelint, and HTMLHint are installed globally
- Check that web support is installed: `pip install coderefactor[web]`

### Getting Help

- Check the documentation: [https://coderefactor.readthedocs.io/](https://coderefactor.readthedocs.io/)
- File an issue on GitHub: [https://github.com/username/coderefactor/issues](https://github.com/username/coderefactor/issues)
- Join the community on Discord: [https://discord.gg/coderefactor](https://discord.gg/coderefactor)