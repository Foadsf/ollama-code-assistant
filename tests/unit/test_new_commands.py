"""Tests for new OCA commands (fix, refactor, test, commit, search)."""

import pytest
from unittest.mock import Mock, patch
from oca.core.session import Session, SessionError
from oca.core.ollama import OllamaClient, OllamaError
from oca.utils.git import GitWrapper
from oca.core.editor import CodeEditor, EditorError
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
        """Test fix command without specific file (should just return suggestion)."""
        self.ollama_client.generate.return_value = "```python\nprint('fixed')\n```"
        result = self.session.fix("Fix it")
        assert "```python" in result
        self.git_wrapper.commit.assert_not_called()

    @patch('oca.core.session.CodeEditor.apply_changes')
    def test_fix_with_file_and_commit(self, mock_apply_changes):
        """Test fix command with file and auto-commit."""
        self.session.auto_commit = True
        self.git_wrapper.has_staged_changes.return_value = True
        self.ollama_client.generate.return_value = "```python\nprint('fixed')\n```"
        
        result = self.session.fix("Fix it", target_file="test.py")

        assert "✅ Applied fix to test.py" in result
        mock_apply_changes.assert_called_once_with(Path("test.py"), "print('fixed')")
        self.git_wrapper.stage_all.assert_called_once()
        self.git_wrapper.commit.assert_called_once()

    @patch('oca.core.session.CodeEditor.apply_changes')
    def test_fix_with_file_no_code(self, mock_apply_changes):
        """Test fix command with file but no code in response."""
        self.ollama_client.generate.return_value = "No code block here."
        result = self.session.fix("Fix it", target_file="test.py")
        assert "No code block here." in result
        mock_apply_changes.assert_not_called()

    @patch('oca.core.session.CodeEditor.apply_changes')
    def test_fix_editor_error(self, mock_apply_changes):
        """Test fix command when CodeEditor fails."""
        mock_apply_changes.side_effect = EditorError("Permission denied")
        self.ollama_client.generate.return_value = "```python\nprint('fixed')\n```"

        result = self.session.fix("Fix it", target_file="test.py")
        
        assert "❌ Failed to apply fix: Permission denied" in result

    def test_refactor_basic(self):
        """Test basic refactor command."""
        self.ollama_client.generate.return_value = "Refactored code with improved structure"
        result = self.session.refactor("Convert callbacks to async/await")
        assert result == "Refactored code with improved structure"
        call_args = self.ollama_client.generate.call_args
        assert "specialized in refactoring" in call_args[1]['system_prompt']

    @patch('oca.core.session.CodeEditor.create_file')
    def test_generate_tests_with_target_file(self, mock_create_file):
        """Test test generation with a target file."""
        self.session.auto_commit = True
        self.git_wrapper.has_staged_changes.return_value = True
        self.ollama_client.generate.return_value = "```python\ndef test_new(): pass\n```"

        result = self.session.generate_tests("Create tests", target_file="src/code.py")

        assert "✅ Generated test file at src/test_code.py" in result
        mock_create_file.assert_called_once_with(Path("src/test_code.py"), "def test_new(): pass")
        self.git_wrapper.commit.assert_called_once()

    @patch('oca.core.session.CodeEditor.create_file')
    def test_generate_tests_no_target_file(self, mock_create_file):
        """Test test generation without a target file."""
        self.ollama_client.generate.return_value = "```python\ndef test_new(): pass\n```"

        result = self.session.generate_tests("Create tests")

        assert "✅ Generated test file at tests/new_test.py" in result
        mock_create_file.assert_called_once_with(Path("tests/new_test.py"), "def test_new(): pass")

    def test_create_commit_basic(self):
        """Test basic commit creation."""
        self.git_wrapper.has_staged_changes.return_value = True
        self.ollama_client.generate.return_value = "feat: add user authentication system"
        
        result = self.session.create_commit()
        
        assert "✅ Committed changes with message:" in result
        assert "feat: add user authentication system" in result
        self.git_wrapper.commit.assert_called_once_with("feat: add user authentication system")

    def test_create_commit_no_staged_changes(self):
        """Test commit creation when no changes are staged."""
        self.git_wrapper.has_staged_changes.return_value = False
        result = self.session.create_commit()
        assert "No staged changes to commit" in result
        self.ollama_client.generate.assert_not_called()

    def test_create_commit_auto_commit_enabled(self):
        """Test create_commit when auto_commit is on."""
        self.session.auto_commit = True
        result = self.session.create_commit()
        assert "Auto-commit is enabled" in result

    def test_search_code_basic(self):
        """Test basic code search."""
        self.ollama_client.generate.return_value = "Found authentication functions in auth.py"
        with patch('oca.core.session.FileScanner'):
            result = self.session.search_code("Find authentication functions")
        
        assert result == "Found authentication functions in auth.py"
        call_args = self.ollama_client.generate.call_args
        assert "code search and analysis assistant" in call_args[1]['system_prompt']

    def test_get_file_context_existing_file(self):
        """Test _get_file_context with existing file."""
        mock_file = Mock()
        mock_file.exists.return_value = True
        mock_file.is_file.return_value = True
        mock_file.read_text.return_value = "def example():\n    pass"
        
        with patch('pathlib.Path.__truediv__', return_value=mock_file):
            context = self.session._get_file_context("example.py")
        
        assert context == "File: example.py\ndef example():\n    pass"

    def test_ollama_error_handling(self):
        """Test error handling when Ollama fails."""
        self.ollama_client.generate.side_effect = OllamaError("Connection failed")
        
        with pytest.raises(SessionError, match="Failed to generate fix"):
            self.session.fix("Fix the bug")
        
        with pytest.raises(SessionError, match="Failed to generate refactoring"):
            self.session.refactor("Refactor code")
        
        with pytest.raises(SessionError, match="Failed to generate tests"):
            self.session.generate_tests("Create tests")
        
        self.git_wrapper.has_staged_changes.return_value = True
        with pytest.raises(SessionError, match="Failed to generate or apply commit message"):
            self.session.create_commit()
        
        with pytest.raises(SessionError, match="Failed to perform search"):
            self.session.search_code("Search code")