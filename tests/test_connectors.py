"""Verification tests for AriaOS connector manifests, Python SDK, and stdio RPC."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
CONNECTORS_DIR = REPO_ROOT / "connectors"
SCHEMA_PATH = REPO_ROOT / "core" / "protocol" / "connector.schema.json"

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
TOOL_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
VALID_TIERS = {"os_ipc", "program_api", "ui_fallback"}
VALID_TRANSPORTS = {"stdio", "unix_socket", "dbus"}
VALID_RISK_LEVELS = {"read", "write", "privileged"}


def _rpc_session(script_path: Path, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    payload = "\n".join(json.dumps(req) for req in requests) + "\n"
    proc = subprocess.run(
        [sys.executable, str(script_path)],
        input=payload,
        text=True,
        capture_output=True,
        check=True,
        timeout=10,
    )
    return [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]


class TestConnectorManifests(unittest.TestCase):
    """Validate protocol schema and every connector manifest in `connectors/`."""

    def test_schema_is_valid_json(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(schema["type"], "object")
        self.assertIn("tools", schema["properties"])

    def test_all_manifests_conform_to_contract(self) -> None:
        manifest_paths = sorted(CONNECTORS_DIR.glob("*/manifest.json"))
        self.assertGreaterEqual(len(manifest_paths), 4)

        seen_ids = set()
        for path in manifest_paths:
            with self.subTest(manifest=str(path)):
                data = json.loads(path.read_text(encoding="utf-8"))
                for req_field in ("id", "name", "version", "tier", "transport", "tools"):
                    self.assertIn(req_field, data)

                self.assertRegex(data["id"], ID_RE)
                self.assertNotIn(data["id"], seen_ids)
                seen_ids.add(data["id"])

                self.assertRegex(data["version"], SEMVER_RE)
                self.assertIn(data["tier"], VALID_TIERS)
                self.assertIn(data["transport"], VALID_TRANSPORTS)
                self.assertIsInstance(data["tools"], list)
                self.assertGreater(len(data["tools"]), 0)

                for tool in data["tools"]:
                    self.assertRegex(tool["name"], TOOL_NAME_RE)
                    self.assertIn(tool["risk_level"], VALID_RISK_LEVELS)
                    self.assertEqual(tool["input_schema"]["type"], "object")


class TestStdioConnectors(unittest.TestCase):
    """Exercise live JSON-RPC stdio execution for template and os-files connectors."""

    def test_template_connector_ping(self) -> None:
        script = CONNECTORS_DIR / "_template" / "connector.py"
        responses = _rpc_session(
            script,
            [
                {"jsonrpc": "2.0", "id": 1, "method": "aria/info", "params": {}},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "ping", "arguments": {"message": "ariaos"}},
                },
            ],
        )
        self.assertEqual(responses[0]["result"]["id"], "template-example")
        self.assertEqual(responses[1]["result"]["tools"], ["ping"])
        self.assertEqual(responses[2]["result"]["data"]["reply"], "ariaos")

    def test_os_files_scan_dedup_and_organize(self) -> None:
        script = CONNECTORS_DIR / "os-files" / "connector.py"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "notes.md").write_text("hello aria", encoding="utf-8")
            (root / "photo.png").write_bytes(b"fake-png-bytes")
            (root / "copy.png").write_bytes(b"fake-png-bytes")

            responses = _rpc_session(
                script,
                [
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/call",
                        "params": {"name": "scan_directory", "arguments": {"path": str(root)}},
                    },
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {"name": "find_duplicates", "arguments": {"path": str(root)}},
                    },
                    {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {
                            "name": "organize_directory",
                            "arguments": {"path": str(root), "apply": False},
                        },
                    },
                ],
            )

            scan = responses[0]["result"]["data"]
            self.assertEqual(scan["total_files"], 3)
            self.assertEqual(scan["categories"], {"Documents": 1, "Images": 2})

            dups = responses[1]["result"]["data"]["duplicate_groups"]
            self.assertEqual(len(dups), 1)
            self.assertEqual(len(dups[0]["files"]), 2)

            dry_run = responses[2]["result"]["data"]
            self.assertFalse(dry_run["applied"])
            self.assertEqual(len(dry_run["moves"]), 3)
            self.assertTrue((root / "notes.md").exists())

            apply_responses = _rpc_session(
                script,
                [
                    {
                        "jsonrpc": "2.0",
                        "id": 4,
                        "method": "tools/call",
                        "params": {
                            "name": "organize_directory",
                            "arguments": {"path": str(root), "apply": True},
                        },
                    },
                    {
                        "jsonrpc": "2.0",
                        "id": 5,
                        "method": "tools/call",
                        "params": {"name": "nonexistent_tool", "arguments": {}},
                    },
                ],
            )

            applied = apply_responses[0]["result"]["data"]
            self.assertTrue(applied["applied"])
            self.assertTrue((root / "Documents" / "notes.md").exists())
            self.assertTrue((root / "Images" / "photo.png").exists())
            self.assertTrue((root / "Images" / "copy.png").exists())

            self.assertEqual(apply_responses[1]["error"]["code"], -32601)

    def test_os_system_and_desktop_and_ffmpeg_info(self) -> None:
        system_script = CONNECTORS_DIR / "os-system" / "connector.py"
        sys_res = _rpc_session(
            system_script,
            [
                {"jsonrpc": "2.0", "id": 1, "method": "aria/info", "params": {}},
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "system_health_summary", "arguments": {}},
                },
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "service_status", "arguments": {"unit": "bad;unit"}},
                },
            ],
        )
        self.assertEqual(sys_res[0]["result"]["id"], "os-system")
        self.assertGreater(sys_res[1]["result"]["data"]["disk"]["total_gb"], 0)
        self.assertEqual(sys_res[2]["error"]["code"], -32602)

        desktop_script = CONNECTORS_DIR / "os-desktop" / "connector.py"
        desk_res = _rpc_session(
            desktop_script,
            [
                {"jsonrpc": "2.0", "id": 1, "method": "aria/info", "params": {}},
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "desktop_environment_info", "arguments": {}},
                },
            ],
        )
        self.assertEqual(desk_res[0]["result"]["id"], "os-desktop")
        self.assertIn("has_graphical_session", desk_res[1]["result"]["data"])

        ffmpeg_script = CONNECTORS_DIR / "multimedia-ffmpeg" / "connector.py"
        ff_res = _rpc_session(
            ffmpeg_script,
            [
                {"jsonrpc": "2.0", "id": 1, "method": "aria/info", "params": {}},
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "inspect_media", "arguments": {"path": "/no/such/file.mp4"}},
                },
            ],
        )
        self.assertEqual(ff_res[0]["result"]["id"], "multimedia-ffmpeg")
        self.assertEqual(ff_res[1]["error"]["code"], -32602)

    def test_os_storage_archives_dev_git_and_os_packages(self) -> None:
        storage_script = CONNECTORS_DIR / "os-storage" / "connector.py"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src_dir = root / "bundle"
            src_dir.mkdir()
            (src_dir / "hello.txt").write_text("aria archive", encoding="utf-8")
            zip_path = root / "bundle.zip"
            out_dir = root / "extracted"

            st_res = _rpc_session(
                storage_script,
                [
                    {"jsonrpc": "2.0", "id": 1, "method": "aria/info", "params": {}},
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "create_archive",
                            "arguments": {"source_path": str(src_dir), "archive_path": str(zip_path)},
                        },
                    },
                    {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {
                            "name": "inspect_archive",
                            "arguments": {"archive_path": str(zip_path)},
                        },
                    },
                    {
                        "jsonrpc": "2.0",
                        "id": 4,
                        "method": "tools/call",
                        "params": {
                            "name": "extract_archive",
                            "arguments": {
                                "archive_path": str(zip_path),
                                "destination_dir": str(out_dir),
                            },
                        },
                    },
                ],
            )
            self.assertEqual(st_res[0]["result"]["id"], "os-storage")
            self.assertTrue(zip_path.exists())
            self.assertEqual(st_res[2]["result"]["data"]["count"], 1)
            self.assertEqual(st_res[3]["result"]["data"]["extracted_count"], 1)
            self.assertTrue((out_dir / "bundle" / "hello.txt").exists())

        git_script = CONNECTORS_DIR / "dev-git" / "connector.py"
        git_res = _rpc_session(
            git_script,
            [
                {"jsonrpc": "2.0", "id": 1, "method": "aria/info", "params": {}},
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "repo_status", "arguments": {"repo_path": str(REPO_ROOT)}},
                },
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "repo_log",
                        "arguments": {"repo_path": str(REPO_ROOT), "limit": 2},
                    },
                },
            ],
        )
        self.assertEqual(git_res[0]["result"]["id"], "dev-git")
        self.assertIn("main", git_res[1]["result"]["data"]["branch"])
        self.assertEqual(len(git_res[2]["result"]["data"]["commits"]), 2)

        pkg_script = CONNECTORS_DIR / "os-packages" / "connector.py"
        pkg_res = _rpc_session(
            pkg_script,
            [
                {"jsonrpc": "2.0", "id": 1, "method": "aria/info", "params": {}},
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "install_package", "arguments": {"package": "bad;rm -rf /"}},
                },
            ],
        )
        self.assertEqual(pkg_res[0]["result"]["id"], "os-packages")
        self.assertEqual(pkg_res[1]["error"]["code"], -32602)


if __name__ == "__main__":
    unittest.main()
