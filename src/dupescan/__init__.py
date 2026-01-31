#!/usr/bin/env python3
"""DupeScan - Find and optionally delete duplicate files."""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

from .scanner import scan_directory, FileInfo
from .hasher import compute_hash
from .formatter import print_duplicates, get_files_to_delete, confirm_delete, format_size


def find_duplicates(files: list[FileInfo]) -> list[list[tuple[Path, int, float]]]:
    """
    Find duplicate files using size grouping and hash comparison.

    Only files in the same directory are considered potential duplicates.

    Returns:
        List of duplicate groups, each group is a list of (path, size, mtime) tuples
    """
    # Phase 1: Group by (directory, size)
    dir_size_groups: dict[tuple[Path, int], list[FileInfo]] = defaultdict(list)
    for file_info in files:
        key = (file_info.path.parent, file_info.size)
        dir_size_groups[key].append(file_info)

    # Filter to only groups with potential duplicates (size > 0 and count > 1)
    potential_dupes = [
        group for (_, size), group in dir_size_groups.items()
        if size > 0 and len(group) > 1
    ]

    # Phase 2: Hash comparison (still grouped by directory from phase 1)
    duplicate_groups = []

    for group in potential_dupes:
        hash_groups: dict[str, list[FileInfo]] = defaultdict(list)

        for file_info in group:
            try:
                file_hash = compute_hash(file_info.path)
                hash_groups[file_hash].append(file_info)
            except (PermissionError, OSError):
                # Skip files we can't read
                continue

        # Collect groups with actual duplicates
        for file_list in hash_groups.values():
            if len(file_list) > 1:
                duplicate_groups.append([
                    (f.path, f.size, f.mtime) for f in file_list
                ])

    return duplicate_groups


def delete_duplicates(files_to_delete: list[tuple[Path, int]]) -> tuple[int, int]:
    """
    Delete the specified files.

    Returns:
        Tuple of (files_deleted_count, bytes_reclaimed)
    """
    deleted_count = 0
    bytes_reclaimed = 0

    for path, size in files_to_delete:
        try:
            path.unlink()
            deleted_count += 1
            bytes_reclaimed += size
        except (PermissionError, OSError) as e:
            print(f"Error deleting {path}: {e}")

    return deleted_count, bytes_reclaimed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find and optionally delete duplicate files in a directory."
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
    duplicate_groups = find_duplicates(files)

    if not duplicate_groups:
        print("No duplicate files found.")
        return 1

    # Display results
    print_duplicates(duplicate_groups, delete_mode=args.delete)

    # Handle deletion
    if args.delete:
        files_to_delete = get_files_to_delete(duplicate_groups)

        if confirm_delete(files_to_delete):
            deleted_count, bytes_reclaimed = delete_duplicates(files_to_delete)
            print(f"\nDeleted {deleted_count} file(s), freed {format_size(bytes_reclaimed)}")
        else:
            print("Deletion cancelled.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
