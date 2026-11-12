#!/usr/bin/env python3
"""GIMP connector for AriaOS (cross-platform header inspection + GIMP Script-Fu)."""

from __future__ import annotations

import shutil
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

server = ConnectorServer("creative-gimp", "0.1.0")


def _probe_image_header(path: Path) -> dict[str, Any]:
    with path.open("rb") as fh:
        head = fh.read(32)
        if head[:8] == b"\x89PNG\r\n\x1a\n" and len(head) >= 24:
            w, h = struct.unpack(">II", head[16:24])
            return {"format": "png", "width": w, "height": h}
        if head[:6] in (b"GIF87a", b"GIF89a") and len(head) >= 10:
            w, h = struct.unpack("<HH", head[6:10])
            return {"format": "gif", "width": w, "height": h}
        if head[:2] == b"BM" and len(head) >= 26:
            w, h = struct.unpack("<II", head[18:26])
            return {"format": "bmp", "width": w, "height": h}
        if head.startswith(b"gimp xcf") and len(head) >= 22:
            w, h = struct.unpack(">II", head[14:22])
            return {"format": "xcf", "width": w, "height": h}
        if head[:2] == b"\xff\xd8":
            fh.seek(2)
            while True:
                marker_start = fh.read(1)
                if not marker_start:
                    break
                if marker_start != b"\xff":
                    continue
                marker = fh.read(1)
                while marker == b"\xff":
                    marker = fh.read(1)
                if not marker or marker in (b"\xd8", b"\xd9"):
                    continue
                seg_len_bytes = fh.read(2)
                if len(seg_len_bytes) < 2:
                    break
                seg_len = struct.unpack(">H", seg_len_bytes)[0]
                if marker[0] in (0xC0, 0xC1, 0xC2):
                    sof = fh.read(5)
                    if len(sof) == 5:
                        h, w = struct.unpack(">HH", sof[1:5])
                        return {"format": "jpeg", "width": w, "height": h}
                    break
                fh.seek(max(0, seg_len - 2), 1)
    return {"format": path.suffix.lstrip(".").lower() or "unknown", "width": None, "height": None}


@server.tool("inspect_image")
def inspect_image(params: dict[str, Any]) -> dict[str, Any]:
    raw_path = params.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ConnectorError("'path' must be a non-empty string.", -32602)

    img = Path(raw_path).expanduser().resolve()
    if not img.is_file():
        raise ConnectorError(f"Image file does not exist: {img}", -32602)

    info = _probe_image_header(img)
    return {"path": str(img), "size_bytes": img.stat().st_size, **info}


@server.tool("run_script_fu")
def run_script_fu(params: dict[str, Any]) -> dict[str, Any]:
    expr = params.get("expression")
    if not isinstance(expr, str) or not expr.strip().startswith("("):
        raise ConnectorError("'expression' must be a non-empty Script-Fu S-expression starting with '('.", -32602)

    gimp = shutil.which("gimp")
    if not gimp:
        raise ConnectorError("GIMP is not installed on this system.", -32000)

    proc = subprocess.run(
        [gimp, "-i", "-b", expr.strip(), "-b", "(gimp-quit 0)"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if proc.returncode != 0:
        raise ConnectorError(proc.stderr.strip() or proc.stdout.strip() or "GIMP Script-Fu failed", -32000)

    return {"ok": True, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}


if __name__ == "__main__":
    server.run_stdio()
