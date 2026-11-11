"""AriaOS `os-files` connector: inspect, deduplicate, and safely organize directories."""

from __future__ import annotations

import hashlib
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

CATEGORY_MAP: Dict[str, str] = {
    ".pdf": "Documents",
    ".doc": "Documents",
    ".docx": "Documents",
    ".odt": "Documents",
    ".txt": "Documents",
    ".md": "Documents",
    ".csv": "Documents",
    ".xlsx": "Documents",
    ".pptx": "Documents",
    ".png": "Images",
    ".jpg": "Images",
    ".jpeg": "Images",
    ".webp": "Images",
    ".gif": "Images",
    ".svg": "Images",
    ".mp4": "Videos",
    ".mkv": "Videos",
    ".mov": "Videos",
    ".webm": "Videos",
    ".mp3": "Audio",
    ".wav": "Audio",
    ".flac": "Audio",
    ".ogg": "Audio",
    ".zip": "Archives",
    ".tar": "Archives",
    ".gz": "Archives",
    ".7z": "Archives",
    ".rar": "Archives",
    ".py": "Code",
    ".rs": "Code",
    ".js": "Code",
    ".ts": "Code",
    ".sh": "Code",
    ".json": "Code",
    ".yaml": "Code",
    ".yml": "Code",
}

server = ConnectorServer(connector_id="os-files", version="0.1.0")


def _require_dir(raw_path: Any) -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ConnectorError("Parameter 'path' must be a non-empty string", code=-32602)
    target = Path(raw_path).expanduser().resolve()
    if not target.exists() or not target.is_dir():
        raise ConnectorError(f"Directory does not exist: {target}", code=-32602)
    return target


def _iter_files(root: Path, recursive: bool) -> Iterable[Path]:
    entries = root.rglob("*") if recursive else root.iterdir()
    for item in entries:
        if item.is_file() and not item.is_symlink():
            yield item


def _categorize(file_path: Path) -> str:
    return CATEGORY_MAP.get(file_path.suffix.lower(), "Other")


def _sha256(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


@server.tool("scan_directory")
def scan_directory(args: Dict[str, Any]) -> Dict[str, Any]:
    """Return file counts, total size in bytes, and category breakdown."""
    root = _require_dir(args.get("path"))
    recursive = bool(args.get("recursive", False))

    by_category: Dict[str, int] = defaultdict(int)
    total_bytes = 0
    total_files = 0

    for item in _iter_files(root, recursive=recursive):
        total_files += 1
        total_bytes += item.stat().st_size
        by_category[_categorize(item)] += 1

    return {
        "path": str(root),
        "recursive": recursive,
        "total_files": total_files,
        "total_bytes": total_bytes,
        "categories": dict(sorted(by_category.items())),
    }


@server.tool("find_duplicates")
def find_duplicates(args: Dict[str, Any]) -> Dict[str, Any]:
    """Group exact duplicate files by SHA-256 checksum (prefiltered by file size)."""
    root = _require_dir(args.get("path"))
    recursive = bool(args.get("recursive", True))

    by_size: Dict[int, List[Path]] = defaultdict(list)
    for item in _iter_files(root, recursive=recursive):
        by_size[item.stat().st_size].append(item)

    duplicates: List[Dict[str, Any]] = []
    for size, candidates in by_size.items():
        if len(candidates) < 2:
            continue
        by_hash: Dict[str, List[str]] = defaultdict(list)
        for path in candidates:
            by_hash[_sha256(path)].append(str(path))
        for file_hash, paths in by_hash.items():
            if len(paths) > 1:
                duplicates.append(
                    {"sha256": file_hash, "size_bytes": size, "files": sorted(paths)}
                )

    return {"path": str(root), "duplicate_groups": duplicates}


@server.tool("organize_directory")
def organize_directory(args: Dict[str, Any]) -> Dict[str, Any]:
    """Build or apply a non-destructive top-level organization plan."""
    root = _require_dir(args.get("path"))
    apply_changes = bool(args.get("apply", False))

    planned_moves: List[Dict[str, str]] = []
    skipped: List[Dict[str, str]] = []

    for item in sorted(_iter_files(root, recursive=False)):
        category = _categorize(item)
        dest_dir = root / category
        dest_path = dest_dir / item.name
        if dest_path.exists():
            skipped.append({"source": str(item), "reason": f"Target exists: {dest_path}"})
            continue
        planned_moves.append({"source": str(item), "destination": str(dest_path)})

    if apply_changes:
        for move in planned_moves:
            dest = Path(move["destination"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(move["source"], str(dest))

    return {
        "path": str(root),
        "applied": apply_changes,
        "moves": planned_moves,
        "skipped": skipped,
    }


if __name__ == "__main__":
    server.run_stdio()

