"""Session management and Git worktree handling for OCA."""

import os
import tempfile
import shutil
import re
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager
import yaml
import click 

from ..utils.git import GitWrapper, GitError
from ..utils.git_safe import SafeGitWorktree, GitSafeError
from ..utils.files import FileScanner
from .ollama import OllamaClient, OllamaError, get_model
from .gemini_adapter import GeminiAdapter
from .editor import CodeEditor, EditorError
from .context import ContextAnalyzer 


class SessionError(Exception):
    """Session management error."""
    pass


class Session:
    """Represents an OCA session with isolated Git worktree."""
    
    def __init__(self, worktree_path: Path, git_wrapper: SafeGitWorktree, 
                 ai_client: any, auto_commit: bool = True,
                 verbose: bool = False, dry_run: bool = False) -> None:
        """Initialize session."""
        self.worktree_path = worktree_path
        self.git = git_wrapper
        self.ai_client = ai_client
        self.auto_commit = auto_commit
        self.verbose = verbose
        self.editor = CodeEditor(self.worktree_path)
        self.dry_run = dry_run # Added dry_run to Session constructor

    def _parse_code_from_response(self, response: str) -> Optional[str]:
        """Extracts the first code block from a markdown-formatted response."""
        pattern = re.compile(r"```(?:\w+)?\n(.*?)\n```", re.DOTALL)
        match = pattern.search(response)
        if match:
            return match.group(1).strip()
        return None

    def explain(self, prompt: str, target_file: Optional[str] = None) -> str:
        """Explain code based on prompt."""
        system_prompt = """You are an expert Python developer. Follow these steps:
1. Read the code carefully
2. Identify the main purpose and functionality
3. Explain any potential issues or improvements
4. Provide a clear, concise explanation

Code to analyze:
{code}

Question (if any): {question}
"""
        context = self._get_file_context(target_file)
        
        full_prompt = f"Question: {prompt}\n\n"
        
        try:
            response = self.ai_client.generate(
                prompt=full_prompt,
                system_prompt=system_prompt,
                context=context
            )
            return response
        except Exception as e:
            raise SessionError(f"Failed to generate explanation: {e}")
    
    def fix(self, prompt: str, error_message: Optional[str] = None, 
            target_file: Optional[str] = None) -> str:
        """Fix bugs or issues in code."""
        system_prompt = """You are an expert Python developer. Follow these steps:
1. Read the code carefully
2. Identify the specific issue: {issue}
3. Provide the corrected code
4. Explain what was fixed

Code to fix:
{code}

Issue to fix: {issue}

Provide only the corrected code in a code block, followed by a brief explanation.
"""
        context = self._get_file_context(target_file)
        
        full_prompt = f"User Request: {prompt}\n\n"
        if error_message:
            full_prompt += f"Error Message:\n{error_message}\n\n"
        full_prompt += "Provide the fixed code in a markdown block, and explain the fix."
        
        try:
            response = self.ai_client.generate(prompt=full_prompt, system_prompt=system_prompt, context=context)
            parsed_code = self._parse_code_from_response(response)
            
            if parsed_code and target_file:
                click.echo(f"Proposed fix for {target_file}:\n```\n{parsed_code}\n```")
                if self.dry_run or click.confirm("Apply this fix?"):
                    try:
                        self.editor.apply_changes(Path(target_file), parsed_code)
                        if self.auto_commit:
                            commit_msg = f"fix: Apply fix for '{prompt[:50]}'"
                            self.git.stage_all()
                            if self.git.has_staged_changes():
                                self.git.commit(commit_msg)
                        return f"✅ Applied fix to {target_file}.\n\n{response}"
                    except EditorError as e:
                        return f"❌ Failed to apply fix: {e}\n\n{response}"
            
            return response
        except Exception as e:
            raise SessionError(f"Failed to generate fix: {e}")
    
    def refactor(self, prompt: str, pattern: Optional[str] = None, 
                 target_file: Optional[str] = None) -> str:
        """Refactor code."""
        system_prompt = """You are an expert Python developer. Follow these steps:
1. Read the existing code
2. Apply the requested refactoring: {refactor_request}
3. Provide the improved code
4. Explain the improvements made

Code to refactor:
{code}

Refactoring request: {refactor_request}

Provide the refactored code in a code block, followed by explanation of improvements.
"""
        context = self._get_file_context(target_file)
        
        full_prompt = f"User Request: {prompt}\n\n"
        if pattern:
            full_prompt += f"Refactoring Pattern: {pattern}\n\n"
        full_prompt += "Provide the refactored code in a markdown block, and explain the refactoring."
        
        try:
            response = self.ai_client.generate(prompt=full_prompt, system_prompt=system_prompt, context=context)
            parsed_code = self._parse_code_from_response(response)

            if parsed_code and target_file:
                click.echo(f"Proposed refactoring for {target_file}:\n```\n{parsed_code}\n```")
                if self.dry_run or click.confirm("Apply this refactoring?"):
                    try:
                        self.editor.apply_changes(Path(target_file), parsed_code)
                        if self.auto_commit:
                            commit_msg = f"refactor: Apply refactoring for '{prompt[:50]}'"
                            self.git.stage_all()
                            if self.git.has_staged_changes():
                                self.git.commit(commit_msg)
                        return f"✅ Applied refactoring to {target_file}.\n\n{response}"
                    except EditorError as e:
                        return f"❌ Failed to apply refactoring: {e}\n\n{response}"

            return response
        except Exception as e:
            raise SessionError(f"Failed to generate refactoring: {e}")
    
    def generate_tests(self, prompt: str, coverage: bool = False, 
                      style: Optional[str] = None, target_file: Optional[str] = None) -> str:
        """Generate tests for code."""
        system_prompt = (
            "You are a code assistant specialized in test generation. "
            "Analyze the provided code context and the user's request. "
            "Create comprehensive, well-structured tests in a markdown code block. "
            "Cover edge cases, error conditions, and typical usage patterns. "
            "Explain the tests you generated. Only provide the code block for the tests, do not include any other text outside the code block."
        )
        context = self._get_file_context(target_file)
        
        full_prompt = f"User Request: {prompt}\n\n"
        if style:
            full_prompt += f"Test Style: {style}\n\n"
        if coverage:
            full_prompt += "Focus on comprehensive test coverage including edge cases.\n\n"
        full_prompt += "Provide the generated tests in a markdown block, and explain the tests."
        
        try:
            response = self.ai_client.generate(prompt=full_prompt, system_prompt=system_prompt, context=context)
            parsed_code = self._parse_code_from_response(response)
            
            if parsed_code:
                if target_file:
                    original_path = Path(target_file)
                    test_file_path = original_path.parent / f"test_{original_path.name}"
                else:
                    test_file_path = Path("tests/new_test.py")

                click.echo(f"Proposed test file content for {test_file_path}:\n```\n{parsed_code}\n```")
                if self.dry_run or click.confirm("Create this test file?"):
                    try:
                        self.editor.create_file(test_file_path, parsed_code)
                        if self.auto_commit:
                            commit_msg = f"test: Generate tests for '{target_file or prompt[:30]}'"
                            self.git.stage_all()
                            if self.git.has_staged_changes():
                                self.git.commit(commit_msg)
                        return f"✅ Generated test file at {test_file_path}.\n\n{response}"
                    except EditorError as e:
                        return f"❌ Failed to create test file: {e}\n\n{response}"
            
            return response
        except Exception as e:
            raise SessionError(f"Failed to generate tests: {e}")
    
    def create_commit(self, message: Optional[str] = None, 
                     commit_type: Optional[str] = None) -> str:
        """Create descriptive commits."""
        # This command should now be used to commit changes made without auto-commit.
        if self.auto_commit:
            return "Auto-commit is enabled. Changes are committed automatically after each command."

        system_prompt = (
            "You are a Git commit message specialist. Analyze the staged changes provided in the context "
            "and create a clear, descriptive commit message following conventional commit format. "
            "Focus on the 'why' and 'what' of the changes. "
            "Provide only the commit message, no other text."
        )
        context = ""
        try:
            if self.git.has_staged_changes():
                diff = self.git.get_diff(staged=True)
                context = f"Staged Git Diff:\n```diff\n{diff[:4000]}\n```\n\n"
            else:
                return "No staged changes to commit. Use commands like 'fix' or 'refactor' to make changes."
        except Exception as e:
            context = f"Could not analyze changes: {e}"
        
        full_prompt = f"User Request: {message or 'Generate a commit message for the staged changes.'}\n\n"
        if commit_type:
            full_prompt += f"Commit Type: {commit_type}\n\n"
        full_prompt += "Generate the commit message."
        
        try:
            response = self.ai_client.generate(prompt=full_prompt, system_prompt=system_prompt, context=context)
            # Ask user for confirmation before committing? For now, we commit directly.
            self.git.commit(response)
            return f"✅ Committed changes with message:\n{response}"
        except (Exception, GitError) as e:
            raise SessionError(f"Failed to generate or apply commit message: {e}")
    
    def search_code(self, prompt: str, regex: Optional[str] = None,
                   search_type: Optional[str] = None) -> str:
        """Search codebase."""
        system_prompt = (
            "You are a code search and analysis assistant. "
            "Analyze the user's request and the provided search results/context. "
            "Help users find specific code patterns, functions, classes, or concepts in their codebase. "
            "Provide clear guidance on where to look and what to search for. "
            "Summarize the findings and suggest next steps."
        )

        context_parts = []
        if regex:
            context_parts.append(f"Regex Pattern: {regex}")
        if search_type:
            context_parts.append(f"Search Type: {search_type}")
        
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
                    context_parts.append(f"Functions found:\n" + "\n".join(functions_found[:20]))
                else:
                    context_parts.append("No functions found in codebase.")

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
                    context_parts.append(f"Classes found:\n" + "\n".join(classes_found[:20]))
                else:
                    context_parts.append("No classes found in codebase.")

            elif regex:
                search_results = scanner.search_in_files(regex, is_regex=True)
                if search_results:
                    context_parts.append(f"Regex search results:\n")
                    for file_path, matches in list(search_results.items())[:10]:
                        context_parts.append(f"{file_path}: {len(matches)} matches")
                        for match in matches[:3]:
                            context_parts.append(f"  Line {match['line']}: {match['content'][:100]}")
                else:
                    context_parts.append(f"No matches found for regex: {regex}")

            else:
                keywords = [word for word in prompt.lower().split() if len(word) > 3 and word not in ['find', 'search', 'where', 'what', 'code']]
                if keywords:
                    search_results = scanner.search_in_files(keywords[0])
                    if search_results:
                        context_parts.append(f"Search results for '{keywords[0]}':\n")
                        for file_path, matches in list(search_results.items())[:5]:
                            context_parts.append(f"{file_path}: {len(matches)} matches")
                    else:
                        context_parts.append(f"No results found for keyword: {keywords[0]}")
                else:
                    context_parts.append("General codebase analysis requested.")

        except Exception as e:
            context_parts.append(f"Error during codebase scan: {e}")

        full_context = "\n\n".join(context_parts)
        full_prompt = f"User Request: {prompt}\n\nSearch Context:\n{full_context}\n\nSummarize the findings and suggest next steps."

        try:
            response = self.ai_client.generate(prompt=full_prompt, system_prompt=system_prompt, context=full_context)
            return response
        except Exception as e:
            raise SessionError(f"Failed to perform search: {e}")

    def _get_file_context(self, target_file: Optional[str]) -> str:
        """Get context from a target file, including its content and basic analysis."""
        if not target_file:
            return ""
        
        file_path = self.worktree_path / target_file
        if not file_path.exists() or not file_path.is_file():
            if self.verbose:
                print(f"Warning: Target file does not exist or is not a file: {target_file}")
            return ""

        context_str = f"### File: {target_file}\n\n"
        try:
            file_content = file_path.read_text()
            context_str += f"```\n{file_content}\n```\n\n"
        except Exception as e:
            if self.verbose:
                print(f"Warning: Could not read file {target_file}: {e}")
            return ""

        # Add basic analysis from ContextAnalyzer
        try:
            analyzer = ContextAnalyzer(self.worktree_path)
            if file_path.suffix == '.py':
                import_analysis = analyzer.analyze_imports(file_path.relative_to(self.worktree_path))
                if import_analysis:
                    context_str += "### Imports:\n"
                    for imp in import_analysis['imports']:
                        context_str += f"- import {imp}\n"
                    for module, names in import_analysis['from_imports'].items():
                        context_str += f"- from {module} import {', '.join(names)}\n"
                    context_str += "\n"

            # Add more analysis here as ContextAnalyzer features are implemented

        except Exception as e:
            if self.verbose:
                print(f"Warning: Could not analyze context for {target_file}: {e}")

        return context_str


