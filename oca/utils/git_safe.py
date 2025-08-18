import tempfile
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List
from datetime import datetime

class GitSafeError(Exception):
    """Safe Git operation error."""
    pass

class SafeGitWorktree:
    def __init__(self, source_repo_path: Path, verbose: bool = False):
        self.source_repo = source_repo_path.resolve()
        self.worktree_path: Optional[Path] = None
        self.verbose = verbose
        
    def _run_git_in_worktree(self, args: List[str], capture_output: bool = True, 
                             check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command within the isolated worktree."""
        if not self.worktree_path or not self.worktree_path.exists():
            raise GitSafeError("Worktree not initialized or does not exist.")
            
        cmd = ['git'] + args
        if self.verbose:
            print(f"Running in worktree {self.worktree_path}: {' '.join(cmd)}")
            
        try:
            result = subprocess.run(
                cmd, 
                cwd=self.worktree_path,
                capture_output=capture_output,
                text=True,
                check=check
            )
            if self.verbose and result.stdout:
                print(f"Worktree Output: {result.stdout.strip()}")
            if result.stderr and self.verbose:
                print(f"Worktree Stderr: {result.stderr.strip()}")
            return result
        except subprocess.CalledProcessError as e:
            raise GitSafeError(f"Git command failed in worktree: {' '.join(cmd)}\n{e.stderr}")
        except FileNotFoundError:
            raise GitSafeError("Git executable not found. Ensure Git is installed and in PATH.")

    def create_isolated_worktree(self, branch_name: str):
        """
        Creates a completely isolated Git repository by cloning the source.
        This ensures no modification to the original repository's worktrees.
        """
        if self.worktree_path and self.worktree_path.exists():
            raise GitSafeError("Worktree already exists. Call cleanup() first.")

        temp_dir = Path(tempfile.mkdtemp(prefix="oca-safe-worktree-"))
        self.worktree_path = temp_dir / "repo" # Clone into a subdirectory within temp_dir

        if self.verbose:
            print(f"Cloning {self.source_repo} to {self.worktree_path}")
        
        try:
            # Clone the source repository into the temporary worktree path
            subprocess.run(
                ['git', 'clone', str(self.source_repo), str(self.worktree_path)],
                check=True,
                capture_output=True,
                text=True
            )
            
            # Checkout the desired branch in the new worktree
            self._run_git_in_worktree(['checkout', '-b', branch_name])
            self.branch_name = branch_name
            
            if self.verbose:
                print(f"Successfully created isolated worktree at {self.worktree_path} on branch {self.branch_name}")
        except subprocess.CalledProcessError as e:
            self.cleanup() # Clean up if clone fails
            raise GitSafeError(f"Failed to clone repository for isolated worktree: {e.stderr}")
        except Exception as e:
            self.cleanup()
            raise GitSafeError(f"Unexpected error during worktree creation: {e}")

    def cleanup(self):
        """Safely remove the isolated worktree directory."""
        if self.worktree_path and self.worktree_path.exists():
            if self.verbose:
                print(f"Cleaning up isolated worktree at {self.worktree_path}")
            try:
                # Remove the entire temporary directory
                shutil.rmtree(self.worktree_path.parent)
                self.worktree_path = None
                self.branch_name = None
            except OSError as e:
                raise GitSafeError(f"Failed to remove worktree directory {self.worktree_path.parent}: {e}")
        else:
            if self.verbose:
                print("No worktree to clean up.")

    # Expose necessary GitWrapper methods, but operate on self.worktree_path
    def is_git_repo(self) -> bool:
        try:
            self._run_git_in_worktree(['rev-parse', '--git-dir'])
            return True
        except GitSafeError:
            return False

    def get_current_branch(self) -> str:
        result = self._run_git_in_worktree(['branch', '--show-current'])
        return result.stdout.strip()

    def commit(self, message: str, add_all: bool = False) -> None:
        if add_all:
            self.stage_all()
        self._run_git_in_worktree(['commit', '-m', message])

    def stage_all(self) -> None:
        self._run_git_in_worktree(['add', '.'])

    def stage_file(self, file_path: Path) -> None:
        self._run_git_in_worktree(['add', str(file_path)])

    def has_staged_changes(self) -> bool:
        return bool(self.get_diff(staged=True))
    
    def has_changes(self) -> bool:
        try:
            result = self._run_git_in_worktree(['status', '--porcelain'])
            return bool(result.stdout.strip())
        except GitSafeError:
            return False
    
    def get_diff(self, staged: bool = False) -> str:
        try:
            args = ['diff']
            if staged:
                args.append('--cached')
            result = self._run_git_in_worktree(args)
            return result.stdout
        except GitSafeError:
            return ""
    
    def get_status(self) -> str:
        try:
            result = self._run_git_in_worktree(['status', '--porcelain'])
            return result.stdout
        except GitSafeError:
            return ""
    
    def get_file_content(self, file_path: str, ref: str = "HEAD") -> str:
        try:
            result = self._run_git_in_worktree(['show', f'{ref}:{file_path}'])
            return result.stdout
        except GitSafeError:
            return ""

    def generate_branch_name(self, prefix: str = "oca") -> str:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"{prefix}/session-{timestamp}"
