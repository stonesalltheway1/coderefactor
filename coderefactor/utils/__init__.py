# coderefactor/coderefactor/utils/__init__.py

"""
Utilities: Helper functions and classes for the CodeRefactor tool.

This module provides configuration, logging, and output formatting utilities.
"""

# Import utility modules
from .config import ConfigManager, get_config
from .logging import setup_logging, get_logger, debug_mode
from .output import (
    format_output, 
    TextFormatter, 
    HTMLFormatter, 
    JSONFormatter, 
    MarkdownFormatter
)

# Export utility functions and classes
__all__ = [
    'ConfigManager',
    'get_config',
    'setup_logging',
    'get_logger',
    'debug_mode',
    'format_output',
    'TextFormatter',
    'HTMLFormatter',
    'JSONFormatter',
    'MarkdownFormatter',
]