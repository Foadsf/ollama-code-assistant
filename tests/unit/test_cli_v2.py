import pytest
from click.testing import CliRunner
from unittest.mock import patch, Mock
from pathlib import Path

from oca.cli_v2 import self_improve

@patch('oca.cli_v2.SelfImprover')
def test_self_improve_cli_wrapper(mock_improver_class):
    """Test that the cli_v2 wrapper correctly calls SelfImprover."""
    runner = CliRunner()
    mock_improver_instance = mock_improver_class.return_value

    with patch('oca.cli_v2.Path.cwd') as mock_cwd:
        mock_cwd.return_value = Path("/test/project")

        result = runner.invoke(
            self_improve,
            ['--auto', '--type', 'documentation', '--dry-run', '--verbose', '--model', 'test-model']
        )

    assert result.exit_code == 0

    mock_improver_class.assert_called_once_with(
        root_path=Path("/test/project"),
        model_name='test-model',
        verbose=True
    )

    mock_improver_instance.run_improvement_cycle.assert_called_once_with(
        auto=True,
        improvement_type='documentation',
        dry_run=True
    )
