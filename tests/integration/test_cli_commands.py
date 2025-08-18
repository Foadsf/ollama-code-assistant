import pytest
from pathlib import Path
import yaml
from unittest.mock import patch
from click.testing import CliRunner

from oca.cli import cli

@pytest.fixture
def temp_git_repo(tmp_path: Path):
    """Creates a temporary git repository for integration tests."""
    project_path = tmp_path / "test_project"
    project_path.mkdir()
    
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=project_path):
        result = runner.invoke(cli, ["init"], catch_exceptions=False)
        assert result.exit_code == 0
    
    # Create a file
    (project_path / "main.py").write_text("def hello():\n    print('Hello')")
    
    # Initial commit
    import subprocess
    subprocess.run(["git", "add", "."], cwd=project_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=project_path, capture_output=True)
    
    return project_path

def test_init_command(tmp_path: Path):
    """Test the 'oca init' command."""
    # --- Setup ---
    project_dir = tmp_path / "new_project"
    project_dir.mkdir()

    # --- Action ---
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=project_dir):
        result = runner.invoke(cli, ["init"], catch_exceptions=False)

        # --- Assertions ---
        assert result.exit_code == 0
        assert "OCA initialized successfully" in result.output
        
        # Check for .git directory
        assert Path(".git").is_dir()
        
        # Check for .oca/config.yaml
        config_path = Path(".oca") / "config.yaml"
        assert config_path.is_file()
        
        # Check config content
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        assert "ollama" in config
        assert config["ollama"]["model"] == "codellama"

@patch('oca.core.session.OllamaClient')
def test_explain_command(mock_ollama_class, temp_git_repo):
    """Test the 'oca explain' command."""
    # --- Setup ---
    mock_ollama_instance = mock_ollama_class.return_value
    mock_ollama_instance.generate.return_value = "This is a test explanation."

    # --- Action ---
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=temp_git_repo):
        result = runner.invoke(
            cli,
            ["explain", "What does this code do?", "--file", "main.py"],
            catch_exceptions=False
        )

    # --- Assertions ---
    assert result.exit_code == 0
    assert "This is a test explanation." in result.output
    mock_ollama_instance.generate.assert_called_once()