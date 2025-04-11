# coderefactor/coderefactor/cli/__init__.py

"""
Command-Line Interface: CLI for the CodeRefactor tool.

This module provides a command-line interface for running code analysis
and applying fixes from the terminal.
"""

# Import main CLI function
from .commands import main

# Export functions
__all__ = ['main']