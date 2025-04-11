#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CodeRefactor: Advanced Code Analysis & Refactoring Tool

This is the main application entry point that integrates all components.
"""

import os
import sys
import logging
import argparse
import json
import tempfile
import subprocess
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path
import importlib.util
import yaml
from datetime import datetime

# Import core components
from python_analyzer import PythonAnalyzer
from html_js_css_analyzer import WebTechAnalyzer
from claude_api import ClaudeAPI, LLMConfig

# Try importing C# analyzer (optional)
try:
    import clr
    from csharp_analyzer import CSharpAnalyzer
    HAS_CSHARP = True
except ImportError:
    HAS_CSHARP = False


class CodeRefactorApp:
    """Main application class that integrates all analyzers and components."""
    
    def __init__(self, config_path: Optional[str] = None):
        # Setup logging
        self._setup_logging()
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize analyzers
        self._init_analyzers()
        
        # Initialize LLM if configured
        self._init_llm()
    
    def _setup_logging(self):
        """Setup logging configuration."""
        log_level = os.environ.get("CODEREFACTOR_LOG_LEVEL", "INFO").upper()
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format
        )
        
        self.logger = logging.getLogger("coderefactor")
        self.logger.info("Initializing CodeRefactor application")
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file or use defaults."""
        config = {
            "python": {
                "enabled": True,
                "tools": ["pylint", "mypy", "flake8", "bandit", "ast"]
            },
            "javascript": {
                "enabled": True
            },
            "typescript": {
                "enabled": True
            },
            "html": {
                "enabled": True
            },
            "css": {
                "enabled": True
            },
            "csharp": {
                "enabled": HAS_CSHARP
            },
            "llm": {
                "enabled": bool(os.environ.get("ANTHROPIC_API_KEY")),
                "model": "claude-3-7-sonnet-20250219",
                "use_extended_thinking": True
            },
            "output": {
                "format": "terminal",
                "colored": True
            }
        }
        
        if config_path:
            try:
                with open(config_path, 'r') as f:
                    file_config = yaml.safe_load(f)
                    
                # Merge configurations
                self._deep_merge(config, file_config)
                
                self.logger.info(f"Loaded configuration from {config_path}")
            except Exception as e:
                self.logger.error(f"Error loading configuration: {str(e)}")
                self.logger.warning("Using default configuration")
        
        return config
    
    def _deep_merge(self, base: Dict, update: Dict) -> None:
        """Deep merge two dictionaries."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _init_analyzers(self):
        """Initialize code analyzers based on configuration."""
        # Initialize Python analyzer
        if self.config["python"]["enabled"]:
            self.python_analyzer = PythonAnalyzer(self.config["python"])
            self.logger.info("Initialized Python analyzer")
        else:
            self.python_analyzer = None
        
        # Initialize Web Tech analyzer (JS/TS/HTML/CSS)
        if (self.config["javascript"]["enabled"] or
            self.config["typescript"]["enabled"] or
            self.config["html"]["enabled"] or
            self.config["css"]["enabled"]):
            
            web_config = {
                "javascript": self.config["javascript"],
                "typescript": self.config["typescript"],
                "html": self.config["html"],
                "css": self.config["css"]
            }
            self.web_analyzer = WebTechAnalyzer(web_config)
            self.logger.info("Initialized Web Technologies analyzer")
        else:
            self.web_analyzer = None
        
        # Initialize C# analyzer
        if self.config["csharp"]["enabled"] and HAS_CSHARP:
            self.csharp_analyzer = CSharpAnalyzer(self.config["csharp"])
            self.logger.info("Initialized C# analyzer")
        else:
            self.csharp_analyzer = None
    
    def _init_llm(self):
        """Initialize LLM integration if enabled in config."""
        if self.config["llm"]["enabled"]:
            # Check for API key
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                self.logger.warning("LLM integration enabled but ANTHROPIC_API_KEY not set in environment")
                self.llm = None
                return
            
            # Create LLM config
            llm_config = LLMConfig(
                api_key=api_key,
                model=self.config["llm"]["model"],
                use_extended_thinking=self.config["llm"]["use_extended_thinking"]
            )
            
            # Initialize Claude API
            self.llm = ClaudeAPI(llm_config)
            self.logger.info(f"Initialized LLM integration with model {llm_config.model}")
        else:
            self.llm = None
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a single file using the appropriate analyzer."""
        if not os.path.exists(file_path):
            self.logger.error(f"File does not exist: {file_path}")
            return {"error": f"File not found: {file_path}"}
        
        # Get file extension to determine analyzer
        file_ext = os.path.splitext(file_path)[1].lower()
        
        result = {
            "file_path": file_path,
            "timestamp": datetime.now().isoformat(),
            "issues": [],
            "suggestions": []
        }
        
        # Python files
        if file_ext == '.py' and self.python_analyzer:
            analysis_result = self.python_analyzer.analyze_file(file_path)
            
            if analysis_result.error:
                result["error"] = analysis_result.error
            else:
                # Convert issues to dictionary format for JSON serialization
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
        
        # Web Tech files (JS/TS/HTML/CSS)
        elif file_ext in ['.js', '.jsx', '.ts', '.tsx', '.html', '.htm', '.css', '.scss', '.less'] and self.web_analyzer:
            analysis_result = self.web_analyzer.analyze_file(file_path)
            
            if analysis_result.error:
                result["error"] = analysis_result.error
            else:
                # Convert issues to dictionary format for JSON serialization
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
        
        # C# files
        elif file_ext in ['.cs', '.csx'] and self.csharp_analyzer:
            # This would be asynchronous in the real implementation
            analysis_result = asyncio.run(self.csharp_analyzer.AnalyzeFileAsync(file_path))
            
            if hasattr(analysis_result, 'Error') and analysis_result.Error:
                result["error"] = analysis_result.Error
            else:
                # Convert issues to dictionary format for JSON serialization
                for issue in analysis_result.Issues:
                    result["issues"].append({
                        "id": issue.Id,
                        "line": issue.Line,
                        "column": issue.Column,
                        "end_line": issue.EndLine,
                        "end_column": issue.EndColumn,
                        "message": issue.Message,
                        "description": issue.Description,
                        "severity": str(issue.Severity).lower(),
                        "category": str(issue.Category).lower(),
                        "source": issue.Source,
                        "rule_id": issue.RuleId,
                        "fixable": issue.Fixable,
                        "fix_type": issue.FixType,
                        "code_snippet": issue.CodeSnippet
                    })
        
        else:
            result["error"] = f"Unsupported file type: {file_ext}"
        
        # If LLM is enabled and there are issues, get AI suggestions
        if self.llm and "error" not in result and result["issues"]:
            # Get file content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                # Determine language based on file extension
                language_map = {
                    '.py': 'python',
                    '.js': 'javascript',
                    '.jsx': 'javascript',
                    '.ts': 'typescript',
                    '.tsx': 'typescript',
                    '.html': 'html',
                    '.htm': 'html',
                    '.css': 'css',
                    '.scss': 'css',
                    '.less': 'css',
                    '.cs': 'csharp'
                }
                
                language = language_map.get(file_ext, 'text')
                
                # Get AI analysis
                ai_result = asyncio.run(self.llm.analyze_code(code, language))
                
                if not ai_result.error:
                    # Add AI issues and suggestions
                    for suggestion in ai_result.suggestions:
                        result["suggestions"].append({
                            "title": suggestion.changes[0].get("description", "AI Suggestion") if suggestion.changes else "AI Suggestion",
                            "description": suggestion.explanation,
                            "before": suggestion.original_code,
                            "after": suggestion.refactored_code
                        })
                    
                    # Add explanation if available
                    if ai_result.explanation:
                        result["ai_explanation"] = ai_result.explanation
            
            except Exception as e:
                self.logger.error(f"Error getting AI suggestions: {str(e)}")
        
        return result
    
    def analyze_directory(self, dir_path: str, recursive: bool = True, pattern: Optional[str] = None) -> Dict[str, Any]:
        """Analyze all supported files in a directory."""
        if not os.path.isdir(dir_path):
            self.logger.error(f"Directory does not exist: {dir_path}")
            return {"error": f"Directory not found: {dir_path}"}
        
        # Initialize result structure
        result = {
            "directory": dir_path,
            "timestamp": datetime.now().isoformat(),
            "files_analyzed": 0,
            "total_issues": 0,
            "issues_by_severity": {
                "critical": 0,
                "error": 0,
                "warning": 0,
                "info": 0
            },
            "issues_by_category": {},
            "files": []
        }
        
        # Find files to analyze
        files_to_analyze = []
        
        # Define supported extensions
        supported_extensions = set()
        
        if self.python_analyzer:
            supported_extensions.add('.py')
        
        if self.web_analyzer:
            supported_extensions.update(['.js', '.jsx', '.ts', '.tsx', '.html', '.htm', '.css', '.scss', '.less'])
        
        if self.csharp_analyzer:
            supported_extensions.update(['.cs', '.csx'])
        
        # Walk directory and find supported files
        for root, _, files in os.walk(dir_path):
            if not recursive and root != dir_path:
                continue
            
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file)[1].lower()
                
                if file_ext in supported_extensions:
                    # Apply pattern filter if specified
                    if pattern and not self._match_pattern(file, pattern):
                        continue
                    
                    files_to_analyze.append(file_path)
        
        # Analyze each file
        for file_path in files_to_analyze:
            self.logger.info(f"Analyzing file: {file_path}")
            file_result = self.analyze_file(file_path)
            
            # Update summary statistics
            if "error" not in file_result:
                result["files_analyzed"] += 1
                result["total_issues"] += len(file_result["issues"])
                
                # Count issues by severity
                for issue in file_result["issues"]:
                    severity = issue["severity"]
                    result["issues_by_severity"][severity] = result["issues_by_severity"].get(severity, 0) + 1
                    
                    # Count issues by category
                    category = issue["category"]
                    result["issues_by_category"][category] = result["issues_by_category"].get(category, 0) + 1
                
                # Add to files list
                result["files"].append(file_result)
        
        self.logger.info(f"Analyzed {result['files_analyzed']} files, found {result['total_issues']} issues")
        
        return result
    
    def _match_pattern(self, filename: str, pattern: str) -> bool:
        """Check if a filename matches a glob pattern."""
        import fnmatch
        return fnmatch.fnmatch(filename, pattern)
    
    async def get_fix_suggestion(self, file_path: str, issue_id: str) -> Dict[str, Any]:
        """Get a fix suggestion for a specific issue using LLM."""
        if not self.llm:
            return {"error": "LLM integration not enabled"}
        
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}
        
        # First analyze the file to get the issues
        analysis = self.analyze_file(file_path)
        
        if "error" in analysis:
            return {"error": analysis["error"]}
        
        # Find the specific issue
        issue = None
        for i in analysis["issues"]:
            if i["id"] == issue_id:
                issue = i
                break
        
        if not issue:
            return {"error": f"Issue with ID {issue_id} not found"}
        
        # Get file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # Determine language based on file extension
            file_ext = os.path.splitext(file_path)[1].lower()
            language_map = {
                '.py': 'python',
                '.js': 'javascript',
                '.jsx': 'javascript',
                '.ts': 'typescript',
                '.tsx': 'typescript',
                '.html': 'html',
                '.htm': 'html',
                '.css': 'css',
                '.scss': 'css',
                '.less': 'css',
                '.cs': 'csharp'
            }
            
            language = language_map.get(file_ext, 'text')
            
            # Get fix suggestion from LLM
            suggestion = await self.llm.suggest_refactoring(
                code, 
                language, 
                f"{issue['description']} (Line {issue['line']})"
            )
            
            return {
                "original_code": suggestion.original_code,
                "refactored_code": suggestion.refactored_code,
                "changes": suggestion.changes,
                "explanation": suggestion.explanation,
                "confidence": suggestion.confidence
            }
            
        except Exception as e:
            self.logger.error(f"Error getting fix suggestion: {str(e)}")
            return {"error": str(e)}
    
    def output_results(self, results: Dict[str, Any], output_format: Optional[str] = None, output_file: Optional[str] = None) -> None:
        """Output analysis results in the specified format."""
        format_type = output_format or self.config["output"]["format"]
        
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    if format_type == "json":
                        json.dump(results, f, indent=2)
                    elif format_type == "html":
                        f.write(self._generate_html_report(results))
                    else:
                        # Default to text format
                        f.write(self._generate_text_report(results))
                
                self.logger.info(f"Results saved to {output_file}")
                
            except Exception as e:
                self.logger.error(f"Error saving results: {str(e)}")
        else:
            # Output to terminal
            if format_type == "json":
                print(json.dumps(results, indent=2))
            else:
                # Default to text format
                print(self._generate_text_report(results))
    
    def _generate_text_report(self, results: Dict[str, Any]) -> str:
        """Generate a text report from analysis results."""
        report = []
        
        # Handle error
        if "error" in results:
            report.append(f"ERROR: {results['error']}")
            return "\n".join(report)
        
        # Single file report
        if "file_path" in results:
            report.append(f"Analysis Results for {results['file_path']}")
            report.append("-" * 80)
            
            if len(results["issues"]) == 0:
                report.append("No issues found!")
            else:
                report.append(f"Found {len(results['issues'])} issues:")
                report.append("")
                
                # Group issues by severity
                severity_order = ["critical", "error", "warning", "info"]
                severity_issues = {s: [] for s in severity_order}
                
                for issue in results["issues"]:
                    severity = issue["severity"]
                    severity_issues[severity].append(issue)
                
                # Output issues by severity
                for severity in severity_order:
                    issues = severity_issues[severity]
                    if issues:
                        report.append(f"{severity.upper()} level issues:")
                        
                        for issue in issues:
                            location = f"Line {issue['line']}"
                            if issue['column']:
                                location += f", Column {issue['column']}"
                            
                            report.append(f"  {location}: {issue['message']} [{issue['rule_id']}]")
                            report.append(f"    {issue['description']}")
                            if issue['fixable']:
                                report.append(f"    (Fixable: {issue['fix_type']})")
                            report.append("")
            
            # Add AI suggestions if available
            if "suggestions" in results and results["suggestions"]:
                report.append("\nAI Suggestions:")
                for suggestion in results["suggestions"]:
                    report.append(f"  {suggestion['title']}")
                    report.append(f"    {suggestion['description']}")
                    report.append("")
            
            # Add AI explanation if available
            if "ai_explanation" in results:
                report.append("\nAI Code Assessment:")
                report.append(results["ai_explanation"])
        
        # Directory report
        elif "directory" in results:
            report.append(f"Analysis Results for Directory: {results['directory']}")
            report.append("-" * 80)
            report.append(f"Files analyzed: {results['files_analyzed']}")
            report.append(f"Total issues found: {results['total_issues']}")
            
            # Issues by severity
            report.append("\nIssues by severity:")
            for severity, count in results["issues_by_severity"].items():
                report.append(f"  {severity.upper()}: {count}")
            
            # Issues by category
            report.append("\nIssues by category:")
            for category, count in sorted(results["issues_by_category"].items(), key=lambda x: x[1], reverse=True):
                report.append(f"  {category}: {count}")
            
            # Top files with issues
            if results["files"]:
                report.append("\nTop files with most issues:")
                files_sorted = sorted(results["files"], key=lambda f: len(f["issues"]), reverse=True)
                for i, file in enumerate(files_sorted[:10]):  # Show top 10
                    report.append(f"  {i+1}. {file['file_path']}: {len(file['issues'])} issues")
        
        return "\n".join(report)
    
    def _generate_html_report(self, results: Dict[str, Any]) -> str:
        """Generate an HTML report from analysis results."""
        # Basic HTML template
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CodeRefactor Analysis Report</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        h1, h2, h3 {
            color: #2c3e50;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 20px;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        .issue-critical {
            border-left: 5px solid #e74c3c;
        }
        .issue-error {
            border-left: 5px solid #e67e22;
        }
        .issue-warning {
            border-left: 5px solid #f1c40f;
        }
        .issue-info {
            border-left: 5px solid #3498db;
        }
        .code-snippet {
            background-color: #f8f8f8;
            border: 1px solid #ddd;
            border-radius: 3px;
            padding: 10px;
            overflow-x: auto;
            font-family: Consolas, Monaco, 'Andale Mono', monospace;
            font-size: 14px;
            margin-top: 5px;
        }
        .suggestion {
            background-color: #e8f4fc;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 15px;
        }
        .summary-box {
            background-color: #f8f9fa;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 20px;
        }
        .file-summary {
            cursor: pointer;
            padding: 10px;
            border: 1px solid #ddd;
            margin-bottom: 5px;
            border-radius: 3px;
        }
        .file-summary:hover {
            background-color: #f5f5f5;
        }
        .hidden {
            display: none;
        }
    </style>
