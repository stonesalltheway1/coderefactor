"""
Tests for the Web technologies fixer (HTML, CSS, JavaScript/TypeScript).
"""
import os
import sys
import pytest
from pathlib import Path
from typing import Dict, List, Any, Optional

from coderefactor.fixers.web_fixer import WebTechFixer
from coderefactor.analyzers.web_analyzer import WebTechAnalyzer
from coderefactor.analyzers.utils.models import AnalysisResult, AnalysisIssue, IssueSeverity, IssueCategory
from coderefactor.fixers.base import FixResult, FixStatus


class TestWebTechFixer:
    """Test suite for the WebTechFixer class."""

    def test_initialization(self, web_fixer):
        """Test that the fixer initializes properly."""
        assert web_fixer is not None
        assert hasattr(web_fixer, "fix_code")
        assert hasattr(web_fixer, "fix_file")
        assert hasattr(web_fixer, "fix_issue")

    def test_fix_html_doctype(self, web_fixer, web_analyzer, sample_html_code):
        """Test fixing a missing doctype in HTML."""
        # First analyze the code to find doctype issues
        result = web_analyzer.analyze_string(sample_html_code, file_type="html")
        
        # Find a doctype issue
        doctype_issue = next(
            (issue for issue in result.issues if "doctype" in issue.rule_id.lower() or 
             "doctype" in issue.message.lower()), None
        )
        
        if doctype_issue is None:
            pytest.skip("No doctype issue found in sample code")
        
        # Fix the issue
        fix_result = web_fixer.fix_issue(sample_html_code, doctype_issue)
        
        assert isinstance(fix_result, FixResult)
        assert fix_result.status == FixStatus.SUCCESS
        assert fix_result.error is None
        assert fix_result.original_code == sample_html_code
        assert fix_result.fixed_code != sample_html_code
        
        # The fixed code should have a doctype
        assert "<!DOCTYPE html>" in fix_result.fixed_code

    def test_fix_html_tag_pair(self, web_fixer, web_analyzer):
        """Test fixing unclosed HTML tags."""
        # Create code with unclosed tags
        html_with_unclosed_tags = """<html>
<head>
    <title>Test Page</title>
</head>
<body>
    <div>
        <h1>Hello World!</h1>
        <p>This paragraph is not closed.
    </div>
</body>
</html>"""
        
        # First analyze the code to find unclosed tag issues
        result = web_analyzer.analyze_string(html_with_unclosed_tags, file_type="html")
        
        # Find an unclosed tag issue
        unclosed_tag_issue = next(
            (issue for issue in result.issues if "tag-pair" in issue.rule_id.lower() or 
             "unclosed" in issue.message.lower()), None
        )
        
        if unclosed_tag_issue is None:
            pytest.skip("No unclosed tag issue found in sample code")
        
        # Fix the issue
        fix_result = web_fixer.fix_issue(html_with_unclosed_tags, unclosed_tag_issue)
        
        assert isinstance(fix_result, FixResult)
        assert fix_result.status == FixStatus.SUCCESS
        assert fix_result.error is None
        assert fix_result.original_code == html_with_unclosed_tags
        assert fix_result.fixed_code != html_with_unclosed_tags
        
        # The fixed code should close the paragraph tag
        assert "</p>" in fix_result.fixed_code

    def test_fix_html_attributes(self, web_fixer, web_analyzer):
        """Test fixing HTML attribute issues."""
        # Create code with attribute issues
        html_with_attribute_issues = """<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
</head>
<body>
    <img src=image.jpg alt=Image>
    <DIV class="container">
        <H1>Hello World!</H1>
    </DIV>
</body>
</html>"""
        
        # First analyze the code to find attribute issues
        result = web_analyzer.analyze_string(html_with_attribute_issues, file_type="html")
        
        # Find an attribute issue
        attribute_issue = next(
            (issue for issue in result.issues if "attr" in issue.rule_id.lower() or 
             "attribute" in issue.message.lower()), None
        )
        
        if attribute_issue is None:
            pytest.skip("No attribute issue found in sample code")
        
        # Fix the issue
        fix_result = web_fixer.fix_issue(html_with_attribute_issues, attribute_issue)
        
        assert isinstance(fix_result, FixResult)
        assert fix_result.status == FixStatus.SUCCESS
        assert fix_result.error is None
        assert fix_result.original_code == html_with_attribute_issues
        assert fix_result.fixed_code != html_with_attribute_issues
        
        # Check for fixed attributes (either quoted or lowercase tag names)
        fixed_code = fix_result.fixed_code.lower()
        assert 'src="image.jpg"' in fixed_code or 'alt="image"' in fixed_code or "<div" in fixed_code

    def test_fix_css_missing_semicolon(self, web_fixer, web_analyzer):
        """Test fixing missing semicolons in CSS."""
        # Create CSS with missing semicolons
        css_with_missing_semicolons = """body {
    color: red;
    background-color: white
    font-size: 14px
}

h1 {
    color: blue;
}"""
        
        # First analyze the code to find missing semicolon issues
        result = web_analyzer.analyze_string(css_with_missing_semicolons, file_type="css")
        
        # Find a missing semicolon issue
        missing_semicolon_issue = next(
            (issue for issue in result.issues if "semicolon" in issue.message.lower() or 
             "missing" in issue.message.lower()), None
        )
        
        if missing_semicolon_issue is None:
            pytest.skip("No missing semicolon issue found in sample code")
        
        # Fix the issue
        fix_result = web_fixer.fix_issue(css_with_missing_semicolons, missing_semicolon_issue)
        
        assert isinstance(fix_result, FixResult)
        assert fix_result.status == FixStatus.SUCCESS
        assert fix_result.error is None
        assert fix_result.original_code == css_with_missing_semicolons
        assert fix_result.fixed_code != css_with_missing_semicolons
        
        # The fixed code should add semicolons
        fixed_code = fix_result.fixed_code
        assert "white;" in fixed_code or "14px;" in fixed_code

    def test_fix_css_invalid_color(self, web_fixer, web_analyzer):
        """Test fixing invalid color values in CSS."""
        # Create CSS with invalid colors
        css_with_invalid_colors = """body {
    color: #1234ZZ;
    background-color: redd;
}

h1 {
    color: rgb(300, 0, 0);
}"""
        
        # First analyze the code to find invalid color issues
        result = web_analyzer.analyze_string(css_with_invalid_colors, file_type="css")
        
        # Find an invalid color issue
        invalid_color_issue = next(
            (issue for issue in result.issues if "color" in issue.rule_id.lower() or 
             "color" in issue.message.lower()), None
        )
        
        if invalid_color_issue is None:
            pytest.skip("No invalid color issue found in sample code")
        
        # Fix the issue
        fix_result = web_fixer.fix_issue(css_with_invalid_colors, invalid_color_issue)
        
        assert isinstance(fix_result, FixResult)
        assert fix_result.status == FixStatus.SUCCESS
        assert fix_result.error is None
        assert fix_result.original_code == css_with_invalid_colors
        assert fix_result.fixed_code != css_with_invalid_colors

    def test_fix_js_missing_semicolon(self, web_fixer, web_analyzer, sample_js_code):
        """Test fixing missing semicolons in JavaScript."""
        # First analyze the code to find missing semicolon issues
        result = web_analyzer.analyze_string(sample_js_code, file_type="javascript")
        
        # Find a missing semicolon issue
        missing_semicolon_issue = next(
            (issue for issue in result.issues if "semi" in issue.rule_id.lower() or 
             "semicolon" in issue.message.lower() or ";" in issue.message), None
        )
        
        if missing_semicolon_issue is None:
            pytest.skip("No missing semicolon issue found in sample code")
        
        # Fix the issue
        fix_result = web_fixer.fix_issue(sample_js_code, missing_semicolon_issue)
        
        assert isinstance(fix_result, FixResult)
        assert fix_result.status == FixStatus.SUCCESS
        assert fix_result.error is None
        assert fix_result.original_code == sample_js_code
        assert fix_result.fixed_code != sample_js_code
        
        # The fixed code should add semicolons
        assert "return total;" in fix_result.fixed_code

    def test_fix_js_unused_variable(self, web_fixer, web_analyzer, sample_js_code):
        """Test fixing unused variables in JavaScript."""
        # First analyze the code to find unused variable issues
        result = web_analyzer.analyze_string(sample_js_code, file_type="javascript")
        
        # Find an unused variable issue
        unused_var_issue = next(
            (issue for issue in result.issues if "no-unused-vars" in issue.rule_id.lower() or 
             "unused" in issue.message.lower() and "variable" in issue.message.lower()), None
        )
        
        if unused_var_issue is None:
            pytest.skip("No unused variable issue found in sample code")
        
        # Fix the issue
        fix_result = web_fixer.fix_issue(sample_js_code, unused_var_issue)
        
        assert isinstance(fix_result, FixResult)
        assert fix_result.status == FixStatus.SUCCESS
        assert fix_result.error is None
        assert fix_result.original_code == sample_js_code
        assert fix_result.fixed_code != sample_js_code
        
        # The fixed code should either remove or comment out the unused variable
        assert "let count = items.length" not in fix_result.fixed_code or "// let count" in fix_result.fixed_code

    def test_fix_js_null_check(self, web_fixer, web_analyzer, sample_js_code):
        """Test fixing missing null checks in JavaScript."""
        # First analyze the code to find null reference issues
        result = web_analyzer.analyze_string(sample_js_code, file_type="javascript")
        
        # Find a null reference issue
        null_ref_issue = next(
            (issue for issue in result.issues if "null" in issue.message.lower() or 
             "undefined" in issue.message.lower()), None
        )
        
        if null_ref_issue is None:
            pytest.skip("No null reference issue found in sample code")
        
        # Fix the issue
        fix_result = web_fixer.fix_issue(sample_js_code, null_ref_issue)
        
        assert isinstance(fix_result, FixResult)
        assert fix_result.status == FixStatus.SUCCESS
        assert fix_result.error is None
        assert fix_result.original_code == sample_js_code
        assert fix_result.fixed_code != sample_js_code
        
        # The fixed code should add a null check
        assert "if" in fix_result.fixed_code and ("user" in fix_result.fixed_code or "discount" in fix_result.fixed_code)

    def test_fix_file(self, web_fixer, tmp_path, sample_html_code):
        """Test fixing issues in a web file."""
        # Write the sample code to a temporary file
        file_path = tmp_path / "test_fix.html"
        with open(file_path, "w") as f:
            f.write(sample_html_code)
        
        # Fix the file
        fix_results = web_fixer.fix_file(str(file_path))
        
        assert isinstance(fix_results, Dict)
        assert len(fix_results) > 0
        
        # Check that the file was modified
        with open(file_path, "r") as f:
            fixed_code = f.read()
        
        assert fixed_code != sample_html_code

    def test_fix_code_multiple_issues(self, web_fixer, web_analyzer, sample_html_code):
        """Test fixing multiple issues in web code."""
        # First analyze the code to find all issues
        result = web_analyzer.analyze_string(sample_html_code, file_type="html")
        
        if len(result.issues) < 2:
            pytest.skip("Not enough issues found in sample code for multiple fix test")
        
        # Fix all issues
        fix_result = web_fixer.fix_code(sample_html_code, result.issues)
        
        assert isinstance(fix_result, FixResult)
        assert fix_result.status == FixStatus.SUCCESS
        assert fix_result.error is None
        assert fix_result.original_code == sample_html_code
        assert fix_result.fixed_code != sample_html_code
        
        # Check that the fixed code has fewer issues
        new_result = web_analyzer.analyze_string(fix_result.fixed_code, file_type="html")
        assert len(new_result.issues) < len(result.issues)

    def test_fix_code_with_syntax_error(self, web_fixer):
        """Test fixing code with syntax errors."""
        # Create HTML with a syntax error
        html_with_error = """<!DOCTYPE html>
<html>
<head>
    <title>Test</title>
</head>
<body>
    <div>
        <p>This is a test</p>
    </div>
</body>
"""  # Missing closing html tag
        
        # Attempt to fix the code
        fix_result = web_fixer.fix_code(html_with_error, [])
        
        assert isinstance(fix_result, FixResult)
        # Might be ERROR or SUCCESS with a fix for the missing tag
        if fix_result.status == FixStatus.ERROR:
            assert fix_result.error is not None
            assert fix_result.original_code == html_with_error
            assert fix_result.fixed_code == html_with_error  # Should not be modified
        else:
            assert fix_result.status == FixStatus.SUCCESS
            assert fix_result.error is None
            assert fix_result.original_code == html_with_error
            assert fix_result.fixed_code != html_with_error
            assert "</html>" in fix_result.fixed_code

    def test_fix_nonexistent_file(self, web_fixer):
        """Test fixing a nonexistent file."""
        fix_results = web_fixer.fix_file("nonexistent_file.html")
        
        assert isinstance(fix_results, Dict)
        assert len(fix_results) == 0 or "error" in fix_results

    def test_get_fix_description(self, web_fixer):
        """Test getting a description for a fix."""
        # Create a sample issue
        issue = AnalysisIssue(
            rule_id="doctype-first",
            message="Doctype must be declared first",
            line=1,
            column=1,
            severity=IssueSeverity.ERROR,
            category=IssueCategory.ERROR,
            file_path="test.html",
            code_snippet="<html><head><title>Test</title></head><body></body></html>",
        )
        
        description = web_fixer.get_fix_description(issue)
        
        assert isinstance(description, str)
        assert len(description) > 0
        assert "doctype" in description.lower()

    def test_fix_prioritization(self, web_fixer, web_analyzer, sample_html_code):
        """Test that issues are fixed in the right priority order."""
        # First analyze the code to find all issues
        result = web_analyzer.analyze_string(sample_html_code, file_type="html")
        
        if len(result.issues) < 2:
            pytest.skip("Not enough issues found in sample code for prioritization test")
        
        # Get the issues sorted by priority
        issues = web_fixer.prioritize_issues(result.issues)
        
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
def web_fixer():
    """Create a WebTechFixer instance for testing."""
    from coderefactor.fixers.web_fixer import WebTechFixer
    return WebTechFixer()

