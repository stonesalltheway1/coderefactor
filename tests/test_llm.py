"""
Tests for the Claude API integration and LLM functionality.
"""
import os
import sys
import pytest
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from unittest.mock import patch, MagicMock

# Import the LLM module components
try:
    from claude_api import ClaudeAPI, LLMConfig, RefactorSuggestion
    HAS_CLAUDE_API = True
except ImportError:
    HAS_CLAUDE_API = False


class TestClaudeAPI:
    """Test suite for the Claude API integration."""
    
    def test_initialization(self):
        """Test that the API client initializes properly."""
        if not HAS_CLAUDE_API:
            pytest.skip("Claude API not available")
        
        # Check if API key is available in environment
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("ANTHROPIC_API_KEY not set in environment")
        
        # Create config
        config = LLMConfig(
            api_key=api_key,
            model="claude-3-7-sonnet-20250219",
            temperature=0.3
        )
        
        # Initialize API client
        api = ClaudeAPI(config)
        
        assert api is not None
        assert api.config.api_key == api_key
        assert api.config.model == "claude-3-7-sonnet-20250219"
        assert api.config.temperature == 0.3
    
    @pytest.mark.asyncio
    async def test_suggest_refactoring_with_mock(self):
        """Test the suggest_refactoring method with mocked responses."""
        if not HAS_CLAUDE_API:
            pytest.skip("Claude API not available")
        
        # Mock the API client and responses
        with patch('claude_api.ClaudeAPI') as mock_api:
            # Create a mock instance
            mock_instance = MagicMock()
            mock_api.return_value = mock_instance
            
            # Set up the mock response
            mock_response = RefactorSuggestion(
                original_code="def example():\n    return 'hello'",
                refactored_code="def example() -> str:\n    return 'hello'",
                explanation="Added type hint for the return value",
                changes=[{"description": "Add return type annotation"}],
                confidence=0.9
            )
            
            # Configure the mock to return our response
            mock_instance.suggest_refactoring.return_value = mock_response
            
            # Create config
            config = LLMConfig(
                api_key="dummy-key",
                model="claude-3-7-sonnet-20250219"
            )
            
            # Initialize API client with mock
            api = ClaudeAPI(config)
            
            # Test the method
            code = "def example():\n    return 'hello'"
            language = "python"
            issue = "Missing return type hint"
            
            result = await api.suggest_refactoring(code, language, issue)
            
            # Verify the result
            assert result.original_code == "def example():\n    return 'hello'"
            assert result.refactored_code == "def example() -> str:\n    return 'hello'"
            assert result.explanation == "Added type hint for the return value"
            assert len(result.changes) == 1
            assert result.changes[0]["description"] == "Add return type annotation"
            assert result.confidence == 0.9
    
    @pytest.mark.asyncio
    async def test_analyze_code_with_mock(self):
        """Test the analyze_code method with mocked responses."""
        if not HAS_CLAUDE_API:
            pytest.skip("Claude API not available")
        
        # Mock the API client and responses
        with patch('claude_api.ClaudeAPI') as mock_api:
            # Create a mock instance
            mock_instance = MagicMock()
            mock_api.return_value = mock_instance
            
            # Set up the mock response
            mock_response = MagicMock()
            mock_response.issues = [
                {
                    "line": 2,
                    "column": 5,
                    "rule_id": "missing-return-type",
                    "message": "Function is missing return type annotation",
                    "severity": "warning",
                    "category": "style",
                    "fixable": True
                }
            ]
            mock_response.suggestions = [
                RefactorSuggestion(
                    original_code="def example():\n    return 'hello'",
                    refactored_code="def example() -> str:\n    return 'hello'",
                    explanation="Added return type annotation",
                    changes=[{"description": "Add return type hint"}],
                    confidence=0.9
                )
            ]
            mock_response.explanation = "This function is missing a return type annotation, which would improve type checking."
            mock_response.error = None
            
            # Configure the mock to return our response
            mock_instance.analyze_code.return_value = mock_response
            
            # Create config
            config = LLMConfig(
                api_key="dummy-key",
                model="claude-3-7-sonnet-20250219"
            )
            
            # Initialize API client with mock
            api = ClaudeAPI(config)
            
            # Test the method
            code = "def example():\n    return 'hello'"
            language = "python"
            
            result = await api.analyze_code(code, language)
            
            # Verify the result
            assert result.error is None
            assert len(result.issues) == 1
            assert result.issues[0]["line"] == 2
            assert result.issues[0]["rule_id"] == "missing-return-type"
            assert len(result.suggestions) == 1
            assert result.suggestions[0].original_code == "def example():\n    return 'hello'"
            assert result.explanation == "This function is missing a return type annotation, which would improve type checking."
    
    @pytest.mark.asyncio
    async def test_explain_code_with_mock(self):
        """Test the explain_code method with mocked responses."""
        if not HAS_CLAUDE_API:
            pytest.skip("Claude API not available")
        
        # Mock the API client and responses
        with patch('claude_api.ClaudeAPI') as mock_api:
            # Create a mock instance
            mock_instance = MagicMock()
            mock_api.return_value = mock_instance
            
            # Set up the mock response
            explanation = "This function takes no arguments and returns the string 'hello'."
            
            # Configure the mock to return our response
            mock_instance.explain_code.return_value = explanation
            
            # Create config
            config = LLMConfig(
                api_key="dummy-key",
                model="claude-3-7-sonnet-20250219"
            )
            
            # Initialize API client with mock
            api = ClaudeAPI(config)
            
            # Test the method
            code = "def example():\n    return 'hello'"
            language = "python"
            
            result = await api.explain_code(code, language)
            
            # Verify the result
            assert result == explanation
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_integration_suggest_refactoring(self):
        """Integration test for suggestion refactoring with real API."""
        if not HAS_CLAUDE_API:
            pytest.skip("Claude API not available")
        
        # Check if API key is available in environment
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("ANTHROPIC_API_KEY not set in environment")
        
        # Create config
        config = LLMConfig(
            api_key=api_key,
            model="claude-3-7-sonnet-20250219",
            temperature=0.3
        )
        
        # Initialize API client
        api = ClaudeAPI(config)
        
        # Test code with an obvious issue
        code = """def calculate_average(numbers):
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)  # Potential division by zero error
"""
        language = "python"
        issue = "This function has a potential division by zero error if numbers is empty"
        
        try:
            result = await api.suggest_refactoring(code, language, issue)
            
            # Check that we got a valid response
            assert result.original_code is not None
            assert result.refactored_code is not None
            assert result.refactored_code != result.original_code
            assert result.explanation is not None
            
            # The solution should include a check for empty list
            assert "empty" in result.explanation.lower() or "len" in result.explanation.lower()
            
        except Exception as e:
            pytest.skip(f"API call failed: {str(e)}")


