import pytest
import tempfile
import shutil
import os
import subprocess
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, Mock

from oca.cli import cli
from oca.utils.git import GitWrapper

@pytest.fixture
def cli_runner():
    """Fixture for invoking CLI commands."""
    return CliRunner()

@pytest.fixture
def oca_project(tmp_path):
    """Fixture to create a temporary copy of the OCA project with a git repo."""
    project_root = Path(__file__).parent.parent.parent
    ignore = shutil.ignore_patterns('.git', 'venv', '.pytest_cache', 'htmlcov', '.coverage')
    shutil.copytree(project_root, tmp_path, dirs_exist_ok=True, ignore=ignore)

    git = GitWrapper(tmp_path)
    git.init_repo()
    git._run_git(["config", "user.email", "test@example.com"])
    git._run_git(["config", "user.name", "Test User"])
    git.commit("feat: Initial commit", add_all=True)

    return tmp_path

def test_explain_own_code(cli_runner, oca_project):
    """Test if OCA can explain its own CodeEditor."""
    os.chdir(oca_project)
    result = cli_runner.invoke(
        cli,
        ["explain", "Explain how the CodeEditor class works?", "--file", "oca/core/editor.py"],
        env={"OCA_MOCK_OLLAMA": "true"},
        catch_exceptions=False
    )

    assert result.exit_code == 0
    assert "This code appears to be a basic utility function." in result.output

def test_search_own_code_for_todos(cli_runner, oca_project):
    """Test if OCA can find TODOs in its own codebase."""
    os.chdir(oca_project)
    editor_path = oca_project / "oca/core/editor.py"
    original_content = editor_path.read_text()
    try:
        editor_path.write_text(original_content + "\n# TODO: Add more tests")

        result = cli_runner.invoke(
            cli,
            ["search", "Find all TODOs", "--regex", "TODO"],
            env={"OCA_MOCK_OLLAMA": "true"},
            catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Search Results" in result.output

    finally:
        editor_path.write_text(original_content)

def test_refactor_own_code(cli_runner, oca_project):
    """Test if OCA can refactor one of its own files."""
    os.chdir(oca_project)
    file_to_refactor = "oca/core/ollama.py"

    mock_refactored_code = "# Refactored by OCA\nprint('hello')"

    with patch('oca.core.session.OllamaClient.generate', return_value=f"```python\n{mock_refactored_code}\n```"):
        result = cli_runner.invoke(
            cli,
            ["--branch", "test-refactor", "refactor", "Improve this file", "--file", file_to_refactor],
            catch_exceptions=False,
            env={"OCA_MOCK_OLLAMA": "false"}
        )

    assert result.exit_code == 0
    assert f"✅ Applied refactoring to {file_to_refactor}" in result.output

    git = GitWrapper(oca_project)
    branches = git._run_git(['branch']).stdout
    assert "test-refactor" in branches

    git._run_git(["checkout", "test-refactor"])
    refactored_content = (oca_project / file_to_refactor).read_text()
    assert refactored_content == mock_refactored_code

    log = git._run_git(['log', '--oneline']).stdout
    assert "refactor: Apply refactoring" in log

@patch('oca.cli.OllamaClient.generate')
def test_self_improve_add_docstring_e2e(mock_generate, cli_runner, oca_project):
    """Test the full end-to-end self-improvement workflow for adding a docstring."""
    os.chdir(oca_project)

    # --- Setup ---
    target_file = oca_project / "oca/core/self_modifier.py"
    original_content = target_file.read_text()
    content_without_docstring = original_content.replace('"""\n        Initializes the SelfModifier.\n\n        Args:\n            repo_path: The path to the repository to be modified (OCA\'s own repo).\n        """', '')
    target_file.write_text(content_without_docstring)

    git = GitWrapper(oca_project)
    git.commit("test: Remove docstring for testing", add_all=True)

    mock_generate.return_value = f"```python\n{original_content}\n```"

    original_subprocess_run = subprocess.run
    def mock_run(*args, **kwargs):
        if "pytest" in str(args[0]):
            return Mock(returncode=0, stdout="All tests passed", stderr="")
        return original_subprocess_run(*args, **kwargs)

    # --- Action ---
    with patch('subprocess.run', side_effect=mock_run):
        result = cli_runner.invoke(
            cli,
            ['self-improve', '--auto', '--type', 'documentation', '--plain-output'],
            catch_exceptions=False
        )

    # --- Assertions ---
    assert result.exit_code == 0
    output = result.output

    assert "Automatically applying first safe improvement" in output
    assert "Function '__init__' is missing a docstring." in output
    assert "Created and checked out new branch" in output
    assert "All tests passed!" in output
    assert "Self-improvement successful!" in output

    branches = git._run_git(['branch']).stdout
    assert "oca/self-improve/documentation" in branches
    current_branch = git.get_current_branch()
    assert current_branch != "oca/self-improve/documentation"
