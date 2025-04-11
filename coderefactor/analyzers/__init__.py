# coderefactor/coderefactor/analyzers/__init__.py

"""
Code Analyzers: Component responsible for detecting issues in source code.

This module provides analyzers for various programming languages,
integrating with established linters and analysis tools.
"""

# Import the analyzer implementations
from .python_analyzer import PythonAnalyzer
from .html_js_css_analyzer import WebTechAnalyzer

# Try to import C# analyzer if available
try:
    from .csharp_analyzer import CSharpAnalyzer
    __has_csharp__ = True
except ImportError:
    __has_csharp__ = False

# Export the analyzer classes
__all__ = [
    'PythonAnalyzer',
    'WebTechAnalyzer',
]

# Add CSharpAnalyzer to exports if available
if __has_csharp__:
    __all__.append('CSharpAnalyzer')