"""
Tests for the Web interface and API.
"""
import os
import sys
import pytest
import json
import tempfile
from unittest.mock import patch, MagicMock
from pathlib import Path

# Import web interface components
from coderefactor.web.app import create_app
from coderefactor.web.routes import register_routes


class TestWebInterface:
    """Test suite for the web interface."""

    @pytest.fixture
    def app(self):
        """Create a test Flask application."""
        app = create_app(testing=True)
        app.config['TESTING'] = True
        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client for the Flask application."""
        return app.test_client()

    def test_app_creation(self, app):
        """Test that the app is created correctly."""
        assert app is not None
        assert app.config['TESTING'] is True

    def test_routes_registration(self, app):
        """Test that routes are registered correctly."""
        # Routes should be registered during app creation
        # Verify that the app has the expected routes
        url_map = app.url_map
        expected_routes = [
            '/', 
            '/analyze', 
            '/fix', 
            '/api/analyze', 
            '/api/fix',
            '/api/explain',
            '/api/file',
            '/api/save',
            '/api/config'
        ]
        
        # Check if routes exist
        for route in expected_routes:
            assert any(route in str(rule) for rule in url_map.iter_rules())

    def test_index_route(self, client):
        """Test the index route."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'<!DOCTYPE html>' in response.data
        assert b'CodeRefactor' in response.data

    def test_analyze_page(self, client):
        """Test the analyze page."""
        response = client.get('/analyze')
        assert response.status_code == 200
        assert b'<!DOCTYPE html>' in response.data
        assert b'analyze' in response.data.lower()

    def test_fix_page(self, client):
        """Test the fix page."""
        response = client.get('/fix')
        assert response.status_code == 200
        assert b'<!DOCTYPE html>' in response.data
        assert b'fix' in response.data.lower()

    def test_api_analyze_endpoint(self, client):
        """Test the API analyze endpoint."""
        with patch('coderefactor.web.routes.analyze_string') as mock_analyze:
            # Mock the analyze_string function to return a sample result
            mock_analyze.return_value = {
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
            
            # Make a POST request to the analyze endpoint
            response = client.post('/api/analyze',
                                  json={
                                      'code': 'import datetime\n\ndef test():\n    pass',
                                      'language': 'python'
                                  })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'issues' in data
            assert len(data['issues']) == 1
            assert data['issues'][0]['rule_id'] == 'W0611'
            
            # Verify mock was called with correct args
            mock_analyze.assert_called_once()
            args, kwargs = mock_analyze.call_args
            assert 'import datetime' in args[0]
            assert kwargs.get('file_type') == 'python'

    def test_api_analyze_with_invalid_json(self, client):
        """Test the API analyze endpoint with invalid JSON."""
        response = client.post('/api/analyze',
                              data='Invalid JSON',
                              content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_api_analyze_missing_required_field(self, client):
        """Test the API analyze endpoint with missing required field."""
        response = client.post('/api/analyze',
                              json={
                                  'code': 'import datetime\n\ndef test():\n    pass'
                                  # missing language field
                              })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'language' in data['error'].lower()

    def test_api_fix_endpoint(self, client):
        """Test the API fix endpoint."""
        with patch('coderefactor.web.routes.fix_issue') as mock_fix:
            # Mock the fix_issue function to return a sample result
            mock_fix.return_value = {
                'status': 'success',
                'original_code': 'import datetime\n\ndef test():\n    pass',
                'fixed_code': 'def test():\n    pass',
                'changes': [{'line': 1, 'description': 'Removed unused import datetime'}],
                'error': None
            }
            
            # Make a POST request to the fix endpoint
            response = client.post('/api/fix',
                                  json={
                                      'code': 'import datetime\n\ndef test():\n    pass',
                                      'issue': {
                                          'rule_id': 'W0611',
                                          'line': 1,
                                          'column': 1
                                      },
                                      'language': 'python'
                                  })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'success'
            assert 'fixed_code' in data
            assert 'import datetime' not in data['fixed_code']
            
            # Verify mock was called with correct args
            mock_fix.assert_called_once()

    def test_api_fix_with_invalid_issue(self, client):
        """Test the API fix endpoint with an invalid issue."""
        response = client.post('/api/fix',
                              json={
                                  'code': 'import datetime\n\ndef test():\n    pass',
                                  'issue': {
                                      'invalid': 'issue'  # Missing required issue fields
                                  },
                                  'language': 'python'
                              })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_api_explain_endpoint(self, client):
        """Test the API explain endpoint."""
        with patch('coderefactor.web.routes.explain_code') as mock_explain:
            # Mock the explain_code function to return a sample explanation
            mock_explain.return_value = 'This code imports datetime but does not use it. It defines a function named "test" that takes no arguments and does nothing.'
            
            # Make a POST request to the explain endpoint
            response = client.post('/api/explain',
                                  json={
                                      'code': 'import datetime\n\ndef test():\n    pass',
                                      'language': 'python'
                                  })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'explanation' in data
            assert 'imports datetime' in data['explanation']
            
            # Verify mock was called with correct args
            mock_explain.assert_called_once()
            args, kwargs = mock_explain.call_args
            assert 'import datetime' in args[0]
            assert args[1] == 'python'

    def test_api_file_load_endpoint(self, client):
        """Test the API file load endpoint."""
        # Create a temporary file to load
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
            temp_file.write(b'def test_function():\n    pass\n')
            temp_path = temp_file.name
        
        try:
            with patch('os.path.exists') as mock_exists:
                with patch('builtins.open', new_callable=MagicMock) as mock_open:
                    # Mock file existence check and open
                    mock_exists.return_value = True
                    mock_open().__enter__().read.return_value = 'def test_function():\n    pass\n'
                    
                    # Make a GET request to the file endpoint
                    response = client.get(f'/api/file?path={temp_path}')
                    
                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert 'content' in data
                    assert 'def test_function()' in data['content']
                    
                    # Verify mocks were called correctly
                    mock_exists.assert_called_with(temp_path)
                    mock_open.assert_called_with(temp_path, 'r', encoding='utf-8')
        finally:
            os.unlink(temp_path)

    def test_api_file_load_nonexistent(self, client):
        """Test the API file load endpoint with a nonexistent file."""
        response = client.get('/api/file?path=nonexistent_file.py')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
        assert 'not found' in data['error'].lower()

    def test_api_file_save_endpoint(self, client):
        """Test the API file save endpoint."""
        # Create a temporary file path to save to
        temp_file = tempfile.mktemp(suffix='.py')
        
        try:
            with patch('builtins.open', new_callable=MagicMock) as mock_open:
                # Make a POST request to the save endpoint
                response = client.post('/api/save',
                                      json={
                                          'path': temp_file,
                                          'content': 'def test_function():\n    pass\n'
                                      })
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['status'] == 'success'
                
                # Verify open was called with correct args
                mock_open.assert_called_with(temp_file, 'w', encoding='utf-8')
                handle = mock_open().__enter__()
                handle.write.assert_called_with('def test_function():\n    pass\n')
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_api_config_endpoint(self, client):
        """Test the API config endpoint."""
        with patch('coderefactor.web.routes.load_config') as mock_load:
            # Mock the load_config function to return a sample config
            mock_load.return_value = {
                'python': {
                    'enabled': True,
                    'tools': ['pylint', 'flake8']
                },
                'llm': {
                    'enabled': True,
                    'model': 'claude-3-7-sonnet-20250219'
                }
            }
            
            # Make a GET request to the config endpoint
            response = client.get('/api/config')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'python' in data
            assert data['python']['enabled'] is True
            assert 'llm' in data
            assert data['llm']['model'] == 'claude-3-7-sonnet-20250219'
            
            # Verify mock was called
            mock_load.assert_called_once()


class TestWebInterfaceIntegration:
    """Integration tests for the web interface."""

    @pytest.fixture
    def app(self):
        """Create a test Flask application."""
        # Create a real app with mocked dependencies
        with patch('coderefactor.CodeRefactorApp') as mock_app_class:
            app_instance = MagicMock()
            mock_app_class.return_value = app_instance
            
            # Setup sample responses for the mock
            app_instance.analyze_string.return_value = {
                'issues': [
                    {
                        'rule_id': 'W0611',
                        'message': 'Unused import datetime',
                        'line': 1,
                        'column': 1,
                        'severity': 'warning',
                        'category': 'maintainability'
                    }
                ],
                'error': None
            }
            
            app_instance.fix_issue.return_value = {
                'status': 'success',
                'original_code': 'import datetime\n\ndef test():\n    pass',
                'fixed_code': 'def test():\n    pass',
                'changes': [{'line': 1, 'description': 'Removed unused import datetime'}],
                'error': None
            }
            
            app = create_app(testing=True)
            app.config['TESTING'] = True
            return app

    @pytest.fixture
    def client(self, app):
        """Create a test client for the Flask application."""
        return app.test_client()

    def test_workflow(self, client):
        """Test a typical workflow of analysis and fixing."""
        # Step 1: Analyze code
        analyze_response = client.post('/api/analyze',
                                      json={
                                          'code': 'import datetime\n\ndef test():\n    pass',
                                          'language': 'python'
                                      })
        
        assert analyze_response.status_code == 200
        analyze_data = json.loads(analyze_response.data)
        assert 'issues' in analyze_data
        assert len(analyze_data['issues']) == 1
        issue = analyze_data['issues'][0]
        
        # Step 2: Fix the issue found in analysis
        fix_response = client.post('/api/fix',
                                  json={
                                      'code': 'import datetime\n\ndef test():\n    pass',
                                      'issue': issue,
                                      'language': 'python'
                                  })
        
        assert fix_response.status_code == 200
        fix_data = json.loads(fix_response.data)
        assert fix_data['status'] == 'success'
        assert 'fixed_code' in fix_data
        
        # Step 3: Save the fixed code
        temp_file = tempfile.mktemp(suffix='.py')
        try:
            with patch('builtins.open', new_callable=MagicMock):
                save_response = client.post('/api/save',
                                          json={
                                              'path': temp_file,
                                              'content': fix_data['fixed_code']
                                          })
                
                assert save_response.status_code == 200
                save_data = json.loads(save_response.data)
                assert save_data['status'] == 'success'
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_error_handling(self, client):
        """Test error handling in the web interface."""
        # Test handling of invalid language
        response = client.post('/api/analyze',
                              json={
                                  'code': 'import datetime\n\ndef test():\n    pass',
                                  'language': 'invalid_language'
                              })
        
        assert response.status_code in [400, 404, 422]  # Different valid status codes for error
        data = json.loads(response.data)
        assert 'error' in data

        # Test handling of server error
        with patch('coderefactor.web.routes.analyze_string') as mock_analyze:
            # Mock function to raise an exception
            mock_analyze.side_effect = Exception("Test server error")
            
            response = client.post('/api/analyze',
                                  json={
                                      'code': 'import datetime\n\ndef test():\n    pass',
                                      'language': 'python'
                                  })
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data
            assert 'server error' in data['error'].lower()