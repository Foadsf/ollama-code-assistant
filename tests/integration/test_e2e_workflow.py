import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from oca.core.session import Session
from oca.utils.git import GitWrapper

@pytest.fixture
def temp_git_repo():
    """Creates a temporary git repository for integration tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        git = GitWrapper(project_path)
        git.init_repo()
        # Create .oca dir for backups
        (project_path / ".oca").mkdir()
        yield project_path

@patch('oca.core.session.OllamaClient')
def test_fix_command_e2e_workflow(mock_ollama_class, temp_git_repo):
    """
    Tests the end-to-end workflow of the 'fix' command within a Session.
    This test bypasses the SessionManager to have more control and simplify the test setup.
    """
    # --- Setup ---
    project_path = temp_git_repo

    # Create a buggy file in the main branch
    buggy_code = "def buggy_function():\n    return 1 + '1'"
    buggy_file_path = project_path / "buggy_file.py"
    buggy_file_path.write_text(buggy_code)

    git = GitWrapper(project_path)
    git.commit("feat: Add buggy file", add_all=True)

    # Mock the OllamaClient
    mock_ollama_instance = Mock()
    fixed_code = "def buggy_function():\n    return 1 + 1"
    mock_ollama_instance.generate.return_value = f"```python\n{fixed_code}\n```"
    mock_ollama_class.return_value = mock_ollama_instance

    # --- Action ---
    # Manually create a session, as SessionManager is hard to test with its temp dirs
    session_git_wrapper = GitWrapper(project_path, verbose=True)
    session = Session(
        worktree_path=project_path,
        git_wrapper=session_git_wrapper,
        ollama_client=mock_ollama_instance,
        auto_commit=True,
        verbose=True
    )
    # Mock has_staged_changes to ensure commit happens
    session_git_wrapper.has_staged_changes = Mock(return_value=True)

    session.fix("Fix the type error", target_file="buggy_file.py")

    # --- Assertions ---
    # 1. Assert the file was modified correctly
    corrected_content = buggy_file_path.read_text()
    assert corrected_content == fixed_code

    # 2. Assert that a backup was created
    backup_dir = project_path / ".oca" / "backups"
    assert backup_dir.exists()
    backup_files = list(backup_dir.iterdir())
    assert len(backup_files) == 1
    assert backup_files[0].name.startswith("buggy_file.py")
    assert backup_files[0].name.endswith(".bak")

    # 3. Assert that a new commit was made
    log = git._run_git(['log', '--oneline']).stdout
    assert "fix: Apply fix for 'Fix the type error...'" in log
    assert "feat: Add buggy file" in log
    assert len(log.strip().split('\n')) == 2