</head>
<body>
    <h1>CodeRefactor Analysis Report</h1>
    <p>Generated on: {timestamp}</p>
"""
        
        # Handle error
        if "error" in results:
            html += f"<div class='error'><h2>Error</h2><p>{results['error']}</p></div>"
            html += "</body></html>"
            return html
        
        # Add timestamp
        timestamp = results.get("timestamp", datetime.now().isoformat())
        html = html.format(timestamp=timestamp)
        
        # Single file report
        if "file_path" in results:
            file_path = results["file_path"]
            issues = results["issues"]
            
            html += f"<h2>Analysis Results for: {file_path}</h2>"
            
            if not issues:
                html += "<div class='summary-box'><p>No issues found! Good job!</p></div>"
            else:
                html += f"<div class='summary-box'><p>Found {len(issues)} issues</p></div>"
                
                # Issues table
                html += "<h3>Issues</h3>"
                html += """<table>
                <tr>
                    <th>Severity</th>
                    <th>Location</th>
                    <th>Rule</th>
                    <th>Description</th>
                    <th>Fixable</th>
                </tr>
                """
                
                # Sort issues by severity
                severity_order = {"critical": 0, "error": 1, "warning": 2, "info": 3}
                sorted_issues = sorted(issues, key=lambda x: (severity_order.get(x["severity"], 99), x["line"]))
                
                for issue in sorted_issues:
                    severity = issue["severity"]
                    location = f"Line {issue['line']}"
                    if issue['column']:
                        location += f", Col {issue['column']}"
                    
                    html += f"""<tr class="issue-{severity}">
                        <td>{severity.upper()}</td>
                        <td>{location}</td>
                        <td>{issue['rule_id']}</td>
                        <td>
                            <strong>{issue['message']}</strong>
                            <p>{issue['description']}</p>
                            {f'<div class="code-snippet"><pre>{issue["code_snippet"]}</pre></div>' if issue['code_snippet'] else ''}
                        </td>
                        <td>{issue['fix_type'] if issue['fixable'] else 'No'}</td>
                    </tr>"""
                
                html += "</table>"
            
            # Add AI suggestions if available
            if "suggestions" in results and results["suggestions"]:
                html += "<h3>AI Suggestions</h3>"
                
                for suggestion in results["suggestions"]:
                    html += f"""<div class="suggestion">
                        <h4>{suggestion['title']}</h4>
                        <p>{suggestion['description']}</p>
                        <h5>Before:</h5>
                        <div class="code-snippet"><pre>{suggestion['before']}</pre></div>
                        <h5>After:</h5>
                        <div class="code-snippet"><pre>{suggestion['after']}</pre></div>
                    </div>"""
            
            # Add AI explanation if available
            if "ai_explanation" in results:
                html += f"""<div class="summary-box">
                    <h3>AI Code Assessment</h3>
                    <p>{results['ai_explanation']}</p>
                </div>"""
        
        # Directory report
        elif "directory" in results:
            directory = results["directory"]
            files_analyzed = results["files_analyzed"]
            total_issues = results["total_issues"]
            
            html += f"<h2>Analysis Results for Directory: {directory}</h2>"
            
            # Summary box
            html += f"""<div class="summary-box">
                <p>Files analyzed: {files_analyzed}</p>
                <p>Total issues found: {total_issues}</p>
            </div>"""
            
            # Issues by severity
            html += "<h3>Issues by Severity</h3>"
            html += "<table>"
            html += "<tr><th>Severity</th><th>Count</th></tr>"
            
            for severity, count in results["issues_by_severity"].items():
                html += f"<tr><td>{severity.upper()}</td><td>{count}</td></tr>"
            
            html += "</table>"
            
            # Issues by category
            html += "<h3>Issues by Category</h3>"
            html += "<table>"
            html += "<tr><th>Category</th><th>Count</th></tr>"
            
            for category, count in sorted(results["issues_by_category"].items(), key=lambda x: x[1], reverse=True):
                html += f"<tr><td>{category}</td><td>{count}</td></tr>"
            
            html += "</table>"
            
            # Files details
            if results["files"]:
                html += "<h3>Files</h3>"
                
                # Sort files by issue count
                files_sorted = sorted(results["files"], key=lambda f: len(f["issues"]), reverse=True)
                
                for i, file in enumerate(files_sorted):
                    file_path = file["file_path"]
                    issue_count = len(file["issues"])
                    file_id = f"file-{i}"
                    
                    html += f"""<div class="file-summary" onclick="toggleFile('{file_id}')">
                        {file_path} - {issue_count} issues
                    </div>
                    <div id="{file_id}" class="hidden">"""
                    
                    if file["issues"]:
                        # Issues table for this file
                        html += "<table>"
                        html += """<tr>
                            <th>Severity</th>
                            <th>Location</th>
                            <th>Rule</th>
                            <th>Description</th>
                        </tr>"""
                        
                        # Sort issues by severity
                        severity_order = {"critical": 0, "error": 1, "warning": 2, "info": 3}
                        sorted_issues = sorted(file["issues"], key=lambda x: (severity_order.get(x["severity"], 99), x["line"]))
                        
                        for issue in sorted_issues:
                            severity = issue["severity"]
                            location = f"Line {issue['line']}"
                            if issue['column']:
                                location += f", Col {issue['column']}"
                            
                            html += f"""<tr class="issue-{severity}">
                                <td>{severity.upper()}</td>
                                <td>{location}</td>
                                <td>{issue['rule_id']}</td>
                                <td>
                                    <strong>{issue['message']}</strong>
                                    <p>{issue['description']}</p>
                                </td>
                            </tr>"""
                        
                        html += "</table>"
                    else:
                        html += "<p>No issues found in this file!</p>"
                    
                    html += "</div>"
        
        # Add JavaScript for file toggling
        html += """
