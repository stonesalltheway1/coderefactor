"""
CodeRefactor test suite.

This package contains the test suite for all components of the CodeRefactor system.
"""

import os
import sys
import pytest

# Add the parent directory to the path so tests can import from the main package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))