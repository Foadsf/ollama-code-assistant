import pytest
import tempfile
import shutil
from pathlib import Path

from oca.utils.git import GitWrapper

@pytest.fixture
def temp_git_repo():
    """Creates a temporary git repository for integration tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        git = GitWrapper(project_path)
        git.init_repo()
        (project_path / "test_file.txt").write_text("initial content")
        git.commit("Initial commit", add_all=True)
        yield project_path

def test_git_worktree_isolation(temp_git_repo):
    """
    Tests that changes made in a git worktree are isolated from the main branch.
    """
    # --- Setup ---
    project_path = temp_git_repo
    main_branch_git = GitWrapper(project_path)
    
    # --- Action ---
    # 1. Create a new worktree
    worktree_path = project_path / "worktree"
    worktree_branch = "test-branch"
    main_branch_git.create_worktree(worktree_path, worktree_branch)
    
    worktree_git = GitWrapper(worktree_path)

    # --- Assertions for Worktree Creation ---
    assert worktree_path.exists()
    assert worktree_git.get_current_branch() == worktree_branch
    assert main_branch_git.get_current_branch() != worktree_branch

    # --- Action ---
    # 2. Modify the file in the worktree
    (worktree_path / "test_file.txt").write_text("modified content")

    # --- Assertions for File Modification ---
    # The file in the worktree should be modified
    assert (worktree_path / "test_file.txt").read_text() == "modified content"
    # The file in the main branch should be unchanged
    assert (project_path / "test_file.txt").read_text() == "initial content"

    # --- Action ---
    # 3. Commit the change in the worktree
    worktree_git.commit("Modify file in worktree", add_all=True)

    # --- Assertions for Commit ---
    # The commit should be in the worktree's branch log
    worktree_log = worktree_git._run_git(['log', '--oneline']).stdout
    assert "Modify file in worktree" in worktree_log
    # The commit should NOT be in the main branch's log
    main_branch_log = main_branch_git._run_git(['log', '--oneline']).stdout
    assert "Modify file in worktree" not in main_branch_log

    # --- Cleanup ---
    main_branch_git.remove_worktree(worktree_path)
    assert not worktree_path.exists()
