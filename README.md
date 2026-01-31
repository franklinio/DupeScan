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
    KEEP   /path/to/photo.jpg (2023-01-15)
    DELETE /path/to/backup/photo.jpg (2024-06-20)

[2] 3 files (24.0 KB each):
    KEEP   /path/to/doc.pdf (2022-03-10)
    DELETE /path/to/old/doc.pdf (2023-08-01)
    DELETE /path/to/archive/doc.pdf (2024-01-05)

Total: 3 duplicate file(s) (1.5 MB wasted)

Delete 3 file(s) (1.5 MB)? [y/N]: y

Deleted 3 file(s), freed 1.5 MB
```

## How It Works

DupeScan uses a two-phase approach to efficiently find duplicates:

1. **Group by file size** - Files are first grouped by their size. Files with unique sizes are skipped immediately since they cannot have duplicates. This avoids expensive hash computations for most files.

2. **Compare by hash** - For files with matching sizes, a SHA-256 hash is computed. Files with identical hashes are true duplicates. Hashing is done in 64KB chunks to handle large files without loading them entirely into memory.

When deleting, DupeScan keeps the file with the oldest modification time and removes all other copies.

### What Gets Scanned

- Recursively scans all subdirectories
- Skips symbolic links
- Skips hidden files and directories (names starting with `.`)

## Development

Run tests:

```bash
uv run pytest
```
