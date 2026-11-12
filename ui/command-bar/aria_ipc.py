#!/usr/bin/env python3
"""Zero-dependency Unix socket client and command parser for AriaOS Command Bar."""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path
from typing import Any


def resolve_socket_path() -> Path:
    custom = os.environ.get("ARIAOS_SOCKET_PATH")
    if custom:
        return Path(custom)
    runtime_sock = Path("/run/ariaos/agent.sock")
    if runtime_sock.exists():
        return runtime_sock
    return Path("/tmp/ariaos-agent.sock")


def parse_command(raw: str) -> dict[str, Any]:
    """Parse user input into a Command Bar intent ('tools', 'call', 'help', or 'ask')."""
    text = raw.strip()
    if not text:
        return {"kind": "empty"}
    if text in {"/help", "?"}:
        return {"kind": "help"}
    if text == "/tools":
        return {"kind": "tools"}
    if text in {"/kernel", "/telemetry"}:
        return {"kind": "kernel"}
    if text in {"/optimize", "/ram"}:
        return {"kind": "optimize"}
    if text.startswith("/call "):
        rest = text[6:].strip()
        parts = rest.split(None, 2)
        if len(parts) < 2:
            return {"kind": "error", "error": "Usage: /call <connector> <tool> [json_args]"}
        connector, tool = parts[0], parts[1]
        raw_args = parts[2].strip() if len(parts) > 2 else "{}"
        try:
            arguments = json.loads(raw_args)
        except json.JSONDecodeError as exc:
            return {"kind": "error", "error": f"Invalid JSON arguments: {exc}"}
        if not isinstance(arguments, dict):
            return {"kind": "error", "error": "Tool arguments must be a JSON object."}
        return {"kind": "call", "connector": connector, "tool": tool, "arguments": arguments}

    return {"kind": "ask", "prompt": text}


class AriaDaemonClient:
    """Client talking newline-delimited JSON to `aria-daemon` over Unix socket."""

    def __init__(self, socket_path: Path | str | None = None, timeout: float = 300.0) -> None:
        self.socket_path = Path(socket_path) if socket_path else resolve_socket_path()
        self.timeout = timeout

    def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not hasattr(socket, "AF_UNIX"):
            raise RuntimeError("Unix domain sockets are not supported on this platform.")
        if not self.socket_path.exists():
            raise ConnectionError(f"aria-daemon socket not found at {self.socket_path}")

        raw_line = json.dumps(payload) + "\n"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(self.timeout)
            sock.connect(str(self.socket_path))
            sock.sendall(raw_line.encode("utf-8"))
            chunks: list[bytes] = []
            while True:
                data = sock.recv(65536)
                if not data:
                    break
                chunks.append(data)
                if b"\n" in data:
                    break
        reply = b"".join(chunks).decode("utf-8").splitlines()[0]
        return json.loads(reply)

    def list_tools(self) -> dict[str, Any]:
        return self.request({"action": "list_tools"})

    def kernel_telemetry(self) -> dict[str, Any]:
        return self.request({"action": "kernel_telemetry"})

    def optimize_kernel(self) -> dict[str, Any]:
        return self.request({"action": "optimize_kernel"})

    def call_tool(
        self,
        connector: str,
        tool: str,
        arguments: dict[str, Any] | None = None,
        approved: bool = False,
    ) -> dict[str, Any]:
        return self.request(
            {
                "action": "call",
                "connector": connector,
                "tool": tool,
                "arguments": arguments or {},
                "approved": approved,
            }
        )

    def ask(self, prompt: str, approved_tools: list[str] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"action": "ask", "prompt": prompt}
        if approved_tools:
            payload["approved_tools"] = approved_tools
        return self.request(payload)
