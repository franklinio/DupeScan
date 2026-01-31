#!/usr/bin/env python3
"""DupeScan - Find and optionally delete duplicate files."""

import argparse
import hashlib
import shutil
import sys
from collections import defaultdict
from pathlib import Path

from .scanner import scan_directory, FileInfo
from .hasher import compute_hash
from .formatter import print_duplicates, get_files_to_delete, confirm_delete, format_size


def compute_dir_signature(dir_path: Path, dir_files: list[FileInfo]) -> str:
    """
    Compute a signature for a directory based on its file contents.

    Args:
        dir_path: Path to the directory
        dir_files: List of FileInfo for files that might be in this directory

    Returns:
        Hash string representing the directory contents, or "" if empty/subdirs-only
    """
    # Get files directly in this directory (not subdirs)
    items = []
    for f in dir_files:
        if f.path.parent == dir_path:
            try:
                file_hash = compute_hash(f.path)
                items.append((f.path.name, file_hash))
            except (PermissionError, OSError):
                continue

    if not items:
        return ""  # Empty or subdirs-only

    # Sort by filename for consistent ordering
    items.sort()
    # Combine into single hash
    combined = "".join(f"{name}:{hash}" for name, hash in items)
    return hashlib.sha256(combined.encode()).hexdigest()


def find_duplicate_folders(files: list[FileInfo]) -> tuple[list[list[tuple[Path, int, float]]], set[Path]]:
    """
    Find duplicate folders (sibling directories with identical contents).

    Args:
        files: List of all files found during scan

    Returns:
        Tuple of:
        - List of folder duplicate groups, each group is list of (folder_path, total_size, oldest_mtime)
        - Set of file paths that are part of duplicate folders (to exclude from file duplicate detection)
    """
    # Group files by their parent directory
    dir_files: dict[Path, list[FileInfo]] = defaultdict(list)
    for f in files:
        dir_files[f.path.parent].append(f)

    # Group directories by their parent (to find siblings)
    sibling_groups: dict[Path, list[Path]] = defaultdict(list)
    for dir_path in dir_files.keys():
        parent = dir_path.parent
        sibling_groups[parent].append(dir_path)

    # Find duplicate folders among siblings
    duplicate_folder_groups: list[list[tuple[Path, int, float]]] = []
    files_in_duplicate_folders: set[Path] = set()

    for parent, siblings in sibling_groups.items():
        if len(siblings) < 2:
            continue

        # Compute signature for each sibling directory
        sig_groups: dict[str, list[Path]] = defaultdict(list)
        for dir_path in siblings:
            sig = compute_dir_signature(dir_path, dir_files[dir_path])
            if sig:  # Skip empty directories
                sig_groups[sig].append(dir_path)

        # Collect groups with actual duplicates
        for sig, dirs in sig_groups.items():
            if len(dirs) > 1:
                group = []
                for dir_path in dirs:
                    dir_file_list = dir_files[dir_path]
                    # Only count direct files (not subdirs)
                    direct_files = [f for f in dir_file_list if f.path.parent == dir_path]
                    total_size = sum(f.size for f in direct_files)
                    oldest_mtime = min(f.mtime for f in direct_files) if direct_files else 0
                    group.append((dir_path, total_size, oldest_mtime))

                    # Mark all direct files as part of duplicate folders
                    for f in direct_files:
                        files_in_duplicate_folders.add(f.path)

                duplicate_folder_groups.append(group)

    return duplicate_folder_groups, files_in_duplicate_folders


