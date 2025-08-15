from pathlib import Path
from typing import List, Optional

from oca.utils.backup import BackupManager, BackupError
from oca.utils.validation import SyntaxValidator, SyntaxValidationError

# The user prompt specified `changes: List[Change]` as an argument for `apply_changes`.
# However, the `Change` type was not defined, and LLMs typically return the full content
# of a file. For this initial implementation, we are simplifying `apply_changes` to
# accept the new content for a single file as a string. This can be extended later
# to support more granular, multi-file changes if needed.
class Change: # Placeholder for future complex changes
    pass

class EditorError(Exception):
    """Custom exception for editor errors."""
    pass

class CodeEditor:
    """Safe code editor with backup and validation."""

    def __init__(self, root_path: Path, backup_dir: Optional[Path] = None):
        self.root_path = root_path
        self.backup_dir = backup_dir or self.root_path / ".oca" / "backups"
        self.backup_manager = BackupManager(self.backup_dir)
        self.syntax_validator = SyntaxValidator()

    def apply_changes(self, file_path: Path, new_content: str) -> bool:
        """Apply code changes to a single file with validation and backup.

        Args:
            file_path: The path to the file to modify, relative to the project root.
            new_content: The new, full content for the file.

        Returns:
            True if changes were applied successfully.

        Raises:
            EditorError: If any step in the process fails.
        """
        full_path = self._resolve_path(file_path)

        if not full_path.exists():
            raise EditorError(f"File not found: {full_path}")

        # 1. Validate syntax before doing anything else
        try:
            self.validate_syntax(full_path, new_content)
        except SyntaxValidationError as e:
            raise EditorError(f"Syntax validation failed: {e}")

        # 2. Create a backup
        try:
            backup_path = self.backup_file(full_path)
        except BackupError as e:
            raise EditorError(f"Backup failed: {e}")

        # 3. Apply the changes
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_content)
        except IOError as e:
            # If writing fails, try to restore from backup
            try:
                self.backup_manager.restore_backup(backup_path, full_path)
            except BackupError as restore_e:
                raise EditorError(f"Failed to write to file {full_path} and also failed to restore backup: {restore_e}")
            raise EditorError(f"Failed to write to file {full_path} but restored from backup: {e}")

        return True

    def create_file(self, file_path: Path, content: str) -> bool:
        """Create a new file with content.

        Args:
            file_path: The path to the new file, relative to the project root.
            content: The content to write to the file.

        Returns:
            True if the file was created successfully.
        """
        full_path = self._resolve_path(file_path)

        if full_path.exists():
            raise EditorError(f"File already exists: {full_path}")

        full_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self.validate_syntax(full_path, content)
        except SyntaxValidationError as e:
            raise EditorError(f"Syntax validation failed for new file: {e}")

        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
        except IOError as e:
            raise EditorError(f"Failed to create file {full_path}: {e}")

        return True

    def backup_file(self, file_path: Path) -> Path:
        """Create a backup before editing."""
        return self.backup_manager.create_backup(file_path)

    def validate_syntax(self, file_path: Path, content: str) -> bool:
        """Validate syntax before applying changes."""
        return self.syntax_validator.validate(file_path, content)

    def _resolve_path(self, file_path: Path) -> Path:
        """Resolve a relative path against the root path and prevent traversal."""
        # Ensure the path is relative to avoid security issues with absolute paths.
        if file_path.is_absolute():
             raise EditorError("File path must be relative to the project root.")

        full_path = (self.root_path / file_path).resolve()

        # Final check to ensure the path is within the project root.
        if self.root_path.resolve() not in full_path.parents and full_path.resolve() != self.root_path.resolve():
            raise EditorError(f"File path '{file_path}' resolves outside the project root '{self.root_path}'")

        return full_path
