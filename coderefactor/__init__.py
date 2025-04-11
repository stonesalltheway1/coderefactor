# coderefactor/coderefactor/__init__.py

"""
CodeRefactor: Advanced Code Analysis & Refactoring Tool

A comprehensive tool for analyzing code quality, detecting issues,
and applying intelligent fixes across multiple programming languages.
"""

import os
import sys
from pathlib import Path

# Package version
__version__ = "0.1.0"
__author__ = "Your Name"

# Import main application class
from .main import CodeRefactorApp

# Make config singleton accessible
from .utils.config import get_config

# Setup logging by default
from .utils.logging import setup_logging
default_logger = setup_logging()

# Expose key analyzers
from .analyzers.python_analyzer import PythonAnalyzer
from .analyzers.web_analyzer import WebTechAnalyzer

# Export commonly used components
__all__ = [
    'CodeRefactorApp',
    'get_config',
    'PythonAnalyzer',
    'WebTechAnalyzer',
    '__version__',
]# CodeRefactor package