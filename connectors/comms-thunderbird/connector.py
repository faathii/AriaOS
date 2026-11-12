#!/usr/bin/env python3
"""Thunderbird connector for AriaOS (profiles.ini, SQLite Gloda read-only, CLI compose)."""

from __future__ import annotations

import configparser
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

server = ConnectorServer("comms-thunderbird", "0.1.0")
EMAIL_RE = re.compile(r"^[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+$")


def _default_tb_dir(override: Any = None) -> Path:
    if override is not None:
        if not isinstance(override, str) or not override.strip():
            raise ConnectorError("'thunderbird_dir' must be a non-empty string.", -32602)
        return Path(override).expanduser().resolve()
    return Path.home() / ".thunderbird"


@server.tool("list_profiles")
def list_profiles(params: dict[str, Any]) -> dict[str, Any]:
    tb_dir = _default_tb_dir(params.get("thunderbird_dir"))
    ini_path = tb_dir / "profiles.ini"
    if not ini_path.is_file():
        raise ConnectorError(f"profiles.ini not found: {ini_path}", -32000)

    parser = configparser.ConfigParser()
    parser.read(ini_path, encoding="utf-8")
    profiles: list[dict[str, Any]] = []
    for section in parser.sections():
        if section.startswith("Profile"):
            rel_path = parser.get(section, "Path", fallback="")
            is_rel = parser.getboolean(section, "IsRelative", fallback=True)
            resolved = str((tb_dir / rel_path).resolve()) if is_rel and rel_path else rel_path
            profiles.append(
                {
                    "section": section,
                    "name": parser.get(section, "Name", fallback=""),
                    "path": resolved,
                    "default": parser.getboolean(section, "Default", fallback=False),
                }
            )
    return {"thunderbird_dir": str(tb_dir), "profiles": profiles}


@server.tool("search_messages")
def search_messages(params: dict[str, Any]) -> dict[str, Any]:
    query = params.get("query")
    if not isinstance(query, str) or not query.strip():
        raise ConnectorError("'query' must be a non-empty string.", -32602)

    limit = params.get("limit", 15)
    if not isinstance(limit, int) or limit < 1 or limit > 50:
        raise ConnectorError("'limit' must be between 1 and 50.", -32602)

    raw_db = params.get("db_path")
    if raw_db is not None:
        if not isinstance(raw_db, str) or not raw_db.strip():
            raise ConnectorError("'db_path' must be a non-empty string.", -32602)
        db_path = Path(raw_db).expanduser().resolve()
    else:
        candidates = list((Path.home() / ".thunderbird").glob("*/global-messages-db.sqlite"))
        if not candidates:
            raise ConnectorError("No Thunderbird global-messages-db.sqlite found.", -32000)
        db_path = candidates[0]

    if not db_path.is_file():
        raise ConnectorError(f"Database not found: {db_path}", -32602)

    uri = f"{db_path.as_uri()}?mode=ro"
    like_term = f"%{query.strip()}%"
    try:
        with sqlite3.connect(uri, uri=True, timeout=2.0) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT docid, c3author, c1subject, c4attachmentNames
                FROM messagesText_content
                WHERE c1subject LIKE ? OR c3author LIKE ?
                LIMIT ?
                """,
                (like_term, like_term, limit),
            ).fetchall()
    except sqlite3.Error as exc:
        raise ConnectorError(f"Failed querying Thunderbird SQLite DB: {exc}", -32000) from exc

    results = [
        {
            "docid": row["docid"],
            "author": row["c3author"],
            "subject": row["c1subject"],
            "attachments": row["c4attachmentNames"],
        }
        for row in rows
    ]
    return {"db_path": str(db_path), "query": query.strip(), "count": len(results), "messages": results}


@server.tool("compose_email")
def compose_email(params: dict[str, Any]) -> dict[str, Any]:
    to = params.get("to")
    subject = params.get("subject")
    body = params.get("body", "")

    if not isinstance(to, str) or not EMAIL_RE.match(to.strip()):
        raise ConnectorError("'to' must be a single valid email address.", -32602)
    if not isinstance(subject, str) or not subject.strip():
        raise ConnectorError("'subject' must be a non-empty string.", -32602)
    if not isinstance(body, str):
        raise ConnectorError("'body' must be a string.", -32602)

    tb = shutil.which("thunderbird")
    if not tb:
        raise ConnectorError("Thunderbird is not installed on this system.", -32000)

    clean_subject = subject.replace("\r", " ").replace("\n", " ").replace("'", "")
    clean_body = body.replace("\r", "").replace("\n", "\\n").replace("'", "")
    compose_arg = f"to='{to.strip()}',subject='{clean_subject}',body='{clean_body}'"

    proc = subprocess.Popen(
        [tb, "-compose", compose_arg],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return {"opened_compose": True, "pid": proc.pid, "to": to.strip(), "subject": clean_subject}


if __name__ == "__main__":
    server.run_stdio()
