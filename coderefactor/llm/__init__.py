# coderefactor/coderefactor/llm/__init__.py

"""
LLM Integration: Claude API integration for AI-powered code analysis and fixes.

This module provides interfaces for interacting with Claude via the Anthropic API.
"""

# Import the Claude API client
from .claude_api import ClaudeAPI, LLMConfig, RefactorSuggestion, AnalysisResult

# Export the classes
__all__ = [
    'ClaudeAPI',
    'LLMConfig',
    'RefactorSuggestion',
    'AnalysisResult',
]