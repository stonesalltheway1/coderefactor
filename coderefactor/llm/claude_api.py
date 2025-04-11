#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Claude API Integration: Provides LLM-powered code analysis and fixes.
Part of the CodeRefactor project.
"""

import os
import json
import logging
import time
import re
from typing import Dict, Any, List, Optional, Tuple, Union
import httpx
from dataclasses import dataclass, field, asdict


@dataclass
class LLMConfig:
    """Configuration for the Claude API."""
    api_key: str = ""
    model: str = "claude-3-7-sonnet-20250219"
    timeout: int = 60
    temperature: float = 0.3
    max_tokens: int = 4000
    use_extended_thinking: bool = True


@dataclass
class RefactorSuggestion:
    """Represents a code refactoring suggestion from the LLM."""
    original_code: str = ""
    refactored_code: str = ""
    changes: List[Dict[str, Any]] = field(default_factory=list)
    explanation: str = ""
    confidence: float = 0.0
    

@dataclass
class AnalysisResult:
    """Represents the result of an LLM code analysis."""
    issues: List[Dict[str, Any]] = field(default_factory=list)
    suggestions: List[RefactorSuggestion] = field(default_factory=list)
    explanation: str = ""
    error: Optional[str] = None


class ClaudeAPI:
    """Interface for interacting with Claude API for code analysis and refactoring."""

    def __init__(self, config: LLMConfig = None, logger=None):
        """Initialize the Claude API interface."""
        self.config = config or LLMConfig()
        self.logger = logger or logging.getLogger("coderefactor.claude")
        
        if not self.config.api_key:
            # Try to get API key from environment
            self.config.api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            
        if not self.config.api_key:
            self.logger.warning("No Claude API key provided. API calls will fail.")
    
    async def analyze_code(self, code: str, language: str, specific_concerns: List[str] = None) -> AnalysisResult:
        """
        Analyze code using Claude to identify issues and potential improvements.
        
        Args:
            code: The code to analyze
            language: The programming language (python, csharp, javascript, etc.)
            specific_concerns: Optional list of specific concerns to focus on
        
        Returns:
            AnalysisResult containing identified issues and suggestions
        """
        self.logger.info(f"Analyzing {language} code with Claude")
        
        try:
            # Build the prompt
            prompt = self._build_analysis_prompt(code, language, specific_concerns)
            
            # Call the API
            response = await self._call_claude_api(prompt)
            
            if not response:
                return AnalysisResult(error="Failed to get response from Claude API")
            
            # Parse the analysis results
            return self._parse_analysis_response(response, code)
            
        except Exception as e:
            self.logger.error(f"Error analyzing code with Claude: {str(e)}")
            return AnalysisResult(error=str(e))
    
    async def suggest_refactoring(self, code: str, language: str, issue_description: str) -> RefactorSuggestion:
        """
        Suggest a refactoring for a specific issue in the code.
        
        Args:
            code: The code to refactor
            language: The programming language
            issue_description: Description of the issue to fix
        
        Returns:
            RefactorSuggestion with the suggested changes
        """
        self.logger.info(f"Requesting refactoring suggestion for {language} code")
        
        try:
            # Build the prompt
            prompt = self._build_refactoring_prompt(code, language, issue_description)
            
            # Call the API
            response = await self._call_claude_api(prompt)
            
            if not response:
                return RefactorSuggestion(
                    original_code=code,
                    explanation="Failed to get response from Claude API"
                )
            
            # Parse the refactoring suggestion
            return self._parse_refactoring_response(response, code)
            
        except Exception as e:
            self.logger.error(f"Error getting refactoring suggestion: {str(e)}")
            return RefactorSuggestion(
                original_code=code,
                explanation=f"Error: {str(e)}"
            )
    
    async def explain_code(self, code: str, language: str) -> str:
        """
        Get an explanation of what the code does.
        
        Args:
            code: The code to explain
            language: The programming language
        
        Returns:
            String containing the explanation
        """
        self.logger.info(f"Requesting code explanation for {language} code")
        
        try:
            # Build the prompt
            prompt = self._build_explanation_prompt(code, language)
            
            # Call the API
            response = await self._call_claude_api(prompt, max_tokens=1000)
            
            if not response:
                return "Failed to get explanation from Claude API"
            
            # Extract the explanation text
            return response.get("content", [{"text": "No explanation provided"}])[0]["text"]
            
        except Exception as e:
            self.logger.error(f"Error getting code explanation: {str(e)}")
            return f"Error: {str(e)}"

    async def _call_claude_api(self, prompt: str, max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """
        Call the Claude API with the given prompt.
        
        Args:
            prompt: The prompt to send to Claude
            max_tokens: Optional override for max response tokens
        
        Returns:
            The API response as a dictionary
        """
        if not self.config.api_key:
            self.logger.error("Cannot call Claude API: No API key provided")
            return {}
        
        try:
            headers = {
                "x-api-key": self.config.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            
            data = {
                "model": self.config.model,
                "max_tokens": max_tokens or self.config.max_tokens,
                "temperature": self.config.temperature,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
            
            # Add extended thinking if enabled
            if self.config.use_extended_thinking:
                data["system"] = "Think step-by-step about the code analysis problem before responding."
            
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=data
                )
                
                if response.status_code != 200:
                    self.logger.error(f"Claude API error: {response.status_code} - {response.text}")
                    return {}
                
                return response.json()
                
        except Exception as e:
            self.logger.error(f"Error calling Claude API: {str(e)}")
            return {}
    
    def _build_analysis_prompt(self, code: str, language: str, specific_concerns: List[str] = None) -> str:
        """Build a prompt for code analysis."""
        concerns_text = ""
        if specific_concerns:
            concerns_text = "Pay special attention to these specific concerns:\n" + "\n".join(f"- {concern}" for concern in specific_concerns)
        
        return f"""You are a senior software engineer reviewing code. I would like you to analyze this {language} code and identify potential issues, bugs, or improvements.

