"""
Tests for the utility modules (config, logging, output).
"""
import os
import sys
import pytest
import tempfile
import shutil
import json
import yaml
import logging
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

from coderefactor.utils.config import (
    load_config, 
    merge_configs, 
    get_default_config, 
    validate_config
)
from coderefactor.utils.logging import (
    setup_logging, 
    get_logger
)
from coderefactor.utils.output import (
    format_results,
    write_json_results,
    write_html_report,
    format_issue
)
from coderefactor.analyzers.utils.models import AnalysisIssue, IssueSeverity, IssueCategory


class TestConfigUtils:
    """Test suite for configuration utilities."""

    def test_get_default_config(self):
        """Test getting the default configuration."""
        config = get_default_config()
        
        assert isinstance(config, dict)
        assert "python" in config
        assert "csharp" in config
        assert "web" in config
        assert "llm" in config
        assert "output" in config
        
        # Check specific values
        assert config["python"]["enabled"] is True
        assert "tools" in config["python"]
        assert isinstance(config["python"]["tools"], list)
        
        assert config["llm"]["enabled"] is True
        assert "model" in config["llm"]
        assert "claude" in config["llm"]["model"]

    def test_load_config_from_file(self):
        """Test loading config from a file."""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as temp_file:
            temp_file.write(b"""
python:
  enabled: true
  tools:
    - pylint
    - flake8

llm:
  enabled: false
  model: claude-3-7-sonnet-20250219
            """)
            config_path = temp_file.name
        
        try:
            config = load_config(config_path)
            
            assert isinstance(config, dict)
            assert config["python"]["enabled"] is True
            assert "pylint" in config["python"]["tools"]
            assert "flake8" in config["python"]["tools"]
            assert config["llm"]["enabled"] is False
            assert config["llm"]["model"] == "claude-3-7-sonnet-20250219"
        finally:
            os.unlink(config_path)

    def test_load_config_nonexistent_file(self):
        """Test loading config from a nonexistent file."""
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent_file.yaml")

    def test_load_config_invalid_yaml(self):
        """Test loading config from an invalid YAML file."""
        # Create a temporary file with invalid YAML
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as temp_file:
            temp_file.write(b"""
python:
  enabled: true
  tools:
    - pylint
    - flake8
  invalid yaml: : :
            """)
            config_path = temp_file.name
        
        try:
            with pytest.raises(yaml.YAMLError):
                load_config(config_path)
        finally:
            os.unlink(config_path)

    def test_merge_configs(self):
        """Test merging configurations."""
        # Base config
        base_config = {
            "python": {
                "enabled": True,
                "tools": ["pylint", "flake8"],
                "rules": {
                    "pylint": {"disable": ["C0111"]}
                }
            },
            "csharp": {
                "enabled": False
            },
            "output": {
                "format": "text",
                "colored": True
            }
        }
        
        # Override config
        override_config = {
            "python": {
                "tools": ["pylint", "mypy"],  # Changed tools
                "rules": {
                    "pylint": {"disable": ["C0111", "C0103"]}  # Added a rule
                }
            },
            "output": {
                "format": "json"  # Changed format
            },
            "llm": {  # New section
                "enabled": True,
                "model": "claude-3-7-sonnet-20250219"
            }
        }
        
        # Merge configs
        merged = merge_configs(base_config, override_config)
        
        # Check that the merge was done correctly
        assert merged["python"]["enabled"] is True  # Unchanged from base
        assert set(merged["python"]["tools"]) == set(["pylint", "mypy"])  # Overridden
        assert set(merged["python"]["rules"]["pylint"]["disable"]) == set(["C0111", "C0103"])  # Merged
        assert merged["csharp"]["enabled"] is False  # Unchanged from base
        assert merged["output"]["format"] == "json"  # Overridden
        assert merged["output"]["colored"] is True  # Unchanged from base
        assert merged["llm"]["enabled"] is True  # Added from override
        assert merged["llm"]["model"] == "claude-3-7-sonnet-20250219"  # Added from override

    def test_validate_config(self):
        """Test config validation."""
        # Valid config
        valid_config = {
            "python": {
                "enabled": True,
                "tools": ["pylint", "flake8"]
            },
            "llm": {
                "enabled": True,
                "model": "claude-3-7-sonnet-20250219"
            }
        }
        
        # Should not raise an exception
        validate_config(valid_config)
        
        # Invalid config (wrong type)
        invalid_config = {
            "python": {
                "enabled": "not a boolean",  # Should be a boolean
                "tools": ["pylint", "flake8"]
            }
        }
        
        with pytest.raises(ValueError):
            validate_config(invalid_config)
        
        # Invalid config (missing required field)
        invalid_config = {
            "python": {
                # Missing "enabled" field
                "tools": ["pylint", "flake8"]
            }
        }
        
        with pytest.raises(ValueError):
            validate_config(invalid_config)


