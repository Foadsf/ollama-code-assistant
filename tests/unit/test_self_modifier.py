import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from oca.core.self_modifier import SelfModifier, SelfModifierError
from oca.core.self_analysis import ImprovementOpportunity
from oca.utils.git import GitError
from oca.core.ollama import OllamaClient
from oca.core.editor import CodeEditor

@pytest.fixture
def modifier():
    """Fixture for SelfModifier."""
    root_path = Path("/test")
    with patch('oca.core.self_modifier.GitWrapper') as mock_git_class, \
         patch('oca.core.self_modifier.OllamaClient') as mock_ollama_class, \
         patch('oca.core.self_modifier.CodeEditor') as mock_editor_class:

        ollama_instance = mock_ollama_class.return_value
        editor_instance = mock_editor_class.return_value

        modifier_instance = SelfModifier(
            repo_path=root_path,
            ollama=ollama_instance,
            editor=editor_instance
        )
        modifier_instance.git = mock_git_class.return_value
        yield modifier_instance

@patch('pathlib.Path.exists', return_value=True)
@patch('pathlib.Path.read_text', return_value='def my_func(): pass')
@patch('oca.core.self_modifier._parse_code_from_response')
@patch('oca.core.self_modifier.subprocess.run')
def test_apply_self_improvement_success(mock_subprocess_run, mock_parse_code, mock_read_text, mock_path_exists, modifier):
    """Test the full successful workflow of applying a self-improvement."""
    opportunity: ImprovementOpportunity = {
        "type": "documentation", "description": "Missing docstring",
        "file_path": "file.py", "line_number": 1, "severity": "low",
        "estimated_effort": "low", "suggested_fix": "Add a docstring."
    }
    modifier.git.get_current_branch.return_value = "main"
    modifier.create_improvement_branch = Mock(return_value="self-improve-branch")
    modifier.ollama.generate.return_value = "response with code"
    mock_parse_code.return_value = "new file content"
    mock_subprocess_run.return_value = Mock(returncode=0)

    result = modifier.apply_self_improvement(opportunity)

    assert result["success"] is True
    modifier.create_improvement_branch.assert_called_once_with(opportunity)
    modifier.editor.apply_changes.assert_called_once()
    mock_subprocess_run.assert_called_once()
    modifier.git.commit.assert_called_once()
    modifier.git._run_git.assert_called_with(['checkout', 'main'])

@patch('pathlib.Path.exists', return_value=True)
@patch('pathlib.Path.read_text', return_value='def my_func(): pass')
@patch('oca.core.self_modifier._parse_code_from_response')
@patch('oca.core.self_modifier.subprocess.run')
def test_apply_self_improvement_test_failure(mock_subprocess_run, mock_parse_code, mock_read_text, mock_path_exists, modifier):
    """Test the workflow when validation (tests) fail."""
    opportunity: ImprovementOpportunity = {
        "type": "documentation", "description": "Missing docstring",
        "file_path": "file.py", "line_number": 1, "severity": "low",
        "estimated_effort": "low", "suggested_fix": "Add a docstring."
    }
    modifier.git.get_current_branch.return_value = "main"
    modifier.create_improvement_branch = Mock(return_value="self-improve-branch")
    mock_parse_code.return_value = "new file content"
    mock_subprocess_run.return_value = Mock(returncode=1, stderr="Tests failed")

    result = modifier.apply_self_improvement(opportunity)

    assert result["success"] is False
    assert "Tests failed" in result["reason"]
    modifier.git.commit.assert_not_called()
    modifier.git._run_git.assert_any_call(['checkout', 'main'])
    modifier.git._run_git.assert_any_call(['branch', '-D', 'self-improve-branch'])

def test_create_improvement_branch_success(modifier):
    """Test successful creation of an improvement branch."""
    opportunity: ImprovementOpportunity = {
        "type": "documentation", "description": "", "file_path": "", "line_number": 0,
        "severity": "", "estimated_effort": "", "suggested_fix": ""
    }
    modifier.git._run_git.return_value = Mock()

    with patch('oca.core.self_modifier.datetime') as mock_datetime:
        mock_datetime.now.return_value.strftime.return_value = "20240101-120000"
        branch_name = modifier.create_improvement_branch(opportunity)

    expected_branch_name = "oca/self-improve/documentation-20240101-120000"
    assert branch_name == expected_branch_name
    modifier.git._run_git.assert_called_once_with(['checkout', '-b', expected_branch_name])