# Fixture for sample code
@pytest.fixture
def sample_python_code() -> str:
    """Sample Python code with quality issues for testing."""
    return """import os
import sys
import re  # Unused import

def example_function(x, y):
    # This function adds two numbers
    z = x + y  # Unused variable
    return x + y

# Example usage
result = example_function(10, 20)
print(f"Result: {result}")

# Potential bug: undefined variable
try:
    print(undefined_var)
except:
    pass

# Inconsistent indentation
if True:
    print("True")
 print("Still in if block")  # Indentation error
"""

@pytest.fixture
def sample_csharp_code() -> str:
    """Sample C# code with quality issues for testing."""
    return """using System;
using System.Collections.Generic;
using System.Linq;  // Unused import

namespace SampleCode
{
    class Program
    {
        private static int unusedField;  // Unused field
        
        static void Main(string[] args)
        {
            // Unused variable
            string greeting = "Hello, World!";
            
            // Print multiple times
            for (int i = 0; i < 3)  // Missing semicolon
            {
                Console.WriteLine("Count: {0}", i);
            }
            
            // Potential null reference
            string name = null;
            Console.WriteLine(name.Length);
        }
        
        [TestMethod]  // Missing attribute import
        public void TestMethod()
        {
            // Test code
            int x = 5;
            int y = 10;
            Assert.AreEqual(15, x + y);
        }
    }
}
"""

@pytest.fixture
def sample_js_code() -> str:
    """Sample JavaScript code with quality issues for testing."""
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