"""Tests for session management."""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
from oca.core.session import Session, SessionManager, SessionError
from oca.utils.git import GitWrapper
from oca.core.ollama import OllamaClient


class TestSession:
    """Test cases for Session."""
    
    def test_init(self):
        """Test Session initialization."""
        worktree_path = Path("/tmp/worktree")
        git_wrapper = Mock(spec=GitWrapper)
        ollama_client = Mock(spec=OllamaClient)
        
        session = Session(
            worktree_path=worktree_path,
            git_wrapper=git_wrapper,
            ollama_client=ollama_client,
            auto_commit=True,
            verbose=True
        )
        
        assert session.worktree_path == worktree_path
        assert session.git == git_wrapper
        assert session.ollama == ollama_client
        assert session.auto_commit is True
        assert session.verbose is True
    
    def test_explain_no_file(self):
        """Test explain command without specific file."""
        worktree_path = Path("/tmp/worktree")
        git_wrapper = Mock(spec=GitWrapper)
        ollama_client = Mock(spec=OllamaClient)
        ollama_client.generate.return_value = "This code creates a function"
        
        session = Session(
            worktree_path=worktree_path,
            git_wrapper=git_wrapper,
            ollama_client=ollama_client,
            auto_commit=False
        )
        
        result = session.explain("What does this function do?")
        
        assert result == "This code creates a function"
        ollama_client.generate.assert_called_once()
        call_args = ollama_client.generate.call_args
        assert "code assistant" in call_args[1]['system_prompt'].lower()
        assert call_args[1]['prompt'] == "What does this function do?"
        assert call_args[1]['context'] == ""
    
    def test_explain_with_file(self):
        """Test explain command with specific file."""
        worktree_path = Path("/tmp/worktree")
        git_wrapper = Mock(spec=GitWrapper)
        ollama_client = Mock(spec=OllamaClient)
        ollama_client.generate.return_value = "This function calculates the sum"
        
        session = Session(
            worktree_path=worktree_path,
            git_wrapper=git_wrapper,
            ollama_client=ollama_client,
            auto_commit=False
        )
        
        # Mock file reading
        file_content = "def add(a, b):\n    return a + b"
        mock_file = Mock()
        mock_file.exists.return_value = True
        mock_file.is_file.return_value = True
        mock_file.read_text.return_value = file_content
        
        with patch('pathlib.Path.__truediv__', return_value=mock_file):
            result = session.explain("Explain this function", target_file="math.py")
        
        assert result == "This function calculates the sum"
        ollama_client.generate.assert_called_once()
        call_args = ollama_client.generate.call_args
        assert "File: math.py" in call_args[1]['context']
        assert file_content in call_args[1]['context']
    
    def test_explain_with_auto_commit(self):
        """Test explain command with auto-commit enabled."""
        worktree_path = Path("/tmp/worktree")
        git_wrapper = Mock(spec=GitWrapper)
        git_wrapper.has_changes.return_value = True
        ollama_client = Mock(spec=OllamaClient)
        ollama_client.generate.return_value = "Code explanation"
        
        session = Session(
            worktree_path=worktree_path,
            git_wrapper=git_wrapper,
            ollama_client=ollama_client,
            auto_commit=True
        )
        
        with patch('builtins.open', mock_open()) as mock_file:
            with patch.object(Path, 'mkdir'):
                result = session.explain("Explain the code")
        
        assert result == "Code explanation"
        git_wrapper.commit.assert_called_once()
        # Check that commit message includes the prompt
        commit_msg = git_wrapper.commit.call_args[0][0]
        assert "OCA explain" in commit_msg
        assert "Explain the code" in commit_msg


