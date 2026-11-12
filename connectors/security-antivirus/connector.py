"""AriaOS `security-antivirus` connector: 100% free ClamAV integration & reversible quarantine."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

CLAMAV_DB_DIR = Path("/var/lib/clamav")
CLAMD_SOCKET = Path("/run/clamav/clamd.ctl")

server = ConnectorServer(connector_id="security-antivirus", version="0.1.0")


def _quarantine_dir() -> Path:
    override = os.environ.get("ARIAOS_QUARANTINE_DIR")
    if override:
        return Path(override).expanduser()
    # When running as the OS daemon (root), isolate malware inside a system vault inaccessible to normal apps.
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        return Path("/var/lib/ariaos/quarantine")
    data_home = os.environ.get("XDG_DATA_HOME")
    base = Path(data_home).expanduser() if data_home else Path.home() / ".local" / "share"
    return base / "ariaos" / "quarantine"


def _load_manifest(qdir: Path) -> List[Dict[str, Any]]:
    manifest_file = qdir / "manifest.json"
    if not manifest_file.exists():
        return []
    try:
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _save_manifest(qdir: Path, items: List[Dict[str, Any]]) -> None:
    qdir.mkdir(parents=True, exist_ok=True)
    manifest_file = qdir / "manifest.json"
    manifest_file.write_text(json.dumps(items, indent=2), encoding="utf-8")


def _sha256(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _systemctl_state(unit: str) -> str:
    if not shutil.which("systemctl"):
        return "unavailable"
    proc = subprocess.run(
        ["systemctl", "is-active", unit],
        text=True,
        capture_output=True,
        timeout=5,
    )
    return (proc.stdout or proc.stderr or "unknown").strip()


def _db_files_info() -> List[Dict[str, Any]]:
    if not CLAMAV_DB_DIR.exists():
        return []
    dbs: List[Dict[str, Any]] = []
    for entry in sorted(CLAMAV_DB_DIR.iterdir()):
        if entry.is_file() and entry.suffix.lower() in {".cvd", ".cld", ".cud"}:
            st = entry.stat()
            dbs.append(
                {
                    "name": entry.name,
                    "size_bytes": st.st_size,
                    "updated_utc": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
                }
            )
    return dbs


@server.tool("av_status")
def av_status(_args: Dict[str, Any]) -> Dict[str, Any]:
    """Return ClamAV availability, daemon/freshclam services, database files, and quarantine count."""
    binaries = {
        name: shutil.which(name)
        for name in ("clamscan", "clamdscan", "freshclam", "clamonacc")
    }
    version = None
    if binaries["clamscan"]:
        proc = subprocess.run([binaries["clamscan"], "--version"], text=True, capture_output=True, timeout=5)
        version = proc.stdout.strip() or proc.stderr.strip()

    qdir = _quarantine_dir()
    dbs = _db_files_info()
    return {
        "engine": "ClamAV (GPLv2, 100% Free)",
        "installed": bool(binaries["clamscan"] or binaries["clamdscan"]),
        "version": version,
        "binaries": binaries,
        "services": {
            "clamav-daemon": _systemctl_state("clamav-daemon.service"),
            "clamav-freshclam": _systemctl_state("clamav-freshclam.service"),
        },
        "clamd_socket_present": CLAMD_SOCKET.exists(),
        "databases_ready": len(dbs) > 0,
        "databases": dbs,
        "quarantine_dir": str(qdir),
        "quarantine_count": len(_load_manifest(qdir)),
    }


def _parse_clam_findings(output: str) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    for line in output.splitlines():
        line = line.strip()
        if line.endswith(" FOUND") and ":" in line:
            path_part, rest = line.rsplit(":", 1)
            signature = rest.strip()[:-6].strip()
            findings.append({"path": path_part.strip(), "signature": signature})
    return findings


@server.tool("av_scan_path")
def av_scan_path(args: Dict[str, Any]) -> Dict[str, Any]:
    """Scan a file or directory using ClamAV."""
    raw_path = args.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ConnectorError("Parameter 'path' must be a non-empty string", code=-32602)
    target = Path(raw_path).expanduser().resolve()
    if not target.exists():
        raise ConnectorError(f"Path does not exist: {target}", code=-32602)

    recursive = bool(args.get("recursive", True))
    max_filesize_mb = max(1, min(int(args.get("max_filesize_mb") or 200), 4096))

    clamdscan = shutil.which("clamdscan")
    clamscan = shutil.which("clamscan")

    use_daemon = bool(clamdscan and CLAMD_SOCKET.exists())
    if use_daemon:
        cmd = [clamdscan, "--fdpass", "--multiscan", "--infected", "--no-summary", str(target)]
        engine_used = "clamdscan"
    elif clamscan:
        if not _db_files_info():
            return {
                "scanned": False,
                "path": str(target),
                "engine": "clamscan",
                "error": "No ClamAV signature databases found in /var/lib/clamav yet. Run 'freshclam' (or av_update_signatures) once online.",
                "threats": [],
            }
        cmd = [clamscan, "--infected", f"--max-filesize={max_filesize_mb}M", f"--max-scansize={max_filesize_mb}M"]
        if recursive and target.is_dir():
            cmd.append("--recursive")
        cmd.append(str(target))
        engine_used = "clamscan"
    else:
        return {
            "scanned": False,
            "path": str(target),
            "engine": "none",
            "error": "ClamAV is not installed on this host (missing clamscan/clamdscan).",
            "threats": [],
        }

    started = time.monotonic()
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=600)
    elapsed = round(time.monotonic() - started, 3)

    combined = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
    threats = _parse_clam_findings(combined)
    # clamscan/clamdscan exit codes: 0 = clean, 1 = infected, 2 = error
    if proc.returncode not in (0, 1):
        raise ConnectorError(f"ClamAV scan failed (exit {proc.returncode}): {combined.strip()}", code=-32000)

    return {
        "scanned": True,
        "path": str(target),
        "engine": engine_used,
        "clean": proc.returncode == 0 and len(threats) == 0,
        "threat_count": len(threats),
        "threats": threats,
        "duration_seconds": elapsed,
        "summary": proc.stdout.strip()[-1000:],
    }


@server.tool("av_update_signatures")
def av_update_signatures(_args: Dict[str, Any]) -> Dict[str, Any]:
    """Run freshclam to download the latest free ClamAV virus signatures."""
    freshclam = shutil.which("freshclam")
    if not freshclam:
        raise ConnectorError("freshclam binary not found. Install 'clamav' package.", code=-32000)
    proc = subprocess.run([freshclam, "--stdout"], text=True, capture_output=True, timeout=180)
    if proc.returncode != 0:
        raise ConnectorError(f"freshclam failed: {(proc.stderr or proc.stdout).strip()}", code=-32000)
    return {
        "updated": True,
        "output": proc.stdout.strip()[-1500:],
        "databases": _db_files_info(),
    }


@server.tool("av_quarantine_list")
def av_quarantine_list(_args: Dict[str, Any]) -> Dict[str, Any]:
    """List isolated items stored in the AriaOS quarantine vault."""
    qdir = _quarantine_dir()
    items = _load_manifest(qdir)
    enriched = []
    for item in items:
        vault_file = qdir / "vault" / str(item.get("id", ""))
        enriched.append({**item, "vault_present": vault_file.exists()})
    return {
        "quarantine_dir": str(qdir),
        "count": len(enriched),
        "items": enriched,
    }


@server.tool("av_quarantine_file")
def av_quarantine_file(args: Dict[str, Any]) -> Dict[str, Any]:
    """Safely isolate a suspicious file in quarantine without permanent deletion."""
    raw_path = args.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ConnectorError("Parameter 'path' must be a non-empty string", code=-32602)
    target = Path(raw_path).expanduser().resolve()
    if not target.exists() or not target.is_file():
        raise ConnectorError(f"Target file does not exist: {target}", code=-32602)

    home = Path.home().resolve()
    forbidden = {target.anchor, str(home), "/etc", "/usr", "/bin", "/boot", "/var", "/home"}
    if str(target) in forbidden:
        raise ConnectorError(f"Refusing to quarantine protected path: {target}", code=-32602)

    reason = str(args.get("reason") or "Manual or ClamAV detection").strip()
    qdir = _quarantine_dir()
    vault_dir = qdir / "vault"
    vault_dir.mkdir(parents=True, exist_ok=True)
    for d in (qdir, vault_dir):
        try:
            os.chmod(d, 0o700)
        except OSError:
            pass

    q_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    vault_file = vault_dir / q_id
    digest = _sha256(target)
    st = target.stat()
    size = st.st_size

    shutil.move(str(target), str(vault_file))
    try:
        os.chmod(vault_file, 0o400)
    except OSError:
        pass

    record = {
        "id": q_id,
        "original_path": str(target),
        "filename": target.name,
        "size_bytes": size,
        "sha256": digest,
        "uid": getattr(st, "st_uid", None),
        "gid": getattr(st, "st_gid", None),
        "reason": reason,
        "quarantined_utc": datetime.now(timezone.utc).isoformat(),
    }
    items = _load_manifest(qdir)
    items.append(record)
    _save_manifest(qdir, items)
    return {"quarantined": True, "record": record}


@server.tool("av_restore_file")
def av_restore_file(args: Dict[str, Any]) -> Dict[str, Any]:
    """Restore a quarantined file to its original path without overwriting existing files."""
    q_id = args.get("quarantine_id")
    if not isinstance(q_id, str) or not q_id.strip():
        raise ConnectorError("Parameter 'quarantine_id' must be a non-empty string", code=-32602)

    qdir = _quarantine_dir()
    items = _load_manifest(qdir)
    match = next((item for item in items if item.get("id") == q_id), None)
    if not match:
        raise ConnectorError(f"Quarantine ID not found: {q_id}", code=-32602)

    vault_file = qdir / "vault" / q_id
    if not vault_file.exists():
        raise ConnectorError(f"Vault payload missing for {q_id}", code=-32000)

    orig_path = Path(match["original_path"])
    if orig_path.exists():
        raise ConnectorError(f"Refusing to overwrite existing file at {orig_path}", code=-32000)

    orig_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(vault_file, 0o600)
    except OSError:
        pass
    shutil.move(str(vault_file), str(orig_path))
    if hasattr(os, "chown") and match.get("uid") is not None and match.get("gid") is not None:
        try:
            os.chown(orig_path, int(match["uid"]), int(match["gid"]))
        except OSError:
            pass

    remaining = [item for item in items if item.get("id") != q_id]
    _save_manifest(qdir, remaining)
    return {"restored": True, "quarantine_id": q_id, "restored_path": str(orig_path)}


if __name__ == "__main__":
    server.run_stdio()

