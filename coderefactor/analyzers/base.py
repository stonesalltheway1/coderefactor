#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Base Analyzer Interface: Abstract base class for all code analyzers.
Defines the common interface that all language-specific analyzers must implement.
"""

import abc
import os
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple, Union
import uuid

# Import models from utils
from .utils.models import AnalysisResult, AnalysisIssue, IssueSeverity, IssueCategory


class BaseAnalyzer(abc.ABC):
    """
    Abstract base class for all code analyzers.
    
    This class defines the common interface that all language-specific analyzers
    must implement. It also provides some common utility methods that can be
    reused by subclasses.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the analyzer with optional configuration.
        
        Args:
            config: Configuration dictionary for this analyzer
        """
        self.config = config or {}
        self.logger = logging.getLogger(f"coderefactor.{self.__class__.__name__.lower()}")
    
    @abc.abstractmethod
    def analyze_file(self, file_path: str) -> AnalysisResult:
        """
        Analyze a single file.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            AnalysisResult containing detected issues
        """
        pass
    
    @abc.abstractmethod
    def analyze_string(self, code: str, filename: Optional[str] = None) -> AnalysisResult:
        """
        Analyze code from a string.
        
        Args:
            code: The code to analyze
            filename: Optional filename to pass to the analyzer
            
        Returns:
            AnalysisResult containing detected issues
        """
        pass
    
    def analyze_directory(self, dir_path: str, recursive: bool = True, pattern: Optional[str] = None) -> Dict[str, AnalysisResult]:
        """
        Analyze all supported files in a directory.
        
        Args:
            dir_path: Path to the directory
            recursive: Whether to analyze subdirectories
            pattern: Optional glob pattern to filter files
            
        Returns:
            Dictionary mapping file paths to AnalysisResults
        """
        results = {}
        dir_path = Path(dir_path)
        
        if not dir_path.is_dir():
            self.logger.error(f"Directory not found: {dir_path}")
            return results
        
        # Get file extensions supported by this analyzer
        extensions = self.get_supported_extensions()
        
        # Get files to analyze
        files_to_analyze = self._find_files(dir_path, extensions, recursive, pattern)
        
        # Analyze each file
        for file_path in files_to_analyze:
            try:
                self.logger.debug(f"Analyzing {file_path}")
                results[str(file_path)] = self.analyze_file(str(file_path))
            except Exception as e:
                self.logger.error(f"Error analyzing {file_path}: {str(e)}")
                # Create an error result
                results[str(file_path)] = AnalysisResult(
                    file_path=str(file_path),
                    error=f"Analysis failed: {str(e)}"
                )
        
        return results
    
    @abc.abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """
        Get file extensions supported by this analyzer.
        
        Returns:
            List of supported file extensions (e.g. ['.py', '.pyi'])
        """
        pass
    
    def _find_files(self, dir_path: Path, extensions: List[str], recursive: bool = True, pattern: Optional[str] = None) -> List[Path]:
        """
        Find files with the given extensions in a directory.
        
        Args:
            dir_path: Path to the directory
            extensions: List of file extensions to include
            recursive: Whether to search in subdirectories
            pattern: Optional glob pattern to filter files
            
        Returns:
            List of file paths
        """
        files = []
        
        # Use glob if pattern is specified
        if pattern:
            if recursive:
                glob_pattern = f"**/{pattern}"
            else:
                glob_pattern = pattern
            
            for path in dir_path.glob(glob_pattern):
                if path.is_file() and path.suffix in extensions:
                    files.append(path)
        else:
            # Otherwise use os.walk
            for root, _, filenames in os.walk(dir_path):
                # Skip if not recursive and not in the root directory
                if not recursive and Path(root) != dir_path:
                    continue
                
                for filename in filenames:
                    file_path = Path(root) / filename
                    if file_path.suffix in extensions:
                        files.append(file_path)
        
        return files
    
    def extract_code_snippet(self, file_path: str, line: int, context_lines: int = 2) -> str:
        """
        Extract a code snippet from a file with context lines.
        
        Args:
            file_path: Path to the file
            line: Line number to extract (1-based)
            context_lines: Number of context lines before and after
            
        Returns:
            Code snippet as a string
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Adjust line number to 0-based index
            line_idx = line - 1
            
            # Calculate start and end line indices
            start_line = max(0, line_idx - context_lines)
            end_line = min(len(lines), line_idx + context_lines + 1)
            
            # Extract and join the lines
            snippet = ''.join(lines[start_line:end_line])
            
            return snippet
        except Exception as e:
            self.logger.debug(f"Error extracting code snippet: {str(e)}")
            return f"<Error extracting code snippet: {str(e)}>"
    
    def get_line_column(self, content: str, position: int) -> Tuple[int, int]:
        """
        Convert a character position to line and column numbers.
        
        Args:
            content: The source code text
            position: Character position in the text
            
        Returns:
            Tuple of (line, column) numbers (1-based)
        """
        if position > len(content):
            raise ValueError(f"Position {position} is out of range for content of length {len(content)}")
        
        # Get the text up to the position
        text_before = content[:position]
        
        # Count the newlines to get the line number
        line = text_before.count('\n') + 1
        
        # Find the last newline before the position
        last_newline = text_before.rfind('\n')
        
        # Calculate the column (characters after the last newline)
        column = position - last_newline if last_newline >= 0 else position + 1
        
        return line, column
    
    def create_temp_file(self, content: str, suffix: Optional[str] = None) -> str:
        """
        Create a temporary file with the given content.
        
        Args:
            content: Content to write to the file
            suffix: Optional file extension
            
        Returns:
            Path to the temporary file
        """
        suffix = suffix or '.tmp'
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            f.write(content.encode('utf-8'))
            return f.name
    
    def find_tool_executable(self, tool_name: str) -> Optional[str]:
        """
        Find the executable path for a tool.
        
        Args:
            tool_name: Name of the tool executable
            
        Returns:
            Path to the executable or None if not found
        """
        import shutil
        
        # Try to find the executable in PATH
        executable = shutil.which(tool_name)
        
        # Try to find via npx for Node.js tools
        if not executable:
            npx_path = shutil.which('npx')
            if npx_path:
                try:
                    result = subprocess.run(
                        [npx_path, '--no-install', tool_name, '--version'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=2
                    )
                    if result.returncode == 0:
                        # Tool is available via npx
                        return f"npx {tool_name}"
                except Exception:
                    pass
        
        return executable
    
    def categorize_issue(self, issue_type: str, rule_id: str) -> IssueCategory:
        """
        Categorize an issue based on type and rule ID.
        
        Args:
            issue_type: The type of issue (e.g., 'error', 'warning', 'info')
            rule_id: The rule identifier
            
        Returns:
            Appropriate IssueCategory value
        """
        # Common keywords for categorizing issues
        keywords = {
            "security": IssueCategory.SECURITY,
            "performance": IssueCategory.PERFORMANCE,
            "maintainability": IssueCategory.MAINTAINABILITY,
            "complexity": IssueCategory.COMPLEXITY,
            "style": IssueCategory.STYLE,
            "typing": IssueCategory.TYPING,
            "error": IssueCategory.ERROR
        }
        
        # Check rule_id for keywords
        rule_lower = rule_id.lower()
        for keyword, category in keywords.items():
            if keyword in rule_lower:
                return category
        
        # Check issue_type for keywords
        type_lower = issue_type.lower()
        for keyword, category in keywords.items():
            if keyword in type_lower:
                return category
        
        # Default to style for minor issues, error for more severe ones
        if issue_type.lower() in ['info', 'convention', 'refactor']:
            return IssueCategory.STYLE
        elif issue_type.lower() in ['error', 'fatal']:
            return IssueCategory.ERROR
        else:
            return IssueCategory.MAINTAINABILITY
    
    def determine_severity(self, severity_str: str) -> IssueSeverity:
        """
        Convert a string severity level to an IssueSeverity enum value.
        
        Args:
            severity_str: String representation of severity
            
        Returns:
            Appropriate IssueSeverity value
        """
        severity_map = {
            "critical": IssueSeverity.CRITICAL,
            "error": IssueSeverity.ERROR,
            "fatal": IssueSeverity.ERROR,
            "warning": IssueSeverity.WARNING,
            "warn": IssueSeverity.WARNING,
            "info": IssueSeverity.INFO,
            "information": IssueSeverity.INFO,
            "convention": IssueSeverity.INFO,
            "refactor": IssueSeverity.INFO,
            "hint": IssueSeverity.INFO
        }
        
        # Normalize and look up in map
        normalized = severity_str.lower().strip()
        return severity_map.get(normalized, IssueSeverity.WARNING)


# Utility functions that may be useful to analyzer implementations
def merge_analysis_results(results: List[AnalysisResult]) -> AnalysisResult:
    """
    Merge multiple analysis results into one.
    
    Args:
        results: List of results to merge
        
    Returns:
        Combined AnalysisResult
    """
    if not results:
        return AnalysisResult(file_path="")
    
    # Use first result as base
    merged = AnalysisResult(
        file_path=results[0].file_path,
        issues=[],
        error=None
    )
    
    # Gather all issues
    for result in results:
        merged.issues.extend(result.issues)
    
    # Collect errors
    errors = [r.error for r in results if r.error]
    if errors:
        merged.error = "; ".join(errors)
    
    return merged


def deduplicate_issues(issues: List[AnalysisIssue]) -> List[AnalysisIssue]:
    """
    Remove duplicate issues based on location and message.
    
    Args:
        issues: List of issues to deduplicate
        
    Returns:
        Deduplicated list of issues
    """
    seen = set()
    unique_issues = []
    
    for issue in issues:
        # Create a key based on location and message
        key = (
            issue.file_path,
            issue.line,
            issue.column,
            issue.message
        )
        
        if key not in seen:
            seen.add(key)
            unique_issues.append(issue)
    
    return unique_issues#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Base Analyzer Interface: Abstract base class for all code analyzers.
Defines the common interface that all language-specific analyzers must implement.
"""

import abc
from typing import Dict, Any, List, Optional
from pathlib import Path

from .utils.models import AnalysisResult


class BaseAnalyzer(abc.ABC):
    """Abstract base class for code analyzers."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the analyzer with optional configuration.
        
        Args:
            config: Configuration dictionary for this analyzer
        """
        self.config = config or {}
    
    @abc.abstractmethod
    def analyze_file(self, file_path: str) -> AnalysisResult:
        """
        Analyze a single file.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            AnalysisResult containing detected issues
        """
        pass
    
    @abc.abstractmethod
    def analyze_string(self, code: str, filename: Optional[str] = None) -> AnalysisResult:
        """
        Analyze code from a string.
        
        Args:
            code: The code to analyze
            filename: Optional filename to pass to the analyzer
            
        Returns:
            AnalysisResult containing detected issues
        """
        pass
    
    def analyze_directory(self, dir_path: str, recursive: bool = True) -> Dict[str, AnalysisResult]:
        """
        Analyze all supported files in a directory.
        
        Args:
            dir_path: Path to the directory
            recursive: Whether to analyze subdirectories
            
        Returns:
            Dictionary mapping file paths to AnalysisResults
        """
        results = {}
        dir_path = Path(dir_path)
        
        if not dir_path.is_dir():
            return results
        
        # Get file extensions supported by this analyzer
        extensions = self.get_supported_extensions()
        
        # Helper function to find and analyze files
        def process_directory(path):
            for item in path.iterdir():
                if item.is_file() and item.suffix.lower() in extensions:
                    results[str(item)] = self.analyze_file(str(item))
                elif recursive and item.is_dir():
                    process_directory(item)
        
        process_directory(dir_path)
        return results
    
    @abc.abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """
        Get file extensions supported by this analyzer.
        
        Returns:
            List of supported file extensions (e.g. ['.py', '.pyi'])
        """
        pass
