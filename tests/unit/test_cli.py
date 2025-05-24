"""Tests for CLI interface."""

import pytest
from click.testing import CliRunner
from unittest.mock import Mock, patch
from oca.cli import cli


class TestCLI:
    """Test cases for CLI interface."""
    
    def test_cli_version(self):
        """Test CLI version option."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--version'])
        
        assert result.exit_code == 0
        assert "0.1.0" in result.output
    
    def test_cli_help(self):
        """Test CLI help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert "Ollama Code Assistant" in result.output
        assert "AI-powered coding with Git isolation" in result.output
    
    @patch('oca.cli.SessionManager')
    def test_init_command_success(self, mock_session_manager_class):
        """Test successful init command."""
        mock_session_manager = Mock()
        mock_session_manager_class.return_value = mock_session_manager
        
        runner = CliRunner()
        result = runner.invoke(cli, ['init'])
        
        assert result.exit_code == 0
        assert "✓ OCA initialized successfully" in result.output
        mock_session_manager.init_project.assert_called_once()
    
    @patch('oca.cli.SessionManager')
    def test_init_command_with_options(self, mock_session_manager_class):
        """Test init command with options."""
        mock_session_manager = Mock()
        mock_session_manager_class.return_value = mock_session_manager
        
        runner = CliRunner()
        result = runner.invoke(cli, ['init', '--model', 'llama2', '--config', '/path/to/config'])
        
        assert result.exit_code == 0
        mock_session_manager.init_project.assert_called_once_with(
            model='llama2',
            config_path='/path/to/config'
        )
    
    @patch('oca.cli.SessionManager')
    def test_init_command_error(self, mock_session_manager_class):
        """Test init command with error."""
        mock_session_manager = Mock()
        mock_session_manager.init_project.side_effect = Exception("Init failed")
        mock_session_manager_class.return_value = mock_session_manager
        
        runner = CliRunner()
        result = runner.invoke(cli, ['init'])
        
        assert result.exit_code == 1
        assert "✗ Error initializing OCA: Init failed" in result.output
    
    @patch('oca.cli.SessionManager')
    def test_explain_command_success(self, mock_session_manager_class):
        """Test successful explain command."""
        # Setup mock session and session manager
        mock_session = Mock()
        mock_session.explain.return_value = "This code does something useful"
        
        mock_session_manager = Mock()
        mock_session_manager.create_session.return_value.__enter__.return_value = mock_session
        mock_session_manager.create_session.return_value.__exit__.return_value = None
        mock_session_manager_class.return_value = mock_session_manager
        
        runner = CliRunner()
        result = runner.invoke(cli, ['explain', 'What does this code do?'])
        
        assert result.exit_code == 0
        assert "This code does something useful" in result.output
        mock_session.explain.assert_called_once_with('What does this code do?', target_file=None)
    
    @patch('oca.cli.SessionManager')
    def test_explain_command_with_file(self, mock_session_manager_class):
        """Test explain command with file option."""
        mock_session = Mock()
        mock_session.explain.return_value = "File explanation"
        
        mock_session_manager = Mock()
        mock_session_manager.create_session.return_value.__enter__.return_value = mock_session
        mock_session_manager.create_session.return_value.__exit__.return_value = None
        mock_session_manager_class.return_value = mock_session_manager
        
        runner = CliRunner()
        result = runner.invoke(cli, ['explain', '--file', 'test.py', 'Explain this file'])
        
        assert result.exit_code == 0
        mock_session.explain.assert_called_once_with('Explain this file', target_file='test.py')
    
    @patch('oca.cli.SessionManager')
    def test_explain_command_error(self, mock_session_manager_class):
        """Test explain command with error."""
        mock_session_manager = Mock()
        mock_session_manager.create_session.side_effect = Exception("Session failed")
        mock_session_manager_class.return_value = mock_session_manager
        
        runner = CliRunner()
        result = runner.invoke(cli, ['explain', 'What does this do?'])
        
        assert result.exit_code == 1
        assert "✗ Error: Session failed" in result.output
    
    def test_global_options(self):
        """Test global options are passed to context."""
        runner = CliRunner()
        
        # Test that global options don't cause errors
        result = runner.invoke(cli, [
            '--verbose',
            '--model', 'testmodel',
            '--branch', 'testbranch',
            '--no-commit',
            '--dry-run',
            '--help'
        ])
        
        assert result.exit_code == 0