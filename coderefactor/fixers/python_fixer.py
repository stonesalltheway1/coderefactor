#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Python code fixer for CodeRefactor.
Implements automatic fixes for common Python code issues.
"""

import os
import re
import ast
import logging
import asyncio
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple, Set
import difflib
import textwrap

# Import the base fixer
from fixers.base import BaseFixer, FixResult, FixChange, FixType

# Import claude_api for LLM-assisted fixes if available
try:
    from claude_api import ClaudeAPI, RefactorSuggestion
    HAS_LLM = True
except ImportError:
    HAS_LLM = False


class PythonFixer(BaseFixer):
    """
    Fixer for Python code.
    Implements automatic fixes for common Python code issues.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Python fixer.
        
        Args:
            config: Optional configuration dictionary with the following keys:
                - autoformat: Whether to automatically format code (default: True)
                - formatter: Formatter to use (default: 'black')
                - fix_imports: Whether to fix imports (default: True)
                - fix_style: Whether to fix style issues (default: True)
                - fix_bugs: Whether to fix bug issues (default: True)
                - use_llm: Whether to use LLM for complex fixes (default: True if available)
                - llm_config: Configuration for LLM integration
        """
        super().__init__(config)
        
        # Extract config options
        self.autoformat = self.config.get('autoformat', True)
        self.formatter = self.config.get('formatter', 'black')
        self.fix_imports = self.config.get('fix_imports', True)
        self.fix_style = self.config.get('fix_style', True)
        self.fix_bugs = self.config.get('fix_bugs', True)
        self.use_llm = self.config.get('use_llm', HAS_LLM)
        
        # Initialize formatters
        self._has_black = self._check_black()
        self._has_autopep8 = self._check_autopep8()
        self._has_isort = self._check_isort()
        
        # Initialize LLM if configured
        self.llm = None
        if self.use_llm and HAS_LLM:
            llm_config = self.config.get('llm_config', {})
            try:
                from claude_api import ClaudeAPI, LLMConfig
                api_key = llm_config.get('api_key') or os.environ.get("ANTHROPIC_API_KEY")
                
                if api_key:
                    config = LLMConfig(
                        api_key=api_key,
                        model=llm_config.get('model', "claude-3-7-sonnet-20250219"),
                        temperature=llm_config.get('temperature', 0.3)
                    )
                    self.llm = ClaudeAPI(config)
                    self.logger.info("Initialized LLM integration for complex fixes")
                else:
                    self.logger.warning("LLM integration enabled but no API key provided")
            except Exception as e:
                self.logger.error(f"Failed to initialize LLM integration: {str(e)}")
    
    def _check_black(self) -> bool:
        """Check if black is installed."""
        try:
            import black
            self.logger.info("Found black formatter")
            return True
        except ImportError:
            try:
                subprocess.run(
                    ["black", "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False
                )
                self.logger.info("Found black formatter (command-line)")
                return True
            except (subprocess.SubprocessError, FileNotFoundError):
                self.logger.warning("black formatter not found")
                return False
    
    def _check_autopep8(self) -> bool:
        """Check if autopep8 is installed."""
        try:
            import autopep8
            self.logger.info("Found autopep8 formatter")
            return True
        except ImportError:
            try:
                subprocess.run(
                    ["autopep8", "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False
                )
                self.logger.info("Found autopep8 formatter (command-line)")
                return True
            except (subprocess.SubprocessError, FileNotFoundError):
                self.logger.warning("autopep8 formatter not found")
                return False
    
    def _check_isort(self) -> bool:
        """Check if isort is installed."""
        try:
            import isort
            self.logger.info("Found isort import formatter")
            return True
        except ImportError:
            try:
                subprocess.run(
                    ["isort", "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False
                )
                self.logger.info("Found isort import formatter (command-line)")
                return True
            except (subprocess.SubprocessError, FileNotFoundError):
                self.logger.warning("isort import formatter not found")
                return False
    
    async def fix_code(self, code: str, file_path: Optional[str] = None, 
                      issues: Optional[List[Dict[str, Any]]] = None) -> FixResult:
        """
        Fix issues in Python code.
        
        Args:
            code: The Python code to fix.
            file_path: Optional path to the file (for reference).
            issues: Optional list of issues to fix. If None, all fixable issues will be addressed.
        
        Returns:
            FixResult containing the original and fixed code, along with details of changes made.
        """
        # Initialize the result
        result = FixResult(
            file_path=file_path or "",
            original_code=code,
            fixed_code=code,
            success=False
        )
        
        # Skip if the code is empty
        if not code.strip():
            result.warnings.append("Empty code provided, nothing to fix")
            return result
        
        # Check if the code is valid Python
        try:
            ast.parse(code)
        except SyntaxError as e:
            result.error = f"Invalid Python syntax: {str(e)}"
            return result
        
        # Apply fixes in sequence
        modified_code = code
        changes = []
        
        # 1. Fix specific issues if provided
        if issues:
            issue_fixes = await self._fix_specific_issues(modified_code, issues, file_path)
            if issue_fixes:
                # Apply the changes
                for change in issue_fixes:
                    changes.append(change)
                modified_code = self.apply_changes(modified_code, issue_fixes)
        
        # 2. Fix imports if enabled
        if self.fix_imports:
            import_fixes = await self._fix_imports(modified_code, file_path)
            if import_fixes:
                # Apply the changes
                for change in import_fixes:
                    changes.append(change)
                modified_code = self.apply_changes(modified_code, import_fixes)
        
        # 3. Fix common style issues if enabled
        if self.fix_style:
            style_fixes = await self._fix_style_issues(modified_code, file_path)
            if style_fixes:
                # Apply the changes
                for change in style_fixes:
                    changes.append(change)
                modified_code = self.apply_changes(modified_code, style_fixes)
        
        # 4. Fix potential bugs if enabled
        if self.fix_bugs:
            bug_fixes = await self._fix_bug_issues(modified_code, file_path)
            if bug_fixes:
                # Apply the changes
                for change in bug_fixes:
                    changes.append(change)
                modified_code = self.apply_changes(modified_code, bug_fixes)
        
        # 5. Auto-format the code if enabled
        if self.autoformat:
            formatted_code, format_changes = await self._format_code(modified_code, file_path)
            if formatted_code != modified_code:
                # Record the formatting as a single change
                changes.extend(format_changes)
                modified_code = formatted_code
        
        # Update the result
        result.fixed_code = modified_code
        result.changes = changes
        result.success = modified_code != code or bool(changes)
        
        return result
    
    async def get_fix_suggestions(self, code: str, issue: Dict[str, Any], 
                                file_path: Optional[str] = None) -> List[FixChange]:
        """
        Get suggestions for fixing a specific issue.
        
        Args:
            code: The Python code containing the issue.
            issue: The issue to fix, with the following keys:
                - id: Issue identifier
                - line: Line number
                - column: Column number
                - message: Issue message
                - description: Issue description
                - rule_id: Rule identifier (e.g., 'W0612' for pylint)
                - severity: Issue severity
                - category: Issue category
                - fixable: Whether the issue is fixable
                - fix_type: Type of fix
            file_path: Optional path to the file (for reference).
        
        Returns:
            List of FixChange objects with suggestions.
        """
        suggestions = []
        
        # Check if the issue is fixable
        if not issue.get('fixable', False):
            return suggestions
        
        rule_id = issue.get('rule_id', '')
        message = issue.get('message', '')
        line = issue.get('line', 0)
        column = issue.get('column', 0)
        
        # Try specific fixers based on rule_id
        if rule_id.startswith('W0612'):  # Unused variable
            changes = self._fix_unused_variable(code, line, column, message)
            suggestions.extend(changes)
        
        elif rule_id.startswith('E0601'):  # Using variable before assignment
            changes = self._fix_undefined_variable(code, line, column, message)
            suggestions.extend(changes)
        
        elif rule_id.startswith('C0303'):  # Trailing whitespace
            changes = self._fix_trailing_whitespace(code, line)
            suggestions.extend(changes)
        
        elif rule_id.startswith('C0304'):  # Final newline missing
            changes = self._fix_final_newline(code)
            suggestions.extend(changes)
        
        elif rule_id.startswith('C0111') or rule_id.startswith('D100') or 'missing docstring' in message.lower():  # Missing docstring
            changes = await self._fix_missing_docstring(code, line, column, file_path)
            suggestions.extend(changes)
        
        elif rule_id.startswith('F401'):  # Unused import
            changes = self._fix_unused_import(code, line, column, message)
            suggestions.extend(changes)
        
        # If no specific fixer found, try LLM
        if not suggestions and self.llm:
            changes = await self._get_llm_suggestions(code, issue, file_path)
            suggestions.extend(changes)
        
        return suggestions
    
    async def _fix_specific_issues(self, code: str, issues: List[Dict[str, Any]], 
                                  file_path: Optional[str] = None) -> List[FixChange]:
        """
        Fix specific issues identified by the analyzer.
        
        Args:
            code: The Python code to fix.
            issues: List of issues to fix.
            file_path: Optional path to the file (for reference).
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Group issues by fixability to prioritize simple fixes first
        fixable_issues = []
        llm_issues = []
        
        for issue in issues:
            if issue.get('fixable', False):
                fix_type = issue.get('fix_type', '')
                if fix_type == 'llm-assisted':
                    llm_issues.append(issue)
                else:
                    fixable_issues.append(issue)
        
        # Process fixable issues first
        for issue in fixable_issues:
            # Get suggestions for fixing this issue
            suggestions = await self.get_fix_suggestions(code, issue, file_path)
            changes.extend(suggestions)
        
        # Then process LLM-assisted issues if LLM is available
        if self.llm and llm_issues:
            for issue in llm_issues:
                suggestions = await self.get_fix_suggestions(code, issue, file_path)
                changes.extend(suggestions)
        
        return changes
    
    async def _fix_imports(self, code: str, file_path: Optional[str] = None) -> List[FixChange]:
        """
        Fix import-related issues in the code.
        
        Args:
            code: The Python code to fix.
            file_path: Optional path to the file (for reference).
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Use isort if available
        if self._has_isort:
            try:
                # Write code to a temporary file
                with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
                    temp_path = temp_file.name
                    temp_file.write(code.encode('utf-8'))
                
                try:
                    # Import isort dynamically
                    import isort
                    
                    # Use isort programmatically
                    sorted_code = isort.code(code)
                    
                    if sorted_code != code:
                        # Create a FixChange for the whole file
                        change = FixChange(
                            description="Sort imports",
                            start_line=1,
                            start_column=1,
                            end_line=len(code.splitlines()) + 1,
                            end_column=1,
                            original_text=code,
                            replacement_text=sorted_code,
                            fix_type=FixType.SIMPLE
                        )
                        changes.append(change)
                
                except ImportError:
                    # Use isort command-line
                    result = subprocess.run(
                        ["isort", temp_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=False
                    )
                    
                    if result.returncode == 0:
                        # Read the sorted code
                        with open(temp_path, 'r', encoding='utf-8') as f:
                            sorted_code = f.read()
                        
                        if sorted_code != code:
                            # Create a FixChange for the whole file
                            change = FixChange(
                                description="Sort imports",
                                start_line=1,
                                start_column=1,
                                end_line=len(code.splitlines()) + 1,
                                end_column=1,
                                original_text=code,
                                replacement_text=sorted_code,
                                fix_type=FixType.SIMPLE
                            )
                            changes.append(change)
                
                finally:
                    # Clean up the temporary file
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
            
            except Exception as e:
                self.logger.warning(f"Error fixing imports with isort: {str(e)}")
        
        # Detect and fix unused imports
        try:
            # Use AST to detect unused imports
            unused_imports = self._detect_unused_imports(code)
            
            if unused_imports:
                # Apply fixes for unused imports
                for line, name in unused_imports:
                    # Get the line of code
                    lines = code.splitlines()
                    if 0 < line <= len(lines):
                        code_line = lines[line - 1]
                        
                        # Create a fix change
                        changes.extend(self._fix_unused_import(code, line, 1, f"Unused import: {name}"))
        
        except Exception as e:
            self.logger.warning(f"Error detecting unused imports: {str(e)}")
        
        return changes
    
    def _detect_unused_imports(self, code: str) -> List[Tuple[int, str]]:
        """
        Detect unused imports in the code.
        
        Args:
            code: The Python code to analyze.
        
        Returns:
            List of tuples (line_number, import_name) for unused imports.
        """
        unused_imports = []
        
        try:
            # Parse the code
            tree = ast.parse(code)
            
            # Track imported names and their line numbers
            imports = {}
            
            # Collect all import statements
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports[name.asname or name.name] = node.lineno
                
                elif isinstance(node, ast.ImportFrom):
                    for name in node.names:
                        if name.name == '*':
                            # Wildcard import, can't track usage
                            continue
                        imports[name.asname or name.name] = node.lineno
            
            # Collect all used names
            used_names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    used_names.add(node.id)
                elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
                    if isinstance(node.value, ast.Name):
                        # Handle module.attribute
                        used_names.add(node.value.id)
            
            # Find unused imports
            for name, line in imports.items():
                if name not in used_names:
                    unused_imports.append((line, name))
        
        except Exception as e:
            self.logger.warning(f"Error in AST analysis: {str(e)}")
        
        return unused_imports
    
    async def _fix_style_issues(self, code: str, file_path: Optional[str] = None) -> List[FixChange]:
        """
        Fix common style issues in the code.
        
        Args:
            code: The Python code to fix.
            file_path: Optional path to the file (for reference).
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Fix trailing whitespace
        lines = code.splitlines(True)  # Keep line endings
        for i, line in enumerate(lines):
            stripped = line.rstrip()
            if stripped and stripped != line.rstrip('\n') and not stripped.startswith('#'):
                # Line has trailing whitespace, create a fix
                changes.extend(self._fix_trailing_whitespace(code, i + 1))
        
        # Fix missing final newline
        if code and not code.endswith('\n'):
            changes.extend(self._fix_final_newline(code))
        
        # Fix inconsistent indentation
        changes.extend(self._fix_inconsistent_indentation(code))
        
        return changes
    
    async def _fix_bug_issues(self, code: str, file_path: Optional[str] = None) -> List[FixChange]:
        """
        Fix potential bug issues in the code.
        
        Args:
            code: The Python code to fix.
            file_path: Optional path to the file (for reference).
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Parse the code to detect bugs
        try:
            tree = ast.parse(code)
            
            # Detect common bugs using AST
            
            # 1. List/dict comprehension with unused variables
            changes.extend(self._fix_unused_comprehension_vars(code, tree))
            
            # 2. Potential infinite loops
            changes.extend(self._fix_potential_infinite_loops(code, tree))
            
            # 3. Dict lookup without .get()
            changes.extend(self._fix_dict_lookup_without_get(code, tree))
            
            # 4. Referenced before assignment
            changes.extend(self._fix_referenced_before_assignment(code, tree))
            
        except SyntaxError:
            # Don't analyze code with syntax errors
            pass
        except Exception as e:
            self.logger.warning(f"Error detecting bugs: {str(e)}")
        
        return changes
    
    async def _format_code(self, code: str, file_path: Optional[str] = None) -> Tuple[str, List[FixChange]]:
        """
        Format the Python code using the configured formatter.
        
        Args:
            code: The Python code to format.
            file_path: Optional path to the file (for reference).
        
        Returns:
            Tuple of (formatted_code, changes).
        """
        changes = []
        formatted_code = code
        
        # Use the appropriate formatter
        if self.formatter == 'black' and self._has_black:
            try:
                # Try to use black programmatically
                import black
                
                try:
                    mode = black.Mode()
                    formatted_code = black.format_str(code, mode=mode)
                    
                    if formatted_code != code:
                        # Create a change for the whole file
                        change = FixChange(
                            description="Format code with black",
                            start_line=1,
                            start_column=1,
                            end_line=len(code.splitlines()) + 1,
                            end_column=1,
                            original_text=code,
                            replacement_text=formatted_code,
                            fix_type=FixType.SIMPLE
                        )
                        changes.append(change)
                
                except Exception as e:
                    self.logger.warning(f"Error formatting with black: {str(e)}")
                    
                    # Fallback to command-line black
                    with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
                        temp_path = temp_file.name
                        temp_file.write(code.encode('utf-8'))
                    
                    try:
                        # Use black command-line
                        result = subprocess.run(
                            ["black", "-q", temp_path],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            check=False
                        )
                        
                        if result.returncode == 0:
                            # Read the formatted code
                            with open(temp_path, 'r', encoding='utf-8') as f:
                                formatted_code = f.read()
                            
                            if formatted_code != code:
                                # Create a change for the whole file
                                change = FixChange(
                                    description="Format code with black",
                                    start_line=1,
                                    start_column=1,
                                    end_line=len(code.splitlines()) + 1,
                                    end_column=1,
                                    original_text=code,
                                    replacement_text=formatted_code,
                                    fix_type=FixType.SIMPLE
                                )
                                changes.append(change)
                    
                    finally:
                        # Clean up the temporary file
                        if os.path.exists(temp_path):
                            os.unlink(temp_path)
            
            except ImportError:
                # Use black command-line
                with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
                    temp_path = temp_file.name
                    temp_file.write(code.encode('utf-8'))
                
                try:
                    # Use black command-line
                    result = subprocess.run(
                        ["black", "-q", temp_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=False
                    )
                    
                    if result.returncode == 0:
                        # Read the formatted code
                        with open(temp_path, 'r', encoding='utf-8') as f:
                            formatted_code = f.read()
                        
                        if formatted_code != code:
                            # Create a change for the whole file
                            change = FixChange(
                                description="Format code with black",
                                start_line=1,
                                start_column=1,
                                end_line=len(code.splitlines()) + 1,
                                end_column=1,
                                original_text=code,
                                replacement_text=formatted_code,
                                fix_type=FixType.SIMPLE
                            )
                            changes.append(change)
                
                finally:
                    # Clean up the temporary file
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
        
        elif self.formatter == 'autopep8' and self._has_autopep8:
            try:
                # Try to use autopep8 programmatically
                import autopep8
                
                formatted_code = autopep8.fix_code(code)
                
                if formatted_code != code:
                    # Create a change for the whole file
                    change = FixChange(
                        description="Format code with autopep8",
                        start_line=1,
                        start_column=1,
                        end_line=len(code.splitlines()) + 1,
                        end_column=1,
                        original_text=code,
                        replacement_text=formatted_code,
                        fix_type=FixType.SIMPLE
                    )
                    changes.append(change)
            
            except ImportError:
                # Use autopep8 command-line
                with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
                    temp_path = temp_file.name
                    temp_file.write(code.encode('utf-8'))
                
                try:
                    # Use autopep8 command-line
                    result = subprocess.run(
                        ["autopep8", temp_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=False
                    )
                    
                    if result.returncode == 0:
                        # Read the formatted code
                        formatted_code = result.stdout
                        
                        if formatted_code != code:
                            # Create a change for the whole file
                            change = FixChange(
                                description="Format code with autopep8",
                                start_line=1,
                                start_column=1,
                                end_line=len(code.splitlines()) + 1,
                                end_column=1,
                                original_text=code,
                                replacement_text=formatted_code,
                                fix_type=FixType.SIMPLE
                            )
                            changes.append(change)
                
                finally:
                    # Clean up the temporary file
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
        
        return formatted_code, changes
    
    def _fix_unused_variable(self, code: str, line: int, column: int, message: str) -> List[FixChange]:
        """
        Fix unused variable issue.
        
        Args:
            code: The Python code to fix.
            line: Line number of the issue.
            column: Column number of the issue.
            message: Issue message.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        try:
            # Extract the variable name from the message
            var_name_match = re.search(r'Unused variable [\'"]?([a-zA-Z0-9_]+)[\'"]?', message)
            if not var_name_match:
                return changes
            
            var_name = var_name_match.group(1)
            
            # Get the line of code
            lines = code.splitlines()
            if 0 < line <= len(lines):
                code_line = lines[line - 1]
                
                # Check if it's an assignment
                assignment_match = re.search(fr'(\s*)({var_name})\s*=', code_line)
                if assignment_match:
                    indent = assignment_match.group(1)
                    
                    # Two options: comment out the line or use _ as variable name
                    comment_fix = FixChange(
                        description=f"Comment out unused variable '{var_name}'",
                        start_line=line,
                        start_column=1,
                        end_line=line,
                        end_column=len(code_line) + 1,
                        original_text=code_line,
                        replacement_text=f"{indent}# {code_line.lstrip()}  # Unused",
                        fix_type=FixType.SIMPLE,
                        confidence=0.8
                    )
                    changes.append(comment_fix)
                    
                    # Use _ as variable name
                    underscore_fix = FixChange(
                        description=f"Rename unused variable '{var_name}' to '_'",
                        start_line=line,
                        start_column=assignment_match.start(2) + 1,
                        end_line=line,
                        end_column=assignment_match.end(2) + 1,
                        original_text=var_name,
                        replacement_text="_",
                        fix_type=FixType.SIMPLE,
                        confidence=0.9
                    )
                    changes.append(underscore_fix)
        
        except Exception as e:
            self.logger.warning(f"Error fixing unused variable: {str(e)}")
        
        return changes
    
    def _fix_unused_import(self, code: str, line: int, column: int, message: str) -> List[FixChange]:
        """
        Fix unused import issue.
        
        Args:
            code: The Python code to fix.
            line: Line number of the issue.
            column: Column number of the issue.
            message: Issue message.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        try:
            # Extract the import name from the message
            import_name_match = re.search(r'Unused import[:]?\s*([a-zA-Z0-9_.]+)', message)
            if not import_name_match:
                return changes
            
            import_name = import_name_match.group(1)
            
            # Get the line of code
            lines = code.splitlines()
            if 0 < line <= len(lines):
                code_line = lines[line - 1]
                
                # Check if it's an import statement
                if 'import' in code_line:
                    # Two options: comment out the line or remove the import
                    
                    # Comment out the line
                    comment_fix = FixChange(
                        description=f"Comment out unused import '{import_name}'",
                        start_line=line,
                        start_column=1,
                        end_line=line,
                        end_column=len(code_line) + 1,
                        original_text=code_line,
                        replacement_text=f"# {code_line}  # Unused import",
                        fix_type=FixType.SIMPLE,
                        confidence=0.8
                    )
                    changes.append(comment_fix)
                    
                    # Remove the import
                    # Check if it's a "from x import y" statement
                    from_import_match = re.search(r'from\s+([a-zA-Z0-9_.]+)\s+import\s+(.+)', code_line)
                    if from_import_match:
                        module = from_import_match.group(1)
                        imports = from_import_match.group(2)
                        
                        # Parse the imports
                        import_items = []
                        for item in imports.split(','):
                            item = item.strip()
                            if item.startswith(import_name + ' ') or item == import_name:
                                continue
                            import_items.append(item)
                        
                        if import_items:
                            # Recreate the import statement without the unused import
                            new_line = f"from {module} import {', '.join(import_items)}"
                            
                            remove_fix = FixChange(
                                description=f"Remove unused import '{import_name}'",
                                start_line=line,
                                start_column=1,
                                end_line=line,
                                end_column=len(code_line) + 1,
                                original_text=code_line,
                                replacement_text=new_line,
                                fix_type=FixType.SIMPLE,
                                confidence=0.9
                            )
                            changes.append(remove_fix)
                        else:
                            # All imports from this module are unused, remove the line
                            remove_fix = FixChange(
                                description=f"Remove unused import '{import_name}'",
                                start_line=line,
                                start_column=1,
                                end_line=line,
                                end_column=len(code_line) + 1,
                                original_text=code_line,
                                replacement_text="",  # Remove the line
                                fix_type=FixType.SIMPLE,
                                confidence=0.9
                            )
                            changes.append(remove_fix)
                    else:
                        # Check if it's a "import x, y, z" statement
                        import_match = re.search(r'import\s+(.+)', code_line)
                        if import_match:
                            imports = import_match.group(1)
                            
                            # Parse the imports
                            import_items = []
                            for item in imports.split(','):
                                item = item.strip()
                                if item.startswith(import_name + ' ') or item == import_name:
                                    continue
                                import_items.append(item)
                            
                            if import_items:
                                # Recreate the import statement without the unused import
                                new_line = f"import {', '.join(import_items)}"
                                
                                remove_fix = FixChange(
                                    description=f"Remove unused import '{import_name}'",
                                    start_line=line,
                                    start_column=1,
                                    end_line=line,
                                    end_column=len(code_line) + 1,
                                    original_text=code_line,
                                    replacement_text=new_line,
                                    fix_type=FixType.SIMPLE,
                                    confidence=0.9
                                )
                                changes.append(remove_fix)
                            else:
                                # All imports are unused, remove the line
                                remove_fix = FixChange(
                                    description=f"Remove unused import '{import_name}'",
                                    start_line=line,
                                    start_column=1,
                                    end_line=line,
                                    end_column=len(code_line) + 1,
                                    original_text=code_line,
                                    replacement_text="",  # Remove the line
                                    fix_type=FixType.SIMPLE,
                                    confidence=0.9
                                )
                                changes.append(remove_fix)
        
        except Exception as e:
            self.logger.warning(f"Error fixing unused import: {str(e)}")
        
        return changes
    
    def _fix_undefined_variable(self, code: str, line: int, column: int, message: str) -> List[FixChange]:
        """
        Fix undefined variable issue.
        
        Args:
            code: The Python code to fix.
            line: Line number of the issue.
            column: Column number of the issue.
            message: Issue message.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        try:
            # Extract the variable name from the message
            var_name_match = re.search(r'Undefined variable [\'"]?([a-zA-Z0-9_]+)[\'"]?', message)
            if not var_name_match:
                var_name_match = re.search(r'Variable [\'"]?([a-zA-Z0-9_]+)[\'"]? is not defined', message)
            
            if not var_name_match:
                return changes
            
            var_name = var_name_match.group(1)
            
            # Get the line of code
            lines = code.splitlines()
            if 0 < line <= len(lines):
                code_line = lines[line - 1]
                
                # Check if the variable appears in the line
                var_match = re.search(fr'(\b{var_name}\b)', code_line)
                if var_match:
                    # Initialize the variable
                    indent_match = re.match(r'^(\s*)', code_line)
                    indent = indent_match.group(1) if indent_match else ""
                    
                    init_fix = FixChange(
                        description=f"Initialize undefined variable '{var_name}'",
                        start_line=line,
                        start_column=1,
                        end_line=line,
                        end_column=1,
                        original_text="",
                        replacement_text=f"{indent}{var_name} = None  # TODO: Initialize with appropriate value\n",
                        fix_type=FixType.COMPLEX,
                        confidence=0.7
                    )
                    changes.append(init_fix)
        
        except Exception as e:
            self.logger.warning(f"Error fixing undefined variable: {str(e)}")
        
        return changes
    
    def _fix_trailing_whitespace(self, code: str, line: int) -> List[FixChange]:
        """
        Fix trailing whitespace issue.
        
        Args:
            code: The Python code to fix.
            line: Line number of the issue.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        try:
            # Get the line of code
            lines = code.splitlines(True)  # Keep line endings
            if 0 < line <= len(lines):
                code_line = lines[line - 1]
                stripped_line = code_line.rstrip('\r\n')
                
                if stripped_line and stripped_line.rstrip() != stripped_line:
                    # Line has trailing whitespace
                    fixed_line = stripped_line.rstrip()
                    if code_line.endswith('\r\n'):
                        fixed_line += '\r\n'
                    elif code_line.endswith('\n'):
                        fixed_line += '\n'
                    
                    change = FixChange(
                        description="Remove trailing whitespace",
                        start_line=line,
                        start_column=1,
                        end_line=line,
                        end_column=len(code_line) + 1,
                        original_text=code_line,
                        replacement_text=fixed_line,
                        fix_type=FixType.SIMPLE
                    )
                    changes.append(change)
        
        except Exception as e:
            self.logger.warning(f"Error fixing trailing whitespace: {str(e)}")
        
        return changes
    
    def _fix_final_newline(self, code: str) -> List[FixChange]:
        """
        Fix missing final newline issue.
        
        Args:
            code: The Python code to fix.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        if code and not code.endswith('\n'):
            change = FixChange(
                description="Add missing final newline",
                start_line=len(code.splitlines()) + 1,
                start_column=1,
                end_line=len(code.splitlines()) + 1,
                end_column=1,
                original_text="",
                replacement_text="\n",
                fix_type=FixType.SIMPLE
            )
            changes.append(change)
        
        return changes
    
    def _fix_inconsistent_indentation(self, code: str) -> List[FixChange]:
        """
        Fix inconsistent indentation issues.
        
        Args:
            code: The Python code to fix.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        try:
            # Analyze the indentation styles in the code
            lines = code.splitlines()
            indentation_types = {'spaces': 0, 'tabs': 0}
            most_common_spaces = 0
            space_counts = {}
            
            for line in lines:
                # Skip empty lines and comments
                if not line.strip() or line.strip().startswith('#'):
                    continue
                
                # Count leading spaces and tabs
                indent_match = re.match(r'^(\s*)', line)
                if indent_match:
                    indent = indent_match.group(1)
                    tabs = indent.count('\t')
                    spaces = len(indent) - tabs
                    
                    if tabs > 0:
                        indentation_types['tabs'] += 1
                    elif spaces > 0:
                        indentation_types['spaces'] += 1
                        space_counts[spaces] = space_counts.get(spaces, 0) + 1
            
            # Determine the most common indentation
            if indentation_types['spaces'] > indentation_types['tabs']:
                # Spaces are more common, find the most common space count
                if space_counts:
                    most_common_spaces = max(space_counts.items(), key=lambda x: x[1])[0]
                    
                    # Check for tabs and convert them to spaces
                    for i, line in enumerate(lines):
                        if '\t' in line:
                            # Replace tabs with spaces
                            fixed_line = line.replace('\t', ' ' * most_common_spaces)
                            
                            change = FixChange(
                                description="Convert tabs to spaces",
                                start_line=i + 1,
                                start_column=1,
                                end_line=i + 1,
                                end_column=len(line) + 1,
                                original_text=line,
                                replacement_text=fixed_line,
                                fix_type=FixType.SIMPLE
                            )
                            changes.append(change)
            
            elif indentation_types['tabs'] > indentation_types['spaces']:
                # Tabs are more common, convert spaces to tabs
                for i, line in enumerate(lines):
                    indent_match = re.match(r'^( +)', line)
                    if indent_match:
                        spaces = indent_match.group(1)
                        if len(spaces) % 4 == 0:  # Assume 4 spaces per tab
                            # Replace leading spaces with tabs
                            tabs = '\t' * (len(spaces) // 4)
                            fixed_line = line.replace(spaces, tabs, 1)
                            
                            change = FixChange(
                                description="Convert spaces to tabs",
                                start_line=i + 1,
                                start_column=1,
                                end_line=i + 1,
                                end_column=len(line) + 1,
                                original_text=line,
                                replacement_text=fixed_line,
                                fix_type=FixType.SIMPLE
                            )
                            changes.append(change)
        
        except Exception as e:
            self.logger.warning(f"Error fixing inconsistent indentation: {str(e)}")
        
        return changes
    
    def _fix_unused_comprehension_vars(self, code: str, tree: ast.AST) -> List[FixChange]:
        """
        Fix unused variables in comprehensions.
        
        Args:
            code: The Python code to fix.
            tree: The AST tree.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        try:
            for node in ast.walk(tree):
                if isinstance(node, (ast.ListComp, ast.DictComp, ast.SetComp)):
                    # Check if any comprehension variables are unused
                    for i, comp in enumerate(node.generators):
                        # Skip if not a simple target name
                        if not isinstance(comp.target, ast.Name):
                            continue
                        
                        # Check if the variable is used in the result
                        var_name = comp.target.id
                        result_vars = set()
                        
                        # Collect variable names used in the result
                        if isinstance(node, ast.ListComp):
                            for n in ast.walk(node.elt):
                                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                                    result_vars.add(n.id)
                        elif isinstance(node, ast.SetComp):
                            for n in ast.walk(node.elt):
                                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                                    result_vars.add(n.id)
                        elif isinstance(node, ast.DictComp):
                            for n in ast.walk(node.key):
                                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                                    result_vars.add(n.id)
                            for n in ast.walk(node.value):
                                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                                    result_vars.add(n.id)
                        
                        # If the variable is not used in the result, rename it to _
                        if var_name not in result_vars:
                            # Get the source code for the node
                            lines = code.splitlines()
                            if node.lineno <= len(lines):
                                # Location of the variable name
                                start_line = node.lineno
                                
                                # Find all occurrences of the variable name in the line
                                line = lines[start_line - 1]
                                for match in re.finditer(fr'\b{var_name}\b', line):
                                    # Verify this is the target of a comprehension
                                    if 'for' in line[:match.start()]:
                                        change = FixChange(
                                            description=f"Rename unused comprehension variable '{var_name}' to '_'",
                                            start_line=start_line,
                                            start_column=match.start() + 1,
                                            end_line=start_line,
                                            end_column=match.end() + 1,
                                            original_text=var_name,
                                            replacement_text="_",
                                            fix_type=FixType.SIMPLE
                                        )
                                        changes.append(change)
                                        break
        
        except Exception as e:
            self.logger.warning(f"Error fixing unused comprehension variables: {str(e)}")
        
        return changes
    
    def _fix_potential_infinite_loops(self, code: str, tree: ast.AST) -> List[FixChange]:
        """
        Detect and fix potential infinite loops.
        
        Args:
            code: The Python code to fix.
            tree: The AST tree.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        try:
            # Look for potentially infinite while loops
            for node in ast.walk(tree):
                if isinstance(node, ast.While):
                    # Check if the loop has no break statement
                    has_break = any(
                        isinstance(n, ast.Break)
                        for n in ast.walk(node)
                    )
                    
                    # Check if the condition is a constant
                    is_constant_true = (
                        isinstance(node.test, ast.Constant) and 
                        node.test.value is True
                    ) or (
                        isinstance(node.test, ast.Name) and 
                        node.test.id == 'True'
                    )
                    
                    if is_constant_true and not has_break:
                        # This is a potential infinite loop
                        lines = code.splitlines()
                        if node.lineno <= len(lines):
                            line = lines[node.lineno - 1]
                            
                            # Find the while statement
                            match = re.search(r'(\s*while\s+)(True|true)(\s*:)', line, re.IGNORECASE)
                            if match:
                                # Get the indentation
                                indent = match.group(1)
                                
                                # Add a warning comment
                                change = FixChange(
                                    description="Add warning for potential infinite loop",
                                    start_line=node.lineno,
                                    start_column=1,
                                    end_line=node.lineno,
                                    end_column=len(line) + 1,
                                    original_text=line,
                                    replacement_text=f"{line}  # WARNING: Potential infinite loop",
                                    fix_type=FixType.SIMPLE
                                )
                                changes.append(change)
                                
                                # Suggest adding a break condition
                                body_indentation = indent + "    "
                                body_start_line = node.lineno + 1
                                
                                # Find where to insert the break
                                last_body_line = 0
                                for child in ast.iter_child_nodes(node):
                                    if hasattr(child, 'lineno'):
                                        last_body_line = max(last_body_line, child.lineno)
                                
                                if last_body_line > 0 and last_body_line <= len(lines):
                                    change = FixChange(
                                        description="Add break condition to prevent infinite loop",
                                        start_line=last_body_line + 1,
                                        start_column=1,
                                        end_line=last_body_line + 1,
                                        end_column=1,
                                        original_text="",
                                        replacement_text=f"{body_indentation}# TODO: Add a condition to break out of the loop\n{body_indentation}if condition:  # Replace with actual condition\n{body_indentation}    break\n",
                                        fix_type=FixType.COMPLEX,
                                        confidence=0.7
                                    )
                                    changes.append(change)
        
        except Exception as e:
            self.logger.warning(f"Error fixing potential infinite loops: {str(e)}")
        
        return changes
    
    def _fix_dict_lookup_without_get(self, code: str, tree: ast.AST) -> List[FixChange]:
        """
        Fix dictionary lookups without using .get().
        
        Args:
            code: The Python code to fix.
            tree: The AST tree.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        try:
            # Look for dictionary subscripts that might raise KeyError
            for node in ast.walk(tree):
                if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load):
                    # Check if this is inside a try-except block
                    in_try_except = False
                    parent = node
                    while parent:
                        if hasattr(parent, 'parent'):
                            parent = parent.parent
                            if isinstance(parent, ast.Try):
                                in_try_except = True
                                break
                        else:
                            break
                    
                    if not in_try_except:
                        # This might be a risky dict lookup
                        lines = code.splitlines()
                        if node.lineno <= len(lines):
                            line = lines[node.lineno - 1]
                            
                            # Try to identify the dictionary name and key
                            if isinstance(node.value, ast.Name) and isinstance(node.slice, ast.Constant):
                                dict_name = node.value.id
                                key = repr(node.slice.value)
                                
                                # Find the subscript in the line
                                subscript_pattern = fr'{dict_name}\s*\[\s*{key}\s*\]'
                                for match in re.finditer(subscript_pattern, line):
                                    # Suggest using .get() instead
                                    change = FixChange(
                                        description=f"Use .get() for safer dictionary lookup",
                                        start_line=node.lineno,
                                        start_column=match.start() + 1,
                                        end_line=node.lineno,
                                        end_column=match.end() + 1,
                                        original_text=match.group(),
                                        replacement_text=f"{dict_name}.get({key}, None)",  # Default to None
                                        fix_type=FixType.SIMPLE,
                                        confidence=0.8
                                    )
                                    changes.append(change)
                                    break
        
        except Exception as e:
            self.logger.warning(f"Error fixing dict lookups: {str(e)}")
        
        return changes
    
    def _fix_referenced_before_assignment(self, code: str, tree: ast.AST) -> List[FixChange]:
        """
        Fix variables that might be referenced before assignment.
        
        Args:
            code: The Python code to fix.
            tree: The AST tree.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        try:
            # Track variable definitions and usage within functions
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Track variables defined in the function
                    defined_vars = set()
                    referenced_vars = set()
                    
                    # Process function body in order
                    for stmt in node.body:
                        # Check for variable definitions
                        for sub_node in ast.walk(stmt):
                            if isinstance(sub_node, ast.Name):
                                if isinstance(sub_node.ctx, ast.Store):
                                    defined_vars.add(sub_node.id)
                                elif isinstance(sub_node.ctx, ast.Load):
                                    if (sub_node.id not in defined_vars and 
                                        sub_node.id not in dir(__builtins__) and
                                        sub_node.id != 'self'):
                                        referenced_vars.add(sub_node.id)
                    
                    # Suggest initializing potentially undefined variables
                    for var in referenced_vars:
                        # Find the first reference to the variable
                        first_ref_line = 0
                        first_ref_col = 0
                        
                        for stmt in ast.walk(node):
                            if hasattr(stmt, 'lineno') and isinstance(stmt, ast.Name) and stmt.id == var:
                                if first_ref_line == 0 or stmt.lineno < first_ref_line:
                                    first_ref_line = stmt.lineno
                                    first_ref_col = getattr(stmt, 'col_offset', 0)
                        
                        if first_ref_line > 0:
                            lines = code.splitlines()
                            if first_ref_line <= len(lines):
                                line = lines[first_ref_line - 1]
                                
                                # Get the indentation level
                                indent_match = re.match(r'^(\s*)', line)
                                indent = indent_match.group(1) if indent_match else ""
                                
                                # Suggest initializing the variable
                                change = FixChange(
                                    description=f"Initialize variable '{var}' before use",
                                    start_line=first_ref_line,
                                    start_column=1,
                                    end_line=first_ref_line,
                                    end_column=1,
                                    original_text="",
                                    replacement_text=f"{indent}{var} = None  # TODO: Initialize with appropriate value\n",
                                    fix_type=FixType.COMPLEX,
                                    confidence=0.7
                                )
                                changes.append(change)
        
        except Exception as e:
            self.logger.warning(f"Error fixing referenced before assignment: {str(e)}")
        
        return changes
    
    async def _fix_missing_docstring(self, code: str, line: int, column: int, file_path: Optional[str] = None) -> List[FixChange]:
        """
        Fix missing docstring issue.
        
        Args:
            code: The Python code to fix.
            line: Line number of the issue.
            column: Column number of the issue.
            file_path: Optional path to the file (for reference).
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        try:
            # Parse the code
            tree = ast.parse(code)
            
            # Find the node that needs a docstring
            node_with_missing_docstring = None
            for node in ast.walk(tree):
                if hasattr(node, 'lineno') and node.lineno == line:
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
                        node_with_missing_docstring = node
                        break
            
            if not node_with_missing_docstring:
                # Try to infer from the line number
                lines = code.splitlines()
                if 0 < line <= len(lines):
                    line_text = lines[line - 1]
                    
                    # Check if it's a function/class definition
                    func_match = re.match(r'\s*def\s+([a-zA-Z0-9_]+)\s*\(', line_text)
                    class_match = re.match(r'\s*class\s+([a-zA-Z0-9_]+)', line_text)
                    
                    if func_match:
                        # It's a function definition
                        func_name = func_match.group(1)
                        
                        # Find the function node
                        for node in ast.walk(tree):
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
                                node_with_missing_docstring = node
                                break
                    
                    elif class_match:
                        # It's a class definition
                        class_name = class_match.group(1)
                        
                        # Find the class node
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef) and node.name == class_name:
                                node_with_missing_docstring = node
                                break
            
            if node_with_missing_docstring:
                if isinstance(node_with_missing_docstring, ast.Module):
                    # It's the module docstring
                    docstring = await self._generate_docstring(code, "module", file_path)
                    
                    # Insert at the beginning of the file
                    change = FixChange(
                        description="Add module docstring",
                        start_line=1,
                        start_column=1,
                        end_line=1,
                        end_column=1,
                        original_text="",
                        replacement_text=f'"""{docstring}"""\n\n',
                        fix_type=FixType.LLM
                    )
                    changes.append(change)
                
                elif isinstance(node_with_missing_docstring, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # It's a function docstring
                    func_name = node_with_missing_docstring.name
                    
                    # Generate a docstring for the function
                    docstring = await self._generate_docstring(code, "function", file_path, node_with_missing_docstring)
                    
                    # Get the function body
                    lines = code.splitlines()
                    func_def_line = node_with_missing_docstring.lineno
                    
                    if 0 < func_def_line <= len(lines):
                        # Find the colon at the end of the function definition
                        func_def = lines[func_def_line - 1]
                        colon_pos = func_def.find(':')
                        
                        if colon_pos >= 0:
                            # Get the indentation for the function body
                            body_line = func_def_line
                            indent = ""
                            
                            # Find the indentation of the first line in the function body
                            while body_line <= len(lines):
                                body_text = lines[body_line - 1]
                                
                                if body_text.strip():
                                    indent_match = re.match(r'^(\s+)', body_text)
                                    if indent_match:
                                        indent = indent_match.group(1)
                                    break
                                
                                body_line += 1
                            
                            # Format the docstring with the correct indentation
                            indented_docstring = textwrap.indent(docstring, indent + "    ")
                            
                            # Insert after the function definition
                            change = FixChange(
                                description=f"Add docstring to function '{func_name}'",
                                start_line=func_def_line,
                                start_column=len(func_def) + 1,
                                end_line=func_def_line,
                                end_column=len(func_def) + 1,
                                original_text="",
                                replacement_text=f"\n{indent}    \"\"\"{indented_docstring}\n{indent}    \"\"\"",
                                fix_type=FixType.LLM
                            )
                            changes.append(change)
                
                elif isinstance(node_with_missing_docstring, ast.ClassDef):
                    # It's a class docstring
                    class_name = node_with_missing_docstring.name
                    
                    # Generate a docstring for the class
                    docstring = await self._generate_docstring(code, "class", file_path, node_with_missing_docstring)
                    
                    # Get the class body
                    lines = code.splitlines()
                    class_def_line = node_with_missing_docstring.lineno
                    
                    if 0 < class_def_line <= len(lines):
                        # Find the colon at the end of the class definition
                        class_def = lines[class_def_line - 1]
                        colon_pos = class_def.find(':')
                        
                        if colon_pos >= 0:
                            # Get the indentation for the class body
                            body_line = class_def_line
                            indent = ""
                            
                            # Find the indentation of the first line in the class body
                            while body_line <= len(lines):
                                body_text = lines[body_line - 1]
                                
                                if body_text.strip():
                                    indent_match = re.match(r'^(\s+)', body_text)
                                    if indent_match:
                                        indent = indent_match.group(1)
                                    break
                                
                                body_line += 1
                            
                            # Format the docstring with the correct indentation
                            indented_docstring = textwrap.indent(docstring, indent + "    ")
                            
                            # Insert after the class definition
                            change = FixChange(
                                description=f"Add docstring to class '{class_name}'",
                                start_line=class_def_line,
                                start_column=len(class_def) + 1,
                                end_line=class_def_line,
                                end_column=len(class_def) + 1,
                                original_text="",
                                replacement_text=f"\n{indent}    \"\"\"{indented_docstring}\n{indent}    \"\"\"",
                                fix_type=FixType.LLM
                            )
                            changes.append(change)
        
        except Exception as e:
            self.logger.warning(f"Error fixing missing docstring: {str(e)}")
        
        return changes
    
    async def _generate_docstring(self, code: str, node_type: str, file_path: Optional[str] = None, 
                                 node: Optional[ast.AST] = None) -> str:
        """
        Generate a docstring for a module, function, or class.
        
        Args:
            code: The Python code.
            node_type: The type of node ('module', 'function', or 'class').
            file_path: Optional path to the file (for reference).
            node: Optional AST node to generate docstring for.
        
        Returns:
            The generated docstring.
        """
        if self.llm:
            try:
                # Extract the relevant code
                if node and hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                    # Extract the code for this node
                    lines = code.splitlines()
                    start_line = node.lineno - 1
                    end_line = getattr(node, 'end_lineno', len(lines)) - 1
                    node_code = '\n'.join(lines[start_line:end_line + 1])
                else:
                    node_code = code
                
                # Use LLM to generate a docstring
                prompt = f"""Generate a concise and informative docstring for this Python {node_type}:

```python
{node_code}
```

The docstring should follow Google-style format and include:
- A brief description of the {node_type}'s purpose
- Parameters (if a function)
- Returns/yields (if a function that returns/yields values)
- Raises (if a function that raises exceptions)
- Attributes (if a class)

Return only the docstring content without the triple quotes. Keep it concise but informative.
"""
                
                # Call the LLM to generate the docstring
                from claude_api import ClaudeAPI, RefactorSuggestion
                result = await self.llm.explain_code(prompt, "python")
                
                # Clean up the response
                docstring = result.strip()
                
                # Remove any markdown code block formatting
                docstring = re.sub(r'^```python\s*', '', docstring)
                docstring = re.sub(r'^```\s*', '', docstring)
                docstring = re.sub(r'\s*```$', '', docstring)
                
                # Remove any triple quotes
                docstring = docstring.replace('"""', '')
                
                return docstring
                
            except Exception as e:
                self.logger.warning(f"Error generating docstring with LLM: {str(e)}")
        
        # Fallback docstring if LLM is not available or fails
        if node_type == "module":
            return "Module docstring.\n\nDescription of the module's purpose and functionality."
        elif node_type == "function":
            func_name = node.name if node and hasattr(node, 'name') else "function"
            return f"{func_name} function.\n\nDescription of what the function does."
        elif node_type == "class":
            class_name = node.name if node and hasattr(node, 'name') else "class"
            return f"{class_name} class.\n\nDescription of what the class represents."
        else:
            return "Docstring.\n\nDescription of this code element."
    
    async def _get_llm_suggestions(self, code: str, issue: Dict[str, Any], file_path: Optional[str] = None) -> List[FixChange]:
        """
        Get suggestions for fixing an issue using LLM.
        
        Args:
            code: The Python code containing the issue.
            issue: The issue to fix.
            file_path: Optional path to the file (for reference).
        
        Returns:
            List of FixChange objects with suggestions.
        """
        changes = []
        
        if not self.llm:
            return changes
        
        try:
            # Extract issue details
            issue_id = issue.get('id', '')
            rule_id = issue.get('rule_id', '')
            message = issue.get('message', '')
            description = issue.get('description', '')
            line = issue.get('line', 0)
            
            # Extract the relevant code
            lines = code.splitlines()
            
            # Get context lines around the issue
            start_line = max(0, line - 5)
            end_line = min(len(lines), line + 5)
            
            context_code = '\n'.join(lines[start_line:end_line])
            
            # Construct the prompt for the LLM
            prompt = f"""I have a Python code issue to fix. Here's the issue:

- Rule ID: {rule_id}
- Message: {message}
- Description: {description}
- Line number: {line}

Here's the relevant code (line {line} is where the issue is):

```python
{context_code}
```

Please suggest a fix for this issue. Your response should include:
1. A brief explanation of the issue
2. The fixed code snippet
3. Explanation of the changes made

Return your response in JSON format:
```json
{{
  "explanation": "Brief explanation of the issue and fix",
  "original_code": "The problematic code snippet",
  "fixed_code": "The fixed code snippet"
}}
```
"""
            
            # Call the LLM to get a suggested fix
            from claude_api import ClaudeAPI, RefactorSuggestion
            suggestion = await self.llm.suggest_refactoring(code, "python", prompt)
            
            if suggestion.original_code and suggestion.refactored_code and suggestion.original_code != suggestion.refactored_code:
                # Create a fix change
                change = FixChange(
                    description=f"Fix issue: {message}",
                    start_line=line,
                    start_column=1,
                    end_line=line,
                    end_column=len(lines[line - 1]) + 1 if 0 < line <= len(lines) else 1,
                    original_text=suggestion.original_code,
                    replacement_text=suggestion.refactored_code,
                    fix_type=FixType.LLM,
                    confidence=suggestion.confidence
                )
                changes.append(change)
        
        except Exception as e:
            self.logger.warning(f"Error getting LLM suggestions: {str(e)}")
        
        return changes


if __name__ == "__main__":
    # Simple test for the Python fixer
    import asyncio
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    async def main():
        # Create the Python fixer
        fixer = PythonFixer()
        
        # Test code with various issues
        test_code = """import os
import sys
import re  # Unused import

def example_function(x, y):
    # Unused variable
    z = x + y
    
    # Missing return statement
    return x * y

class ExampleClass:
    def __init__(self, value):
        self.value = value
    
    def process(self, data):
        # Dict lookup without .get()
        result = data['key']
        
        # Potential infinite loop
        while True:
            print("Processing...")
            
            if self.value > 10:
                break
        
        return result
"""
        
        # Fix the code
        result = await fixer.fix_code(test_code)
        
        # Display the result
        print("Original code:")
        print(result.original_code)
        print("\nFixed code:")
        print(result.fixed_code)
        print("\nChanges:")
        for change in result.changes:
            print(f"- {change.description}: Line {change.start_line}, Col {change.start_column}")
        
        # Preview the changes
        print("\nDiff:")
        fixer.preview_changes(result.original_code, result.fixed_code)
    
    # Run the test
    asyncio.run(main())