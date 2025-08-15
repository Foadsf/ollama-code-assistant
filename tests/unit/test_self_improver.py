import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from oca.core.self_improver import SelfImprover

@pytest.fixture
def improver(tmp_path):
    """Fixture for SelfImprover that uses a temporary directory."""
    with patch('oca.core.self_improver.SelfAnalyzer') as mock_analyzer_class, \
         patch('oca.core.self_improver.SelfModifier') as mock_modifier_class, \
         patch('oca.core.self_improver.ImprovementUI') as mock_ui_class:

        improver_instance = SelfImprover(root_path=tmp_path)
        improver_instance.analyzer = mock_analyzer_class.return_value
        improver_instance.modifier = mock_modifier_class.return_value
        improver_instance.ui = mock_ui_class.return_value
        yield improver_instance

def test_run_improvement_cycle_auto_mode(improver):
    """Test the run_improvement_cycle in auto mode."""
    mock_opportunity = {"type": "documentation", "description": "Missing docstring"}
    improver.analyzer.identify_improvement_opportunities.return_value = [mock_opportunity]
    improver.modifier.apply_self_improvement.return_value = {"success": True, "reason": ""}

    improver.run_improvement_cycle(auto=True, improvement_type=None, dry_run=False)

    improver.analyzer.identify_improvement_opportunities.assert_called_once()
    improver.ui.present_opportunities.assert_called_once_with([mock_opportunity])
    improver.modifier.apply_self_improvement.assert_called_once_with(mock_opportunity)

def test_run_improvement_cycle_no_opportunities(improver):
    """Test the cycle when no opportunities are found."""
    improver.analyzer.identify_improvement_opportunities.return_value = []

    improver.run_improvement_cycle(auto=True, improvement_type=None, dry_run=False)

    improver.ui.present_opportunities.assert_called_once_with([])
    improver.modifier.apply_self_improvement.assert_not_called()

def test_run_improvement_cycle_interactive_mode(improver):
    """Test the run_improvement_cycle in interactive mode."""
    mock_opportunity1 = {"type": "documentation", "description": "Docstring 1"}
    mock_opportunity2 = {"type": "type_hints", "description": "Type hint 2"}
    improver.analyzer.identify_improvement_opportunities.return_value = [mock_opportunity1, mock_opportunity2]

    improver.ui.present_opportunities.return_value = [mock_opportunity1]
    improver.modifier.apply_self_improvement.return_value = {"success": True, "reason": ""}

    improver.run_improvement_cycle(auto=False, improvement_type=None, dry_run=False)

    improver.ui.present_opportunities.assert_called_once()
    improver.modifier.apply_self_improvement.assert_called_once_with(mock_opportunity1)
