#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Python Analysis Engine: Integration with established Python linters and analyzers.
Part of the CodeRefactor project.
"""

import os
import sys
import subprocess
import json
import tempfile
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union, Set
from enum import Enum, auto
import uuid
from pathlib import Path
import importlib.util
import traceback
import ast


class IssueSeverity(Enum):
    """Standardized severity levels for issues."""
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()


class IssueCategory(Enum):
    """Categories of code issues."""
    STYLE = auto()
    TYPING = auto()
    SECURITY = auto()
    PERFORMANCE = auto()
    MAINTAINABILITY = auto()
    COMPLEXITY = auto()
    ERROR = auto()


@dataclass
class AnalysisIssue:
    """Unified issue representation across all analyzers."""
    id: str
    file_path: str
    line: int
    column: int
    end_line: Optional[int] = None
    end_column: Optional[int] = None
    message: str = ""
    description: str = ""
    severity: IssueSeverity = IssueSeverity.WARNING
    category: IssueCategory = IssueCategory.STYLE
    source: str = ""  # Which tool found this issue
    rule_id: str = ""  # Original rule identifier
    fixable: bool = False
    fix_type: str = ""  # Simple, complex, llm-assisted, etc.
    code_snippet: str = ""


@dataclass
class AnalysisResult:
    """Result of code analysis on a file or project."""
    file_path: str
    issues: List[AnalysisIssue] = field(default_factory=list)
    execution_time: float = 0.0
    error: Optional[str] = None


class PythonAnalyzer:
    """Core Python analysis engine that integrates multiple tools."""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger("coderefactor.python")
        
        # Available tools
        self.tools = {
            "pylint": self._analyze_with_pylint,
            "mypy": self._analyze_with_mypy,
            "flake8": self._analyze_with_flake8,
            "bandit": self._analyze_with_bandit,
            "ast": self._analyze_with_ast,
        }
        
        # Check which tools are installed
        self.available_tools = self._check_available_tools()
        
        # Default tool selection if not specified in config
        self.selected_tools = self.config.get("tools", list(self.available_tools))
    
    def _check_available_tools(self) -> Set[str]:
        """Check which analysis tools are installed and available."""
        available = set()
        
        # Check for pylint
        if importlib.util.find_spec("pylint"):
            available.add("pylint")
        
        # Check for mypy
        if importlib.util.find_spec("mypy"):
            available.add("mypy")
        
        # Check for flake8
        if importlib.util.find_spec("flake8"):
            available.add("flake8")
        
        # Check for bandit
        if importlib.util.find_spec("bandit"):
            available.add("bandit")
        
        # AST analyzer is built in
        available.add("ast")
        
        return available

    def analyze_file(self, file_path: str) -> AnalysisResult:
        """Analyze a single Python file using selected tools."""
        if not os.path.exists(file_path) or not file_path.endswith(".py"):
            return AnalysisResult(
                file_path=file_path,
                error="File does not exist or is not a Python file"
            )
        
        self.logger.info(f"Analyzing {file_path}")
        
        # Check which tools to use
        tools_to_run = [t for t in self.selected_tools if t in self.available_tools]
        
        if not tools_to_run:
            self.logger.warning("No analysis tools available")
            return AnalysisResult(
                file_path=file_path,
                error="No analysis tools available"
            )
        
        # Run each tool and collect issues
        all_issues = []
        
        for tool in tools_to_run:
            try:
                self.logger.debug(f"Running {tool} on {file_path}")
                tool_fn = self.tools[tool]
                issues = tool_fn(file_path)
                all_issues.extend(issues)
                self.logger.debug(f"{tool} found {len(issues)} issues")
            except Exception as e:
                self.logger.error(f"Error running {tool}: {str(e)}")
                self.logger.debug(traceback.format_exc())
        
        return AnalysisResult(
            file_path=file_path,
            issues=all_issues
        )
    
    def analyze_directory(self, directory_path: str, pattern: str = "*.py") -> Dict[str, AnalysisResult]:
        """Analyze all Python files in a directory."""
        results = {}
        
        if not os.path.isdir(directory_path):
            self.logger.error(f"Directory {directory_path} does not exist")
            return results
        
        # Find all Python files
        for root, _, files in os.walk(directory_path):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    results[file_path] = self.analyze_file(file_path)
        
        return results
    
    def _analyze_with_pylint(self, file_path: str) -> List[AnalysisIssue]:
        """Run pylint on a file and convert output to AnalysisIssue objects."""
        issues = []
        
        try:
            from pylint import lint
            from pylint.reporters.json import JSONReporter
            
            # Use a temporary file to store pylint JSON output
            with tempfile.NamedTemporaryFile(delete=False, mode="w+", suffix=".json") as tmp_file:
                tmp_path = tmp_file.name
            
            # Run pylint with JSON reporter
            args = [
                file_path,
                "--output-format=json",
                f"--output={tmp_path}"
            ]
            
            # Add any custom pylint args from config
            if "pylint_args" in self.config:
                args.extend(self.config["pylint_args"])
            
            # Run pylint
            lint.Run(args, exit=False)
            
            # Parse the JSON output
            with open(tmp_path, "r") as f:
                pylint_issues = json.load(f)
            
            # Clean up temp file
            os.unlink(tmp_path)
            
            # Convert pylint issues to our format
            for issue in pylint_issues:
                severity_map = {
                    "convention": IssueSeverity.INFO,
                    "refactor": IssueSeverity.INFO,
                    "warning": IssueSeverity.WARNING,
                    "error": IssueSeverity.ERROR,
                    "fatal": IssueSeverity.CRITICAL
                }
                
                category_map = {
                    "convention": IssueCategory.STYLE,
                    "refactor": IssueCategory.MAINTAINABILITY,
                    "warning": IssueCategory.WARNING if "warning" in issue["type"] else IssueCategory.MAINTAINABILITY,
                    "error": IssueCategory.ERROR,
                    "fatal": IssueCategory.ERROR
                }
                
                # Extract code snippet
                code_snippet = self._extract_code_snippet(file_path, issue["line"])
                
                issues.append(AnalysisIssue(
                    id=str(uuid.uuid4()),
                    file_path=file_path,
                    line=issue["line"],
                    column=issue["column"],
                    message=issue["message"],
                    description=f"{issue['message-id']}: {issue['message']}",
                    severity=severity_map.get(issue["type"], IssueSeverity.WARNING),
                    category=category_map.get(issue["type"], IssueCategory.MAINTAINABILITY),
                    source="pylint",
                    rule_id=issue["message-id"],
                    fixable=self._is_pylint_fixable(issue["message-id"]),
                    fix_type="simple" if self._is_pylint_fixable(issue["message-id"]) else "manual",
                    code_snippet=code_snippet
                ))
            
        except ImportError:
            self.logger.warning("pylint is not installed")
        except Exception as e:
            self.logger.error(f"Error running pylint: {str(e)}")
            self.logger.debug(traceback.format_exc())
        
        return issues
    
    def _analyze_with_mypy(self, file_path: str) -> List[AnalysisIssue]:
        """Run mypy on a file and convert output to AnalysisIssue objects."""
        issues = []
        
        try:
            from mypy import api
            
            # Run mypy
            result = api.run([file_path])
            
            # Parse the output
            if result[0]:  # stdout
                for line in result[0].splitlines():
                    # Parse mypy output format: file:line: severity: message
                    if ":" not in line:
                        continue
                    
                    parts = line.split(":", 3)
                    if len(parts) < 3:
                        continue
                    
                    f_path, line_num = parts[0], parts[1]
                    
                    # Check that this is for our file
                    if os.path.abspath(f_path) != os.path.abspath(file_path):
                        continue
                    
                    # Extract severity and message
                    if "error" in parts[2].lower():
                        severity = IssueSeverity.ERROR
                        category = IssueCategory.TYPING
                    else:
                        severity = IssueSeverity.WARNING
                        category = IssueCategory.TYPING
                    
                    message = parts[3] if len(parts) > 3 else parts[2]
                    
                    # Extract code snippet
                    code_snippet = self._extract_code_snippet(file_path, int(line_num))
                    
                    issues.append(AnalysisIssue(
                        id=str(uuid.uuid4()),
                        file_path=file_path,
                        line=int(line_num),
                        column=1,  # mypy doesn't provide column info
                        message=message.strip(),
                        description=message.strip(),
                        severity=severity,
                        category=category,
                        source="mypy",
                        rule_id="mypy-type-error",
                        fixable=False,  # Type errors generally need manual fixes
                        fix_type="manual",
                        code_snippet=code_snippet
                    ))
            
        except ImportError:
            self.logger.warning("mypy is not installed")
        except Exception as e:
            self.logger.error(f"Error running mypy: {str(e)}")
            self.logger.debug(traceback.format_exc())
        
        return issues
    
    def _analyze_with_flake8(self, file_path: str) -> List[AnalysisIssue]:
        """Run flake8 on a file and convert output to AnalysisIssue objects."""
        issues = []
        
        try:
            # We'll use subprocess to run flake8
            cmd = ["flake8", "--format=json", file_path]
            
            # Add any custom flake8 args from config
            if "flake8_args" in self.config:
                cmd.extend(self.config["flake8_args"])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False  # Don't raise an exception on flake8 errors
            )
            
            # Parse the JSON output
            if result.stdout:
                try:
                    flake8_issues = json.loads(result.stdout)
                    
                    for file_issues in flake8_issues.values():
                        for issue in file_issues:
                            # Extract code snippet
                            code_snippet = self._extract_code_snippet(file_path, issue["line_number"])
                            
                            issues.append(AnalysisIssue(
                                id=str(uuid.uuid4()),
                                file_path=file_path,
                                line=issue["line_number"],
                                column=issue["column_number"],
                                message=issue["text"],
                                description=issue["text"],
                                severity=IssueSeverity.WARNING,
                                category=IssueCategory.STYLE,
                                source="flake8",
                                rule_id=issue["code"],
                                fixable=self._is_flake8_fixable(issue["code"]),
                                fix_type="simple" if self._is_flake8_fixable(issue["code"]) else "manual",
                                code_snippet=code_snippet
                            ))
                except json.JSONDecodeError:
                    # Fallback to parsing text output
                    for line in result.stdout.splitlines():
                        parts = line.split(":", 3)
                        if len(parts) < 4:
                            continue
                        
                        f_path, line_num, col_num = parts[0], parts[1], parts[2]
                        
                        # Check that this is for our file
                        if os.path.abspath(f_path) != os.path.abspath(file_path):
                            continue
                        
                        message = parts[3].strip()
                        code_match = message.split(" ", 1)
                        rule_id = code_match[0] if len(code_match) > 1 else ""
                        
                        # Extract code snippet
                        code_snippet = self._extract_code_snippet(file_path, int(line_num))
                        
                        issues.append(AnalysisIssue(
                            id=str(uuid.uuid4()),
                            file_path=file_path,
                            line=int(line_num),
                            column=int(col_num),
                            message=message,
                            description=message,
                            severity=IssueSeverity.WARNING,
                            category=IssueCategory.STYLE,
                            source="flake8",
                            rule_id=rule_id,
                            fixable=self._is_flake8_fixable(rule_id),
                            fix_type="simple" if self._is_flake8_fixable(rule_id) else "manual",
                            code_snippet=code_snippet
                        ))
        
        except FileNotFoundError:
            self.logger.warning("flake8 is not installed or not in PATH")
        except Exception as e:
            self.logger.error(f"Error running flake8: {str(e)}")
            self.logger.debug(traceback.format_exc())
        
        return issues
    
    def _analyze_with_bandit(self, file_path: str) -> List[AnalysisIssue]:
        """Run bandit on a file and convert output to AnalysisIssue objects."""
        issues = []
        
        try:
            # Run bandit as a subprocess
            cmd = ["bandit", "-f", "json", file_path]
            
            # Add any custom bandit args from config
            if "bandit_args" in self.config:
                cmd.extend(self.config["bandit_args"])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False  # Don't raise an exception on bandit findings
            )
            
            # Parse the JSON output
            if result.stdout:
                try:
                    bandit_result = json.loads(result.stdout)
                    
                    # Extract issues
                    if "results" in bandit_result:
                        for issue in bandit_result["results"]:
                            severity_map = {
                                "LOW": IssueSeverity.INFO,
                                "MEDIUM": IssueSeverity.WARNING,
                                "HIGH": IssueSeverity.CRITICAL
                            }
                            
                            # Extract code snippet from bandit output
                            code_snippet = issue.get("code", "")
                            if not code_snippet:
                                code_snippet = self._extract_code_snippet(file_path, issue["line_number"])
                            
                            issues.append(AnalysisIssue(
                                id=str(uuid.uuid4()),
                                file_path=file_path,
                                line=issue["line_number"],
                                column=1,  # bandit doesn't provide column info
                                message=issue["issue_text"],
                                description=issue.get("more_info", issue["issue_text"]),
                                severity=severity_map.get(issue["issue_severity"], IssueSeverity.WARNING),
                                category=IssueCategory.SECURITY,
                                source="bandit",
                                rule_id=issue["test_id"],
                                fixable=False,  # Security issues generally need manual review
                                fix_type="manual",
                                code_snippet=code_snippet
                            ))
                
                except json.JSONDecodeError:
                    self.logger.warning("Failed to parse bandit JSON output")
        
        except FileNotFoundError:
            self.logger.warning("bandit is not installed or not in PATH")
        except Exception as e:
            self.logger.error(f"Error running bandit: {str(e)}")
            self.logger.debug(traceback.format_exc())
        
        return issues
    
    def _analyze_with_ast(self, file_path: str) -> List[AnalysisIssue]:
        """Use Python's built-in AST module to find issues."""
        issues = []
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
            
            # Parse the code with ast
            try:
                tree = ast.parse(code, filename=file_path)
                
                # Analyze function complexity
                issues.extend(self._check_function_complexity(file_path, tree, code))
                
                # Analyze for missing docstrings
                issues.extend(self._check_missing_docstrings(file_path, tree, code))
                
                # Check for unused variables using name binding analysis
                issues.extend(self._check_unused_variables(file_path, tree, code))
                
            except SyntaxError as e:
                # Report syntax errors
                line = e.lineno or 1
                col = e.offset or 1
                message = f"Syntax error: {e}"
                
                # Extract code snippet
                code_snippet = self._extract_code_snippet(file_path, line)
                
                issues.append(AnalysisIssue(
                    id=str(uuid.uuid4()),
                    file_path=file_path,
                    line=line,
                    column=col,
                    message=message,
                    description=message,
                    severity=IssueSeverity.ERROR,
                    category=IssueCategory.ERROR,
                    source="ast",
                    rule_id="syntax-error",
                    fixable=False,
                    fix_type="manual",
                    code_snippet=code_snippet
                ))
        
        except Exception as e:
            self.logger.error(f"Error in AST analysis: {str(e)}")
            self.logger.debug(traceback.format_exc())
        
        return issues
    
    def _check_function_complexity(self, file_path: str, tree: ast.AST, code: str) -> List[AnalysisIssue]:
        """Analyze function complexity using AST."""
        issues = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Calculate cyclomatic complexity
                complexity = 1  # Base complexity
                
                for child_node in ast.walk(node):
                    # Control flow increases complexity
                    if isinstance(child_node, (ast.If, ast.For, ast.AsyncFor, ast.While)):
                        complexity += 1
                    elif isinstance(child_node, ast.Try):
                        complexity += len(child_node.handlers)  # Each except clause
                    elif isinstance(child_node, ast.BoolOp) and isinstance(child_node.op, ast.And):
                        complexity += len(child_node.values) - 1
                    elif isinstance(child_node, ast.BoolOp) and isinstance(child_node.op, ast.Or):
                        complexity += len(child_node.values) - 1
                
                # Report if complexity is too high
                if complexity > 10:
                    # Extract code snippet - just the function definition line
                    code_lines = code.splitlines()
                    code_snippet = code_lines[node.lineno - 1] if 0 < node.lineno <= len(code_lines) else ""
                    
                    issues.append(AnalysisIssue(
                        id=str(uuid.uuid4()),
                        file_path=file_path,
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Function '{node.name}' has a cyclomatic complexity of {complexity} (too high)",
                        description=(
                            f"High cyclomatic complexity ({complexity}) in function '{node.name}'. "
                            "Consider breaking the function into smaller, more focused functions."
                        ),
                        severity=IssueSeverity.WARNING,
                        category=IssueCategory.COMPLEXITY,
                        source="ast",
                        rule_id="high-complexity",
                        fixable=False,  # Complex functions usually need manual refactoring
                        fix_type="llm-assisted",  # AI could help suggest a refactoring
                        code_snippet=code_snippet
                    ))
        
        return issues
    
    def _check_missing_docstrings(self, file_path: str, tree: ast.AST, code: str) -> List[AnalysisIssue]:
        """Check for missing docstrings in functions and classes."""
        issues = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                # Skip if it's a private function/class (starts with _)
                if node.name.startswith('_') and not node.name.startswith('__'):
                    continue
                
                # Check if there's a docstring
                docstring = ast.get_docstring(node)
                if not docstring:
                    kind = "class" if isinstance(node, ast.ClassDef) else "function"
                    
                    # Extract code snippet - just the definition line
                    code_lines = code.splitlines()
                    code_snippet = code_lines[node.lineno - 1] if 0 < node.lineno <= len(code_lines) else ""
                    
                    issues.append(AnalysisIssue(
                        id=str(uuid.uuid4()),
                        file_path=file_path,
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Missing docstring in {kind} '{node.name}'",
                        description=f"Add a docstring to document the purpose and usage of this {kind}.",
                        severity=IssueSeverity.INFO,
                        category=IssueCategory.MAINTAINABILITY,
                        source="ast",
                        rule_id="missing-docstring",
                        fixable=True,
                        fix_type="llm-assisted",  # AI can generate good docstrings
                        code_snippet=code_snippet
                    ))
        
        return issues
    
    def _check_unused_variables(self, file_path: str, tree: ast.AST, code: str) -> List[AnalysisIssue]:
        """Simple check for unused variables using AST."""
        issues = []
        
        # This is a simplified implementation. A more thorough unused variable
        # detection would require full control flow analysis.
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Find all variable assignments
                assigned_vars = {}
                used_vars = set()
                
                # Visit all assignments in the function
                for child in ast.walk(node):
                    if isinstance(child, ast.Assign):
                        for target in child.targets:
                            if isinstance(target, ast.Name):
                                assigned_vars[target.id] = target
                    
                    # Track variable usage
                    elif isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                        used_vars.add(child.id)
                
                # Find unused variables
                for var_name, var_node in assigned_vars.items():
                    # Skip if used or is a special variable (_, etc.)
                    if var_name in used_vars or var_name == '_' or var_name.startswith('__'):
                        continue
                    
                    # Extract code snippet
                    code_lines = code.splitlines()
                    code_snippet = code_lines[var_node.lineno - 1] if 0 < var_node.lineno <= len(code_lines) else ""
                    
                    issues.append(AnalysisIssue(
                        id=str(uuid.uuid4()),
                        file_path=file_path,
                        line=var_node.lineno,
                        column=var_node.col_offset,
                        message=f"Unused variable '{var_name}'",
                        description=f"Variable '{var_name}' is assigned but never used.",
                        severity=IssueSeverity.INFO,
                        category=IssueCategory.MAINTAINABILITY,
                        source="ast",
                        rule_id="unused-variable",
                        fixable=True,
                        fix_type="simple",
                        code_snippet=code_snippet
                    ))
        
        return issues
    
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
    
    def _is_pylint_fixable(self, rule_id: str) -> bool:
        """Determine if a pylint issue is fixable automatically."""
        # List of fixable pylint rule IDs
        fixable_rules = {
            "C0303",  # Trailing whitespace
            "C0304",  # Final newline missing
            "C0321",  # More than one statement on a single line
            "C0410",  # Multiple imports on one line
            "C0411",  # Wrong import order
            "W0404",  # Reimport
            "W0611",  # Unused import
            "W0612",  # Unused variable
            "W0104",  # Statement seems to have no effect
            "W0106",  # Expression is assigned to nothing
            "W1401",  # Anomalous backslash in string
            "R0903",  # Too few public methods (can add 'pass')
        }
        
        return rule_id in fixable_rules
    
    def _is_flake8_fixable(self, rule_id: str) -> bool:
        """Determine if a flake8 issue is fixable automatically."""
        # List of fixable flake8 rule IDs
        fixable_rules = {
            "E101",  # Indentation contains mixed spaces and tabs
            "E111",  # Indentation is not a multiple of four
            "E112",  # Expected an indented block
            "E113",  # Unexpected indentation
            "E114",  # Indentation is not a multiple of four (comment)
            "E115",  # Expected an indented block (comment)
            "E116",  # Unexpected indentation (comment)
            "E117",  # Over-indented
            "E121",  # Continuation line under-indented for hanging indent
            "E122",  # Continuation line missing indentation or outdented
            "E123",  # Closing bracket does not match indentation of opening bracket's line
            "E124",  # Closing bracket does not match visual indentation
            "E125",  # Continuation line with same indent as next logical line
            "E126",  # Continuation line over-indented for hanging indent
            "E127",  # Continuation line over-indented for visual indent
            "E128",  # Continuation line under-indented for visual indent
            "E129",  # Visually indented line with same indent as next logical line
            "E131",  # Continuation line unaligned for hanging indent
            "E133",  # Closing bracket is missing indentation
            "E201",  # Whitespace after '('
            "E202",  # Whitespace before ')'
            "E203",  # Whitespace before ':'
            "E211",  # Whitespace before '('
            "E221",  # Multiple spaces before operator
            "E222",  # Multiple spaces after operator
            "E223",  # Tab before operator
            "E224",  # Tab after operator
            "E225",  # Missing whitespace around operator
            "E226",  # Missing whitespace around arithmetic operator
            "E227",  # Missing whitespace around bitwise or shift operator
            "E228",  # Missing whitespace around modulo operator
            "E231",  # Missing whitespace after ','
            "E241",  # Multiple spaces after ','
            "E242",  # Tab after ','
            "E251",  # Unexpected spaces around keyword / parameter equals
            "E261",  # At least two spaces before inline comment
            "E262",  # Inline comment should start with '# '
            "E265",  # Block comment should start with '# '
            "E266",  # Too many leading '#' for block comment
            "E271",  # Multiple spaces after keyword
            "E272",  # Multiple spaces before keyword
            "E273",  # Tab after keyword
            "E274",  # Tab before keyword
            "E301",  # Expected 1 blank line, found 0
            "E302",  # Expected 2 blank lines, found 0
            "E303",  # Too many blank lines
            "E304",  # Blank lines found after function decorator
            "E401",  # Multiple imports on one line
            "E501",  # Line too long
            "E502",  # The backslash is redundant between brackets
            "E701",  # Multiple statements on one line (colon)
            "E702",  # Multiple statements on one line (semicolon)
            "E703",  # Statement ends with a semicolon
            "E711",  # Comparison to None should be 'if cond is None:'
            "E712",  # Comparison to True should be 'if cond is True:'
            "E713",  # Test for membership should be 'not in'
            "E714",  # Test for object identity should be 'is not'
            "E721",  # Do not compare types, use 'isinstance()'
            "E722",  # Do not use bare except
            "E731",  # Do not assign a lambda expression, use a def
            "E741",  # Ambiguous variable name
            "E742",  # Ambiguous class name
            "E743",  # Ambiguous function name
            "F401",  # Module imported but unused
            "F403",  # 'from module import *' used
            "F405",  # Name may be undefined, or defined from star imports
            "F811",  # Redefinition of unused name
            "F821",  # Undefined name
            "F841",  # Local variable name is assigned to but never used
            "W291",  # Trailing whitespace
            "W292",  # No newline at end of file
            "W293",  # Blank line contains whitespace
            "W391",  # Blank line at end of file
            "W503",  # Line break before binary operator
            "W504",  # Line break after binary operator
            "W505",  # Doc line too long
        }
        
        return rule_id in fixable_rules


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Example usage
    analyzer = PythonAnalyzer()
    
    # Analyze a file
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        result = analyzer.analyze_file(file_path)
        
        # Print results
        print(f"Analyzed {file_path}")
        print(f"Found {len(result.issues)} issues")
        
        for issue in result.issues:
            print(f"Line {issue.line}: {issue.source} - {issue.message}")
    else:
        print("Please provide a file path to analyze")