#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API Routes: Flask API routes for the CodeRefactor web interface.
Provides endpoints for code analysis, fixes, and explanations.
"""

import os
import sys
import logging
import tempfile
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from flask import request, jsonify, abort

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import our modules
from .app import app
from ..analyzers.python_analyzer import PythonAnalyzer
from ..llm.claude_api import ClaudeAPI, LLMConfig

# Configure logging
logger = logging.getLogger("coderefactor.web.routes")

# Initialize analyzers
python_analyzer = PythonAnalyzer()
claude_api = ClaudeAPI(
    LLMConfig(
        api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        model="claude-3-7-sonnet-20250219",
        temperature=0.3
    )
)

# Language extensions mapping
LANGUAGE_EXTENSIONS = {
    "python": ".py",
    "javascript": ".js",
    "typescript": ".ts",
    "html": ".html",
    "css": ".css",
    "csharp": ".cs",
    "java": ".java",
    "go": ".go",
    "rust": ".rs",
    "php": ".php",
    "ruby": ".rb",
    "shell": ".sh",
    "sql": ".sql",
    "xml": ".xml",
    "json": ".json"
}

def get_file_extension(language: str) -> str:
    """Get file extension for a language."""
    return LANGUAGE_EXTENSIONS.get(language, f".{language}")

def save_temp_file(content: str, language: str) -> str:
    """Save content to a temporary file."""
    ext = get_file_extension(language)
    handle, path = tempfile.mkstemp(suffix=ext)
    with os.fdopen(handle, 'w') as f:
        f.write(content)
    return path

async def analyze_code(code: str, language: str, use_llm: bool = False) -> Dict[str, Any]:
    """Analyze code using appropriate analyzer based on language."""
    result = {"issues": [], "time": datetime.now().isoformat()}
    
    try:
        # Python analysis
        if language == "python":
            # Save to temporary file
            temp_file = save_temp_file(code, language)
            
            # Run analyzer
            analysis_result = python_analyzer.analyze_file(temp_file)
            
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass
            
            # Convert issues to our format
            for issue in analysis_result.issues:
                result["issues"].append({
                    "id": issue.id,
                    "line": issue.line,
                    "column": issue.column,
                    "end_line": issue.end_line,
                    "end_column": issue.end_column,
                    "message": issue.message,
                    "description": issue.description,
                    "severity": issue.severity.name.lower(),
                    "category": issue.category.name.lower(),
                    "source": issue.source,
                    "rule_id": issue.rule_id,
                    "fixable": issue.fixable,
                    "fix_type": issue.fix_type,
                    "code_snippet": issue.code_snippet
                })
        
        # For JavaScript/TypeScript/HTML/CSS, we'll use Claude
        # since we don't have language-specific analyzers for these yet
        elif language in ["javascript", "typescript", "html", "css"] or use_llm:
            # Use Claude API for analysis
            analysis_result = await claude_api.analyze_code(code, language)
            
            # Check for errors
            if analysis_result.error:
                return {"error": analysis_result.error, "issues": []}
            
            # Add issues from Claude
            result["issues"] = analysis_result.issues
            
            # Add suggestions if available
            if analysis_result.suggestions:
                result["suggestions"] = [
                    {
                        "title": "Suggestion" if not suggestion.changes else suggestion.changes[0].get("description", "Refactoring suggestion"),
                        "description": suggestion.explanation,
                        "before": suggestion.original_code,
                        "after": suggestion.refactored_code
                    }
                    for suggestion in analysis_result.suggestions
                ]
            
            # Add overall explanation
            if analysis_result.explanation:
                result["explanation"] = analysis_result.explanation
        
        else:
            # For unsupported languages, return an error
            result["error"] = f"Language '{language}' is not supported for analysis yet."
    
    except Exception as e:
        logger.error(f"Error analyzing {language} code: {str(e)}")
        result["error"] = str(e)
    
    return result

async def get_fix_suggestion(code: str, language: str, issue_id: str, issue_description: str) -> Dict[str, Any]:
    """Get a fix suggestion for a specific issue."""
    try:
        # Use Claude API for fix suggestions
        suggestion = await claude_api.suggest_refactoring(code, language, issue_description)
        
        # Convert to response format
        return {
            "original_code": suggestion.original_code,
            "refactored_code": suggestion.refactored_code,
            "changes": suggestion.changes,
            "explanation": suggestion.explanation,
            "confidence": suggestion.confidence
        }
    
    except Exception as e:
        logger.error(f"Error getting fix suggestion: {str(e)}")
        return {"error": str(e)}

async def explain_code(code: str, language: str) -> Dict[str, Any]:
    """Get an explanation of the code."""
    try:
        # Use Claude API for code explanation
        explanation = await claude_api.explain_code(code, language)
        
        return {"explanation": explanation}
    
    except Exception as e:
        logger.error(f"Error getting code explanation: {str(e)}")
        return {"error": str(e)}

# API Routes
@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    """Analyze code and return issues."""
    data = request.json
    code = data.get('code', '')
    language = data.get('language', 'python').lower()
    use_llm = data.get('use_llm', False)
    
    if not code:
        return jsonify({"error": "No code provided"}), 400
    
    # Run analysis (this needs to be async)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(analyze_code(code, language, use_llm))
    loop.close()
    
    return jsonify(result)

@app.route('/api/fix', methods=['POST'])
def api_fix():
    """Get fix suggestion for an issue."""
    data = request.json
    code = data.get('code', '')
    language = data.get('language', 'python').lower()
    issue_id = data.get('issue_id', '')
    issue_description = data.get('issue_description', '')
    
    if not code or not issue_description:
        return jsonify({"error": "Code and issue description are required"}), 400
    
    # Get fix suggestion (this needs to be async)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(get_fix_suggestion(code, language, issue_id, issue_description))
    loop.close()
    
    return jsonify(result)

@app.route('/api/explain', methods=['POST'])
def api_explain():
    """Get an explanation of the code."""
    data = request.json
    code = data.get('code', '')
    language = data.get('language', 'python').lower()
    
    if not code:
        return jsonify({"error": "No code provided"}), 400
    
    # Get explanation (this needs to be async)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(explain_code(code, language))
    loop.close()
    
    return jsonify(result)
