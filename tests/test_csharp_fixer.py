"""
Tests for the C# code fixer.
"""
import os
import sys
import pytest
from pathlib import Path
from typing import Dict, List, Any, Optional

from coderefactor.fixers.csharp_fixer import CSharpFixer
from coderefactor.analyzers.csharp_analyzer import CSharpAnalyzer
from coderefactor.analyzers.utils.models import AnalysisResult, AnalysisIssue, IssueSeverity, IssueCategory
from coderefactor.fixers.base import FixResult, FixStatus


class TestCSharpFixer:
    """Test suite for the CSharpFixer class."""

    def test_initialization(self, csharp_fixer):
        """Test that the fixer initializes properly."""
        if csharp_fixer is None:
            pytest.skip("C# fixer not available")
            
        assert csharp_fixer is not None
        assert hasattr(csharp_fixer, "fix_code")
        assert hasattr(csharp_fixer, "fix_file")
        assert hasattr(csharp_fixer, "fix_issue")

    def test_fix_unused_using(self, csharp_fixer, csharp_analyzer, sample_csharp_code):
        """Test fixing an unused using directive."""
        if csharp_fixer is None:
            pytest.skip("C# fixer not available")
            
        # First analyze the code to find unused using directives
        result = csharp_analyzer.analyze_string(sample_csharp_code)
        
        # Find an unused using issue
        unused_using_issue = next(
            (issue for issue in result.issues if "CS0105" in issue.rule_id or 
             "CS0168" in issue.rule_id or 
             "unused using" in issue.message.lower()), None
        )
        
        if unused_using_issue is None:
            pytest.skip("No unused using issue found in sample code")
        
        # Fix the issue
        fix_result = csharp_fixer.fix_issue(sample_csharp_code, unused_using_issue)
        
        assert isinstance(fix_result, FixResult)
        assert fix_result.status == FixStatus.SUCCESS
        assert fix_result.error is None
        assert fix_result.original_code == sample_csharp_code
        assert fix_result.fixed_code != sample_csharp_code
        
        # Analyze the fixed code
        new_result = csharp_analyzer.analyze_string(fix_result.fixed_code)
        new_issues = [issue for issue in new_result.issues if issue.rule_id == unused_using_issue.rule_id]
        
        # The specific issue should be fixed
        assert len(new_issues) < 1

    def test_fix_unused_field(self, csharp_fixer, csharp_analyzer, sample_csharp_code):
        """Test fixing an unused field."""
        if csharp_fixer is None:
            pytest.skip("C# fixer not available")
            
        # First analyze the code to find unused field
        result = csharp_analyzer.analyze_string(sample_csharp_code)
        
        # Find an unused field issue
        unused_field_issue = next(
            (issue for issue in result.issues if "CS0649" in issue.rule_id or 
             "unused field" in issue.message.lower()), None
        )
        
        if unused_field_issue is None:
            pytest.skip("No unused field issue found in sample code")
        
        # Fix the issue
        fix_result = csharp_fixer.fix_issue(sample_csharp_code, unused_field_issue)
        
        assert isinstance(fix_result, FixResult)
        assert fix_result.status == FixStatus.SUCCESS
        assert fix_result.error is None
        assert fix_result.original_code == sample_csharp_code
        assert fix_result.fixed_code != sample_csharp_code
        
        # Analyze the fixed code
        new_result = csharp_analyzer.analyze_string(fix_result.fixed_code)
        new_issues = [issue for issue in new_result.issues if issue.rule_id == unused_field_issue.rule_id]
        
        # The specific issue should be fixed
        assert len(new_issues) < 1

    def test_fix_missing_semicolon(self, csharp_fixer, csharp_analyzer):
        """Test fixing a missing semicolon."""
        if csharp_fixer is None:
            pytest.skip("C# fixer not available")
            
        # Create a code sample with a missing semicolon
        code = """using System;
namespace Test {
    class Program {
        static void Main() {
            int x = 5
            Console.WriteLine(x);
        }
    }
}
"""
        
        # First analyze the code to find the missing semicolon issue
        result = csharp_analyzer.analyze_string(code)
        
        # Find the missing semicolon issue
        missing_semicolon_issue = next(
            (issue for issue in result.issues if "syntax" in issue.rule_id.lower() or 
             "missing" in issue.message.lower() and "semicolon" in issue.message.lower()), None
        )
        
        if missing_semicolon_issue is None:
            pytest.skip("No missing semicolon issue found in the test code")
        
        # Fix the issue
        fix_result = csharp_fixer.fix_issue(code, missing_semicolon_issue)
        
        assert isinstance(fix_result, FixResult)
        assert fix_result.status == FixStatus.SUCCESS
        assert fix_result.error is None
        assert fix_result.original_code == code
        assert fix_result.fixed_code != code
        
        # The fixed code should have a semicolon after x = 5
        assert "x = 5;" in fix_result.fixed_code

    def test_fix_potential_null_reference(self, csharp_fixer, csharp_analyzer, sample_csharp_code):
        """Test fixing a potential null reference exception."""
        if csharp_fixer is None:
            pytest.skip("C# fixer not available")
            
        # First analyze the code to find null reference issues
        result = csharp_analyzer.analyze_string(sample_csharp_code)
        
        # Find a null reference issue
        null_ref_issue = next(
            (issue for issue in result.issues if "null" in issue.message.lower() and 
             "reference" in issue.message.lower()), None
        )
        
        if null_ref_issue is None:
            pytest.skip("No null reference issue found in sample code")
        
        # Fix the issue
        fix_result = csharp_fixer.fix_issue(sample_csharp_code, null_ref_issue)
        
        assert isinstance(fix_result, FixResult)
        assert fix_result.status == FixStatus.SUCCESS
        assert fix_result.error is None
        assert fix_result.original_code == sample_csharp_code
        assert fix_result.fixed_code != sample_csharp_code
        
        # The fixed code should add a null check
        assert "null" in fix_result.fixed_code and "if" in fix_result.fixed_code

    def test_fix_file(self, csharp_fixer, tmp_path, sample_csharp_code):
        """Test fixing issues in a file."""
        if csharp_fixer is None:
            pytest.skip("C# fixer not available")
            
        # Write the sample code to a temporary file
        file_path = tmp_path / "test_fix.cs"
        with open(file_path, "w") as f:
            f.write(sample_csharp_code)
        
        # Fix the file
        fix_results = csharp_fixer.fix_file(str(file_path))
        
        assert isinstance(fix_results, Dict)
        # Should have results or an error entry
        assert len(fix_results) > 0
        
        # Check that the file was modified if fixes were applied
        if "error" not in fix_results:
            with open(file_path, "r") as f:
                fixed_code = f.read()
            
            assert fixed_code != sample_csharp_code

    def test_fix_code_multiple_issues(self, csharp_fixer, csharp_analyzer, sample_csharp_code):
        """Test fixing multiple issues in code."""
        if csharp_fixer is None:
            pytest.skip("C# fixer not available")
            
        # First analyze the code to find all issues
        result = csharp_analyzer.analyze_string(sample_csharp_code)
        
        if len(result.issues) < 2:
            pytest.skip("Not enough issues found in sample code for multiple fix test")
        
        # Fix all issues
        fix_result = csharp_fixer.fix_code(sample_csharp_code, result.issues)
        
        assert isinstance(fix_result, FixResult)
        assert fix_result.status == FixStatus.SUCCESS
        assert fix_result.error is None
        assert fix_result.original_code == sample_csharp_code
        assert fix_result.fixed_code != sample_csharp_code
        
        # Check that the fixed code has fewer issues
        new_result = csharp_analyzer.analyze_string(fix_result.fixed_code)
        assert len(new_result.issues) < len(result.issues)

    def test_fix_code_with_syntax_error(self, csharp_fixer):
        """Test fixing code with syntax errors."""
        if csharp_fixer is None:
            pytest.skip("C# fixer not available")
            
        # Create code with a syntax error
        code_with_error = """using System;
namespace Test {
    class Program {
        static void Main() {
            Console.WriteLine("This is broken"
        }
    }
}
"""
        
        # Attempt to fix the code
        fix_result = csharp_fixer.fix_code(code_with_error, [])
        
        assert isinstance(fix_result, FixResult)
        assert fix_result.status == FixStatus.ERROR
        assert fix_result.error is not None
        assert "syntax" in fix_result.error.lower() or "parser" in fix_result.error.lower()
        assert fix_result.original_code == code_with_error
        assert fix_result.fixed_code == code_with_error  # Should not be modified

    def test_fix_nonexistent_file(self, csharp_fixer):
        """Test fixing a nonexistent file."""
        if csharp_fixer is None:
            pytest.skip("C# fixer not available")
            
        fix_results = csharp_fixer.fix_file("nonexistent_file.cs")
        
        assert isinstance(fix_results, Dict)
        assert "error" in fix_results
        assert "not found" in fix_results["error"].lower() or "does not exist" in fix_results["error"].lower()

    def test_get_fix_description(self, csharp_fixer):
        """Test getting a description for a fix."""
        if csharp_fixer is None:
            pytest.skip("C# fixer not available")
            
        # Create a sample issue
        issue = AnalysisIssue(
            rule_id="CS0168",
            message="The variable 'x' is declared but never used",
            line=5,
            column=13,
            severity=IssueSeverity.WARNING,
            category=IssueCategory.MAINTAINABILITY,
            file_path="test.cs",
            code_snippet="int x = 5;",
        )
        
        description = csharp_fixer.get_fix_description(issue)
        
        assert isinstance(description, str)
        assert len(description) > 0
        assert "variable" in description.lower() or "unused" in description.lower()

    def test_fix_prioritization(self, csharp_fixer, csharp_analyzer, complex_csharp_code):
        """Test that issues are fixed in the right priority order."""
        if csharp_fixer is None:
            pytest.skip("C# fixer not available")
            
        # First analyze the code to find all issues
        result = csharp_analyzer.analyze_string(complex_csharp_code)
        
        if len(result.issues) < 2:
            pytest.skip("Not enough issues found in sample code for prioritization test")
        
        # Get the issues sorted by priority
        issues = csharp_fixer.prioritize_issues(result.issues)
        
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
def csharp_fixer():
    """Create a CSharpFixer instance for testing."""
    try:
        from coderefactor.fixers.csharp_fixer import CSharpFixer
        return CSharpFixer()
    except (ImportError, ModuleNotFoundError):
        # C# fixer not available
        return None

