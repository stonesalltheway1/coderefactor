#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Prompts: Prompt templates for Claude API interactions.
These prompts are used to guide Claude for code analysis and refactoring tasks.
"""

# Analysis prompt template
CODE_ANALYSIS_PROMPT = """You are a senior software engineer reviewing code. I would like you to analyze this {language} code and identify potential issues, bugs, or improvements.

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
      "severity": "critical|error|warning|info",
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

{specific_concerns}

Focus on the most important issues first. For each issue, provide concrete suggestions for how to fix it when possible.
"""

# Refactoring prompt template
CODE_REFACTORING_PROMPT = """You are a senior software engineer helping refactor code. I have the following {language} code that needs improvement:

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

# Explanation prompt template
CODE_EXPLANATION_PROMPT = """You are a senior software engineer explaining code to a colleague. Please explain what this {language} code does:

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

# Function to get an analysis prompt
def get_analysis_prompt(code: str, language: str, specific_concerns: str = "") -> str:
    """
    Generate a prompt for code analysis.
    
    Args:
        code: The code to analyze
        language: The programming language
        specific_concerns: Optional specific concerns to focus on
        
    Returns:
        Formatted prompt string
    """
    return CODE_ANALYSIS_PROMPT.format(
        language=language,
        code=code,
        specific_concerns=specific_concerns
    )

# Function to get a refactoring prompt
def get_refactoring_prompt(code: str, language: str, issue_description: str) -> str:
    """
    Generate a prompt for code refactoring.
    
    Args:
        code: The code to refactor
        language: The programming language
        issue_description: Description of the issue to fix
        
    Returns:
        Formatted prompt string
    """
    return CODE_REFACTORING_PROMPT.format(
        language=language,
        code=code,
        issue_description=issue_description
    )

# Function to get an explanation prompt
def get_explanation_prompt(code: str, language: str) -> str:
    """
    Generate a prompt for code explanation.
    
    Args:
        code: The code to explain
        language: The programming language
        
    Returns:
        Formatted prompt string
    """
    return CODE_EXPLANATION_PROMPT.format(
        language=language,
        code=code
    )
