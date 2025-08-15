import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import ast

from oca.core.self_analysis import SelfAnalyzer

@pytest.fixture
def analyzer():
    """Fixture for SelfAnalyzer."""
    with patch('oca.core.self_analysis.FileScanner') as mock_scanner:
        with patch('oca.core.self_analysis.ASTTools') as mock_ast_tools:
            analyzer_instance = SelfAnalyzer(root_path=Path("/test"))
            analyzer_instance.scanner = mock_scanner.return_value
            analyzer_instance.ast_tools = mock_ast_tools.return_value
            yield analyzer_instance

def test_analyze_code_quality_structure(analyzer):
    """Test the structure of the analyze_code_quality response."""
    analyzer._calculate_complexity = Mock(return_value={"average_complexity": 5})
    analyzer._check_test_coverage = Mock(return_value={"coverage_percentage": 90.0})
    analyzer._check_documentation = Mock(return_value={"documentation_coverage": 80.0})
    analyzer._analyze_dependencies = Mock(return_value={"count": 10})

    result = analyzer.analyze_code_quality()

    assert "complexity" in result
    assert "test_coverage" in result
    assert "documentation" in result
    assert "dependencies" in result
    assert result["complexity"]["average_complexity"] == 5
    assert result["test_coverage"]["coverage_percentage"] == 90.0
    assert result["documentation"]["documentation_coverage"] == 80.0
    assert result["dependencies"]["count"] == 10

def test_check_documentation(analyzer):
    """Test the documentation checking logic."""
    analyzer.scanner.scan_files.return_value = [Path("/test/file1.py")]

    func_with_doc = ast.FunctionDef(name='f1', body=[ast.Expr(value=ast.Constant(value='doc'))])
    func_without_doc = ast.FunctionDef(name='f2', body=[])
    mock_tree = ast.Module(body=[func_with_doc, func_without_doc], type_ignores=[])

    analyzer.ast_tools.parse_python_file.return_value = mock_tree
    analyzer.ast_tools.find_functions.return_value = [func_with_doc, func_without_doc]

    result = analyzer._check_documentation()

    assert result["total_functions"] == 2
    assert result["functions_with_docstrings"] == 1
    assert result["documentation_coverage"] == 50.0

def test_analyze_dependencies(analyzer):
    """Test the dependency analysis logic."""
    analyzer.scanner.scan_files.return_value = [Path("/test/file1.py")]

    import_node = ast.Import(names=[ast.alias(name='requests')])
    import_from_node = ast.ImportFrom(module='os', names=[ast.alias(name='path')], level=0)
    local_import_node = ast.ImportFrom(module='oca.utils', names=[ast.alias(name='files')], level=0)
    mock_tree = ast.Module(body=[import_node, import_from_node, local_import_node], type_ignores=[])

    analyzer.ast_tools.parse_python_file.return_value = mock_tree

    result = analyzer._analyze_dependencies()

    assert result["count"] == 2
    assert "requests" in result["dependencies"]
    assert "os" in result["dependencies"]
    assert "oca" not in result["dependencies"]

def test_placeholder_methods(analyzer):
    """Test that placeholder methods return dummy data and print warnings."""
    with patch('builtins.print') as mock_print:
        assert analyzer._calculate_complexity() == {"average_complexity": 0, "high_complexity_functions": []}
        mock_print.assert_called_with("Warning: Complexity calculation is a placeholder.")

        assert analyzer._check_test_coverage() == {"coverage_percentage": 0.0, "uncovered_files": []}
        mock_print.assert_called_with("Warning: Test coverage check is a placeholder.")

        assert analyzer.identify_improvement_opportunities() == []
        mock_print.assert_called_with("Warning: Improvement opportunity identification is a placeholder.")

        assert analyzer.suggest_next_features() == []
        mock_print.assert_called_with("Warning: Next feature suggestion is a placeholder.")
