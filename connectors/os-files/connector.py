"""AriaOS `os-files` connector: KDE Dolphin integration, search, inspection, XDG Trash, and organization."""

from __future__ import annotations

import fnmatch
import hashlib
import mimetypes
import os
import shutil
import stat
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List
from urllib.parse import quote

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

MAX_CONTENT_SCAN_BYTES = 2 * 1024 * 1024

server = ConnectorServer(connector_id="os-files", version="0.2.0")


def _require_path(raw_path: Any) -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ConnectorError("Parameter 'path' must be a non-empty string", code=-32602)
    target = Path(raw_path).expanduser().resolve()
    if not target.exists():
        raise ConnectorError(f"Path does not exist: {target}", code=-32602)
    return target


def _require_dir(raw_path: Any) -> Path:
    target = _require_path(raw_path)
    if not target.is_dir():
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


def _matches_name(name: str, query: str) -> bool:
    if any(ch in query for ch in "*?["):
        return fnmatch.fnmatch(name.lower(), query.lower())
    return query.lower() in name.lower()


def _contains_text(file_path: Path, text_query: str) -> bool:
    try:
        if file_path.stat().st_size > MAX_CONTENT_SCAN_BYTES:
            return False
        raw = file_path.read_bytes()
    except OSError:
        return False
    if b"\x00" in raw[:4096]:
        return False
    return text_query.lower() in raw.decode("utf-8", errors="ignore").lower()


@server.tool("search_files")
def search_files(args: Dict[str, Any]) -> Dict[str, Any]:
    """Search files/directories by filename pattern, minimum size, or UTF-8 text content."""
    root = _require_dir(args.get("path"))
    query = args.get("query")
    text_query = args.get("text_query")
    min_size = int(args.get("min_size_bytes") or 0)
    recursive = bool(args.get("recursive", True))
    limit = max(1, min(int(args.get("limit") or 50), 500))

    iterator = root.rglob("*") if recursive else root.iterdir()
    matches: List[Dict[str, Any]] = []
    for item in iterator:
        if item.is_symlink():
            continue
        if query and not _matches_name(item.name, str(query)):
            continue
        is_file = item.is_file()
        try:
            size = item.stat().st_size if is_file else 0
        except OSError:
            continue
        if min_size > 0 and (not is_file or size < min_size):
            continue
        if text_query:
            if not is_file or not _contains_text(item, str(text_query)):
                continue
        matches.append(
            {
                "path": str(item),
                "name": item.name,
                "kind": "file" if is_file else "directory",
                "size_bytes": size,
            }
        )
        if len(matches) >= limit:
            break

    return {
        "path": str(root),
        "count": len(matches),
        "truncated": len(matches) >= limit,
        "matches": matches,
    }


@server.tool("file_info")
def file_info(args: Dict[str, Any]) -> Dict[str, Any]:
    """Return detailed file/directory metadata, MIME type, permissions, and optional SHA-256."""
    target = _require_path(args.get("path"))
    include_hash = bool(args.get("include_hash", False))
    st = target.stat()
    mime, _ = mimetypes.guess_type(str(target))
    result: Dict[str, Any] = {
        "path": str(target),
        "name": target.name,
        "kind": "directory" if target.is_dir() else "file",
        "size_bytes": st.st_size,
        "mime_type": "inode/directory" if target.is_dir() else (mime or "application/octet-stream"),
        "permissions": stat.filemode(st.st_mode),
        "modified_utc": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
    }
    if include_hash and target.is_file():
        result["sha256"] = _sha256(target)
    return result


def _xdg_trash_root() -> Path:
    data_home = os.environ.get("XDG_DATA_HOME")
    base = Path(data_home).expanduser() if data_home else Path.home() / ".local" / "share"
    return base / "Trash"


def _unique_trash_name(files_dir: Path, info_dir: Path, name: str) -> str:
    candidate = name
    idx = 2
    while (files_dir / candidate).exists() or (info_dir / f"{candidate}.trashinfo").exists():
        stem = Path(name).stem
        suffix = Path(name).suffix
        candidate = f"{stem}.{idx}{suffix}" if suffix else f"{name}.{idx}"
        idx += 1
    return candidate


@server.tool("move_to_trash")
def move_to_trash(args: Dict[str, Any]) -> Dict[str, Any]:
    """Move a file or directory safely to FreeDesktop/Dolphin Trash with .trashinfo metadata."""
    target = _require_path(args.get("path"))
    home = Path.home().resolve()
    forbidden = {target.anchor, str(home), "/etc", "/usr", "/bin", "/boot", "/var", "/home"}
    if str(target) in forbidden or target.parent == target:
        raise ConnectorError(f"Refusing to trash protected path: {target}", code=-32602)

    trash_root = _xdg_trash_root()
    files_dir = trash_root / "files"
    info_dir = trash_root / "info"
    files_dir.mkdir(parents=True, exist_ok=True)
    info_dir.mkdir(parents=True, exist_ok=True)

    trash_name = _unique_trash_name(files_dir, info_dir, target.name)
    trashed_path = files_dir / trash_name
    info_path = info_dir / f"{trash_name}.trashinfo"
    deletion_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    info_content = (
        "[Trash Info]\n"
        f"Path={quote(str(target), safe='/')}\n"
        f"DeletionDate={deletion_date}\n"
    )
    info_path.write_text(info_content, encoding="utf-8")
    shutil.move(str(target), str(trashed_path))

    return {
        "trashed": True,
        "original_path": str(target),
        "trash_path": str(trashed_path),
        "trashinfo_path": str(info_path),
    }


@server.tool("open_in_dolphin")
def open_in_dolphin(args: Dict[str, Any]) -> Dict[str, Any]:
    """Open a directory or select a file in KDE Dolphin."""
    target = _require_path(args.get("path"))
    select_file = bool(args.get("select_file", True))
    dolphin_bin = shutil.which("dolphin")
    if not dolphin_bin:
        return {
            "launched": False,
            "path": str(target),
            "reason": "dolphin binary not found on PATH",
        }
    cmd = [dolphin_bin, "--select", str(target)] if (select_file and target.is_file()) else [dolphin_bin, str(target)]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return {"launched": True, "pid": proc.pid, "command": cmd, "path": str(target)}


if __name__ == "__main__":
    server.run_stdio()

