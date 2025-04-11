"""
Tests for the Web technologies analyzer (HTML, CSS, JavaScript/TypeScript).
"""
import os
import sys
import pytest
from pathlib import Path
from typing import Dict, List, Any, Optional

from coderefactor.analyzers.web_analyzer import WebTechAnalyzer
from coderefactor.analyzers.utils.models import AnalysisResult, AnalysisIssue, IssueSeverity, IssueCategory


class TestWebTechAnalyzer:
    """Test suite for the WebTechAnalyzer class."""

    def test_initialization(self, web_analyzer):
        """Test that the analyzer initializes properly."""
        assert web_analyzer is not None
        assert isinstance(web_analyzer, WebTechAnalyzer)
        assert hasattr(web_analyzer, "analyze_file")
        assert hasattr(web_analyzer, "analyze_string")
        assert hasattr(web_analyzer, "analyze_directory")

    def test_supported_extensions(self, web_analyzer):
        """Test that the supported extensions are correct."""
        extensions = web_analyzer.get_supported_extensions()
        assert isinstance(extensions, list)
        # Check for HTML extensions
        assert any(ext in extensions for ext in ['.html', '.htm', '.xhtml'])
        # Check for CSS extensions
        assert any(ext in extensions for ext in ['.css', '.scss', '.less'])
        # Check for JS/TS extensions
        assert any(ext in extensions for ext in ['.js', '.jsx', '.ts', '.tsx'])

    def test_linter_availability(self, web_analyzer):
        """Test that linter availability is correctly detected."""
        # Check that the linter availability flags are set
        assert hasattr(web_analyzer, "_has_eslint")
        assert hasattr(web_analyzer, "_has_stylelint")
        assert hasattr(web_analyzer, "_has_htmlhint")
        # These are booleans indicating availability
        assert isinstance(web_analyzer._has_eslint, bool)
        assert isinstance(web_analyzer._has_stylelint, bool)
        assert isinstance(web_analyzer._has_htmlhint, bool)

    def test_analyze_html_string(self, web_analyzer, sample_html_code):
        """Test analyzing HTML code from a string."""
        result = web_analyzer.analyze_string(sample_html_code, file_type="html")
        assert isinstance(result, AnalysisResult)
        assert result.file_path == ""  # No filename provided
        assert result.error is None

        # Check that issues were detected (if HTMLHint is available)
        if web_analyzer._has_htmlhint:
            assert len(result.issues) > 0
            
            # Common HTML issues to check for
            html_issues = {
                "doctype-first": "Doctype must be declared first",
                "attr-value": "Attribute value must be in double quotes",
                "attr-lowercase": "Attribute name must be lowercase",
                "alt-require": "Alt attribute required for <img> tags",
            }
            
            # Check if any of these common issues were detected
            found_issues = [issue.rule_id for issue in result.issues]
            assert any(issue_id in found_issues for issue_id in html_issues.keys())

    def test_analyze_css_string(self, web_analyzer, sample_css_code):
        """Test analyzing CSS code from a string."""
        result = web_analyzer.analyze_string(sample_css_code, file_type="css")
        assert isinstance(result, AnalysisResult)
        assert result.file_path == ""  # No filename provided
        assert result.error is None

        # Check that issues were detected (if Stylelint is available)
        if web_analyzer._has_stylelint:
            assert len(result.issues) > 0
            
            # Common CSS issues to check for
            css_issues = {
                "color-no-invalid-hex": "Invalid hex color",
                "declaration-block-no-duplicate-properties": "Duplicate properties",
                "block-no-empty": "Empty block",
                "rule-empty-line-before": "Rule should have an empty line before",
            }
            
            # Check if any of these common issues were detected
            found_issues = [issue.rule_id for issue in result.issues]
            assert any(issue_id in ''.join(found_issues) for issue_id in css_issues.keys())

    def test_analyze_js_string(self, web_analyzer, sample_js_code):
        """Test analyzing JavaScript code from a string."""
        result = web_analyzer.analyze_string(sample_js_code, file_type="javascript")
        assert isinstance(result, AnalysisResult)
        assert result.file_path == ""  # No filename provided
        assert result.error is None

        # Check that issues were detected (if ESLint is available)
        if web_analyzer._has_eslint:
            assert len(result.issues) > 0
            
            # Common JS issues to check for
            js_issues = {
                "no-unused-vars": "Unused variable",
                "semi": "Missing semicolon",
                "no-undef": "Undefined variable",
                "quotes": "Inconsistent quotes",
            }
            
            # Check if any of these common issues were detected
            found_issues = [issue.rule_id for issue in result.issues]
            assert any(issue_id in ''.join(found_issues) for issue_id in js_issues.keys())

    def test_analyze_string_with_filename(self, web_analyzer, sample_html_code):
        """Test analyzing code from a string with a filename."""
        result = web_analyzer.analyze_string(sample_html_code, filename="test_file.html")
        assert isinstance(result, AnalysisResult)
        assert result.file_path == "test_file.html"
        assert result.error is None

    def test_analyze_file(self, web_analyzer, web_fixtures_dir):
        """Test analyzing web files."""
        # Test HTML file
        html_file = web_fixtures_dir / "simple.html"
        if html_file.exists():
            result = web_analyzer.analyze_file(str(html_file))
            assert isinstance(result, AnalysisResult)
            assert result.file_path == str(html_file)
            assert result.error is None

        # Test CSS file
        css_file = web_fixtures_dir / "simple.css"
        if css_file.exists():
            result = web_analyzer.analyze_file(str(css_file))
            assert isinstance(result, AnalysisResult)
            assert result.file_path == str(css_file)
            assert result.error is None

        # Test JS file
        js_file = web_fixtures_dir / "simple.js"
        if js_file.exists():
            result = web_analyzer.analyze_file(str(js_file))
            assert isinstance(result, AnalysisResult)
            assert result.file_path == str(js_file)
            assert result.error is None

    def test_analyze_nonexistent_file(self, web_analyzer):
        """Test analyzing a nonexistent file."""
        result = web_analyzer.analyze_file("nonexistent_file.html")
        assert isinstance(result, AnalysisResult)
        assert result.file_path == "nonexistent_file.html"
        assert result.error is not None
        assert "not found" in result.error.lower() or "does not exist" in result.error.lower()

    def test_analyze_directory(self, web_analyzer, web_fixtures_dir):
        """Test analyzing all web files in a directory."""
        # Ensure there are some web files in the directory
        if not any(f.suffix in ['.html', '.css', '.js'] for f in web_fixtures_dir.iterdir() if f.is_file()):
            pytest.skip("No web test files found in fixtures directory")
        
        results = web_analyzer.analyze_directory(str(web_fixtures_dir))
        assert isinstance(results, dict)
        assert len(results) > 0
        for file_path, result in results.items():
            assert isinstance(result, AnalysisResult)
            assert result.file_path == file_path

    def test_analyze_directory_recursive(self, web_analyzer, fixtures_dir):
        """Test analyzing all web files in a directory recursively."""
        # Create a nested directory for testing
        nested_dir = fixtures_dir / "web" / "nested"
        nested_dir.mkdir(exist_ok=True)
        nested_file = nested_dir / "nested_test.html"
        with open(nested_file, "w") as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <title>Nested Test</title>