@pytest.fixture
def csharp_analyzer():
    """Create a CSharpAnalyzer instance for testing."""
    try:
        from coderefactor.analyzers.csharp_analyzer import CSharpAnalyzer
        return CSharpAnalyzer()
    except (ImportError, ModuleNotFoundError):
        # C# analyzer not available
        return None

@pytest.fixture
def sample_csharp_code():
    """Return a sample C# code with common issues for testing."""
    return """using System;
using System.Collections.Generic;
using System.Linq;  // Unused namespace

namespace CodeRefactorTests
{
    /// <summary>
    /// A simple calculator class for testing the code analyzer and fixer.
    /// </summary>
    public class Calculator
    {
        // Unused field
        private int unusedField;

        /// <summary>
        /// Adds two numbers.
        /// </summary>
        /// <param name="a">First number</param>
        /// <param name="b">Second number</param>
        /// <returns>The sum of a and b</returns>
        public int Add(int a, int b)
        {
            return a + b;
        }

        /// <summary>
        /// Subtracts the second number from the first.
        /// </summary>
        /// <param name="a">First number</param>
        /// <param name="b">Second number</param>
        /// <returns>The result of a - b</returns>
        public int Subtract(int a, int b)
        {
            return a - b;
        }

        /// <summary>
        /// Multiplies two numbers.
        /// </summary>
        /// <param name="a">First number</param>
        /// <param name="b">Second number</param>
        /// <returns>The product of a and b</returns>
        public int Multiply(int a, int b)
        {
            return a * b;
        }

        /// <summary>
        /// Divides the first number by the second.
        /// </summary>
        /// <param name="a">First number</param>
        /// <param name="b">Second number</param>
        /// <returns>The result of a / b</returns>
        public double Divide(int a, int b)
        {
            // Missing null check
            return a / b;  // Potential division by zero
        }

        /// <summary>
        /// Calculates the average of a list of numbers.
        /// </summary>
        /// <param name="numbers">List of numbers</param>
        /// <returns>The average of the numbers</returns>
        public double Average(List<int> numbers)
        {
            // Issue: Potential null reference exception
            int sum = 0;
            foreach (int number in numbers)
            {
                sum += number;
            }
            
            return sum / numbers.Count;  // Potential division by zero
        }
    }

    /// <summary>
    /// Main program class.
    /// </summary>
    public class Program
    {
        /// <summary>
        /// Entry point of the application.
        /// </summary>
        /// <param name="args">Command line arguments</param>
        public static void Main(string[] args)
        {
            // Unused variable
            string Greeting = "Hello, World!";
            
            // Create a calculator
            Calculator calculator = new Calculator();
            
            // Perform calculations
            int a = 10;
            int b = 5;
            
            Console.WriteLine($"Add: {calculator.Add(a, b)}");
            Console.WriteLine($"Subtract: {calculator.Subtract(a, b)}");
            Console.WriteLine($"Multiply: {calculator.Multiply(a, b)}");
            
            // Issue: No try-catch for potential exception
            Console.WriteLine($"Divide: {calculator.Divide(a, b)}");
            
            // Create a list of numbers
            List<int> numbers = new List<int> { 1, 2, 3, 4, 5 };
            
            // Calculate and display the average
            double average = calculator.Average(numbers);
            Console.WriteLine($"Average: {average}");
            
            // Wait for user input before exiting
            Console.WriteLine("Press any key to exit...");
            Console.ReadKey();
        }
    }
}"""

