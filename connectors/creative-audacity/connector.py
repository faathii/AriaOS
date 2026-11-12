#!/usr/bin/env python3
"""Audacity connector for AriaOS (mod-script-pipe IPC)."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

server = ConnectorServer("creative-audacity", "0.1.0")


def _pipe_paths() -> tuple[Path, Path]:
    if os.name == "nt":
        return Path(r"\\.\pipe\ToSrvPipe"), Path(r"\\.\pipe\FromSrvPipe")
    uid = os.getuid() if hasattr(os, "getuid") else 1000
    return Path(f"/tmp/audacity_script_pipe.to.{uid}"), Path(f"/tmp/audacity_script_pipe.from.{uid}")


@server.tool("pipe_status")
def pipe_status(params: dict[str, Any]) -> dict[str, Any]:
    to_pipe, from_pipe = _pipe_paths()
    return {
        "audacity_installed": bool(shutil.which("audacity")),
        "to_pipe": str(to_pipe),
        "from_pipe": str(from_pipe),
        "pipe_ready": to_pipe.exists() and from_pipe.exists(),
    }


@server.tool("send_pipe_command")
def send_pipe_command(params: dict[str, Any]) -> dict[str, Any]:
    cmd = params.get("command")
    if not isinstance(cmd, str) or not cmd.strip() or "\n" in cmd or "\r" in cmd:
        raise ConnectorError("'command' must be a non-empty single-line string.", -32602)

    to_pipe, from_pipe = _pipe_paths()
    if not (to_pipe.exists() and from_pipe.exists()):
        raise ConnectorError(
            "Audacity mod-script-pipe is not active. Start Audacity and enable mod-script-pipe in Preferences -> Modules.",
            -32000,
        )

    try:
        with to_pipe.open("w", encoding="utf-8", buffering=1) as writer:
            writer.write(cmd.strip() + "\n")
            writer.flush()
        lines: list[str] = []
        with from_pipe.open("r", encoding="utf-8") as reader:
            while True:
                line = reader.readline()
                if not line or line == "\n":
                    break
                lines.append(line.rstrip("\r\n"))
    except OSError as exc:
        raise ConnectorError(f"Failed communicating with Audacity pipe: {exc}", -32000) from exc

    return {"command": cmd.strip(), "response": "\n".join(lines)}


if __name__ == "__main__":
    server.run_stdio()
