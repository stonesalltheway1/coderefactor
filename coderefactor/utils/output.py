#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Output formatting utilities for CodeRefactor.
Provides functionality to format analysis results in different formats.
"""

import os
import json
import html
import datetime
import tempfile
import webbrowser
from pathlib import Path
from typing import Dict, Any, List, Union, Optional, TextIO

# ANSI color codes for terminal output
COLORS = {
    'RESET': '\033[0m',
    'RED': '\033[31m',
    'GREEN': '\033[32m',
    'YELLOW': '\033[33m',
    'BLUE': '\033[34m',
    'MAGENTA': '\033[35m',
    'CYAN': '\033[36m',
    'BOLD': '\033[1m',
    'UNDERLINE': '\033[4m',
}

# Maps severity levels to colors
SEVERITY_COLORS = {
    'critical': COLORS['BOLD'] + COLORS['RED'],
    'error': COLORS['RED'],
    'warning': COLORS['YELLOW'],
    'info': COLORS['BLUE'],
}


class OutputFormatter:
    """Base class for formatting analysis results."""
    
    def __init__(self, use_colors: bool = True):
        self.use_colors = use_colors and self._supports_colors()
    
    def _supports_colors(self) -> bool:
        """Check if the terminal supports colors."""
        return hasattr(os, 'isatty') and os.isatty(1)
    
    def format(self, result: Dict[str, Any]) -> str:
        """
        Format the analysis result.
        
        Args:
            result: The analysis result dictionary.
        
        Returns:
            The formatted result as a string.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def write(self, result: Dict[str, Any], output_file: Optional[str] = None) -> None:
        """
        Write the formatted result to a file or stdout.
        
        Args:
            result: The analysis result dictionary.
            output_file: Optional path to write the output to.
                        If None, writes to stdout.
        """
        formatted = self.format(result)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(formatted)
        else:
            print(formatted)


class TextFormatter(OutputFormatter):
    """Formats analysis results as plain text."""
    
    def format(self, result: Dict[str, Any]) -> str:
        """Format the analysis result as plain text."""
        lines = []
        
        # Handle error
        if "error" in result:
            return f"ERROR: {result['error']}"
        
        # Single file report
        if "file_path" in result:
            lines.append(f"Analysis Results for {result['file_path']}")
            lines.append("-" * 80)
            
            if len(result.get("issues", [])) == 0:
                lines.append("No issues found!")
            else:
                lines.append(f"Found {len(result['issues'])} issues:")
                lines.append("")
                
                # Group issues by severity
                severity_order = ["critical", "error", "warning", "info"]
                severity_issues = {s: [] for s in severity_order}
                
                for issue in result.get("issues", []):
                    severity = issue.get("severity", "info").lower()
                    severity_issues[severity].append(issue)
                
                # Output issues by severity
                for severity in severity_order:
                    issues = severity_issues[severity]
                    if issues:
                        if self.use_colors:
                            color = SEVERITY_COLORS.get(severity, COLORS['RESET'])
                            lines.append(f"{color}{severity.upper()} level issues:{COLORS['RESET']}")
                        else:
                            lines.append(f"{severity.upper()} level issues:")
                        
                        for issue in issues:
                            location = f"Line {issue.get('line', '?')}"
                            if issue.get('column'):
                                location += f", Column {issue.get('column')}"
                            
                            lines.append(f"  {location}: {issue.get('message', '')} [{issue.get('rule_id', '?')}]")
                            lines.append(f"    {issue.get('description', '')}")
                            if issue.get('fixable', False):
                                lines.append(f"    (Fixable: {issue.get('fix_type', 'unknown')})")
                            lines.append("")
            
            # Add AI suggestions if available
            if "suggestions" in result and result["suggestions"]:
                lines.append("\nAI Suggestions:")
                for suggestion in result["suggestions"]:
                    lines.append(f"  {suggestion.get('title', 'Suggestion')}")
                    lines.append(f"    {suggestion.get('description', '')}")
                    lines.append("")
            
            # Add AI explanation if available
            if "ai_explanation" in result:
                lines.append("\nAI Code Assessment:")
                lines.append(result["ai_explanation"])
        
        # Directory report
        elif "directory" in result:
            lines.append(f"Analysis Results for Directory: {result['directory']}")
            lines.append("-" * 80)
            lines.append(f"Files analyzed: {result.get('files_analyzed', 0)}")
            lines.append(f"Total issues found: {result.get('total_issues', 0)}")
            
            # Issues by severity
            lines.append("\nIssues by severity:")
            for severity, count in result.get("issues_by_severity", {}).items():
                if self.use_colors:
                    color = SEVERITY_COLORS.get(severity, COLORS['RESET'])
                    lines.append(f"  {color}{severity.upper()}{COLORS['RESET']}: {count}")
                else:
                    lines.append(f"  {severity.upper()}: {count}")
            
            # Issues by category
            lines.append("\nIssues by category:")
            for category, count in sorted(
                result.get("issues_by_category", {}).items(),
                key=lambda x: x[1],
                reverse=True
            ):
                lines.append(f"  {category}: {count}")
            
            # Top files with issues
            if result.get("files", []):
                lines.append("\nTop files with most issues:")
                files_sorted = sorted(
                    result["files"],
                    key=lambda f: len(f.get("issues", [])),
                    reverse=True
                )
                for i, file in enumerate(files_sorted[:10]):  # Show top 10
                    lines.append(f"  {i+1}. {file.get('file_path', '?')}: {len(file.get('issues', []))} issues")
        
        return "\n".join(lines)


