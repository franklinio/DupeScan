# DupeScan

A CLI tool to find and optionally delete duplicate files in a directory.

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
| `--delete` | Delete duplicate files, keeping the oldest copy based on modification time |
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

DupeScan uses a two-phase approach to efficiently find duplicates:

1. **Group by directory and file size** - Files are first grouped by their parent directory and size. Only files in the same directory with matching sizes are considered potential duplicates. This avoids expensive hash computations for most files.

2. **Compare by hash** - For files with matching sizes in the same directory, a SHA-256 hash is computed. Files with identical hashes are true duplicates. Hashing is done in 64KB chunks to handle large files without loading them entirely into memory.

When deleting, DupeScan keeps the file with the oldest modification time and removes all other copies.

### What Gets Scanned

- Recursively scans all subdirectories
- Skips symbolic links
- Skips hidden files and directories (names starting with `.`)
- Only considers files in the same directory as potential duplicates (files with identical content in different directories are not flagged)

## Development

Run tests:

```bash
uv run pytest
```