class TestLoggingUtils:
    """Test suite for logging utilities."""

    def test_setup_logging(self):
        """Test setting up logging."""
        # Test with default parameters
        logger = setup_logging()
        
        assert logger is not None
        assert isinstance(logger, logging.Logger)
        assert logger.name == "coderefactor"
        assert logger.level == logging.INFO
        
        # Test with custom parameters
        custom_logger = setup_logging(log_level=logging.DEBUG, log_file="test.log")
        
        assert custom_logger is not None
        assert isinstance(custom_logger, logging.Logger)
        assert custom_logger.name == "coderefactor"
        assert custom_logger.level == logging.DEBUG
        
        # Check that the file handler was added
        has_file_handler = any(
            isinstance(handler, logging.FileHandler) and handler.baseFilename.endswith("test.log")
            for handler in custom_logger.handlers
        )
        assert has_file_handler

    def test_get_logger(self):
        """Test getting a logger."""
        # Setup logging first
        setup_logging()
        
        # Get a logger
        logger = get_logger()
        
        assert logger is not None
        assert isinstance(logger, logging.Logger)
        assert logger.name == "coderefactor"
        
        # Get a module-specific logger
        module_logger = get_logger("test_module")
        
        assert module_logger is not None
        assert isinstance(module_logger, logging.Logger)
        assert module_logger.name == "coderefactor.test_module"


class TestOutputUtils:
    """Test suite for output utilities."""

    def test_format_issue(self):
        """Test formatting a single issue."""
        # Create a sample issue
        issue = AnalysisIssue(
            rule_id="W0611",
            message="Unused import datetime",
            line=3,
            column=1,
            severity=IssueSeverity.WARNING,
            category=IssueCategory.MAINTAINABILITY,
            file_path="test.py",
            code_snippet="import datetime  # Unused import"
        )
        
        # Format the issue
        formatted = format_issue(issue)
        
        assert isinstance(formatted, str)
        assert "W0611" in formatted
        assert "Unused import datetime" in formatted
        assert "line 3" in formatted.lower()
        assert "warning" in formatted.lower() or "maintainability" in formatted.lower()

    def test_format_results_text(self):
        """Test formatting results as text."""
        # Create sample results
        results = {
            "test.py": {
                "file_path": "test.py",
                "issues": [
                    AnalysisIssue(
                        rule_id="W0611",
                        message="Unused import datetime",
                        line=3,
                        column=1,
                        severity=IssueSeverity.WARNING,
                        category=IssueCategory.MAINTAINABILITY,
                        file_path="test.py",
                        code_snippet="import datetime  # Unused import"
                    ),
                    AnalysisIssue(
                        rule_id="W0612",
                        message="Unused variable 'x'",
                        line=5,
                        column=5,
                        severity=IssueSeverity.WARNING,
                        category=IssueCategory.MAINTAINABILITY,
                        file_path="test.py",
                        code_snippet="    x = 10  # Unused variable"
                    )
                ],
                "error": None
            }
        }
        
        # Format the results as text
        formatted = format_results(results, output_format="text")
        
        assert isinstance(formatted, str)
        assert "test.py" in formatted
        assert "W0611" in formatted
        assert "Unused import datetime" in formatted
        assert "W0612" in formatted
        assert "Unused variable 'x'" in formatted
        assert "line 3" in formatted.lower()
        assert "line 5" in formatted.lower()

    def test_format_results_json(self):
        """Test formatting results as JSON."""
        # Create sample results
        results = {
            "test.py": {
                "file_path": "test.py",
                "issues": [
                    AnalysisIssue(
                        rule_id="W0611",
                        message="Unused import datetime",
                        line=3,
                        column=1,
                        severity=IssueSeverity.WARNING,
                        category=IssueCategory.MAINTAINABILITY,
                        file_path="test.py",
                        code_snippet="import datetime  # Unused import"
                    )
                ],
                "error": None
            }
        }
        
        # Format the results as JSON
        formatted = format_results(results, output_format="json")
        
        assert isinstance(formatted, str)
        
        # Parse the JSON to verify its structure
        json_data = json.loads(formatted)
        assert isinstance(json_data, dict)
        assert "test.py" in json_data
        assert "issues" in json_data["test.py"]
        assert len(json_data["test.py"]["issues"]) == 1
        assert json_data["test.py"]["issues"][0]["rule_id"] == "W0611"
        assert json_data["test.py"]["issues"][0]["message"] == "Unused import datetime"
        assert json_data["test.py"]["issues"][0]["line"] == 3
        assert json_data["test.py"]["issues"][0]["column"] == 1
        assert json_data["test.py"]["issues"][0]["severity"] == "WARNING"
        assert json_data["test.py"]["issues"][0]["category"] == "MAINTAINABILITY"

    def test_write_json_results(self):
        """Test writing results to a JSON file."""
        # Create sample results
        results = {
            "test.py": {
                "file_path": "test.py",
                "issues": [
                    AnalysisIssue(
                        rule_id="W0611",
                        message="Unused import datetime",
                        line=3,
                        column=1,
                        severity=IssueSeverity.WARNING,
                        category=IssueCategory.MAINTAINABILITY,
                        file_path="test.py",
                        code_snippet="import datetime  # Unused import"
                    )
                ],
                "error": None
            }
        }
        
        # Create a temporary file to write to
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
            json_path = temp_file.name
        
        try:
            # Write results to the JSON file
            write_json_results(results, json_path)
            
            # Verify that the file was written correctly
            assert os.path.exists(json_path)
            
            # Read the file and parse JSON
            with open(json_path, 'r') as f:
                json_data = json.load(f)
            
            assert isinstance(json_data, dict)
            assert "test.py" in json_data
            assert "issues" in json_data["test.py"]
            assert len(json_data["test.py"]["issues"]) == 1
            assert json_data["test.py"]["issues"][0]["rule_id"] == "W0611"
        finally:
            os.unlink(json_path)

    def test_write_html_report(self):
        """Test writing results to an HTML report."""
        # Create sample results
        results = {
            "test.py": {
                "file_path": "test.py",
                "issues": [
                    AnalysisIssue(
                        rule_id="W0611",
                        message="Unused import datetime",
                        line=3,
                        column=1,
                        severity=IssueSeverity.WARNING,
                        category=IssueCategory.MAINTAINABILITY,
                        file_path="test.py",
                        code_snippet="import datetime  # Unused import"
                    )
                ],
                "error": None
            }
        }
        
        # Create a temporary file to write to
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp_file:
            html_path = temp_file.name
        
        try:
            # Write results to the HTML file
            write_html_report(results, html_path)
            
            # Verify that the file was written correctly
            assert os.path.exists(html_path)
            
            # Read the file and check content
            with open(html_path, 'r') as f:
                html_content = f.read()
            
            assert "<!DOCTYPE html>" in html_content
            assert "CodeRefactor Analysis Report" in html_content
            assert "test.py" in html_content
            assert "W0611" in html_content
            assert "Unused import datetime" in html_content
        finally:
            os.unlink(html_path)