class JSONFormatter(OutputFormatter):
    """Formats analysis results as JSON."""
    
    def __init__(self, use_colors: bool = True, indent: int = 2):
        super().__init__(use_colors)
        self.indent = indent
    
    def format(self, result: Dict[str, Any]) -> str:
        """Format the analysis result as JSON."""
        # Convert datetime objects to ISO format strings
        def json_serializer(obj):
            if isinstance(obj, (datetime.datetime, datetime.date)):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")
        
        return json.dumps(result, indent=self.indent, default=json_serializer)


class HTMLFormatter(OutputFormatter):
    """Formats analysis results as HTML."""
    
    def __init__(self, use_colors: bool = True, include_css: bool = True):
        super().__init__(use_colors)
        self.include_css = include_css
    
    def format(self, result: Dict[str, Any]) -> str:
        """Format the analysis result as HTML."""
        html_output = []
        
        # Start HTML document
        html_output.append("<!DOCTYPE html>")
        html_output.append("<html lang=\"en\">")
        html_output.append("<head>")
        html_output.append("    <meta charset=\"UTF-8\">")
        html_output.append("    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">")
        html_output.append("    <title>CodeRefactor Analysis Report</title>")
        
        # Include CSS
        if self.include_css:
            html_output.append("    <style>")
            html_output.append(self._get_css())
            html_output.append("    </style>")
        
        html_output.append("</head>")
        html_output.append("<body>")
        html_output.append("    <div class=\"container\">")
        html_output.append("        <h1>CodeRefactor Analysis Report</h1>")
        
        # Add timestamp
        timestamp = result.get("timestamp", datetime.datetime.now().isoformat())
        html_output.append(f"        <p class=\"timestamp\">Generated on: {timestamp}</p>")
        
        # Handle error
        if "error" in result:
            html_output.append(f"        <div class=\"error\"><h2>Error</h2><p>{html.escape(result['error'])}</p></div>")
        
        # Single file report
        elif "file_path" in result:
            file_path = result["file_path"]
            issues = result.get("issues", [])
            
            html_output.append(f"        <h2>Analysis Results for: {html.escape(file_path)}</h2>")
            
            if not issues:
                html_output.append("        <div class=\"summary-box\"><p>No issues found! Good job!</p></div>")
            else:
                html_output.append(f"        <div class=\"summary-box\"><p>Found {len(issues)} issues</p></div>")
                
                # Issues table
                html_output.append("        <h3>Issues</h3>")
                html_output.append("        <table>")
                html_output.append("            <tr>")
                html_output.append("                <th>Severity</th>")
                html_output.append("                <th>Location</th>")
                html_output.append("                <th>Rule</th>")
                html_output.append("                <th>Description</th>")
                html_output.append("                <th>Fixable</th>")
                html_output.append("            </tr>")
                
                # Sort issues by severity
                severity_order = {"critical": 0, "error": 1, "warning": 2, "info": 3}
                sorted_issues = sorted(
                    issues,
                    key=lambda x: (severity_order.get(x.get("severity", "info").lower(), 99), x.get("line", 0))
                )
                
                for issue in sorted_issues:
                    severity = issue.get("severity", "info").lower()
                    location = f"Line {issue.get('line', '?')}"
                    if issue.get('column'):
                        location += f", Col {issue.get('column')}"
                    
                    html_output.append(f"            <tr class=\"issue-{severity}\">")
                    html_output.append(f"                <td>{severity.upper()}</td>")
                    html_output.append(f"                <td>{location}</td>")
                    html_output.append(f"                <td>{html.escape(issue.get('rule_id', ''))}</td>")
                    
                    description = f"""
                        <strong>{html.escape(issue.get('message', ''))}</strong>
                        <p>{html.escape(issue.get('description', ''))}</p>
                    """
                    
                    if issue.get('code_snippet'):
                        description += f"""
                            <div class="code-snippet"><pre>{html.escape(issue.get('code_snippet', ''))}</pre></div>
                        """
                    
                    html_output.append(f"                <td>{description}</td>")
                    
                    fixable = issue.get('fixable', False)
                    fix_text = issue.get('fix_type', 'No') if fixable else 'No'
                    html_output.append(f"                <td>{fix_text}</td>")
                    
                    html_output.append("            </tr>")
                
                html_output.append("        </table>")
            
            # Add AI suggestions if available
            if "suggestions" in result and result["suggestions"]:
                html_output.append("        <h3>AI Suggestions</h3>")
                
                for suggestion in result["suggestions"]:
                    html_output.append("        <div class=\"suggestion\">")
                    html_output.append(f"            <h4>{html.escape(suggestion.get('title', 'Suggestion'))}</h4>")
                    html_output.append(f"            <p>{html.escape(suggestion.get('description', ''))}</p>")
                    
                    if "before" in suggestion and "after" in suggestion:
                        html_output.append("            <h5>Before:</h5>")
                        html_output.append(f"            <div class=\"code-snippet\"><pre>{html.escape(suggestion.get('before', ''))}</pre></div>")
                        html_output.append("            <h5>After:</h5>")
                        html_output.append(f"            <div class=\"code-snippet\"><pre>{html.escape(suggestion.get('after', ''))}</pre></div>")
                    
                    html_output.append("        </div>")
            
            # Add AI explanation if available
            if "ai_explanation" in result:
                html_output.append("        <div class=\"summary-box\">")
                html_output.append("            <h3>AI Code Assessment</h3>")
                html_output.append(f"            <p>{html.escape(result['ai_explanation'])}</p>")
                html_output.append("        </div>")
        
        # Directory report
        elif "directory" in result:
            directory = result["directory"]
            files_analyzed = result.get("files_analyzed", 0)
            total_issues = result.get("total_issues", 0)
            
            html_output.append(f"        <h2>Analysis Results for Directory: {html.escape(directory)}</h2>")
            
            # Summary box
            html_output.append("        <div class=\"summary-box\">")
            html_output.append(f"            <p>Files analyzed: {files_analyzed}</p>")
            html_output.append(f"            <p>Total issues found: {total_issues}</p>")
            html_output.append("        </div>")
            
            # Issues by severity
            html_output.append("        <h3>Issues by Severity</h3>")
            html_output.append("        <table>")
            html_output.append("            <tr><th>Severity</th><th>Count</th></tr>")
            
            for severity, count in result.get("issues_by_severity", {}).items():
                html_output.append(f"            <tr class=\"issue-{severity.lower()}\">")
                html_output.append(f"                <td>{severity.upper()}</td>")
                html_output.append(f"                <td>{count}</td>")
                html_output.append("            </tr>")
            
            html_output.append("        </table>")
            
            # Issues by category
            html_output.append("        <h3>Issues by Category</h3>")
            html_output.append("        <table>")
            html_output.append("            <tr><th>Category</th><th>Count</th></tr>")
            
            for category, count in sorted(
                result.get("issues_by_category", {}).items(),
                key=lambda x: x[1],
                reverse=True
            ):
                html_output.append("            <tr>")
                html_output.append(f"                <td>{html.escape(category)}</td>")
                html_output.append(f"                <td>{count}</td>")
                html_output.append("            </tr>")
            
            html_output.append("        </table>")
            
            # Files details
            if result.get("files", []):
                html_output.append("        <h3>Files</h3>")
                
                # Sort files by issue count
                files_sorted = sorted(
                    result["files"],
                    key=lambda f: len(f.get("issues", [])),
                    reverse=True
                )
                
                for i, file in enumerate(files_sorted):
                    file_path = file.get("file_path", "")
                    issue_count = len(file.get("issues", []))
                    file_id = f"file-{i}"
                    
                    html_output.append(f"        <div class=\"file-summary\" onclick=\"toggleFile('{file_id}')\">")
                    html_output.append(f"            {html.escape(file_path)} - {issue_count} issues")
                    html_output.append("        </div>")
                    html_output.append(f"        <div id=\"{file_id}\" class=\"hidden\">")
                    
                    if file.get("issues", []):
                        # Issues table for this file
                        html_output.append("            <table>")
                        html_output.append("                <tr>")
                        html_output.append("                    <th>Severity</th>")
                        html_output.append("                    <th>Location</th>")
                        html_output.append("                    <th>Rule</th>")
                        html_output.append("                    <th>Description</th>")
                        html_output.append("                </tr>")
                        
                        # Sort issues by severity
                        severity_order = {"critical": 0, "error": 1, "warning": 2, "info": 3}
                        sorted_issues = sorted(
                            file.get("issues", []),
                            key=lambda x: (severity_order.get(x.get("severity", "info").lower(), 99), x.get("line", 0))
                        )
                        
                        for issue in sorted_issues:
                            severity = issue.get("severity", "info").lower()
                            location = f"Line {issue.get('line', '?')}"
                            if issue.get('column'):
                                location += f", Col {issue.get('column')}"
                            
                            html_output.append(f"                <tr class=\"issue-{severity}\">")
                            html_output.append(f"                    <td>{severity.upper()}</td>")
                            html_output.append(f"                    <td>{location}</td>")
                            html_output.append(f"                    <td>{html.escape(issue.get('rule_id', ''))}</td>")
                            
                            description = f"""
                                <strong>{html.escape(issue.get('message', ''))}</strong>
                                <p>{html.escape(issue.get('description', ''))}</p>
                            """
                            
                            html_output.append(f"                    <td>{description}</td>")
                            html_output.append("                </tr>")
                        
                        html_output.append("            </table>")
                    else:
                        html_output.append("            <p>No issues found in this file!</p>")
                    
                    html_output.append("        </div>")
        
        # Add JavaScript for file toggling
        html_output.append("        <script>")
        html_output.append("        function toggleFile(fileId) {")
        html_output.append("            const element = document.getElementById(fileId);")
        html_output.append("            if (element.classList.contains('hidden')) {")
        html_output.append("                element.classList.remove('hidden');")
        html_output.append("            } else {")
        html_output.append("                element.classList.add('hidden');")
        html_output.append("            }")
        html_output.append("        }")
        html_output.append("        </script>")
        
        # End HTML document
        html_output.append("    </div>")
        html_output.append("</body>")
        html_output.append("</html>")
        
        return "\n".join(html_output)
    
    def _get_css(self) -> str:
        """Return the CSS for HTML reports."""
        return """
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            .container {
                width: 100%;
                box-sizing: border-box;
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
            .error {
                background-color: #fee;
                border: 1px solid #e74c3c;
                border-radius: 5px;
                padding: 15px;
                margin-bottom: 20px;
            }
            .timestamp {
                color: #666;
                font-style: italic;
                margin-bottom: 20px;
            }
        """


class MarkdownFormatter(OutputFormatter):
    """Formats analysis results as Markdown."""
    
    def format(self, result: Dict[str, Any]) -> str:
        """Format the analysis result as Markdown."""
        md_output = []
        
        # Handle error
        if "error" in result:
            md_output.append(f"# Error\n\n{result['error']}")
            return "\n".join(md_output)
        
        # Add title and timestamp
        md_output.append("# CodeRefactor Analysis Report\n")
        timestamp = result.get("timestamp", datetime.datetime.now().isoformat())
        md_output.append(f"Generated on: {timestamp}\n")
        
        # Single file report
        if "file_path" in result:
            file_path = result["file_path"]
            issues = result.get("issues", [])
            
            md_output.append(f"## Analysis Results for: {file_path}\n")
            
            if not issues:
                md_output.append("No issues found! Good job!\n")
            else:
                md_output.append(f"Found {len(issues)} issues\n")
                
                # Group issues by severity
                severity_order = ["critical", "error", "warning", "info"]
                severity_issues = {s: [] for s in severity_order}
                
                for issue in issues:
                    severity = issue.get("severity", "info").lower()
                    severity_issues[severity].append(issue)
                
                # Output issues by severity
                for severity in severity_order:
                    issues = severity_issues[severity]
                    if issues:
                        md_output.append(f"### {severity.upper()} level issues\n")
                        
                        for issue in issues:
                            location = f"Line {issue.get('line', '?')}"
                            if issue.get('column'):
                                location += f", Column {issue.get('column')}"
                            
                            md_output.append(f"- **{location}**: {issue.get('message', '')} [{issue.get('rule_id', '?')}]")
                            md_output.append(f"  - {issue.get('description', '')}")
                            if issue.get('fixable', False):
                                md_output.append(f"  - (Fixable: {issue.get('fix_type', 'unknown')})")
                            
                            if issue.get('code_snippet'):
                                md_output.append(f"  ```\n  {issue.get('code_snippet', '').strip()}\n  ```")
                            
                            md_output.append("")
            
            # Add AI suggestions if available
            if "suggestions" in result and result["suggestions"]:
                md_output.append("## AI Suggestions\n")
                
                for suggestion in result["suggestions"]:
                    md_output.append(f"### {suggestion.get('title', 'Suggestion')}\n")
                    md_output.append(f"{suggestion.get('description', '')}\n")
                    
                    if "before" in suggestion and "after" in suggestion:
                        md_output.append("**Before:**\n")
                        md_output.append(f"```\n{suggestion.get('before', '')}\n```\n")
                        md_output.append("**After:**\n")
                        md_output.append(f"```\n{suggestion.get('after', '')}\n```\n")
            
            # Add AI explanation if available
            if "ai_explanation" in result:
                md_output.append("## AI Code Assessment\n")
                md_output.append(f"{result['ai_explanation']}\n")
        
        # Directory report
        elif "directory" in result:
            directory = result["directory"]
            files_analyzed = result.get("files_analyzed", 0)
            total_issues = result.get("total_issues", 0)
            
            md_output.append(f"## Analysis Results for Directory: {directory}\n")
            md_output.append(f"- Files analyzed: {files_analyzed}")
            md_output.append(f"- Total issues found: {total_issues}\n")
            
            # Issues by severity
            md_output.append("### Issues by Severity\n")
            for severity, count in result.get("issues_by_severity", {}).items():
                md_output.append(f"- **{severity.upper()}**: {count}")
            
            md_output.append("")
            
            # Issues by category
            md_output.append("### Issues by Category\n")
            for category, count in sorted(
                result.get("issues_by_category", {}).items(),
                key=lambda x: x[1],
                reverse=True
            ):
                md_output.append(f"- {category}: {count}")
            
            md_output.append("")
            
            # Top files with issues
            if result.get("files", []):
                md_output.append("### Top Files with Most Issues\n")
                
                # Sort files by issue count
                files_sorted = sorted(
                    result["files"],
                    key=lambda f: len(f.get("issues", [])),
                    reverse=True
                )
                
                for i, file in enumerate(files_sorted[:10]):  # Show top 10
                    file_path = file.get("file_path", "")
                    issue_count = len(file.get("issues", []))
                    md_output.append(f"{i+1}. **{file_path}**: {issue_count} issues")
        
        return "\n".join(md_output)


def format_output(result: Dict[str, Any], format_type: str = "text", output_file: Optional[str] = None, use_colors: bool = True, open_browser: bool = False) -> None:
    """
    Format and output the analysis result.
    
    Args:
        result: The analysis result dictionary.
        format_type: The output format type (text, json, html, markdown).
        output_file: Optional path to write the output to.
                    If None, writes to stdout.
        use_colors: Whether to use colors in the output (if supported).
        open_browser: Whether to open the output in a browser (for HTML format).
    """
    # Create the appropriate formatter
    formatters = {
        "text": TextFormatter(use_colors),
        "json": JSONFormatter(use_colors),
        "html": HTMLFormatter(use_colors),
        "markdown": MarkdownFormatter(use_colors),
    }
    
    if format_type not in formatters:
        raise ValueError(f"Unsupported format type: {format_type}")
    
    formatter = formatters[format_type]
    
    # Format and write the output
    if output_file:
        formatter.write(result, output_file)
        
        # Open the output in a browser if requested
        if open_browser and format_type == "html":
            webbrowser.open(f"file://{os.path.abspath(output_file)}")
    else:
        # If no output file is specified, and format is HTML, create a temporary file
        if format_type == "html" and open_browser:
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp_file:
                formatter.write(result, tmp_file.name)
                webbrowser.open(f"file://{os.path.abspath(tmp_file.name)}")
        else:
            formatter.write(result)


if __name__ == "__main__":
    # Test the output formatters
    import argparse
    
    parser = argparse.ArgumentParser(description="Test output formatters")
    parser.add_argument("--format", default="text", choices=["text", "json", "html", "markdown"],
                       help="Output format")
    parser.add_argument("--file", help="Output file path")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    parser.add_argument("--open-browser", action="store_true", help="Open HTML output in browser")
    
    args = parser.parse_args()
    
    # Create a sample result
    sample_result = {
        "file_path": "example.py",
        "timestamp": datetime.datetime.now().isoformat(),
        "issues": [
            {
                "id": "1",
                "line": 10,
                "column": 5,
                "message": "Unused variable 'x'",
                "description": "Variable 'x' is assigned but never used.",
                "severity": "warning",
                "category": "maintainability",
                "source": "pylint",
                "rule_id": "W0612",
                "fixable": True,
                "fix_type": "simple",
                "code_snippet": "    x = 10  # This variable is not used"
            },
            {
                "id": "2",
                "line": 15,
                "column": 1,
                "message": "Missing docstring",
                "description": "Function is missing a docstring.",
                "severity": "info",
                "category": "style",
                "source": "pylint",
                "rule_id": "C0111",
                "fixable": True,
                "fix_type": "llm-assisted",
                "code_snippet": "def example_function():\n    return 42"
            }
        ],
        "suggestions": [
            {
                "title": "Remove unused variable",
                "description": "The variable 'x' is assigned but never used. It should be removed or used.",
                "before": "    x = 10  # This variable is not used",
                "after": "    # Variable removed"
            }
        ],
        "ai_explanation": "The code is generally well-structured but has some minor issues like unused variables and missing docstrings."
    }
    
    # Format and output the result
    format_output(
        sample_result,
        format_type=args.format,
        output_file=args.file,
        use_colors=not args.no_color,
        open_browser=args.open_browser
    )