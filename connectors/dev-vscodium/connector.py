#!/usr/bin/env python3
"""VSCodium & Kate connector for AriaOS."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

server = ConnectorServer("dev-vscodium", "0.1.0")
ALLOWED_EDITORS = {"auto", "vscodium", "kate"}


@server.tool("list_extensions")
def list_extensions(params: dict[str, Any]) -> dict[str, Any]:
    codium = shutil.which("codium") or shutil.which("vscodium")
    if not codium:
        raise ConnectorError("VSCodium ('codium') is not installed on this system.", -32000)

    proc = subprocess.run([codium, "--list-extensions", "--show-versions"], capture_output=True, text=True, timeout=15, check=False)
    if proc.returncode != 0:
        raise ConnectorError(proc.stderr.strip() or "Failed listing VSCodium extensions", -32000)

    exts = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    return {"count": len(exts), "extensions": exts}


@server.tool("open_in_editor")
def open_in_editor(params: dict[str, Any]) -> dict[str, Any]:
    raw_path = params.get("path")
    editor = params.get("editor", "auto")
    line = params.get("line")
    column = params.get("column")

    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ConnectorError("'path' must be a non-empty string.", -32602)
    if not isinstance(editor, str) or editor not in ALLOWED_EDITORS:
        raise ConnectorError(f"'editor' must be one of: {', '.join(sorted(ALLOWED_EDITORS))}", -32602)
    if line is not None and (not isinstance(line, int) or line < 1):
        raise ConnectorError("'line' must be an integer >= 1.", -32602)
    if column is not None and (not isinstance(column, int) or column < 1):
        raise ConnectorError("'column' must be an integer >= 1.", -32602)

    target = Path(raw_path).expanduser().resolve()
    if not target.exists():
        raise ConnectorError(f"Path does not exist: {target}", -32602)

    candidates = (
        ["codium", "vscodium"]
        if editor == "vscodium"
        else ["kate"]
        if editor == "kate"
        else ["codium", "vscodium", "kate"]
    )
    binary = next((shutil.which(name) for name in candidates if shutil.which(name)), None)
    if not binary:
        raise ConnectorError(f"No requested editor installed ({', '.join(candidates)}).", -32000)

    bin_name = Path(binary).name
    cmd = [binary]
    if "codium" in bin_name:
        if line is not None:
            loc = f"{target}:{line}:{column}" if column is not None else f"{target}:{line}"
            cmd.extend(["--goto", loc])
        else:
            cmd.append(str(target))
    else:
        if line is not None:
            cmd.extend(["-l", str(line)])
        if column is not None:
            cmd.extend(["-c", str(column)])
        cmd.append(str(target))

    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return {"launched": True, "editor": bin_name, "pid": proc.pid, "path": str(target)}


if __name__ == "__main__":
    server.run_stdio()
