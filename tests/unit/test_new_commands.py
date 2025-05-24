"""Tests for new OCA commands (fix, refactor, test, commit, search)."""

import pytest
from unittest.mock import Mock, patch
from oca.core.session import Session, SessionError
from oca.core.ollama import OllamaClient, OllamaError
from oca.utils.git import GitWrapper
from pathlib import Path


class TestNewSessionCommands:
    """Test cases for new Session commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.worktree_path = Path("/tmp/worktree")
        self.git_wrapper = Mock(spec=GitWrapper)
        self.ollama_client = Mock(spec=OllamaClient)
        
        self.session = Session(
            worktree_path=self.worktree_path,
            git_wrapper=self.git_wrapper,
            ollama_client=self.ollama_client,
            auto_commit=False,
            verbose=False
        )

    def test_fix_without_file(self):
        """Test fix command without specific file."""
        self.ollama_client.generate.return_value = "Fixed the TypeError by adding proper type checking"
        
        result = self.session.fix("Fix the TypeError in user authentication")
        
        assert result == "Fixed the TypeError by adding proper type checking"
        self.ollama_client.generate.assert_called_once()
        call_args = self.ollama_client.generate.call_args
        assert "debugging and fixing code issues" in call_args[1]['system_prompt']
        assert call_args[1]['prompt'] == "Fix the TypeError in user authentication"
        assert call_args[1]['context'] == ""

    def test_fix_with_error_message(self):
        """Test fix command with specific error message."""
        self.ollama_client.generate.return_value = "The error is caused by..."
        
        result = self.session.fix(
            "Fix this error",
            error_message="TypeError: unsupported operand type(s) for +: 'int' and 'str'"
        )
        
        assert result == "The error is caused by..."
        call_args = self.ollama_client.generate.call_args
        assert "TypeError: unsupported operand type(s)" in call_args[1]['context']

    def test_fix_with_file(self):
        """Test fix command with specific file."""
        self.ollama_client.generate.return_value = "File-specific fix"
        
        # Mock file reading
        mock_file = Mock()
        mock_file.exists.return_value = True
        mock_file.is_file.return_value = True
        mock_file.read_text.return_value = "def broken_function():\n    return 1 + '1'"
        
        with patch('pathlib.Path.__truediv__', return_value=mock_file):
            result = self.session.fix("Fix the type error", target_file="user.py")
        
        assert result == "File-specific fix"
        call_args = self.ollama_client.generate.call_args
        assert "File: user.py" in call_args[1]['context']
        assert "def broken_function" in call_args[1]['context']

    def test_fix_with_auto_commit(self):
        """Test fix command with auto-commit enabled."""
        self.session.auto_commit = True
        self.git_wrapper.has_changes.return_value = True
        self.ollama_client.generate.return_value = "Fixed the issue"
        
        with patch('builtins.open') as mock_open:
            with patch.object(Path, 'mkdir'):
                result = self.session.fix("Fix bug")
        
        assert result == "Fixed the issue"
        self.git_wrapper.commit.assert_called_once()
        commit_msg = self.git_wrapper.commit.call_args[0][0]
        assert "OCA fix: Fix bug" in commit_msg

    def test_refactor_basic(self):
        """Test basic refactor command."""
        self.ollama_client.generate.return_value = "Refactored code with improved structure"
        
        result = self.session.refactor("Convert callbacks to async/await")
        
        assert result == "Refactored code with improved structure"
        call_args = self.ollama_client.generate.call_args
        assert "specialized in refactoring" in call_args[1]['system_prompt']
        assert "best practices and modern patterns" in call_args[1]['system_prompt']

    def test_refactor_with_pattern(self):
        """Test refactor command with specific pattern."""
        self.ollama_client.generate.return_value = "Applied singleton pattern"
        
        result = self.session.refactor(
            "Apply design pattern",
            pattern="singleton"
        )
        
        assert result == "Applied singleton pattern"
        call_args = self.ollama_client.generate.call_args
        assert "Refactoring Pattern: singleton" in call_args[1]['context']

    def test_generate_tests_basic(self):
        """Test basic test generation command."""
        self.ollama_client.generate.return_value = "def test_user_authentication():\n    pass"
        
        result = self.session.generate_tests("Create tests for user auth")
        
        assert "def test_user_authentication" in result
        call_args = self.ollama_client.generate.call_args
        assert "specialized in test generation" in call_args[1]['system_prompt']
        assert "comprehensive, well-structured tests" in call_args[1]['system_prompt']

    def test_generate_tests_with_coverage(self):
        """Test test generation with coverage option."""
        self.ollama_client.generate.return_value = "Comprehensive test suite"
        
        result = self.session.generate_tests(
            "Create comprehensive tests",
            coverage=True
        )
        
        assert result == "Comprehensive test suite"
        call_args = self.ollama_client.generate.call_args
        assert "comprehensive test coverage" in call_args[1]['context']

    def test_generate_tests_with_style(self):
        """Test test generation with specific style."""
        self.ollama_client.generate.return_value = "Pytest-style tests"
        
        result = self.session.generate_tests(
            "Create tests",
            style="pytest"
        )
        
        assert result == "Pytest-style tests"
        call_args = self.ollama_client.generate.call_args
        assert "Test Style: pytest" in call_args[1]['context']

    def test_create_commit_basic(self):
        """Test basic commit creation."""
        self.git_wrapper.has_changes.return_value = True
        self.ollama_client.generate.return_value = "feat: add user authentication system"
        
        result = self.session.create_commit()
        
        assert result == "feat: add user authentication system"
        call_args = self.ollama_client.generate.call_args
        assert "Git commit message specialist" in call_args[1]['system_prompt']
        assert "conventional commit format" in call_args[1]['system_prompt']

    def test_create_commit_with_message(self):
        """Test commit creation with custom message."""
        self.git_wrapper.has_changes.return_value = True
        self.ollama_client.generate.return_value = "feat: custom feature implementation"
        
        result = self.session.create_commit(message="Add custom feature")
        
        assert result == "feat: custom feature implementation"
        call_args = self.ollama_client.generate.call_args
        assert call_args[1]['prompt'] == "Add custom feature"

    def test_create_commit_with_type(self):
        """Test commit creation with specific type."""
        self.git_wrapper.has_changes.return_value = True
        self.ollama_client.generate.return_value = "fix: resolve authentication bug"
        
        result = self.session.create_commit(commit_type="fix")
        
        assert result == "fix: resolve authentication bug"
        call_args = self.ollama_client.generate.call_args
        assert "Commit Type: fix" in call_args[1]['context']

    def test_create_commit_no_changes(self):
        """Test commit creation when no changes exist."""
        self.git_wrapper.has_changes.return_value = False
        self.ollama_client.generate.return_value = "No changes to commit"
        
        result = self.session.create_commit()
        
        assert result == "No changes to commit"
        call_args = self.ollama_client.generate.call_args
        assert "No changes detected" in call_args[1]['context']

    def test_search_code_basic(self):
        """Test basic code search."""
        self.ollama_client.generate.return_value = "Found authentication functions in auth.py"
        
        result = self.session.search_code("Find authentication functions")
        
        assert result == "Found authentication functions in auth.py"
        call_args = self.ollama_client.generate.call_args
        assert "code search and analysis assistant" in call_args[1]['system_prompt']

    def test_search_code_with_regex(self):
        """Test code search with regex pattern."""
        self.ollama_client.generate.return_value = "Found TODO comments in multiple files"
        
        result = self.session.search_code(
            "Find all TODO comments",
            regex="TODO|FIXME"
        )
        
        assert result == "Found TODO comments in multiple files"
        call_args = self.ollama_client.generate.call_args
        assert "Regex Pattern: TODO|FIXME" in call_args[1]['context']

    def test_search_code_with_type(self):
        """Test code search with specific type."""
        self.ollama_client.generate.return_value = "Found function definitions"
        
        result = self.session.search_code(
            "Find all functions",
            search_type="function"
        )
        
        assert result == "Found function definitions"
        call_args = self.ollama_client.generate.call_args
        assert "Search Type: function" in call_args[1]['context']

    def test_get_file_context_existing_file(self):
        """Test _get_file_context with existing file."""
        mock_file = Mock()
        mock_file.exists.return_value = True
        mock_file.is_file.return_value = True
        mock_file.read_text.return_value = "def example():\n    pass"
        
        with patch('pathlib.Path.__truediv__', return_value=mock_file):
            context = self.session._get_file_context("example.py")
        
        assert context == "File: example.py\ndef example():\n    pass"

    def test_get_file_context_missing_file(self):
        """Test _get_file_context with missing file."""
        mock_file = Mock()
        mock_file.exists.return_value = False
        
        with patch('pathlib.Path.__truediv__', return_value=mock_file):
            context = self.session._get_file_context("missing.py")
        
        assert context == ""

    def test_get_file_context_no_file(self):
        """Test _get_file_context with no file specified."""
        context = self.session._get_file_context(None)
        assert context == ""

    def test_ollama_error_handling(self):
        """Test error handling when Ollama fails."""
        self.ollama_client.generate.side_effect = OllamaError("Connection failed")
        
        with pytest.raises(SessionError, match="Failed to generate fix"):
            self.session.fix("Fix the bug")
        
        with pytest.raises(SessionError, match="Failed to generate refactoring"):
            self.session.refactor("Refactor code")
        
        with pytest.raises(SessionError, match="Failed to generate tests"):
            self.session.generate_tests("Create tests")
        
        with pytest.raises(SessionError, match="Failed to generate commit message"):
            self.session.create_commit()
        
        with pytest.raises(SessionError, match="Failed to perform search"):
            self.session.search_code("Search code")