"""
Tests for the command-line interface.
"""
import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import json
import yaml

from coderefactor.cli.commands import (
    analyze_command, 
    fix_command, 
    web_command, 
    main
)


class TestCLICommands:
    """Test suite for the CLI commands."""

    def test_cli_help(self):
        """Test the help command."""
        with patch('sys.argv', ['coderefactor', '--help']):
            with patch('sys.exit') as mock_exit:
                with patch('builtins.print') as mock_print:
                    try:
                        main()
                    except SystemExit:
                        pass
                    
                    mock_exit.assert_called_once()
                    assert mock_print.call_count > 0
                    # Check that help text was printed
                    help_text = ''.join(call[0][0] for call in mock_print.call_args_list if call[0])
                    assert 'usage' in help_text.lower()
                    assert 'analyze' in help_text.lower()
                    assert 'fix' in help_text.lower()
                    assert 'web' in help_text.lower()

    def test_cli_version(self):
        """Test the version command."""
        with patch('sys.argv', ['coderefactor', '--version']):
            with patch('sys.exit') as mock_exit:
                with patch('builtins.print') as mock_print:
                    try:
                        main()
                    except SystemExit:
                        pass
                    
                    mock_exit.assert_called_once()
                    assert mock_print.call_count > 0
                    # Check that version info was printed
                    version_text = ''.join(call[0][0] for call in mock_print.call_args_list if call[0])
                    assert 'version' in version_text.lower()

    def test_analyze_command_file(self):
        """Test the analyze command with a file."""
        # Create a temporary Python file
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
            temp_file.write(b'def test_function():\n    pass\n')
            temp_path = temp_file.name
        
        try:
            with patch('sys.argv', ['coderefactor', 'analyze', temp_path]):
                with patch('coderefactor.cli.commands.analyze_file') as mock_analyze:
                    mock_analyze.return_value = {'issues': []}
                    
                    analyze_command()
                    
                    mock_analyze.assert_called_once_with(temp_path, config=None)
        finally:
            os.unlink(temp_path)

    def test_analyze_command_directory(self):
        """Test the analyze command with a directory."""
        # Create a temporary directory with Python files
        temp_dir = tempfile.mkdtemp()
        try:
            # Create a Python file in the directory
            with open(os.path.join(temp_dir, 'test.py'), 'w') as f:
                f.write('def test_function():\n    pass\n')
            
            with patch('sys.argv', ['coderefactor', 'analyze', temp_dir, '--recursive']):
                with patch('coderefactor.cli.commands.analyze_directory') as mock_analyze:
                    mock_analyze.return_value = {}
                    
                    analyze_command()
                    
                    mock_analyze.assert_called_once_with(
                        temp_dir, recursive=True, pattern=None, config=None
                    )
        finally:
            shutil.rmtree(temp_dir)

    def test_analyze_command_with_pattern(self):
        """Test the analyze command with a file pattern."""
        # Create a temporary directory with Python files
        temp_dir = tempfile.mkdtemp()
        try:
            # Create two different Python files
            with open(os.path.join(temp_dir, 'test1.py'), 'w') as f:
                f.write('def test_function1():\n    pass\n')
            with open(os.path.join(temp_dir, 'test2.py'), 'w') as f:
                f.write('def test_function2():\n    pass\n')
            
            with patch('sys.argv', ['coderefactor', 'analyze', temp_dir, '--pattern', 'test1*.py']):
                with patch('coderefactor.cli.commands.analyze_directory') as mock_analyze:
                    mock_analyze.return_value = {}
                    
                    analyze_command()
                    
                    mock_analyze.assert_called_once_with(
                        temp_dir, recursive=False, pattern='test1*.py', config=None
                    )
        finally:
            shutil.rmtree(temp_dir)

    def test_analyze_command_output_format(self):
        """Test the analyze command with different output formats."""
        # Create a temporary Python file
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
            temp_file.write(b'def test_function():\n    pass\n')
            temp_path = temp_file.name
        
        try:
            # Test JSON output format
            with patch('sys.argv', ['coderefactor', 'analyze', temp_path, '--format', 'json']):
                with patch('coderefactor.cli.commands.analyze_file') as mock_analyze:
                    mock_analyze.return_value = {'issues': []}
                    with patch('builtins.print') as mock_print:
                        
                        analyze_command()
                        
                        mock_analyze.assert_called_once()
                        assert mock_print.call_count > 0
                        # Check if JSON output was printed
                        json_text = mock_print.call_args[0][0]
                        # Verify it's valid JSON
                        assert json.loads(json_text) is not None
            
            # Test HTML output format
            with patch('sys.argv', ['coderefactor', 'analyze', temp_path, '--format', 'html', '--output', 'report.html']):
                with patch('coderefactor.cli.commands.analyze_file') as mock_analyze:
                    mock_analyze.return_value = {'issues': []}
                    with patch('coderefactor.utils.output.write_html_report') as mock_write:
                        
                        analyze_command()
                        
                        mock_analyze.assert_called_once()
                        mock_write.assert_called_once()
        finally:
            os.unlink(temp_path)

    def test_analyze_command_with_config(self):
        """Test the analyze command with a custom configuration file."""
        # Create a temporary Python file
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
            temp_file.write(b'def test_function():\n    pass\n')
            py_temp_path = temp_file.name
        
        # Create a temporary YAML config file
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as temp_file:
            temp_file.write(b'python:\n  enabled: true\n  tools:\n    - pylint\n    - flake8\n')
            config_temp_path = temp_file.name
        
        try:
            with patch('sys.argv', ['coderefactor', 'analyze', py_temp_path, '--config', config_temp_path]):
                with patch('coderefactor.cli.commands.analyze_file') as mock_analyze:
                    mock_analyze.return_value = {'issues': []}
                    
                    analyze_command()
                    
                    mock_analyze.assert_called_once()
                    # Verify the config was loaded
                    args, kwargs = mock_analyze.call_args
                    assert kwargs['config'] is not None
                    assert isinstance(kwargs['config'], dict)
                    assert 'python' in kwargs['config']
                    assert kwargs['config']['python']['enabled'] is True
        finally:
            os.unlink(py_temp_path)
            os.unlink(config_temp_path)

    def test_fix_command(self):
        """Test the fix command."""
        # Create a temporary Python file with an issue
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
            temp_file.write(b'import os\nimport sys\nimport datetime  # Unused import\n\ndef test_function():\n    pass\n')
            temp_path = temp_file.name
        
        try:
            with patch('sys.argv', ['coderefactor', 'fix', temp_path, 'W0611']):
                with patch('coderefactor.cli.commands.fix_issue') as mock_fix:
                    mock_fix.return_value = {'status': 'success', 'changes': 1}
                    
                    fix_command()
                    
                    mock_fix.assert_called_once_with(temp_path, 'W0611', config=None)
        finally:
            os.unlink(temp_path)

    def test_fix_command_all_issues(self):
        """Test the fix command with the --all flag."""
        # Create a temporary Python file with multiple issues
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
            temp_file.write(b'import os\nimport sys\nimport datetime  # Unused import\n\ndef test_function():\n    unused_var = 42  # Unused variable\n    return None\n')
            temp_path = temp_file.name
        
        try:
            with patch('sys.argv', ['coderefactor', 'fix', temp_path, '--all']):
                with patch('coderefactor.cli.commands.fix_all_issues') as mock_fix_all:
                    mock_fix_all.return_value = {'fixed': 2, 'failed': 0}
                    
                    fix_command()
                    
                    mock_fix_all.assert_called_once_with(temp_path, config=None)
        finally:
            os.unlink(temp_path)

    def test_fix_command_with_config(self):
        """Test the fix command with a custom configuration file."""
        # Create a temporary Python file
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
            temp_file.write(b'import os\nimport sys\nimport datetime  # Unused import\n\ndef test_function():\n    pass\n')
            py_temp_path = temp_file.name
        
        # Create a temporary YAML config file
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as temp_file:
            temp_file.write(b'python:\n  enabled: true\n  tools:\n    - pylint\n    - flake8\n')
            config_temp_path = temp_file.name
        
        try:
            with patch('sys.argv', ['coderefactor', 'fix', py_temp_path, 'W0611', '--config', config_temp_path]):
                with patch('coderefactor.cli.commands.fix_issue') as mock_fix:
                    mock_fix.return_value = {'status': 'success', 'changes': 1}
                    
                    fix_command()
                    
                    mock_fix.assert_called_once()
                    # Verify the config was loaded
                    args, kwargs = mock_fix.call_args
                    assert kwargs['config'] is not None
                    assert isinstance(kwargs['config'], dict)
                    assert 'python' in kwargs['config']
                    assert kwargs['config']['python']['enabled'] is True
        finally:
            os.unlink(py_temp_path)
            os.unlink(config_temp_path)

    def test_web_command(self):
        """Test the web command."""
        with patch('sys.argv', ['coderefactor', 'web']):
            with patch('coderefactor.cli.commands.start_web_interface') as mock_web:
                
                web_command()
                
                mock_web.assert_called_once_with(host='127.0.0.1', port=5000)

    def test_web_command_with_host_port(self):
        """Test the web command with custom host and port."""
        with patch('sys.argv', ['coderefactor', 'web', '--host', '0.0.0.0', '--port', '8080']):
            with patch('coderefactor.cli.commands.start_web_interface') as mock_web:
                
                web_command()
                
                mock_web.assert_called_once_with(host='0.0.0.0', port=8080)


