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

from aria_sdk import (  # noqa: E402
    ConnectorError,
    ConnectorServer,
    chown_for_context,
    launch_in_desktop_session,
    resolve_desktop_context,
)

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
    ctx = resolve_desktop_context(target)
    forbidden = {target.anchor, str(Path.home().resolve()), str(ctx.home.resolve()), "/etc", "/usr", "/bin", "/boot", "/var", "/home"}
    if str(target) in forbidden or target.parent == target:
        raise ConnectorError(f"Refusing to trash protected path: {target}", code=-32602)

    trash_root = ctx.xdg_data_home / "Trash"
    files_dir = trash_root / "files"
    info_dir = trash_root / "info"
    files_dir.mkdir(parents=True, exist_ok=True)
    info_dir.mkdir(parents=True, exist_ok=True)
    for d in (trash_root, files_dir, info_dir):
        chown_for_context(d, ctx)

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
    chown_for_context(info_path, ctx)
    chown_for_context(trashed_path, ctx)

    return {
        "trashed": True,
        "owner": ctx.username,
        "original_path": str(target),
        "trash_path": str(trashed_path),
        "trashinfo_path": str(info_path),
    }


@server.tool("create_directory")
def create_directory(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new folder or directory recursively with correct user ownership."""
    raw_path = args.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ConnectorError("Parameter 'path' must be a non-empty string", code=-32602)
    target = Path(raw_path).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    ctx = resolve_desktop_context(target)
    chown_for_context(target, ctx)
    return {
        "created": True,
        "path": str(target),
        "owner": ctx.username,
    }


@server.tool("write_file")
def write_file(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create or overwrite a file with given text content."""
    raw_path = args.get("path")
    content = str(args.get("content", ""))
    append = bool(args.get("append", False))
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ConnectorError("Parameter 'path' must be a non-empty string", code=-32602)
    target = Path(raw_path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    ctx = resolve_desktop_context(target.parent)
    chown_for_context(target.parent, ctx)
    mode = "a" if append else "w"
    with open(target, mode, encoding="utf-8") as f:
        f.write(content)
    chown_for_context(target, ctx)
    return {
        "written": True,
        "path": str(target),
        "bytes": len(content.encode("utf-8")),
        "append": append,
    }


@server.tool("delete_path")
def delete_path(args: Dict[str, Any]) -> Dict[str, Any]:
    """Permanently delete a file or directory."""
    target = _require_path(args.get("path"))
    forbidden = {target.anchor, str(Path.home().resolve()), "/etc", "/usr", "/bin", "/boot", "/var", "/home", "/root"}
    if str(target) in forbidden or target.parent == target:
        raise ConnectorError(f"Refusing to delete protected system path: {target}", code=-32602)
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    return {"deleted": True, "path": str(target)}


@server.tool("copy_path")
def copy_path(args: Dict[str, Any]) -> Dict[str, Any]:
    """Copy a file or directory to a destination path."""
    src = _require_path(args.get("source"))
    raw_dst = args.get("destination")
    if not isinstance(raw_dst, str) or not raw_dst.strip():
        raise ConnectorError("Parameter 'destination' must be a non-empty string", code=-32602)
    dst = Path(raw_dst).expanduser().resolve()
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    ctx = resolve_desktop_context(dst)
    chown_for_context(dst, ctx)
    return {"copied": True, "source": str(src), "destination": str(dst)}


@server.tool("move_path")
def move_path(args: Dict[str, Any]) -> Dict[str, Any]:
    """Move or rename a file or directory."""
    src = _require_path(args.get("source"))
    raw_dst = args.get("destination")
    if not isinstance(raw_dst, str) or not raw_dst.strip():
        raise ConnectorError("Parameter 'destination' must be a non-empty string", code=-32602)
    dst = Path(raw_dst).expanduser().resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    ctx = resolve_desktop_context(dst)
    chown_for_context(dst, ctx)
    return {"moved": True, "source": str(src), "destination": str(dst)}


@server.tool("open_in_dolphin")
def open_in_dolphin(args: Dict[str, Any]) -> Dict[str, Any]:
    """Open a directory or select a file in the active desktop file manager (Thunar / Dolphin)."""
    target = _require_path(args.get("path"))
    select_file = bool(args.get("select_file", True))
    fm_bin = shutil.which("thunar") or shutil.which("dolphin") or shutil.which("xdg-open")
    if not fm_bin:
        return {
            "launched": False,
            "path": str(target),
            "reason": "no graphical file manager found on PATH",
        }
    ctx = resolve_desktop_context(target)
    if "thunar" in fm_bin:
        cmd = [fm_bin, str(target if target.is_dir() else target.parent)]
    elif "dolphin" in fm_bin:
        cmd = [fm_bin, "--select", str(target)] if (select_file and target.is_file()) else [fm_bin, str(target)]
    else:
        cmd = [fm_bin, str(target if target.is_dir() else target.parent)]
    proc = launch_in_desktop_session(cmd, ctx)
    return {
        "launched": True,
        "pid": proc.pid,
        "session_user": ctx.username,
        "command": cmd,
        "path": str(target),
    }


if __name__ == "__main__":
    server.run_stdio()

