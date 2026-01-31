"""Unit tests for DupeScan components."""

import tempfile
import os
from pathlib import Path

import pytest

from dupescan.hasher import compute_hash
from dupescan.scanner import scan_directory, FileInfo
from dupescan.formatter import format_size, get_files_to_delete
from dupescan import find_duplicates


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
        groups = [[
            (Path("/a.txt"), 100, 1000.0),  # oldest
            (Path("/b.txt"), 100, 2000.0),
            (Path("/c.txt"), 100, 3000.0),
        ]]

        to_delete = get_files_to_delete(groups)

        paths = [p for p, _ in to_delete]
        assert Path("/a.txt") not in paths
        assert Path("/b.txt") in paths
        assert Path("/c.txt") in paths


class TestFindDuplicates:
    def test_finds_duplicates(self, tmp_path):
        (tmp_path / "file1.txt").write_text("duplicate")
        (tmp_path / "file2.txt").write_text("duplicate")
        (tmp_path / "unique.txt").write_text("unique")

        files = scan_directory(tmp_path)
        duplicates = find_duplicates(files)

        assert len(duplicates) == 1
        assert len(duplicates[0]) == 2

    def test_no_duplicates(self, tmp_path):
        (tmp_path / "file1.txt").write_text("content a")
        (tmp_path / "file2.txt").write_text("content b")

        files = scan_directory(tmp_path)
        duplicates = find_duplicates(files)

        assert len(duplicates) == 0

    def test_empty_files_not_duplicates(self, tmp_path):
        (tmp_path / "empty1.txt").write_text("")
        (tmp_path / "empty2.txt").write_text("")

        files = scan_directory(tmp_path)
        duplicates = find_duplicates(files)

        assert len(duplicates) == 0
