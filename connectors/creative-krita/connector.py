#!/usr/bin/env python3
"""Krita connector for AriaOS (.kra XML inspection + headless export CLI)."""

from __future__ import annotations

import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

server = ConnectorServer("creative-krita", "0.1.0")


@server.tool("inspect_krita_doc")
def inspect_krita_doc(params: dict[str, Any]) -> dict[str, Any]:
    raw_path = params.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ConnectorError("'path' must be a non-empty string.", -32602)

    kra = Path(raw_path).expanduser().resolve()
    if not kra.is_file() or kra.suffix.lower() != ".kra":
        raise ConnectorError(f"Expected an existing .kra file: {kra}", -32602)

    try:
        with zipfile.ZipFile(kra, "r") as zf:
            if "maindoc.xml" not in zf.namelist():
                raise ConnectorError("Missing maindoc.xml inside .kra archive.", -32602)
            root = ET.fromstring(zf.read("maindoc.xml"))
    except zipfile.BadZipFile as exc:
        raise ConnectorError(f"Invalid .kra zip archive: {exc}", -32602) from exc
    except ET.ParseError as exc:
        raise ConnectorError(f"Invalid maindoc.xml inside .kra: {exc}", -32602) from exc

    img = root.find(".//IMAGE")
    layers = [
        {
            "name": layer.attrib.get("name", ""),
            "nodetype": layer.attrib.get("nodetype", ""),
            "visible": layer.attrib.get("visible", "1") == "1",
            "opacity": layer.attrib.get("opacity", "255"),
        }
        for layer in root.findall(".//layer")
    ]
    return {
        "path": str(kra),
        "width": int(img.attrib["width"]) if img is not None and "width" in img.attrib else None,
        "height": int(img.attrib["height"]) if img is not None and "height" in img.attrib else None,
        "colorspacename": img.attrib.get("colorspacename") if img is not None else None,
        "layer_count": len(layers),
        "layers": layers,
    }


@server.tool("export_krita")
def export_krita(params: dict[str, Any]) -> dict[str, Any]:
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
        raise ConnectorError(f"Refusing to overwrite existing output file: {dst}", -32602)

    krita = shutil.which("krita")
    if not krita:
        raise ConnectorError("Krita is not installed on this system.", -32000)

    proc = subprocess.run(
        [krita, "--export", "--export-filename", str(dst), str(src)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if proc.returncode != 0:
        raise ConnectorError(proc.stderr.strip() or proc.stdout.strip() or "Krita export failed", -32000)

    return {"input_path": str(src), "output_path": str(dst), "exists": dst.is_file()}


if __name__ == "__main__":
    server.run_stdio()