class SessionManager:
    """Manages OCA sessions and Git worktrees."""
    
    def __init__(self, verbose: bool = False, model: Optional[str] = None,
                 branch: Optional[str] = None, auto_commit: bool = True,
                 dry_run: bool = False) -> None:
        self.verbose = verbose
        self.model = model
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
            'ollama': {'model': model or self.model or get_model(), 'api_url': 'http://localhost:11434', 'timeout': 180, 'max_tokens': 4096},
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
        
        # Use SafeGitWorktree for isolated operations
        safe_git = SafeGitWorktree(self.cwd, verbose=self.verbose)
        
        branch_name = self.branch or safe_git.generate_branch_name() 
        
        try:
            if self.verbose:
                print(f"Creating isolated worktree for branch {branch_name}")
            safe_git.create_isolated_worktree(branch_name)
            
            # The worktree_path is now managed by SafeGitWorktree
            worktree_path = safe_git.worktree_path 
            if not worktree_path:
                raise SessionError("Failed to get worktree path from SafeGitWorktree.")

            if os.environ.get('OCA_USE_GEMINI') == 'true':
                ai_client = GeminiAdapter(model=self.model)
            else:
                ai_client = OllamaClient(model=self.model)

            session = Session(
                worktree_path=worktree_path,
                git_wrapper=safe_git, 
                ai_client=ai_client,
                auto_commit=not self.dry_run and self.auto_commit,
                verbose=self.verbose,
                dry_run=self.dry_run 
            )
            yield session
        except GitSafeError as e:
            if self.verbose:
                print(f"Git Safe Session error: {e}")
            raise SessionError(f"Failed to create session due to Git issue: {e}")
        except Exception as e:
            if self.verbose:
                print(f"Session error: {e}")
            raise SessionError(f"Failed to create session: {e}")
        finally:
            # Ensure cleanup happens even if session creation fails mid-way
            try:
                safe_git.cleanup()
            except GitSafeError as e:
                if self.verbose:
                    print(f"Warning: Could not cleanup safe worktree: {e}")
