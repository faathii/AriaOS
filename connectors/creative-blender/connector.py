#!/usr/bin/env python3
"""Blender connector for AriaOS (background bpy inspection + headless render)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

server = ConnectorServer("creative-blender", "0.1.0")

INSPECT_PY = (
    "import bpy, json; "
    "s = bpy.context.scene; "
    "print('ARIA_BLEND_JSON:' + json.dumps({"
    "'scene': s.name, "
    "'engine': s.render.engine, "
    "'resolution_x': s.render.resolution_x, "
    "'resolution_y': s.render.resolution_y, "
    "'frame_start': s.frame_start, "
    "'frame_end': s.frame_end, "
    "'objects': [o.name for o in bpy.data.objects[:100]]"
    "}))"
)


def _validate_blend(raw_path: Any) -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ConnectorError("'path' must be a non-empty string.", -32602)
    blend = Path(raw_path).expanduser().resolve()
    if not blend.is_file() or blend.suffix.lower() != ".blend":
        raise ConnectorError(f"Expected an existing .blend file: {blend}", -32602)
    return blend


@server.tool("inspect_blend_scene")
def inspect_blend_scene(params: dict[str, Any]) -> dict[str, Any]:
    blend = _validate_blend(params.get("path"))
    blender = shutil.which("blender")
    if not blender:
        raise ConnectorError("Blender is not installed on this system.", -32000)

    proc = subprocess.run(
        [blender, "-b", str(blend), "--python-expr", INSPECT_PY],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if proc.returncode != 0:
        raise ConnectorError(proc.stderr.strip() or "Blender inspection failed", -32000)

    for line in proc.stdout.splitlines():
        if line.startswith("ARIA_BLEND_JSON:"):
            return {"path": str(blend), **json.loads(line.split(":", 1)[1])}

    raise ConnectorError("Did not receive scene metadata from Blender.", -32000)


@server.tool("render_frame")
def render_frame(params: dict[str, Any]) -> dict[str, Any]:
    blend = _validate_blend(params.get("blend_path"))
    raw_out = params.get("output_prefix")
    frame = params.get("frame", 1)

    if not isinstance(raw_out, str) or not raw_out.strip():
        raise ConnectorError("'output_prefix' must be a non-empty string.", -32602)
    if not isinstance(frame, int) or frame < 0:
        raise ConnectorError("'frame' must be an integer >= 0.", -32602)

    out_prefix = Path(raw_out).expanduser().resolve()
    if not out_prefix.parent.is_dir():
        raise ConnectorError(f"Output parent directory does not exist: {out_prefix.parent}", -32602)
    if list(out_prefix.parent.glob(f"{out_prefix.name}*")):
        raise ConnectorError(f"Refusing to overwrite existing output matching: {out_prefix}*", -32602)

    blender = shutil.which("blender")
    if not blender:
        raise ConnectorError("Blender is not installed on this system.", -32000)

    proc = subprocess.run(
        [blender, "-b", str(blend), "-o", str(out_prefix), "-f", str(frame)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if proc.returncode != 0:
        raise ConnectorError(proc.stderr.strip() or "Blender render failed", -32000)

    return {"blend_path": str(blend), "output_prefix": str(out_prefix), "frame": frame, "ok": True}


if __name__ == "__main__":
    server.run_stdio()
