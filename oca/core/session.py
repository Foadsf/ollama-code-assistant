"""Session management and Git worktree handling for OCA."""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager
import yaml

from ..utils.git import GitWrapper, GitError
from ..utils.files import FileScanner
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
        
        context = self._get_file_context(target_file)
        
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
    
    def fix(self, prompt: str, error_message: Optional[str] = None, 
            target_file: Optional[str] = None) -> str:
        """Fix bugs or issues in code.
        
        Args:
            prompt: Bug fix prompt
            error_message: Specific error message to fix
            target_file: Specific file to fix
            
        Returns:
            Fix response with code changes
        """
        system_prompt = (
            "You are a code assistant specialized in debugging and fixing code issues. "
            "Analyze the code and error message, identify the root cause, and provide "
            "a clear fix with explanation. Focus on correct, safe, and maintainable solutions."
        )
        
        context = self._get_file_context(target_file)
        if error_message:
            context += f"\n\nError Message:\n{error_message}"
        
        try:
            response = self.ollama.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                context=context
            )
            
            if self.auto_commit:
                commit_msg = f"OCA fix: {prompt}"
                if target_file:
                    commit_msg += f" (file: {target_file})"
                if error_message:
                    commit_msg += f" (error: {error_message[:50]}...)"
                self._commit_session_log(commit_msg, "fix", prompt, response)
            
            return response
            
        except OllamaError as e:
            raise SessionError(f"Failed to generate fix: {e}")
    
    def refactor(self, prompt: str, pattern: Optional[str] = None, 
                 target_file: Optional[str] = None) -> str:
        """Refactor code.
        
        Args:
            prompt: Refactoring prompt
            pattern: Specific pattern to refactor
            target_file: Specific file to refactor
            
        Returns:
            Refactored code response
        """
        system_prompt = (
            "You are a code assistant specialized in refactoring. "
            "Improve code quality, maintainability, and performance while "
            "preserving functionality. Follow best practices and modern patterns."
        )
        
        context = self._get_file_context(target_file)
        if pattern:
            context += f"\n\nRefactoring Pattern: {pattern}"
        
        try:
            response = self.ollama.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                context=context
            )
            
            if self.auto_commit:
                commit_msg = f"OCA refactor: {prompt}"
                if target_file:
                    commit_msg += f" (file: {target_file})"
                if pattern:
                    commit_msg += f" (pattern: {pattern})"
                self._commit_session_log(commit_msg, "refactor", prompt, response)
            
            return response
            
        except OllamaError as e:
            raise SessionError(f"Failed to generate refactoring: {e}")
    
    def generate_tests(self, prompt: str, coverage: bool = False, 
                      style: Optional[str] = None, target_file: Optional[str] = None) -> str:
        """Generate tests for code.
        
        Args:
            prompt: Test generation prompt
            coverage: Whether to include coverage considerations
            style: Test style (pytest, unittest, etc.)
            target_file: Specific file/module to test
            
        Returns:
            Generated test code
        """
        system_prompt = (
            "You are a code assistant specialized in test generation. "
            "Create comprehensive, well-structured tests that cover edge cases, "
            "error conditions, and typical usage patterns. Write clear, maintainable tests."
        )
        
        context = self._get_file_context(target_file)
        if style:
            context += f"\n\nTest Style: {style}"
        if coverage:
            context += "\n\nFocus on comprehensive test coverage including edge cases."
        
        try:
            response = self.ollama.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                context=context
            )
            
            if self.auto_commit:
                commit_msg = f"OCA test: {prompt}"
                if target_file:
                    commit_msg += f" (file: {target_file})"
                if style:
                    commit_msg += f" (style: {style})"
                self._commit_session_log(commit_msg, "test", prompt, response)
            
            return response
            
        except OllamaError as e:
            raise SessionError(f"Failed to generate tests: {e}")
    
    def create_commit(self, message: Optional[str] = None, 
                     commit_type: Optional[str] = None) -> str:
        """Create descriptive commits.
        
        Args:
            message: Custom commit message
            commit_type: Commit type (feat, fix, docs, etc.)
            
        Returns:
            Generated commit message or confirmation
        """
        system_prompt = (
            "You are a Git commit message specialist. Analyze the changes and create "
            "clear, descriptive commit messages following conventional commit format. "
            "Focus on the 'why' and 'what' of the changes."
        )
        
        # Get git status and diff for context
        context = ""
        try:
            if self.git.has_changes():
                status = self.git.get_status()
                diff = self.git.get_diff()
                context = f"Git Status:\n{status}\n\nGit Diff:\n{diff[:2000]}..."  # Limit diff size
            else:
                context = "No changes detected in working directory."
        except Exception as e:
            context = f"Could not analyze changes: {e}"
        
        if commit_type:
            context += f"\n\nCommit Type: {commit_type}"
        
        prompt_text = message or "Analyze the changes and create an appropriate commit message"
        
        try:
            response = self.ollama.generate(
                prompt=prompt_text,
                system_prompt=system_prompt,
                context=context
            )
            
            if self.auto_commit:
                commit_msg = f"OCA commit: Generated commit message"
                self._commit_session_log(commit_msg, "commit", prompt_text, response)
            
            return response
            
        except OllamaError as e:
            raise SessionError(f"Failed to generate commit message: {e}")
    
    def search_code(self, prompt: str, regex: Optional[str] = None, 
                   search_type: Optional[str] = None) -> str:
        """Search codebase.
        
        Args:
            prompt: Search prompt
            regex: Regular expression pattern to search for
            search_type: Search type (comment, function, class, etc.)
            
        Returns:
            Search results and analysis
        """
        system_prompt = (
            "You are a code search and analysis assistant. Help users find specific "
            "code patterns, functions, classes, or concepts in their codebase. "
            "Provide clear guidance on where to look and what to search for."
        )
        
        context = ""
        if regex:
            context += f"Regex Pattern: {regex}\n"
        if search_type:
            context += f"Search Type: {search_type}\n"
        
        # Perform actual codebase scanning
        try:
            scanner = FileScanner(self.worktree_path)
            
            if search_type == "function":
                # Search for functions
                functions_found = []
                for file_path in scanner.scan_files(['.py', '.js', '.ts']):
                    functions = scanner.find_functions(file_path)
                    if functions:
                        relative_path = str(file_path.relative_to(self.worktree_path))
                        functions_found.append(f"{relative_path}: {len(functions)} functions")
                        for func in functions[:3]:  # Limit to first 3
                            functions_found.append(f"  - {func['name']} (line {func['line']})")
                
                if functions_found:
                    context += f"\nFunctions found:\n" + "\n".join(functions_found[:20])  # Limit output
                else:
                    context += "\nNo functions found in codebase."
            
            elif search_type == "class":
                # Search for classes
                classes_found = []
                for file_path in scanner.scan_files(['.py']):
                    classes = scanner.find_classes(file_path)
                    if classes:
                        relative_path = str(file_path.relative_to(self.worktree_path))
                        classes_found.append(f"{relative_path}: {len(classes)} classes")
                        for cls in classes[:3]:  # Limit to first 3
                            classes_found.append(f"  - {cls['name']} (line {cls['line']})")
                
                if classes_found:
                    context += f"\nClasses found:\n" + "\n".join(classes_found[:20])  # Limit output
                else:
                    context += "\nNo classes found in codebase."
            
            elif regex:
                # Search using regex
                search_results = scanner.search_in_files(regex, is_regex=True)
                if search_results:
                    context += f"\nRegex search results:\n"
                    for file_path, matches in list(search_results.items())[:10]:  # Limit files
                        context += f"{file_path}: {len(matches)} matches\n"
                        for match in matches[:3]:  # Limit matches per file
                            context += f"  Line {match['line']}: {match['content'][:100]}\n"
                else:
                    context += f"\nNo matches found for regex: {regex}"
            
            else:
                # General text search based on prompt keywords
                # Extract keywords from prompt for search
                keywords = [word for word in prompt.lower().split() 
                           if len(word) > 3 and word not in ['find', 'search', 'where', 'what', 'code']]
                
                if keywords:
                    search_results = scanner.search_in_files(keywords[0])  # Search first keyword
                    if search_results:
                        context += f"\nSearch results for '{keywords[0]}':\n"
                        for file_path, matches in list(search_results.items())[:5]:  # Limit files
                            context += f"{file_path}: {len(matches)} matches\n"
                    else:
                        context += f"\nNo results found for keyword: {keywords[0]}"
                else:
                    context += "\nGeneral codebase analysis requested."
        
        except Exception as e:
            context += f"\nError during codebase scan: {e}"
        
        try:
            response = self.ollama.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                context=context
            )
            
            if self.auto_commit:
                commit_msg = f"OCA search: {prompt}"
                if regex:
                    commit_msg += f" (regex: {regex})"
                self._commit_session_log(commit_msg, "search", prompt, response)
            
            return response
            
        except OllamaError as e:
            raise SessionError(f"Failed to perform search: {e}")
    
    def _get_file_context(self, target_file: Optional[str]) -> str:
        """Get context from a target file.
        
        Args:
            target_file: Path to the target file
            
        Returns:
            File content as context string
        """
        if not target_file:
            return ""
            
        file_path = self.worktree_path / target_file
        if file_path.exists() and file_path.is_file():
            try:
                return f"File: {target_file}\n{file_path.read_text()}"
            except Exception as e:
                if self.verbose:
                    print(f"Warning: Could not read file {target_file}: {e}")
        
        return ""
    
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
            mock_session.fix = lambda prompt, error_message=None, target_file=None: f"DRY RUN: Would fix '{prompt}'"
            mock_session.refactor = lambda prompt, pattern=None, target_file=None: f"DRY RUN: Would refactor '{prompt}'"
            mock_session.generate_tests = lambda prompt, coverage=False, style=None, target_file=None: f"DRY RUN: Would generate tests '{prompt}'"
            mock_session.create_commit = lambda message=None, commit_type=None: f"DRY RUN: Would create commit '{message or 'auto-generated'}'"
            mock_session.search_code = lambda prompt, regex=None, search_type=None: f"DRY RUN: Would search '{prompt}'"
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