class TestSessionManager:
    """Test cases for SessionManager."""
    
    def test_init(self):
        """Test SessionManager initialization."""
        manager = SessionManager(
            verbose=True,
            model="testmodel",
            branch="testbranch",
            auto_commit=False,
            dry_run=True
        )
        
        assert manager.verbose is True
        assert manager.model == "testmodel"
        assert manager.branch == "testbranch"
        assert manager.auto_commit is False
        assert manager.dry_run is True
    
    def test_init_defaults(self):
        """Test SessionManager initialization with defaults."""
        manager = SessionManager()
        
        assert manager.verbose is False
        assert manager.model == "codellama"
        assert manager.branch is None
        assert manager.auto_commit is True
        assert manager.dry_run is False
    
    @patch('oca.core.session.GitWrapper')
    def test_init_project_new_repo(self, mock_git_class):
        """Test project initialization in new repository."""
        mock_git = Mock()
        mock_git.is_git_repo.return_value = False
        mock_git_class.return_value = mock_git
        
        manager = SessionManager()
        
        with patch.object(Path, 'mkdir') as mock_mkdir:
            with patch('builtins.open', mock_open()) as mock_file:
                with patch('yaml.dump') as mock_yaml_dump:
                    manager.init_project(model="testmodel")
        
        mock_git.init_repo.assert_called_once()
        mock_mkdir.assert_called_once()
        mock_yaml_dump.assert_called_once()
    
    @patch('oca.core.session.GitWrapper')
    def test_init_project_existing_repo(self, mock_git_class):
        """Test project initialization in existing repository."""
        mock_git = Mock()
        mock_git.is_git_repo.return_value = True
        mock_git_class.return_value = mock_git
        
        manager = SessionManager()
        
        with patch.object(Path, 'mkdir') as mock_mkdir:
            with patch('builtins.open', mock_open()) as mock_file:
                with patch('yaml.dump') as mock_yaml_dump:
                    manager.init_project()
        
        mock_git.init_repo.assert_not_called()
        mock_mkdir.assert_called_once()
    
    def test_init_project_dry_run(self):
        """Test project initialization in dry run mode."""
        manager = SessionManager(dry_run=True)
        
        # Should not raise any exceptions and not create files
        manager.init_project()
    
    @patch('oca.core.session.GitWrapper')
    @patch('tempfile.TemporaryDirectory')
    def test_create_session_dry_run(self, mock_tempdir, mock_git_class):
        """Test session creation in dry run mode."""
        manager = SessionManager(dry_run=True)
        
        with manager.create_session() as session:
            result = session.explain("test prompt")
            assert "DRY RUN" in result
    
    @patch('oca.core.session.GitWrapper')
    @patch('oca.core.session.OllamaClient')
    @patch('tempfile.TemporaryDirectory')
    def test_create_session_success(self, mock_tempdir, mock_ollama_class, mock_git_class):
        """Test successful session creation."""
        # Setup mocks
        mock_git = Mock()
        mock_git.is_git_repo.return_value = True
        mock_git.generate_branch_name.return_value = "oca/test-branch"
        mock_git_class.return_value = mock_git
        
        mock_tempdir_instance = MagicMock()
        mock_tempdir_instance.__enter__.return_value = "/tmp/test"
        mock_tempdir_instance.__exit__.return_value = None
        mock_tempdir.return_value = mock_tempdir_instance
        
        mock_ollama = Mock()
        mock_ollama_class.return_value = mock_ollama
        
        manager = SessionManager()
        
        with patch.object(Path, 'exists', return_value=True):
            with manager.create_session() as session:
                assert isinstance(session, Session)
        
        # Verify worktree was created and cleaned up
        mock_git.create_worktree.assert_called_once()
        mock_git.remove_worktree.assert_called_once()
    
    @patch('oca.core.session.GitWrapper')
    def test_create_session_not_git_repo(self, mock_git_class):
        """Test session creation when not in a git repo."""
        mock_git = Mock()
        mock_git.is_git_repo.return_value = False
        mock_git_class.return_value = mock_git
        
        manager = SessionManager()
        
        with pytest.raises(SessionError, match="Not a Git repository"):
            with manager.create_session():
                pass
    
    @patch('oca.core.session.GitWrapper')
    @patch('tempfile.TemporaryDirectory')
    def test_create_session_worktree_error(self, mock_tempdir, mock_git_class):
        """Test session creation when worktree creation fails."""
        mock_git = Mock()
        mock_git.is_git_repo.return_value = True
        mock_git.create_worktree.side_effect = Exception("Worktree creation failed")
        mock_git_class.return_value = mock_git
        
        mock_tempdir_instance = MagicMock()
        mock_tempdir_instance.__enter__.return_value = "/tmp/test"
        mock_tempdir_instance.__exit__.return_value = None
        mock_tempdir.return_value = mock_tempdir_instance
        
        manager = SessionManager()
        
        with pytest.raises(SessionError, match="Failed to create session"):
            with manager.create_session():
                pass