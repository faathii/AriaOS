"""AriaOS `multimedia-ffmpeg` connector: inspect and transcode media safely."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

server = ConnectorServer(connector_id="multimedia-ffmpeg", version="0.1.0")


def _require_file(raw_path: Any, label: str = "path") -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ConnectorError(f"Parameter '{label}' must be a non-empty string", code=-32602)
    target = Path(raw_path).expanduser().resolve()
    if not target.exists() or not target.is_file():
        raise ConnectorError(f"File does not exist: {target}", code=-32602)
    return target


def _run_tool(cmd: List[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except FileNotFoundError as exc:
        raise ConnectorError(f"Missing media tool '{cmd[0]}' (install ffmpeg)") from exc


@server.tool("inspect_media")
def inspect_media(args: Dict[str, Any]) -> Dict[str, Any]:
    """Return structured format and stream metadata from ffprobe."""
    target = _require_file(args.get("path"))
    res = _run_tool(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(target)],
        timeout=20,
    )
    if res.returncode != 0:
        raise ConnectorError(res.stderr.strip() or f"ffprobe failed on {target}")

    probe = json.loads(res.stdout or "{}")
    fmt = probe.get("format", {})
    streams = [
        {
            "codec_type": s.get("codec_type"),
            "codec_name": s.get("codec_name"),
            "width": s.get("width"),
            "height": s.get("height"),
            "sample_rate": s.get("sample_rate"),
        }
        for s in probe.get("streams", [])
    ]
    return {
        "path": str(target),
        "format_name": fmt.get("format_name"),
        "duration_seconds": float(fmt["duration"]) if "duration" in fmt else None,
        "size_bytes": int(fmt["size"]) if "size" in fmt else target.stat().st_size,
        "streams": streams,
    }


@server.tool("convert_media")
def convert_media(args: Dict[str, Any]) -> Dict[str, Any]:
    """Transcode input_path into a non-existing output_path using ffmpeg."""
    src = _require_file(args.get("input_path"), label="input_path")
    raw_out = args.get("output_path")
    if not isinstance(raw_out, str) or not raw_out.strip():
        raise ConnectorError("Parameter 'output_path' must be a non-empty string", code=-32602)
    dst = Path(raw_out).expanduser().resolve()
    if dst.exists():
        raise ConnectorError(f"Refusing to overwrite existing output file: {dst}", code=-32602)

    preset = args.get("preset", "balanced")
    cmd = ["ffmpeg", "-nostdin", "-i", str(src)]
    if preset == "audio_only":
        cmd += ["-vn"]
    elif preset == "fast":
        cmd += ["-preset", "veryfast"]
    elif preset != "balanced":
        raise ConnectorError(f"Unsupported preset: {preset}", code=-32602)

    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd.append(str(dst))

    res = _run_tool(cmd, timeout=300)
    if res.returncode != 0:
        raise ConnectorError(res.stderr.splitlines()[-1] if res.stderr else "ffmpeg conversion failed")

    return {"input_path": str(src), "output_path": str(dst), "size_bytes": dst.stat().st_size}


if __name__ == "__main__":
    server.run_stdio()

