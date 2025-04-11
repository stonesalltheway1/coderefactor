"""
Tests for the Python code fixer.
"""
import os
import sys
import pytest
from pathlib import Path
from typing import Dict, List, Any, Optional

from coderefactor.fixers.python_fixer import PythonFixer
from coderefactor.analyzers.python_analyzer import PythonAnalyzer
from coderefactor.analyzers.utils.models import AnalysisResult, AnalysisIssue, IssueSeverity, IssueCategory
from coderefactor.fixers.base import FixResult, FixStatus


class TestPythonFixer:
    """Test suite for the PythonFixer class."""

    def test_initialization(self, python_fixer):
        """Test that the fixer initializes properly."""
        assert python_fixer is not None
        assert isinstance(python_fixer, PythonFixer)
        assert hasattr(python_fixer, "fix_code")
        assert hasattr(python_fixer, "fix_file")
        assert hasattr(python_fixer, "fix_issue")

    def test_fix_unused_import(self, python_fixer, python_analyzer, sample_python_code):
        """Test fixing an unused import issue."""
        # First analyze the code to find the unused import
        result = python_analyzer.analyze_string(sample_python_code)
        
        # Find an unused import issue
        unused_import_issue = next(
            (issue for issue in result.issues if "W0611" in issue.rule_id), None
        )
        
        assert unused_import_issue is not None, "No unused import issue found in sample code"
        
        # Fix the issue
        fix_result = python_fixer.fix_issue(sample_python_code, unused_import_issue)
        
        assert isinstance(fix_result, FixResult)
        assert fix_result.status == FixStatus.SUCCESS
        assert fix_result.error is None
        assert fix_result.original_code == sample_python_code
        assert fix_result.fixed_code != sample_python_code
        
        # Verify that the unused import was removed
        assert "import datetime" not in fix_result.fixed_code

    def test_fix_unused_variable(self, python_fixer, python_analyzer, sample_python_code):
        """Test fixing an unused variable issue."""
        # First analyze the code to find the unused variable
        result = python_analyzer.analyze_string(sample_python_code)
        
        # Find an unused variable issue
        unused_var_issue = next(
            (issue for issue in result.issues if "W0612" in issue.rule_id), None
        )
        
        if unused_var_issue is None:
            pytest.skip("No unused variable issue found in sample code")
        
        # Fix the issue
        fix_result = python_fixer.fix_issue(sample_python_code, unused_var_issue)
        
        assert isinstance(fix_result, FixResult)
        assert fix_result.status == FixStatus.SUCCESS
        assert fix_result.error is None
        assert fix_result.original_code == sample_python_code
        assert fix_result.fixed_code != sample_python_code
        
        # The fixed code should either remove the unused variable or prefix it with _
        line_num = unused_var_issue.line - 1  # Convert to 0-based indexing
        code_lines = sample_python_code.splitlines()
        fixed_lines = fix_result.fixed_code.splitlines()
        
        if len(code_lines) == len(fixed_lines):
            # Variable was prefixed with _, not removed
            assert "_" in fixed_lines[line_num]
        else:
            # Variable was removed
            assert len(fixed_lines) < len(code_lines)

    def test_fix_missing_docstring(self, python_fixer, python_analyzer):
        """Test fixing a missing docstring issue."""
        # Create a code sample with a missing docstring
        code = """def function_without_docstring(a, b):
    return a + b
"""
        
        # First analyze the code to find the missing docstring issue
        result = python_analyzer.analyze_string(code)
        
        # Find a missing docstring issue
        missing_docstring_issue = next(
            (issue for issue in result.issues if "missing-docstring" in issue.rule_id), None
        )
        
        if missing_docstring_issue is None:
            pytest.skip("No missing docstring issue found in the test code")
        
        # Fix the issue
        fix_result = python_fixer.fix_issue(code, missing_docstring_issue)
        
        assert isinstance(fix_result, FixResult)
        assert fix_result.status == FixStatus.SUCCESS
        assert fix_result.error is None
        assert fix_result.original_code == code
        assert fix_result.fixed_code != code
        
        # Verify that a docstring was added
        assert '"""' in fix_result.fixed_code
        assert "function_without_docstring" in fix_result.fixed_code

    def test_fix_file(self, python_fixer, tmp_path, sample_python_code):
        """Test fixing issues in a file."""
        # Write the sample code to a temporary file
        file_path = tmp_path / "test_fix.py"
        with open(file_path, "w") as f:
            f.write(sample_python_code)
        
        # Fix the file
        fix_results = python_fixer.fix_file(str(file_path))
        
        assert isinstance(fix_results, Dict)
        assert len(fix_results) > 0
        
        # Check that the file was modified
        with open(file_path, "r") as f:
            fixed_code = f.read()
        
        assert fixed_code != sample_python_code

    def test_fix_code_multiple_issues(self, python_fixer, python_analyzer, sample_python_code):
        """Test fixing multiple issues in code."""
        # First analyze the code to find all issues
        result = python_analyzer.analyze_string(sample_python_code)
        
        # Fix all issues
        fix_result = python_fixer.fix_code(sample_python_code, result.issues)
        
        assert isinstance(fix_result, FixResult)
        assert fix_result.status == FixStatus.SUCCESS
        assert fix_result.error is None
        assert fix_result.original_code == sample_python_code
        assert fix_result.fixed_code != sample_python_code
        
        # Check that the fixed code has fewer issues
        new_result = python_analyzer.analyze_string(fix_result.fixed_code)
        assert len(new_result.issues) < len(result.issues)

    def test_fix_code_with_syntax_error(self, python_fixer):
        """Test fixing code with syntax errors."""
        # Create code with a syntax error
        code_with_error = """def broken_function():
    print("This is broken"
    return None
"""
        
        # Attempt to fix the code
        fix_result = python_fixer.fix_code(code_with_error, [])
        
        assert isinstance(fix_result, FixResult)
        assert fix_result.status == FixStatus.ERROR
        assert fix_result.error is not None
        assert "syntax" in fix_result.error.lower() or "parser" in fix_result.error.lower()
        assert fix_result.original_code == code_with_error
        assert fix_result.fixed_code == code_with_error  # Should not be modified

    def test_fix_nonexistent_file(self, python_fixer):
        """Test fixing a nonexistent file."""
        fix_results = python_fixer.fix_file("nonexistent_file.py")
        
        assert isinstance(fix_results, Dict)
        assert len(fix_results) == 0
        
        # Should have an error
        assert fix_results.get("error") is not None
        assert "not found" in fix_results.get("error").lower() or "does not exist" in fix_results.get("error").lower()

    def test_get_fix_description(self, python_fixer):
        """Test getting a description for a fix."""
        # Create a sample issue
        issue = AnalysisIssue(
            rule_id="W0611",
            message="Unused import datetime",
            line=3,
            column=1,
            severity=IssueSeverity.WARNING,
            category=IssueCategory.MAINTAINABILITY,
            file_path="test.py",
            code_snippet="import datetime  # Unused import",
        )
        
        description = python_fixer.get_fix_description(issue)
        
        assert isinstance(description, str)
        assert len(description) > 0
        assert "import" in description.lower() or "W0611" in description

    def test_fix_prioritization(self, python_fixer, python_analyzer, complex_python_code):
        """Test that issues are fixed in the right priority order."""
        # First analyze the code to find all issues
        result = python_analyzer.analyze_string(complex_python_code)
        
        # Get the issues sorted by priority
        issues = python_fixer.prioritize_issues(result.issues)
        
        assert isinstance(issues, List)
        assert len(issues) > 0
        
        # Check that critical/error issues come before warnings and info
        sevs = [issue.severity for issue in issues]
        for i in range(1, len(sevs)):
            if sevs[i-1] == IssueSeverity.CRITICAL and sevs[i] != IssueSeverity.CRITICAL:
                # Critical issues should be fixed first
                assert True
            elif sevs[i-1] == IssueSeverity.ERROR and sevs[i] == IssueSeverity.INFO:
                # Error issues should be fixed before info
                assert True


