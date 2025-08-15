import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from oca.core.self_modifier import SelfModifier, SelfModifierError
from oca.core.self_analysis import ImprovementOpportunity
from oca.utils.git import GitError

@pytest.fixture
def modifier():
    """Fixture for SelfModifier."""
    with patch('oca.core.self_modifier.GitWrapper') as mock_git_wrapper:
        modifier_instance = SelfModifier(repo_path=Path("/test"))
        modifier_instance.git = mock_git_wrapper.return_value
        yield modifier_instance

def test_create_improvement_branch_success(modifier):
    """Test successful creation of an improvement branch."""
    opportunity: ImprovementOpportunity = {
        "type": "documentation",
        "description": "Missing docstring",
        "file_path": "file.py",
        "line_number": 1,
        "severity": "low",
        "estimated_effort": "low",
        "suggested_fix": "Add a docstring."
    }

    modifier.git._run_git.return_value = Mock()

    with patch('oca.core.self_modifier.datetime') as mock_datetime:
        mock_datetime.now.return_value.strftime.return_value = "20240101-120000"
        branch_name = modifier.create_improvement_branch(opportunity)

    expected_branch_name = "oca/self-improve/documentation-20240101-120000"
    assert branch_name == expected_branch_name
    modifier.git._run_git.assert_called_once_with(['checkout', '-b', expected_branch_name])

def test_create_improvement_branch_git_error(modifier):
    """Test handling of GitError during branch creation."""
    opportunity: ImprovementOpportunity = {"type": "documentation", "description": "", "file_path": "", "line_number": 0, "severity": "", "estimated_effort": "", "suggested_fix": ""}

    modifier.git._run_git.side_effect = GitError("Branch already exists")

    with pytest.raises(SelfModifierError, match="Failed to create improvement branch"):
        modifier.create_improvement_branch(opportunity)
