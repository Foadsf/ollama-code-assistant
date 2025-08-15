import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from oca.core.self_improver import SelfImprover

@pytest.fixture
def improver(tmp_path):
    """Fixture for SelfImprover that uses a temporary directory."""
    with patch('oca.core.self_improver.SelfAnalyzer') as mock_analyzer_class, \
         patch('oca.core.self_improver.SelfModifier') as mock_modifier_class, \
         patch('oca.core.self_improver.ImprovementUI') as mock_ui_class, \
         patch('oca.core.self_improver.MemorySystem') as mock_memory_class:

        improver_instance = SelfImprover(root_path=tmp_path)
        improver_instance.analyzer = mock_analyzer_class.return_value
        improver_instance.modifier = mock_modifier_class.return_value
        improver_instance.ui = mock_ui_class.return_value
        improver_instance.memory = mock_memory_class.return_value
        yield improver_instance

def test_run_improvement_cycle_auto_mode(improver):
    """Test the run_improvement_cycle in auto mode."""
    mock_opportunity = {"type": "documentation", "description": "Missing docstring"}
    improver.analyzer.identify_improvement_opportunities.return_value = [mock_opportunity]
    mock_result = {"success": True, "reason": "Completed"}
    improver.modifier.apply_self_improvement.return_value = mock_result

    improver.run_improvement_cycle(auto=True, improvement_type=None, dry_run=False)

    improver.modifier.apply_self_improvement.assert_called_once_with(mock_opportunity)
    improver.memory.record_improvement_attempt.assert_called_once_with(mock_opportunity, mock_result)

def test_run_improvement_cycle_no_opportunities(improver):
    """Test the cycle when no opportunities are found."""
    improver.analyzer.identify_improvement_opportunities.return_value = []

    improver.run_improvement_cycle(auto=True, improvement_type=None, dry_run=False)

    improver.modifier.apply_self_improvement.assert_not_called()
    improver.memory.record_improvement_attempt.assert_not_called()

def test_run_improvement_cycle_interactive_mode(improver):
    """Test the run_improvement_cycle in interactive mode."""
    mock_opportunity1 = {"type": "documentation", "description": "Docstring 1"}
    mock_opportunity2 = {"type": "type_hints", "description": "Type hint 2"}
    improver.analyzer.identify_improvement_opportunities.return_value = [mock_opportunity1, mock_opportunity2]
    improver.memory.get_success_patterns.return_value = {} # Mock this call

    improver.ui.present_opportunities.return_value = [mock_opportunity1]
    mock_result = {"success": True, "reason": ""}
    improver.modifier.apply_self_improvement.return_value = mock_result

    improver.run_improvement_cycle(auto=False, improvement_type=None, dry_run=False)

    improver.modifier.apply_self_improvement.assert_called_once_with(mock_opportunity1)
    improver.memory.record_improvement_attempt.assert_called_once_with(mock_opportunity1, mock_result)

def test_run_improvement_cycle_prioritization(improver):
    """Test that opportunities are correctly prioritized based on success rates."""
    opp_docs = {"type": "documentation", "description": "Docstring"}
    opp_types = {"type": "type_hints", "description": "Type hint"}
    opp_refactor = {"type": "refactoring", "description": "Refactor"}

    # Unordered list of opportunities
    improver.analyzer.identify_improvement_opportunities.return_value = [opp_docs, opp_refactor, opp_types]

    # Mock success patterns with different success rates
    improver.memory.get_success_patterns.return_value = {
        "documentation": {"success_rate": 60.0},
        "type_hints": {"success_rate": 95.0},
        # 'refactoring' is not in memory, so it should get a default score of 50.0
    }

    # We are only testing the prioritization, so we can mock the UI to return nothing
    improver.ui.present_opportunities.return_value = []

    improver.run_improvement_cycle(auto=False, improvement_type=None, dry_run=True)

    # Assert that the opportunities were passed to the UI in the correct, prioritized order
    call_args = improver.ui.present_opportunities.call_args[0][0]
    assert len(call_args) == 3
    assert call_args[0]["type"] == "type_hints"  # Highest success rate
    assert call_args[1]["type"] == "documentation" # Medium success rate
    assert call_args[2]["type"] == "refactoring" # Default 50% success rate
