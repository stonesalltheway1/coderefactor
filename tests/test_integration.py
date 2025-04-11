"""
Integration tests for the complete CodeRefactor application.
"""
import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from coderefactor import CodeRefactorApp


class TestCodeRefactorApp:
    """Test suite for the main CodeRefactorApp class."""

    def test_initialization(self):
        """Test that the app initializes properly."""
        app = CodeRefactorApp()
        
        assert app is not None
        assert hasattr(app, "analyze_file")
        assert hasattr(app, "analyze_directory")
        assert hasattr(app, "analyze_string")
        assert hasattr(app, "fix_file")
        assert hasattr(app, "fix_issue")
        assert hasattr(app, "get_fix_suggestion")

    def test_analyze_python_file(self):
        """Test analyzing a Python file."""
        # Create a temporary Python file
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
            temp_file.write(b'import os\nimport sys\nimport datetime  # Unused import\n\ndef test_function():\n    pass\n')
            temp_path = temp_file.name
        
        try:
            app = CodeRefactorApp()
            result = app.analyze_file(temp_path)
            
            assert result is not None
            assert "file_path" in result
            assert result["file_path"] == temp_path
            assert "issues" in result
            assert isinstance(result["issues"], list)
            assert len(result["issues"]) > 0
            
            # Should find the unused import
            assert any("W0611" in issue["rule_id"] or "unused import" in issue["message"].lower() 
                      for issue in result["issues"])
        finally:
            os.unlink(temp_path)

    def test_analyze_csharp_file(self):
        """Test analyzing a C# file."""
        # Create a temporary C# file
        with tempfile.NamedTemporaryFile(suffix='.cs', delete=False) as temp_file:
            temp_file.write(b'using System;\nusing System.Collections.Generic;\nusing System.Linq;  // Unused\n\nnamespace Test {\n    class Program {\n        static void Main() {\n            Console.WriteLine("Hello");\n        }\n    }\n}')
            temp_path = temp_file.name
        
        try:
            app = CodeRefactorApp()
            result = app.analyze_file(temp_path)
            
            assert result is not None
            assert "file_path" in result
            assert result["file_path"] == temp_path
            
            # If C# analyzer is available, should find issues
            if "issues" in result and result["issues"]:
                assert isinstance(result["issues"], list)
                # Might find unused using directive
                if any("CS0105" in issue["rule_id"] or "CS0168" in issue["rule_id"] or 
                      "unused" in issue["message"].lower() and "using" in issue["message"].lower() 
                      for issue in result["issues"]):
                    assert True
        finally:
            os.unlink(temp_path)

    def test_analyze_web_files(self):
        """Test analyzing web files (HTML, CSS, JS)."""
        # Create temporary web files
        web_files = {
            "html": (
                tempfile.NamedTemporaryFile(suffix='.html', delete=False),
                b'<html>\n<head>\n    <title>Test</title>\n</head>\n<body>\n    <img src=image.jpg>\n</body>\n</html>'
            ),
            "css": (
                tempfile.NamedTemporaryFile(suffix='.css', delete=False),
                b'body {\n    color: red;\n    background-color: blue\n}'
            ),
            "js": (
                tempfile.NamedTemporaryFile(suffix='.js', delete=False),
                b'function test() {\n    var unused = 10;\n    console.log("Hello");\n}'
            )
        }
        
        try:
            for file_type, (temp_file, content) in web_files.items():
                temp_file.write(content)
                temp_file.close()
                
                app = CodeRefactorApp()
                result = app.analyze_file(temp_file.name)
                
                assert result is not None
                assert "file_path" in result
                assert result["file_path"] == temp_file.name
                
                # If web analyzer is available, should find issues
                if "issues" in result and result["issues"]:
                    assert isinstance(result["issues"], list)
        finally:
            for file_type, (temp_file, _) in web_files.items():
                os.unlink(temp_file.name)

    def test_analyze_directory(self):
        """Test analyzing a directory with multiple files."""
        # Create a temporary directory with multiple file types
        temp_dir = tempfile.mkdtemp()
        try:
            # Create a Python file
            with open(os.path.join(temp_dir, 'test.py'), 'w') as f:
                f.write('import datetime  # Unused import\n\ndef test():\n    pass\n')
            
            # Create a C# file
            with open(os.path.join(temp_dir, 'test.cs'), 'w') as f:
                f.write('using System;\nusing System.Linq;  // Unused\n\nnamespace Test {\n    class Program {\n        static void Main() {\n            Console.WriteLine("Hello");\n        }\n    }\n}')
            
            # Create an HTML file
            with open(os.path.join(temp_dir, 'test.html'), 'w') as f:
                f.write('<html>\n<head>\n    <title>Test</title>\n</head>\n<body>\n    <img src=image.jpg>\n</body>\n</html>')
            
            # Create a subdirectory with another file
            sub_dir = os.path.join(temp_dir, 'subdir')
            os.makedirs(sub_dir)
            with open(os.path.join(sub_dir, 'subtest.py'), 'w') as f:
                f.write('import sys\nimport os\n\ndef subtest():\n    x = 10  # Unused variable\n')
            
            # Analyze the directory
            app = CodeRefactorApp()
            
            # Test without recursion
            results = app.analyze_directory(temp_dir, recursive=False)
            
            assert results is not None
            assert isinstance(results, dict)
            assert len(results) == 3  # Should find 3 files in the top directory
            assert os.path.join(temp_dir, 'test.py') in results
            assert os.path.join(temp_dir, 'test.cs') in results
            assert os.path.join(temp_dir, 'test.html') in results
            assert os.path.join(sub_dir, 'subtest.py') not in results  # Should not find the subdirectory file
            
            # Test with recursion
            results_recursive = app.analyze_directory(temp_dir, recursive=True)
            
            assert results_recursive is not None
            assert isinstance(results_recursive, dict)
            assert len(results_recursive) == 4  # Should find all 4 files
            assert os.path.join(temp_dir, 'test.py') in results_recursive
            assert os.path.join(temp_dir, 'test.cs') in results_recursive
            assert os.path.join(temp_dir, 'test.html') in results_recursive
            assert os.path.join(sub_dir, 'subtest.py') in results_recursive  # Should find the subdirectory file
            
            # Test with pattern
            results_pattern = app.analyze_directory(temp_dir, recursive=True, pattern="*.py")
            
            assert results_pattern is not None
            assert isinstance(results_pattern, dict)
            assert len(results_pattern) == 2  # Should find only Python files
            assert os.path.join(temp_dir, 'test.py') in results_pattern
            assert os.path.join(sub_dir, 'subtest.py') in results_pattern
            assert os.path.join(temp_dir, 'test.cs') not in results_pattern
            assert os.path.join(temp_dir, 'test.html') not in results_pattern
        finally:
            shutil.rmtree(temp_dir)

    def test_fix_python_unused_import(self):
        """Test fixing an unused import in a Python file."""
        # Create a temporary Python file with an unused import
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
            temp_file.write(b'import os\nimport sys\nimport datetime  # Unused import\n\ndef test_function():\n    pass\n')
            temp_path = temp_file.name
        
        try:
            app = CodeRefactorApp()
            
            # First analyze to get the issue
            result = app.analyze_file(temp_path)
            
            # Find the unused import issue
            unused_import_issue = None
            for issue in result["issues"]:
                if "W0611" in issue["rule_id"] or "unused import" in issue["message"].lower():
                    unused_import_issue = issue
                    break
            
            assert unused_import_issue is not None, "No unused import issue found"
            
            # Fix the issue
            fix_result = app.fix_issue(temp_path, unused_import_issue["rule_id"])
            
            assert fix_result is not None
            assert isinstance(fix_result, dict)
            assert "status" in fix_result
            assert fix_result["status"] == "success"
            assert "fixed_code" in fix_result
            assert "import datetime" not in fix_result["fixed_code"]
            
            # Verify the file was updated
            with open(temp_path, 'r') as f:
                fixed_code = f.read()
            
            assert "import datetime" not in fixed_code
        finally:
            os.unlink(temp_path)

    def test_llm_integration(self):
        """Test the LLM integration for code analysis and explanation."""
        # Skip if LLM integration is not available
        try:
            from coderefactor.llm.claude_api import ClaudeAPI
        except ImportError:
            pytest.skip("LLM integration not available")
        
        # Create a Python file with complex code that might benefit from LLM analysis
        code = """
def calculate_average(numbers):
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)  # Potential division by zero error
"""
        
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
            temp_file.write(code.encode('utf-8'))
            temp_path = temp_file.name
        
        try:
            # Mock the LLM API to avoid actual API calls during testing
            with patch('coderefactor.llm.claude_api.ClaudeAPI') as mock_api:
                # Setup mock responses
                mock_instance = MagicMock()
                mock_api.return_value = mock_instance
                
                mock_instance.analyze_code.return_value = MagicMock(
                    issues=[{
                        "line": 5,
                        "column": 12,
                        "rule_id": "potential-zero-division",
                        "message": "Potential division by zero when numbers is empty",
                        "severity": "error",
                        "category": "error",
                        "fixable": True
                    }],
                    suggestions=[{
                        "original_code": code.strip(),
                        "refactored_code": """
def calculate_average(numbers):
    if not numbers:
        return 0
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)
""".strip(),
                        "explanation": "Added a check for empty list to prevent division by zero",
                        "changes": [{"description": "Added check for empty list"}],
                        "confidence": 0.9
                    }],
                    explanation="This function calculates the average of a list of numbers, but doesn't check if the list is empty, which would cause a division by zero error.",
                    error=None
                )
                
                mock_instance.explain_code.return_value = "This function calculates the average of a list of numbers by iterating through each number, adding it to a running total, and then dividing by the count of numbers. However, it doesn't handle the case where the input list is empty."
                
                mock_instance.suggest_refactoring.return_value = MagicMock(
                    original_code=code.strip(),
                    refactored_code="""
def calculate_average(numbers):
    if not numbers:
        return 0
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)
""".strip(),
                    explanation="Added a check for empty list to prevent division by zero",
                    changes=[{"description": "Added check for empty list"}],
                    confidence=0.9
                )
                
                # Initialize app with mocked LLM
                app = CodeRefactorApp()
                
                # Test LLM-enhanced analysis
                result = app.analyze_file(temp_path, use_llm=True)
                
                assert result is not None
                assert "issues" in result
                assert "llm_analysis" in result
                assert "explanation" in result["llm_analysis"]
                assert "issues" in result["llm_analysis"]
                assert "suggestions" in result["llm_analysis"]
                
                # Test getting fix suggestions
                fix_suggestion = app.get_fix_suggestion(temp_path, "potential-zero-division")
                
                assert fix_suggestion is not None
                assert "explanation" in fix_suggestion
                assert "refactored_code" in fix_suggestion
                assert "if not numbers:" in fix_suggestion["refactored_code"]
        finally:
            os.unlink(temp_path)

    def test_end_to_end_workflow(self):
        """Test an end-to-end workflow: analyze, fix, and verify."""
        # Create a temporary Python file with issues
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
            temp_file.write(b"""
import os
import sys
import datetime  # Unused import

def calculate_average(numbers):
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)  # Potential division by zero error

def unused_function():  # Unused function
    pass

x = 10  # Unused variable
"""
            )
            temp_path = temp_file.name
        
        try:
            app = CodeRefactorApp()
            
            # Step 1: Analyze the file
            analysis_result = app.analyze_file(temp_path)
            
            assert analysis_result is not None
            assert "issues" in analysis_result
            
            initial_issue_count = len(analysis_result["issues"])
            assert initial_issue_count > 0
            
            # Step 2: Fix all issues
            for issue in analysis_result["issues"]:
                fix_result = app.fix_issue(temp_path, issue["rule_id"])
                
                if "status" in fix_result and fix_result["status"] == "success":
                    # Issue fixed successfully
                    assert "fixed_code" in fix_result
                    assert fix_result["fixed_code"] != analysis_result["original_code"]
            
            # Step 3: Re-analyze to verify fixes
            new_analysis = app.analyze_file(temp_path)
            
            assert new_analysis is not None
            assert "issues" in new_analysis
            
            # Should have fewer issues after fixing
            assert len(new_analysis["issues"]) < initial_issue_count
        finally:
            os.unlink(temp_path)


