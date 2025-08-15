import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import ast

from oca.core.self_analysis import SelfAnalyzer, ImprovementOpportunity

@pytest.fixture
def analyzer():
    """Fixture for SelfAnalyzer."""
    root_path = Path("/test")
    with patch('oca.core.self_analysis.FileScanner') as mock_scanner_class:
        with patch('oca.core.self_analysis.ASTTools') as mock_ast_tools_class:
            analyzer_instance = SelfAnalyzer(root_path=root_path)
            analyzer_instance.scanner = mock_scanner_class.return_value
            analyzer_instance.ast_tools = mock_ast_tools_class.return_value
            yield analyzer_instance

def test_identify_missing_docstrings(analyzer):
    """Test the identify_improvement_opportunities for missing docstrings."""
    # Setup mock file and AST data
    file_path = analyzer.root_path / "module" / "file1.py"
    analyzer.scanner.scan_files.return_value = [file_path]

    func_without_doc = ast.FunctionDef(name='f2', body=[], lineno=10, col_offset=0)
    mock_tree = ast.Module(body=[func_without_doc], type_ignores=[])

    analyzer.ast_tools.parse_python_file.return_value = mock_tree
    analyzer.ast_tools.find_functions.return_value = [func_without_doc]

    # Run the method
    opportunities = analyzer.identify_improvement_opportunities()

    # Assertions
    assert len(opportunities) == 1
    opportunity = opportunities[0]

    assert opportunity['type'] == 'documentation'
    assert opportunity['description'] == "Function 'f2' is missing a docstring."
    assert opportunity['file_path'] == "module/file1.py"
    assert opportunity['line_number'] == 10
    assert opportunity['severity'] == 'medium'

def test_identify_no_opportunities(analyzer):
    """Test case where no improvement opportunities are found."""
    analyzer.scanner.scan_files.return_value = [Path("/test/file1.py")]

    func_with_doc = ast.FunctionDef(name='f1', body=[ast.Expr(value=ast.Constant(value='doc'))])
    mock_tree = ast.Module(body=[func_with_doc], type_ignores=[])

    analyzer.ast_tools.parse_python_file.return_value = mock_tree
    analyzer.ast_tools.find_functions.return_value = [func_with_doc]

    opportunities = analyzer.identify_improvement_opportunities()

    assert len(opportunities) == 0

def test_check_documentation(analyzer):
    """Test the old documentation checking logic for now."""
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
