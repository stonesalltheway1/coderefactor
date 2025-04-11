# coderefactor/coderefactor/web/__init__.py

"""
Web Interface: Flask-based web interface for the CodeRefactor tool.

This module provides a user-friendly web interface with Monaco Editor
for interactive code analysis and refactoring.
"""

import os
import sys
from pathlib import Path

# Define function to create the app with necessary components
def create_app(config=None):
    """
    Create and configure the Flask application.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Configured Flask application
    """
    from .app import app
    return app

# Export the app factory
__all__ = ['create_app']