#!/usr/bin/env python3
"""LibreOffice connector for AriaOS (ODF/OOXML inspection, headless conversion, UNO probe)."""

from __future__ import annotations

import shutil
import socket
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

server = ConnectorServer("office-libreoffice", "0.1.0")

SUPPORTED_DOC_EXTS = {".odt", ".ods", ".odp", ".docx", ".xlsx", ".pptx"}
SUPPORTED_OUT_FORMATS = {"pdf", "docx", "odt", "xlsx", "ods", "pptx", "odp", "txt", "html", "csv"}


def _find_soffice() -> str:
    binary = shutil.which("soffice") or shutil.which("libreoffice")
    if not binary:
        raise ConnectorError("LibreOffice binary (soffice) is not installed on this system.", -32000)
    return binary


def _extract_xml_text(raw_xml: bytes) -> str:
    root = ET.fromstring(raw_xml)
    chunks = [text.strip() for text in root.itertext() if text and text.strip()]
    return "\n".join(chunks)


@server.tool("inspect_document")
def inspect_document(params: dict[str, Any]) -> dict[str, Any]:
    raw_path = params.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ConnectorError("'path' must be a non-empty string.", -32602)

    max_chars = params.get("max_chars", 4000)
    if not isinstance(max_chars, int) or max_chars < 100 or max_chars > 20000:
        raise ConnectorError("'max_chars' must be an integer between 100 and 20000.", -32602)

    doc_path = Path(raw_path).expanduser().resolve()
    if not doc_path.is_file():
        raise ConnectorError(f"Document does not exist: {doc_path}", -32602)

    ext = doc_path.suffix.lower()
    if ext not in SUPPORTED_DOC_EXTS:
        raise ConnectorError(
            f"Unsupported extension '{ext}'. Supported: {', '.join(sorted(SUPPORTED_DOC_EXTS))}",
            -32602,
        )

    try:
        with zipfile.ZipFile(doc_path, "r") as zf:
            names = set(zf.namelist())
            parts: list[str] = []
            if ext in {".odt", ".ods", ".odp"} and "content.xml" in names:
                parts.append(_extract_xml_text(zf.read("content.xml")))
            elif ext == ".docx" and "word/document.xml" in names:
                parts.append(_extract_xml_text(zf.read("word/document.xml")))
            elif ext == ".xlsx":
                for name in sorted(names):
                    if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"):
                        parts.append(f"[{name}]\n{_extract_xml_text(zf.read(name))}")
                    elif name == "xl/sharedStrings.xml":
                        parts.append(f"[sharedStrings]\n{_extract_xml_text(zf.read(name))}")
            elif ext == ".pptx":
                slides = [n for n in sorted(names) if n.startswith("ppt/slides/slide") and n.endswith(".xml")]
                for slide in slides:
                    parts.append(f"[{slide}]\n{_extract_xml_text(zf.read(slide))}")
            text = "\n\n".join(parts)
    except zipfile.BadZipFile as exc:
        raise ConnectorError(f"Invalid document archive: {exc}", -32602) from exc
    except ET.ParseError as exc:
        raise ConnectorError(f"Failed to parse document XML: {exc}", -32000) from exc

    truncated = len(text) > max_chars
    return {
        "path": str(doc_path),
        "format": ext.lstrip("."),
        "size_bytes": doc_path.stat().st_size,
        "truncated": truncated,
        "text_preview": text[:max_chars],
    }


@server.tool("convert_document")
def convert_document(params: dict[str, Any]) -> dict[str, Any]:
    raw_input = params.get("input_path")
    target_format = params.get("target_format")
    raw_out_dir = params.get("output_dir")

    if not isinstance(raw_input, str) or not raw_input.strip():
        raise ConnectorError("'input_path' must be a non-empty string.", -32602)
    if not isinstance(target_format, str) or target_format not in SUPPORTED_OUT_FORMATS:
        raise ConnectorError(
            f"'target_format' must be one of: {', '.join(sorted(SUPPORTED_OUT_FORMATS))}",
            -32602,
        )

    src = Path(raw_input).expanduser().resolve()
    if not src.is_file():
        raise ConnectorError(f"Input file does not exist: {src}", -32602)

    out_dir = Path(raw_out_dir).expanduser().resolve() if raw_out_dir else src.parent
    if not out_dir.is_dir():
        raise ConnectorError(f"Output directory does not exist: {out_dir}", -32602)

    expected_out = out_dir / f"{src.stem}.{target_format}"
    if expected_out.exists():
        raise ConnectorError(f"Refusing to overwrite existing output file: {expected_out}", -32602)

    soffice = _find_soffice()
    cmd = [soffice, "--headless", "--convert-to", target_format, "--outdir", str(out_dir), str(src)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
    if proc.returncode != 0:
        raise ConnectorError(proc.stderr.strip() or proc.stdout.strip() or "LibreOffice conversion failed", -32000)

    return {
        "input_path": str(src),
        "output_path": str(expected_out),
        "target_format": target_format,
        "exists": expected_out.is_file(),
    }


@server.tool("uno_status")
def uno_status(params: dict[str, Any]) -> dict[str, Any]:
    host = params.get("host", "127.0.0.1")
    port = params.get("port", 2002)
    if not isinstance(host, str) or not host.strip():
        raise ConnectorError("'host' must be a non-empty string.", -32602)
    if not isinstance(port, int) or port < 1 or port > 65535:
        raise ConnectorError("'port' must be an integer between 1 and 65535.", -32602)

    reachable = False
    try:
        with socket.create_connection((host.strip(), port), timeout=1.0):
            reachable = True
    except OSError:
        reachable = False

    return {
        "host": host.strip(),
        "port": port,
        "uno_reachable": reachable,
        "soffice_installed": bool(shutil.which("soffice") or shutil.which("libreoffice")),
    }


if __name__ == "__main__":
    server.run_stdio()
