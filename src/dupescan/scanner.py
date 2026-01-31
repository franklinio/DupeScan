"""Directory traversal logic."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileInfo:
    """Information about a scanned file."""
    path: Path
    size: int
    mtime: float


def scan_directory(directory: Path) -> list[FileInfo]:
    """
    Recursively scan directory for files.

    Skips:
    - Symbolic links
    - Hidden files and directories (starting with '.')
    """
    files = []

    for root, dirs, filenames in os.walk(directory, followlinks=False):
        # Filter out hidden directories (modifies in-place to prevent descending)
        dirs[:] = [d for d in dirs if not d.startswith(".")]

        for filename in filenames:
            # Skip hidden files
            if filename.startswith("."):
                continue

            file_path = Path(root) / filename

            # Skip symbolic links
            if file_path.is_symlink():
                continue

            try:
                stat = file_path.stat()
                files.append(FileInfo(
                    path=file_path,
                    size=stat.st_size,
                    mtime=stat.st_mtime,
                ))
            except (PermissionError, OSError):
                # Skip files we can't access
                continue

    return files
