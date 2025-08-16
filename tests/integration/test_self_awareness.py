import pytest
import tempfile
import shutil
import os
import subprocess
import sys
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, Mock

from oca.cli import cli
from oca.cli_v2 import self_improve as self_improve_v2
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

    # Create .oca directory for memory log
    (tmp_path / ".oca").mkdir()

    git.stage_all()
    git.commit("feat: Initial commit")

    return tmp_path

@patch('oca.core.session.OllamaClient.generate', return_value="This code appears to be a basic utility function.")
def test_explain_own_code(mock_generate, cli_runner, oca_project):
    """Test if OCA can explain its own CodeEditor."""
    os.chdir(oca_project)
    result = cli_runner.invoke(
        cli,
        ["explain", "Explain how the CodeEditor class works?", "--file", "oca/core/editor.py"],
        catch_exceptions=False
    )

    assert result.exit_code == 0
    assert "This code appears to be a basic utility function." in result.output

@patch('oca.core.session.OllamaClient.generate', return_value="Search Results")
def test_search_own_code_for_todos(mock_generate, cli_runner, oca_project):
    """Test if OCA can find TODOs in its own codebase."""
    os.chdir(oca_project)
    editor_path = oca_project / "oca/core/editor.py"
    original_content = editor_path.read_text()
    try:
        editor_path.write_text(original_content + "\n# TODO: Add more tests")

        result = cli_runner.invoke(
            cli,
            ["search", "Find all TODOs", "--regex", "TODO"],
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

@pytest.mark.skip(reason="Integration test needs environment-specific debugging")
def test_self_improve_add_type_hints_e2e(cli_runner, tmp_path):
    """Test the full end-to-end self-improvement workflow for adding a type hint in an isolated environment."""
    # 1. Create an isolated project
    project_dir = tmp_path / "isolated_project"
    project_dir.mkdir()

    # 2. Create a file with a missing type hint
    target_file = project_dir / "my_module.py"
    content_without_type_hint = "def my_function(param): return param"
    content_with_type_hint = "def my_function(param: int) -> int: return param"
    target_file.write_text(content_without_type_hint)

    # 3. Initialize git repo
    git = GitWrapper(project_dir)
    git.init_repo()
    git._run_git(["config", "user.email", "test@example.com"])
    git._run_git(["config", "user.name", "Test User"])
    git.stage_all()
    git.commit("Initial commit")

    # 4. Run the self-improvement command as a subprocess
    env = os.environ.copy()
    env["OCA_MOCK_OLLAMA"] = "true"
    env["OCA_MOCK_PYTEST"] = "true"
    project_root = Path(__file__).parent.parent.parent
    env["PYTHONPATH"] = str(project_root)
    result = subprocess.run(
        [sys.executable, "-m", "oca.cli_v2", "--auto", "--type", "type_hints"],
        capture_output=True, text=True, cwd=project_dir, env=env
    )

    # 6. Assertions
    assert result.returncode == 0, f"CLI command failed with stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
    assert "Self-improvement successful!" in result.stdout

    # Check that a commit was made with the correct message
    log_output = git._run_git(['log', '-1', '--pretty=%B']).stdout
    assert "style: Function 'my_function' is missing type hints for: param, return value" in log_output

    # Check that the file was actually modified
    modified_content = target_file.read_text()
    assert content_with_type_hint in modified_content
