#!/usr/bin/env python3
"""Obsidian & Calibre connector for AriaOS."""

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

server = ConnectorServer("knowledge-notes-ebooks", "0.1.0")


@server.tool("search_obsidian_vault")
def search_obsidian_vault(params: dict[str, Any]) -> dict[str, Any]:
    raw_vault = params.get("vault_dir")
    query = params.get("query")
    limit = params.get("limit", 25)

    if not isinstance(raw_vault, str) or not raw_vault.strip():
        raise ConnectorError("'vault_dir' must be a non-empty string.", -32602)
    if not isinstance(query, str) or not query.strip():
        raise ConnectorError("'query' must be a non-empty string.", -32602)
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ConnectorError("'limit' must be between 1 and 100.", -32602)

    vault = Path(raw_vault).expanduser().resolve()
    if not vault.is_dir():
        raise ConnectorError(f"Vault directory does not exist: {vault}", -32602)

    needle = query.strip().lower()
    matches: list[dict[str, str]] = []
    for md in sorted(vault.rglob("*.md")):
        if ".obsidian" in md.parts:
            continue
        rel = str(md.relative_to(vault))
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if needle in rel.lower() or needle in text.lower():
            matches.append({"note": rel, "preview": text[:240].strip()})
            if len(matches) >= limit:
                break

    return {"vault_dir": str(vault), "query": query.strip(), "count": len(matches), "matches": matches}


@server.tool("create_obsidian_note")
def create_obsidian_note(params: dict[str, Any]) -> dict[str, Any]:
    raw_vault = params.get("vault_dir")
    rel_raw = params.get("relative_path")
    content = params.get("content")

    if not isinstance(raw_vault, str) or not raw_vault.strip():
        raise ConnectorError("'vault_dir' must be a non-empty string.", -32602)
    if not isinstance(rel_raw, str) or not rel_raw.strip().endswith(".md"):
        raise ConnectorError("'relative_path' must be a relative path ending in .md.", -32602)
    if not isinstance(content, str):
        raise ConnectorError("'content' must be a string.", -32602)

    vault = Path(raw_vault).expanduser().resolve()
    if not vault.is_dir():
        raise ConnectorError(f"Vault directory does not exist: {vault}", -32602)

    target = (vault / rel_raw.strip()).resolve()
    if vault not in target.parents:
        raise ConnectorError("'relative_path' escapes the Obsidian vault directory.", -32602)
    if target.exists():
        raise ConnectorError(f"Refusing to overwrite existing note: {target}", -32602)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"created": True, "path": str(target), "size_bytes": target.stat().st_size}


@server.tool("calibre_list_books")
def calibre_list_books(params: dict[str, Any]) -> dict[str, Any]:
    limit = params.get("limit", 25)
    search = params.get("search")
    raw_lib = params.get("library_dir")
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ConnectorError("'limit' must be between 1 and 100.", -32602)

    cli = shutil.which("calibredb")
    if not cli:
        raise ConnectorError("'calibredb' (Calibre) is not installed on this system.", -32000)

    cmd = [cli, "list", "--for-machine", "--fields", "id,title,authors,formats", "--limit", str(limit)]
    if isinstance(raw_lib, str) and raw_lib.strip():
        cmd.extend(["--with-library", str(Path(raw_lib).expanduser().resolve())])
    if isinstance(search, str) and search.strip():
        cmd.extend(["--search", search.strip()])

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
    if proc.returncode != 0:
        raise ConnectorError(proc.stderr.strip() or proc.stdout.strip() or "calibredb list failed", -32000)

    books = json.loads(proc.stdout or "[]")
    return {"count": len(books), "books": books}


@server.tool("calibre_convert_ebook")
def calibre_convert_ebook(params: dict[str, Any]) -> dict[str, Any]:
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

    cli = shutil.which("ebook-convert")
    if not cli:
        raise ConnectorError("'ebook-convert' (Calibre) is not installed on this system.", -32000)

    proc = subprocess.run([cli, str(src), str(dst)], capture_output=True, text=True, timeout=180, check=False)
    if proc.returncode != 0:
        raise ConnectorError(proc.stderr.strip() or proc.stdout.strip() or "ebook-convert failed", -32000)
    return {"input_path": str(src), "output_path": str(dst), "exists": dst.is_file()}


if __name__ == "__main__":
    server.run_stdio()
