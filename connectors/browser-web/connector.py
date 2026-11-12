#!/usr/bin/env python3
"""Web browser connector for AriaOS (Brave CDP / Firefox / Bookmarks JSON)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

server = ConnectorServer("browser-web", "0.1.0")
ALLOWED_BROWSERS = {"auto", "brave", "firefox"}


def _validate_port(port: Any) -> int:
    if not isinstance(port, int) or port < 1024 or port > 65535:
        raise ConnectorError("'cdp_port' must be an integer between 1024 and 65535.", -32602)
    return port


def _validate_url(raw_url: Any) -> str:
    if not isinstance(raw_url, str) or not raw_url.strip():
        raise ConnectorError("'url' must be a non-empty string.", -32602)
    parsed = urllib.parse.urlparse(raw_url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConnectorError("Only valid http:// or https:// URLs are allowed.", -32602)
    return raw_url.strip()


@server.tool("list_tabs")
def list_tabs(params: dict[str, Any]) -> dict[str, Any]:
    port = _validate_port(params.get("cdp_port", 9222))
    endpoint = f"http://127.0.0.1:{port}/json/list"
    try:
        with urllib.request.urlopen(endpoint, timeout=2.0) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ConnectorError(
            f"Brave/Chromium CDP endpoint not reachable on port {port} (launch browser with --remote-debugging-port={port}): {exc}",
            -32000,
        ) from exc

    tabs = [
        {
            "id": item.get("id"),
            "title": item.get("title"),
            "url": item.get("url"),
            "type": item.get("type"),
        }
        for item in payload
        if isinstance(item, dict) and item.get("type") == "page"
    ]
    return {"cdp_port": port, "tab_count": len(tabs), "tabs": tabs}


@server.tool("search_bookmarks")
def search_bookmarks(params: dict[str, Any]) -> dict[str, Any]:
    query = params.get("query")
    if not isinstance(query, str) or not query.strip():
        raise ConnectorError("'query' must be a non-empty string.", -32602)

    limit = params.get("limit", 25)
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ConnectorError("'limit' must be an integer between 1 and 100.", -32602)

    custom_path = params.get("bookmarks_path")
    if custom_path is not None:
        if not isinstance(custom_path, str) or not custom_path.strip():
            raise ConnectorError("'bookmarks_path' must be a non-empty string.", -32602)
        bm_path = Path(custom_path).expanduser().resolve()
    else:
        bm_path = Path.home() / ".config" / "BraveSoftware" / "Brave-Browser" / "Default" / "Bookmarks"

    if not bm_path.is_file():
        raise ConnectorError(f"Bookmarks file not found: {bm_path}", -32000)

    try:
        data = json.loads(bm_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConnectorError(f"Failed to read bookmarks JSON: {exc}", -32000) from exc

    needle = query.strip().lower()
    matches: list[dict[str, str]] = []

    def walk(node: Any, folder: str) -> None:
        if len(matches) >= limit or not isinstance(node, dict):
            return
        node_type = node.get("type")
        if node_type == "url":
            name = str(node.get("name", ""))
            url = str(node.get("url", ""))
            if needle in name.lower() or needle in url.lower():
                matches.append({"folder": folder, "name": name, "url": url})
        for child in node.get("children", []):
            next_folder = f"{folder}/{node.get('name', '')}".strip("/") if node_type == "folder" else folder
            walk(child, next_folder)

    roots = data.get("roots", {})
    if isinstance(roots, dict):
        for root_name, root_node in roots.items():
            walk(root_node, root_name)

    return {"query": query.strip(), "bookmarks_path": str(bm_path), "matches": matches}


@server.tool("open_url")
def open_url(params: dict[str, Any]) -> dict[str, Any]:
    url = _validate_url(params.get("url"))
    browser = params.get("browser", "auto")
    port = _validate_port(params.get("cdp_port", 9222))

    if not isinstance(browser, str) or browser not in ALLOWED_BROWSERS:
        raise ConnectorError(f"'browser' must be one of: {', '.join(sorted(ALLOWED_BROWSERS))}", -32602)

    if browser in {"auto", "brave"}:
        cdp_new = f"http://127.0.0.1:{port}/json/new?{urllib.parse.quote(url, safe=':/?=&')}"
        try:
            req = urllib.request.Request(cdp_new, method="PUT")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                info = json.loads(resp.read().decode("utf-8"))
                return {"opened_via": "cdp", "url": url, "tab_id": info.get("id")}
        except Exception:
            pass

    candidates = (
        ["brave", "brave-browser"]
        if browser == "brave"
        else ["firefox"]
        if browser == "firefox"
        else ["brave", "brave-browser", "firefox", "xdg-open"]
    )
    binary = next((shutil.which(name) for name in candidates if shutil.which(name)), None)
    if not binary:
        raise ConnectorError(f"No supported browser binary found among: {', '.join(candidates)}", -32000)

    proc = subprocess.Popen([binary, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return {"opened_via": Path(binary).name, "pid": proc.pid, "url": url}


if __name__ == "__main__":
    server.run_stdio()
