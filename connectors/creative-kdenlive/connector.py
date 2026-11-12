#!/usr/bin/env python3
"""Kdenlive & MLT connector for AriaOS (.kdenlive XML inspection + melt CLI)."""

from __future__ import annotations

import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

server = ConnectorServer("creative-kdenlive", "0.1.0")


@server.tool("inspect_project")
def inspect_project(params: dict[str, Any]) -> dict[str, Any]:
    raw_path = params.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ConnectorError("'path' must be a non-empty string.", -32602)

    proj = Path(raw_path).expanduser().resolve()
    if not proj.is_file() or proj.suffix.lower() != ".kdenlive":
        raise ConnectorError(f"Expected an existing .kdenlive file: {proj}", -32602)

    try:
        root = ET.parse(proj).getroot()
    except ET.ParseError as exc:
        raise ConnectorError(f"Invalid .kdenlive XML: {exc}", -32602) from exc

    profile = root.find("profile")
    playlists = root.findall("playlist")
    sources: list[str] = []
    for producer in root.findall("producer"):
        for prop in producer.findall("property"):
            if prop.attrib.get("name") == "resource" and prop.text:
                sources.append(prop.text.strip())

    return {
        "path": str(proj),
        "profile": dict(profile.attrib) if profile is not None else {},
        "track_count": len(playlists),
        "source_count": len(sources),
        "sources": sources[:50],
    }


@server.tool("render_project")
def render_project(params: dict[str, Any]) -> dict[str, Any]:
    raw_proj = params.get("project_path")
    raw_out = params.get("output_path")
    if not isinstance(raw_proj, str) or not raw_proj.strip():
        raise ConnectorError("'project_path' must be a non-empty string.", -32602)
    if not isinstance(raw_out, str) or not raw_out.strip():
        raise ConnectorError("'output_path' must be a non-empty string.", -32602)

    proj = Path(raw_proj).expanduser().resolve()
    out = Path(raw_out).expanduser().resolve()
    if not proj.is_file() or proj.suffix.lower() != ".kdenlive":
        raise ConnectorError(f"Expected an existing .kdenlive file: {proj}", -32602)
    if out.exists():
        raise ConnectorError(f"Refusing to overwrite existing output file: {out}", -32602)

    melt = shutil.which("melt")
    if not melt:
        raise ConnectorError("'melt' (MLT) is not installed on this system.", -32000)

    proc = subprocess.run(
        [melt, str(proj), "-consumer", f"avformat:{out}"],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    if proc.returncode != 0:
        raise ConnectorError(proc.stderr.strip() or proc.stdout.strip() or "MLT render failed", -32000)

    return {"project_path": str(proj), "output_path": str(out), "exists": out.is_file()}


if __name__ == "__main__":
    server.run_stdio()