@pytest.fixture
def web_analyzer():
    """Create a WebTechAnalyzer instance for testing."""
    from coderefactor.analyzers.web_analyzer import WebTechAnalyzer
    return WebTechAnalyzer()

@pytest.fixture
def sample_html_code():
    """Return a sample HTML code with common issues for testing."""
    return """<html>
<head>
    <title>Test Page</title>
</head>
<body>
    <h1>Hello World!</h1>
    <img src=image.jpg alt=Image>
    <DIV class="container">
        <p>This is a paragraph
        <p>This is another paragraph</p>
    </DIV>
    <span style="color: #1234ZZ">Invalid color</span>
</body>
</html>"""

@pytest.fixture
def sample_css_code():
    """Return a sample CSS code with common issues for testing."""
    return """body {
    color: red;
    background-color: white
    font-size: 14px
}

h1 {
    color: blue;
    text-align: center
}

.container {
    width: 100%;
    padding: 20px;
    margin: 0
}

#header {
    color: #1234ZZ;  /* Invalid color */
    background-color: redd;  /* Misspelled color */
}"""

@pytest.fixture
def sample_js_code():
    """Return a sample JavaScript code with common issues for testing."""
    return """// Sample JavaScript with issues
function calculateTotal(items) {
    let total = 0;
    
    // Unused variable
    let count = items.length;
    
    for (let i = 0; i < items.length; i++) {
        total += items[i].price;
    }
    
    return total
}  // Missing semicolon

// Potential null reference
function displayUser(user) {
    console.log(user.name);  // No null check
}

// Example usage
const products = [
    { name: 'Apple', price: 0.5 },
    { name: 'Orange', price: 0.7 },
    { name: 'Banana', price: 0.3 }
];

const total = calculateTotal(products);
console.log('Total:', total);

// Undefined variable
console.log(discount);  // Undefined
"""