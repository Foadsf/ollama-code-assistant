"""Tests for Git operations."""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from oca.utils.git import GitWrapper, GitError


class TestGitWrapper:
    """Test cases for GitWrapper."""
    
    def test_init(self):
        """Test GitWrapper initialization."""
        repo_path = Path("/test/repo")
        git = GitWrapper(repo_path, verbose=True)
        
        assert git.repo_path == repo_path
        assert git.verbose is True
    
    @patch('subprocess.run')
    def test_run_git_success(self, mock_run):
        """Test successful git command execution."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=['git', 'status'],
            returncode=0,
            stdout='clean working tree',
            stderr=''
        )
        
        git = GitWrapper(Path("/test"))
        result = git._run_git(['status'])
        
        assert result.stdout == 'clean working tree'
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_run_git_failure(self, mock_run):
        """Test git command failure."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=['git', 'invalid'],
            stderr='unknown command'
        )
        
        git = GitWrapper(Path("/test"))
        
        with pytest.raises(GitError, match="Git command failed"):
            git._run_git(['invalid'])
    
    @patch('subprocess.run')
    def test_is_git_repo_true(self, mock_run):
        """Test checking if directory is a git repo (positive case)."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=['git', 'rev-parse', '--git-dir'],
            returncode=0,
            stdout='.git',
            stderr=''
        )
        
        git = GitWrapper(Path("/test"))
        assert git.is_git_repo() is True
    
    @patch('subprocess.run')
    def test_is_git_repo_false(self, mock_run):
        """Test checking if directory is a git repo (negative case)."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=128,
            cmd=['git', 'rev-parse', '--git-dir'],
            stderr='not a git repository'
        )
        
        git = GitWrapper(Path("/test"))
        assert git.is_git_repo() is False
    
    @patch('subprocess.run')
    def test_init_repo(self, mock_run):
        """Test repository initialization."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=['git', 'init'],
            returncode=0,
            stdout='Initialized empty Git repository',
            stderr=''
        )
        
        git = GitWrapper(Path("/test"))
        git.init_repo()
        
        mock_run.assert_called_once_with(
            ['git', 'init'],
            cwd=Path("/test"),
            capture_output=True,
            text=True,
            check=True
        )
    
    @patch('subprocess.run')
    def test_get_current_branch(self, mock_run):
        """Test getting current branch name."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=['git', 'branch', '--show-current'],
            returncode=0,
            stdout='main\n',
            stderr=''
        )
        
        git = GitWrapper(Path("/test"))
        branch = git.get_current_branch()
        
        assert branch == 'main'
    
    @patch('subprocess.run')
    def test_create_worktree(self, mock_run):
        """Test creating a git worktree."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=['git', 'worktree', 'add', '-b', 'test-branch', '/tmp/worktree'],
            returncode=0,
            stdout='Preparing worktree',
            stderr=''
        )
        
        git = GitWrapper(Path("/test"))
        worktree_path = Path("/tmp/worktree")
        
        with patch('pathlib.Path.exists', return_value=False):
            git.create_worktree(worktree_path, 'test-branch')
        
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_create_worktree_exists_error(self, mock_run):
        """Test creating worktree when path already exists."""
        git = GitWrapper(Path("/test"))
        worktree_path = Path("/tmp/worktree")
        
        with patch('pathlib.Path.exists', return_value=True):
            with pytest.raises(GitError, match="Worktree path already exists"):
                git.create_worktree(worktree_path, 'test-branch')
    
    @patch('subprocess.run')
    def test_remove_worktree(self, mock_run):
        """Test removing a git worktree."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=['git', 'worktree', 'remove', '/tmp/worktree'],
            returncode=0,
            stdout='',
            stderr=''
        )
        
        git = GitWrapper(Path("/test"))
        git.remove_worktree(Path("/tmp/worktree"))
        
        mock_run.assert_called_once_with(
            ['git', 'worktree', 'remove', '/tmp/worktree'],
            cwd=Path("/test"),
            capture_output=True,
            text=True,
            check=True
        )
    
    @patch('subprocess.run')
    def test_remove_worktree_force(self, mock_run):
        """Test force removing a git worktree."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=['git', 'worktree', 'remove', '/tmp/worktree', '--force'],
            returncode=0,
            stdout='',
            stderr=''
        )
        
        git = GitWrapper(Path("/test"))
        git.remove_worktree(Path("/tmp/worktree"), force=True)
        
        expected_args = ['git', 'worktree', 'remove', '/tmp/worktree', '--force']
        mock_run.assert_called_once_with(
            expected_args,
            cwd=Path("/test"),
            capture_output=True,
            text=True,
            check=True
        )
    
    def test_generate_branch_name(self):
        """Test branch name generation."""
        git = GitWrapper(Path("/test"))
        
        with patch('oca.utils.git.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20240101-120000"
            branch_name = git.generate_branch_name("test")
            
        assert branch_name == "test/session-20240101-120000"
    
    @patch('subprocess.run')
    def test_commit(self, mock_run):
        """Test creating a commit."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=['git', 'commit', '-m', 'test commit'],
            returncode=0,
            stdout='[main abc123] test commit',
            stderr=''
        )
        
        git = GitWrapper(Path("/test"))
        git.commit("test commit")
        
        # Should be called twice: git add . and git commit
        assert mock_run.call_count == 2
    
    @patch('subprocess.run')
    def test_commit_no_add(self, mock_run):
        """Test creating a commit without adding files."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=['git', 'commit', '-m', 'test commit'],
            returncode=0,
            stdout='[main abc123] test commit',
            stderr=''
        )
        
        git = GitWrapper(Path("/test"))
        git.commit("test commit", add_all=False)
        
        # Should be called once: git commit only
        assert mock_run.call_count == 1
    
    @patch('subprocess.run')
    def test_has_changes_true(self, mock_run):
        """Test checking for changes when there are changes."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=['git', 'status', '--porcelain'],
            returncode=0,
            stdout='M file.txt\n',
            stderr=''
        )
        
        git = GitWrapper(Path("/test"))
        assert git.has_changes() is True
    
    @patch('subprocess.run')
    def test_has_changes_false(self, mock_run):
        """Test checking for changes when there are no changes."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=['git', 'status', '--porcelain'],
            returncode=0,
            stdout='',
            stderr=''
        )
        
        git = GitWrapper(Path("/test"))
        assert git.has_changes() is False