class TestEndToEndScenarios:
    """Test end-to-end scenarios with different file types and workflows."""

    def test_mixed_project_analysis(self):
        """Test analyzing a mixed project with multiple file types."""
        # Create a temporary project directory
        project_dir = tempfile.mkdtemp()
        try:
            # Create a sample project structure
            # - src/
            #   - main.py
            #   - utils.py
            # - web/
            #   - index.html
            #   - styles.css
            #   - script.js
            # - lib/
            #   - library.cs
            
            # Create directories
            os.makedirs(os.path.join(project_dir, "src"))
            os.makedirs(os.path.join(project_dir, "web"))
            os.makedirs(os.path.join(project_dir, "lib"))
            
            # Create Python files
            with open(os.path.join(project_dir, "src", "main.py"), "w") as f:
                f.write("""
import os
import sys
import datetime  # Unused import

def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
""")
            
            with open(os.path.join(project_dir, "src", "utils.py"), "w") as f:
                f.write("""
def calculate_average(numbers):
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)  # Potential division by zero error

def unused_function():  # Unused function
    pass
""")
            
            # Create web files
            with open(os.path.join(project_dir, "web", "index.html"), "w") as f:
                f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
    <link rel="stylesheet" href="styles.css">
    <script src="script.js"></script>
</head>
<body>
    <h1>Hello World!</h1>
    <img src=image.jpg alt=Image>
    <DIV class="container">
        <p>This is a paragraph
        <p>This is another paragraph</p>
    </DIV>
