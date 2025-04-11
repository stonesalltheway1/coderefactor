# CodeRefactor Project Structure

```
coderefactor/
│
├── coderefactor/                       # Main package
│   ├── __init__.py                     # Package initialization
│   ├── analyzers/                      # Code analyzers
│   │   ├── __init__.py
│   │   ├── base.py                     # Base analyzer interface
│   │   ├── python_analyzer.py          # Python code analyzer
│   │   ├── csharp_analyzer.py          # C# code analyzer
│   │   ├── web_analyzer.py             # HTML/CSS/JS analyzer
│   │   └── utils/                      # Shared analyzer utilities
│   │       ├── __init__.py
│   │       └── models.py               # Shared data models
│   │
│   ├── fixers/                         # Code fixers
│   │   ├── __init__.py
│   │   ├── base.py                     # Base fixer interface
│   │   ├── python_fixer.py             # Python code fixer
│   │   ├── csharp_fixer.py             # C# code fixer
│   │   └── web_fixer.py                # HTML/CSS/JS fixer
│   │
│   ├── llm/                            # LLM integration
│   │   ├── __init__.py
│   │   ├── claude_api.py               # Claude API integration
│   │   └── prompts.py                  # LLM prompts
│   │
│   ├── web/                            # Web interface
│   │   ├── __init__.py
│   │   ├── app.py                      # Flask application
│   │   ├── routes.py                   # API routes
│   │   ├── static/                     # Static files
│   │   │   ├── css/                    # Stylesheets
│   │   │   ├── js/                     # JavaScript files
│   │   │   └── img/                    # Images
│   │   └── templates/                  # HTML templates
│   │
│   ├── cli/                            # Command-line interface
│   │   ├── __init__.py
│   │   └── commands.py                 # CLI commands
│   │
│   └── utils/                          # Utility modules
│       ├── __init__.py
│       ├── config.py                   # Configuration handling
│       ├── logging.py                  # Logging utilities
│       └── output.py                   # Output formatters
│
├── tests/                              # Tests
│   ├── __init__.py
│   ├── test_python_analyzer.py
│   ├── test_csharp_analyzer.py
│   ├── test_web_analyzer.py
│   ├── test_llm.py
│   └── fixtures/                       # Test fixtures
│       ├── python/                     # Python test files
│       ├── csharp/                     # C# test files
│       └── web/                        # HTML/CSS/JS test files
│
├── docs/                               # Documentation
│   ├── index.md                        # Main documentation page
│   ├── installation.md                 # Installation guide
│   ├── usage.md                        # Usage guide
│   ├── configuration.md                # Configuration guide
│   ├── api/                            # API documentation
│   └── examples/                       # Example use cases
│
├── examples/                           # Example scripts and configurations
│   ├── analyze_python_project.py
│   ├── analyze_csharp_project.py
│   ├── custom_config.yaml
│   └── web_integration.py
│
├── requirements/                       # Requirements files
│   ├── base.txt                        # Base requirements
│   ├── dev.txt                         # Development requirements
│   ├── docs.txt                        # Documentation requirements
│   └── test.txt                        # Test requirements
│
├── .github/                            # GitHub configuration
│   └── workflows/                      # GitHub Actions
│       ├── tests.yml                   # Run tests
│       └── release.yml                 # Release workflow
│
├── setup.py                            # Package setup script
├── setup.cfg                           # Setup configuration
├── pyproject.toml                      # Project configuration
├── MANIFEST.in                         # Package manifest
├── README.md                           # Project readme
├── LICENSE                             # Project license
└── CHANGELOG.md                        # Project changelog
```

## Key Components and Features

### Analyzers

The core of the CodeRefactor system is the analyzer modules that integrate with various static analysis tools:

- **Python Analyzer**: Integrates with pylint, mypy, flake8, bandit and more
- **C# Analyzer**: Uses Roslyn analyzers, Roslynator, and other .NET tools
- **Web Analyzer**: Supports HTML, CSS, JavaScript, and TypeScript analysis

### Fixers

Fixers handle applying changes to code based on analysis results:

- **Simple Fixers**: Apply straightforward changes like formatting fixes
- **Complex Fixers**: Multi-step refactoring for more involved changes
- **LLM-Assisted Fixers**: Use Claude to suggest fixes for complex issues

### LLM Integration

Claude API integration provides advanced code understanding and suggestions:

- **Code Analysis**: Get AI assessment of code quality and potential issues
- **Refactoring Suggestions**: AI-powered suggestions for complex refactoring
- **Code Explanations**: Get explanations of what code does and how it works

### Web Interface

A modern interface for code analysis and refactoring:

- **Monaco Editor**: Rich code editing experience from VS Code
- **Real-time Analysis**: Get feedback as you type
- **Interactive Fixes**: Preview and apply suggested fixes
- **Diff View**: See before/after comparisons

### CLI Interface

Command-line interface for integration with workflows:

- **Project Analysis**: Analyze entire projects or specific files
- **Automated Fixes**: Apply fixes from the command line
- **CI/CD Integration**: Easily integrate with build pipelines
- **Custom Reporting**: Output in multiple formats (text, JSON, HTML)

## Configuration

The system is highly configurable through YAML configuration files:

```yaml
# Example configuration
python:
  enabled: true
  tools:
    - pylint
    - mypy
    - flake8
    - bandit
  rules:
    # Rule customizations
    pylint:
      disable:
        - C0111  # missing-docstring
      severity:
        C0103: error  # invalid-name

csharp:
  enabled: true
  analyzers:
    - Roslyn
    - Roslynator
    - SonarAnalyzer
  rules:
    # Rule customizations

llm:
  enabled: true
  model: claude-3-7-sonnet-20250219
  use_extended_thinking: true
  temperature: 0.3

output:
  format: html
  colored: true
  details: true
```