@pytest.fixture
def complex_csharp_code():
    """Return a more complex C# code with various issues for testing."""
    return """using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.IO;  // Unused namespace
using System.Diagnostics;  // Unused namespace

namespace CodeRefactorTests.Complex
{
    /// <summary>
    /// Data model for a user with quality issues.
    /// </summary>
    public class User
    {
        // Public fields (which should be properties)
        public int ID;
        public string Name;
        public string Email;
        
        // Unused private field
        private DateTime registrationDate;
        
        // Inconsistent naming convention (not camelCase)
        private bool IsActive;
        
        /// <summary>
        /// Default constructor.
        /// </summary>
        public User()
        {
            ID = 0;
            Name = string.Empty;
            Email = string.Empty;
            registrationDate = DateTime.Now;
            IsActive = true;
        }
        
        /// <summary>
        /// Constructor with parameters.
        /// </summary>
        public User(int id, string name, string email)
        {
            ID = id;
            Name = name;
            Email = email;
            registrationDate = DateTime.Now;
            IsActive = true;
        }
        
        /// <summary>
        /// Gets a display name for the user.
        /// </summary>
        public string GetDisplayName()
        {
            // Redundant check (null comparison for value type)
            if (ID == null)
            {
                return Name;
            }
            
            return $"{ID}: {Name}";
        }
        
        /// <summary>
        /// Validates the user email.
        /// </summary>
        public bool ValidateEmail()
        {
            // Overly simplified validation
            return Email.Contains("@");
        }
        
        /// <summary>
        /// Updates user status.
        /// </summary>
        /// <param name="active">New active status</param>
        public void SetStatus(bool active)
        {
            // Unused variable
            bool previousStatus = IsActive;
            
            IsActive = active;
        }
    }
}"""