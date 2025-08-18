import os
from pathlib import Path
import shutil
from click.testing import CliRunner
from oca.cli import cli

def setup_test_env():
    """Set up a clean test environment."""
    teardown_test_env()
    os.makedirs(".oca", exist_ok=True)

def teardown_test_env():
    """Clean up the test environment."""
    if os.path.exists(".oca"):
        shutil.rmtree(".oca")
    if os.path.exists(".git"):
        shutil.rmtree(".git")

def test_init_creates_default_config():
    """Verify that `oca init` creates a config with the default model."""
    print("--- Running Test Case 1: `init` creates default config ---")
    setup_test_env()

    runner = CliRunner()
    result = runner.invoke(cli, ['init'])

    assert result.exit_code == 0, f"CLI command failed: {result.output}"

    config_path = Path(".oca/config.yaml")
    assert config_path.exists(), "Config file was not created."

    import yaml
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    assert config['ollama']['model'] == 'qwen2:7b', f"Model in config is {config['ollama']['model']}, expected qwen2:7b"

    print("✅ Test Case 1 Passed: `init` command created config with default model.")
    teardown_test_env()

if __name__ == "__main__":
    test_init_creates_default_config()