class TestCLIArguments:
    """Test suite for CLI argument parsing."""

    def test_analyze_command_arguments(self):
        """Test argument parsing for the analyze command."""
        with patch('sys.argv', ['coderefactor', 'analyze', 'path/to/file.py']):
            with patch('argparse.ArgumentParser.parse_args') as mock_parse:
                mock_parse.return_value = MagicMock(
                    command='analyze',
                    path='path/to/file.py',
                    recursive=False,
                    pattern=None,
                    format='text',
                    output=None,
                    config=None,
                    colored=True
                )
                
                with patch('coderefactor.cli.commands.analyze_file') as mock_analyze:
                    mock_analyze.return_value = {'issues': []}
                    
                    analyze_command()
                    
                    mock_parse.assert_called_once()
                    mock_analyze.assert_called_once()

    def test_fix_command_arguments(self):
        """Test argument parsing for the fix command."""
        with patch('sys.argv', ['coderefactor', 'fix', 'path/to/file.py', 'issue-id']):
            with patch('argparse.ArgumentParser.parse_args') as mock_parse:
                mock_parse.return_value = MagicMock(
                    command='fix',
                    path='path/to/file.py',
                    issue_id='issue-id',
                    all=False,
                    config=None
                )
                
                with patch('coderefactor.cli.commands.fix_issue') as mock_fix:
                    mock_fix.return_value = {'status': 'success'}
                    
                    fix_command()
                    
                    mock_parse.assert_called_once()
                    mock_fix.assert_called_once()

    def test_web_command_arguments(self):
        """Test argument parsing for the web command."""
        with patch('sys.argv', ['coderefactor', 'web', '--host', '0.0.0.0', '--port', '8080']):
            with patch('argparse.ArgumentParser.parse_args') as mock_parse:
                mock_parse.return_value = MagicMock(
                    command='web',
                    host='0.0.0.0',
                    port=8080
                )
                
                with patch('coderefactor.cli.commands.start_web_interface') as mock_web:
                    
                    web_command()
                    
                    mock_parse.assert_called_once()
                    mock_web.assert_called_once()


