"""AriaOS `dev-git` connector: inspect repositories, diffs, history, and commit safely."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

server = ConnectorServer(connector_id="dev-git", version="0.1.0")


def _require_repo(raw_path: Any) -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ConnectorError("Parameter 'repo_path' must be a non-empty string", code=-32602)
    repo = Path(raw_path).expanduser().resolve()
    if not repo.is_dir():
        raise ConnectorError(f"Repository directory does not exist: {repo}", code=-32602)
    return repo


def _git(repo: Path, args: List[str]) -> str:
    res = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if res.returncode != 0:
        raise ConnectorError(res.stderr.strip() or f"git {' '.join(args)} failed")
    return res.stdout


@server.tool("repo_status")
def repo_status(args: Dict[str, Any]) -> Dict[str, Any]:
    """Return branch name and changed/untracked files."""
    repo = _require_repo(args.get("repo_path"))
    out = _git(repo, ["status", "--porcelain=v1", "-b"])
    lines = out.splitlines()
    branch = lines[0].removeprefix("## ").strip() if lines else "unknown"
    changes = [ln for ln in lines[1:] if ln.strip()]
    return {
        "repo_path": str(repo),
        "branch": branch,
        "clean": len(changes) == 0,
        "changes": changes,
    }


@server.tool("repo_log")
def repo_log(args: Dict[str, Any]) -> Dict[str, Any]:
    """Return recent commit summaries."""
    repo = _require_repo(args.get("repo_path"))
    limit = max(1, min(int(args.get("limit", 10)), 50))
    out = _git(repo, ["log", f"-n{limit}", "--format=%h|%an|%ad|%s", "--date=short"])
    commits = []
    for line in out.splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4:
            commits.append(
                {"hash": parts[0], "author": parts[1], "date": parts[2], "subject": parts[3]}
            )
    return {"repo_path": str(repo), "commits": commits}


@server.tool("repo_diff")
def repo_diff(args: Dict[str, Any]) -> Dict[str, Any]:
    """Return diff summary and bounded patch preview."""
    repo = _require_repo(args.get("repo_path"))
    staged = bool(args.get("staged", False))
    base_args = ["diff", "--cached"] if staged else ["diff"]
    stat = _git(repo, [*base_args, "--stat"]).strip()
    patch = _git(repo, base_args)
    truncated = len(patch) > 4000
    return {
        "repo_path": str(repo),
        "staged": staged,
        "stat": stat,
        "patch": patch[:4000],
        "truncated": truncated,
    }


@server.tool("stage_and_commit")
def stage_and_commit(args: Dict[str, Any]) -> Dict[str, Any]:
    """Stage specific files and create a commit."""
    repo = _require_repo(args.get("repo_path"))
    files = args.get("files")
    message = str(args.get("message", "")).strip()
    if not isinstance(files, list) or not files or not all(isinstance(f, str) and f.strip() for f in files):
        raise ConnectorError("Parameter 'files' must be a non-empty list of paths", code=-32602)
    if not message:
        raise ConnectorError("Parameter 'message' must be non-empty", code=-32602)

    _git(repo, ["add", "--", *files])
    _git(repo, ["commit", "-m", message])
    head = _git(repo, ["rev-parse", "--short", "HEAD"]).strip()
    return {"repo_path": str(repo), "commit": head, "message": message}


if __name__ == "__main__":
    server.run_stdio()
