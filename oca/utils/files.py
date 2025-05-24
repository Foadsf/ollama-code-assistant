"""File system operations for OCA."""

import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Iterator
import fnmatch


class FileScanner:
    """File system scanner with filtering capabilities."""
    
    def __init__(self, root_path: Path, ignore_patterns: Optional[List[str]] = None) -> None:
        """Initialize file scanner.
        
        Args:
            root_path: Root directory to scan
            ignore_patterns: Patterns to ignore (gitignore style)
        """
        self.root_path = Path(root_path)
        self.ignore_patterns = ignore_patterns or [
            '*.pyc', '__pycache__', '.git', 'node_modules',
            '.venv', 'venv', '.env', '*.log'
        ]
    
    def scan_files(self, extensions: Optional[List[str]] = None, 
                   max_size: int = 10 * 1024 * 1024) -> Iterator[Path]:
        """Scan files matching criteria.
        
        Args:
            extensions: File extensions to include (e.g., ['.py', '.js'])
            max_size: Maximum file size in bytes
            
        Yields:
            Path objects for matching files
        """
        for file_path in self._walk_directory():
            # Check size
            try:
                if file_path.stat().st_size > max_size:
                    continue
            except (OSError, PermissionError):
                continue
            
            # Check extension
            if extensions and file_path.suffix not in extensions:
                continue
            
            # Check ignore patterns
            if self._should_ignore(file_path):
                continue
            
            yield file_path
    
    def search_in_files(self, pattern: str, extensions: Optional[List[str]] = None,
                       is_regex: bool = False) -> Dict[str, List[Dict[str, any]]]:
        """Search for pattern in files.
        
        Args:
            pattern: Search pattern
            extensions: File extensions to search
            is_regex: Whether pattern is a regex
            
        Returns:
            Dict mapping file paths to list of matches
        """
        results = {}
        
        if is_regex:
            try:
                regex = re.compile(pattern, re.MULTILINE | re.IGNORECASE)
            except re.error:
                return results
        
        for file_path in self.scan_files(extensions=extensions):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                matches = []
                if is_regex:
                    for match in regex.finditer(content):
                        line_num = content[:match.start()].count('\n') + 1
                        line_start = content.rfind('\n', 0, match.start()) + 1
                        line_end = content.find('\n', match.end())
                        if line_end == -1:
                            line_end = len(content)
                        line_content = content[line_start:line_end]
                        
                        matches.append({
                            'line': line_num,
                            'content': line_content.strip(),
                            'match': match.group(),
                            'start': match.start() - line_start,
                            'end': match.end() - line_start
                        })
                else:
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        if pattern.lower() in line.lower():
                            matches.append({
                                'line': i,
                                'content': line.strip(),
                                'match': pattern,
                                'start': line.lower().find(pattern.lower()),
                                'end': line.lower().find(pattern.lower()) + len(pattern)
                            })
                
                if matches:
                    relative_path = str(file_path.relative_to(self.root_path))
                    results[relative_path] = matches
                    
            except (OSError, UnicodeDecodeError, PermissionError):
                continue
        
        return results
    
    def find_functions(self, file_path: Path) -> List[Dict[str, any]]:
        """Find function definitions in a file.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            List of function information
        """
        functions = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Simple function detection for Python files
            if file_path.suffix == '.py':
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if stripped.startswith('def ') or stripped.startswith('async def '):
                        # Extract function name
                        func_match = re.match(r'(async\s+)?def\s+(\w+)\s*\(', stripped)
                        if func_match:
                            functions.append({
                                'name': func_match.group(2),
                                'line': i,
                                'type': 'async' if func_match.group(1) else 'sync',
                                'signature': stripped
                            })
            
            # Simple function detection for JavaScript/TypeScript
            elif file_path.suffix in ['.js', '.ts']:
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    # function declarations
                    func_match = re.match(r'function\s+(\w+)\s*\(', stripped)
                    if func_match:
                        functions.append({
                            'name': func_match.group(1),
                            'line': i,
                            'type': 'function',
                            'signature': stripped
                        })
                    # arrow functions
                    arrow_match = re.match(r'(?:const|let|var)\s+(\w+)\s*=\s*\([^)]*\)\s*=>', stripped)
                    if arrow_match:
                        functions.append({
                            'name': arrow_match.group(1),
                            'line': i,
                            'type': 'arrow',
                            'signature': stripped
                        })
        
        except (OSError, UnicodeDecodeError, PermissionError):
            pass
        
        return functions
    
    def find_classes(self, file_path: Path) -> List[Dict[str, any]]:
        """Find class definitions in a file.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            List of class information
        """
        classes = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            if file_path.suffix == '.py':
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if stripped.startswith('class '):
                        class_match = re.match(r'class\s+(\w+)(?:\([^)]*\))?:', stripped)
                        if class_match:
                            classes.append({
                                'name': class_match.group(1),
                                'line': i,
                                'signature': stripped
                            })
        
        except (OSError, UnicodeDecodeError, PermissionError):
            pass
        
        return classes
    
    def _walk_directory(self) -> Iterator[Path]:
        """Walk directory tree, respecting ignore patterns."""
        for root, dirs, files in os.walk(self.root_path):
            # Filter directories
            dirs[:] = [d for d in dirs if not self._should_ignore_dir(Path(root) / d)]
            
            for file_name in files:
                file_path = Path(root) / file_name
                if file_path.is_file():
                    yield file_path
    
    def _should_ignore(self, file_path: Path) -> bool:
        """Check if file should be ignored based on patterns."""
        relative_path = str(file_path.relative_to(self.root_path))
        
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(relative_path, pattern) or fnmatch.fnmatch(file_path.name, pattern):
                return True
        
        return False
    
    def _should_ignore_dir(self, dir_path: Path) -> bool:
        """Check if directory should be ignored."""
        relative_path = str(dir_path.relative_to(self.root_path))
        
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(relative_path, pattern) or fnmatch.fnmatch(dir_path.name, pattern):
                return True
        
        return False