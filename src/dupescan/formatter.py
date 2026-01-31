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


def print_duplicates(
    folder_duplicates: list[list[tuple[Path, int, float]]],
    file_duplicates: list[list[tuple[Path, int, float]]],
    delete_mode: bool = False
) -> None:
    """
    Print duplicate folder and file groups.

    Args:
        folder_duplicates: List of folder groups, each is list of (folder_path, total_size, oldest_mtime)
        file_duplicates: List of file groups, each is list of (file_path, size, mtime)
        delete_mode: If True, show KEEP/DELETE labels
    """
    if not folder_duplicates and not file_duplicates:
        print("No duplicates found.")
        return

    total_folder_dupes = sum(len(group) - 1 for group in folder_duplicates)
    total_file_dupes = sum(len(group) - 1 for group in file_duplicates)
    folder_wasted = sum((len(group) - 1) * group[0][1] for group in folder_duplicates)
    file_wasted = sum((len(group) - 1) * group[0][1] for group in file_duplicates)

    total_sets = len(folder_duplicates) + len(file_duplicates)
    print(f"\nFound {total_sets} set(s) of duplicates:\n")

    idx = 1

    # Print folder duplicates
    for group in folder_duplicates:
        size = group[0][1]
        print(f"[{idx}] {len(group)} folders ({format_size(size)} each):")
        idx += 1

        sorted_group = sorted(group, key=lambda x: x[2])

        for j, (path, _, mtime) in enumerate(sorted_group):
            date_str = format_date(mtime)
            if delete_mode:
                label = "KEEP  " if j == 0 else "DELETE"
                print(f"    {label} {path}/ ({date_str})")
            else:
                print(f"    {path}/")
        print()

    # Print file duplicates
    for group in file_duplicates:
        size = group[0][1]
        print(f"[{idx}] {len(group)} files ({format_size(size)} each):")
        idx += 1

        sorted_group = sorted(group, key=lambda x: x[2])

        for j, (path, _, mtime) in enumerate(sorted_group):
            date_str = format_date(mtime)
            if delete_mode:
                label = "KEEP  " if j == 0 else "DELETE"
                print(f"    {label} {path} ({date_str})")
            else:
                print(f"    {path}")
        print()

    # Summary
    parts = []
    if total_folder_dupes:
        parts.append(f"{total_folder_dupes} duplicate folder(s)")
    if total_file_dupes:
        parts.append(f"{total_file_dupes} duplicate file(s)")
    total_wasted = folder_wasted + file_wasted
    print(f"Total: {', '.join(parts)} ({format_size(total_wasted)} wasted)")


def get_files_to_delete(
    folder_duplicates: list[list[tuple[Path, int, float]]],
    file_duplicates: list[list[tuple[Path, int, float]]]
) -> tuple[list[tuple[Path, int]], list[tuple[Path, int]]]:
    """
    Get lists of files and folders to delete (all except oldest in each group).

    Args:
        folder_duplicates: List of folder duplicate groups
        file_duplicates: List of file duplicate groups

    Returns:
        Tuple of (files_to_delete, folders_to_delete), each is list of (path, size)
    """
    files_to_delete = []
    folders_to_delete = []

    # Get folders to delete
    for group in folder_duplicates:
        sorted_group = sorted(group, key=lambda x: x[2])
        for path, size, _ in sorted_group[1:]:
            folders_to_delete.append((path, size))

    # Get files to delete
    for group in file_duplicates:
        sorted_group = sorted(group, key=lambda x: x[2])
        for path, size, _ in sorted_group[1:]:
            files_to_delete.append((path, size))

    return files_to_delete, folders_to_delete


def confirm_delete(
    files_to_delete: list[tuple[Path, int]],
    folders_to_delete: list[tuple[Path, int]] | None = None
) -> bool:
    """Prompt user to confirm deletion."""
    folders_to_delete = folders_to_delete or []
    file_size = sum(size for _, size in files_to_delete)
    folder_size = sum(size for _, size in folders_to_delete)
    total_size = file_size + folder_size

    parts = []
    if folders_to_delete:
        parts.append(f"{len(folders_to_delete)} folder(s)")
    if files_to_delete:
        parts.append(f"{len(files_to_delete)} file(s)")

    print(f"\nDelete {', '.join(parts)} ({format_size(total_size)})? [y/N]: ", end="")

    try:
        response = input().strip().lower()
        return response == "y"
    except (EOFError, KeyboardInterrupt):
        print()
        return False
