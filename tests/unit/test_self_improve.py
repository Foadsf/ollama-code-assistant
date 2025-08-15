"""Tests specifically for the self-improve command."""

import pytest
from click.testing import CliRunner
from unittest.mock import Mock, patch, MagicMock
from oca.cli import cli
from oca.core.self_analysis import ImprovementOpportunity

class TestSelfImproveCommand:
    """Dedicated tests for the self-improve command."""

    @patch('oca.cli.SelfAnalyzer')
    def test_self_improve_command_dry_run(self, mock_analyzer_class):
        """Test the self-improve command in dry-run mode."""
        mock_analyzer = mock_analyzer_class.return_value
        mock_opportunity: ImprovementOpportunity = {
            "type": "documentation",
            "description": "Function 'test' is missing a docstring.",
            "file_path": "oca/test.py",
            "line_number": 10,
            "severity": "medium",
            "estimated_effort": "low",
            "suggested_fix": "Add a docstring."
        }
        mock_analyzer.identify_improvement_opportunities.return_value = [mock_opportunity]

        runner = CliRunner()
        result = runner.invoke(cli, ['self-improve', '--dry-run', '--plain-output'])

        assert result.exit_code == 0

        output = result.output
        assert "OCA Self-Improvement Mode" in output
        assert "Found 1 improvement opportunities" in output
        assert "Function 'test' is missing a docstring." in output
        assert "oca/test.py:10" in output
        assert "--dry-run enabled. No changes will be made." in output
