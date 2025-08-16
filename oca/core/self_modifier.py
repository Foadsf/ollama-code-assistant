import subprocess
import os
import sys
import re
from pathlib import Path
from datetime import datetime
from typing import TypedDict, Optional

from rich.console import Console

from oca.utils.git import GitWrapper, GitError
from oca.core.self_analysis import ImprovementOpportunity
from oca.core.ollama import OllamaClient
from oca.core.editor import CodeEditor

class SelfModifierError(Exception):
    """Custom exception for self-modification errors."""
    pass

class ApplyResult(TypedDict):
    """Represents the result of a self-improvement application."""
    success: bool
    reason: str

def _parse_code_from_response(response: str) -> Optional[str]:
    """Extracts the first code block from a markdown-formatted response."""
    pattern = re.compile(r"```(?:\w+)?\n(.*?)\n```", re.DOTALL)
    match = pattern.search(response)
    if match:
        return match.group(1).strip()
    return None

class SelfModifier:
    """Safely modifies OCA's own code."""

    def __init__(self, repo_path: Path, ollama: OllamaClient, editor: CodeEditor):
        self.repo_path = repo_path
        self.git = GitWrapper(self.repo_path)
        self.ollama = ollama
        self.editor = editor
        self.console = Console()

    def apply_self_improvement(self, opportunity: ImprovementOpportunity) -> ApplyResult:
        """Complete workflow for applying a self-improvement."""
        original_branch = ""
        branch_name = ""
        try:
            original_branch = self.git.get_current_branch()
            branch_name = self.create_improvement_branch(opportunity)
            self.console.print(f"✅ Created and checked out new branch: [bold blue]{branch_name}[/bold blue]")

            if opportunity['type'] == "documentation":
                self._apply_docstring_improvement(opportunity)
            elif opportunity['type'] == "type_hints":
                self._apply_type_hint_improvement(opportunity)
            else:
                self._rollback_improvement(original_branch, branch_name)
                return {"success": False, "reason": f"Unsupported improvement type: {opportunity['type']}"}

            validation_result = self._validate_improvement()
            if not validation_result['success']:
                self._rollback_improvement(original_branch, branch_name)
                return validation_result

            commit_prefix = "docs" if opportunity['type'] == "documentation" else "style"
            commit_message = f"{commit_prefix}: {opportunity['description']}"
            self.git.commit(commit_message, add_all=True)
            self.console.print(f"📝 Committed changes with message: \"{commit_message}\"")
            self.console.print("\n🎉 [bold green]Self-improvement successful![/bold green]")
            self.console.print(f"Changes are on branch [bold blue]{branch_name}[/bold blue]. Please review and merge.")
            self.git._run_git(['checkout', original_branch])

            return {"success": True, "reason": f"Successfully applied {opportunity['type']} improvement"}

        except Exception as e:
            self.console.print(f"[bold red]An error occurred during self-modification: {e}[/bold red]")
            if original_branch and branch_name:
                self._rollback_improvement(original_branch, branch_name)
            return {"success": False, "reason": f"Failed to apply improvement: {e}"}

    def _apply_docstring_improvement(self, opportunity: ImprovementOpportunity):
        """Generates and applies a docstring."""
        self.console.print("🧠 Generating docstring with Ollama...")
        file_path = self.repo_path / opportunity['file_path']
        file_content = file_path.read_text()
        prompt = f"{opportunity['suggested_fix']}\n\nHere is the full content of the file `{opportunity['file_path']}`. Please return the complete, modified file content in a single markdown code block.\n\n```python\n{file_content}\n```"
        new_content_response = self.ollama.generate(prompt)
        new_content = _parse_code_from_response(new_content_response)

        if not new_content:
            raise SelfModifierError("Failed to parse new content from Ollama response.")

        self.console.print(f"✍️ Applying changes to [cyan]{opportunity['file_path']}[/cyan]...")
        self.editor.apply_changes(Path(opportunity['file_path']), new_content)

    def _apply_type_hint_improvement(self, opportunity: ImprovementOpportunity):
        """Generates and applies type hints."""
        self.console.print("🧠 Generating type hints with Ollama...")
        file_path = self.repo_path / opportunity['file_path']
        file_content = file_path.read_text()

        prompt = f"{opportunity['suggested_fix']}\n\nHere is the full content of the file `{opportunity['file_path']}`. Please return the complete, modified file content with the new type hints in a single markdown code block.\n\n```python\n{file_content}\n```"
        new_content_response = self.ollama.generate(prompt)
        new_content = _parse_code_from_response(new_content_response)

        if not new_content:
            raise SelfModifierError("Failed to parse new content from Ollama response.")

        self.console.print(f"✍️ Applying changes to [cyan]{opportunity['file_path']}[/cyan]...")
        self.editor.apply_changes(Path(opportunity['file_path']), new_content)

    def _validate_improvement(self) -> ApplyResult:
        """Runs the test suite to validate the changes."""
        self.console.print("🛡️ Running test suite to validate changes...")

        if os.getenv("OCA_MOCK_PYTEST") == "true":
            self.console.print("✅ [bold green]All tests passed! (mocked)[/bold green]")
            return {"success": True, "reason": "All tests passed (mocked)."}

        # Use the current python interpreter to run pytest as a module
        # This is more robust than hardcoding the path to the executable
        python_executable = sys.executable
        if not python_executable:
            raise SelfModifierError("Could not determine python executable from sys.executable.")

        result = subprocess.run(
            [python_executable, "-m", "pytest"],
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            self.console.print("✅ [bold green]All tests passed![/bold green]")
            return {"success": True, "reason": "All tests passed."}
        else:
            self.console.print("❌ [bold red]Tests failed after applying changes.[/bold red]")
            self.console.print("--- TEST OUTPUT ---")
            self.console.print(result.stdout)
            self.console.print(result.stderr)
            return {"success": False, "reason": "Tests failed after modification."}

    def _rollback_improvement(self, original_branch: str, new_branch: str):
        """Rolls back the changes by switching branch and deleting the new one."""
        try:
            self.console.print("⏪ Rolling back changes...")
            self.git._run_git(['checkout', original_branch])
            self.git._run_git(['branch', '-D', new_branch])
            self.console.print("✅ Rollback complete.")
        except GitError as e:
            self.console.print(f"[bold red]Rollback failed: {e}[/bold red]")

    def create_improvement_branch(self, improvement: ImprovementOpportunity) -> str:
        """Create an isolated Git branch for a self-improvement task."""
        improvement_type = improvement['type']
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        branch_name = f"oca/self-improve/{improvement_type}-{timestamp}"

        try:
            self.git._run_git(['checkout', '-b', branch_name])
            return branch_name
        except GitError as e:
            raise SelfModifierError(f"Failed to create improvement branch '{branch_name}': {e}")
