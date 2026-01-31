# DupeScan

A CLI tool to find and optionally delete duplicate files and folders in a directory.

## Installation

```bash
uv sync
```

## Usage

Scan a directory for duplicates:

```bash
uv run dupescan /path/to/directory
```

Scan and delete duplicates (keeps the oldest copy):

```bash
uv run dupescan /path/to/directory --delete
```

### Options

| Option | Description |
|--------|-------------|
| `--delete` | Delete duplicate files and folders, keeping the oldest copy based on modification time |
| `--help` | Show help message |

### Example Output

```
Scanning: /path/to/directory
Found 1247 files, checking for duplicates...

Found 2 set(s) of duplicates:

[1] 2 files (1.5 MB each):
    KEEP   /path/to/photos/photo.jpg (2023-01-15)
    DELETE /path/to/photos/photo_copy.jpg (2024-06-20)

[2] 3 files (24.0 KB each):
    KEEP   /path/to/docs/report.pdf (2022-03-10)
    DELETE /path/to/docs/report_v2.pdf (2023-08-01)
    DELETE /path/to/docs/report_final.pdf (2024-01-05)

Total: 3 duplicate file(s) (1.5 MB wasted)

Delete 3 file(s) (1.5 MB)? [y/N]: y

Deleted 3 file(s), freed 1.5 MB
```

## How It Works

DupeScan finds duplicates in two phases:

### Duplicate Folders

First, DupeScan detects duplicate folders. Two sibling directories (directories with the same parent) are considered duplicates if they contain files with identical names and content. The comparison is shallow—only immediate files are compared, not subdirectories.

When duplicate folders are found, the entire folder is treated as a unit. Deletion removes the entire folder.

### Duplicate Files

After folder duplicates are identified, DupeScan finds duplicate files among the remaining files:

1. **Group by directory and file size** - Files are first grouped by their parent directory and size. Only files in the same directory with matching sizes are considered potential duplicates.

2. **Compare by hash** - For files with matching sizes in the same directory, a SHA-256 hash is computed. Files with identical hashes are true duplicates. Hashing is done in 64KB chunks to handle large files without loading them entirely into memory.

When deleting, DupeScan keeps the file or folder with the oldest modification time and removes all other copies.

### What Gets Scanned

- Recursively scans all subdirectories
- Skips symbolic links
- Skips hidden files and directories (names starting with `.`)
- Only considers files/folders in the same directory as potential duplicates
- Empty folders or folders with only subdirectories are not considered for folder duplication

## Development

Run tests:

```bash
uv run pytest
```
