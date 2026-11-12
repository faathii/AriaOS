#!/usr/bin/env python3
"""HandBrake, Shotcut, and Pitivi connector for AriaOS."""

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

server = ConnectorServer("creative-video-transcode", "0.1.0")
ALLOWED_APPS = {"shotcut", "pitivi", "ghb"}


@server.tool("inspect_video_project")
def inspect_video_project(params: dict[str, Any]) -> dict[str, Any]:
    raw_path = params.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ConnectorError("'path' must be a non-empty string.", -32602)

    proj = Path(raw_path).expanduser().resolve()
    if not proj.is_file() or proj.suffix.lower() not in {".mlt", ".xges"}:
        raise ConnectorError(f"Expected an existing .mlt or .xges project file: {proj}", -32602)

    try:
        root = ET.parse(proj).getroot()
    except ET.ParseError as exc:
        raise ConnectorError(f"Invalid project XML: {exc}", -32602) from exc

    if proj.suffix.lower() == ".mlt":
        profile = root.find("profile")
        sources = [
            prop.text.strip()
            for prod in root.findall("producer")
            for prop in prod.findall("property")
            if prop.attrib.get("name") == "resource" and prop.text
        ]
        return {
            "format": "shotcut-mlt",
            "profile": dict(profile.attrib) if profile is not None else {},
            "sources": sources[:50],
        }

    assets = [a.attrib.get("id", "") for a in root.findall(".//asset") if a.attrib.get("id")]
    return {
        "format": "pitivi-xges",
        "asset_count": len(assets),
        "assets": assets[:50],
    }


@server.tool("handbrake_transcode")
def handbrake_transcode(params: dict[str, Any]) -> dict[str, Any]:
    raw_in = params.get("input_path")
    raw_out = params.get("output_path")
    preset = params.get("preset", "Fast 1080p30")

    if not isinstance(raw_in, str) or not raw_in.strip():
        raise ConnectorError("'input_path' must be a non-empty string.", -32602)
    if not isinstance(raw_out, str) or not raw_out.strip():
        raise ConnectorError("'output_path' must be a non-empty string.", -32602)
    if not isinstance(preset, str) or not preset.strip():
        raise ConnectorError("'preset' must be a non-empty string.", -32602)

    src = Path(raw_in).expanduser().resolve()
    dst = Path(raw_out).expanduser().resolve()
    if not src.is_file():
        raise ConnectorError(f"Input file does not exist: {src}", -32602)
    if dst.exists():
        raise ConnectorError(f"Refusing to overwrite existing output: {dst}", -32602)

    cli = shutil.which("HandBrakeCLI")
    if not cli:
        raise ConnectorError("'HandBrakeCLI' is not installed on this system.", -32000)

    proc = subprocess.run(
        [cli, "-i", str(src), "-o", str(dst), "--preset", preset.strip()],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    if proc.returncode != 0:
        raise ConnectorError(proc.stderr.strip() or proc.stdout.strip() or "HandBrakeCLI failed", -32000)
    return {"input_path": str(src), "output_path": str(dst), "preset": preset.strip(), "exists": dst.is_file()}


@server.tool("launch_video_app")
def launch_video_app(params: dict[str, Any]) -> dict[str, Any]:
    app = params.get("app")
    proj = params.get("project_path")
    if not isinstance(app, str) or app not in ALLOWED_APPS:
        raise ConnectorError(f"'app' must be one of: {', '.join(sorted(ALLOWED_APPS))}", -32602)

    cmd_args: list[str] = []
    if proj is not None:
        if not isinstance(proj, str) or not proj.strip():
            raise ConnectorError("'project_path' must be a non-empty string.", -32602)
        p = Path(proj).expanduser().resolve()
        if not p.is_file():
            raise ConnectorError(f"Project file does not exist: {p}", -32602)
        cmd_args.append(str(p))

    binary = shutil.which(app)
    if not binary:
        raise ConnectorError(f"'{app}' is not installed on this system.", -32000)

    proc = subprocess.Popen([binary, *cmd_args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return {"launched": True, "app": app, "pid": proc.pid}


if __name__ == "__main__":
    server.run_stdio()
