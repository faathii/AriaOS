#!/usr/bin/env python3
"""Inkscape, Darktable, and RawTherapee connector for AriaOS."""

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

server = ConnectorServer("creative-design-photo", "0.1.0")
ALLOWED_INKSCAPE_EXTS = {".png", ".pdf", ".eps", ".svg"}


def _validate_io(params: dict[str, Any]) -> tuple[Path, Path]:
    raw_in = params.get("input_path")
    raw_out = params.get("output_path")
    if not isinstance(raw_in, str) or not raw_in.strip():
        raise ConnectorError("'input_path' must be a non-empty string.", -32602)
    if not isinstance(raw_out, str) or not raw_out.strip():
        raise ConnectorError("'output_path' must be a non-empty string.", -32602)

    src = Path(raw_in).expanduser().resolve()
    dst = Path(raw_out).expanduser().resolve()
    if not src.is_file():
        raise ConnectorError(f"Input file does not exist: {src}", -32602)
    if dst.exists():
        raise ConnectorError(f"Refusing to overwrite existing output: {dst}", -32602)
    if not dst.parent.is_dir():
        raise ConnectorError(f"Output directory does not exist: {dst.parent}", -32602)
    return src, dst


@server.tool("inspect_svg")
def inspect_svg(params: dict[str, Any]) -> dict[str, Any]:
    raw_path = params.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ConnectorError("'path' must be a non-empty string.", -32602)

    svg = Path(raw_path).expanduser().resolve()
    if not svg.is_file() or svg.suffix.lower() != ".svg":
        raise ConnectorError(f"Expected an existing .svg file: {svg}", -32602)

    try:
        root = ET.parse(svg).getroot()
    except ET.ParseError as exc:
        raise ConnectorError(f"Invalid SVG XML: {exc}", -32602) from exc

    layers: list[dict[str, str]] = []
    for elem in root.iter():
        if elem.tag.endswith("}g") or elem.tag == "g":
            label = elem.attrib.get("{http://www.inkscape.org/namespaces/inkscape}label")
            if label:
                layers.append({"id": elem.attrib.get("id", ""), "label": label})

    return {
        "path": str(svg),
        "width": root.attrib.get("width"),
        "height": root.attrib.get("height"),
        "viewBox": root.attrib.get("viewBox"),
        "layers": layers,
    }


@server.tool("inkscape_export")
def inkscape_export(params: dict[str, Any]) -> dict[str, Any]:
    src, dst = _validate_io(params)
    dpi = params.get("dpi", 150)
    if dst.suffix.lower() not in ALLOWED_INKSCAPE_EXTS:
        raise ConnectorError(f"Unsupported output extension '{dst.suffix}'.", -32602)
    if not isinstance(dpi, int) or dpi < 36 or dpi > 1200:
        raise ConnectorError("'dpi' must be between 36 and 1200.", -32602)

    binary = shutil.which("inkscape")
    if not binary:
        raise ConnectorError("Inkscape is not installed on this system.", -32000)

    proc = subprocess.run(
        [binary, f"--export-filename={dst}", f"--export-dpi={dpi}", str(src)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if proc.returncode != 0:
        raise ConnectorError(proc.stderr.strip() or proc.stdout.strip() or "Inkscape export failed", -32000)
    return {"input_path": str(src), "output_path": str(dst), "dpi": dpi, "exists": dst.is_file()}


@server.tool("darktable_export")
def darktable_export(params: dict[str, Any]) -> dict[str, Any]:
    src, dst = _validate_io(params)
    binary = shutil.which("darktable-cli")
    if not binary:
        raise ConnectorError("'darktable-cli' is not installed on this system.", -32000)

    proc = subprocess.run([binary, str(src), str(dst)], capture_output=True, text=True, timeout=120, check=False)
    if proc.returncode != 0:
        raise ConnectorError(proc.stderr.strip() or proc.stdout.strip() or "darktable-cli failed", -32000)
    return {"input_path": str(src), "output_path": str(dst), "exists": dst.is_file()}


@server.tool("rawtherapee_export")
def rawtherapee_export(params: dict[str, Any]) -> dict[str, Any]:
    src, dst = _validate_io(params)
    binary = shutil.which("rawtherapee-cli")
    if not binary:
        raise ConnectorError("'rawtherapee-cli' is not installed on this system.", -32000)

    proc = subprocess.run([binary, "-o", str(dst), "-c", str(src)], capture_output=True, text=True, timeout=120, check=False)
    if proc.returncode != 0:
        raise ConnectorError(proc.stderr.strip() or proc.stdout.strip() or "rawtherapee-cli failed", -32000)
    return {"input_path": str(src), "output_path": str(dst), "exists": dst.is_file()}


if __name__ == "__main__":
    server.run_stdio()