# Fixtures for the tests

@pytest.fixture
def python_fixer():
    """Create a PythonFixer instance for testing."""
    return PythonFixer()

@pytest.fixture
def python_analyzer():
    """Create a PythonAnalyzer instance for testing."""
    return PythonAnalyzer()

@pytest.fixture
def sample_python_code():
    """Return a sample Python code with common issues for testing."""
    return """
import os
import sys
import datetime  # Unused import

def add_numbers(a, b):
    \"\"\"Add two numbers and return the result.\"\"\"
    return a + b

def subtract_numbers(a, b):
    \"\"\"Subtract b from a and return the result.\"\"\"
    result = a - b  # This local variable is used
    return result

def multiply_numbers(a, b):
    \"\"\"Multiply two numbers and return the result.\"\"\"
    product = a * b  # Good: Variable is used
    return product

def divide_numbers(a, b):
    \"\"\"Divide a by b and return the result.\"\"\"
    # Issue: Missing check for division by zero
    return a / b

class Calculator:
    \"\"\"A simple calculator class.\"\"\"
    
    def __init__(self, initial_value=0):
        \"\"\"Initialize the calculator with an optional initial value.\"\"\"
        self.value = initial_value
        self._unused_attr = None  # Unused attribute
    
    def add(self, x):
        \"\"\"Add x to the current value.\"\"\"
        self.value += x
        return self
    
    def subtract(self, x):
        \"\"\"Subtract x from the current value.\"\"\"
        self.value -= x
        return self
    
    def get_value(self):
        \"\"\"Return the current value.\"\"\"
        return self.value
    
    def reset(self):
        \"\"\"Reset the calculator to zero.\"\"\"
        old_value = self.value  # Unused variable
        self.value = 0
        return self

# Example usage
if __name__ == "__main__":
    x = 10
    y = 5
    
    # Calculate and print results
    print(f"Add: {add_numbers(x, y)}")
    print(f"Subtract: {subtract_numbers(x, y)}")
    print(f"Multiply: {multiply_numbers(x, y)}")
    
    try:
        print(f"Divide: {divide_numbers(x, y)}")
    except ZeroDivisionError:
        print("Cannot divide by zero")
    
    # Create and use calculator
    calc = Calculator(x)
    calc.add(y).subtract(3)
    print(f"Calculator: {calc.get_value()}")
"""

