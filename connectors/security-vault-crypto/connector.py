#!/usr/bin/env python3
"""KeePassXC, VeraCrypt, Timeshift, and Flameshot connector for AriaOS."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

server = ConnectorServer("security-vault-crypto", "0.1.0")
KDBX_SIG = b"\x03\xd9\xa2\x9a\x67\xfb\x4b\xb5"


@server.tool("keepassxc_check_db")
def keepassxc_check_db(params: dict[str, Any]) -> dict[str, Any]:
    raw_path = params.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ConnectorError("'path' must be a non-empty string.", -32602)

    db = Path(raw_path).expanduser().resolve()
    if not db.is_file() or db.suffix.lower() != ".kdbx":
        raise ConnectorError(f"Expected an existing .kdbx database: {db}", -32602)

    head = db.read_bytes()[:12]
    return {
        "path": str(db),
        "size_bytes": db.stat().st_size,
        "valid_kdbx_signature": head.startswith(KDBX_SIG),
        "keepassxc_cli_installed": bool(shutil.which("keepassxc-cli")),
    }


@server.tool("veracrypt_list_volumes")
def veracrypt_list_volumes(params: dict[str, Any]) -> dict[str, Any]:
    vc = shutil.which("veracrypt")
    if not vc:
        raise ConnectorError("VeraCrypt is not installed on this system.", -32000)

    proc = subprocess.run([vc, "--text", "--list"], capture_output=True, text=True, timeout=10, check=False)
    output = (proc.stdout or proc.stderr).strip()
    return {"installed": True, "returncode": proc.returncode, "output": output}


@server.tool("timeshift_list_snapshots")
def timeshift_list_snapshots(params: dict[str, Any]) -> dict[str, Any]:
    ts = shutil.which("timeshift")
    if not ts:
        raise ConnectorError("Timeshift is not installed on this system.", -32000)

    proc = subprocess.run([ts, "--list"], capture_output=True, text=True, timeout=15, check=False)
    if proc.returncode != 0:
        raise ConnectorError(proc.stderr.strip() or proc.stdout.strip() or "timeshift --list failed", -32000)
    return {"output": proc.stdout.strip()}


@server.tool("flameshot_capture")
def flameshot_capture(params: dict[str, Any]) -> dict[str, Any]:
    mode = params.get("mode", "gui")
    raw_out = params.get("output_path")
    if mode not in {"gui", "full"}:
        raise ConnectorError("'mode' must be 'gui' or 'full'.", -32602)

    cmd_args = [mode]
    if raw_out is not None:
        if not isinstance(raw_out, str) or not raw_out.strip():
            raise ConnectorError("'output_path' must be a non-empty string.", -32602)
        out = Path(raw_out).expanduser().resolve()
        if out.exists():
            raise ConnectorError(f"Refusing to overwrite existing screenshot: {out}", -32602)
        cmd_args.extend(["-p", str(out)])

    fs = shutil.which("flameshot")
    if not fs:
        raise ConnectorError("Flameshot is not installed on this system.", -32000)

    proc = subprocess.Popen([fs, *cmd_args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return {"launched": True, "mode": mode, "pid": proc.pid}


if __name__ == "__main__":
    server.run_stdio()
