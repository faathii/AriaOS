"""AriaOS `os-packages` connector: Arch Linux package inspection, updates, and safe cache hygiene."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

PKG_RE = re.compile(r"^[a-z0-9@._+-]+$")
CACHE_DIR = Path("/var/cache/pacman/pkg")

server = ConnectorServer(connector_id="os-packages", version="0.1.0")


def _run(cmd: List[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except FileNotFoundError as exc:
        raise ConnectorError(f"Required binary not found: {cmd[0]}") from exc


def _require_pacman() -> None:
    if not shutil.which("pacman"):
        raise ConnectorError("'pacman' is only available on Arch Linux systems")


def _with_sudo(cmd: List[str]) -> List[str]:
    if hasattr(os, "geteuid") and os.geteuid() != 0 and shutil.which("sudo"):
        return ["sudo", "-n"] + cmd
    return cmd


@server.tool("list_installed_packages")
def list_installed_packages(args: Dict[str, Any]) -> Dict[str, Any]:
    """List installed packages via `pacman -Q`, optionally filtered."""
    _require_pacman()
    query = str(args.get("query", "")).strip().lower()
    limit = max(1, min(int(args.get("limit", 30)), 200))

    res = _run(["pacman", "-Q"])
    if res.returncode != 0:
        raise ConnectorError(res.stderr.strip() or "Failed to query pacman")

    matches = []
    total_installed = 0
    for line in res.stdout.splitlines():
        if not line.strip():
            continue
        total_installed += 1
        name, _, version = line.partition(" ")
        if query and query not in name.lower():
            continue
        if len(matches) < limit:
            matches.append({"name": name, "version": version.strip()})

    return {
        "total_installed": total_installed,
        "filter": query or None,
        "packages": matches,
    }


@server.tool("search_packages")
def search_packages(args: Dict[str, Any]) -> Dict[str, Any]:
    """Search Arch repositories via `pacman -Ss`."""
    query = str(args.get("query", "")).strip()
    if not query:
        raise ConnectorError("Parameter 'query' must be non-empty", code=-32602)
    _require_pacman()
    limit = max(1, min(int(args.get("limit", 15)), 50))

    res = _run(["pacman", "-Ss", query])
    if res.returncode not in (0, 1):
        raise ConnectorError(res.stderr.strip() or "pacman search failed")

    results = []
    lines = res.stdout.splitlines()
    for idx in range(0, len(lines), 2):
        header = lines[idx].strip()
        desc = lines[idx + 1].strip() if idx + 1 < len(lines) else ""
        if not header:
            continue
        results.append({"entry": header, "description": desc})
        if len(results) >= limit:
            break

    return {"query": query, "results": results}


@server.tool("check_system_updates")
def check_system_updates(_args: Dict[str, Any]) -> Dict[str, Any]:
    """Check pending package updates and pacman cache size."""
    _require_pacman()

    cache_bytes = 0
    cached_files = 0
    if CACHE_DIR.exists():
        for item in CACHE_DIR.iterdir():
            if item.is_file():
                cached_files += 1
                cache_bytes += item.stat().st_size

    cmd = ["checkupdates"] if shutil.which("checkupdates") else ["pacman", "-Qu"]
    res = _run(cmd, timeout=60)
    updates = [line.strip() for line in res.stdout.splitlines() if line.strip()]

    return {
        "pending_updates_count": len(updates),
        "pending_updates": updates[:50],
        "pacman_cache_files": cached_files,
        "pacman_cache_mb": round(cache_bytes / (1024 * 1024), 1),
    }


@server.tool("clean_package_cache")
def clean_package_cache(args: Dict[str, Any]) -> Dict[str, Any]:
    """Clean older pacman cache files using `paccache` safely."""
    keep = max(0, min(int(args.get("keep_versions", 2)), 5))
    dry_run = bool(args.get("dry_run", True))
    if not shutil.which("paccache"):
        raise ConnectorError("'paccache' not found (install pacman-contrib)")

    flag = "-d" if dry_run else "-r"
    cmd = ["paccache", flag, "-k", str(keep)]
    if not dry_run:
        cmd = _with_sudo(cmd)

    res = _run(cmd, timeout=60)
    if res.returncode != 0:
        raise ConnectorError(res.stderr.strip() or "paccache failed")
    return {"dry_run": dry_run, "keep_versions": keep, "output": res.stdout.strip()}


@server.tool("install_package")
def install_package(args: Dict[str, Any]) -> Dict[str, Any]:
    """Install one Arch package (requires privileged confirmation in aria-daemon)."""
    pkg = str(args.get("package", "")).strip()
    if not pkg or not PKG_RE.match(pkg):
        raise ConnectorError("Invalid package name", code=-32602)
    _require_pacman()

    cmd = _with_sudo(["pacman", "-S", "--noconfirm", "--needed", pkg])
    res = _run(cmd, timeout=300)
    if res.returncode != 0:
        raise ConnectorError(res.stderr.strip() or f"Failed to install {pkg}")
    return {"package": pkg, "installed": True}


if __name__ == "__main__":
    server.run_stdio()
