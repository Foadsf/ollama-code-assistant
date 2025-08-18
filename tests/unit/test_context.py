import pytest
from pathlib import Path
from unittest import mock

from oca.core.context import ContextAnalyzer

@pytest.fixture
def temp_project(tmp_path: Path):
    """Creates a temporary project structure for testing."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("import os\nfrom math import sqrt")
    (project_dir / "utils.js").write_text("console.log('hello');")
    (project_dir / "data").mkdir()
    (project_dir / "data" / "file.txt").write_text("some data")
    return project_dir

def test_context_analyzer_init(tmp_path: Path):
    """Test that the ContextAnalyzer is initialized correctly."""
    analyzer = ContextAnalyzer(tmp_path)
    assert analyzer.root_path == tmp_path

def test_analyze_project_structure_no_filter(temp_project: Path):
    """Test project structure analysis without any file extension filters."""
    analyzer = ContextAnalyzer(temp_project)
    structure = analyzer.analyze_project_structure()

    assert structure["root_path"] == str(temp_project)
    assert structure["file_count"] == 3
    assert "main.py" in structure["files"]
    assert "utils.js" in structure["files"]
    assert "data/file.txt" in structure["files"]
    assert structure["files"]["main.py"]["suffix"] == ".py"

def test_analyze_project_structure_with_filter(temp_project: Path):
    """Test project structure analysis with a file extension filter."""
    analyzer = ContextAnalyzer(temp_project)
    structure = analyzer.analyze_project_structure(extensions=[".py"])

    assert structure["file_count"] == 1
    assert "main.py" in structure["files"]
    assert "utils.js" not in structure["files"]

def test_analyze_project_structure_empty_dir(tmp_path: Path):
    """Test project structure analysis on an empty directory."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    analyzer = ContextAnalyzer(empty_dir)
    structure = analyzer.analyze_project_structure()

    assert structure["file_count"] == 0
    assert structure["files"] == {}

def test_analyze_project_structure_os_error(temp_project: Path):
    """Test that OSError is handled when a file is deleted after scanning."""
    analyzer = ContextAnalyzer(temp_project)
    
    # Create mock Path objects
    file1 = temp_project / "file1.py"
    file2 = temp_project / "file2.py"
    
    # Mock the stat method on one of the Path objects to raise an OSError
    mock_file2 = mock.MagicMock(spec=Path)
    mock_file2.relative_to.return_value = "file2.py"
    mock_file2.stat.side_effect = OSError("File not found")
    
    with mock.patch('oca.core.context.FileScanner.scan_files', return_value=[file1, mock_file2]):
        structure = analyzer.analyze_project_structure()
        # The file that raised the error should be excluded
        assert "file2.py" not in structure["files"]
        assert structure["file_count"] >= 0


def test_analyze_imports_python_file(temp_project: Path):
    """Test import analysis on a valid Python file."""
    analyzer = ContextAnalyzer(temp_project)
    py_file = Path("main.py")
    analysis = analyzer.analyze_imports(py_file)

    assert analysis is not None
    assert analysis["file_path"] == "main.py"
    assert "os" in analysis["imports"]
    assert "math" in analysis["from_imports"]
    assert "sqrt" in analysis["from_imports"]["math"]

def test_analyze_imports_non_python_file(temp_project: Path):
    """Test import analysis on a non-Python file."""
    analyzer = ContextAnalyzer(temp_project)
    js_file = Path("utils.js")
    analysis = analyzer.analyze_imports(js_file)

    assert analysis is None

def test_analyze_imports_file_with_syntax_error(temp_project: Path):
    """Test import analysis on a Python file with a syntax error."""
    error_file = temp_project / "error.py"
    error_file.write_text("import os\nthis is not valid python")
    analyzer = ContextAnalyzer(temp_project)
    analysis = analyzer.analyze_imports(Path("error.py"))

    assert analysis is None

def test_placeholder_methods(capsys):
    """Test that placeholder methods return empty lists and print warnings."""
    analyzer = ContextAnalyzer(Path("."))
    
    # Test get_function_dependencies
    deps = analyzer.get_function_dependencies("my_func")
    assert deps == []
    captured = capsys.readouterr()
    assert "Warning: `get_function_dependencies` for 'my_func' is not yet implemented." in captured.out

    # Test detect_patterns
    patterns = analyzer.detect_patterns()
    assert patterns == []
    captured = capsys.readouterr()
    assert "Warning: `detect_patterns` is not yet implemented." in captured.out
