import pytest
from pathlib import Path
from oca.utils.validation import SyntaxValidator, SyntaxValidationError

def test_validate_python_valid():
    """Test validation of correct Python syntax."""
    validator = SyntaxValidator()
    code = "def hello():\n    print('Hello')"
    assert validator.validate(Path("test.py"), code) is True

def test_validate_python_invalid():
    """Test validation of incorrect Python syntax."""
    validator = SyntaxValidator()
    code = "def hello()"
    with pytest.raises(SyntaxValidationError, match="Invalid Python syntax"):
        validator.validate(Path("test.py"), code)

def test_validate_js_placeholder(capsys):
    """Test the placeholder validation for JavaScript."""
    validator = SyntaxValidator()
    code = "function hello() { console.log('hello'); }"
    assert validator.validate(Path("test.js"), code) is True
    captured = capsys.readouterr()
    assert "Warning: JS/TS syntax validation is not yet implemented." in captured.out

def test_validate_ts_placeholder(capsys):
    """Test the placeholder validation for TypeScript."""
    validator = SyntaxValidator()
    code = "function hello(): void { console.log('hello'); }"
    assert validator.validate(Path("test.ts"), code) is True
    captured = capsys.readouterr()
    assert "Warning: JS/TS syntax validation is not yet implemented." in captured.out

def test_validate_unsupported_language():
    """Test validation of an unsupported language."""
    validator = SyntaxValidator()
    code = "public class HelloWorld {}"
    assert validator.validate(Path("test.java"), code) is True
