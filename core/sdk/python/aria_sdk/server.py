"""Lightweight zero-dependency JSON-RPC 2.0 stdio server for AriaOS connectors."""

from __future__ import annotations

import json
import sys
from typing import Any, Callable, Dict, Optional, TextIO

ToolHandler = Callable[[Dict[str, Any]], Any]


class ConnectorError(Exception):
    """Raised by a tool handler to return a structured JSON-RPC error."""

    def __init__(self, message: str, code: int = -32000) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ConnectorServer:
    """Minimal JSON-RPC 2.0 server speaking the AriaOS connector wire protocol."""

    PROTOCOL_VERSION = "aria-jsonrpc/1.0"

    def __init__(self, connector_id: str, version: str) -> None:
        self.connector_id = connector_id
        self.version = version
        self._tools: Dict[str, ToolHandler] = {}

    def tool(self, name: str) -> Callable[[ToolHandler], ToolHandler]:
        """Decorator registering a callable as an AriaOS connector tool."""

        def decorator(func: ToolHandler) -> ToolHandler:
            self._tools[name] = func
            return func

        return decorator

    def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a parsed JSON-RPC 2.0 request object and return a response dict."""
        req_id = request.get("id")
        if request.get("jsonrpc") != "2.0" or not isinstance(request.get("method"), str):
            return self._error(req_id, -32600, "Invalid JSON-RPC 2.0 request")

        method = request["method"]
        params = request.get("params")
        if params is None:
            params = {}
        if not isinstance(params, dict):
            return self._error(req_id, -32602, "Params must be a JSON object")

        if method == "aria/info":
            result = {
                "id": self.connector_id,
                "version": self.version,
                "protocol": self.PROTOCOL_VERSION,
            }
            return self._result(req_id, result)

        if method == "tools/list":
            return self._result(req_id, {"tools": sorted(self._tools.keys())})

        if method == "tools/call":
            return self._dispatch_tool(req_id, params)

        return self._error(req_id, -32601, f"Method not found: {method}")

    def _dispatch_tool(self, req_id: Any, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not isinstance(tool_name, str) or not tool_name:
            return self._error(req_id, -32602, "Missing tool 'name'")
        if not isinstance(arguments, dict):
            return self._error(req_id, -32602, "'arguments' must be a JSON object")

        handler = self._tools.get(tool_name)
        if handler is None:
            return self._error(req_id, -32601, f"Unknown tool: {tool_name}")

        try:
            output = handler(arguments)
            return self._result(req_id, {"ok": True, "data": output})
        except ConnectorError as exc:
            return self._error(req_id, exc.code, exc.message)
        except Exception as exc:  # noqa: BLE001 - surface runtime failure over RPC
            return self._error(req_id, -32000, f"Tool execution error: {exc}")

    @staticmethod
    def _result(req_id: Any, result: Any) -> Optional[Dict[str, Any]]:
        if req_id is None:
            return None
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    @staticmethod
    def _error(req_id: Any, code: int, message: str) -> Dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": code, "message": message},
        }

    def process_line(self, raw_line: str) -> Optional[str]:
        """Parse one NDJSON line and return serialized response, or None for notifications."""
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            return json.dumps(self._error(None, -32700, f"Parse error: {exc}"))

        if not isinstance(payload, dict):
            return json.dumps(self._error(None, -32600, "Request must be a JSON object"))

        response = self.handle_request(payload)
        return json.dumps(response) if response is not None else None

    def run_stdio(
        self,
        stdin: Optional[TextIO] = None,
        stdout: Optional[TextIO] = None,
    ) -> None:
        """Run the blocking newline-delimited JSON-RPC loop over stdio."""
        in_stream = stdin or sys.stdin
        out_stream = stdout or sys.stdout

        for line in in_stream:
            stripped = line.strip()
            if not stripped:
                continue
            reply = self.process_line(stripped)
            if reply is not None:
                out_stream.write(reply + "\n")
                out_stream.flush()

