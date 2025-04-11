#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Web Interface: Flask-based web interface for the CodeRefactor tool.
Integrates Monaco Editor for code editing and real-time analysis.
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

from flask import Flask, render_template, request, jsonify, abort
import flask_cors

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import our modules
from python_analyzer import PythonAnalyzer, AnalysisResult as PyAnalysisResult
from claude_api import ClaudeAPI, LLMConfig

# Create Flask app
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
flask_cors.CORS(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("coderefactor.web")

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

# Web Routes
@app.route('/')
def index():
    """Render the main application page."""
    return render_template('index.html')

@app.route('/about')
def about():
    """Render the about page."""
    return render_template('about.html')

# Main entry point
if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('static', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    
    # Generate initial HTML templates if they don't exist
    index_html_path = os.path.join('templates', 'index.html')
    if not os.path.exists(index_html_path):
        with open(index_html_path, 'w') as f:
            f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CodeRefactor - Advanced Code Analysis & Refactoring</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/styles.css') }}">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body>
    <div class="app-container">
        <header>
            <div class="logo">
                <i class="fas fa-code"></i>
                <h1>CodeRefactor</h1>
            </div>
            <nav>
                <ul>
                    <li><a href="/" class="active">Editor</a></li>
                    <li><a href="/about">About</a></li>
                </ul>
            </nav>
        </header>
        
        <main>
            <div class="toolbar">
                <div class="language-selector">
                    <label for="language-select">Language:</label>
                    <select id="language-select">
                        <option value="python">Python</option>
                        <option value="javascript">JavaScript</option>
                        <option value="typescript">TypeScript</option>
                        <option value="html">HTML</option>
                        <option value="css">CSS</option>
                        <option value="csharp">C#</option>
                    </select>
                </div>
                <div class="actions">
                    <button id="analyze-btn" class="primary-btn">
                        <i class="fas fa-search"></i> Analyze
                    </button>
                    <button id="explain-btn">
                        <i class="fas fa-book"></i> Explain
                    </button>
                    <button id="fix-all-btn">
                        <i class="fas fa-magic"></i> Fix All
                    </button>
                    <label class="checkbox-container">
                        <input type="checkbox" id="use-llm-checkbox">
                        <span class="checkmark"></span>
                        Use Claude Analysis
                    </label>
                </div>
            </div>
            
            <div class="editor-container">
                <div id="editor"></div>
                <div class="results-panel">
                    <div class="panel-header">
                        <h3>Analysis Results</h3>
                        <div class="panel-actions">
                            <button id="collapse-results" title="Collapse Panel">
                                <i class="fas fa-chevron-right"></i>
                            </button>
                        </div>
                    </div>
                    <div class="panel-content">
                        <div id="issues-list"></div>
                        <div id="explanation-container" class="hidden">
                            <h4>Code Explanation</h4>
                            <div id="explanation-content"></div>
                        </div>
                    </div>
                </div>
            </div>
        </main>
        
        <div id="fix-modal" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Fix Suggestion</h3>
                    <button class="close-modal">×</button>
                </div>
                <div class="modal-body">
                    <div class="explanation"></div>
                    <div class="diff-container">
                        <div class="diff-header">
                            <div>Original</div>
                            <div>Refactored</div>
                        </div>
                        <div class="diff-view">
                            <div id="original-code"></div>
                            <div id="refactored-code"></div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="dismiss-btn">Dismiss</button>
                    <button class="apply-btn primary-btn">Apply Fix</button>
                </div>
            </div>
        </div>
        
        <div id="loading-overlay">
            <div class="spinner"></div>
            <div class="loading-text">Processing...</div>
        </div>
    </div>
    
    <!-- Monaco Editor -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.50.0/min/vs/loader.min.js"></script>
    <!-- Main App JS -->
    <script src="{{ url_for('static', filename='js/app.js') }}"></script>
</body>
</html>
""")
    
    about_html_path = os.path.join('templates', 'about.html')
    if not os.path.exists(about_html_path):
        with open(about_html_path, 'w') as f:
            f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>About - CodeRefactor</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/styles.css') }}">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body>
    <div class="app-container">
        <header>
            <div class="logo">
                <i class="fas fa-code"></i>
                <h1>CodeRefactor</h1>
            </div>
            <nav>
                <ul>
                    <li><a href="/">Editor</a></li>
                    <li><a href="/about" class="active">About</a></li>
                </ul>
            </nav>
        </header>
        
        <main class="about-container">
            <section class="about-section">
                <h2>About CodeRefactor</h2>
                <p>
                    CodeRefactor is an advanced code analysis and refactoring tool designed to help developers improve
                    their code quality, identify potential issues, and apply intelligent fixes.
                </p>
                <p>
                    By combining established static analysis tools with artificial intelligence, CodeRefactor provides
                    deep insights into your code and suggests improvements that go beyond simple style fixes.
                </p>
            </section>
            
            <section class="about-section">
                <h2>Key Features</h2>
                <div class="features-grid">
                    <div class="feature-card">
                        <i class="fas fa-search"></i>
                        <h3>Advanced Analysis</h3>
                        <p>Integrates with established linters and analyzers for comprehensive code analysis.</p>
                    </div>
                    <div class="feature-card">
                        <i class="fas fa-magic"></i>
                        <h3>Intelligent Fixes</h3>
                        <p>Suggests fixes for identified issues with preview and apply capabilities.</p>
                    </div>
                    <div class="feature-card">
                        <i class="fas fa-robot"></i>
                        <h3>AI Integration</h3>
                        <p>Uses Claude LLM to provide context-aware suggestions and explanations.</p>
                    </div>
                    <div class="feature-card">
                        <i class="fas fa-code"></i>
                        <h3>Multi-Language Support</h3>
                        <p>Supports Python, JavaScript, HTML, CSS, and more languages.</p>
                    </div>
                    <div class="feature-card">
                        <i class="fas fa-desktop"></i>
                        <h3>Modern Interface</h3>
                        <p>Intuitive web interface with Monaco Editor for a smooth coding experience.</p>
                    </div>
                    <div class="feature-card">
                        <i class="fas fa-book"></i>
                        <h3>Code Explanations</h3>
                        <p>Get in-depth explanations of code functionality and logic.</p>
                    </div>
                </div>
            </section>
            
            <section class="about-section">
                <h2>Technologies Used</h2>
                <ul class="tech-list">
                    <li><span>Python</span> - Core application logic and analysis engines</li>
                    <li><span>Flask</span> - Web framework for the application</li>
                    <li><span>Monaco Editor</span> - Feature-rich code editor from VS Code</li>
                    <li><span>Claude API</span> - LLM integration for AI-powered analysis</li>
                    <li><span>Roslyn</span> - .NET Compiler Platform for C# analysis</li>
                    <li><span>pylint, mypy, flake8, bandit</span> - Python analysis tools</li>
                </ul>
            </section>
        </main>
        
        <footer>
            <p>&copy; 2025 CodeRefactor. All rights reserved.</p>
        </footer>
    </div>
</body>
</html>
""")
    
    # Create CSS directory and stylesheet
    css_dir = os.path.join('static', 'css')
    os.makedirs(css_dir, exist_ok=True)
    
    css_path = os.path.join(css_dir, 'styles.css')
    if not os.path.exists(css_path):
        with open(css_path, 'w') as f:
            f.write("""/* Main Styles for CodeRefactor */

:root {
    --primary-color: #4a6fff;
    --primary-hover: #3555d3;
    --secondary-color: #30c9b0;
    --background-color: #f5f7fa;
    --panel-bg-color: #ffffff;
    --text-color: #2c3e50;
    --border-color: #e0e4e9;
    --error-color: #e74c3c;
    --warning-color: #f39c12;
    --info-color: #3498db;
    --success-color: #2ecc71;
    
    --header-height: 60px;
    --toolbar-height: 50px;
    --panel-width: 350px;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    line-height: 1.6;
    color: var(--text-color);
    background-color: var(--background-color);
}

.app-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
}

/* Header */
header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background-color: var(--panel-bg-color);
    height: var(--header-height);
    padding: 0 20px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    z-index: 10;
}

.logo {
    display: flex;
    align-items: center;
}

.logo i {
    font-size: 24px;
    color: var(--primary-color);
    margin-right: 10px;
}

.logo h1 {
    font-size: 1.5rem;
    font-weight: 600;
}

nav ul {
    display: flex;
    list-style: none;
}

nav ul li {
    margin-left: 20px;
}

nav ul li a {
    text-decoration: none;
    color: var(--text-color);
    font-weight: 500;
    padding: 5px 10px;
    border-radius: 4px;
    transition: background-color 0.2s;
}

nav ul li a:hover {
    background-color: rgba(74, 111, 255, 0.1);
}

nav ul li a.active {
    color: var(--primary-color);
    border-bottom: 2px solid var(--primary-color);
}

/* Main Content */
main {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

/* Toolbar */
.toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    height: var(--toolbar-height);
    padding: 0 20px;
    background-color: var(--panel-bg-color);
    border-bottom: 1px solid var(--border-color);
}

.language-selector {
    display: flex;
    align-items: center;
}

.language-selector label {
    margin-right: 10px;
    font-weight: 500;
}

select {
    padding: 6px 10px;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    background-color: white;
}

.actions {
    display: flex;
    align-items: center;
    gap: 10px;
}

button {
    padding: 8px 15px;
    border: none;
    border-radius: 4px;
    background-color: white;
    color: var(--text-color);
    font-weight: 500;
    cursor: pointer;
    display: flex;
    align-items: center;
    transition: background-color 0.2s;
}

button i {
    margin-right: 5px;
}

button:hover {
    background-color: #f0f3f7;
}

.primary-btn {
    background-color: var(--primary-color);
    color: white;
}

.primary-btn:hover {
    background-color: var(--primary-hover);
}

/* Checkbox */
.checkbox-container {
    display: flex;
    align-items: center;
    position: relative;
    padding-left: 30px;
    cursor: pointer;
    user-select: none;
}

.checkbox-container input {
    position: absolute;
    opacity: 0;
    cursor: pointer;
    height: 0;
    width: 0;
}

.checkmark {
    position: absolute;
    top: 0;
    left: 0;
    height: 20px;
    width: 20px;
    background-color: #eee;
    border-radius: 3px;
}

.checkbox-container:hover input ~ .checkmark {
    background-color: #ccc;
}

.checkbox-container input:checked ~ .checkmark {
    background-color: var(--primary-color);
}

.checkmark:after {
    content: "";
    position: absolute;
    display: none;
}

.checkbox-container input:checked ~ .checkmark:after {
    display: block;
}

.checkbox-container .checkmark:after {
    left: 7px;
    top: 3px;
    width: 5px;
    height: 10px;
    border: solid white;
    border-width: 0 2px 2px 0;
    transform: rotate(45deg);
}

/* Editor Container */
.editor-container {
    flex: 1;
    display: flex;
    overflow: hidden;
}

#editor {
    flex: 1;
    height: 100%;
}

/* Results Panel */
.results-panel {
    width: var(--panel-width);
    background-color: var(--panel-bg-color);
    border-left: 1px solid var(--border-color);
    display: flex;
    flex-direction: column;
    transition: width 0.3s;
}

.results-panel.collapsed {
    width: 40px;
}

.panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 15px;
    border-bottom: 1px solid var(--border-color);
}

.panel-header h3 {
    font-size: 1rem;
    font-weight: 600;
}

.panel-actions button {
    padding: 5px;
    background: none;
}

.panel-content {
    flex: 1;
    overflow-y: auto;
    padding: 15px;
}

.results-panel.collapsed .panel-content {
    display: none;
}

/* Issues List */
#issues-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.issue-item {
    border: 1px solid var(--border-color);
    border-radius: 4px;
    padding: 10px;
    background-color: #fafbfc;
}

.issue-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 5px;
}

.issue-title {
    font-weight: 600;
}

.issue-severity {
    font-size: 0.8rem;
    padding: 2px 6px;
    border-radius: 3px;
    color: white;
}

.severity-error {
    background-color: var(--error-color);
}

.severity-warning {
    background-color: var(--warning-color);
}

.severity-info {
    background-color: var(--info-color);
}

.issue-location {
    font-size: 0.8rem;
    color: #666;
    margin-bottom: 5px;
}

.issue-message {
    margin-bottom: 8px;
    font-size: 0.9rem;
}

.issue-actions {
    display: flex;
    justify-content: flex-end;
    gap: 5px;
}

.issue-actions button {
    padding: 4px 8px;
    font-size: 0.8rem;
}

/* Explanation Container */
#explanation-container {
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid var(--border-color);
}

#explanation-container h4 {
    margin-bottom: 10px;
    font-size: 1rem;
}

#explanation-content {
    background-color: #fafbfc;
    padding: 15px;
    border-radius: 4px;
    border: 1px solid var(--border-color);
    font-size: 0.9rem;
    white-space: pre-wrap;
}

.hidden {
    display: none;
}

/* Modal */
.modal {
    display: none;
    position: fixed;
    z-index: 1000;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.5);
}

.modal-content {
    background-color: var(--panel-bg-color);
    border-radius: 6px;
    width: 80%;
    max-width: 1000px;
    margin: 50px auto;
    height: calc(100% - 100px);
    display: flex;
    flex-direction: column;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 15px 20px;
    border-bottom: 1px solid var(--border-color);
}

.modal-header h3 {
    font-size: 1.2rem;
}

.close-modal {
    font-size: 1.5rem;
    background: none;
    padding: 0;
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.modal-body {
    flex: 1;
    padding: 20px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 20px;
}

.explanation {
    background-color: #f8f9fa;
    padding: 15px;
    border-radius: 4px;
    border-left: 4px solid var(--primary-color);
}

.diff-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    overflow: hidden;
}

.diff-header {
    display: flex;
    background-color: #f1f3f5;
    border-bottom: 1px solid var(--border-color);
}

.diff-header div {
    flex: 1;
    padding: 8px 15px;
    font-weight: 600;
    text-align: center;
}

.diff-view {
    display: flex;
    flex: 1;
    min-height: 300px;
}

.diff-view > div {
    flex: 1;
    overflow: auto;
    height: 100%;
}

#original-code {
    border-right: 1px solid var(--border-color);
}

.modal-footer {
    padding: 15px 20px;
    border-top: 1px solid var(--border-color);
    display: flex;
    justify-content: flex-end;
    gap: 10px;
}

/* Loading Overlay */
#loading-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(255, 255, 255, 0.8);
    display: none;
    justify-content: center;
    align-items: center;
    z-index: 2000;
    flex-direction: column;
}

.spinner {
    width: 50px;
    height: 50px;
    border: 5px solid var(--border-color);
    border-top: 5px solid var(--primary-color);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 15px;
}

.loading-text {
    font-size: 1.1rem;
    font-weight: 500;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* About Page Styles */
.about-container {
    padding: 30px;
    max-width: 1200px;
    margin: 0 auto;
}

.about-section {
    margin-bottom: 40px;
}

.about-section h2 {
    margin-bottom: 20px;
    padding-bottom: 10px;
    border-bottom: 2px solid var(--primary-color);
}

.about-section p {
    margin-bottom: 15px;
    line-height: 1.8;
}

.features-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 20px;
}

.feature-card {
    background-color: white;
    border-radius: 8px;
    padding: 25px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    transition: transform 0.2s, box-shadow 0.2s;
}

.feature-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.feature-card i {
    font-size: 2rem;
    color: var(--primary-color);
    margin-bottom: 15px;
}

.feature-card h3 {
    margin-bottom: 10px;
}

.tech-list {
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.tech-list li {
    background-color: white;
    padding: 12px 15px;
    border-radius: 6px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.tech-list li span {
    font-weight: 600;
    color: var(--primary-color);
}

footer {
    text-align: center;
    padding: 20px;
    background-color: var(--panel-bg-color);
    border-top: 1px solid var(--border-color);
}

/* Responsive Design */
@media (max-width: 768px) {
    .toolbar {
        flex-direction: column;
        height: auto;
        padding: 10px;
        gap: 10px;
    }
    
    .actions {
        flex-wrap: wrap;
        justify-content: center;
    }
    
    .editor-container {
        flex-direction: column;
    }
    
    .results-panel {
        width: 100%;
        height: 300px;
        border-left: none;
        border-top: 1px solid var(--border-color);
    }
    
    .modal-content {
        width: 95%;
        margin: 20px auto;
        height: calc(100% - 40px);
    }
    
    .features-grid {
        grid-template-columns: 1fr;
    }
}
""")
    
    # Create JS directory and app.js
    js_dir = os.path.join('static', 'js')
    os.makedirs(js_dir, exist_ok=True)
    
    js_path = os.path.join(js_dir, 'app.js')
    if not os.path.exists(js_path):
        with open(js_path, 'w') as f:
            f.write("""/* Main Application JavaScript for CodeRefactor */

// Global variables
let editor;
let monaco;
let currentLanguage = 'python';
let decorations = [];
let currentIssues = [];
let isAnalyzing = false;

// Default code samples
const DEFAULT_CODE_SAMPLES = {
    python: `def calculate_average(numbers):
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)

def process_data(data):
    # Process the data and return results
    results = []
    for item in data:
        if item > 10:
            results.append(item * 2)
        else:
            results.append(item)
    return results

# Example usage
data_list = [5, 10, 15, 20, 25]
avg = calculate_average(data_list)
print(f"Average: {avg}")
processed = process_data(data_list)
print(f"Processed data: {processed}")`,

    javascript: `// Function to calculate average
function calculateAverage(numbers) {
    let total = 0;
    for (let i = 0; i < numbers.length; i++) {
        total += numbers[i];
    }
    return total / numbers.length;
}

// Process data function
function processData(data) {
    // Process the data and return results
    const results = [];
    for (let i = 0; i < data.length; i++) {
        if (data[i] > 10) {
            results.push(data[i] * 2);
        } else {
            results.push(data[i]);
        }
    }
    return results;
}

// Example usage
const dataList = [5, 10, 15, 20, 25];
const avg = calculateAverage(dataList);
console.log("Average: " + avg);
const processed = processData(dataList);
console.log("Processed data: " + processed);`,

    typescript: `// Function to calculate average
function calculateAverage(numbers: number[]): number {
    let total = 0;
    for (let i = 0; i < numbers.length; i++) {
        total += numbers[i];
    }
    return total / numbers.length;
}

// Process data function
function processData(data: number[]): number[] {
    // Process the data and return results
    const results: number[] = [];
    for (let i = 0; i < data.length; i++) {
        if (data[i] > 10) {
            results.push(data[i] * 2);
        } else {
            results.push(data[i]);
        }
    }
    return results;
}

// Example usage
const dataList: number[] = [5, 10, 15, 20, 25];
const avg: number = calculateAverage(dataList);
console.log("Average: " + avg);
const processed: number[] = processData(dataList);
console.log("Processed data: " + processed);`,

    html: `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Simple Webpage</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            color: #333;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        header {
            background-color: #f4f4f4;
            padding: 20px;
            text-align: center;
        }
        .content {
            padding: 20px;
        }
        footer {
            text-align: center;
            margin-top: 20px;
            padding: 10px;
            background-color: #f4f4f4;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Welcome to My Website</h1>
            <p>A simple demonstration of HTML structure</p>
        </header>
        
        <div class="content">
            <h2>About This Page</h2>
            <p>This is a basic HTML template that demonstrates various HTML elements.</p>
            
            <h2>Features</h2>
            <ul>
                <li>Simple and clean design</li>
                <li>Responsive layout</li>
                <li>Basic styling with CSS</li>
            </ul>
            
            <h2>Contact Information</h2>
            <p>You can reach me at <a href="mailto:example@example.com">example@example.com</a></p>
        </div>
        
        <footer>
            <p>&copy; 2025 My Website. All rights reserved.</p>
        </footer>
    </div>
</body>
</html>`,

    css: `/* Main Styles */
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    line-height: 1.6;
    margin: 0;
    padding: 0;
    background-color: #f4f4f4;
    color: #333;
}

.container {
    width: 80%;
    margin: auto;
    overflow: hidden;
}

/* Header Styles */
header {
    background: #50b3a2;
    color: white;
    padding: 20px 0;
    text-align: center;
}

header h1 {
    margin: 0;
    padding: 0;
}

/* Navigation Styles */
nav {
    background: #444;
    color: white;
}

nav ul {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
}

nav li {
    padding: 10px 20px;
}

nav a {
    color: white;
    text-decoration: none;
}

nav a:hover {
    color: #50b3a2;
}

/* Main Content */
.content {
    padding: 20px;
    background: white;
    margin: 20px 0;
    border-radius: 5px;
    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
}

/* Footer */
footer {
    background: #444;
    color: white;
    text-align: center;
    padding: 10px;
    margin-top: 20px;
}

/* Media Queries */
@media (max-width: 700px) {
    .container {
        width: 95%;
    }
    
    nav ul {
        flex-direction: column;
    }
}`,

    csharp: `using System;
using System.Collections.Generic;
using System.Linq;

namespace CodeRefactorExample
{
    class Program
    {
        static void Main(string[] args)
        {
            // Example data
            List<int> dataList = new List<int> { 5, 10, 15, 20, 25 };
            
            // Calculate average
            double avg = CalculateAverage(dataList);
            Console.WriteLine($"Average: {avg}");
            
            // Process data
            List<int> processed = ProcessData(dataList);
            Console.WriteLine($"Processed data: {string.Join(", ", processed)}");
            
            Console.ReadLine();
        }
        
        static double CalculateAverage(List<int> numbers)
        {
            int total = 0;
            foreach (int n in numbers)
            {
                total += n;
            }
            return (double)total / numbers.Count;
        }
        
        static List<int> ProcessData(List<int> data)
        {
            // Process the data and return results
            List<int> results = new List<int>();
            foreach (int item in data)
            {
                if (item > 10)
                {
                    results.Add(item * 2);
                }
                else
                {
                    results.Add(item);
                }
            }
            return results;
        }
    }
}`
};

// Initialize the application
document.addEventListener('DOMContentLoaded', initApp);

// Initialize Monaco Editor
function initApp() {
    // Initialize the editor
    initMonacoEditor().then(() => {
        // Setup event listeners
        setupEventListeners();
        
        // Show loading before API check
        showLoading();
        
        // Check if API is available (can be implemented later)
        setTimeout(hideLoading, 500);
    });
}

// Initialize Monaco Editor
async function initMonacoEditor() {
    return new Promise((resolve) => {
        require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.50.0/min/vs' } });
        require(['vs/editor/editor.main'], function() {
            monaco = window.monaco;
            
            // Set the language
            currentLanguage = document.getElementById('language-select').value;
            
            // Create the editor
            editor = monaco.editor.create(document.getElementById('editor'), {
                value: DEFAULT_CODE_SAMPLES[currentLanguage],
                language: currentLanguage,
                theme: 'vs',
                automaticLayout: true,
                minimap: { enabled: true },
                scrollBeyondLastLine: false,
                renderLineHighlight: 'all',
                contextmenu: true,
                lineNumbers: 'on',
                rulers: [80, 120],
                renderWhitespace: 'selection',
                fontFamily: 'Consolas, "Courier New", monospace',
                fontSize: 14
            });
            
            // Resize the editor to fit the container
            window.addEventListener('resize', () => {
                editor.layout();
            });
            
            resolve();
        });
    });
}

// Setup all event listeners
function setupEventListeners() {
    // Language selector change
    document.getElementById('language-select').addEventListener('change', (e) => {
        const newLanguage = e.target.value;
        changeLanguage(newLanguage);
    });
    
    // Analyze button click
    document.getElementById('analyze-btn').addEventListener('click', () => {
        if (!isAnalyzing) {
            analyzeCode();
        }
    });
    
    // Explain button click
    document.getElementById('explain-btn').addEventListener('click', () => {
        if (!isAnalyzing) {
            explainCode();
        }
    });
    
    // Fix all button click
    document.getElementById('fix-all-btn').addEventListener('click', () => {
        if (!isAnalyzing && currentIssues.length > 0) {
            fixAllIssues();
        }
    });
    
    // Collapse results panel
    document.getElementById('collapse-results').addEventListener('click', () => {
        const resultsPanel = document.querySelector('.results-panel');
        resultsPanel.classList.toggle('collapsed');
        
        // Update the button icon
        const button = document.getElementById('collapse-results');
        const icon = button.querySelector('i');
        
        if (resultsPanel.classList.contains('collapsed')) {
            icon.className = 'fas fa-chevron-left';
            button.title = 'Expand Panel';
        } else {
            icon.className = 'fas fa-chevron-right';
            button.title = 'Collapse Panel';
        }
        
        // Resize editor
        setTimeout(() => editor.layout(), 300);
    });
    
    // Modal close button
    document.querySelector('.close-modal').addEventListener('click', () => {
        document.getElementById('fix-modal').style.display = 'none';
    });
    
    // Modal dismiss button
    document.querySelector('.dismiss-btn').addEventListener('click', () => {
        document.getElementById('fix-modal').style.display = 'none';
    });
    
    // Modal apply button
    document.querySelector('.apply-btn').addEventListener('click', () => {
        applyFix();
    });
    
    // Allow clicking outside the modal to close it
    document.getElementById('fix-modal').addEventListener('click', (e) => {
        if (e.target === document.getElementById('fix-modal')) {
            document.getElementById('fix-modal').style.display = 'none';
        }
    });
}

// Change the editor language
function changeLanguage(newLanguage) {
    if (newLanguage === currentLanguage) return;
    
    currentLanguage = newLanguage;
    monaco.editor.setModelLanguage(editor.getModel(), newLanguage);
    
    // Set default code sample if editor is empty
    if (editor.getValue().trim() === '') {
        editor.setValue(DEFAULT_CODE_SAMPLES[newLanguage]);
    }
    
    // Clear any existing issues
    clearIssues();
}

// Analyze the code
async function analyzeCode() {
    if (isAnalyzing) return;
    
    isAnalyzing = true;
    showLoading();
    clearIssues();
    hideExplanation();
    
    try {
        const code = editor.getValue();
        const language = currentLanguage;
        const useLLM = document.getElementById('use-llm-checkbox').checked;
        
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ code, language, use_llm: useLLM })
        });
        
        if (!response.ok) {
            throw new Error(`Error: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        // Store current issues
        currentIssues = data.issues || [];
        
        // Show the issues
        displayIssues(currentIssues);
        
        // Add decorations to editor
        addIssueDecorations(currentIssues);
        
        // Show explanation if available
        if (data.explanation) {
            showExplanation(data.explanation);
        }
    } catch (error) {
        console.error('Error analyzing code:', error);
        showError(`Error analyzing code: ${error.message}`);
    } finally {
        isAnalyzing = false;
        hideLoading();
    }
}

// Explain the code
async function explainCode() {
    if (isAnalyzing) return;
    
    isAnalyzing = true;
    showLoading();
    
    try {
        const code = editor.getValue();
        const language = currentLanguage;
        
        const response = await fetch('/api/explain', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ code, language })
        });
        
        if (!response.ok) {
            throw new Error(`Error: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        // Show the explanation
        showExplanation(data.explanation);
    } catch (error) {
        console.error('Error explaining code:', error);
        showError(`Error explaining code: ${error.message}`);
    } finally {
        isAnalyzing = false;
        hideLoading();
    }
}

// Fix all issues
async function fixAllIssues() {
    if (isAnalyzing || currentIssues.length === 0) return;
    
    // TODO: Implement fix all
    showError('Fix all feature coming soon!');
}

// Get fix for a specific issue
async function getFixSuggestion(issueId) {
    if (isAnalyzing) return;
    
    isAnalyzing = true;
    showLoading();
    
    try {
        const issue = currentIssues.find(i => i.id === issueId);
        if (!issue) {
            throw new Error('Issue not found');
        }
        
        const code = editor.getValue();
        const language = currentLanguage;
        const issueDescription = issue.description || issue.message;
        
        const response = await fetch('/api/fix', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                code, 
                language, 
                issue_id: issueId,
                issue_description: issueDescription
            })
        });
        
        if (!response.ok) {
            throw new Error(`Error: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        // Show the fix modal
        showFixModal(data);
    } catch (error) {
        console.error('Error getting fix suggestion:', error);
        showError(`Error getting fix suggestion: ${error.message}`);
    } finally {
        isAnalyzing = false;
        hideLoading();
    }
}

// Show fix modal
function showFixModal(fixData) {
    const modal = document.getElementById('fix-modal');
    const explanation = modal.querySelector('.explanation');
    const originalCodeContainer = document.getElementById('original-code');
    const refactoredCodeContainer = document.getElementById('refactored-code');
    
    // Set explanation
    explanation.textContent = fixData.explanation || 'No explanation provided';
    
    // Initialize original code editor
    if (!window.originalCodeEditor) {
        window.originalCodeEditor = monaco.editor.create(originalCodeContainer, {
            value: fixData.original_code || '',
            language: currentLanguage,
            theme: 'vs',
            minimap: { enabled: false },
            readOnly: true,
            scrollBeyondLastLine: false,
            lineNumbers: 'on',
            renderWhitespace: 'selection',
            fontFamily: 'Consolas, "Courier New", monospace',
            fontSize: 14
        });
    } else {
        window.originalCodeEditor.setValue(fixData.original_code || '');
    }
    
    // Initialize refactored code editor
    if (!window.refactoredCodeEditor) {
        window.refactoredCodeEditor = monaco.editor.create(refactoredCodeContainer, {
            value: fixData.refactored_code || '',
            language: currentLanguage,
            theme: 'vs',
            minimap: { enabled: false },
            readOnly: true,
            scrollBeyondLastLine: false,
            lineNumbers: 'on',
            renderWhitespace: 'selection',
            fontFamily: 'Consolas, "Courier New", monospace',
            fontSize: 14
        });
    } else {
        window.refactoredCodeEditor.setValue(fixData.refactored_code || '');
    }
    
    // Store the fix data for apply action
    window.currentFixData = fixData;
    
    // Show the modal
    modal.style.display = 'block';
    
    // Resize editors after display
    setTimeout(() => {
        window.originalCodeEditor.layout();
        window.refactoredCodeEditor.layout();
    }, 100);
}

// Apply the suggested fix
function applyFix() {
    if (!window.currentFixData || !window.currentFixData.refactored_code) {
        showError('No fix data available');
        return;
    }
    
    // Apply the fix by replacing the entire code
    editor.setValue(window.currentFixData.refactored_code);
    
    // Close the modal
    document.getElementById('fix-modal').style.display = 'none';
    
    // Re-analyze the code
    analyzeCode();
}

// Display issues in the sidebar
function displayIssues(issues) {
    const issuesList = document.getElementById('issues-list');
    issuesList.innerHTML = '';
    
    if (issues.length === 0) {
        issuesList.innerHTML = '<div class="no-issues">No issues found! Good job!</div>';
        return;
    }
    
    // Sort issues by severity and line number
    issues.sort((a, b) => {
        const severityOrder = { 'critical': 0, 'error': 1, 'warning': 2, 'info': 3 };
        const aSeverity = severityOrder[a.severity.toLowerCase()] || 4;
        const bSeverity = severityOrder[b.severity.toLowerCase()] || 4;
        
        if (aSeverity !== bSeverity) {
            return aSeverity - bSeverity;
        }
        
        return a.line - b.line;
    });
    
    // Create issue items
    issues.forEach(issue => {
        const issueItem = document.createElement('div');
        issueItem.className = 'issue-item';
        
        const title = issue.title || `${issue.category} Issue`;
        const severity = issue.severity.toLowerCase();
        const message = issue.message || issue.description;
        const location = `Line ${issue.line}${issue.column ? `, Column ${issue.column}` : ''}`;
        
        issueItem.innerHTML = `
            <div class="issue-header">
                <div class="issue-title">${escapeHtml(title)}</div>
                <div class="issue-severity severity-${severity}">${severity}</div>
            </div>
            <div class="issue-location">${location}</div>
            <div class="issue-message">${escapeHtml(message)}</div>
            <div class="issue-actions">
                <button class="goto-btn" data-line="${issue.line}" data-column="${issue.column || 0}">
                    <i class="fas fa-arrow-right"></i> Go to
                </button>
                ${issue.fixable ? `
                    <button class="fix-btn" data-issue-id="${issue.id}">
                        <i class="fas fa-wrench"></i> Fix
                    </button>
                ` : ''}
            </div>
        `;
        
        issuesList.appendChild(issueItem);
    });
    
    // Add event listeners to buttons
    document.querySelectorAll('.goto-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const line = parseInt(btn.getAttribute('data-line'));
            const column = parseInt(btn.getAttribute('data-column'));
            goToLocation(line, column);
        });
    });
    
    document.querySelectorAll('.fix-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const issueId = btn.getAttribute('data-issue-id');
            getFixSuggestion(issueId);
        });
    });
}

// Add decorations to editor for issues
function addIssueDecorations(issues) {
    // Remove existing decorations
    decorations = editor.deltaDecorations(decorations, []);
    
    // Create new decorations
    const newDecorations = issues.map(issue => {
        const startLineNumber = issue.line;
        const startColumn = issue.column || 1;
        const endLineNumber = issue.end_line || issue.line;
        const endColumn = issue.end_column || 1000;
        
        const severity = issue.severity.toLowerCase();
        let className = 'issue-decoration';
        
        if (severity === 'critical' || severity === 'error') {
            className = 'error-decoration';
        } else if (severity === 'warning') {
            className = 'warning-decoration';
        } else {
            className = 'info-decoration';
        }
        
        return {
            range: new monaco.Range(startLineNumber, startColumn, endLineNumber, endColumn),
            options: {
                inlineClassName: className,
                hoverMessage: { value: issue.message || issue.description },
                className: `${className}-line`
            }
        };
    });
    
    // Apply decorations
    decorations = editor.deltaDecorations([], newDecorations);
    
    // Add CSS for decorations if not already added
    if (!document.getElementById('decoration-styles')) {
        const style = document.createElement('style');
        style.id = 'decoration-styles';
        style.innerHTML = `
            .error-decoration { border-bottom: 2px wavy #e74c3c; }
            .warning-decoration { border-bottom: 2px wavy #f39c12; }
            .info-decoration { border-bottom: 2px dotted #3498db; }
            .error-decoration-line { background-color: rgba(231, 76, 60, 0.1); }
            .warning-decoration-line { background-color: rgba(243, 156, 18, 0.1); }
            .info-decoration-line { background-color: rgba(52, 152, 219, 0.1); }
        `;
        document.head.appendChild(style);
    }
}

// Go to location in editor
function goToLocation(line, column) {
    editor.revealPositionInCenter({ lineNumber: line, column: column });
    editor.setPosition({ lineNumber: line, column: column });
    editor.focus();
}

// Show explanation in the sidebar
function showExplanation(explanation) {
    const explanationContainer = document.getElementById('explanation-container');
    const explanationContent = document.getElementById('explanation-content');
    
    explanationContent.textContent = explanation;
    explanationContainer.classList.remove('hidden');
}

// Hide explanation
function hideExplanation() {
    document.getElementById('explanation-container').classList.add('hidden');
}

// Clear all issues
function clearIssues() {
    // Clear issues list
    document.getElementById('issues-list').innerHTML = '';
    
    // Remove decorations
    decorations = editor.deltaDecorations(decorations, []);
    
    // Reset current issues
    currentIssues = [];
}

// Show loading overlay
function showLoading() {
    document.getElementById('loading-overlay').style.display = 'flex';
}

// Hide loading overlay
function hideLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
}

// Show error message
function showError(message) {
    const issuesList = document.getElementById('issues-list');
    issuesList.innerHTML = `
        <div class="error-message">
            <i class="fas fa-exclamation-triangle"></i>
            <p>${escapeHtml(message)}</p>
        </div>
    `;
}

// Helper function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
""")
    
    # Start the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)