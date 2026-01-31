"""File hashing utilities using SHA-256."""

import hashlib
from pathlib import Path

CHUNK_SIZE = 65536  # 64 KB chunks for memory efficiency


def compute_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file using chunked reading."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            sha256.update(chunk)
    return sha256.hexdigest()
