"""Output formatting and display utilities."""

from datetime import datetime
from pathlib import Path


def format_size(size_bytes: int) -> str:
    """Format byte size to human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            if unit == "B":
                return f"{size_bytes} {unit}"
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def format_date(timestamp: float) -> str:
    """Format timestamp to readable date."""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")


def print_duplicates(duplicate_groups: list[list[tuple[Path, int, float]]], delete_mode: bool = False) -> None:
    """
    Print duplicate file groups.

    Args:
        duplicate_groups: List of groups, each group is a list of (path, size, mtime) tuples
        delete_mode: If True, show KEEP/DELETE labels
    """
    if not duplicate_groups:
        print("No duplicate files found.")
        return

    total_dupes = sum(len(group) - 1 for group in duplicate_groups)
    total_wasted = sum((len(group) - 1) * group[0][1] for group in duplicate_groups)

    print(f"\nFound {len(duplicate_groups)} set(s) of duplicates:\n")

    for i, group in enumerate(duplicate_groups, 1):
        size = group[0][1]
        print(f"[{i}] {len(group)} files ({format_size(size)} each):")

        # Sort by mtime (oldest first) for consistent display
        sorted_group = sorted(group, key=lambda x: x[2])

        for j, (path, _, mtime) in enumerate(sorted_group):
            date_str = format_date(mtime)
            if delete_mode:
                label = "KEEP  " if j == 0 else "DELETE"
                print(f"    {label} {path} ({date_str})")
            else:
                print(f"    {path}")
        print()

    print(f"Total: {total_dupes} duplicate file(s) ({format_size(total_wasted)} wasted)")


def get_files_to_delete(duplicate_groups: list[list[tuple[Path, int, float]]]) -> list[tuple[Path, int]]:
    """
    Get list of files to delete (all except oldest in each group).

    Returns:
        List of (path, size) tuples for files to delete
    """
    to_delete = []

    for group in duplicate_groups:
        # Sort by mtime, oldest first
        sorted_group = sorted(group, key=lambda x: x[2])
        # Skip the first (oldest), mark rest for deletion
        for path, size, _ in sorted_group[1:]:
            to_delete.append((path, size))

    return to_delete


def confirm_delete(files_to_delete: list[tuple[Path, int]]) -> bool:
    """Prompt user to confirm deletion."""
    total_size = sum(size for _, size in files_to_delete)
    print(f"\nDelete {len(files_to_delete)} file(s) ({format_size(total_size)})? [y/N]: ", end="")

    try:
        response = input().strip().lower()
        return response == "y"
    except (EOFError, KeyboardInterrupt):
        print()
        return False