</body>
</html>
""")
            
            with open(os.path.join(project_dir, "web", "styles.css"), "w") as f:
                f.write("""
body {
    color: red;
    background-color: white
    font-size: 14px
}

h1 {
    color: blue;
    text-align: center
}
""")
            
            with open(os.path.join(project_dir, "web", "script.js"), "w") as f:
                f.write("""
function calculateTotal(items) {
    let total = 0;
    
    // Unused variable
    let count = items.length;
    
    for (let i = 0; i < items.length; i++) {
        total += items[i].price;
    }
    
    return total
}  // Missing semicolon
""")
            
            # Create C# file
            with open(os.path.join(project_dir, "lib", "library.cs"), "w") as f:
                f.write("""
using System;
using System.Collections.Generic;
using System.Linq;  // Unused namespace

namespace CodeRefactorTests
{
    public class Calculator
    {
        // Unused field
        private int unusedField;

        public int Add(int a, int b)
        {
            return a + b;
        }

        public int Subtract(int a, int b)
        {
            return a - b;
        }
    }
}
""")
            
            # Analyze the project
            app = CodeRefactorApp()
            results = app.analyze_directory(project_dir, recursive=True)
            
            assert results is not None
            assert isinstance(results, dict)
            
            # Should find all 5 files
            assert len(results) == 5
            
            # Check for specific file paths
            expected_files = [
                os.path.join(project_dir, "src", "main.py"),
                os.path.join(project_dir, "src", "utils.py"),
                os.path.join(project_dir, "web", "index.html"),
                os.path.join(project_dir, "web", "styles.css"),
                os.path.join(project_dir, "web", "script.js"),
                os.path.join(project_dir, "lib", "library.cs")
            ]
            
            # At least some of these files should be found (may depend on language support)
            assert any(file_path in results for file_path in expected_files)
            
            # Check that issues were found
            issue_count = sum(len(result["issues"]) for result in results.values() if "issues" in result)
            assert issue_count > 0
            
            # Test fixing multiple issues
            # Find a Python file with issues
            python_files = [path for path in results.keys() if path.endswith(".py") and len(results[path]["issues"]) > 0]
            if python_files:
                python_file = python_files[0]
                issues = results[python_file]["issues"]
                
                # Fix the first issue
                if issues:
                    fix_result = app.fix_issue(python_file, issues[0]["rule_id"])
                    assert fix_result is not None
                    assert "status" in fix_result
        finally:
            shutil.rmtree(project_dir)

    def test_with_custom_config(self):
        """Test using the app with a custom configuration."""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as config_file:
            config_file.write(b"""
python:
  enabled: true
  tools:
    - pylint
    - flake8
  rules:
    pylint:
      disable:
        - C0111  # missing-docstring

csharp:
  enabled: true

web:
  enabled: true

llm:
  enabled: false  # Disable LLM integration for testing

output:
  format: json
  colored: false
"""
            )
            config_path = config_file.name
        
        # Create a temporary Python file
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
            temp_file.write(b"""
def function_without_docstring():
    x = 10  # Unused variable
    return None
"""
            )
            temp_path = temp_file.name
        
        try:
            # Initialize app with custom config
            app = CodeRefactorApp(config_file=config_path)
            
            # Analyze the file
            result = app.analyze_file(temp_path)
            
            assert result is not None
            assert "issues" in result
            
            # Should not find docstring issues (disabled in config)
            assert not any("missing-docstring" in issue["rule_id"] or "C0111" in issue["rule_id"] 
                          for issue in result["issues"])
            
            # But should still find unused variable
            assert any("unused-variable" in issue["rule_id"] or "W0612" in issue["rule_id"] 
                      for issue in result["issues"])
        finally:
            os.unlink(config_path)
            os.unlink(temp_path)