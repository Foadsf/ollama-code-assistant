"""Session management and Git worktree handling for OCA."""

import os
import tempfile
import shutil
import re
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager
import yaml

from ..utils.git import GitWrapper, GitError
from ..utils.files import FileScanner
from .ollama import OllamaClient, OllamaError
from .editor import CodeEditor, EditorError


class SessionError(Exception):
    """Session management error."""
    pass


class Session:
    """Represents an OCA session with isolated Git worktree."""
    
    def __init__(self, worktree_path: Path, git_wrapper: GitWrapper,
                 ollama_client: OllamaClient, auto_commit: bool = True,
                 verbose: bool = False) -> None:
        """Initialize session."""
        self.worktree_path = worktree_path
        self.git = git_wrapper
        self.ollama = ollama_client
        self.auto_commit = auto_commit
        self.verbose = verbose
        self.editor = CodeEditor(self.worktree_path)

    def _parse_code_from_response(self, response: str) -> Optional[str]:
        """Extracts the first code block from a markdown-formatted response."""
        pattern = re.compile(r"```(?:\w+)?\n(.*?)\n```", re.DOTALL)
        match = pattern.search(response)
        if match:
            return match.group(1).strip()
        return None

    def explain(self, prompt: str, target_file: Optional[str] = None) -> str:
        """Explain code based on prompt."""
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
            return response
        except OllamaError as e:
            raise SessionError(f"Failed to generate explanation: {e}")
    
    def fix(self, prompt: str, error_message: Optional[str] = None, 
            target_file: Optional[str] = None) -> str:
        """Fix bugs or issues in code."""
        system_prompt = (
            "You are a code assistant specialized in debugging and fixing code issues. "
            "Analyze the code and error message, identify the root cause, and provide "
            "a clear fix with explanation in a markdown code block. "
            "Focus on correct, safe, and maintainable solutions."
        )
        context = self._get_file_context(target_file)
        if error_message:
            context += f"\n\nError Message:\n{error_message}"
        
        try:
            response = self.ollama.generate(prompt=prompt, system_prompt=system_prompt, context=context)
            parsed_code = self._parse_code_from_response(response)
            
            if parsed_code and target_file:
                try:
                    self.editor.apply_changes(Path(target_file), parsed_code)
                    if self.auto_commit:
                        commit_msg = f"fix: Apply fix for '{prompt[:50]}...'"
                        self.git.stage_all()
                        if self.git.has_staged_changes():
                            self.git.commit(commit_msg)
                    return f"✅ Applied fix to {target_file}.\n\n{response}"
                except EditorError as e:
                    return f"❌ Failed to apply fix: {e}\n\n{response}"
            
            return response
        except OllamaError as e:
            raise SessionError(f"Failed to generate fix: {e}")
    
    def refactor(self, prompt: str, pattern: Optional[str] = None, 
                 target_file: Optional[str] = None) -> str:
        """Refactor code."""
        system_prompt = (
            "You are a code assistant specialized in refactoring. "
            "Improve code quality, maintainability, and performance while "
            "preserving functionality. Provide the refactored code in a "
            "markdown code block. Follow best practices and modern patterns."
        )
        context = self._get_file_context(target_file)
        if pattern:
            context += f"\n\nRefactoring Pattern: {pattern}"
        
        try:
            response = self.ollama.generate(prompt=prompt, system_prompt=system_prompt, context=context)
            parsed_code = self._parse_code_from_response(response)

            if parsed_code and target_file:
                try:
                    self.editor.apply_changes(Path(target_file), parsed_code)
                    if self.auto_commit:
                        commit_msg = f"refactor: Apply refactoring for '{prompt[:50]}...'"
                        self.git.stage_all()
                        if self.git.has_staged_changes():
                            self.git.commit(commit_msg)
                    return f"✅ Applied refactoring to {target_file}.\n\n{response}"
                except EditorError as e:
                    return f"❌ Failed to apply refactoring: {e}\n\n{response}"

            return response
        except OllamaError as e:
            raise SessionError(f"Failed to generate refactoring: {e}")
    
    def generate_tests(self, prompt: str, coverage: bool = False, 
                      style: Optional[str] = None, target_file: Optional[str] = None) -> str:
        """Generate tests for code."""
        system_prompt = (
            "You are a code assistant specialized in test generation. "
            "Create comprehensive, well-structured tests in a markdown code block. "
            "Cover edge cases, error conditions, and typical usage patterns."
        )
        context = self._get_file_context(target_file)
        if style:
            context += f"\n\nTest Style: {style}"
        if coverage:
            context += "\n\nFocus on comprehensive test coverage including edge cases."
        
        try:
            response = self.ollama.generate(prompt=prompt, system_prompt=system_prompt, context=context)
            parsed_code = self._parse_code_from_response(response)
            
            if parsed_code:
                if target_file:
                    original_path = Path(target_file)
                    test_file_path = original_path.parent / f"test_{original_path.name}"
                else:
                    test_file_path = Path("tests/new_test.py")

                try:
                    self.editor.create_file(test_file_path, parsed_code)
                    if self.auto_commit:
                        commit_msg = f"test: Generate tests for '{target_file or prompt[:30]}...'"
                        self.git.stage_all()
                        if self.git.has_staged_changes():
                            self.git.commit(commit_msg)
                    return f"✅ Generated test file at {test_file_path}.\n\n{response}"
                except EditorError as e:
                    return f"❌ Failed to create test file: {e}\n\n{response}"
            
            return response
        except OllamaError as e:
            raise SessionError(f"Failed to generate tests: {e}")
    
    def create_commit(self, message: Optional[str] = None, 
                     commit_type: Optional[str] = None) -> str:
        """Create descriptive commits."""
        # This command should now be used to commit changes made without auto-commit.
        if self.auto_commit:
            return "Auto-commit is enabled. Changes are committed automatically after each command."

        system_prompt = (
            "You are a Git commit message specialist. Analyze the staged changes and create "
            "a clear, descriptive commit message following conventional commit format. "
            "Focus on the 'why' and 'what' of the changes."
        )
        context = ""
        try:
            if self.git.has_staged_changes():
                diff = self.git.get_diff(staged=True)
                context = f"Staged Git Diff:\n{diff[:4000]}..."
            else:
                return "No staged changes to commit. Use commands like 'fix' or 'refactor' to make changes."
        except Exception as e:
            context = f"Could not analyze changes: {e}"
        
        if commit_type:
            context += f"\n\nCommit Type: {commit_type}"
        
        prompt_text = message or "Analyze the staged changes and create an appropriate commit message"
        
        try:
            response = self.ollama.generate(prompt=prompt_text, system_prompt=system_prompt, context=context)
            # Ask user for confirmation before committing? For now, we commit directly.
            self.git.commit(response)
            return f"✅ Committed changes with message:\n{response}"
        except (OllamaError, GitError) as e:
            raise SessionError(f"Failed to generate or apply commit message: {e}")
    
    def search_code(self, prompt: str, regex: Optional[str] = None,
                   search_type: Optional[str] = None) -> str:
        """Search codebase."""
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
        
        try:
            scanner = FileScanner(self.worktree_path)

            if search_type == "function":
                functions_found = []
                for file_path in scanner.scan_files(['.py', '.js', '.ts']):
                    functions = scanner.find_functions(file_path)
                    if functions:
                        relative_path = str(file_path.relative_to(self.worktree_path))
                        functions_found.append(f"{relative_path}: {len(functions)} functions")
                        for func in functions[:3]:
                            functions_found.append(f"  - {func['name']} (line {func['line']})")
                if functions_found:
                    context += f"\nFunctions found:\n" + "\n".join(functions_found[:20])
                else:
                    context += "\nNo functions found in codebase."

            elif search_type == "class":
                classes_found = []
                for file_path in scanner.scan_files(['.py']):
                    classes = scanner.find_classes(file_path)
                    if classes:
                        relative_path = str(file_path.relative_to(self.worktree_path))
                        classes_found.append(f"{relative_path}: {len(classes)} classes")
                        for cls in classes[:3]:
                            classes_found.append(f"  - {cls['name']} (line {cls['line']})")
                if classes_found:
                    context += f"\nClasses found:\n" + "\n".join(classes_found[:20])
                else:
                    context += "\nNo classes found in codebase."

            elif regex:
                search_results = scanner.search_in_files(regex, is_regex=True)
                if search_results:
                    context += f"\nRegex search results:\n"
                    for file_path, matches in list(search_results.items())[:10]:
                        context += f"{file_path}: {len(matches)} matches\n"
                        for match in matches[:3]:
                            context += f"  Line {match['line']}: {match['content'][:100]}\n"
                else:
                    context += f"\nNo matches found for regex: {regex}"

            else:
                keywords = [word for word in prompt.lower().split() if len(word) > 3 and word not in ['find', 'search', 'where', 'what', 'code']]
                if keywords:
                    search_results = scanner.search_in_files(keywords[0])
                    if search_results:
                        context += f"\nSearch results for '{keywords[0]}':\n"
                        for file_path, matches in list(search_results.items())[:5]:
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
            return response
        except OllamaError as e:
            raise SessionError(f"Failed to perform search: {e}")

    def _get_file_context(self, target_file: Optional[str]) -> str:
        """Get context from a target file."""
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