</head>
<body>
    <h1>Nested Test</h1>
</body>
</html>
""")

        try:
            results = web_analyzer.analyze_directory(str(fixtures_dir / "web"), recursive=True)
            assert isinstance(results, dict)
            
            # Should find the nested file
            nested_file_path = str(nested_file)
            assert nested_file_path in results
            assert isinstance(results[nested_file_path], AnalysisResult)
            
            # Try with recursive=False
            non_recursive_results = web_analyzer.analyze_directory(
                str(fixtures_dir / "web"), recursive=False
            )
            assert nested_file_path not in non_recursive_results
            
        finally:
            # Clean up the nested file and directory
            if nested_file.exists():
                nested_file.unlink()
            if nested_dir.exists():
                nested_dir.rmdir()

    def test_analyze_directory_with_pattern(self, web_analyzer, fixtures_dir):
        """Test analyzing web files in a directory with a pattern."""
        # Create sample web files
        web_dir = fixtures_dir / "web"
        web_dir.mkdir(exist_ok=True)
        
        html_file = web_dir / "test.html"
        css_file = web_dir / "test.css"
        js_file = web_dir / "test.js"
        
        with open(html_file, "w") as f:
            f.write("<!DOCTYPE html><html><body><h1>Test</h1></body></html>")
        
        with open(css_file, "w") as f:
            f.write("body { color: red; }")
        
        with open(js_file, "w") as f:
            f.write("function test() { console.log('test'); }")
        
        try:
            # Use a pattern that only matches HTML files
            results = web_analyzer.analyze_directory(str(web_dir), pattern="*.html")
            assert isinstance(results, dict)
            assert str(html_file) in results
            assert str(css_file) not in results
            assert str(js_file) not in results
            
            # Use a pattern that matches CSS and JS files
            results = web_analyzer.analyze_directory(str(web_dir), pattern="*.{css,js}")
            assert str(html_file) not in results
            assert str(css_file) in results
            assert str(js_file) in results
            
        finally:
            # Clean up files
            for file in [html_file, css_file, js_file]:
                if file.exists():
                    file.unlink()

    def test_extract_code_snippet(self, web_analyzer, sample_html_code, tmp_path):
        """Test extraction of code snippet from a web file."""
        # Write the sample code to a temporary file
        file_path = tmp_path / "test_snippet.html"
        with open(file_path, "w") as f:
            f.write(sample_html_code)
        
        # Find a line with an <img> tag
        line_number = 0
        for i, line in enumerate(sample_html_code.splitlines(), 1):
            if "<img" in line:
                line_number = i
                break
        
        if line_number > 0:
            snippet = web_analyzer.extract_code_snippet(str(file_path), line_number, context_lines=1)
            assert "<img" in snippet
            
            # Check that the context lines parameter works
            wide_snippet = web_analyzer.extract_code_snippet(str(file_path), line_number, context_lines=2)
            assert len(wide_snippet.splitlines()) > len(snippet.splitlines())

    def test_determine_file_type(self, web_analyzer):
        """Test determining file type from content and filename."""
        # Test HTML detection
        assert web_analyzer._determine_file_type("<!DOCTYPE html><html><body></body></html>", "test.html") == "html"
        assert web_analyzer._determine_file_type("<html><body><h1>Title</h1></body></html>", None) == "html"
        
        # Test CSS detection
        assert web_analyzer._determine_file_type("body { color: red; }", "test.css") == "css"
        assert web_analyzer._determine_file_type("@media screen { body { color: red; } }", None) == "css"
        
        # Test JavaScript detection
        assert web_analyzer._determine_file_type("function test() { return 1; }", "test.js") == "javascript"
        assert web_analyzer._determine_file_type("const x = 1; let y = 2;", None) == "javascript"
        
        # Test TypeScript detection
        assert web_analyzer._determine_file_type("function test(): number { return 1; }", "test.ts") == "typescript"
        assert web_analyzer._determine_file_type("interface User { name: string; }", None) == "typescript"

    def test_html_specific_checks(self, web_analyzer, sample_html_code):
        """Test HTML-specific analysis."""
        if not web_analyzer._has_htmlhint:
            pytest.skip("HTMLHint not available")
        
        issues = web_analyzer._analyze_html(sample_html_code, "test.html")
        assert isinstance(issues, list)
        
        # Check that common HTML issues were detected
        issue_rules = [issue.rule_id for issue in issues]
        common_rules = ["doctype-first", "attr-lowercase", "tag-pair", "spec-char-escape"]
        assert any(rule in issue_rules for rule in common_rules)

    def test_css_specific_checks(self, web_analyzer, sample_css_code):
        """Test CSS-specific analysis."""
        if not web_analyzer._has_stylelint:
            pytest.skip("Stylelint not available")
        
        issues = web_analyzer._analyze_css(sample_css_code, "test.css")
        assert isinstance(issues, list)
        
        # Check that common CSS issues were detected
        issue_descriptions = [issue.message.lower() for issue in issues]
        common_issues = ["color", "selector", "property", "value"]
        assert any(any(issue in desc for desc in issue_descriptions) for issue in common_issues)

    def test_js_specific_checks(self, web_analyzer, sample_js_code):
        """Test JavaScript-specific analysis."""
        if not web_analyzer._has_eslint:
            pytest.skip("ESLint not available")
        
        issues = web_analyzer._analyze_js(sample_js_code, "test.js")
        assert isinstance(issues, list)
        
        # Check that common JS issues were detected
        issue_rules = [issue.rule_id for issue in issues]
        common_rules = ["no-unused-vars", "semi", "no-undef", "quotes"]
        assert any(any(rule in r for r in issue_rules) for rule in common_rules)

    def test_syntax_error_detection(self, web_analyzer):
        """Test detection of syntax errors in web files."""
        # HTML with syntax error
        html_with_error = "<div><span>Unclosed span</div>"
        html_result = web_analyzer.analyze_string(html_with_error, file_type="html")
        assert any("tag-pair" in issue.rule_id or "unclosed" in issue.message.lower() 
                  for issue in html_result.issues)
        
        # CSS with syntax error
        css_with_error = "body { color: red; background: blue"  # Missing closing brace
        css_result = web_analyzer.analyze_string(css_with_error, file_type="css")
        assert any("block-no-empty" in issue.rule_id or "empty block" in issue.message.lower() 
                  or "missing" in issue.message.lower() for issue in css_result.issues)
        
        # JS with syntax error
        js_with_error = "function test() { console.log('test') "  # Missing closing brace
        js_result = web_analyzer.analyze_string(js_with_error, file_type="javascript")
        assert any("syntax" in issue.rule_id.lower() or "missing" in issue.message.lower() 
                  for issue in js_result.issues)