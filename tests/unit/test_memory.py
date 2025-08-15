import pytest
import json
from unittest.mock import Mock, patch, mock_open
from pathlib import Path

from oca.core.memory import MemorySystem
from oca.core.self_analysis import ImprovementOpportunity
from oca.core.self_modifier import ApplyResult

@pytest.fixture
def memory_system(tmp_path):
    """Fixture for MemorySystem that uses a temporary directory."""
    memory_file = tmp_path / ".oca" / "memory.jsonl"
    return MemorySystem(memory_file=memory_file)

def test_record_improvement_attempt(memory_system):
    """Test that an improvement attempt is correctly recorded to the memory file."""
    opportunity: ImprovementOpportunity = {
        "type": "documentation",
        "description": "Missing docstring",
        "file_path": "file.py",
        "line_number": 1,
        "severity": "low",
        "estimated_effort": "low",
        "suggested_fix": "Add a docstring."
    }
    result: ApplyResult = {
        "success": True,
        "reason": "All tests passed."
    }

    with patch("builtins.open", mock_open()) as mocked_file:
        with patch('oca.core.memory.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00"

            memory_system.record_improvement_attempt(opportunity, result)

    # Assert that open was called with the correct file and mode
    mocked_file.assert_called_once_with(memory_system.memory_file, 'a')

    # Assert that the correct data was written to the file
    handle = mocked_file()
    written_data = handle.write.call_args[0][0]

    # The written data should be a JSON string followed by a newline
    assert written_data.endswith('\n')

    # Parse the JSON part of the string
    record = json.loads(written_data.strip())

    assert record["timestamp"] == "2024-01-01T12:00:00"
    assert record["improvement_type"] == "documentation"
    assert record["description"] == "Missing docstring"
    assert record["file_path"] == "file.py"
    assert record["success"] is True
    assert record["reason"] == "All tests passed."

def test_get_success_patterns(memory_system):
    """Test the success pattern analysis."""
    # Create a mock memory file content
    mock_records = [
        {"improvement_type": "documentation", "success": True},
        {"improvement_type": "documentation", "success": True},
        {"improvement_type": "documentation", "success": False},
        {"improvement_type": "type_hints", "success": True},
    ]
    mock_file_content = "\n".join(json.dumps(r) for r in mock_records)

    with patch("builtins.open", mock_open(read_data=mock_file_content)):
        with patch('pathlib.Path.exists', return_value=True):
            patterns = memory_system.get_success_patterns()

    assert "documentation" in patterns
    assert patterns["documentation"]["total_attempts"] == 3
    assert patterns["documentation"]["successful_attempts"] == 2
    assert patterns["documentation"]["success_rate"] == 66.67

    assert "type_hints" in patterns
    assert patterns["type_hints"]["total_attempts"] == 1
    assert patterns["type_hints"]["successful_attempts"] == 1
    assert patterns["type_hints"]["success_rate"] == 100.0
