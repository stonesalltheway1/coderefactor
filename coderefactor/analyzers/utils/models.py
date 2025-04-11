#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Shared data models for code analysis.
Provides common classes and enums used across different analyzers.
"""

import enum
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union, Set


class IssueSeverity(enum.Enum):
    """Enumeration of possible issue severity levels."""
    CRITICAL = 0
    ERROR = 1
    WARNING = 2
    INFO = 3
    
    def __str__(self) -> str:
        """String representation of the severity level."""
        return self.name.lower()


class IssueCategory(enum.Enum):
    """Enumeration of possible issue categories."""
    SECURITY = 0
    PERFORMANCE = 1
    MAINTAINABILITY = 2
    COMPLEXITY = 3
    STYLE = 4
    ERROR = 5
    TYPE = 6
    LOGIC = 7
    COMPATIBILITY = 8
    DEPRECATION = 9
    BEST_PRACTICE = 10
    OTHER = 99
    
    def __str__(self) -> str:
        """String representation of the category."""
        return self.name.lower()


@dataclass
class Issue:
    """Represents a code issue detected by an analyzer."""
    
    # Core issue properties
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    line: int = 0
    column: Optional[int] = None
    end_line: Optional[int] = None
    end_column: Optional[int] = None
    
    # Issue description
    message: str = ""
    description: str = ""
    severity: IssueSeverity = IssueSeverity.INFO
    category: IssueCategory = IssueCategory.OTHER
    
    # Source information
    source: str = ""  # Name of the analyzer/tool that found the issue
    rule_id: str = ""  # ID or reference for the rule that was violated
    
    # Fix information
    fixable: bool = False
    fix_type: str = ""  # "simple", "complex", "llm-assisted", etc.
    
    # Code context
    code_snippet: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the issue to a dictionary for serialization."""
        return {
            "id": self.id,
            "line": self.line,
            "column": self.column,
            "end_line": self.end_line,
            "end_column": self.end_column,
            "message": self.message,
            "description": self.description,
            "severity": str(self.severity),
            "category": str(self.category),
            "source": self.source,
            "rule_id": self.rule_id,
            "fixable": self.fixable,
            "fix_type": self.fix_type,
            "code_snippet": self.code_snippet
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Issue':
        """Create an Issue from a dictionary."""
        # Handle severity enum
        if isinstance(data.get('severity'), str):
            try:
                severity = IssueSeverity[data['severity'].upper()]
            except (KeyError, AttributeError):
                severity = IssueSeverity.INFO
        else:
            severity = data.get('severity', IssueSeverity.INFO)
        
        # Handle category enum
        if isinstance(data.get('category'), str):
            try:
                category = IssueCategory[data['category'].upper()]
            except (KeyError, AttributeError):
                category = IssueCategory.OTHER
        else:
            category = data.get('category', IssueCategory.OTHER)
        
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            line=data.get('line', 0),
            column=data.get('column'),
            end_line=data.get('end_line'),
            end_column=data.get('end_column'),
            message=data.get('message', ''),
            description=data.get('description', ''),
            severity=severity,
            category=category,
            source=data.get('source', ''),
            rule_id=data.get('rule_id', ''),
            fixable=data.get('fixable', False),
            fix_type=data.get('fix_type', ''),
            code_snippet=data.get('code_snippet')
        )


@dataclass
class AnalysisResult:
    """Results of a code analysis operation."""
    
    # List of issues found
    issues: List[Issue] = field(default_factory=list)
    
    # Any error that occurred during analysis
    error: Optional[str] = None
    
    # File info
    file_path: Optional[str] = None
    language: Optional[str] = None
    
    # Additional context
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_issue(self, issue: Issue) -> None:
        """Add an issue to the result."""
        self.issues.append(issue)
    
    def add_issues(self, issues: List[Issue]) -> None:
        """Add multiple issues to the result."""
        self.issues.extend(issues)
    
    def count_by_severity(self) -> Dict[str, int]:
        """Count issues by severity."""
        counts = {str(sev): 0 for sev in IssueSeverity}
        for issue in self.issues:
            counts[str(issue.severity)] += 1
        return counts
    
    def count_by_category(self) -> Dict[str, int]:
        """Count issues by category."""
        counts = {str(cat): 0 for cat in IssueCategory}
        for issue in self.issues:
            counts[str(issue.category)] += 1
        return counts
    
    def get_issues_by_severity(self, severity: Union[IssueSeverity, str]) -> List[Issue]:
        """Get issues with specified severity."""
        if isinstance(severity, str):
            severity_str = severity.lower()
            return [issue for issue in self.issues if str(issue.severity) == severity_str]
        else:
            return [issue for issue in self.issues if issue.severity == severity]
    
    def get_fixable_issues(self) -> List[Issue]:
        """Get all fixable issues."""
        return [issue for issue in self.issues if issue.fixable]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the analysis result to a dictionary for serialization."""
        return {
            "file_path": self.file_path,
            "language": self.language,
            "error": self.error,
            "issues": [issue.to_dict() for issue in self.issues],
            "metadata": self.metadata,
            "issues_count": len(self.issues),
            "issues_by_severity": self.count_by_severity(),
            "issues_by_category": self.count_by_category()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnalysisResult':
        """Create an AnalysisResult from a dictionary."""
        result = cls(
            file_path=data.get('file_path'),
            language=data.get('language'),
            error=data.get('error'),
            metadata=data.get('metadata', {})
        )
        
        # Add issues
        for issue_data in data.get('issues', []):
            result.add_issue(Issue.from_dict(issue_data))
        
        return result


# Additional utility functions
def merge_analysis_results(results: List[AnalysisResult]) -> AnalysisResult:
    """
    Merge multiple analysis results into one.
    Useful when multiple analyzers process the same file.
    
    Args:
        results: List of analysis results to merge
    
    Returns:
        Combined analysis result
    """
    if not results:
        return AnalysisResult()
    
    # Use the first result as the base
    merged = AnalysisResult(
        file_path=results[0].file_path,
        language=results[0].language,
        metadata=results[0].metadata.copy()
    )
    
    # Combine all issues
    for result in results:
        merged.add_issues(result.issues)
        
        # Combine metadata
        for key, value in result.metadata.items():
            if key not in merged.metadata:
                merged.metadata[key] = value
    
    # If any result has an error, include it
    error_messages = [r.error for r in results if r.error]
    if error_messages:
        merged.error = "; ".join(error_messages)
    
    return merged


def deduplicate_issues(issues: List[Issue]) -> List[Issue]:
    """
    Remove duplicate issues based on line, rule_id, and message.
    
    Args:
        issues: List of issues to deduplicate
    
    Returns:
        Deduplicated list of issues
    """
    unique_issues = []
    seen = set()
    
    for issue in issues:
        # Create a tuple of the key fields to identify duplicates
        key = (issue.line, issue.rule_id, issue.message)
        
        if key not in seen:
            seen.add(key)
            unique_issues.append(issue)
    
    return unique_issues