def find_duplicates(files: list[FileInfo]) -> tuple[list[list[tuple[Path, int, float]]], list[list[tuple[Path, int, float]]]]:
    """
    Find duplicate folders and files.

    First detects duplicate folders (sibling directories with identical contents),
    then finds duplicate files among the remaining files not in duplicate folders.

    Returns:
        Tuple of:
        - List of folder duplicate groups, each group is list of (folder_path, total_size, oldest_mtime)
        - List of file duplicate groups, each group is list of (file_path, size, mtime)
    """
    # Phase 1: Find duplicate folders
    folder_duplicates, files_in_dup_folders = find_duplicate_folders(files)

    # Phase 2: Find file duplicates (excluding files in duplicate folders)
    remaining_files = [f for f in files if f.path not in files_in_dup_folders]

    # Group by (directory, size)
    dir_size_groups: dict[tuple[Path, int], list[FileInfo]] = defaultdict(list)
    for file_info in remaining_files:
        key = (file_info.path.parent, file_info.size)
        dir_size_groups[key].append(file_info)

    # Filter to only groups with potential duplicates (size > 0 and count > 1)
    potential_dupes = [
        group for (_, size), group in dir_size_groups.items()
        if size > 0 and len(group) > 1
    ]

    # Hash comparison
    file_duplicates = []

    for group in potential_dupes:
        hash_groups: dict[str, list[FileInfo]] = defaultdict(list)

        for file_info in group:
            try:
                file_hash = compute_hash(file_info.path)
                hash_groups[file_hash].append(file_info)
            except (PermissionError, OSError):
                continue

        for file_list in hash_groups.values():
            if len(file_list) > 1:
                file_duplicates.append([
                    (f.path, f.size, f.mtime) for f in file_list
                ])

    return folder_duplicates, file_duplicates


def delete_folder(path: Path) -> int:
    """
    Delete a folder and return bytes reclaimed.

    Args:
        path: Path to folder to delete

    Returns:
        Total bytes reclaimed from deleted files
    """
    size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    shutil.rmtree(path)
    return size


def delete_duplicates(
    files_to_delete: list[tuple[Path, int]],
    folders_to_delete: list[tuple[Path, int]] | None = None
) -> tuple[int, int, int, int]:
    """
    Delete the specified files and folders.

    Args:
        files_to_delete: List of (file_path, size) to delete
        folders_to_delete: List of (folder_path, size) to delete

    Returns:
        Tuple of (files_deleted, file_bytes_reclaimed, folders_deleted, folder_bytes_reclaimed)
    """
    files_deleted = 0
    file_bytes = 0
    folders_deleted = 0
    folder_bytes = 0

    # Delete folders first
    if folders_to_delete:
        for path, _ in folders_to_delete:
            try:
                reclaimed = delete_folder(path)
                folders_deleted += 1
                folder_bytes += reclaimed
            except (PermissionError, OSError) as e:
                print(f"Error deleting folder {path}: {e}")

    # Delete individual files
    for path, size in files_to_delete:
        try:
            path.unlink()
            files_deleted += 1
            file_bytes += size
        except (PermissionError, OSError) as e:
            print(f"Error deleting {path}: {e}")

    return files_deleted, file_bytes, folders_deleted, folder_bytes


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find and optionally delete duplicate files and folders in a directory."
    )
    parser.add_argument(
        "directory",
        type=Path,
        help="Directory to scan for duplicates"
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete duplicates, keeping the oldest copy"
    )

    args = parser.parse_args()

    # Validate directory
    if not args.directory.exists():
        print(f"Error: Directory not found: {args.directory}")
        return 2

    if not args.directory.is_dir():
        print(f"Error: Not a directory: {args.directory}")
        return 2

    # Scan directory
    print(f"Scanning: {args.directory}")
    files = scan_directory(args.directory)
    print(f"Found {len(files)} file(s), checking for duplicates...")

    # Find duplicates
    folder_duplicates, file_duplicates = find_duplicates(files)

    if not folder_duplicates and not file_duplicates:
        print("No duplicates found.")
        return 1

    # Display results
    print_duplicates(folder_duplicates, file_duplicates, delete_mode=args.delete)

    # Handle deletion
    if args.delete:
        files_to_delete, folders_to_delete = get_files_to_delete(folder_duplicates, file_duplicates)

        if confirm_delete(files_to_delete, folders_to_delete):
            files_del, file_bytes, folders_del, folder_bytes = delete_duplicates(
                files_to_delete, folders_to_delete
            )
            total_bytes = file_bytes + folder_bytes
            parts = []
            if folders_del:
                parts.append(f"{folders_del} folder(s)")
            if files_del:
                parts.append(f"{files_del} file(s)")
            print(f"\nDeleted {', '.join(parts)}, freed {format_size(total_bytes)}")
        else:
            print("Deletion cancelled.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
