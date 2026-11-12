"""Verification tests for AriaOS Command Bar IPC client and parser."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CMD_BAR_DIR = REPO_ROOT / "ui" / "command-bar"
sys.path.insert(0, str(CMD_BAR_DIR))

from aria_ipc import AriaDaemonClient, parse_command  # noqa: E402


class TestCommandBar(unittest.TestCase):
    def test_command_parser(self) -> None:
        self.assertEqual(parse_command("")["kind"], "empty")
        self.assertEqual(parse_command("/tools")["kind"], "tools")
        self.assertEqual(parse_command("check disk health"), {"kind": "ask", "prompt": "check disk health"})

        call = parse_command('/call os-files scan_directory {"path": "."}')
        self.assertEqual(
            call,
            {
                "kind": "call",
                "connector": "os-files",
                "tool": "scan_directory",
                "arguments": {"path": "."},
            },
        )
        self.assertEqual(parse_command("/call os-files")["kind"], "error")
        self.assertEqual(parse_command("/call os-files scan_directory {bad}")["kind"], "error")

    def test_command_bar_check_flag(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(CMD_BAR_DIR / "aria_command_bar.py"), "--check"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        payload = json.loads(proc.stdout.strip())
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["component"], "aria-command-bar")

    def test_welcome_center_check_flag(self) -> None:
        welcome_py = REPO_ROOT / "ui" / "welcome" / "aria_welcome.py"
        proc = subprocess.run(
            [sys.executable, str(welcome_py), "--check"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        payload = json.loads(proc.stdout.strip())
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["app"], "ariaos-welcome")

    @unittest.skipUnless(hasattr(socket, "AF_UNIX"), "AF_UNIX not available")
    def test_unix_socket_client_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sock_path = Path(tmp) / "agent.sock"
            srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            srv.bind(str(sock_path))
            srv.listen(2)

            def serve_once() -> None:
                for _ in range(2):
                    conn, _ = srv.accept()
                    with conn:
                        line = conn.recv(4096).decode("utf-8").strip()
                        req = json.loads(line)
                        if req["action"] == "list_tools":
                            resp = {"ok": True, "connectors": [{"id": "os-system", "tools": []}]}
                        else:
                            resp = {
                                "ok": bool(req.get("approved")),
                                "requires_confirmation": not req.get("approved"),
                                "risk_level": "write",
                            }
                        conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))

            t = threading.Thread(target=serve_once, daemon=True)
            t.start()
            try:
                client = AriaDaemonClient(sock_path)
                tools = client.list_tools()
                self.assertTrue(tools["ok"])
                self.assertEqual(tools["connectors"][0]["id"], "os-system")

                blocked = client.call_tool("os-files", "organize_directory", {"path": "/tmp"})
                self.assertFalse(blocked["ok"])
                self.assertTrue(blocked["requires_confirmation"])
            finally:
                srv.close()


if __name__ == "__main__":
    unittest.main()