class TestCLIIntegration:
    """Integration tests for the CLI."""

    def test_analyze_workflow(self):
        """Test a typical analyze workflow."""
        # Create a temporary Python file with an issue
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
            temp_file.write(b'import os\nimport sys\nimport datetime  # Unused import\n\ndef test_function():\n    pass\n')
            temp_path = temp_file.name
        
        try:
            # Analyze the file
            with patch('sys.argv', ['coderefactor', 'analyze', temp_path]):
                with patch('builtins.print') as mock_print:
                    # Mock the CodeRefactorApp
                    with patch('coderefactor.cli.commands.CodeRefactorApp') as mock_app:
                        app_instance = MagicMock()
                        mock_app.return_value = app_instance
                        
                        # Mock the analyze_file method to return an issue
                        app_instance.analyze_file.return_value = {
                            'file_path': temp_path,
                            'issues': [
                                {
                                    'rule_id': 'W0611',
                                    'message': 'Unused import datetime',
                                    'line': 3,
                                    'column': 1,
                                    'severity': 'warning',
                                    'category': 'maintainability'
                                }
                            ],
                            'error': None
                        }
                        
                        analyze_command()
                        
                        # Verify the analyze_file method was called
                        app_instance.analyze_file.assert_called_once_with(temp_path, config=None)
                        
                        # Verify output was printed
                        assert mock_print.call_count > 0
                        # Check if the issue was in the output
                        output = ''.join(str(call[0][0]) for call in mock_print.call_args_list if call[0])
                        assert 'W0611' in output
                        assert 'Unused import datetime' in output
        finally:
            os.unlink(temp_path)

    def test_fix_workflow(self):
        """Test a typical fix workflow."""
        # Create a temporary Python file with an issue
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
            temp_file.write(b'import os\nimport sys\nimport datetime  # Unused import\n\ndef test_function():\n    pass\n')
            temp_path = temp_file.name
        
        try:
            # Fix the issue
            with patch('sys.argv', ['coderefactor', 'fix', temp_path, 'W0611']):
                with patch('builtins.print') as mock_print:
                    # Mock the CodeRefactorApp
                    with patch('coderefactor.cli.commands.CodeRefactorApp') as mock_app:
                        app_instance = MagicMock()
                        mock_app.return_value = app_instance
                        
                        # Mock the fix_issue method to return success
                        app_instance.fix_issue.return_value = {
                            'status': 'success',
                            'changes': 1,
                            'fixed_code': 'import os\nimport sys\n\ndef test_function():\n    pass\n',
                            'error': None
                        }
                        
                        fix_command()
                        
                        # Verify the fix_issue method was called
                        app_instance.fix_issue.assert_called_once_with(temp_path, 'W0611', config=None)
                        
                        # Verify output was printed
                        assert mock_print.call_count > 0
                        # Check if success message was in the output
                        output = ''.join(str(call[0][0]) for call in mock_print.call_args_list if call[0])
                        assert 'success' in output.lower()
                        assert '1' in output  # Should show 1 change
        finally:
            os.unlink(temp_path)