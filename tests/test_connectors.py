"""Verification tests for AriaOS connector manifests, Python SDK, and stdio RPC."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
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

    def test_user_app_connectors_stdio_and_validation(self) -> None:
        def call(req_id: int, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            # 1. office-libreoffice: cross-platform .odt inspection + uno_status + validation
            odt_path = root / "sample.odt"
            with zipfile.ZipFile(odt_path, "w") as zf:
                zf.writestr(
                    "content.xml",
                    '<?xml version="1.0" encoding="UTF-8"?><office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"><office:body><text:p xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">Hola AriaOS LibreOffice</text:p></office:body></office:document-content>',
                )
            lo_res = _rpc_session(
                CONNECTORS_DIR / "office-libreoffice" / "connector.py",
                [
                    {"jsonrpc": "2.0", "id": 1, "method": "aria/info", "params": {}},
                    call(2, "inspect_document", {"path": str(odt_path)}),
                    call(3, "convert_document", {"input_path": str(odt_path), "target_format": "exe"}),
                ],
            )
            self.assertEqual(lo_res[0]["result"]["id"], "office-libreoffice")
            self.assertIn("Hola AriaOS LibreOffice", lo_res[1]["result"]["data"]["text_preview"])
            self.assertEqual(lo_res[2]["error"]["code"], -32602)

            # 2. office-okular: validation before poppler lookup
            ok_res = _rpc_session(
                CONNECTORS_DIR / "office-okular" / "connector.py",
                [
                    {"jsonrpc": "2.0", "id": 1, "method": "aria/info", "params": {}},
                    call(2, "inspect_pdf", {"path": str(root / "missing.pdf")}),
                    call(3, "extract_pdf_text", {"path": str(odt_path)}),
                ],
            )
            self.assertEqual(ok_res[0]["result"]["id"], "office-okular")
            self.assertEqual(ok_res[1]["error"]["code"], -32602)
            self.assertEqual(ok_res[2]["error"]["code"], -32602)

            # 3. browser-web: bookmarks search + URL scheme guard
            bm_path = root / "Bookmarks"
            bm_path.write_text(
                json.dumps(
                    {
                        "roots": {
                            "bookmark_bar": {
                                "type": "folder",
                                "name": "Dev",
                                "children": [{"type": "url", "name": "AriaOS Repo", "url": "https://github.com/faathii/AriaOS"}],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            bw_res = _rpc_session(
                CONNECTORS_DIR / "browser-web" / "connector.py",
                [
                    {"jsonrpc": "2.0", "id": 1, "method": "aria/info", "params": {}},
                    call(2, "search_bookmarks", {"query": "ariaos", "bookmarks_path": str(bm_path)}),
                    call(3, "open_url", {"url": "javascript:alert(1)"}),
                ],
            )
            self.assertEqual(bw_res[0]["result"]["id"], "browser-web")
            self.assertEqual(len(bw_res[1]["result"]["data"]["matches"]), 1)
            self.assertEqual(bw_res[2]["error"]["code"], -32602)

            # 4. media-players: strict service/action validation
            mp_res = _rpc_session(
                CONNECTORS_DIR / "media-players" / "connector.py",
                [
                    {"jsonrpc": "2.0", "id": 1, "method": "aria/info", "params": {}},
                    call(2, "control_playback", {"service": "bad.service", "action": "Play"}),
                    call(3, "play_media", {"path": str(root / "missing.mp3")}),
                ],
            )
            self.assertEqual(mp_res[0]["result"]["id"], "media-players")
            self.assertEqual(mp_res[1]["error"]["code"], -32602)
            self.assertEqual(mp_res[2]["error"]["code"], -32602)

            # 5. comms-thunderbird: profiles.ini reader + email validation
            tb_dir = root / "tb"
            tb_dir.mkdir()
            (tb_dir / "profiles.ini").write_text("[Profile0]\nName=default\nIsRelative=1\nPath=abc.default\nDefault=1\n", encoding="utf-8")
            tb_res = _rpc_session(
                CONNECTORS_DIR / "comms-thunderbird" / "connector.py",
                [
                    call(1, "list_profiles", {"thunderbird_dir": str(tb_dir)}),
                    call(2, "compose_email", {"to": "not-an-email", "subject": "Hi"}),
                ],
            )
            self.assertEqual(tb_res[0]["result"]["data"]["profiles"][0]["name"], "default")
            self.assertEqual(tb_res[1]["error"]["code"], -32602)

            # 6. net-filezilla: site reader strips passwords
            fz_xml = root / "sitemanager.xml"
            fz_xml.write_text(
                "<FileZilla3><Servers><Server><Host>example.org</Host><Port>22</Port><Protocol>1</Protocol><User>alice</User><Pass>SECRET123</Pass><Name>Prod</Name></Server></Servers></FileZilla3>",
                encoding="utf-8",
            )
            fz_res = _rpc_session(
                CONNECTORS_DIR / "net-filezilla" / "connector.py",
                [
                    call(1, "list_sites", {"xml_path": str(fz_xml)}),
                    call(2, "list_remote_dir", {"host": "bad;host", "user": "alice"}),
                ],
            )
            self.assertEqual(fz_res[0]["result"]["data"]["sites"][0]["host"], "example.org")
            self.assertNotIn("SECRET123", json.dumps(fz_res[0]))
            self.assertEqual(fz_res[1]["error"]["code"], -32602)

            # 7. media-obs, creative-gimp, creative-krita, creative-blender, creative-audacity, creative-kdenlive, dev-vscodium
            obs_res = _rpc_session(
                CONNECTORS_DIR / "media-obs" / "connector.py",
                [
                    {"jsonrpc": "2.0", "id": 1, "method": "aria/info", "params": {}},
                    call(2, "obs_request", {"request_type": "InvalidOp"}),
                ],
            )
            self.assertEqual(obs_res[0]["result"]["id"], "media-obs")
            self.assertEqual(obs_res[1]["error"]["code"], -32602)

            png_path = root / "pixel.png"
            png_path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x02\x80\x00\x00\x01\xe0\x08\x06\x00\x00\x00")
            gimp_res = _rpc_session(
                CONNECTORS_DIR / "creative-gimp" / "connector.py",
                [
                    call(1, "inspect_image", {"path": str(png_path)}),
                    call(2, "run_script_fu", {"expression": "not-lisp"}),
                ],
            )
            self.assertEqual((gimp_res[0]["result"]["data"]["width"], gimp_res[0]["result"]["data"]["height"]), (640, 480))
            self.assertEqual(gimp_res[1]["error"]["code"], -32602)

            kra_path = root / "art.kra"
            with zipfile.ZipFile(kra_path, "w") as zf:
                zf.writestr(
                    "maindoc.xml",
                    '<DOC><IMAGE width="1920" height="1080" colorspacename="RGBA"><layers><layer name="Sketch" nodetype="paintlayer" visible="1" opacity="255"/></layers></IMAGE></DOC>',
                )
            krita_res = _rpc_session(
                CONNECTORS_DIR / "creative-krita" / "connector.py",
                [call(1, "inspect_krita_doc", {"path": str(kra_path)})],
            )
            self.assertEqual(krita_res[0]["result"]["data"]["width"], 1920)
            self.assertEqual(krita_res[0]["result"]["data"]["layers"][0]["name"], "Sketch")

            blend_res = _rpc_session(
                CONNECTORS_DIR / "creative-blender" / "connector.py",
                [call(1, "inspect_blend_scene", {"path": str(root / "x.txt")})],
            )
            self.assertEqual(blend_res[0]["error"]["code"], -32602)

            aud_res = _rpc_session(
                CONNECTORS_DIR / "creative-audacity" / "connector.py",
                [
                    call(1, "pipe_status", {}),
                    call(2, "send_pipe_command", {"command": "line1\nline2"}),
                ],
            )
            self.assertIn("pipe_ready", aud_res[0]["result"]["data"])
            self.assertEqual(aud_res[1]["error"]["code"], -32602)

            kden_path = root / "proj.kdenlive"
            kden_path.write_text(
                '<mlt><profile width="1920" height="1080" frame_rate_num="60" frame_rate_den="1"/><producer id="p0"><property name="resource">clip.mp4</property></producer><playlist id="pl0"/></mlt>',
                encoding="utf-8",
            )
            kden_res = _rpc_session(
                CONNECTORS_DIR / "creative-kdenlive" / "connector.py",
                [call(1, "inspect_project", {"path": str(kden_path)})],
            )
            self.assertEqual(kden_res[0]["result"]["data"]["profile"]["width"], "1920")
            self.assertEqual(kden_res[0]["result"]["data"]["sources"], ["clip.mp4"])

            vsc_res = _rpc_session(
                CONNECTORS_DIR / "dev-vscodium" / "connector.py",
                [
                    {"jsonrpc": "2.0", "id": 1, "method": "aria/info", "params": {}},
                    call(2, "open_in_editor", {"path": str(root / "missing.py"), "line": 0}),
                ],
            )
            self.assertEqual(vsc_res[0]["result"]["id"], "dev-vscodium")
            self.assertEqual(vsc_res[1]["error"]["code"], -32602)


if __name__ == "__main__":
    unittest.main()
