"""Session management and Git worktree handling for OCA."""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager
import yaml

from ..utils.git import GitWrapper, GitError
from .ollama import OllamaClient, OllamaError


class SessionError(Exception):
    """Session management error."""
    pass


class Session:
    """Represents an OCA session with isolated Git worktree."""
    
    def __init__(self, worktree_path: Path, git_wrapper: GitWrapper,
                 ollama_client: OllamaClient, auto_commit: bool = True,
                 verbose: bool = False) -> None:
        """Initialize session.
        
        Args:
            worktree_path: Path to the Git worktree
            git_wrapper: Git wrapper instance
            ollama_client: Ollama client instance
            auto_commit: Whether to auto-commit changes
            verbose: Enable verbose logging
        """
        self.worktree_path = worktree_path
        self.git = git_wrapper
        self.ollama = ollama_client
        self.auto_commit = auto_commit
        self.verbose = verbose
    
    def explain(self, prompt: str, target_file: Optional[str] = None) -> str:
        """Explain code based on prompt.
        
        Args:
            prompt: Explanation prompt
            target_file: Specific file to explain
            
        Returns:
            Explanation response
        """
        system_prompt = (
            "You are a code assistant. Analyze the given code and provide "
            "clear, helpful explanations. Focus on what the code does, how it works, "
            "and any important patterns or considerations."
        )
        
        context = ""
        if target_file:
            file_path = self.worktree_path / target_file
            if file_path.exists() and file_path.is_file():
                try:
                    context = f"File: {target_file}\n{file_path.read_text()}"
                except Exception as e:
                    if self.verbose:
                        print(f"Warning: Could not read file {target_file}: {e}")
        
        try:
            response = self.ollama.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                context=context
            )
            
            if self.auto_commit:
                commit_msg = f"OCA explain: {prompt}"
                if target_file:
                    commit_msg += f" (file: {target_file})"
                self._commit_session_log(commit_msg, "explain", prompt, response)
            
            return response
            
        except OllamaError as e:
            raise SessionError(f"Failed to generate explanation: {e}")
    
    def _commit_session_log(self, commit_msg: str, command: str, 
                           prompt: str, response: str) -> None:
        """Create a commit with session log.
        
        Args:
            commit_msg: Commit message
            command: OCA command used
            prompt: User prompt
            response: AI response
        """
        try:
            # Create session log
            log_file = self.worktree_path / ".oca" / "session.log"
            log_file.parent.mkdir(exist_ok=True)
            
            log_entry = f"""
--- OCA Session Entry ---
Command: {command}
Timestamp: {__import__('datetime').datetime.now().isoformat()}
Prompt: {prompt}
Response: {response}
---
"""
            
            with open(log_file, 'a') as f:
                f.write(log_entry)
            
            # Commit the log
            if self.git.has_changes():
                self.git.commit(commit_msg)
                
        except Exception as e:
            if self.verbose:
                print(f"Warning: Could not commit session log: {e}")


class SessionManager:
    """Manages OCA sessions and Git worktrees."""
    
    def __init__(self, verbose: bool = False, model: Optional[str] = None,
                 branch: Optional[str] = None, auto_commit: bool = True,
                 dry_run: bool = False) -> None:
        """Initialize session manager.
        
        Args:
            verbose: Enable verbose logging
            model: Ollama model to use
            branch: Custom branch name
            auto_commit: Whether to auto-commit changes
            dry_run: Dry run mode
        """
        self.verbose = verbose
        self.model = model or "codellama"
        self.branch = branch
        self.auto_commit = auto_commit
        self.dry_run = dry_run
        self.cwd = Path.cwd()
        
    def init_project(self, model: Optional[str] = None, 
                    config_path: Optional[str] = None) -> None:
        """Initialize OCA in the current project.
        
        Args:
            model: Default Ollama model
            config_path: Path to config file
        """
        if self.dry_run:
            print("DRY RUN: Would initialize OCA project")
            return
            
        # Check if already a git repo
        git = GitWrapper(self.cwd, verbose=self.verbose)
        if not git.is_git_repo():
            if self.verbose:
                print("Initializing Git repository...")
            git.init_repo()
        
        # Create .oca directory and config
        oca_dir = self.cwd / ".oca"
        oca_dir.mkdir(exist_ok=True)
        
        config = {
            'ollama': {
                'model': model or self.model,
                'api_url': 'http://localhost:11434',
                'timeout': 120,
                'max_tokens': 4096
            },
            'git': {
                'branch_prefix': 'oca',
                'auto_commit': True,
                'commit_style': 'conventional'
            },
            'safety': {
                'max_file_size': '10MB',
                'allowed_extensions': ['.py', '.js', '.ts', '.java', '.go', '.rs'],
                'ignore_patterns': ['*.pyc', '__pycache__', 'node_modules', '.git']
            },
            'logging': {
                'level': 'INFO',
                'file': '.oca/session.log'
            }
        }
        
        config_file = oca_dir / "config.yaml"
        if not config_file.exists():
            with open(config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
        
        # Add .oca to .gitignore if it exists
        gitignore = self.cwd / ".gitignore"
        if gitignore.exists():
            content = gitignore.read_text()
            if ".oca/" not in content:
                gitignore.write_text(content + "\n.oca/\n")
        
        if self.verbose:
            print(f"OCA initialized in {self.cwd}")
    
    @contextmanager
    def create_session(self):
        """Create an isolated OCA session with Git worktree.
        
        Yields:
            Session instance
        """
        if self.dry_run:
            print("DRY RUN: Would create session with Git worktree")
            # Create a mock session for dry run
            from unittest.mock import Mock
            mock_session = Mock()
            mock_session.explain = lambda prompt, target_file=None: f"DRY RUN: Would explain '{prompt}'"
            yield mock_session
            return
        
        git = GitWrapper(self.cwd, verbose=self.verbose)
        
        if not git.is_git_repo():
            raise SessionError("Not a Git repository. Run 'oca init' first.")
        
        # Generate branch name
        branch_name = self.branch or git.generate_branch_name()
        
        # Create temporary directory for worktree
        with tempfile.TemporaryDirectory(prefix="oca-session-") as temp_dir:
            worktree_path = Path(temp_dir) / "worktree"
            
            try:
                if self.verbose:
                    print(f"Creating worktree at {worktree_path} with branch {branch_name}")
                
                # Create worktree and new branch
                git.create_worktree(worktree_path, branch_name)
                
                # Create Git wrapper for the worktree
                worktree_git = GitWrapper(worktree_path, verbose=self.verbose)
                
                # Create Ollama client
                ollama_client = OllamaClient(model=self.model)
                
                # Create session
                session = Session(
                    worktree_path=worktree_path,
                    git_wrapper=worktree_git,
                    ollama_client=ollama_client,
                    auto_commit=self.auto_commit,
                    verbose=self.verbose
                )
                
                yield session
                
            except Exception as e:
                if self.verbose:
                    print(f"Session error: {e}")
                raise SessionError(f"Failed to create session: {e}")
            
            finally:
                # Cleanup worktree
                try:
                    if worktree_path.exists():
                        git.remove_worktree(worktree_path, force=True)
                        if self.verbose:
                            print(f"Cleaned up worktree {worktree_path}")
                except Exception as e:
                    if self.verbose:
                        print(f"Warning: Could not cleanup worktree: {e}")