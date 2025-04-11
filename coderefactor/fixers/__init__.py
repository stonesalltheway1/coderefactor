# coderefactor/coderefactor/fixers/__init__.py

"""
Code Fixers: Components responsible for applying fixes to code issues.

This module provides fixers for various programming languages,
applying both simple fixes and complex refactorings.
"""

# Import the fixer implementations
from .python_fixer import PythonFixer
from .web_fixer import WebFixer

# Try to import C# fixer if available
try:
    from .csharp_fixer import CSharpFixer
    __has_csharp__ = True
except ImportError:
    __has_csharp__ = False

# Export the fixer classes
__all__ = [
    'PythonFixer',
    'WebFixer',
]

# Add CSharpFixer to exports if available
if __has_csharp__:
    __all__.append('CSharpFixer')