"""AriaOS `os-storage` connector: block-device inspection and safe archive handling."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

server = ConnectorServer(connector_id="os-storage", version="0.1.0")


def _require_path(raw: Any, label: str) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise ConnectorError(f"Parameter '{label}' must be a non-empty string", code=-32602)
    return Path(raw).expanduser().resolve()


def _safe_extract_zip(zf: zipfile.ZipFile, dest: Path) -> List[str]:
    extracted: List[str] = []
    for member in zf.infolist():
        target = (dest / member.filename).resolve()
        if not target.is_relative_to(dest):
            raise ConnectorError(f"Unsafe archive path traversal blocked: {member.filename}", code=-32602)
        if member.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        if target.exists():
            raise ConnectorError(f"Refusing to overwrite existing file: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(member) as src, target.open("wb") as out:
            shutil.copyfileobj(src, out)
        extracted.append(member.filename)
    return extracted


def _safe_extract_tar(tf: tarfile.TarFile, dest: Path) -> List[str]:
    extracted: List[str] = []
    for member in tf.getmembers():
        target = (dest / member.name).resolve()
        if not target.is_relative_to(dest):
            raise ConnectorError(f"Unsafe archive path traversal blocked: {member.name}", code=-32602)
        if member.isdir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        if not member.isfile():
            raise ConnectorError(f"Unsupported special tar entry blocked: {member.name}", code=-32602)
        if target.exists():
            raise ConnectorError(f"Refusing to overwrite existing file: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        src = tf.extractfile(member)
        if src is not None:
            with src, target.open("wb") as out:
                shutil.copyfileobj(src, out)
            extracted.append(member.name)
    return extracted


@server.tool("list_block_devices")
def list_block_devices(_args: Dict[str, Any]) -> Dict[str, Any]:
    """Query block devices and mountpoints via `lsblk -J`."""
    if not shutil.which("lsblk"):
        raise ConnectorError("'lsblk' is only available on Linux systems")
    res = subprocess.run(
        ["lsblk", "-J", "-o", "NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,MODEL"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if res.returncode != 0:
        raise ConnectorError(res.stderr.strip() or "lsblk failed")
    return json.loads(res.stdout)


@server.tool("inspect_archive")
def inspect_archive(args: Dict[str, Any]) -> Dict[str, Any]:
    """List entries and sizes inside a .zip or .tar* archive."""
    archive = _require_path(args.get("archive_path"), "archive_path")
    if not archive.is_file():
        raise ConnectorError(f"Archive does not exist: {archive}", code=-32602)

    entries: List[Dict[str, Any]] = []
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive, "r") as zf:
            for info in zf.infolist()[:200]:
                entries.append({"name": info.filename, "size_bytes": info.file_size})
    elif tarfile.is_tarfile(archive):
        with tarfile.open(archive, "r:*") as tf:
            for member in tf.getmembers()[:200]:
                entries.append({"name": member.name, "size_bytes": member.size})
    else:
        raise ConnectorError(f"Unsupported archive format: {archive.name}", code=-32602)

    return {"archive_path": str(archive), "entries": entries, "count": len(entries)}


@server.tool("create_archive")
def create_archive(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create a .zip or .tar.gz archive from source_path."""
    src = _require_path(args.get("source_path"), "source_path")
    dst = _require_path(args.get("archive_path"), "archive_path")
    if not src.exists():
        raise ConnectorError(f"Source path does not exist: {src}", code=-32602)
    if dst.exists():
        raise ConnectorError(f"Refusing to overwrite existing archive: {dst}", code=-32602)

    dst.parent.mkdir(parents=True, exist_ok=True)
    name_lower = dst.name.lower()
    if name_lower.endswith(".zip"):
        with zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            if src.is_file():
                zf.write(src, arcname=src.name)
            else:
                for item in sorted(src.rglob("*")):
                    if item.is_file():
                        zf.write(item, arcname=str(item.relative_to(src.parent)))
    elif name_lower.endswith((".tar.gz", ".tgz")):
        with tarfile.open(dst, "w:gz") as tf:
            tf.add(src, arcname=src.name)
    else:
        raise ConnectorError("Supported output extensions: .zip, .tar.gz, .tgz", code=-32602)

    return {"archive_path": str(dst), "size_bytes": dst.stat().st_size}


@server.tool("extract_archive")
def extract_archive(args: Dict[str, Any]) -> Dict[str, Any]:
    """Extract a .zip or .tar* archive safely without path traversal or overwrites."""
    archive = _require_path(args.get("archive_path"), "archive_path")
    dest = _require_path(args.get("destination_dir"), "destination_dir")
    if not archive.is_file():
        raise ConnectorError(f"Archive does not exist: {archive}", code=-32602)

    dest.mkdir(parents=True, exist_ok=True)
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive, "r") as zf:
            files = _safe_extract_zip(zf, dest)
    elif tarfile.is_tarfile(archive):
        with tarfile.open(archive, "r:*") as tf:
            files = _safe_extract_tar(tf, dest)
    else:
        raise ConnectorError(f"Unsupported archive format: {archive.name}", code=-32602)

    return {"destination_dir": str(dest), "extracted_count": len(files), "files": files[:100]}


if __name__ == "__main__":
    server.run_stdio()
