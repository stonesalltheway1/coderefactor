"""
Tests for the Python code analyzer.
"""
import os
import sys
import pytest
from pathlib import Path
from typing import Dict, List, Any

from coderefactor.analyzers.python_analyzer import PythonAnalyzer
from coderefactor.analyzers.utils.models import AnalysisResult, AnalysisIssue, IssueSeverity, IssueCategory


class TestPythonAnalyzer:
    """Test suite for the PythonAnalyzer class."""

    def test_initialization(self, python_analyzer):
        """Test that the analyzer initializes properly."""
        assert python_analyzer is not None
        assert isinstance(python_analyzer, PythonAnalyzer)
        assert hasattr(python_analyzer, "analyze_file")
        assert hasattr(python_analyzer, "analyze_string")
        assert hasattr(python_analyzer, "analyze_directory")

    def test_supported_extensions(self, python_analyzer):
        """Test that the supported extensions are correct."""
        extensions = python_analyzer.get_supported_extensions()
        assert isinstance(extensions, list)
        assert ".py" in extensions
        assert ".pyi" in extensions

    def test_check_available_tools(self, python_analyzer):
        """Test that the available tools are detected correctly."""
        available_tools = python_analyzer._check_available_tools()
        assert isinstance(available_tools, set)
        # At minimum, AST should always be available as it's built in
        assert "ast" in available_tools

    def test_analyze_string(self, python_analyzer, sample_python_code):
        """Test analyzing code from a string."""
        result = python_analyzer.analyze_string(sample_python_code)
        assert isinstance(result, AnalysisResult)
        assert result.file_path == ""  # No filename provided
        assert len(result.issues) > 0
        assert result.error is None

        # Check that at least the obvious issues were detected
        issues_by_id = {issue.rule_id: issue for issue in result.issues}
        
        # Should detect unused import
        assert any(issue.rule_id.startswith("W0611") for issue in result.issues)
        
        # Should detect unused variable
        assert any(issue.rule_id.startswith("W0612") for issue in result.issues)

    def test_analyze_string_with_filename(self, python_analyzer, sample_python_code):
        """Test analyzing code from a string with a filename."""
        result = python_analyzer.analyze_string(sample_python_code, filename="test_file.py")
        assert isinstance(result, AnalysisResult)
        assert result.file_path == "test_file.py"
        assert len(result.issues) > 0
        assert result.error is None

    def test_analyze_file(self, python_analyzer, python_fixtures_dir):
        """Test analyzing code from a file."""
        file_path = python_fixtures_dir / "simple.py"
        result = python_analyzer.analyze_file(str(file_path))
        assert isinstance(result, AnalysisResult)
        assert result.file_path == str(file_path)
        assert result.error is None

    def test_analyze_nonexistent_file(self, python_analyzer):
        """Test analyzing a nonexistent file."""
        result = python_analyzer.analyze_file("nonexistent_file.py")
        assert isinstance(result, AnalysisResult)
        assert result.file_path == "nonexistent_file.py"
        assert result.error is not None
        assert "not found" in result.error.lower() or "does not exist" in result.error.lower()

    def test_analyze_directory(self, python_analyzer, python_fixtures_dir):
        """Test analyzing all files in a directory."""
        results = python_analyzer.analyze_directory(str(python_fixtures_dir))
        assert isinstance(results, dict)
        assert len(results) > 0
        for file_path, result in results.items():
            assert isinstance(result, AnalysisResult)
            assert result.file_path == file_path

    def test_analyze_directory_recursive(self, python_analyzer, fixtures_dir):
        """Test analyzing all files in a directory recursively."""
        # Create a nested directory for testing
        nested_dir = fixtures_dir / "python" / "nested"
        nested_dir.mkdir(exist_ok=True)
        nested_file = nested_dir / "nested_test.py"
        with open(nested_file, "w") as f:
            f.write("# This is a nested test file\nx = 1\n")

        try:
            results = python_analyzer.analyze_directory(str(fixtures_dir / "python"), recursive=True)
            assert isinstance(results, dict)
            assert len(results) > 0
            
            # Should find the nested file
            nested_file_path = str(nested_file)
            assert nested_file_path in results
            assert isinstance(results[nested_file_path], AnalysisResult)
            
            # Try with recursive=False
            non_recursive_results = python_analyzer.analyze_directory(
                str(fixtures_dir / "python"), recursive=False
            )
            assert nested_file_path not in non_recursive_results
            
        finally:
            # Clean up the nested file and directory
            if nested_file.exists():
                nested_file.unlink()
            if nested_dir.exists():
                nested_dir.rmdir()

    def test_analyze_directory_with_pattern(self, python_analyzer, fixtures_dir):
        """Test analyzing files in a directory with a pattern."""
        # First ensure we have at least two files with different patterns
        simple_file = fixtures_dir / "python" / "simple.py"
        complex_file = fixtures_dir / "python" / "complex.py"
        
        with open(simple_file, "w") as f:
            f.write("# This is a simple test file\nx = 1\n")
        
        with open(complex_file, "w") as f:
            f.write("# This is a complex test file\ny = 2\n")
        
        try:
            # Use a pattern that only matches simple.py
            results = python_analyzer.analyze_directory(
                str(fixtures_dir / "python"), pattern="simple*.py"
            )
            assert isinstance(results, dict)
            assert str(simple_file) in results
            assert str(complex_file) not in results
            
            # Use a pattern that matches both files
            results = python_analyzer.analyze_directory(
                str(fixtures_dir / "python"), pattern="*.py"
            )
            assert str(simple_file) in results
            assert str(complex_file) in results
            
        finally:
            # Clean up files if needed
            pass  # Let the fixtures handle cleanup

    def test_issue_classification(self, python_analyzer):
        """Test classification of issues by category."""
        # Create some test issues
        issue_types = [
            ("error", "syntax-error", IssueCategory.ERROR),
            ("warning", "undefined-variable", IssueCategory.ERROR),
            ("warning", "unused-variable", IssueCategory.MAINTAINABILITY),
            ("convention", "missing-docstring", IssueCategory.STYLE),
            ("refactor", "duplicate-code", IssueCategory.MAINTAINABILITY),
            ("info", "todo-comment", IssueCategory.STYLE),
        ]
        
        for issue_type, rule_id, expected_category in issue_types:
            category = python_analyzer._categorize_issue(issue_type, rule_id)
            assert category == expected_category, f"Failed for {issue_type}, {rule_id}"

    def test_severity_determination(self, python_analyzer):
        """Test determination of issue severity."""
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
            "hint": IssueSeverity.INFO,
        }
        
        for severity_str, expected_severity in severity_map.items():
            severity = python_analyzer._determine_severity(severity_str)
            assert severity == expected_severity, f"Failed for {severity_str}"

    def test_extract_code_snippet(self, python_analyzer, sample_python_code, tmp_path):
        """Test extraction of code snippet from a file."""
        # Write the sample code to a temporary file
        file_path = tmp_path / "test_snippet.py"
        with open(file_path, "w") as f:
            f.write(sample_python_code)
        
        # Extract a snippet from line 2 (the function comment)
        snippet = python_analyzer.extract_code_snippet(str(file_path), 2, context_lines=1)
        assert "def example_function" in snippet
        assert "# This function adds two numbers" in snippet
        assert "return x + y" in snippet
        
        # Check that the context lines parameter works
        narrow_snippet = python_analyzer.extract_code_snippet(str(file_path), 2, context_lines=0)
        assert "def example_function" not in narrow_snippet
        assert "# This function adds two numbers" in narrow_snippet
        assert "return x + y" not in narrow_snippet

    def test_get_line_column(self, python_analyzer, sample_python_code):
        """Test conversion of position to line and column."""
        # Find the position of "unused_var"
        pos = sample_python_code.find("unused_var")
        assert pos > 0
        
        line, column = python_analyzer.get_line_column(sample_python_code, pos)
        assert line == 9  # Line number (1-based)
        assert column > 0  # Column number (1-based)

    def test_create_temp_file(self, python_analyzer, sample_python_code):
        """Test creation of a temporary file."""
        temp_file = python_analyzer.create_temp_file(sample_python_code, suffix=".py")
        try:
            assert os.path.exists(temp_file)
            assert temp_file.endswith(".py")
            
            # Check that the content was written correctly
            with open(temp_file, "r") as f:
                content = f.read()
            assert content == sample_python_code
            
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    # Test the specialized analyzer methods
    def test_analyze_with_pylint(self, python_analyzer, sample_python_code):
        """Test pylint analysis."""
        if "pylint" not in python_analyzer.available_tools:
            pytest.skip("pylint not available")
        
        issues = python_analyzer._analyze_with_pylint(sample_python_code, filename="test.py")
        assert isinstance(issues, list)
        assert any(issue.rule_id == "W0611" for issue in issues)  # Unused import
        assert any(issue.rule_id == "W0612" for issue in issues)  # Unused variable

    def test_analyze_with_mypy(self, python_analyzer, sample_python_code):
        """Test mypy analysis."""
        if "mypy" not in python_analyzer.available_tools:
            pytest.skip("mypy not available")
        
        issues = python_analyzer._analyze_with_mypy(sample_python_code, filename="test.py")
        assert isinstance(issues, list)
        # No type errors in our sample code

    def test_analyze_with_flake8(self, python_analyzer, sample_python_code):
        """Test flake8 analysis."""
        if "flake8" not in python_analyzer.available_tools:
            pytest.skip("flake8 not available")
        
        issues = python_analyzer._analyze_with_flake8(sample_python_code, filename="test.py")
        assert isinstance(issues, list)
        # Should find at least the unused import
        assert any("F401" in issue.rule_id for issue in issues)

    def test_analyze_with_bandit(self, python_analyzer, sample_python_code):
        """Test bandit security analysis."""
        if "bandit" not in python_analyzer.available_tools:
            pytest.skip("bandit not available")
        
        issues = python_analyzer._analyze_with_bandit(sample_python_code, filename="test.py")
        assert isinstance(issues, list)
        # No security issues in our sample code

    def test_analyze_with_ast(self, python_analyzer, sample_python_code):
        """Test AST-based analysis."""
        issues = python_analyzer._analyze_with_ast(sample_python_code, filename="test.py")
        assert isinstance(issues, list)
        # AST analysis should detect at least the missing docstring
        assert any("missing-docstring" in issue.rule_id for issue in issues)