#!/usr/bin/env python3
"""Okular connector for AriaOS (Poppler inspection/extraction + Okular CLI/D-Bus)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

server = ConnectorServer("office-okular", "0.1.0")
SUPPORTED_DOC_EXTS = {".pdf", ".epub", ".djvu", ".cbz", ".cbr", ".md", ".txt"}


def _validate_existing_file(raw_path: Any, expected_exts: set[str] | None = None) -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ConnectorError("'path' must be a non-empty string.", -32602)
    doc = Path(raw_path).expanduser().resolve()
    if not doc.is_file():
        raise ConnectorError(f"File does not exist: {doc}", -32602)
    if expected_exts and doc.suffix.lower() not in expected_exts:
        raise ConnectorError(f"Unsupported extension '{doc.suffix}'.", -32602)
    return doc


@server.tool("inspect_pdf")
def inspect_pdf(params: dict[str, Any]) -> dict[str, Any]:
    pdf_path = _validate_existing_file(params.get("path"), {".pdf"})
    pdfinfo = shutil.which("pdfinfo")
    if not pdfinfo:
        raise ConnectorError("'pdfinfo' (poppler) is not installed on this system.", -32000)

    proc = subprocess.run([pdfinfo, str(pdf_path)], capture_output=True, text=True, timeout=15, check=False)
    if proc.returncode != 0:
        raise ConnectorError(proc.stderr.strip() or "pdfinfo failed", -32000)

    metadata: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            metadata[key.strip()] = val.strip()

    pages_raw = metadata.get("Pages")
    pages = int(pages_raw) if pages_raw and pages_raw.isdigit() else None
    return {
        "path": str(pdf_path),
        "size_bytes": pdf_path.stat().st_size,
        "pages": pages,
        "metadata": metadata,
    }


@server.tool("extract_pdf_text")
def extract_pdf_text(params: dict[str, Any]) -> dict[str, Any]:
    pdf_path = _validate_existing_file(params.get("path"), {".pdf"})
    first_page = params.get("first_page", 1)
    last_page = params.get("last_page", 5)
    max_chars = params.get("max_chars", 6000)

    if not isinstance(first_page, int) or first_page < 1:
        raise ConnectorError("'first_page' must be an integer >= 1.", -32602)
    if not isinstance(last_page, int) or last_page < first_page:
        raise ConnectorError("'last_page' must be >= 'first_page'.", -32602)
    if not isinstance(max_chars, int) or max_chars < 100 or max_chars > 20000:
        raise ConnectorError("'max_chars' must be between 100 and 20000.", -32602)

    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        raise ConnectorError("'pdftotext' (poppler) is not installed on this system.", -32000)

    cmd = [pdftotext, "-f", str(first_page), "-l", str(last_page), str(pdf_path), "-"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    if proc.returncode != 0:
        raise ConnectorError(proc.stderr.strip() or "pdftotext failed", -32000)

    text = proc.stdout
    return {
        "path": str(pdf_path),
        "first_page": first_page,
        "last_page": last_page,
        "truncated": len(text) > max_chars,
        "text": text[:max_chars],
    }


@server.tool("open_document")
def open_document(params: dict[str, Any]) -> dict[str, Any]:
    doc_path = _validate_existing_file(params.get("path"), SUPPORTED_DOC_EXTS)
    page = params.get("page")
    if page is not None and (not isinstance(page, int) or page < 1):
        raise ConnectorError("'page' must be an integer >= 1.", -32602)

    okular = shutil.which("okular")
    if not okular:
        raise ConnectorError("Okular is not installed on this system.", -32000)

    cmd = [okular]
    if page is not None:
        cmd.extend(["-p", str(page)])
    cmd.append(str(doc_path))

    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return {
        "launched": True,
        "pid": proc.pid,
        "path": str(doc_path),
        "page": page,
    }


if __name__ == "__main__":
    server.run_stdio()
