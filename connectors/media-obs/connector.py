#!/usr/bin/env python3
"""OBS Studio & Kamoso connector for AriaOS (zero-dependency OBS WebSocket v5)."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

server = ConnectorServer("media-obs", "0.1.0")

ALLOWED_REQUESTS = {
    "GetVersion",
    "GetSceneList",
    "GetRecordStatus",
    "GetStreamStatus",
    "StartRecord",
    "StopRecord",
    "StartStream",
    "StopStream",
    "SetCurrentProgramScene",
}


def _ws_connect(host: str, port: int) -> tuple[socket.socket, dict[str, Any]]:
    sock = socket.create_connection((host, port), timeout=3.0)
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    handshake = (
        f"GET / HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        f"Upgrade: websocket\r\n"
        f"Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        f"Sec-WebSocket-Version: 13\r\n\r\n"
    )
    sock.sendall(handshake.encode("ascii"))
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            sock.close()
            raise ConnectorError("OBS WebSocket closed connection during handshake.", -32000)
        buf += chunk
    header_bytes, rest = buf.split(b"\r\n\r\n", 1)
    if b"101 " not in header_bytes.splitlines()[0]:
        sock.close()
        raise ConnectorError("OBS WebSocket did not upgrade HTTP connection.", -32000)

    hello_msg = _ws_recv_json(sock, bytearray(rest))
    return sock, hello_msg


def _recv_exact(sock: socket.socket, n: int, buffer: bytearray) -> bytes:
    while len(buffer) < n:
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectorError("Unexpected EOF reading OBS WebSocket frame.", -32000)
        buffer.extend(chunk)
    out = bytes(buffer[:n])
    del buffer[:n]
    return out


def _ws_recv_json(sock: socket.socket, buffer: bytearray) -> dict[str, Any]:
    first_two = _recv_exact(sock, 2, buffer)
    opcode = first_two[0] & 0x0F
    length = first_two[1] & 0x7F
    if length == 126:
        length = struct.unpack("!H", _recv_exact(sock, 2, buffer))[0]
    elif length == 127:
        length = struct.unpack("!Q", _recv_exact(sock, 8, buffer))[0]
    if first_two[1] & 0x80:
        _recv_exact(sock, 4, buffer)
    payload = _recv_exact(sock, length, buffer)
    if opcode == 8:
        raise ConnectorError("OBS WebSocket server closed session.", -32000)
    return json.loads(payload.decode("utf-8"))


def _ws_send_json(sock: socket.socket, data: dict[str, Any]) -> None:
    payload = json.dumps(data).encode("utf-8")
    mask = os.urandom(4)
    header = bytearray([0x81])
    n = len(payload)
    if n < 126:
        header.append(0x80 | n)
    elif n < 65536:
        header.append(0x80 | 126)
        header.extend(struct.pack("!H", n))
    else:
        header.append(0x80 | 127)
        header.extend(struct.pack("!Q", n))
    header.extend(mask)
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    sock.sendall(bytes(header) + masked)


def _obs_auth_string(password: str, challenge: str, salt: str) -> str:
    secret_hash = base64.b64encode(hashlib.sha256((password + salt).encode("utf-8")).digest()).decode("ascii")
    return base64.b64encode(hashlib.sha256((secret_hash + challenge).encode("utf-8")).digest()).decode("ascii")


def _validate_host_port(params: dict[str, Any]) -> tuple[str, int]:
    host = params.get("host", "127.0.0.1")
    port = params.get("port", 4455)
    if not isinstance(host, str) or not host.strip():
        raise ConnectorError("'host' must be a non-empty string.", -32602)
    if not isinstance(port, int) or port < 1 or port > 65535:
        raise ConnectorError("'port' must be between 1 and 65535.", -32602)
    return host.strip(), port


@server.tool("obs_websocket_status")
def obs_websocket_status(params: dict[str, Any]) -> dict[str, Any]:
    host, port = _validate_host_port(params)
    try:
        sock, hello = _ws_connect(host, port)
        sock.close()
    except OSError as exc:
        raise ConnectorError(f"OBS WebSocket not reachable on {host}:{port}: {exc}", -32000) from exc

    data = hello.get("d", {})
    return {
        "host": host,
        "port": port,
        "obs_websocket_version": data.get("obsWebSocketVersion"),
        "rpc_version": data.get("rpcVersion"),
        "authentication_required": bool(data.get("authentication")),
    }


@server.tool("obs_request")
def obs_request(params: dict[str, Any]) -> dict[str, Any]:
    request_type = params.get("request_type")
    if not isinstance(request_type, str) or request_type not in ALLOWED_REQUESTS:
        raise ConnectorError(f"'request_type' must be one of: {', '.join(sorted(ALLOWED_REQUESTS))}", -32602)

    request_data = params.get("request_data", {})
    if not isinstance(request_data, dict):
        raise ConnectorError("'request_data' must be an object.", -32602)

    host, port = _validate_host_port(params)
    password = params.get("password", "")
    if not isinstance(password, str):
        raise ConnectorError("'password' must be a string.", -32602)

    try:
        sock, hello = _ws_connect(host, port)
    except OSError as exc:
        raise ConnectorError(f"OBS WebSocket not reachable on {host}:{port}: {exc}", -32000) from exc

    try:
        buf = bytearray()
        identify_d: dict[str, Any] = {"rpcVersion": 1}
        auth = hello.get("d", {}).get("authentication")
        if auth:
            if not password:
                raise ConnectorError("OBS WebSocket requires 'password' authentication.", -32000)
            identify_d["authentication"] = _obs_auth_string(password, auth["challenge"], auth["salt"])

        _ws_send_json(sock, {"op": 1, "d": identify_d})
        identified = _ws_recv_json(sock, buf)
        if identified.get("op") != 2:
            raise ConnectorError(f"OBS WebSocket identify failed: {identified}", -32000)

        _ws_send_json(
            sock,
            {
                "op": 6,
                "d": {
                    "requestType": request_type,
                    "requestId": "aria-1",
                    "requestData": request_data,
                },
            },
        )
        resp = _ws_recv_json(sock, buf)
        d = resp.get("d", {})
        status = d.get("requestStatus", {})
        if not status.get("result"):
            raise ConnectorError(f"OBS request '{request_type}' failed: {status.get('comment', status)}", -32000)
        return {"request_type": request_type, "response_data": d.get("responseData", {})}
    finally:
        sock.close()


@server.tool("launch_capture_app")
def launch_capture_app(params: dict[str, Any]) -> dict[str, Any]:
    app = params.get("app", "obs")
    if app not in {"obs", "kamoso"}:
        raise ConnectorError("'app' must be 'obs' or 'kamoso'.", -32602)

    binary = shutil.which(app)
    if not binary:
        raise ConnectorError(f"'{app}' is not installed on this system.", -32000)

    proc = subprocess.Popen([binary], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return {"launched": True, "app": app, "pid": proc.pid}


if __name__ == "__main__":
    server.run_stdio()