class TestUtilsIntegration:
    """Integration tests for utility modules."""

    def test_config_logging_integration(self):
        """Test integration between config and logging."""
        # Create a temporary config file with logging settings
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as temp_file:
            temp_file.write(b"""
logging:
  level: DEBUG
  file: test_log.log
            """)
            config_path = temp_file.name
        
        try:
            # Load the config
            config = load_config(config_path)
            
            # Setup logging based on the config
            with patch('logging.FileHandler') as mock_file_handler:
                logger = setup_logging(
                    log_level=getattr(logging, config.get("logging", {}).get("level", "INFO")),
                    log_file=config.get("logging", {}).get("file")
                )
                
                assert logger is not None
                assert logger.level == logging.DEBUG
                mock_file_handler.assert_called_once_with("test_log.log")
        finally:
            os.unlink(config_path)

    def test_config_output_integration(self):
        """Test integration between config and output formatting."""
        # Create a temporary config file with output settings
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as temp_file:
            temp_file.write(b"""
output:
  format: json
  colored: false
            """)
            config_path = temp_file.name
        
        try:
            # Load the config
            config = load_config(config_path)
            
            # Create sample results
            results = {
                "test.py": {
                    "file_path": "test.py",
                    "issues": [
                        AnalysisIssue(
                            rule_id="W0611",
                            message="Unused import datetime",
                            line=3,
                            column=1,
                            severity=IssueSeverity.WARNING,
                            category=IssueCategory.MAINTAINABILITY,
                            file_path="test.py",
                            code_snippet="import datetime  # Unused import"
                        )
                    ],
                    "error": None
                }
            }
            
            # Format results based on config
            formatted = format_results(
                results,
                output_format=config.get("output", {}).get("format", "text"),
                colored=config.get("output", {}).get("colored", True)
            )
            
            assert isinstance(formatted, str)
            
            # Should be JSON format based on config
            json_data = json.loads(formatted)
            assert isinstance(json_data, dict)
            assert "test.py" in json_data
            assert "issues" in json_data["test.py"]
        finally:
            os.unlink(config_path)