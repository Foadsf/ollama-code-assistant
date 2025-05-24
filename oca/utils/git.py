"""Git operations wrapper for OCA."""

import subprocess
import tempfile
from pathlib import Path
from typing import Optional, List
from datetime import datetime


class GitError(Exception):
    """Git operation error."""
    pass


class GitWrapper:
    """Wrapper for Git operations with safety checks."""
    
    def __init__(self, repo_path: Path, verbose: bool = False) -> None:
        """Initialize Git wrapper.
        
        Args:
            repo_path: Path to the Git repository
            verbose: Enable verbose logging
        """
        self.repo_path = Path(repo_path)
        self.verbose = verbose
        
    def _run_git(self, args: List[str], capture_output: bool = True, 
                 check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command.
        
        Args:
            args: Git command arguments
            capture_output: Whether to capture output
            check: Whether to check return code
            
        Returns:
            CompletedProcess result
            
        Raises:
            GitError: If git command fails
        """
        cmd = ['git'] + args
        if self.verbose:
            print(f"Running: {' '.join(cmd)}")
            
        try:
            result = subprocess.run(
                cmd, 
                cwd=self.repo_path,
                capture_output=capture_output,
                text=True,
                check=check
            )
            if self.verbose and result.stdout:
                print(f"Output: {result.stdout.strip()}")
            return result
        except subprocess.CalledProcessError as e:
            raise GitError(f"Git command failed: {' '.join(cmd)}\n{e.stderr}")
    
    def is_git_repo(self) -> bool:
        """Check if the path is a Git repository."""
        try:
            self._run_git(['rev-parse', '--git-dir'])
            return True
        except GitError:
            return False
    
    def init_repo(self) -> None:
        """Initialize a new Git repository."""
        self._run_git(['init'])
        
    def get_current_branch(self) -> str:
        """Get the current branch name."""
        result = self._run_git(['branch', '--show-current'])
        return result.stdout.strip()
    
    def create_worktree(self, worktree_path: Path, branch_name: str, 
                       base_branch: Optional[str] = None) -> None:
        """Create a new Git worktree.
        
        Args:
            worktree_path: Path for the new worktree
            branch_name: Name of the new branch
            base_branch: Base branch for the new branch (defaults to current)
        """
        if worktree_path.exists():
            raise GitError(f"Worktree path already exists: {worktree_path}")
            
        # Create new branch and worktree
        args = ['worktree', 'add', '-b', branch_name, str(worktree_path)]
        if base_branch:
            args.append(base_branch)
        
        self._run_git(args)
    
    def remove_worktree(self, worktree_path: Path, force: bool = False) -> None:
        """Remove a Git worktree.
        
        Args:
            worktree_path: Path to the worktree to remove
            force: Force removal even if worktree is dirty
        """
        args = ['worktree', 'remove', str(worktree_path)]
        if force:
            args.append('--force')
        
        self._run_git(args)
    
    def list_worktrees(self) -> List[dict]:
        """List all worktrees.
        
        Returns:
            List of worktree information dicts
        """
        result = self._run_git(['worktree', 'list', '--porcelain'])
        worktrees = []
        current_worktree = {}
        
        for line in result.stdout.strip().split('\n'):
            if not line:
                if current_worktree:
                    worktrees.append(current_worktree)
                    current_worktree = {}
                continue
                
            if line.startswith('worktree '):
                current_worktree['path'] = line[9:]
            elif line.startswith('HEAD '):
                current_worktree['head'] = line[5:]
            elif line.startswith('branch '):
                current_worktree['branch'] = line[7:]
            elif line == 'bare':
                current_worktree['bare'] = True
            elif line == 'detached':
                current_worktree['detached'] = True
        
        if current_worktree:
            worktrees.append(current_worktree)
            
        return worktrees
    
    def generate_branch_name(self, prefix: str = "oca") -> str:
        """Generate a unique branch name.
        
        Args:
            prefix: Branch name prefix
            
        Returns:
            Unique branch name
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"{prefix}/session-{timestamp}"
    
    def commit(self, message: str, add_all: bool = True) -> None:
        """Create a commit.
        
        Args:
            message: Commit message
            add_all: Whether to add all changes before committing
        """
        if add_all:
            self._run_git(['add', '.'])
        
        self._run_git(['commit', '-m', message])
    
    def has_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        try:
            result = self._run_git(['status', '--porcelain'])
            return bool(result.stdout.strip())
        except GitError:
            return False