```{language}
{code}
```

Please provide your analysis in this JSON format:
```json
{{
  "issues": [
    {{
      "title": "Issue title",
      "description": "Detailed description of the issue",
      "severity": "critical|high|medium|low",
      "category": "security|performance|maintainability|complexity|style|error|other",
      "line_numbers": [X, Y, Z],
      "fixable": true|false,
      "fix_difficulty": "simple|moderate|complex"
    }}
  ],
  "suggestions": [
    {{
      "title": "Suggestion title",
      "description": "Detailed description of the suggestion",
      "before": "The relevant code snippet to be changed",
      "after": "The improved code snippet",
      "explanation": "Why this change is beneficial"
    }}
  ],
  "explanation": "A brief overall assessment of the code quality"
}}
```

{concerns_text}

Focus on the most important issues first. For each issue, provide concrete suggestions for how to fix it when possible.
"""

    def _build_refactoring_prompt(self, code: str, language: str, issue_description: str) -> str:
        """Build a prompt for code refactoring."""
        return f"""You are a senior software engineer helping refactor code. I have the following {language} code that needs improvement:

```{language}
{code}
```

The issue that needs to be fixed is: {issue_description}

Please provide your refactoring suggestion in this JSON format:
```json
{{
  "refactored_code": "The entire refactored code",
  "changes": [
    {{
      "description": "Description of a specific change",
      "before": "The relevant code snippet before change",
      "after": "The relevant code snippet after change",
      "line_numbers": [X, Y]
    }}
  ],
  "explanation": "A detailed explanation of the changes and why they address the issue",
  "confidence": 0.9
}}
```

The refactored code should maintain the same functionality while addressing the issue. Only make changes that are necessary to fix the described issue.
"""

    def _build_explanation_prompt(self, code: str, language: str) -> str:
        """Build a prompt for code explanation."""
        return f"""You are a senior software engineer explaining code to a colleague. Please explain what this {language} code does:

