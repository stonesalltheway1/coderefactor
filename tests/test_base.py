"""
Tests for the base analyzer and fixer classes.
"""
import os
import sys
import pytest
from pathlib import Path
from typing import Dict, List, Any, Optional

from coderefactor.analyzers.base import BaseAnalyzer
from coderefactor.fixers.base import BaseFixer, FixResult, FixStatus
from coderefactor.analyzers.utils.models import AnalysisResult, AnalysisIssue, IssueSeverity, IssueCategory


class TestBaseAnalyzer:
    """Test suite for the BaseAnalyzer abstract base class."""

    def test_instantiation(self):
        """Test that the BaseAnalyzer cannot be instantiated directly."""
        with pytest.raises(TypeError):
            analyzer = BaseAnalyzer()

    def test_concrete_subclass(self):
        """Test that a concrete subclass can be instantiated."""
        class ConcreteAnalyzer(BaseAnalyzer):
            def analyze_string(self, code, **kwargs):
                return AnalysisResult(file_path="", issues=[], error=None)
            
            def analyze_file(self, file_path, **kwargs):
                return AnalysisResult(file_path=file_path, issues=[], error=None)
            
            def analyze_directory(self, dir_path, **kwargs):
                return {}
            
            def get_supported_extensions(self):
                return [".test"]
        
        analyzer = ConcreteAnalyzer()
        assert isinstance(analyzer, BaseAnalyzer)
        assert isinstance(analyzer, ConcreteAnalyzer)

    def test_abstract_methods(self):
        """Test that abstract methods are required in subclasses."""
        # Incomplete implementation missing some abstract methods
        class IncompleteAnalyzer(BaseAnalyzer):
            def analyze_string(self, code, **kwargs):
                return AnalysisResult(file_path="", issues=[], error=None)
            
            # Missing other required methods
        
        with pytest.raises(TypeError):
            analyzer = IncompleteAnalyzer()

    def test_helpers_and_utilities(self):
        """Test helper methods from the base class."""
        class ConcreteAnalyzer(BaseAnalyzer):
            def analyze_string(self, code, **kwargs):
                return AnalysisResult(file_path="", issues=[], error=None)
            
            def analyze_file(self, file_path, **kwargs):
                return AnalysisResult(file_path=file_path, issues=[], error=None)
            
            def analyze_directory(self, dir_path, **kwargs):
                return {}
            
            def get_supported_extensions(self):
                return [".test"]
        
        analyzer = ConcreteAnalyzer()
        
        # Test extract_code_snippet
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("line1\nline2\nline3\nline4\nline5\n")
            temp_path = f.name
        
        try:
            # Extract with different context sizes
            assert analyzer.extract_code_snippet(temp_path, 3, context_lines=0) == "line3"
            assert analyzer.extract_code_snippet(temp_path, 3, context_lines=1) == "line2\nline3\nline4"
            assert analyzer.extract_code_snippet(temp_path, 3, context_lines=2) == "line1\nline2\nline3\nline4\nline5"
            
            # Test with line out of range
            assert analyzer.extract_code_snippet(temp_path, 10, context_lines=1) == ""
        finally:
            os.unlink(temp_path)
        
        # Test get_line_column
        code = "line1\nline2\nline3"
        assert analyzer.get_line_column(code, 0) == (1, 1)  # Start of first line
        assert analyzer.get_line_column(code, 6) == (2, 1)  # Start of second line
        assert analyzer.get_line_column(code, 8) == (2, 3)  # Middle of second line
        
        # Test create_temp_file
        temp_file = analyzer.create_temp_file("test content", suffix=".test")
        try:
            assert os.path.exists(temp_file)
            assert temp_file.endswith(".test")
            with open(temp_file, 'r') as f:
                assert f.read() == "test content"
        finally:
            os.unlink(temp_file)


class TestBaseFixer:
    """Test suite for the BaseFixer abstract base class."""

    def test_instantiation(self):
        """Test that the BaseFixer cannot be instantiated directly."""
        with pytest.raises(TypeError):
            fixer = BaseFixer()

    def test_concrete_subclass(self):
        """Test that a concrete subclass can be instantiated."""
        class ConcreteFixer(BaseFixer):
            def fix_code(self, code, issues, **kwargs):
                return FixResult(
                    status=FixStatus.SUCCESS,
                    original_code=code,
                    fixed_code=code,
                    changes=[],
                    error=None
                )
            
            def fix_file(self, file_path, **kwargs):
                return {}
            
            def fix_issue(self, code, issue, **kwargs):
                return FixResult(
                    status=FixStatus.SUCCESS,
                    original_code=code,
                    fixed_code=code,
                    changes=[],
                    error=None
                )
            
            def get_fix_description(self, issue):
                return "Fix description"
            
            def prioritize_issues(self, issues):
                return issues
        
        fixer = ConcreteFixer()
        assert isinstance(fixer, BaseFixer)
        assert isinstance(fixer, ConcreteFixer)

    def test_abstract_methods(self):
        """Test that abstract methods are required in subclasses."""
        # Incomplete implementation missing some abstract methods
        class IncompleteFixer(BaseFixer):
            def fix_code(self, code, issues, **kwargs):
                return FixResult(
                    status=FixStatus.SUCCESS,
                    original_code=code,
                    fixed_code=code,
                    changes=[],
                    error=None
                )
            
            # Missing other required methods
        
        with pytest.raises(TypeError):
            fixer = IncompleteFixer()

    def test_fix_result_class(self):
        """Test the FixResult class."""
        # Test successful fix
        result = FixResult(
            status=FixStatus.SUCCESS,
            original_code="original",
            fixed_code="fixed",
            changes=[{"line": 1, "description": "Changed something"}],
            error=None
        )
        
        assert result.status == FixStatus.SUCCESS
        assert result.original_code == "original"
        assert result.fixed_code == "fixed"
        assert len(result.changes) == 1
        assert result.changes[0]["line"] == 1
        assert result.changes[0]["description"] == "Changed something"
        assert result.error is None
        
        # Test failed fix
        result = FixResult(
            status=FixStatus.ERROR,
            original_code="original",
            fixed_code="original",  # Unchanged
            changes=[],
            error="Something went wrong"
        )
        
        assert result.status == FixStatus.ERROR
        assert result.original_code == "original"
        assert result.fixed_code == "original"
        assert len(result.changes) == 0
        assert result.error == "Something went wrong"

    def test_fix_status_enum(self):
        """Test the FixStatus enum."""
        assert FixStatus.SUCCESS.value == "success"
        assert FixStatus.ERROR.value == "error"
        assert FixStatus.SKIPPED.value == "skipped"
        
        # Test using the enum in comparisons
        status = FixStatus.SUCCESS
        assert status == FixStatus.SUCCESS
        assert status != FixStatus.ERROR
        assert status != FixStatus.SKIPPED
        
        # Test converting to string
        assert str(FixStatus.SUCCESS) == "success"
        assert str(FixStatus.ERROR) == "error"
        assert str(FixStatus.SKIPPED) == "skipped"


import tempfile  # Add this at the top of the file