<script>
    function toggleFile(fileId) {
        const element = document.getElementById(fileId);
        if (element.classList.contains('hidden')) {
            element.classList.remove('hidden');
        } else {
            element.classList.add('hidden');
        }
    }
</script>
</body>
</html>
"""
        
        return html
    
    def start_web_interface(self, host: str = '0.0.0.0', port: int = 5000):
        """Start the web interface."""
        try:
            # Check if web module is available
            import importlib.util
            if importlib.util.find_spec("web_interface"):
                self.logger.info(f"Starting web interface on {host}:{port}")
                
                # Import the web module dynamically
                import web_interface
                
                # Initialize web app with our analyzers
                web_app = web_interface.create_app(
                    python_analyzer=self.python_analyzer,
                    web_analyzer=self.web_analyzer,
                    csharp_analyzer=self.csharp_analyzer,
                    llm=self.llm
                )
                
                # Start the web server
                web_app.run(host=host, port=port, debug=True)
            else:
                self.logger.error("Web interface module not found")
                print("Error: Web interface module not found. Please install the web components.")
                sys.exit(1)
        
        except Exception as e:
            self.logger.error(f"Error starting web interface: {str(e)}")
            print(f"Error starting web interface: {str(e)}")
            sys.exit(1)


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="CodeRefactor: Advanced Code Analysis & Refactoring Tool")
    
    # Command subparsers
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze code files or directories")
    analyze_parser.add_argument("path", help="File or directory path to analyze")
    analyze_parser.add_argument("-r", "--recursive", action="store_true", help="Recursively analyze directories")
    analyze_parser.add_argument("-p", "--pattern", help="File pattern to match (e.g. *.py)")
    analyze_parser.add_argument("-o", "--output", help="Output file path")
    analyze_parser.add_argument("-f", "--format", choices=["text", "json", "html"], default="text", help="Output format")
    analyze_parser.add_argument("-c", "--config", help="Path to configuration file")
    
    # Fix command
    fix_parser = subparsers.add_parser("fix", help="Get fix suggestions for an issue")
    fix_parser.add_argument("file", help="File path")
    fix_parser.add_argument("issue_id", help="Issue ID to fix")
    fix_parser.add_argument("-o", "--output", help="Output file path")
    fix_parser.add_argument("-c", "--config", help="Path to configuration file")
    
    # Web interface command
    web_parser = subparsers.add_parser("web", help="Start the web interface")
    web_parser.add_argument("-H", "--host", default="0.0.0.0", help="Host to bind to")
    web_parser.add_argument("-p", "--port", type=int, default=5000, help="Port to listen on")
    web_parser.add_argument("-c", "--config", help="Path to configuration file")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Create the app
    app = CodeRefactorApp(args.config if hasattr(args, 'config') else None)
    
    # Execute the command
    if args.command == "analyze":
        if os.path.isfile(args.path):
            # Analyze a single file
            result = app.analyze_file(args.path)
        else:
            # Analyze a directory
            result = app.analyze_directory(args.path, args.recursive, args.pattern)
        
        # Output the results
        app.output_results(result, args.format, args.output)
    
    elif args.command == "fix":
        # Get fix suggestion
        result = asyncio.run(app.get_fix_suggestion(args.file, args.issue_id))
        
        # Output the results
        app.output_results(result, "json" if args.output else "text", args.output)
    
    elif args.command == "web":
        # Start the web interface
        app.start_web_interface(args.host, args.port)
    
    else:
        # No command specified, show help
        parser.print_help()


if __name__ == "__main__":
    main()