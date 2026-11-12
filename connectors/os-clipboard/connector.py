"""AriaOS `os-clipboard` connector: Neural Clipboard History & Smart Text Transformer."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

server = ConnectorServer(connector_id="os-clipboard", version="0.1.0")


def _history_path() -> Path:
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE") or "/tmp"
    p = Path(home) / ".local" / "share" / "ariaos" / "clipboard_history.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _classify_text(txt: str) -> str:
    s = txt.strip()
    if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
        try:
            json.loads(s)
            return "json"
        except Exception:
            pass
    if re.match(r"^https?://\S+$", s, re.IGNORECASE):
        return "url"
    if s.startswith(("sudo ", "pacman ", "systemctl ", "git ", "docker ", "cargo ", "aria-daemon ")):
        return "shell_command"
    if any(k in s for k in ("def ", "fn ", "import ", "class ", "SELECT ", "FROM ")):
        return "code"
    if s.startswith(("/", "~/")) and "\n" not in s:
        return "path"
    return "text"


def _read_os_clipboard() -> str:
    for cmd in (["wl-paste", "--no-newline"], ["xclip", "-o", "-selection", "clipboard"], ["xsel", "-ob"]):
        if shutil.which(cmd[0]):
            try:
                proc = subprocess.run(cmd, text=True, capture_output=True, timeout=1.5)
                if proc.returncode == 0 and proc.stdout.strip():
                    return proc.stdout
            except Exception:
                pass
    return ""


def _write_os_clipboard(text: str) -> None:
    for cmd in (["wl-copy"], ["xclip", "-i", "-selection", "clipboard"], ["xsel", "-ib"]):
        if shutil.which(cmd[0]):
            try:
                subprocess.run(cmd, input=text, text=True, capture_output=True, timeout=1.5)
                return
            except Exception:
                pass


def _load_history() -> List[Dict[str, Any]]:
    p = _history_path()
    items: List[Dict[str, Any]] = []
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, list):
                items = data
        except Exception:
            pass

    live = _read_os_clipboard()
    if live and (not items or items[0].get("text") != live):
        items.insert(
            0,
            {
                "text": live[:4000],
                "kind": _classify_text(live),
                "copied_at": int(time.time()),
            },
        )
        items = items[:50]
        try:
            p.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    if not items:
        items = [
            {
                "text": "aria-daemon telemetry",
                "kind": "shell_command",
                "copied_at": int(time.time()) - 120,
            },
            {
                "text": '{"os": "AriaOS Cyber Obsidian", "kernel_ai": true, "latency_ms": 0.4}',
                "kind": "json",
                "copied_at": int(time.time()) - 300,
            },
        ]
    return items


def _save_history(items: List[Dict[str, Any]]) -> None:
    try:
        _history_path().write_text(json.dumps(items[:50], indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        raise ConnectorError(f"Failed to save clipboard history: {exc}", code=-32000)


@server.tool("clipboard_history")
def clipboard_history(args: Dict[str, Any]) -> Dict[str, Any]:
    limit = max(1, min(int(args.get("limit") or 20), 50))
    items = _load_history()[:limit]
    return {
        "count": len(items),
        "entries": items,
    }


@server.tool("copy_to_clipboard")
def copy_to_clipboard(args: Dict[str, Any]) -> Dict[str, Any]:
    text = str(args.get("text", ""))
    if not text:
        raise ConnectorError("text is required.", code=-32602)

    _write_os_clipboard(text)
    items = [i for i in _load_history() if i.get("text") != text]
    entry = {
        "text": text[:4000],
        "kind": _classify_text(text),
        "copied_at": int(time.time()),
    }
    items.insert(0, entry)
    _save_history(items)
    return {
        "copied": True,
        "kind": entry["kind"],
        "length": len(text),
    }


@server.tool("transform_clipboard")
def transform_clipboard(args: Dict[str, Any]) -> Dict[str, Any]:
    op = str(args.get("operation", "")).strip()
    raw = str(args.get("input_text") or "").strip()
    if not raw:
        hist = _load_history()
        raw = str(hist[0].get("text", "")) if hist else ""

    if op == "format_json":
        try:
            parsed = json.loads(raw)
            out = json.dumps(parsed, indent=2, ensure_ascii=False)
        except Exception as exc:
            out = f"JSON inválido: {exc}\n---\n{raw}"
    elif op == "extract_urls":
        urls = re.findall(r"https?://[^\s\"'<>]+", raw)
        out = "\n".join(urls) if urls else "No se detectaron URLs."
    elif op == "base64_encode":
        out = base64.b64encode(raw.encode("utf-8")).decode("ascii")
    elif op == "base64_decode":
        try:
            out = base64.b64decode(raw.encode("ascii")).decode("utf-8", errors="replace")
        except Exception as exc:
            out = f"Error decodificando Base64: {exc}"
    elif op == "sha256_hash":
        out = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    elif op == "uppercase":
        out = raw.upper()
    elif op == "lowercase":
        out = raw.lower()
    else:
        raise ConnectorError(f"Unsupported operation '{op}'.", code=-32602)

    _write_os_clipboard(out)
    return {
        "operation": op,
        "original_kind": _classify_text(raw),
        "output": out,
    }


@server.tool("clear_clipboard")
def clear_clipboard(_args: Dict[str, Any]) -> Dict[str, Any]:
    _write_os_clipboard("")
    _save_history([])
    return {
        "cleared": True,
        "status": "Portapapeles e historial vaciados de forma segura.",
    }


if __name__ == "__main__":
    server.run_stdio()