class SessionManager:
    """Manages OCA sessions and Git worktrees."""
    
    def __init__(self, verbose: bool = False, model: Optional[str] = None,
                 branch: Optional[str] = None, auto_commit: bool = True,
                 dry_run: bool = False) -> None:
        self.verbose = verbose
        self.model = model or "codellama"
        self.branch = branch
        self.auto_commit = auto_commit
        self.dry_run = dry_run
        self.cwd = Path.cwd()
        
    def init_project(self, model: Optional[str] = None, 
                    config_path: Optional[str] = None) -> None:
        """Initialize OCA in the current project."""
        if self.dry_run:
            print("DRY RUN: Would initialize OCA project")
            return
        git = GitWrapper(self.cwd, verbose=self.verbose)
        if not git.is_git_repo():
            if self.verbose:
                print("Initializing Git repository...")
            git.init_repo()
        oca_dir = self.cwd / ".oca"
        oca_dir.mkdir(exist_ok=True)
        config = {
            'ollama': {'model': model or self.model, 'api_url': 'http://localhost:11434', 'timeout': 180, 'max_tokens': 4096},
            'git': {'branch_prefix': 'oca', 'auto_commit': True, 'commit_style': 'conventional'},
            'safety': {'max_file_size': '10MB', 'allowed_extensions': ['.py', '.js', '.ts'], 'ignore_patterns': ['*.pyc', '__pycache__', 'node_modules', '.git']},
            'logging': {'level': 'INFO', 'file': '.oca/session.log'}
        }
        config_file = oca_dir / "config.yaml"
        if not config_file.exists():
            with open(config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
        gitignore = self.cwd / ".gitignore"
        if gitignore.exists():
            content = gitignore.read_text()
            if ".oca/" not in content:
                gitignore.write_text(content + "\n.oca/\n")
        if self.verbose:
            print(f"OCA initialized in {self.cwd}")
    
    @contextmanager
    def create_session(self):
        """Create an isolated OCA session with Git worktree."""
        if self.dry_run:
            print("DRY RUN: Would create session with Git worktree")
            from unittest.mock import Mock
            mock_session = Mock()
            mock_session.explain.return_value = "DRY RUN: explain"
            mock_session.fix.return_value = "DRY RUN: fix"
            mock_session.refactor.return_value = "DRY RUN: refactor"
            mock_session.generate_tests.return_value = "DRY RUN: generate_tests"
            mock_session.create_commit.return_value = "DRY RUN: create_commit"
            mock_session.search_code.return_value = "DRY RUN: search_code"
            yield mock_session
            return
        
        git = GitWrapper(self.cwd, verbose=self.verbose)
        if not git.is_git_repo():
            raise SessionError("Not a Git repository. Run 'oca init' first.")
        
        branch_name = self.branch or git.generate_branch_name()
        
        with tempfile.TemporaryDirectory(prefix="oca-session-") as temp_dir:
            worktree_path = Path(temp_dir) / "worktree"
            try:
                if self.verbose:
                    print(f"Creating worktree at {worktree_path} with branch {branch_name}")
                git.create_worktree(worktree_path, branch_name)
                worktree_git = GitWrapper(worktree_path, verbose=self.verbose)
                ollama_client = OllamaClient(model=self.model)
                session = Session(
                    worktree_path=worktree_path,
                    git_wrapper=worktree_git,
                    ollama_client=ollama_client,
                    auto_commit=not self.dry_run and self.auto_commit,
                    verbose=self.verbose
                )
                yield session
            except Exception as e:
                if self.verbose:
                    print(f"Session error: {e}")
                raise SessionError(f"Failed to create session: {e}")
            finally:
                try:
                    if worktree_path.exists():
                        git.remove_worktree(worktree_path, force=True)
                        if self.verbose:
                            print(f"Cleaned up worktree {worktree_path}")
                except Exception as e:
                    if self.verbose:
                        print(f"Warning: Could not cleanup worktree: {e}")