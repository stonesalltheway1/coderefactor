"""
Tests for the C# code analyzer.
"""
import os
import sys
import pytest
from pathlib import Path
from typing import Dict, List, Any, Optional

from coderefactor.analyzers.utils.models import AnalysisResult, AnalysisIssue, IssueSeverity, IssueCategory


class TestCSharpAnalyzer:
    """Test suite for the CSharpAnalyzer class."""

    def test_initialization(self, csharp_analyzer):
        """Test that the analyzer initializes properly."""
        if csharp_analyzer is None:
            pytest.skip("C# analyzer not available")
        
        assert csharp_analyzer is not None
        assert hasattr(csharp_analyzer, "analyze_file")
        assert hasattr(csharp_analyzer, "analyze_string")
        assert hasattr(csharp_analyzer, "analyze_directory")

    def test_supported_extensions(self, csharp_analyzer):
        """Test that the supported extensions are correct."""
        if csharp_analyzer is None:
            pytest.skip("C# analyzer not available")
        
        extensions = csharp_analyzer.get_supported_extensions()
        assert isinstance(extensions, list)
        assert ".cs" in extensions

    def test_analyze_string(self, csharp_analyzer, sample_csharp_code):
        """Test analyzing C# code from a string."""
        if csharp_analyzer is None:
            pytest.skip("C# analyzer not available")
        
        result = csharp_analyzer.analyze_string(sample_csharp_code)
        assert isinstance(result, AnalysisResult)
        assert result.file_path == ""  # No filename provided
        assert result.error is None

        # Check that at least some issues were detected
        assert len(result.issues) > 0
        
        # Check that common issues were found
        rule_ids = [issue.rule_id for issue in result.issues]
        
        # Might find unused using directive
        found_unused_using = any(
            "CS0105" in rule_id or "CS0168" in rule_id for rule_id in rule_ids
        )
        
        # Might find unused field
        found_unused_field = any("CS0649" in rule_id for rule_id in rule_ids)
        
        # Might find unused variable
        found_unused_var = any(
            "CS0168" in rule_id or "CS0219" in rule_id for rule_id in rule_ids
        )
        
        # Should find at least one of these issues
        assert found_unused_using or found_unused_field or found_unused_var, \
            f"No common issues found in: {rule_ids}"

    def test_analyze_string_with_filename(self, csharp_analyzer, sample_csharp_code):
        """Test analyzing C# code from a string with a filename."""
        if csharp_analyzer is None:
            pytest.skip("C# analyzer not available")
        
        result = csharp_analyzer.analyze_string(sample_csharp_code, filename="test_file.cs")
        assert isinstance(result, AnalysisResult)
        assert result.file_path == "test_file.cs"
        assert result.error is None

    def test_analyze_file(self, csharp_analyzer, csharp_fixtures_dir):
        """Test analyzing C# code from a file."""
        if csharp_analyzer is None:
            pytest.skip("C# analyzer not available")
        
        file_path = csharp_fixtures_dir / "simple.cs"
        if not file_path.exists():
            pytest.skip(f"Test file not found: {file_path}")
        
        result = csharp_analyzer.analyze_file(str(file_path))
        assert isinstance(result, AnalysisResult)
        assert result.file_path == str(file_path)
        assert result.error is None

    def test_analyze_nonexistent_file(self, csharp_analyzer):
        """Test analyzing a nonexistent C# file."""
        if csharp_analyzer is None:
            pytest.skip("C# analyzer not available")
        
        result = csharp_analyzer.analyze_file("nonexistent_file.cs")
        assert isinstance(result, AnalysisResult)
        assert result.file_path == "nonexistent_file.cs"
        assert result.error is not None
        assert "not found" in result.error.lower() or "does not exist" in result.error.lower()

    def test_analyze_directory(self, csharp_analyzer, csharp_fixtures_dir):
        """Test analyzing all C# files in a directory."""
        if csharp_analyzer is None:
            pytest.skip("C# analyzer not available")
        
        # Ensure there's at least one .cs file in the directory
        if not any(f.suffix == ".cs" for f in csharp_fixtures_dir.iterdir() if f.is_file()):
            pytest.skip("No C# test files found in fixtures directory")
        
        results = csharp_analyzer.analyze_directory(str(csharp_fixtures_dir))
        assert isinstance(results, dict)
        assert len(results) > 0
        for file_path, result in results.items():
            assert isinstance(result, AnalysisResult)
            assert result.file_path == file_path

    def test_analyze_directory_recursive(self, csharp_analyzer, fixtures_dir):
        """Test analyzing all C# files in a directory recursively."""
        if csharp_analyzer is None:
            pytest.skip("C# analyzer not available")
        
        # Create a nested directory for testing
        nested_dir = fixtures_dir / "csharp" / "nested"
        nested_dir.mkdir(exist_ok=True)
        nested_file = nested_dir / "nested_test.cs"
        with open(nested_file, "w") as f:
            f.write("""using System;
namespace Test {
    class NestedTest {
        static void Main() {
            Console.WriteLine("Hello");
        }
    }
}
""")

        try:
            results = csharp_analyzer.analyze_directory(
                str(fixtures_dir / "csharp"), recursive=True
            )
            assert isinstance(results, dict)
            assert len(results) > 0
            
            # Should find the nested file
            nested_file_path = str(nested_file)
            assert nested_file_path in results
            assert isinstance(results[nested_file_path], AnalysisResult)
            
            # Try with recursive=False
            non_recursive_results = csharp_analyzer.analyze_directory(
                str(fixtures_dir / "csharp"), recursive=False
            )
            assert nested_file_path not in non_recursive_results
            
        finally:
            # Clean up the nested file and directory
            if nested_file.exists():
                nested_file.unlink()
            if nested_dir.exists():
                nested_dir.rmdir()

    def test_analyze_directory_with_pattern(self, csharp_analyzer, fixtures_dir):
        """Test analyzing C# files in a directory with a pattern."""
        if csharp_analyzer is None:
            pytest.skip("C# analyzer not available")
        
        # First ensure we have at least two files with different patterns
        simple_file = fixtures_dir / "csharp" / "simple.cs"
        complex_file = fixtures_dir / "csharp" / "complex.cs"
        
        with open(simple_file, "w") as f:
            f.write("""using System;
namespace Test {
    class SimpleTest {
        static void Main() {
            Console.WriteLine("Simple");
        }
    }
}
""")
        
        with open(complex_file, "w") as f:
            f.write("""using System;
namespace Test {
    class ComplexTest {
        static void Main() {
            Console.WriteLine("Complex");
        }
    }
}
""")
        
        try:
            # Use a pattern that only matches simple.cs
            results = csharp_analyzer.analyze_directory(
                str(fixtures_dir / "csharp"), pattern="simple*.cs"
            )
            assert isinstance(results, dict)
            assert str(simple_file) in results
            assert str(complex_file) not in results
            
            # Use a pattern that matches both files
            results = csharp_analyzer.analyze_directory(
                str(fixtures_dir / "csharp"), pattern="*.cs"
            )
            assert str(simple_file) in results
            assert str(complex_file) in results
            
        finally:
            # Clean up files if needed
            pass  # Let the fixtures handle cleanup

    def test_extract_code_snippet(self, csharp_analyzer, sample_csharp_code, tmp_path):
        """Test extraction of code snippet from a C# file."""
        if csharp_analyzer is None:
            pytest.skip("C# analyzer not available")
        
        # Write the sample code to a temporary file
        file_path = tmp_path / "test_snippet.cs"
        with open(file_path, "w") as f:
            f.write(sample_csharp_code)
        
        # Extract a snippet from a line with the TestMethod
        line_number = 0
        for i, line in enumerate(sample_csharp_code.splitlines(), 1):
            if "TestMethod" in line:
                line_number = i
                break
        
        assert line_number > 0, "TestMethod not found in sample code"
        
        snippet = csharp_analyzer.extract_code_snippet(str(file_path), line_number, context_lines=1)
        assert "TestMethod" in snippet
        
        # Check that the context lines parameter works
        wide_snippet = csharp_analyzer.extract_code_snippet(str(file_path), line_number, context_lines=2)
        assert len(wide_snippet.splitlines()) > len(snippet.splitlines())

    def test_get_line_column(self, csharp_analyzer, sample_csharp_code):
        """Test conversion of position to line and column."""
        if csharp_analyzer is None:
            pytest.skip("C# analyzer not available")
        
        # Find the position of "unusedField"
        pos = sample_csharp_code.find("unusedField")
        assert pos > 0
        
        line, column = csharp_analyzer.get_line_column(sample_csharp_code, pos)
        assert line > 0  # Line number (1-based)
        assert column > 0  # Column number (1-based)

    def test_create_temp_file(self, csharp_analyzer, sample_csharp_code):
        """Test creation of a temporary file."""
        if csharp_analyzer is None:
            pytest.skip("C# analyzer not available")
        
        temp_file = csharp_analyzer.create_temp_file(sample_csharp_code, suffix=".cs")
        try:
            assert os.path.exists(temp_file)
            assert temp_file.endswith(".cs")
            
            # Check that the content was written correctly
            with open(temp_file, "r") as f:
                content = f.read()
            assert content == sample_csharp_code
            
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    # Additional tests for C#-specific functionality

    def test_categorize_issue(self, csharp_analyzer):
        """Test categorization of issues by type and rule ID."""
        if csharp_analyzer is None:
            pytest.skip("C# analyzer not available")
        
        # Test various combinations of issue types and rule IDs
        test_cases = [
            ("error", "CS0168", IssueCategory.ERROR),  # Unused variable
            ("warning", "CS0219", IssueCategory.MAINTAINABILITY),  # Assigned but unused variable
            ("info", "IDE0051", IssueCategory.STYLE),  # Private member unused
            ("warning", "IDE0060", IssueCategory.STYLE),  # Unused parameter
            ("error", "CS0649", IssueCategory.ERROR),  # Field never assigned
            ("error", "SecurityInformation", IssueCategory.SECURITY),  # Security issue
            ("warning", "Performance", IssueCategory.PERFORMANCE),  # Performance issue
            ("info", "Style", IssueCategory.STYLE),  # Style issue
        ]
        
        for issue_type, rule_id, expected_category in test_cases:
            category = csharp_analyzer.categorize_issue(issue_type, rule_id)
            assert category == expected_category, f"Failed for {issue_type}, {rule_id}"

    def test_determine_severity(self, csharp_analyzer):
        """Test determination of issue severity."""
        if csharp_analyzer is None:
            pytest.skip("C# analyzer not available")
        
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
            severity = csharp_analyzer.determine_severity(severity_str)
            assert severity == expected_severity, f"Failed for {severity_str}"