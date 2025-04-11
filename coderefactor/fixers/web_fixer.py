#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Web Technologies fixer for CodeRefactor.
Implements automatic fixes for HTML, CSS, JavaScript, and TypeScript code issues.
"""

import os
import re
import json
import logging
import asyncio
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple, Set
import difflib

# Import the base fixer
from fixers.base import BaseFixer, FixResult, FixChange, FixType

# Import claude_api for LLM-assisted fixes if available
try:
    from claude_api import ClaudeAPI, RefactorSuggestion
    HAS_LLM = True
except ImportError:
    HAS_LLM = False


class WebFixer(BaseFixer):
    """
    Fixer for web technologies (HTML, CSS, JavaScript, TypeScript).
    Implements automatic fixes for common web code issues.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Web fixer.
        
        Args:
            config: Optional configuration dictionary with the following keys:
                - autoformat: Whether to automatically format code (default: True)
                - html_formatter: Formatter to use for HTML (default: 'prettier')
                - css_formatter: Formatter to use for CSS (default: 'prettier')
                - js_formatter: Formatter to use for JavaScript/TypeScript (default: 'prettier')
                - fix_structure: Whether to fix structural issues (default: True)
                - fix_style: Whether to fix style issues (default: True)
                - fix_bugs: Whether to fix bug issues (default: True)
                - use_llm: Whether to use LLM for complex fixes (default: True if available)
                - llm_config: Configuration for LLM integration
        """
        super().__init__(config)
        
        # Extract config options
        self.autoformat = self.config.get('autoformat', True)
        self.html_formatter = self.config.get('html_formatter', 'prettier')
        self.css_formatter = self.config.get('css_formatter', 'prettier')
        self.js_formatter = self.config.get('js_formatter', 'prettier')
        self.fix_structure = self.config.get('fix_structure', True)
        self.fix_style = self.config.get('fix_style', True)
        self.fix_bugs = self.config.get('fix_bugs', True)
        self.use_llm = self.config.get('use_llm', HAS_LLM)
        
        # Initialize formatters
        self._has_prettier = self._check_prettier()
        self._has_eslint = self._check_eslint()
        self._has_stylelint = self._check_stylelint()
        self._has_htmlhint = self._check_htmlhint()
        
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
    
    def _check_prettier(self) -> bool:
        """Check if prettier is installed."""
        try:
            result = subprocess.run(
                ["npx", "prettier", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            if result.returncode == 0:
                self.logger.info("Found prettier formatter")
                return True
            else:
                self.logger.warning("prettier formatter not found")
                return False
        except (subprocess.SubprocessError, FileNotFoundError):
            self.logger.warning("prettier formatter not found")
            return False
    
    def _check_eslint(self) -> bool:
        """Check if eslint is installed."""
        try:
            result = subprocess.run(
                ["npx", "eslint", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            if result.returncode == 0:
                self.logger.info("Found eslint formatter")
                return True
            else:
                self.logger.warning("eslint formatter not found")
                return False
        except (subprocess.SubprocessError, FileNotFoundError):
            self.logger.warning("eslint formatter not found")
            return False
    
    def _check_stylelint(self) -> bool:
        """Check if stylelint is installed."""
        try:
            result = subprocess.run(
                ["npx", "stylelint", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            if result.returncode == 0:
                self.logger.info("Found stylelint formatter")
                return True
            else:
                self.logger.warning("stylelint formatter not found")
                return False
        except (subprocess.SubprocessError, FileNotFoundError):
            self.logger.warning("stylelint formatter not found")
            return False
    
    def _check_htmlhint(self) -> bool:
        """Check if htmlhint is installed."""
        try:
            result = subprocess.run(
                ["npx", "htmlhint", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            if result.returncode == 0:
                self.logger.info("Found htmlhint formatter")
                return True
            else:
                self.logger.warning("htmlhint formatter not found")
                return False
        except (subprocess.SubprocessError, FileNotFoundError):
            self.logger.warning("htmlhint formatter not found")
            return False
    
    async def fix_code(self, code: str, file_path: Optional[str] = None, 
                      issues: Optional[List[Dict[str, Any]]] = None) -> FixResult:
        """
        Fix issues in web technology code.
        
        Args:
            code: The code to fix.
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
        
        # Determine the language based on file extension or content
        language = self._determine_language(code, file_path)
        
        if not language:
            result.error = "Could not determine the language of the code"
            return result
        
        # Apply fixes in sequence
        modified_code = code
        changes = []
        
        # 1. Fix specific issues if provided
        if issues:
            issue_fixes = await self._fix_specific_issues(modified_code, issues, language, file_path)
            if issue_fixes:
                # Apply the changes
                for change in issue_fixes:
                    changes.append(change)
                modified_code = self.apply_changes(modified_code, issue_fixes)
        
        # 2. Fix structural issues if enabled
        if self.fix_structure:
            structure_fixes = await self._fix_structural_issues(modified_code, language, file_path)
            if structure_fixes:
                # Apply the changes
                for change in structure_fixes:
                    changes.append(change)
                modified_code = self.apply_changes(modified_code, structure_fixes)
        
        # 3. Fix style issues if enabled
        if self.fix_style:
            style_fixes = await self._fix_style_issues(modified_code, language, file_path)
            if style_fixes:
                # Apply the changes
                for change in style_fixes:
                    changes.append(change)
                modified_code = self.apply_changes(modified_code, style_fixes)
        
        # 4. Fix bug issues if enabled
        if self.fix_bugs:
            bug_fixes = await self._fix_bug_issues(modified_code, language, file_path)
            if bug_fixes:
                # Apply the changes
                for change in bug_fixes:
                    changes.append(change)
                modified_code = self.apply_changes(modified_code, bug_fixes)
        
        # 5. Auto-format the code if enabled
        if self.autoformat:
            formatted_code, format_changes = await self._format_code(modified_code, language, file_path)
            if formatted_code != modified_code:
                # Record the formatting as a change
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
            code: The code containing the issue.
            issue: The issue to fix.
            file_path: Optional path to the file (for reference).
        
        Returns:
            List of FixChange objects with suggestions.
        """
        suggestions = []
        
        # Check if the issue is fixable
        if not issue.get('fixable', False):
            return suggestions
        
        # Determine the language
        language = self._determine_language(code, file_path)
        
        if not language:
            return suggestions
        
        rule_id = issue.get('rule_id', '')
        message = issue.get('message', '')
        line = issue.get('line', 0)
        column = issue.get('column', 0)
        
        # Apply language-specific fixers based on rule_id or message
        if language == "html":
            changes = await self._fix_html_issue(code, line, column, rule_id, message)
            suggestions.extend(changes)
            
        elif language == "css":
            changes = await self._fix_css_issue(code, line, column, rule_id, message)
            suggestions.extend(changes)
            
        elif language in ["javascript", "typescript"]:
            changes = await self._fix_js_issue(code, line, column, rule_id, message, language)
            suggestions.extend(changes)
        
        # If no specific fixer found, try LLM
        if not suggestions and self.llm:
            changes = await self._get_llm_suggestions(code, issue, language, file_path)
            suggestions.extend(changes)
        
        return suggestions
    
    def _determine_language(self, code: str, file_path: Optional[str] = None) -> Optional[str]:
        """
        Determine the language of the code.
        
        Args:
            code: The code to analyze.
            file_path: Optional path to the file.
        
        Returns:
            The determined language ("html", "css", "javascript", "typescript") or None.
        """
        # Try to determine the language based on file extension
        if file_path:
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext in ['.html', '.htm', '.xhtml']:
                return "html"
            elif ext in ['.css', '.scss', '.less']:
                return "css"
            elif ext in ['.js', '.jsx']:
                return "javascript"
            elif ext in ['.ts', '.tsx']:
                return "typescript"
        
        # Try to determine the language based on content
        # Check for HTML tags
        if re.search(r'<\s*html|<\s*body|<\s*div|<\s*p|<\s*span|<\s*h[1-6]|<!DOCTYPE\s+html', code, re.IGNORECASE):
            return "html"
        
        # Check for CSS features
        if re.search(r'(\{[^}]*:[^}]*;[^}]*\})|(@media|@keyframes|@import|@charset|@font-face)', code):
            return "css"
        
        # Check for TypeScript features
        if re.search(r'(:\s*[A-Za-z]+\s*[,=\)])|(<[A-Za-z]+>)|interface\s+[A-Za-z]+|type\s+[A-Za-z]+\s*=', code):
            return "typescript"
        
        # Default to JavaScript for all other code
        if re.search(r'(function|const|let|var|import|export|class|=>|async|await)\s', code):
            return "javascript"
        
        # Could not determine the language
        return None
    
    async def _fix_specific_issues(self, code: str, issues: List[Dict[str, Any]], 
                                 language: str, file_path: Optional[str] = None) -> List[FixChange]:
        """
        Fix specific issues identified by the analyzer.
        
        Args:
            code: The code to fix.
            issues: List of issues to fix.
            language: The code language.
            file_path: Optional path to the file.
        
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
    
    async def _fix_structural_issues(self, code: str, language: str, 
                                   file_path: Optional[str] = None) -> List[FixChange]:
        """
        Fix structural issues in the code.
        
        Args:
            code: The code to fix.
            language: The code language.
            file_path: Optional path to the file.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        if language == "html":
            # Fix HTML structural issues
            changes.extend(self._fix_malformed_html_tags(code))
            changes.extend(self._fix_missing_html_structure(code))
            changes.extend(self._fix_invalid_nesting(code))
            
        elif language == "css":
            # Fix CSS structural issues
            changes.extend(self._fix_missing_css_properties(code))
            changes.extend(self._fix_unbalanced_css_braces(code))
            
        elif language in ["javascript", "typescript"]:
            # Fix JS/TS structural issues
            changes.extend(self._fix_unbalanced_braces(code))
            changes.extend(self._fix_missing_semicolons(code, language))
        
        return changes
    
    async def _fix_style_issues(self, code: str, language: str, 
                              file_path: Optional[str] = None) -> List[FixChange]:
        """
        Fix style issues in the code.
        
        Args:
            code: The code to fix.
            language: The code language.
            file_path: Optional path to the file.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Common style issues for all languages
        changes.extend(self._fix_trailing_whitespace(code))
        changes.extend(self._fix_final_newline(code))
        changes.extend(self._fix_mixed_indentation(code))
        
        # Language-specific style issues
        if language == "html":
            # Fix HTML style issues
            changes.extend(self._fix_inconsistent_html_attributes(code))
            
        elif language == "css":
            # Fix CSS style issues
            changes.extend(self._fix_css_vendor_prefixes(code))
            changes.extend(self._fix_css_color_formats(code))
            
        elif language in ["javascript", "typescript"]:
            # Fix JS/TS style issues
            changes.extend(self._fix_js_quotes(code))
            changes.extend(self._fix_js_spacing(code))
        
        return changes
    
    async def _fix_bug_issues(self, code: str, language: str, 
                            file_path: Optional[str] = None) -> List[FixChange]:
        """
        Fix potential bug issues in the code.
        
        Args:
            code: The code to fix.
            language: The code language.
            file_path: Optional path to the file.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        if language == "html":
            # Fix HTML bug issues
            changes.extend(self._fix_invalid_html_attributes(code))
            changes.extend(self._fix_accessibility_issues(code))
            
        elif language == "css":
            # Fix CSS bug issues
            changes.extend(self._fix_invalid_css_rules(code))
            changes.extend(self._fix_invalid_media_queries(code))
            
        elif language in ["javascript", "typescript"]:
            # Fix JS/TS bug issues
            changes.extend(self._fix_undefined_variables(code, language))
            changes.extend(self._fix_potential_null_refs(code, language))
        
        return changes
    
    async def _format_code(self, code: str, language: str, 
                         file_path: Optional[str] = None) -> Tuple[str, List[FixChange]]:
        """
        Format the code using the configured formatter.
        
        Args:
            code: The code to format.
            language: The code language.
            file_path: Optional path to the file.
        
        Returns:
            Tuple of (formatted_code, changes).
        """
        changes = []
        formatted_code = code
        
        # Use prettier if available
        if self._has_prettier:
            with tempfile.NamedTemporaryFile(delete=False, suffix=self._get_file_extension(language)) as tmp_file:
                tmp_path = tmp_file.name
                tmp_file.write(code.encode('utf-8'))
            
            try:
                # Determine parser based on language
                parser = "html"
                if language == "css":
                    parser = "css"
                elif language in ["javascript", "typescript"]:
                    parser = "babel-ts" if language == "typescript" else "babel"
                
                # Run prettier
                result = subprocess.run(
                    ["npx", "prettier", "--write", f"--parser={parser}", tmp_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False
                )
                
                if result.returncode == 0:
                    # Read the formatted code
                    with open(tmp_path, 'r', encoding='utf-8') as f:
                        formatted_code = f.read()
                    
                    if formatted_code != code:
                        # Create a change for the whole file
                        change = FixChange(
                            description=f"Format {language} code with prettier",
                            start_line=1,
                            start_column=1,
                            end_line=len(code.splitlines()) + 1,
                            end_column=1,
                            original_text=code,
                            replacement_text=formatted_code,
                            fix_type=FixType.SIMPLE
                        )
                        changes.append(change)
                else:
                    self.logger.warning(f"Error formatting {language} code with prettier: {result.stderr}")
            
            except Exception as e:
                self.logger.warning(f"Error formatting {language} code: {str(e)}")
            
            finally:
                # Clean up the temporary file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        
        # Use language-specific formatters if prettier is not available
        elif language == "html" and self._has_htmlhint:
            # No direct formatting capability, just apply indentation fixes
            formatted_code = self._reindent_html(code)
            
            if formatted_code != code:
                change = FixChange(
                    description="Format HTML indentation",
                    start_line=1,
                    start_column=1,
                    end_line=len(code.splitlines()) + 1,
                    end_column=1,
                    original_text=code,
                    replacement_text=formatted_code,
                    fix_type=FixType.SIMPLE
                )
                changes.append(change)
        
        elif language == "css" and self._has_stylelint:
            # No direct formatting capability, just apply indentation fixes
            formatted_code = self._reformat_css(code)
            
            if formatted_code != code:
                change = FixChange(
                    description="Format CSS indentation and spacing",
                    start_line=1,
                    start_column=1,
                    end_line=len(code.splitlines()) + 1,
                    end_column=1,
                    original_text=code,
                    replacement_text=formatted_code,
                    fix_type=FixType.SIMPLE
                )
                changes.append(change)
        
        elif language in ["javascript", "typescript"] and self._has_eslint:
            # Run ESLint with --fix option
            with tempfile.NamedTemporaryFile(delete=False, suffix=self._get_file_extension(language)) as tmp_file:
                tmp_path = tmp_file.name
                tmp_file.write(code.encode('utf-8'))
            
            try:
                # Run ESLint with --fix
                result = subprocess.run(
                    ["npx", "eslint", "--fix", tmp_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False
                )
                
                # Read the fixed code regardless of return code
                with open(tmp_path, 'r', encoding='utf-8') as f:
                    fixed_code = f.read()
                
                if fixed_code != code:
                    formatted_code = fixed_code
                    
                    change = FixChange(
                        description=f"Format {language} code with ESLint",
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
                self.logger.warning(f"Error formatting {language} code with ESLint: {str(e)}")
            
            finally:
                # Clean up the temporary file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        
        return formatted_code, changes
    
    def _get_file_extension(self, language: str) -> str:
        """
        Get the appropriate file extension for a language.
        
        Args:
            language: The code language.
        
        Returns:
            The file extension including the dot.
        """
        if language == "html":
            return ".html"
        elif language == "css":
            return ".css"
        elif language == "javascript":
            return ".js"
        elif language == "typescript":
            return ".ts"
        else:
            return ".txt"
    
    async def _fix_html_issue(self, code: str, line: int, column: int, rule_id: str, message: str) -> List[FixChange]:
        """
        Fix a specific HTML issue.
        
        Args:
            code: The HTML code.
            line: Line number of the issue.
            column: Column number of the issue.
            rule_id: The rule ID of the issue.
            message: The error message.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Handle common HTML issues based on rule ID or message
        if "tag-pair" in rule_id or "unclosed tag" in message.lower():
            changes.extend(self._fix_unclosed_tags(code, line, column, message))
        
        elif "attr-lowercase" in rule_id or "attributes should be lowercase" in message.lower():
            changes.extend(self._fix_uppercase_attributes(code, line, column))
        
        elif "doctype-first" in rule_id or "doctype should be first" in message.lower():
            changes.extend(self._fix_missing_doctype(code))
        
        elif "alt-require" in rule_id or "missing alt attribute" in message.lower():
            changes.extend(self._fix_missing_alt(code, line, column))
        
        return changes
    
    async def _fix_css_issue(self, code: str, line: int, column: int, rule_id: str, message: str) -> List[FixChange]:
        """
        Fix a specific CSS issue.
        
        Args:
            code: The CSS code.
            line: Line number of the issue.
            column: Column number of the issue.
            rule_id: The rule ID of the issue.
            message: The error message.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Handle common CSS issues based on rule ID or message
        if "color-no-invalid-hex" in rule_id or "invalid hex color" in message.lower():
            changes.extend(self._fix_invalid_hex_color(code, line, column, message))
        
        elif "block-no-empty" in rule_id or "empty block" in message.lower():
            changes.extend(self._fix_empty_css_blocks(code, line, column))
        
        elif "unit-no-unknown" in rule_id or "unknown unit" in message.lower():
            changes.extend(self._fix_invalid_css_units(code, line, column, message))
        
        return changes
    
    async def _fix_js_issue(self, code: str, line: int, column: int, rule_id: str, 
                          message: str, language: str) -> List[FixChange]:
        """
        Fix a specific JavaScript/TypeScript issue.
        
        Args:
            code: The JS/TS code.
            line: Line number of the issue.
            column: Column number of the issue.
            rule_id: The rule ID of the issue.
            message: The error message.
            language: "javascript" or "typescript".
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Handle common JS/TS issues based on rule ID or message
        if "no-unused-vars" in rule_id or "is defined but never used" in message.lower():
            changes.extend(self._fix_unused_js_variable(code, line, column, message, language))
        
        elif "missing-semicolon" in rule_id or "missing semicolon" in message.lower():
            changes.extend(self._fix_missing_js_semicolon(code, line, column, language))
        
        elif "no-undef" in rule_id or "is not defined" in message.lower():
            changes.extend(self._fix_undefined_js_variable(code, line, column, message, language))
        
        return changes
    
    def _fix_unclosed_tags(self, code: str, line: int, column: int, message: str) -> List[FixChange]:
        """
        Fix unclosed HTML tags.
        
        Args:
            code: The HTML code.
            line: Line number of the issue.
            column: Column number of the issue.
            message: The error message.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Extract tag name from message
        tag_match = re.search(r'tag\s+<([a-zA-Z0-9]+)>', message)
        if not tag_match:
            # Try another pattern
            tag_match = re.search(r'<([a-zA-Z0-9]+)>', message)
        
        if tag_match:
            tag_name = tag_match.group(1).lower()
            
            # Get the line content
            lines = code.splitlines()
            if 0 < line <= len(lines):
                line_content = lines[line - 1]
                
                # Check if the line contains the opening tag
                opening_tag_pattern = f'<{tag_name}[^>]*>'
                opening_match = re.search(opening_tag_pattern, line_content)
                
                if opening_match:
                    # Add a closing tag at the end of the line
                    change = FixChange(
                        description=f"Add closing tag for <{tag_name}>",
                        start_line=line,
                        start_column=len(line_content) + 1,
                        end_line=line,
                        end_column=len(line_content) + 1,
                        original_text="",
                        replacement_text=f"</{tag_name}>",
                        fix_type=FixType.SIMPLE
                    )
                    changes.append(change)
                else:
                    # Try to find the opening tag in previous lines
                    for i in range(line - 2, -1, -1):
                        prev_line = lines[i]
                        opening_match = re.search(opening_tag_pattern, prev_line)
                        if opening_match:
                            # Add a closing tag at the current line
                            indentation = re.match(r'^(\s*)', line_content)
                            indent = indentation.group(1) if indentation else ""
                            
                            change = FixChange(
                                description=f"Add closing tag for <{tag_name}>",
                                start_line=line,
                                start_column=len(line_content) + 1,
                                end_line=line,
                                end_column=len(line_content) + 1,
                                original_text="",
                                replacement_text=f"\n{indent}</{tag_name}>",
                                fix_type=FixType.SIMPLE
                            )
                            changes.append(change)
                            break
        
        return changes
    
    def _fix_uppercase_attributes(self, code: str, line: int, column: int) -> List[FixChange]:
        """
        Fix uppercase HTML attributes.
        
        Args:
            code: The HTML code.
            line: Line number of the issue.
            column: Column number of the issue.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Get the line content
        lines = code.splitlines()
        if 0 < line <= len(lines):
            line_content = lines[line - 1]
            
            # Find attributes with uppercase letters
            attr_pattern = r'(\s+)([A-Z][a-zA-Z0-9]*)(\s*=\s*[\'"][^\'"]*[\'"]|\s*=\s*[^\s>]+|\s+)'
            for match in re.finditer(attr_pattern, line_content):
                # Convert attribute name to lowercase
                attr_name = match.group(2)
                lowercase_attr = attr_name.lower()
                
                if attr_name != lowercase_attr:
                    change = FixChange(
                        description=f"Convert attribute '{attr_name}' to lowercase",
                        start_line=line,
                        start_column=match.start(2) + 1,
                        end_line=line,
                        end_column=match.end(2) + 1,
                        original_text=attr_name,
                        replacement_text=lowercase_attr,
                        fix_type=FixType.SIMPLE
                    )
                    changes.append(change)
        
        return changes
    
    def _fix_missing_doctype(self, code: str) -> List[FixChange]:
        """
        Fix missing HTML doctype declaration.
        
        Args:
            code: The HTML code.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Check if the doctype is missing
        if not re.search(r'<!DOCTYPE\s+html>', code, re.IGNORECASE):
            # Add doctype at the beginning of the file
            change = FixChange(
                description="Add HTML5 doctype declaration",
                start_line=1,
                start_column=1,
                end_line=1,
                end_column=1,
                original_text="",
                replacement_text="<!DOCTYPE html>\n",
                fix_type=FixType.SIMPLE
            )
            changes.append(change)
        
        return changes
    
    def _fix_missing_alt(self, code: str, line: int, column: int) -> List[FixChange]:
        """
        Fix missing alt attribute for img tags.
        
        Args:
            code: The HTML code.
            line: Line number of the issue.
            column: Column number of the issue.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Get the line content
        lines = code.splitlines()
        if 0 < line <= len(lines):
            line_content = lines[line - 1]
            
            # Find img tags without alt attribute
            img_pattern = r'<img\s+([^>]*)(?<!\salt=[\'"][^\'"]*[\'"])(?<!\salt=[^\s>]+)(/?)>'
            img_match = re.search(img_pattern, line_content)
            
            if img_match:
                # Try to infer a meaningful alt text from context
                alt_text = "Image description"  # Default
                
                # Check for title or src attributes to use as alt
                title_match = re.search(r'title=[\'"]([^\'"]+)[\'"]', img_match.group(1))
                if title_match:
                    alt_text = title_match.group(1)
                else:
                    src_match = re.search(r'src=[\'"]([^\'"]+)[\'"]', img_match.group(1))
                    if src_match:
                        # Extract filename from src path
                        src_path = src_match.group(1)
                        filename = os.path.basename(src_path)
                        name_part = os.path.splitext(filename)[0]
                        # Convert to title case and replace dashes/underscores with spaces
                        alt_text = name_part.replace('-', ' ').replace('_', ' ').title()
                
                # Add alt attribute before the closing bracket
                closing_pos = img_match.end(1) + 1
                
                change = FixChange(
                    description="Add alt attribute to img tag",
                    start_line=line,
                    start_column=closing_pos,
                    end_line=line,
                    end_column=closing_pos,
                    original_text="",
                    replacement_text=f' alt="{alt_text}"',
                    fix_type=FixType.SIMPLE
                )
                changes.append(change)
        
        return changes
    
    def _fix_invalid_hex_color(self, code: str, line: int, column: int, message: str) -> List[FixChange]:
        """
        Fix invalid hex color in CSS.
        
        Args:
            code: The CSS code.
            line: Line number of the issue.
            column: Column number of the issue.
            message: The error message.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Extract the invalid color from the message
        color_match = re.search(r'#([A-Fa-f0-9]+)', message)
        if color_match:
            invalid_color = color_match.group(0)
            
            # Get the line content
            lines = code.splitlines()
            if 0 < line <= len(lines):
                line_content = lines[line - 1]
                
                # Find the invalid color in the line
                if invalid_color in line_content:
                    # Determine the fix based on the length
                    color_value = color_match.group(1)
                    
                    fixed_color = invalid_color
                    if len(color_value) not in [3, 6, 8]:
                        # Invalid length, try to fix it
                        if len(color_value) > 6:
                            fixed_color = f"#{color_value[:6]}"  # Truncate to 6 digits
                        elif len(color_value) in [4, 5]:
                            fixed_color = f"#{color_value[:3]}"  # Truncate to 3 digits
                        elif len(color_value) == 2:
                            fixed_color = f"#{color_value * 3}"  # Repeat to make 6 digits
                        elif len(color_value) == 1:
                            fixed_color = f"#{color_value * 3}"  # Repeat to make 3 digits
                    
                    # Find position in the line
                    start_pos = line_content.find(invalid_color)
                    if start_pos >= 0:
                        change = FixChange(
                            description=f"Fix invalid hex color: {invalid_color}",
                            start_line=line,
                            start_column=start_pos + 1,
                            end_line=line,
                            end_column=start_pos + len(invalid_color) + 1,
                            original_text=invalid_color,
                            replacement_text=fixed_color,
                            fix_type=FixType.SIMPLE
                        )
                        changes.append(change)
        
        return changes
    
    def _fix_empty_css_blocks(self, code: str, line: int, column: int) -> List[FixChange]:
        """
        Fix empty CSS blocks.
        
        Args:
            code: The CSS code.
            line: Line number of the issue.
            column: Column number of the issue.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Get the line content
        lines = code.splitlines()
        if 0 < line <= len(lines):
            line_content = lines[line - 1]
            
            # Find empty blocks: selector { }
            empty_block_pattern = r'([^{]*\{\s*\})'
            empty_block_match = re.search(empty_block_pattern, line_content)
            
            if empty_block_match:
                # Comment out the empty block
                empty_block = empty_block_match.group(1)
                
                change = FixChange(
                    description="Comment out empty CSS block",
                    start_line=line,
                    start_column=empty_block_match.start(1) + 1,
                    end_line=line,
                    end_column=empty_block_match.end(1) + 1,
                    original_text=empty_block,
                    replacement_text=f"/* {empty_block} */",
                    fix_type=FixType.SIMPLE
                )
                changes.append(change)
        
        return changes
    
    def _fix_invalid_css_units(self, code: str, line: int, column: int, message: str) -> List[FixChange]:
        """
        Fix invalid CSS units.
        
        Args:
            code: The CSS code.
            line: Line number of the issue.
            column: Column number of the issue.
            message: The error message.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Extract the invalid unit from the message
        unit_match = re.search(r'(\d+)([a-zA-Z%]+)', message)
        if unit_match:
            value = unit_match.group(1)
            invalid_unit = unit_match.group(2)
            
            # Get the line content
            lines = code.splitlines()
            if 0 < line <= len(lines):
                line_content = lines[line - 1]
                
                # Find the invalid unit in the line
                pattern = re.escape(f"{value}{invalid_unit}")
                for match in re.finditer(pattern, line_content):
                    # Determine the appropriate replacement unit
                    if invalid_unit in ['px', 'pt', 'cm', 'mm', 'in', 'pc']:
                        # It's likely a length value, keep it
                        replacement = f"{value}{invalid_unit}"
                    else:
                        # Try to determine the appropriate unit
                        property_match = re.search(r'([a-zA-Z-]+)\s*:', line_content[:match.start()])
                        
                        if property_match:
                            property_name = property_match.group(1).lower()
                            
                            # Map properties to appropriate units
                            if property_name in ['width', 'height', 'margin', 'padding', 'left', 'right', 'top', 'bottom']:
                                replacement = f"{value}px"
                            elif property_name in ['font-size', 'line-height']:
                                replacement = f"{value}px"
                            elif property_name in ['opacity']:
                                # No unit for opacity
                                replacement = value
                            else:
                                # Default to pixels
                                replacement = f"{value}px"
                        else:
                            # Default to pixels
                            replacement = f"{value}px"
                    
                    if replacement != f"{value}{invalid_unit}":
                        change = FixChange(
                            description=f"Fix invalid CSS unit: {value}{invalid_unit}",
                            start_line=line,
                            start_column=match.start() + 1,
                            end_line=line,
                            end_column=match.end() + 1,
                            original_text=f"{value}{invalid_unit}",
                            replacement_text=replacement,
                            fix_type=FixType.SIMPLE
                        )
                        changes.append(change)
        
        return changes
    
    def _fix_unused_js_variable(self, code: str, line: int, column: int, message: str, language: str) -> List[FixChange]:
        """
        Fix unused variables in JavaScript/TypeScript.
        
        Args:
            code: The JS/TS code.
            line: Line number of the issue.
            column: Column number of the issue.
            message: The error message.
            language: "javascript" or "typescript".
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Extract the variable name from the message
        var_match = re.search(r'[\'"]([a-zA-Z0-9_$]+)[\'"]', message)
        if not var_match:
            var_match = re.search(r'([a-zA-Z0-9_$]+)\s+is defined', message)
        
        if var_match:
            var_name = var_match.group(1)
            
            # Get the line content
            lines = code.splitlines()
            if 0 < line <= len(lines):
                line_content = lines[line - 1]
                
                # Find the variable declaration
                patterns = [
                    rf'(var|let|const)\s+{re.escape(var_name)}\s*=',
                    rf'(var|let|const)\s+[^=,]*,\s*{re.escape(var_name)}\s*=',
                    rf'(var|let|const)\s+[^=,]*,\s*{re.escape(var_name)}\s*,',
                    rf'function\s+{re.escape(var_name)}\s*\('
                ]
                
                for pattern in patterns:
                    var_match = re.search(pattern, line_content)
                    if var_match:
                        # Two options: comment out the variable or prefix with underscore
                        comment_fix = FixChange(
                            description=f"Comment out unused variable '{var_name}'",
                            start_line=line,
                            start_column=1,
                            end_line=line,
                            end_column=len(line_content) + 1,
                            original_text=line_content,
                            replacement_text=f"// {line_content}  // Unused variable '{var_name}'",
                            fix_type=FixType.SIMPLE,
                            confidence=0.8
                        )
                        changes.append(comment_fix)
                        
                        # Rename with underscore prefix
                        if not var_name.startswith('_'):
                            renamed_fix = FixChange(
                                description=f"Prefix unused variable '{var_name}' with underscore",
                                start_line=line,
                                start_column=var_match.end(1) + 1,
                                end_line=line,
                                end_column=var_match.end(1) + 1 + len(var_name),
                                original_text=var_name,
                                replacement_text=f"_{var_name}",
                                fix_type=FixType.SIMPLE,
                                confidence=0.9
                            )
                            changes.append(renamed_fix)
                        
                        break
        
        return changes
    
    def _fix_missing_js_semicolon(self, code: str, line: int, column: int, language: str) -> List[FixChange]:
        """
        Fix missing semicolons in JavaScript/TypeScript.
        
        Args:
            code: The JS/TS code.
            line: Line number of the issue.
            column: Column number of the issue.
            language: "javascript" or "typescript".
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Get the line content
        lines = code.splitlines()
        if 0 < line <= len(lines):
            line_content = lines[line - 1]
            
            # Check if the line ends with a semicolon
            if not line_content.rstrip().endswith(';'):
                # Add semicolon at the end of the line
                change = FixChange(
                    description="Add missing semicolon",
                    start_line=line,
                    start_column=len(line_content.rstrip()) + 1,
                    end_line=line,
                    end_column=len(line_content.rstrip()) + 1,
                    original_text="",
                    replacement_text=";",
                    fix_type=FixType.SIMPLE
                )
                changes.append(change)
        
        return changes
    
    def _fix_undefined_js_variable(self, code: str, line: int, column: int, message: str, language: str) -> List[FixChange]:
        """
        Fix undefined variables in JavaScript/TypeScript.
        
        Args:
            code: The JS/TS code.
            line: Line number of the issue.
            column: Column number of the issue.
            message: The error message.
            language: "javascript" or "typescript".
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Extract the variable name from the message
        var_match = re.search(r'[\'"]([a-zA-Z0-9_$]+)[\'"]', message)
        if not var_match:
            var_match = re.search(r'([a-zA-Z0-9_$]+)\s+is not defined', message)
        
        if var_match:
            var_name = var_match.group(1)
            
            # Get the line content
            lines = code.splitlines()
            if 0 < line <= len(lines):
                line_content = lines[line - 1]
                
                # Find the variable usage
                var_pattern = rf'\b{re.escape(var_name)}\b'
                var_match = re.search(var_pattern, line_content)
                
                if var_match:
                    # Find the function scope to add the variable declaration
                    function_start = -1
                    indent = ""
                    
                    # Look for function definition above the current line
                    for i in range(line - 2, -1, -1):
                        prev_line = lines[i]
                        if re.search(r'function\s+', prev_line):
                            function_start = i
                            indent_match = re.match(r'^(\s+)', prev_line)
                            if indent_match:
                                indent = indent_match.group(1)
                            break
                    
                    if function_start >= 0:
                        # Add variable declaration after the function opening brace
                        for i in range(function_start, line - 1):
                            if '{' in lines[i]:
                                declaration_line = i + 1
                                declaration_indent = indent + "  "  # Additional indent
                                
                                # For TypeScript, determine an appropriate type
                                if language == "typescript":
                                    # Try to infer type from usage
                                    type_annotation = ": any"
                                    if "==" in line_content or "===" in line_content:
                                        type_annotation = ": boolean"
                                    elif re.search(r'\d+', line_content):
                                        type_annotation = ": number"
                                    elif '"' in line_content or "'" in line_content:
                                        type_annotation = ": string"
                                    
                                    declaration = f"{declaration_indent}let {var_name}{type_annotation}; // TODO: Initialize with appropriate value"
                                else:
                                    declaration = f"{declaration_indent}let {var_name}; // TODO: Initialize with appropriate value"
                                
                                change = FixChange(
                                    description=f"Declare variable '{var_name}'",
                                    start_line=declaration_line,
                                    start_column=1,
                                    end_line=declaration_line,
                                    end_column=1,
                                    original_text="",
                                    replacement_text=f"{declaration}\n",
                                    fix_type=FixType.COMPLEX,
                                    confidence=0.7
                                )
                                changes.append(change)
                                break
                    else:
                        # No function scope found, add at the top of the file
                        if language == "typescript":
                            declaration = f"let {var_name}: any; // TODO: Initialize with appropriate value"
                        else:
                            declaration = f"let {var_name}; // TODO: Initialize with appropriate value"
                        
                        change = FixChange(
                            description=f"Declare variable '{var_name}' at the top",
                            start_line=1,
                            start_column=1,
                            end_line=1,
                            end_column=1,
                            original_text="",
                            replacement_text=f"{declaration}\n\n",
                            fix_type=FixType.COMPLEX,
                            confidence=0.6
                        )
                        changes.append(change)
        
        return changes
    
    def _fix_malformed_html_tags(self, code: str) -> List[FixChange]:
        """
        Fix malformed HTML tags.
        
        Args:
            code: The HTML code.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Fix self-closing tags
        lines = code.splitlines()
        for i, line in enumerate(lines):
            # Find self-closing tags that don't use proper syntax
            improper_tags = re.finditer(r'<([a-zA-Z][a-zA-Z0-9]*)[^>]*>(\s*)</\1>', line)
            
            for match in improper_tags:
                tag_name = match.group(1)
                # Self-closing HTML tags
                void_elements = ['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr']
                
                if tag_name.lower() in void_elements:
                    # Convert to proper self-closing tag
                    opening_tag = match.group(0)
                    closing_tag_pos = opening_tag.find('>')
                    
                    change = FixChange(
                        description=f"Convert to self-closing tag: <{tag_name}>",
                        start_line=i + 1,
                        start_column=match.start() + 1,
                        end_line=i + 1,
                        end_column=match.end() + 1,
                        original_text=match.group(0),
                        replacement_text=opening_tag[:closing_tag_pos] + "/>" if not opening_tag[:closing_tag_pos].endswith('/') else opening_tag,
                        fix_type=FixType.SIMPLE
                    )
                    changes.append(change)
        
        return changes
    
    def _fix_missing_html_structure(self, code: str) -> List[FixChange]:
        """
        Fix missing HTML structure elements.
        
        Args:
            code: The HTML code.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Check for essential elements
        has_html = re.search(r'<html', code, re.IGNORECASE) is not None
        has_head = re.search(r'<head', code, re.IGNORECASE) is not None
        has_body = re.search(r'<body', code, re.IGNORECASE) is not None
        
        # If there's content but no structure, add it
        if not has_html and not has_head and not has_body and len(code.strip()) > 0:
            # This is likely a fragment, wrap it with proper HTML structure
            indentation = "  "
            doctype = "<!DOCTYPE html>\n"
            html_open = "<html>\n"
            head = f"{indentation}<head>\n{indentation}{indentation}<meta charset=\"UTF-8\">\n{indentation}{indentation}<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n{indentation}{indentation}<title>Document</title>\n{indentation}</head>\n"
            body_open = f"{indentation}<body>\n"
            
            # Apply appropriate indentation to the content
            content_lines = code.splitlines()
            indented_content = "\n".join([f"{indentation}{indentation}{line}" for line in content_lines])
            
            body_close = f"\n{indentation}</body>\n"
            html_close = "</html>"
            
            structured_code = f"{doctype}{html_open}{head}{body_open}{indented_content}{body_close}{html_close}"
            
            change = FixChange(
                description="Add proper HTML structure",
                start_line=1,
                start_column=1,
                end_line=len(content_lines) + 1,
                end_column=1,
                original_text=code,
                replacement_text=structured_code,
                fix_type=FixType.COMPLEX,
                confidence=0.7
            )
            changes.append(change)
        
        return changes
    
    def _fix_invalid_nesting(self, code: str) -> List[FixChange]:
        """
        Fix invalid HTML tag nesting.
        
        Args:
            code: The HTML code.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # This is complex to do properly without a full HTML parser
        # Here's a simplified approach to catch common issues
        
        # Find problematic nesting like <p><div>...</div></p>
        # (block elements can't be inside paragraphs)
        block_elements = ['div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'section', 'article', 'aside', 'nav', 'header', 'footer']
        
        lines = code.splitlines()
        for i, line in enumerate(lines):
            for block in block_elements:
                # Look for patterns like <p>...<div>
                block_in_p = re.search(rf'<p\b[^>]*>[^<]*<{block}\b', line)
                if block_in_p:
                    # This is invalid nesting, suggest fixing it
                    change = FixChange(
                        description=f"Invalid nesting: <{block}> inside <p>",
                        start_line=i + 1,
                        start_column=1,
                        end_line=i + 1,
                        end_column=len(line) + 1,
                        original_text=line,
                        replacement_text=f"<!-- Warning: Invalid nesting - <{block}> should not be inside <p> -->\n{line}",
                        fix_type=FixType.SIMPLE,
                        confidence=0.6
                    )
                    changes.append(change)
        
        return changes
    
    def _fix_missing_css_properties(self, code: str) -> List[FixChange]:
        """
        Fix missing CSS properties.
        
        Args:
            code: The CSS code.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Find CSS rules with missing properties
        rule_pattern = r'([^{]*\{)\s*\}'
        lines = code.splitlines()
        
        for i, line in enumerate(lines):
            for match in re.finditer(rule_pattern, line):
                selector = match.group(1).strip()
                
                # Add a placeholder property
                change = FixChange(
                    description="Add placeholder property to empty CSS rule",
                    start_line=i + 1,
                    start_column=match.start(0) + len(selector) + 1,
                    end_line=i + 1,
                    end_column=match.end(0),
                    original_text=match.group(0)[len(selector):],
                    replacement_text="{ /* TODO: Add properties */ }",
                    fix_type=FixType.SIMPLE
                )
                changes.append(change)
        
        return changes
    
    def _fix_unbalanced_css_braces(self, code: str) -> List[FixChange]:
        """
        Fix unbalanced braces in CSS.
        
        Args:
            code: The CSS code.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Count opening and closing braces
        opening_count = code.count('{')
        closing_count = code.count('}')
        
        if opening_count > closing_count:
            # Missing closing braces
            diff = opening_count - closing_count
            
            lines = code.splitlines()
            # Add missing closing braces at the end
            change = FixChange(
                description=f"Add {diff} missing closing braces",
                start_line=len(lines) + 1,
                start_column=1,
                end_line=len(lines) + 1,
                end_column=1,
                original_text="",
                replacement_text="\n" + "}" * diff + " /* Added missing closing braces */",
                fix_type=FixType.SIMPLE
            )
            changes.append(change)
        
        elif closing_count > opening_count:
            # Too many closing braces, find and comment out extras
            diff = closing_count - opening_count
            
            lines = code.splitlines()
            braces_to_find = diff
            
            for i in range(len(lines) - 1, -1, -1):
                line = lines[i]
                
                # Find closing braces and comment them
                for j in range(len(line) - 1, -1, -1):
                    if line[j] == '}' and braces_to_find > 0:
                        before = line[:j]
                        after = line[j+1:]
                        
                        change = FixChange(
                            description="Comment out extra closing brace",
                            start_line=i + 1,
                            start_column=j + 1,
                            end_line=i + 1,
                            end_column=j + 2,
                            original_text="}",
                            replacement_text="/* } */",
                            fix_type=FixType.SIMPLE
                        )
                        changes.append(change)
                        
                        braces_to_find -= 1
                        
                        if braces_to_find == 0:
                            break
                
                if braces_to_find == 0:
                    break
        
        return changes
    
    def _fix_unbalanced_braces(self, code: str) -> List[FixChange]:
        """
        Fix unbalanced braces in JavaScript/TypeScript.
        
        Args:
            code: The JS/TS code.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Count different bracket types
        brackets = {
            '{': '}',
            '[': ']',
            '(': ')'
        }
        
        for opening, closing in brackets.items():
            opening_count = code.count(opening)
            closing_count = code.count(closing)
            
            if opening_count > closing_count:
                # Missing closing brackets
                diff = opening_count - closing_count
                
                lines = code.splitlines()
                # Add missing closing brackets at the end
                change = FixChange(
                    description=f"Add {diff} missing {closing} brackets",
                    start_line=len(lines) + 1,
                    start_column=1,
                    end_line=len(lines) + 1,
                    end_column=1,
                    original_text="",
                    replacement_text="\n" + closing * diff + " /* Added missing closing brackets */",
                    fix_type=FixType.SIMPLE
                )
                changes.append(change)
            
            elif closing_count > opening_count:
                # Too many closing brackets, find and comment out extras
                diff = closing_count - opening_count
                
                lines = code.splitlines()
                brackets_to_find = diff
                
                for i in range(len(lines) - 1, -1, -1):
                    line = lines[i]
                    
                    # Find closing brackets and comment them
                    for j in range(len(line) - 1, -1, -1):
                        if line[j] == closing and brackets_to_find > 0:
                            change = FixChange(
                                description=f"Comment out extra {closing} bracket",
                                start_line=i + 1,
                                start_column=j + 1,
                                end_line=i + 1,
                                end_column=j + 2,
                                original_text=closing,
                                replacement_text=f"/* {closing} */",
                                fix_type=FixType.SIMPLE
                            )
                            changes.append(change)
                            
                            brackets_to_find -= 1
                            
                            if brackets_to_find == 0:
                                break
                    
                    if brackets_to_find == 0:
                        break
        
        return changes
    
    def _fix_missing_semicolons(self, code: str, language: str) -> List[FixChange]:
        """
        Fix missing semicolons in JavaScript/TypeScript.
        
        Args:
            code: The JS/TS code.
            language: "javascript" or "typescript".
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Simple approach: check if lines should have semicolons
        lines = code.splitlines()
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Skip empty lines, lines that already have semicolons, and lines that shouldn't have semicolons
            if not stripped or stripped.endswith(';') or stripped.endswith('{') or stripped.endswith('}') or stripped.endswith(':'):
                continue
            
            # Skip lines that start function/class declarations or are clearly flow control
            if (stripped.startswith('function ') or stripped.startswith('class ') or
                stripped.startswith('if ') or stripped.startswith('else ') or
                stripped.startswith('for ') or stripped.startswith('while ') or
                stripped.startswith('switch ') or stripped.startswith('case ')):
                continue
            
            # Skip comment lines
            if stripped.startswith('//') or stripped.startswith('/*'):
                continue
            
            # This line likely needs a semicolon
            change = FixChange(
                description="Add missing semicolon",
                start_line=i + 1,
                start_column=len(line) + 1,
                end_line=i + 1,
                end_column=len(line) + 1,
                original_text="",
                replacement_text=";",
                fix_type=FixType.SIMPLE
            )
            changes.append(change)
        
        return changes
    
    def _fix_trailing_whitespace(self, code: str) -> List[FixChange]:
        """
        Fix trailing whitespace in code.
        
        Args:
            code: The code to fix.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        lines = code.splitlines(True)  # Keep line endings
        
        for i, line in enumerate(lines):
            stripped = line.rstrip('\r\n')
            
            if stripped and stripped.rstrip() != stripped:
                # Line has trailing whitespace
                fixed_line = stripped.rstrip()
                if line.endswith('\r\n'):
                    fixed_line += '\r\n'
                elif line.endswith('\n'):
                    fixed_line += '\n'
                
                change = FixChange(
                    description="Remove trailing whitespace",
                    start_line=i + 1,
                    start_column=1,
                    end_line=i + 1,
                    end_column=len(line) + 1,
                    original_text=line,
                    replacement_text=fixed_line,
                    fix_type=FixType.SIMPLE
                )
                changes.append(change)
        
        return changes
    
    def _fix_final_newline(self, code: str) -> List[FixChange]:
        """
        Fix missing final newline.
        
        Args:
            code: The code to fix.
        
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
    
    def _fix_mixed_indentation(self, code: str) -> List[FixChange]:
        """
        Fix mixed indentation (spaces and tabs).
        
        Args:
            code: The code to fix.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        lines = code.splitlines()
        
        # Count spaces and tabs at the beginning of lines
        space_lines = 0
        tab_lines = 0
        
        for line in lines:
            if line.strip():  # Skip empty lines
                if line.startswith('\t'):
                    tab_lines += 1
                elif line.startswith(' '):
                    space_lines += 1
        
        # Determine the dominant indentation style
        use_spaces = space_lines >= tab_lines
        
        if use_spaces:
            # Convert tabs to spaces (assuming 2 spaces per tab)
            for i, line in enumerate(lines):
                if line.startswith('\t'):
                    # Count leading tabs
                    leading_tabs = 0
                    for char in line:
                        if char == '\t':
                            leading_tabs += 1
                        else:
                            break
                    
                    # Replace tabs with spaces
                    spaces = ' ' * (2 * leading_tabs)
                    fixed_line = spaces + line[leading_tabs:]
                    
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
        else:
            # Convert spaces to tabs (assuming 2 or 4 spaces per tab)
            for i, line in enumerate(lines):
                if line.startswith(' '):
                    # Count leading spaces
                    leading_spaces = 0
                    for char in line:
                        if char == ' ':
                            leading_spaces += 1
                        else:
                            break
                    
                    # Replace spaces with tabs
                    tabs = '\t' * (leading_spaces // 2)  # Assuming 2 spaces per tab
                    remaining_spaces = ' ' * (leading_spaces % 2)
                    fixed_line = tabs + remaining_spaces + line[leading_spaces:]
                    
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
        
        return changes
    
    def _fix_inconsistent_html_attributes(self, code: str) -> List[FixChange]:
        """
        Fix inconsistent HTML attribute quoting.
        
        Args:
            code: The HTML code.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Count single and double quotes
        double_quotes = len(re.findall(r'=\s*"[^"]*"', code))
        single_quotes = len(re.findall(r"=\s*'[^']*'", code))
        
        # Use the dominant quote style
        use_double_quotes = double_quotes >= single_quotes
        
        lines = code.splitlines()
        
        for i, line in enumerate(lines):
            # Find attributes with the non-dominant quote style
            if use_double_quotes:
                # Find single-quoted attributes
                for match in re.finditer(r"(\w+\s*=\s*)('[^']*')(\s)", line):
                    attr_value = match.group(2)
                    # Convert to double quotes
                    new_value = '"' + attr_value[1:-1] + '"'
                    
                    change = FixChange(
                        description="Convert single quotes to double quotes in HTML attribute",
                        start_line=i + 1,
                        start_column=match.start(2) + 1,
                        end_line=i + 1,
                        end_column=match.end(2) + 1,
                        original_text=attr_value,
                        replacement_text=new_value,
                        fix_type=FixType.SIMPLE
                    )
                    changes.append(change)
            else:
                # Find double-quoted attributes
                for match in re.finditer(r'(\w+\s*=\s*)("[^"]*")(\s)', line):
                    attr_value = match.group(2)
                    # Convert to single quotes
                    new_value = "'" + attr_value[1:-1] + "'"
                    
                    change = FixChange(
                        description="Convert double quotes to single quotes in HTML attribute",
                        start_line=i + 1,
                        start_column=match.start(2) + 1,
                        end_line=i + 1,
                        end_column=match.end(2) + 1,
                        original_text=attr_value,
                        replacement_text=new_value,
                        fix_type=FixType.SIMPLE
                    )
                    changes.append(change)
        
        return changes
    
    def _fix_css_vendor_prefixes(self, code: str) -> List[FixChange]:
        """
        Fix missing CSS vendor prefixes.
        
        Args:
            code: The CSS code.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Properties that often need vendor prefixes
        prefix_properties = {
            'transform': ['-webkit-transform', '-moz-transform', '-ms-transform'],
            'transition': ['-webkit-transition', '-moz-transition', '-ms-transition'],
            'animation': ['-webkit-animation', '-moz-animation'],
            'box-shadow': ['-webkit-box-shadow', '-moz-box-shadow'],
            'border-radius': ['-webkit-border-radius', '-moz-border-radius'],
            'user-select': ['-webkit-user-select', '-moz-user-select', '-ms-user-select']
        }
        
        lines = code.splitlines()
        
        for i, line in enumerate(lines):
            # Look for properties that might need prefixes
            for prop, prefixes in prefix_properties.items():
                # Check if the line contains the property but not its prefixes
                prop_pattern = fr'\b{prop}\s*:'
                if re.search(prop_pattern, line):
                    # Check if any prefixes are already present
                    missing_prefixes = []
                    for prefix in prefixes:
                        prefix_pattern = fr'\b{prefix}\s*:'
                        if not re.search(prefix_pattern, ''.join(lines[max(0, i-5):min(len(lines), i+5)])):
                            missing_prefixes.append(prefix)
                    
                    if missing_prefixes:
                        # Extract the property value
                        value_match = re.search(fr'{prop}\s*:\s*([^;]+);?', line)
                        if value_match:
                            prop_value = value_match.group(1).strip()
                            
                            # Get indentation
                            indent_match = re.match(r'^(\s*)', line)
                            indent = indent_match.group(1) if indent_match else ""
                            
                            # Create prefix lines
                            prefix_lines = []
                            for prefix in missing_prefixes:
                                prefix_lines.append(f"{indent}{prefix}: {prop_value};")
                            
                            # Add the prefix lines before the standard property
                            change = FixChange(
                                description=f"Add vendor prefixes for {prop}",
                                start_line=i + 1,
                                start_column=1,
                                end_line=i + 1,
                                end_column=1,
                                original_text="",
                                replacement_text="\n".join(prefix_lines) + "\n",
                                fix_type=FixType.SIMPLE
                            )
                            changes.append(change)
        
        return changes
    
    def _fix_css_color_formats(self, code: str) -> List[FixChange]:
        """
        Fix inconsistent CSS color formats.
        
        Args:
            code: The CSS code.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Find hex colors and normalize them
        hex_pattern = r'#([0-9a-fA-F]{3,6})\b'
        lines = code.splitlines()
        
        for i, line in enumerate(lines):
            for match in re.finditer(hex_pattern, line):
                hex_color = match.group(0)
                hex_value = match.group(1)
                
                # Normalize to lowercase
                if not hex_color.islower():
                    normalized = '#' + hex_value.lower()
                    
                    if hex_color != normalized:
                        change = FixChange(
                            description="Normalize hex color to lowercase",
                            start_line=i + 1,
                            start_column=match.start() + 1,
                            end_line=i + 1,
                            end_column=match.end() + 1,
                            original_text=hex_color,
                            replacement_text=normalized,
                            fix_type=FixType.SIMPLE
                        )
                        changes.append(change)
                
                # Convert #RGB to #RRGGBB if consistent
                if len(hex_value) == 3:
                    expanded = '#' + ''.join([c * 2 for c in hex_value.lower()])
                    
                    # Only suggest if we find another expanded hex
                    if re.search(r'#[0-9a-f]{6}\b', code):
                        change = FixChange(
                            description="Convert #RGB to #RRGGBB format",
                            start_line=i + 1,
                            start_column=match.start() + 1,
                            end_line=i + 1,
                            end_column=match.end() + 1,
                            original_text=hex_color,
                            replacement_text=expanded,
                            fix_type=FixType.SIMPLE,
                            confidence=0.7  # Lower confidence as this is just for consistency
                        )
                        changes.append(change)
        
        return changes
    
    def _fix_js_quotes(self, code: str) -> List[FixChange]:
        """
        Fix inconsistent quotes in JavaScript/TypeScript.
        
        Args:
            code: The JS/TS code.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Count single and double quotes
        double_quotes = len(re.findall(r'"[^"]*"', code))
        single_quotes = len(re.findall(r"'[^']*'", code))
        
        # Determine the dominant quote style
        use_double_quotes = double_quotes > single_quotes
        
        lines = code.splitlines()
        
        for i, line in enumerate(lines):
            # Skip comment lines
            if line.strip().startswith('//') or line.strip().startswith('/*'):
                continue
            
            # Find strings with the non-dominant quote style
            if use_double_quotes:
                # Replace single quotes with double quotes
                for match in re.finditer(r"'([^']*)'", line):
                    # Skip if the string contains double quotes
                    if '"' in match.group(1):
                        continue
                    
                    # Convert to double quotes
                    change = FixChange(
                        description="Convert single quotes to double quotes",
                        start_line=i + 1,
                        start_column=match.start() + 1,
                        end_line=i + 1,
                        end_column=match.end() + 1,
                        original_text=match.group(0),
                        replacement_text=f'"{match.group(1)}"',
                        fix_type=FixType.SIMPLE,
                        confidence=0.8
                    )
                    changes.append(change)
            else:
                # Replace double quotes with single quotes
                for match in re.finditer(r'"([^"]*)"', line):
                    # Skip if the string contains single quotes
                    if "'" in match.group(1):
                        continue
                    
                    # Convert to single quotes
                    change = FixChange(
                        description="Convert double quotes to single quotes",
                        start_line=i + 1,
                        start_column=match.start() + 1,
                        end_line=i + 1,
                        end_column=match.end() + 1,
                        original_text=match.group(0),
                        replacement_text=f"'{match.group(1)}'",
                        fix_type=FixType.SIMPLE,
                        confidence=0.8
                    )
                    changes.append(change)
        
        return changes
    
    def _fix_js_spacing(self, code: str) -> List[FixChange]:
        """
        Fix spacing issues in JavaScript/TypeScript.
        
        Args:
            code: The JS/TS code.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        lines = code.splitlines()
        
        for i, line in enumerate(lines):
            # Fix missing spaces after keywords
            for keyword in ['if', 'for', 'while', 'switch', 'catch']:
                keyword_pattern = fr'\b{keyword}(\()'
                for match in re.finditer(keyword_pattern, line):
                    change = FixChange(
                        description=f"Add space after '{keyword}' keyword",
                        start_line=i + 1,
                        start_column=match.start(1) + 1,
                        end_line=i + 1,
                        end_column=match.start(1) + 1,
                        original_text="",
                        replacement_text=" ",
                        fix_type=FixType.SIMPLE
                    )
                    changes.append(change)
            
            # Fix missing spaces around operators
            operator_pattern = r'([a-zA-Z0-9_])([\+\-\*\/\%\=\<\>\!\&\|])([a-zA-Z0-9_])'
            for match in re.finditer(operator_pattern, line):
                # Skip ++ and -- operators
                if match.group(2) in ['+', '-'] and line[match.start(2):match.start(2)+2] in ['++', '--']:
                    continue
                
                # Add spaces around the operator
                change = FixChange(
                    description=f"Add spaces around '{match.group(2)}' operator",
                    start_line=i + 1,
                    start_column=match.start(2) + 1,
                    end_line=i + 1,
                    end_column=match.start(3) + 1,
                    original_text=match.group(2),
                    replacement_text=f" {match.group(2)} ",
                    fix_type=FixType.SIMPLE
                )
                changes.append(change)
        
        return changes
    
    def _fix_invalid_html_attributes(self, code: str) -> List[FixChange]:
        """
        Fix invalid HTML attributes.
        
        Args:
            code: The HTML code.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        lines = code.splitlines()
        
        for i, line in enumerate(lines):
            # Fix attributes without values
            attr_pattern = r'(<[a-zA-Z][a-zA-Z0-9]*\s+[^>]*?)(\b[a-zA-Z][a-zA-Z0-9]*\b)(\s|>)'
            for match in re.finditer(attr_pattern, line):
                prefix = match.group(1)
                attr = match.group(2)
                suffix = match.group(3)
                
                # Skip if this is actually valid HTML5 (boolean attributes are valid)
                boolean_attrs = ['checked', 'selected', 'disabled', 'readonly', 'required', 'multiple', 'hidden', 'autofocus', 'novalidate', 'formnovalidate']
                if attr.lower() in boolean_attrs:
                    continue
                
                # Skip if it's already a properly formatted attribute
                if re.search(rf'{attr}\s*=\s*[\'"]', prefix) or re.search(rf'{attr}\s*=\s*[a-zA-Z0-9_]', prefix):
                    continue
                
                # Fix by adding ="" to the attribute
                change = FixChange(
                    description=f"Add value to attribute '{attr}'",
                    start_line=i + 1,
                    start_column=match.start(2) + 1,
                    end_line=i + 1,
                    end_column=match.end(2) + 1,
                    original_text=attr,
                    replacement_text=f'{attr}=""',
                    fix_type=FixType.SIMPLE
                )
                changes.append(change)
        
        return changes
    
    def _fix_accessibility_issues(self, code: str) -> List[FixChange]:
        """
        Fix common accessibility issues in HTML.
        
        Args:
            code: The HTML code.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        lines = code.splitlines()
        
        for i, line in enumerate(lines):
            # Fix missing alt attribute on images
            img_pattern = r'<img\s+([^>]*)(?<!\salt=[\'"][^\'"]*[\'"])(?<!\salt=[^\s>]+)(/?)>'
            for match in re.finditer(img_pattern, line):
                # Add alt attribute
                end_pos = match.end(1) + 1
                
                change = FixChange(
                    description="Add alt attribute for accessibility",
                    start_line=i + 1,
                    start_column=end_pos,
                    end_line=i + 1,
                    end_column=end_pos,
                    original_text="",
                    replacement_text=' alt="Image description"',
                    fix_type=FixType.SIMPLE
                )
                changes.append(change)
            
            # Fix missing labels for form inputs
            input_pattern = r'<input\s+([^>]*?type=[\'"](?:text|password|email|number|tel|url)[\'"][^>]*)(?<!\sid=[\'"][^\'"]*[\'"])(?<!\sid=[^\s>]+)(/?)>'
            for match in re.finditer(input_pattern, line):
                # Generate a random ID for the input
                input_id = f"input-{i}-{match.start()}"
                end_pos = match.end(1) + 1
                
                # Add id attribute
                change = FixChange(
                    description="Add id attribute for input accessibility",
                    start_line=i + 1,
                    start_column=end_pos,
                    end_line=i + 1,
                    end_column=end_pos,
                    original_text="",
                    replacement_text=f' id="{input_id}"',
                    fix_type=FixType.SIMPLE
                )
                changes.append(change)
                
                # Add a label before the input
                indent = re.match(r'^(\s*)', line).group(1)
                label_text = "Input label"
                
                # Try to infer label from nearby attributes
                attrs = match.group(1)
                name_match = re.search(r'name=[\'"]([^\'"]*)[\'"]', attrs)
                if name_match:
                    label_text = name_match.group(1).replace('-', ' ').replace('_', ' ').title()
                
                label_change = FixChange(
                    description=f"Add label for input #{input_id}",
                    start_line=i + 1,
                    start_column=match.start() + 1,
                    end_line=i + 1,
                    end_column=match.start() + 1,
                    original_text="",
                    replacement_text=f'<label for="{input_id}">{label_text}:</label>\n{indent}',
                    fix_type=FixType.SIMPLE,
                    confidence=0.7
                )
                changes.append(label_change)
        
        return changes
    
    def _fix_invalid_css_rules(self, code: str) -> List[FixChange]:
        """
        Fix invalid CSS rules.
        
        Args:
            code: The CSS code.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        lines = code.splitlines()
        
        for i, line in enumerate(lines):
            # Fix missing semicolons
            rule_pattern = r'([a-zA-Z-]+\s*:\s*[^;{}]+)(\s*})'
            for match in re.finditer(rule_pattern, line):
                # Add semicolon
                change = FixChange(
                    description="Add missing semicolon in CSS rule",
                    start_line=i + 1,
                    start_column=match.end(1) + 1,
                    end_line=i + 1,
                    end_column=match.end(1) + 1,
                    original_text="",
                    replacement_text=";",
                    fix_type=FixType.SIMPLE
                )
                changes.append(change)
            
            # Fix invalid property names (with uppercase letters)
            prop_pattern = r'([a-zA-Z-]*[A-Z][a-zA-Z-]*)\s*:'
            for match in re.finditer(prop_pattern, line):
                prop_name = match.group(1)
                lowercase_prop = prop_name.lower()
                
                # Convert to lowercase
                change = FixChange(
                    description=f"Convert CSS property '{prop_name}' to lowercase",
                    start_line=i + 1,
                    start_column=match.start(1) + 1,
                    end_line=i + 1,
                    end_column=match.end(1) + 1,
                    original_text=prop_name,
                    replacement_text=lowercase_prop,
                    fix_type=FixType.SIMPLE
                )
                changes.append(change)
        
        return changes
    
    def _fix_invalid_media_queries(self, code: str) -> List[FixChange]:
        """
        Fix invalid CSS media queries.
        
        Args:
            code: The CSS code.
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        lines = code.splitlines()
        
        for i, line in enumerate(lines):
            # Fix media queries without parentheses
            media_pattern = r'(@media\s+)([a-zA-Z-]+)(\s*{)'
            for match in re.finditer(media_pattern, line):
                media_type = match.group(2)
                
                # For standard media types, add proper parentheses
                if media_type in ['screen', 'print', 'all', 'speech']:
                    change = FixChange(
                        description=f"Fix media query syntax for '{media_type}'",
                        start_line=i + 1,
                        start_column=match.end(1) + 1,
                        end_line=i + 1,
                        end_column=match.end(2) + 1,
                        original_text=media_type,
                        replacement_text=f"all and ({media_type})",
                        fix_type=FixType.SIMPLE
                    )
                    changes.append(change)
        
        return changes
    
    def _fix_undefined_variables(self, code: str, language: str) -> List[FixChange]:
        """
        Fix potentially undefined variables in JavaScript/TypeScript.
        
        Args:
            code: The JS/TS code.
            language: "javascript" or "typescript".
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        # Find variable usages that might be undefined
        lines = code.splitlines()
        
        # Collect all defined variables
        defined_vars = set()
        
        # Look for variable declarations
        var_pattern = r'\b(var|let|const|function|class)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)'
        for line in lines:
            for match in re.finditer(var_pattern, line):
                defined_vars.add(match.group(2))
        
        # Add common globals
        globals_js = {'window', 'document', 'console', 'setTimeout', 'setInterval', 'clearTimeout', 'clearInterval',
                     'alert', 'confirm', 'prompt', 'location', 'navigator', 'history', 'Math', 'JSON', 'Date',
                     'Array', 'Object', 'String', 'Number', 'Boolean', 'RegExp', 'Error', 'Map', 'Set', 'Promise',
                     'Symbol', 'this', 'undefined', 'null', 'NaN', 'Infinity', 'isNaN', 'isFinite', 'eval',
                     'encodeURI', 'decodeURI', 'encodeURIComponent', 'decodeURIComponent'}
        
        defined_vars.update(globals_js)
        
        # Look for variable usages
        for i, line in enumerate(lines):
            # Skip comment lines
            if line.strip().startswith('//') or line.strip().startswith('/*'):
                continue
            
            # Find variable usages
            usage_pattern = r'\b([a-zA-Z_$][a-zA-Z0-9_$]*)\b(?!\s*[:,\.]|[\(:])'
            for match in re.finditer(usage_pattern, line):
                var_name = match.group(1)
                
                # Skip keywords and in operators
                if var_name in {'if', 'else', 'for', 'while', 'switch', 'case', 'break', 'continue', 'return',
                              'function', 'var', 'let', 'const', 'class', 'new', 'this', 'typeof', 'instanceof',
                              'in', 'of', 'true', 'false', 'null', 'undefined', 'try', 'catch', 'finally'}:
                    continue
                
                # Check if variable might be undefined
                if var_name not in defined_vars:
                    # Suggest declaring the variable
                    if language == "typescript":
                        declaration = f"let {var_name}: any; // TODO: Define variable"
                    else:
                        declaration = f"let {var_name}; // TODO: Define variable"
                    
                    change = FixChange(
                        description=f"Declare potentially undefined variable '{var_name}'",
                        start_line=1,
                        start_column=1,
                        end_line=1,
                        end_column=1,
                        original_text="",
                        replacement_text=f"{declaration}\n",
                        fix_type=FixType.COMPLEX,
                        confidence=0.6  # Lower confidence since this is a heuristic
                    )
                    changes.append(change)
                    
                    # Add to defined vars to avoid duplicate suggestions
                    defined_vars.add(var_name)
        
        return changes
    
    def _fix_potential_null_refs(self, code: str, language: str) -> List[FixChange]:
        """
        Fix potential null reference issues in JavaScript/TypeScript.
        
        Args:
            code: The JS/TS code.
            language: "javascript" or "typescript".
        
        Returns:
            List of FixChange objects with changes to apply.
        """
        changes = []
        
        lines = code.splitlines()
        
        for i, line in enumerate(lines):
            # Skip comment lines
            if line.strip().startswith('//') or line.strip().startswith('/*'):
                continue
            
            # Find potential null references (obj.prop without null check)
            ref_pattern = r'(\b[a-zA-Z_$][a-zA-Z0-9_$]*)(\.)[a-zA-Z_$][a-zA-Z0-9_$]*\b'
            for match in re.finditer(ref_pattern, line):
                obj_name = match.group(1)
                
                # Skip references to common globals that shouldn't be null
                if obj_name in {'window', 'document', 'console', 'Math', 'JSON', 'Object', 'Array', 'String'}:
                    continue
                
                # Check if there's a null check already in this line or nearby
                null_check_pattern = fr'(if\s*\(\s*{re.escape(obj_name)}\s*[!=]=|{re.escape(obj_name)}\s*(\?\.|&&))'
                has_null_check = False
                
                # Check current line
                if re.search(null_check_pattern, line):
                    has_null_check = True
                
                # Check previous line
                if i > 0 and re.search(null_check_pattern, lines[i-1]):
                    has_null_check = True
                
                if not has_null_check:
                    # Suggest adding a null check
                    if "?" in line:
                        # Already using optional chaining (ES2020)?
                        replacement_text = f"{obj_name}?."
                    else:
                        replacement_text = f"{obj_name} && {obj_name}."
                    
                    change = FixChange(
                        description=f"Add null check for '{obj_name}'",
                        start_line=i + 1,
                        start_column=match.start(1) + 1,
                        end_line=i + 1,
                        end_column=match.end(2) + 1,
                        original_text=f"{obj_name}.",
                        replacement_text=replacement_text,
                        fix_type=FixType.SIMPLE,
                        confidence=0.7  # Lower confidence since this is a heuristic
                    )
                    changes.append(change)
        
        return changes
    
    def _reindent_html(self, code: str) -> str:
        """
        Re-indent HTML code for proper formatting.
        
        Args:
            code: The HTML code.
        
        Returns:
            The re-indented code.
        """
        lines = code.splitlines()
        result = []
        indent = 0
        indent_size = 2
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                result.append('')
                continue
            
            # Check for closing tags at the beginning
            if stripped.startswith('</'):
                indent -= 1
            
            # Add line with proper indentation
            result.append(' ' * (indent * indent_size) + stripped)
            
            # Check for opening tags (that aren't self-closing)
            if stripped.startswith('<') and not stripped.startswith('</') and not stripped.endswith('/>'):
                # Check if it's a void element that doesn't need a closing tag
                tag_match = re.match(r'<([a-zA-Z][a-zA-Z0-9]*)', stripped)
                if tag_match:
                    tag = tag_match.group(1).lower()
                    void_elements = ['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr']
                    
                    if tag not in void_elements:
                        indent += 1
            
            # Check for closing tag at the end
            if stripped.endswith('</'):
                indent -= 1
        
        return '\n'.join(result)
    
    def _reformat_css(self, code: str) -> str:
        """
        Reformat CSS code for proper indentation and spacing.
        
        Args:
            code: The CSS code.
        
        Returns:
            The reformatted code.
        """
        # Basic formatter - insert proper spacing and line breaks
        code = re.sub(r'\s*{\s*', ' {\n  ', code)
        code = re.sub(r';\s*', ';\n  ', code)
        code = re.sub(r'\s*}\s*', '\n}\n\n', code)
        
        # Remove excess new lines
        code = re.sub(r'\n{3,}', '\n\n', code)
        
        return code
    
    async def _get_llm_suggestions(self, code: str, issue: Dict[str, Any], language: str, 
                                 file_path: Optional[str] = None) -> List[FixChange]:
        """
        Get suggestions for fixing an issue using LLM.
        
        Args:
            code: The code containing the issue.
            issue: The issue to fix.
            language: The code language.
            file_path: Optional path to the file.
        
        Returns:
            List of FixChange objects with suggestions.
        """
        changes = []
        
        if not self.llm:
            return changes
        
        try:
            # Extract issue details
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
            prompt = f"""I have a {language.upper()} code issue to fix. Here's the issue:

- Rule ID: {rule_id}
- Message: {message}
- Description: {description}
- Line number: {line}

Here's the relevant code (line {line} is where the issue is):

```{language}
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
            suggestion = await self.llm.suggest_refactoring(code, language, prompt)
            
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
    # Simple test for the Web fixer
    import asyncio
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    async def main():
        # Create the Web fixer
        fixer = WebFixer()
        
        # Test HTML code
        html_code = """<!doctype html>
<html>
<head>
    <title>Test Page</title>
</head>
<BODY>
    <div CLASS="container">
        <h1>Welcome</h1>
        <img src="logo.png">
        <form>
            <input type="text" name="username">
            <input type="password">
            <button>Submit</button>
        </form>
    </div>
</BODY>
</html>"""
        
        # Test CSS code
        css_code = """body {
    background-color: #FFF;
    Color: #333;
}
.container {
    width: 800px;
    margin: 0 auto;
}
h1 {
    font-family: Arial;
    font-size: 24px
}
"""
        
        # Test JavaScript code
        js_code = """function validateForm() {
    var username = document.getElementById('username')
    var password = document.getElementById('password')
    
    if (username.value == "") {
        alert("Username is required");
        return false;
    }
    
    if (password.value == "") {
        alert("Password is required");
        return false
    }
    
    return true
}"""
        
        # Fix the code
        html_result = await fixer.fix_code(html_code)
        css_result = await fixer.fix_code(css_code)
        js_result = await fixer.fix_code(js_code)
        
        # Display the results
        print("HTML Fixes:")
        print("Original code:")
        print(html_result.original_code)
        print("\nFixed code:")
        print(html_result.fixed_code)
        print("\nChanges:")
        for change in html_result.changes:
            print(f"- {change.description}: Line {change.start_line}, Col {change.start_column}")
        
        print("\nCSS Fixes:")
        print("Original code:")
        print(css_result.original_code)
        print("\nFixed code:")
        print(css_result.fixed_code)
        print("\nChanges:")
        for change in css_result.changes:
            print(f"- {change.description}: Line {change.start_line}, Col {change.start_column}")
        
        print("\nJavaScript Fixes:")
        print("Original code:")
        print(js_result.original_code)
        print("\nFixed code:")
        print(js_result.fixed_code)
        print("\nChanges:")
        for change in js_result.changes:
            print(f"- {change.description}: Line {change.start_line}, Col {change.start_column}")
    
    # Run the test
    asyncio.run(main())