# coderefactor/coderefactor/analyzers/utils/__init__.py

"""
Analyzer Utilities: Shared components for code analysis.

This module provides utilities and models used by multiple analyzers.
"""

# Import shared data models and utilities
from .models import AnalysisResult, Issue, IssueSeverity, IssueCategory

# Export the classes
__all__ = [
    'AnalysisResult',
    'Issue',
    'IssueSeverity',
    'IssueCategory',
]