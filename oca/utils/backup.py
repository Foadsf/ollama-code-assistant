import shutil
from pathlib import Path
from datetime import datetime

class BackupError(Exception):
    """Custom exception for backup errors."""
    pass

class BackupManager:
    """Manages file backups."""

    def __init__(self, backup_dir: Path):
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, file_path: Path) -> Path:
        """Create a backup of a file.

        Args:
            file_path: The path to the file to back up.

        Returns:
            The path to the backup file.
        """
        if not file_path.exists():
            raise BackupError(f"File not found: {file_path}")

        try:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            backup_file_name = f"{file_path.name}.{timestamp}.bak"
            backup_path = self.backup_dir / backup_file_name
            shutil.copy2(file_path, backup_path)
            return backup_path
        except shutil.Error as e:
            raise BackupError(f"Failed to create backup for {file_path}: {e}")

    def restore_backup(self, backup_path: Path, original_path: Path) -> None:
        """Restore a file from a backup.

        Args:
            backup_path: The path to the backup file.
            original_path: The path to restore the file to.
        """
        if not backup_path.exists():
            raise BackupError(f"Backup file not found: {backup_path}")

        try:
            shutil.copy2(backup_path, original_path)
        except shutil.Error as e:
            raise BackupError(f"Failed to restore backup from {backup_path}: {e}")
