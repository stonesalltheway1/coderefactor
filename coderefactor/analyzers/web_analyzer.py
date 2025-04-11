#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Web Technologies Analyzer: Integration with HTML, CSS, and JavaScript linters.
Part of the CodeRefactor project.
"""

import os
import sys
import json
import subprocess
import tempfile
import logging
from typing import List, Dict, Any, Optional, Set
from enum import Enum, auto
import uuid
from pathlib import Path
import traceback
from dataclasses import dataclass, field

# Import the shared issue model from python_analyzer
from python_analyzer import AnalysisIssue, AnalysisResult, IssueSeverity, IssueCategory


class WebTechAnalyzer:
    """Analyzer for HTML, CSS, and JavaScript/TypeScript files using popular linters."""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger("coderefactor.webtech")
        
        # Linter availability flags
        self._has_eslint = self._check_eslint()
        self._has_stylelint = self._check_stylelint()
        self._has_htmlhint = self._check_htmlhint()
        
        # Setup linting configurations - can be customized via config
        self._setup_linting_configs()
    
    def _check_eslint(self) -> bool:
        """Check if ESLint is installed."""
        try:
            subprocess.run(
                ["npx", "eslint", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            self.logger.info("ESLint is available")
            return True
        except Exception:
            self.logger.warning("ESLint is not available. JavaScript/TypeScript analysis will be limited.")
            return False
    
    def _check_stylelint(self) -> bool:
        """Check if Stylelint is installed."""
        try:
            subprocess.run(
                ["npx", "stylelint", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            self.logger.info("Stylelint is available")
            return True
        except Exception:
            self.logger.warning("Stylelint is not available. CSS analysis will be limited.")
            return False
    
    def _check_htmlhint(self) -> bool:
        """Check if HTMLHint is installed."""
        try:
            subprocess.run(
                ["npx", "htmlhint", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            self.logger.info("HTMLHint is available")
            return True
        except Exception:
            self.logger.warning("HTMLHint is not available. HTML analysis will be limited.")
            return False
    
    def _setup_linting_configs(self):
        """Setup linting configuration files in a temporary directory."""
        # Base directory for configs
        self.config_dir = tempfile.mkdtemp(prefix="coderefactor-config-")
        self.logger.debug(f"Created temporary config directory: {self.config_dir}")
        
        # ESLint config
        if self._has_eslint:
            self._eslint_config_path = os.path.join(self.config_dir, ".eslintrc.json")
            with open(self._eslint_config_path, "w") as f:
                json.dump({
                    "env": {
                        "browser": True,
                        "es2021": True,
                        "node": True
                    },
                    "extends": [
                        "eslint:recommended"
                    ],
                    "parserOptions": {
                        "ecmaVersion": "latest",
                        "sourceType": "module"
                    },
                    "rules": {
                        "indent": ["error", 2],
                        "quotes": ["warn", "single"],
                        "semi": ["error", "always"],
                        "no-unused-vars": "warn",
                        "no-console": "warn",
                        "no-debugger": "warn"
                    }
                }, f, indent=2)
        
        # Stylelint config
        if self._has_stylelint:
            self._stylelint_config_path = os.path.join(self.config_dir, ".stylelintrc.json")
            with open(self._stylelint_config_path, "w") as f:
                json.dump({
                    "extends": [
                        "stylelint-config-standard"
                    ],
                    "rules": {
                        "indentation": 2,
                        "color-no-invalid-hex": True,
                        "font-family-no-duplicate-names": True,
                        "block-no-empty": True
                    }
                }, f, indent=2)
        
        # HTMLHint config
        if self._has_htmlhint:
            self._htmlhint_config_path = os.path.join(self.config_dir, ".htmlhintrc")
            with open(self._htmlhint_config_path, "w") as f:
                json.dump({
                    "tagname-lowercase": True,
                    "attr-lowercase": True,
                    "attr-value-double-quotes": True,
                    "doctype-first": True,
                    "spec-char-escape": True,
                    "id-unique": True,
                    "src-not-empty": True,
                    "attr-no-duplication": True,
                    "title-require": True
                }, f, indent=2)
    
    def analyze_file(self, file_path: str) -> AnalysisResult:
        """Analyze a web technology file (HTML, CSS, JavaScript, TypeScript)."""
        if not os.path.exists(file_path):
            return AnalysisResult(
                file_path=file_path,
                error="File does not exist"
            )
        
        # Determine file type based on extension
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext in ['.js', '.jsx', '.ts', '.tsx']:
            return self._analyze_js_ts(file_path)
        elif file_ext in ['.css', '.scss', '.less']:
            return self._analyze_css(file_path)
        elif file_ext in ['.html', '.htm', '.xhtml']:
            return self._analyze_html(file_path)
        else:
            return AnalysisResult(
                file_path=file_path,
                error=f"Unsupported file type: {file_ext}"
            )
    
    def _analyze_js_ts(self, file_path: str) -> AnalysisResult:
        """Analyze JavaScript or TypeScript file."""
        self.logger.info(f"Analyzing JS/TS file: {file_path}")
        issues = []
        
        # Use ESLint if available
        if self._has_eslint:
            try:
                eslint_issues = self._run_eslint(file_path)
                issues.extend(eslint_issues)
            except Exception as e:
                self.logger.error(f"Error running ESLint: {str(e)}")
                self.logger.debug(traceback.format_exc())
        
        # Add syntactic analysis results
        try:
            # Basic syntax checks (can be expanded)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Check for unbalanced brackets
            bracket_issues = self._check_unbalanced_brackets(content, file_path)
            issues.extend(bracket_issues)
            
            # Add more syntax checks as needed
        except Exception as e:
            self.logger.error(f"Error analyzing JS/TS file: {str(e)}")
            self.logger.debug(traceback.format_exc())
        
        return AnalysisResult(file_path=file_path, issues=issues)
    
    def _analyze_css(self, file_path: str) -> AnalysisResult:
        """Analyze CSS file."""
        self.logger.info(f"Analyzing CSS file: {file_path}")
        issues = []
        
        # Use Stylelint if available
        if self._has_stylelint:
            try:
                stylelint_issues = self._run_stylelint(file_path)
                issues.extend(stylelint_issues)
            except Exception as e:
                self.logger.error(f"Error running Stylelint: {str(e)}")
                self.logger.debug(traceback.format_exc())
        
        # Add syntactic analysis results
        try:
            # Basic syntax checks
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Check for unbalanced brackets
            bracket_issues = self._check_unbalanced_brackets(content, file_path)
            issues.extend(bracket_issues)
            
            # Check for invalid color values
            color_issues = self._check_css_colors(content, file_path)
            issues.extend(color_issues)
            
            # Add more CSS-specific checks as needed
        except Exception as e:
            self.logger.error(f"Error analyzing CSS file: {str(e)}")
            self.logger.debug(traceback.format_exc())
        
        return AnalysisResult(file_path=file_path, issues=issues)
    
    def _analyze_html(self, file_path: str) -> AnalysisResult:
        """Analyze HTML file."""
        self.logger.info(f"Analyzing HTML file: {file_path}")
        issues = []
        
        # Use HTMLHint if available
        if self._has_htmlhint:
            try:
                htmlhint_issues = self._run_htmlhint(file_path)
                issues.extend(htmlhint_issues)
            except Exception as e:
                self.logger.error(f"Error running HTMLHint: {str(e)}")
                self.logger.debug(traceback.format_exc())
        
        # Add syntactic analysis results
        try:
            # Basic syntax checks
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Check for unmatched HTML tags
            tag_issues = self._check_unmatched_html_tags(content, file_path)
            issues.extend(tag_issues)
            
            # Add more HTML-specific checks as needed
        except Exception as e:
            self.logger.error(f"Error analyzing HTML file: {str(e)}")
            self.logger.debug(traceback.format_exc())
        
        return AnalysisResult(file_path=file_path, issues=issues)
    
    def _run_eslint(self, file_path: str) -> List[AnalysisIssue]:
        """Run ESLint on JavaScript/TypeScript file."""
        issues = []
        
        try:
            # Run ESLint with JSON reporter
            cmd = [
                "npx", "eslint",
                "--format", "json",
                "--config", self._eslint_config_path,
                file_path
            ]
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            # Parse the JSON output
            if result.stdout:
                eslint_result = json.loads(result.stdout)
                
                for file_result in eslint_result:
                    if "messages" in file_result:
                        for msg in file_result["messages"]:
                            # Map ESLint severity to our severity
                            severity = IssueSeverity.WARNING
                            if msg.get("severity") == 2:  # Error
                                severity = IssueSeverity.ERROR
                            elif msg.get("severity") == 1:  # Warning
                                severity = IssueSeverity.WARNING
                            
                            # Map rule to category
                            category = IssueCategory.STYLE
                            rule_id = msg.get("ruleId", "")
                            
                            if rule_id:
                                if "security" in rule_id:
                                    category = IssueCategory.SECURITY
                                elif "performance" in rule_id:
                                    category = IssueCategory.PERFORMANCE
                                elif "complexity" in rule_id:
                                    category = IssueCategory.COMPLEXITY
                                elif "error" in rule_id:
                                    category = IssueCategory.ERROR
                            
                            issues.append(AnalysisIssue(
                                id=str(uuid.uuid4()),
                                file_path=file_path,
                                line=msg.get("line", 1),
                                column=msg.get("column", 1),
                                end_line=msg.get("endLine"),
                                end_column=msg.get("endColumn"),
                                message=msg.get("message", ""),
                                description=f"{rule_id}: {msg.get('message', '')}",
                                severity=severity,
                                category=category,
                                source="eslint",
                                rule_id=rule_id,
                                fixable=msg.get("fix") is not None,
                                fix_type="automated" if msg.get("fix") else "manual",
                                code_snippet=self._extract_code_snippet(file_path, msg.get("line", 1))
                            ))
        except Exception as e:
            self.logger.error(f"Error running ESLint: {str(e)}")
        
        return issues
    
    def _run_stylelint(self, file_path: str) -> List[AnalysisIssue]:
        """Run Stylelint on CSS file."""
        issues = []
        
        try:
            # Run Stylelint with JSON reporter
            cmd = [
                "npx", "stylelint",
                "--formatter", "json",
                "--config", self._stylelint_config_path,
                file_path
            ]
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            # Parse the JSON output
            if result.stdout:
                stylelint_result = json.loads(result.stdout)
                
                for file_result in stylelint_result:
                    if "warnings" in file_result:
                        for warning in file_result["warnings"]:
                            # Map severity
                            severity = IssueSeverity.WARNING
                            if warning.get("severity") == "error":
                                severity = IssueSeverity.ERROR
                            
                            # Determine category
                            category = IssueCategory.STYLE
                            rule = warning.get("rule", "")
                            
                            if rule:
                                if "performance" in rule:
                                    category = IssueCategory.PERFORMANCE
                                elif "compatibility" in rule:
                                    category = IssueCategory.MAINTAINABILITY
                            
                            issues.append(AnalysisIssue(
                                id=str(uuid.uuid4()),
                                file_path=file_path,
                                line=warning.get("line", 1),
                                column=warning.get("column", 1),
                                message=warning.get("text", ""),
                                description=warning.get("text", ""),
                                severity=severity,
                                category=category,
                                source="stylelint",
                                rule_id=warning.get("rule", ""),
                                fixable=False,  # Stylelint doesn't provide fix info in JSON
                                fix_type="manual",
                                code_snippet=self._extract_code_snippet(file_path, warning.get("line", 1))
                            ))
        except Exception as e:
            self.logger.error(f"Error running Stylelint: {str(e)}")
        
        return issues
    
    def _run_htmlhint(self, file_path: str) -> List[AnalysisIssue]:
        """Run HTMLHint on HTML file."""
        issues = []
        
        try:
            # Run HTMLHint with JSON reporter
            cmd = [
                "npx", "htmlhint",
                "--config", self._htmlhint_config_path,
                "--format", "json",
                file_path
            ]
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            # Parse the JSON output
            if result.stdout:
                try:
                    htmlhint_result = json.loads(result.stdout)
                    
                    for file_result in htmlhint_result:
                        if "messages" in file_result:
                            for msg in file_result["messages"]:
                                # Map severity
                                severity = IssueSeverity.WARNING
                                if msg.get("type") == "error":
                                    severity = IssueSeverity.ERROR
                                
                                issues.append(AnalysisIssue(
                                    id=str(uuid.uuid4()),
                                    file_path=file_path,
                                    line=msg.get("line", 1),
                                    column=msg.get("col", 1),
                                    message=msg.get("message", ""),
                                    description=f"{msg.get('rule', '')}: {msg.get('message', '')}",
                                    severity=severity,
                                    category=IssueCategory.STYLE,
                                    source="htmlhint",
                                    rule_id=msg.get("rule", ""),
                                    fixable=False,  # HTMLHint doesn't provide fix info
                                    fix_type="manual",
                                    code_snippet=self._extract_code_snippet(file_path, msg.get("line", 1))
                                ))
                except json.JSONDecodeError:
                    self.logger.warning("HTMLHint output is not valid JSON")
        except Exception as e:
            self.logger.error(f"Error running HTMLHint: {str(e)}")
        
        return issues
    
    def _check_unbalanced_brackets(self, content: str, file_path: str) -> List[AnalysisIssue]:
        """Check for unbalanced brackets in code."""
        issues = []
        
        # Stack to track brackets
        stack = []
        
        # Track line and column
        line = 1
        column = 1
        
        # Opening and closing brackets
        brackets = {
            "{": "}",
            "[": "]",
            "(": ")"
        }
        
        # Positions for reporting issues
        positions = {}
        
        for i, char in enumerate(content):
            # Update line and column
            if char == "\n":
                line += 1
                column = 1
            else:
                column += 1
            
            # Check for brackets
            if char in brackets:
                stack.append(char)
                positions[len(stack)] = (line, column)
            elif char in brackets.values():
                if not stack:
                    # Closing bracket without opening
                    issues.append(AnalysisIssue(
                        id=str(uuid.uuid4()),
                        file_path=file_path,
                        line=line,
                        column=column,
                        message=f"Unexpected closing bracket '{char}'",
                        description=f"Found closing bracket '{char}' without a matching opening bracket",
                        severity=IssueSeverity.ERROR,
                        category=IssueCategory.SYNTAX,
                        source="coderefactor",
                        rule_id="syntax-error",
                        fixable=False,
                        fix_type="manual",
                        code_snippet=self._extract_code_snippet(file_path, line)
                    ))
                else:
                    opening = stack.pop()
                    if char != brackets[opening]:
                        # Mismatched brackets
                        open_line, open_col = positions[len(stack) + 1]
                        issues.append(AnalysisIssue(
                            id=str(uuid.uuid4()),
                            file_path=file_path,
                            line=line,
                            column=column,
                            message=f"Mismatched brackets: '{opening}' at line {open_line}, column {open_col} and '{char}'",
                            description=f"Opening bracket '{opening}' at line {open_line}, column {open_col} does not match closing bracket '{char}'",
                            severity=IssueSeverity.ERROR,
                            category=IssueCategory.SYNTAX,
                            source="coderefactor",
                            rule_id="syntax-error",
                            fixable=False,
                            fix_type="manual",
                            code_snippet=self._extract_code_snippet(file_path, line)
                        ))
        
        # Check for unclosed brackets
        for i, bracket in enumerate(stack):
            line, column = positions[i + 1]
            issues.append(AnalysisIssue(
                id=str(uuid.uuid4()),
                file_path=file_path,
                line=line,
                column=column,
                message=f"Unclosed bracket '{bracket}'",
                description=f"Opening bracket '{bracket}' at line {line}, column {column} is never closed",
                severity=IssueSeverity.ERROR,
                category=IssueCategory.SYNTAX,
                source="coderefactor",
                rule_id="syntax-error",
                fixable=False,
                fix_type="manual",
                code_snippet=self._extract_code_snippet(file_path, line)
            ))
        
        return issues
    
    def _check_css_colors(self, content: str, file_path: str) -> List[AnalysisIssue]:
        """Check for invalid CSS color values."""
        issues = []
        
        # Regex patterns for color formats
        hex_pattern = r'#([A-Fa-f0-9]{3}|[A-Fa-f0-9]{6}|[A-Fa-f0-9]{8})(?![A-Fa-f0-9])'
        rgb_pattern = r'rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)'
        rgba_pattern = r'rgba\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*([01]?\.?\d*)\s*\)'
        
        import re
        
        # Check for invalid hex colors
        for match in re.finditer(r'#[A-Fa-f0-9]+', content):
            color = match.group(0)
            if not re.match(hex_pattern, color):
                # Get line and column
                line, column = self._get_line_col(content, match.start())
                
                issues.append(AnalysisIssue(
                    id=str(uuid.uuid4()),
                    file_path=file_path,
                    line=line,
                    column=column,
                    message=f"Invalid hex color format: '{color}'",
                    description=f"Hex color '{color}' is not in a valid format. Use #RGB, #RRGGBB, or #RRGGBBAA.",
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.STYLE,
                    source="coderefactor",
                    rule_id="css-color-format",
                    fixable=True,
                    fix_type="automated",
                    code_snippet=self._extract_code_snippet(file_path, line)
                ))
        
        # Check for invalid rgb/rgba values
        for pattern, format_name in [(rgb_pattern, 'rgb'), (rgba_pattern, 'rgba')]:
            for match in re.finditer(pattern, content):
                values = match.groups()
                
                # Check for valid RGB values (0-255)
                if format_name == 'rgb' or format_name == 'rgba':
                    for i in range(3):  # First 3 values are RGB
                        if int(values[i]) > 255:
                            line, column = self._get_line_col(content, match.start())
                            
                            issues.append(AnalysisIssue(
                                id=str(uuid.uuid4()),
                                file_path=file_path,
                                line=line,
                                column=column,
                                message=f"Invalid {format_name} color value: {values[i]} > 255",
                                description=f"RGB values must be between 0 and 255, but found {values[i]}.",
                                severity=IssueSeverity.WARNING,
                                category=IssueCategory.STYLE,
                                source="coderefactor",
                                rule_id="css-color-value",
                                fixable=True,
                                fix_type="automated",
                                code_snippet=self._extract_code_snippet(file_path, line)
                            ))
                
                # Check for valid alpha value (0-1)
                if format_name == 'rgba' and float(values[3]) > 1:
                    line, column = self._get_line_col(content, match.start())
                    
                    issues.append(AnalysisIssue(
                        id=str(uuid.uuid4()),
                        file_path=file_path,
                        line=line,
                        column=column,
                        message=f"Invalid rgba alpha value: {values[3]} > 1",
                        description=f"Alpha values must be between 0 and 1, but found {values[3]}.",
                        severity=IssueSeverity.WARNING,
                        category=IssueCategory.STYLE,
                        source="coderefactor",
                        rule_id="css-color-value",
                        fixable=True,
                        fix_type="automated",
                        code_snippet=self._extract_code_snippet(file_path, line)
                    ))
        
        return issues
    
    def _check_unmatched_html_tags(self, content: str, file_path: str) -> List[AnalysisIssue]:
        """Check for unmatched HTML tags."""
        issues = []
        
        # Stack to track tags
        stack = []
        
        # Track positions
        positions = {}
        
        # Extract tags using regex
        import re
        
        # Pattern for HTML tags (simplistic, doesn't handle all edge cases)
        tag_pattern = r'<\s*(/?)(\w+)[^>]*>'
        
        for match in re.finditer(tag_pattern, content):
            is_closing = match.group(1) == '/'
            tag_name = match.group(2).lower()
            
            # Skip self-closing tags and void elements
            if content[match.end() - 2] == '/' or tag_name in [
                'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
                'link', 'meta', 'param', 'source', 'track', 'wbr'
            ]:
                continue
            
            # Get line and column
            line, column = self._get_line_col(content, match.start())
            
            if is_closing:
                # Closing tag - check if it matches the last opening tag
                if not stack:
                    issues.append(AnalysisIssue(
                        id=str(uuid.uuid4()),
                        file_path=file_path,
                        line=line,
                        column=column,
                        message=f"Unexpected closing tag '</{tag_name}>'",
                        description=f"Found closing tag '</{tag_name}>' without a matching opening tag",
                        severity=IssueSeverity.ERROR,
                        category=IssueCategory.SYNTAX,
                        source="coderefactor",
                        rule_id="html-tag-match",
                        fixable=False,
                        fix_type="manual",
                        code_snippet=self._extract_code_snippet(file_path, line)
                    ))
                else:
                    last_tag, last_line, last_col = stack.pop()
                    if last_tag != tag_name:
                        issues.append(AnalysisIssue(
                            id=str(uuid.uuid4()),
                            file_path=file_path,
                            line=line,
                            column=column,
                            message=f"Mismatched HTML tags: '<{last_tag}>' at line {last_line} and '</{tag_name}>'",
                            description=f"Opening tag '<{last_tag}>' at line {last_line}, column {last_col} does not match closing tag '</{tag_name}>'",
                            severity=IssueSeverity.ERROR,
                            category=IssueCategory.SYNTAX,
                            source="coderefactor",
                            rule_id="html-tag-match",
                            fixable=False,
                            fix_type="manual",
                            code_snippet=self._extract_code_snippet(file_path, line)
                        ))
            else:
                # Opening tag - push to stack
                stack.append((tag_name, line, column))
        
        # Check for unclosed tags
        for tag_name, line, column in stack:
            issues.append(AnalysisIssue(
                id=str(uuid.uuid4()),
                file_path=file_path,
                line=line,
                column=column,
                message=f"Unclosed HTML tag '<{tag_name}>'",
                description=f"Opening tag '<{tag_name}>' at line {line}, column {column} is never closed",
                severity=IssueSeverity.ERROR,
                category=IssueCategory.SYNTAX,
                source="coderefactor",
                rule_id="html-tag-match",
                fixable=False,
                fix_type="manual",
                code_snippet=self._extract_code_snippet(file_path, line)
            ))
        
        return issues
    
    def _get_line_col(self, content: str, pos: int) -> tuple:
        """Get line and column for a position in content."""
        line = content[:pos].count('\n') + 1
        line_start = content.rfind('\n', 0, pos)
        if line_start == -1:
            line_start = 0
        else:
            line_start += 1
        column = pos - line_start + 1
        return line, column
    
    def _extract_code_snippet(self, file_path: str, line_number: int, context_lines: int = 1) -> str:
        """Extract code snippet from a file with context lines."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # Adjust line range to include context
            start_line = max(0, line_number - context_lines - 1)
            end_line = min(len(lines), line_number + context_lines)
            
            return ''.join(lines[start_line:end_line])
        
        except Exception as e:
            self.logger.warning(f"Failed to extract code snippet: {str(e)}")
            return ""


# Test if run directly
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create analyzer
    analyzer = WebTechAnalyzer()
    
    # Check command line args
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        
        # Analyze file
        result = analyzer.analyze_file(file_path)
        
        # Print results
        print(f"Analyzed {file_path}")
        print(f"Found {len(result.issues)} issues")
        
        for issue in result.issues:
            print(f"Line {issue.line}: {issue.source} - {issue.message}")
    
    else:
        print("Please provide a file path to analyze")