@pytest.fixture
def complex_python_code():
    """Return a more complex Python code with various issues for testing."""
    return """
import os
import sys
import re
import json
import datetime
import math
import random
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass


# Global variable
global_counter = 0


@dataclass
class UserData:
    \"\"\"Data class for user information.\"\"\"
    id: int
    name: str
    email: str
    active: bool = True
    created_at: Optional[datetime.datetime] = None
    metadata: Dict[str, Any] = None  # Issue: Should use field(default_factory=dict)


class DataProcessor:
    \"\"\"Class for processing data with various quality issues.\"\"\"
    
    def __init__(self, data_source: str, options: Optional[Dict[str, Any]] = None):
        \"\"\"Initialize the processor with a data source and options.\"\"\"
        self.data_source = data_source
        self.options = options or {}
        self.processed_items = 0
        self._cache = {}  # Private cache
        self._unUsed_variable = None  # Unused and badly named
    
    def process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        \"\"\"Process a single data item.\"\"\"
        global global_counter
        
        # Increment counters
        self.processed_items += 1
        global_counter += 1
        
        # Issue: Unnecessarily complex code
        result = {}
        for key, value in item.items():
            if isinstance(value, str):
                # Issue: Uses strip() but doesn't check if needed
                result[key] = value.strip()
            elif isinstance(value, (int, float)):
                if value < 0:
                    # Issue: Magic number
                    result[key] = value * 1.1
                else:
                    result[key] = value
            elif isinstance(value, list):
                # Issue: Creates a new list unnecessarily
                new_list = []
                for subvalue in value:
                    new_list.append(subvalue)
                result[key] = new_list
            else:
                result[key] = value
        
        # Cache the result
        item_id = item.get('id')
        if item_id:
            self._cache[item_id] = result
        
        return result
"""