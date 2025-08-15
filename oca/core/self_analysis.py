import ast
from pathlib import Path
from typing import List, Dict, Any, TypedDict

from oca.utils.files import FileScanner
from oca.core.ast_tools import ASTTools

# --- Data Structures ---

class ImprovementOpportunity(TypedDict):
    """Represents a specific, actionable improvement opportunity."""
    type: str  # e.g., 'documentation', 'testing', 'refactoring'
    description: str
    file_path: str
    line_number: int
    severity: str  # e.g., 'high', 'medium', 'low'
    estimated_effort: str # e.g., 'low', 'medium', 'high'
    suggested_fix: str

class Feature(TypedDict):
    """Represents a potential new feature."""
    name: str
    description: str
    priority: str

# --- Self Analyzer ---

class SelfAnalyzer:
    """Analyzes OCA's own codebase for improvements."""

    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.scanner = FileScanner(self.root_path)
        self.ast_tools = ASTTools()

    def identify_improvement_opportunities(self) -> List[ImprovementOpportunity]:
        """Generate concrete, actionable improvement tasks."""
        opportunities = []
        opportunities.extend(self._find_missing_docstrings())
        return opportunities

    def _find_missing_docstrings(self) -> List[ImprovementOpportunity]:
        """Finds all functions that are missing a docstring."""
        opportunities = []
        py_files = self.scanner.scan_files(extensions=['.py'])
        for file_path in py_files:
            try:
                # Make sure we are using a path relative to the project root for display
                relative_path = file_path.relative_to(self.root_path)
                tree = self.ast_tools.parse_python_file(file_path)
                functions = self.ast_tools.find_functions(tree)
                for func in functions:
                    if not ast.get_docstring(func):
                        opportunities.append({
                            "type": "documentation",
                            "description": f"Function '{func.name}' is missing a docstring.",
                            "file_path": str(relative_path),
                            "line_number": func.lineno,
                            "severity": "medium",
                            "estimated_effort": "low",
                            "suggested_fix": f"Add a comprehensive docstring to the '{func.name}' function explaining its purpose, arguments, and return value."
                        })
            except Exception:
                continue
        return opportunities

    def analyze_code_quality(self) -> Dict[str, Any]:
        """Analyze OCA's code quality metrics."""
        return {
            'complexity': self._calculate_complexity(),
            'test_coverage': self._check_test_coverage(),
            'documentation': self._check_documentation(),
            'dependencies': self._analyze_dependencies()
        }

    def _calculate_complexity(self) -> Dict[str, Any]:
        """
        Calculates cyclomatic complexity of the codebase.
        NOTE: This is a placeholder.
        """
        print("Warning: Complexity calculation is a placeholder.")
        return {"average_complexity": 0, "high_complexity_functions": []}

    def _check_test_coverage(self) -> Dict[str, Any]:
        """
        Checks test coverage by running pytest.
        NOTE: This is a placeholder.
        """
        print("Warning: Test coverage check is a placeholder.")
        return {"coverage_percentage": 0.0, "uncovered_files": []}

    def _check_documentation(self) -> Dict[str, Any]:
        """Analyzes the documentation coverage (docstrings)."""
        total_funcs = 0
        funcs_with_docs = 0
        py_files = self.scanner.scan_files(extensions=['.py'])
        for file_path in py_files:
            try:
                tree = self.ast_tools.parse_python_file(file_path)
                functions = self.ast_tools.find_functions(tree)
                total_funcs += len(functions)
                for func in functions:
                    if ast.get_docstring(func):
                        funcs_with_docs += 1
            except Exception:
                continue
        doc_coverage = (funcs_with_docs / total_funcs * 100) if total_funcs > 0 else 100
        return {
            "total_functions": total_funcs,
            "functions_with_docstrings": funcs_with_docs,
            "documentation_coverage": round(doc_coverage, 2)
        }

    def _analyze_dependencies(self) -> Dict[str, Any]:
        """Analyzes third-party dependencies."""
        all_imports = set()
        py_files = self.scanner.scan_files(extensions=['.py'])
        for file_path in py_files:
            try:
                tree = self.ast_tools.parse_python_file(file_path)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            all_imports.add(alias.name.split('.')[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            all_imports.add(node.module.split('.')[0])
            except Exception:
                continue
        local_modules = {"oca"}
        external_imports = sorted(list(all_imports - local_modules))
        return {"dependencies": external_imports, "count": len(external_imports)}

    def suggest_next_features(self) -> List[Feature]:
        """
        Based on code analysis, suggest what to build next.
        NOTE: This is a placeholder.
        """
        print("Warning: Next feature suggestion is a placeholder.")
        return []
