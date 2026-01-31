"""Unit tests for DupeScan components."""

import tempfile
import os
from pathlib import Path

import pytest

from dupescan.hasher import compute_hash
from dupescan.scanner import scan_directory, FileInfo
from dupescan.formatter import format_size, get_files_to_delete
from dupescan import find_duplicates, find_duplicate_folders


class TestHasher:
    def test_identical_content_same_hash(self, tmp_path):
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("same content")
        file2.write_text("same content")

        assert compute_hash(file1) == compute_hash(file2)

    def test_different_content_different_hash(self, tmp_path):
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("content a")
        file2.write_text("content b")

        assert compute_hash(file1) != compute_hash(file2)


class TestScanner:
    def test_finds_files_recursively(self, tmp_path):
        (tmp_path / "file1.txt").write_text("a")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file2.txt").write_text("b")

        files = scan_directory(tmp_path)

        assert len(files) == 2

    def test_skips_hidden_files(self, tmp_path):
        (tmp_path / "visible.txt").write_text("a")
        (tmp_path / ".hidden.txt").write_text("b")

        files = scan_directory(tmp_path)

        assert len(files) == 1
        assert files[0].path.name == "visible.txt"

    def test_skips_hidden_directories(self, tmp_path):
        (tmp_path / "visible.txt").write_text("a")
        (tmp_path / ".hidden_dir").mkdir()
        (tmp_path / ".hidden_dir" / "file.txt").write_text("b")

        files = scan_directory(tmp_path)

        assert len(files) == 1

    def test_skips_symlinks(self, tmp_path):
        real_file = tmp_path / "real.txt"
        real_file.write_text("content")
        symlink = tmp_path / "link.txt"
        symlink.symlink_to(real_file)

        files = scan_directory(tmp_path)

        assert len(files) == 1
        assert files[0].path.name == "real.txt"


class TestFormatter:
    @pytest.mark.parametrize("size,expected", [
        (0, "0 B"),
        (512, "512 B"),
        (1024, "1.0 KB"),
        (1536, "1.5 KB"),
        (1048576, "1.0 MB"),
        (1073741824, "1.0 GB"),
    ])
    def test_format_size(self, size, expected):
        assert format_size(size) == expected

    def test_get_files_to_delete_keeps_oldest(self):
        file_groups = [[
            (Path("/a.txt"), 100, 1000.0),  # oldest
            (Path("/b.txt"), 100, 2000.0),
            (Path("/c.txt"), 100, 3000.0),
        ]]

        files_to_delete, folders_to_delete = get_files_to_delete([], file_groups)

        paths = [p for p, _ in files_to_delete]
        assert Path("/a.txt") not in paths
        assert Path("/b.txt") in paths
        assert Path("/c.txt") in paths
        assert len(folders_to_delete) == 0

    def test_get_folders_to_delete_keeps_oldest(self):
        folder_groups = [[
            (Path("/folder_a"), 100, 1000.0),  # oldest
            (Path("/folder_b"), 100, 2000.0),
        ]]

        files_to_delete, folders_to_delete = get_files_to_delete(folder_groups, [])

        folder_paths = [p for p, _ in folders_to_delete]
        assert Path("/folder_a") not in folder_paths
        assert Path("/folder_b") in folder_paths
        assert len(files_to_delete) == 0


class TestFindDuplicates:
    def test_finds_duplicates(self, tmp_path):
        (tmp_path / "file1.txt").write_text("duplicate")
        (tmp_path / "file2.txt").write_text("duplicate")
        (tmp_path / "unique.txt").write_text("unique")

        files = scan_directory(tmp_path)
        folder_dupes, file_dupes = find_duplicates(files)

        assert len(folder_dupes) == 0
        assert len(file_dupes) == 1
        assert len(file_dupes[0]) == 2

    def test_no_duplicates(self, tmp_path):
        (tmp_path / "file1.txt").write_text("content a")
        (tmp_path / "file2.txt").write_text("content b")

        files = scan_directory(tmp_path)
        folder_dupes, file_dupes = find_duplicates(files)

        assert len(folder_dupes) == 0
        assert len(file_dupes) == 0

    def test_empty_files_not_duplicates(self, tmp_path):
        (tmp_path / "empty1.txt").write_text("")
        (tmp_path / "empty2.txt").write_text("")

        files = scan_directory(tmp_path)
        folder_dupes, file_dupes = find_duplicates(files)

        assert len(folder_dupes) == 0
        assert len(file_dupes) == 0

    def test_same_content_different_dirs_not_duplicates(self, tmp_path):
        (tmp_path / "file1.txt").write_text("same")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file2.txt").write_text("same")

        files = scan_directory(tmp_path)
        folder_dupes, file_dupes = find_duplicates(files)

        assert len(folder_dupes) == 0
        assert len(file_dupes) == 0  # Not duplicates - different directories


