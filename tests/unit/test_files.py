import pytest
from pathlib import Path
from unittest import mock
from oca.utils.files import FileScanner

@pytest.fixture
def temp_project(tmp_path: Path):
    """Creates a temporary project structure for testing."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("def hello():\n    print('Hello')\n\nclass MyClass:\n    pass")
    (project_dir / "app.js").write_text("function greet() {\n    console.log('Hi');\n}\nconst sayHi = () => console.log('Hi');")
    (project_dir / "data.txt").write_text("some data")
    (project_dir / ".env").write_text("SECRET=123")
    (project_dir / "large_file.log").write_text("a" * 100)
    
    node_modules = project_dir / "node_modules"
    node_modules.mkdir()
    (node_modules / "lib.js").write_text("console.log('lib');")
    
    return project_dir

def test_file_scanner_init(temp_project: Path):
    """Test FileScanner initialization."""
    scanner = FileScanner(temp_project)
    assert scanner.root_path == temp_project
    assert "*.pyc" in scanner.ignore_patterns

    custom_scanner = FileScanner(temp_project, ignore_patterns=["*.tmp"])
    assert "*.tmp" in custom_scanner.ignore_patterns

def test_scan_files_basic(temp_project: Path):
    """Test basic file scanning."""
    scanner = FileScanner(temp_project)
    files = list(scanner.scan_files())
    filenames = [f.name for f in files]
    
    assert "main.py" in filenames
    assert "app.js" in filenames
    assert "data.txt" in filenames
    assert ".env" not in filenames
    assert "large_file.log" not in filenames
    assert "lib.js" not in filenames

def test_scan_files_with_extension_filter(temp_project: Path):
    """Test scanning with an extension filter."""
    scanner = FileScanner(temp_project)
    files = list(scanner.scan_files(extensions=[".js"]))
    assert len(files) == 1
    assert files[0].name == "app.js"

def test_scan_files_with_size_filter(temp_project: Path):
    """Test scanning with a size filter."""
    scanner = FileScanner(temp_project)
    files = list(scanner.scan_files(max_size=50))
    filenames = [f.name for f in files]
    assert "large_file.log" not in filenames

@mock.patch('oca.utils.files.FileScanner._walk_directory')
def test_scan_files_permission_error(mock_walk, temp_project: Path):
    """Test that PermissionError is handled during scanning."""
    mock_file = mock.MagicMock(spec=Path)
    mock_file.stat.side_effect = PermissionError
    mock_walk.return_value = [mock_file]
    
    scanner = FileScanner(temp_project)
    files = list(scanner.scan_files())
    assert len(files) == 0

def test_search_in_files_string(temp_project: Path):
    """Test searching for a simple string."""
    scanner = FileScanner(temp_project)
    results = scanner.search_in_files("console.log")
    
    assert "app.js" in results
    assert len(results["app.js"]) == 2

def test_search_in_files_regex(temp_project: Path):
    """Test searching with a regex pattern."""
    scanner = FileScanner(temp_project)
    results = scanner.search_in_files(r"def\s+\w+\(\)", is_regex=True)
    
    assert "main.py" in results
    assert results["main.py"][0]["match"] == "def hello()"

def test_search_in_files_invalid_regex(temp_project: Path):
    """Test searching with an invalid regex pattern."""
    scanner = FileScanner(temp_project)
    results = scanner.search_in_files(r"[", is_regex=True)
    assert results == {}

@mock.patch("builtins.open", side_effect=PermissionError)
def test_search_in_files_open_error(mock_open, temp_project: Path):
    """Test error handling when opening a file for search."""
    scanner = FileScanner(temp_project)
    results = scanner.search_in_files("anything")
    assert results == {}

def test_find_functions_python(temp_project: Path):
    """Test finding functions in a Python file."""
    scanner = FileScanner(temp_project)
    functions = scanner.find_functions(temp_project / "main.py")
    
    assert len(functions) == 1
    assert functions[0]["name"] == "hello"

def test_find_functions_js(temp_project: Path):
    """Test finding functions in a JavaScript file."""
    scanner = FileScanner(temp_project)
    functions = scanner.find_functions(temp_project / "app.js")
    
    assert len(functions) == 2
    assert functions[0]["name"] == "greet"
    assert functions[1]["name"] == "sayHi"

@mock.patch("builtins.open", side_effect=PermissionError)
def test_find_functions_open_error(mock_open, temp_project: Path):
    """Test error handling when opening a file for function finding."""
    scanner = FileScanner(temp_project)
    functions = scanner.find_functions(temp_project / "main.py")
    assert functions == []

def test_find_classes_python(temp_project: Path):
    """Test finding classes in a Python file."""
    scanner = FileScanner(temp_project)
    classes = scanner.find_classes(temp_project / "main.py")
    
    assert len(classes) == 1
    assert classes[0]["name"] == "MyClass"

@mock.patch("builtins.open", side_effect=PermissionError)
def test_find_classes_open_error(mock_open, temp_project: Path):
    """Test error handling when opening a file for class finding."""
    scanner = FileScanner(temp_project)
    classes = scanner.find_classes(temp_project / "main.py")
    assert classes == []