```{language}
{code}
```

Provide a clear and concise explanation of:
1. The overall purpose of the code
2. The main components or functions and what they do
3. Any important algorithms or patterns being used
4. Potential edge cases or limitations

Keep your explanation technical but accessible to someone familiar with programming.
"""

    def _parse_analysis_response(self, response: Dict[str, Any], original_code: str) -> AnalysisResult:
        """Parse the response from the code analysis API call."""
        try:
            # Extract the text content from the response
            content = response.get("content", [{"text": ""}])[0]["text"]
            
            # Extract JSON from the content (it might be wrapped in ```json blocks)
            json_match = re.search(r"```json\s*([\s\S]*?)\s*```", content)
            json_str = json_match.group(1) if json_match else content
            
            # Parse JSON
            result_data = json.loads(json_str)
            
            # Create AnalysisResult object
            result = AnalysisResult(
                issues=result_data.get("issues", []),
                explanation=result_data.get("explanation", "")
            )
            
            # Convert suggestions to RefactorSuggestion objects
            for suggestion_data in result_data.get("suggestions", []):
                suggestion = RefactorSuggestion(
                    original_code=suggestion_data.get("before", ""),
                    refactored_code=suggestion_data.get("after", ""),
                    explanation=suggestion_data.get("explanation", ""),
                    changes=[
                        {
                            "description": suggestion_data.get("title", ""),
                            "before": suggestion_data.get("before", ""),
                            "after": suggestion_data.get("after", "")
                        }
                    ]
                )
                result.suggestions.append(suggestion)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing analysis response: {str(e)}")
            return AnalysisResult(error=f"Failed to parse response: {str(e)}")
    
    def _parse_refactoring_response(self, response: Dict[str, Any], original_code: str) -> RefactorSuggestion:
        """Parse the response from the refactoring API call."""
        try:
            # Extract the text content from the response
            content = response.get("content", [{"text": ""}])[0]["text"]
            
            # Extract JSON from the content (it might be wrapped in ```json blocks)
            json_match = re.search(r"```json\s*([\s\S]*?)\s*```", content)
            json_str = json_match.group(1) if json_match else content
            
            # Parse JSON
            result_data = json.loads(json_str)
            
            # Create RefactorSuggestion object
            suggestion = RefactorSuggestion(
                original_code=original_code,
                refactored_code=result_data.get("refactored_code", original_code),
                changes=result_data.get("changes", []),
                explanation=result_data.get("explanation", ""),
                confidence=result_data.get("confidence", 0.0)
            )
            
            return suggestion
            
        except Exception as e:
            self.logger.error(f"Error parsing refactoring response: {str(e)}")
            return RefactorSuggestion(
                original_code=original_code,
                explanation=f"Failed to parse response: {str(e)}"
            )


# Simple CLI test if run directly
if __name__ == "__main__":
    import asyncio
    import sys
    
    async def main():
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        
        # Get API key from environment
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            print("Error: ANTHROPIC_API_KEY environment variable not set")
            sys.exit(1)
        
        # Create Claude API client
        config = LLMConfig(api_key=api_key)
        claude = ClaudeAPI(config)
        
        # Test code to analyze
        test_code = """
def calculate_average(numbers):
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)
        """
        
        # Get analysis
        result = await claude.analyze_code(test_code, "python")
        
        # Print results
        print("\nAnalysis Result:")
        print(f"Overall assessment: {result.explanation}")
        print("\nIssues:")
        for issue in result.issues:
            print(f"- {issue['title']} (Severity: {issue['severity']})")
            print(f"  {issue['description']}")
        
        print("\nSuggestions:")
        for suggestion in result.suggestions:
            print(f"- {suggestion.changes[0]['description'] if suggestion.changes else 'Suggestion'}")
            print(f"  Before: {suggestion.original_code}")
            print(f"  After: {suggestion.refactored_code}")
            print(f"  Explanation: {suggestion.explanation}")
    
    # Run the async main function
    asyncio.run(main())