class TestFindDuplicateFolders:
    def test_finds_duplicate_folders(self, tmp_path):
        """Two sibling folders with identical files are detected as duplicates."""
        # Create two sibling directories with identical content
        (tmp_path / "folder_a").mkdir()
        (tmp_path / "folder_b").mkdir()
        (tmp_path / "folder_a" / "file.txt").write_text("same content")
        (tmp_path / "folder_b" / "file.txt").write_text("same content")

        files = scan_directory(tmp_path)
        folder_dupes, files_in_folders = find_duplicate_folders(files)

        assert len(folder_dupes) == 1
        assert len(folder_dupes[0]) == 2
        folder_paths = {p for p, _, _ in folder_dupes[0]}
        assert tmp_path / "folder_a" in folder_paths
        assert tmp_path / "folder_b" in folder_paths

    def test_duplicate_folders_not_shown_as_file_duplicates(self, tmp_path):
        """Files inside duplicate folders are excluded from file duplicate detection."""
        # Create duplicate folders
        (tmp_path / "folder_a").mkdir()
        (tmp_path / "folder_b").mkdir()
        (tmp_path / "folder_a" / "file.txt").write_text("same content")
        (tmp_path / "folder_b" / "file.txt").write_text("same content")

        files = scan_directory(tmp_path)
        folder_dupes, file_dupes = find_duplicates(files)

        # Should be folder duplicates, not file duplicates
        assert len(folder_dupes) == 1
        assert len(file_dupes) == 0

    def test_different_content_folders_not_duplicates(self, tmp_path):
        """Sibling folders with different content are not duplicates."""
        (tmp_path / "folder_a").mkdir()
        (tmp_path / "folder_b").mkdir()
        (tmp_path / "folder_a" / "file.txt").write_text("content a")
        (tmp_path / "folder_b" / "file.txt").write_text("content b")

        files = scan_directory(tmp_path)
        folder_dupes, files_in_folders = find_duplicate_folders(files)

        assert len(folder_dupes) == 0

    def test_different_filename_folders_not_duplicates(self, tmp_path):
        """Folders with same content but different filenames are not duplicates."""
        (tmp_path / "folder_a").mkdir()
        (tmp_path / "folder_b").mkdir()
        (tmp_path / "folder_a" / "file1.txt").write_text("same content")
        (tmp_path / "folder_b" / "file2.txt").write_text("same content")

        files = scan_directory(tmp_path)
        folder_dupes, files_in_folders = find_duplicate_folders(files)

        assert len(folder_dupes) == 0

    def test_non_sibling_folders_not_duplicates(self, tmp_path):
        """Folders with different parents are not considered for folder duplication."""
        (tmp_path / "parent1").mkdir()
        (tmp_path / "parent2").mkdir()
        (tmp_path / "parent1" / "child").mkdir()
        (tmp_path / "parent2" / "child").mkdir()
        (tmp_path / "parent1" / "child" / "file.txt").write_text("same")
        (tmp_path / "parent2" / "child" / "file.txt").write_text("same")

        files = scan_directory(tmp_path)
        folder_dupes, files_in_folders = find_duplicate_folders(files)

        # The "child" folders are not siblings (different parents)
        assert len(folder_dupes) == 0

    def test_empty_folders_not_duplicates(self, tmp_path):
        """Empty folders are not considered for duplication."""
        (tmp_path / "folder_a").mkdir()
        (tmp_path / "folder_b").mkdir()

        files = scan_directory(tmp_path)
        folder_dupes, files_in_folders = find_duplicate_folders(files)

        assert len(folder_dupes) == 0
