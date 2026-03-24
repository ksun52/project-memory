"""Local file storage client for managing source files.

Handles reading, writing, and deleting files on the local filesystem.
File keys follow the pattern: {memory_space_id}/{source_id}/{filename}
"""

import os
from pathlib import Path

from app.core.config import settings


class LocalStorageClient:
    """Client for local filesystem storage operations."""

    def __init__(self, base_path: str) -> None:
        """Initialize the storage client and create the base directory if needed.

        Args:
            base_path: Root directory for all stored files.
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save_file(self, file_key: str, data: bytes) -> str:
        """Write bytes to a file at {base_path}/{file_key}.

        Args:
            file_key: Relative path within storage (e.g. {space_id}/{source_id}/{name}).
            data: Raw bytes to write.

        Returns:
            The absolute file path as a string.
        """
        file_path = self.base_path / file_key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(data)
        return str(file_path)

    def read_file(self, file_key: str) -> bytes:
        """Read and return the bytes of a stored file.

        Args:
            file_key: Relative path within storage.

        Returns:
            The raw bytes of the file.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        file_path = self.base_path / file_key
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_key}")
        return file_path.read_bytes()

    def delete_file(self, file_key: str) -> None:
        """Remove a file if it exists. No-op if already absent.

        Args:
            file_key: Relative path within storage.
        """
        file_path = self.base_path / file_key
        if file_path.exists():
            file_path.unlink()

    def file_exists(self, file_key: str) -> bool:
        """Check whether a file exists in storage.

        Args:
            file_key: Relative path within storage.

        Returns:
            True if the file exists, False otherwise.
        """
        return (self.base_path / file_key).exists()


storage_client = LocalStorageClient(settings.STORAGE_PATH)
