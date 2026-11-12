#!/usr/bin/env python3
"""Floating KDE Plasma 6 Command Bar UI and CLI bridge for AriaOS."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from aria_ipc import AriaDaemonClient, parse_command  # noqa: E402


HELP_TEXT = (
    "AriaOS Command Bar:\n"
    "  - Ask naturally: e.g. 'Check system health and list top processes'\n"
    "  - Direct tool call: /call <connector> <tool> [json_args]\n"
    "  - List active tools: /tools\n"
    "  - Esc closes this window"
)


def _run_cli(client: AriaDaemonClient, prompt: str | None) -> int:
    def handle_one(text: str) -> None:
        intent = parse_command(text)
        kind = intent["kind"]
        if kind == "empty":
            return
        if kind == "help":
            print(HELP_TEXT)
            return
        if kind == "error":
            print(f"Error: {intent['error']}", file=sys.stderr)
            return
        try:
            if kind == "tools":
                resp = client.list_tools()
            elif kind == "call":
                resp = client.call_tool(intent["connector"], intent["tool"], intent["arguments"])
                if not resp.get("ok") and resp.get("requires_confirmation"):
                    risk = resp.get("risk_level", "write")
                    ans = input(
                        f"Allow {risk} action {intent['connector']}.{intent['tool']} "
                        f"with {json.dumps(intent['arguments'])}? [y/N]: "
                    ).strip().lower()
                    if ans in {"y", "yes", "s", "si"}:
                        resp = client.call_tool(
                            intent["connector"],
                            intent["tool"],
                            intent["arguments"],
                            approved=True,
                        )
            else:
                resp = client.ask(intent["prompt"])
            print(json.dumps(resp, indent=2, ensure_ascii=False))
        except Exception as exc:
            print(f"Daemon error: {exc}", file=sys.stderr)

    if prompt:
        handle_one(prompt)
        return 0

    print("AriaOS Command Bar CLI (type /help or Ctrl-D to exit)")
    for line in sys.stdin:
        handle_one(line)
    return 0


def _launch_gui(client: AriaDaemonClient) -> int:
    try:
        from PyQt6.QtCore import Qt, QThread, pyqtSignal
        from PyQt6.QtGui import QIcon, QKeySequence, QShortcut
        from PyQt6.QtWidgets import (
            QApplication,
            QLabel,
            QLineEdit,
            QListWidget,
            QMessageBox,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except ImportError as exc:
        print(f"PyQt6 is required for graphical Command Bar mode ({exc}). Falling back to --cli.", file=sys.stderr)
        return _run_cli(client, None)

    class DaemonWorker(QThread):
        finished_payload = pyqtSignal(dict, dict)

        def __init__(self, intent: dict[str, Any], approved: bool = False) -> None:
            super().__init__()
            self.intent = intent
            self.approved = approved

        def run(self) -> None:
            try:
                kind = self.intent["kind"]
                if kind == "tools":
                    resp = client.list_tools()
                elif kind == "call":
                    resp = client.call_tool(
                        self.intent["connector"],
                        self.intent["tool"],
                        self.intent["arguments"],
                        approved=self.approved,
                    )
                else:
                    resp = client.ask(self.intent["prompt"])
            except Exception as exc:
                resp = {"ok": False, "error": str(exc)}
            self.finished_payload.emit(self.intent, resp)

    class AriaCommandBar(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self._worker: DaemonWorker | None = None
            self.setWindowTitle("AriaOS Command Bar")
            self.setWindowIcon(QIcon.fromTheme("ariaos-logo"))
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Tool
            )
            self.resize(740, 420)
            self.setStyleSheet(
                """
                QWidget {
                    background-color: #121622;
                    color: #e6ecff;
                    border: 1px solid #3b82f6;
                    border-radius: 12px;
                    font-family: "Noto Sans", sans-serif;
                    font-size: 13px;
                }
                QLineEdit {
                    background-color: #1b2234;
                    border: 1px solid #334155;
                    border-radius: 8px;
                    padding: 10px 12px;
                    font-size: 15px;
                    color: #ffffff;
                }
                QTextEdit, QListWidget {
                    background-color: #0e121c;
                    border: 1px solid #263147;
                    border-radius: 8px;
                    padding: 8px;
                }
                QLabel#status {
                    border: none;
                    color: #94a3b8;
                    font-size: 11px;
                }
                """
            )

            layout = QVBoxLayout(self)
            layout.setContentsMargins(14, 14, 14, 14)
            layout.setSpacing(10)

            self.input = QLineEdit()
            self.input.setPlaceholderText("Ask AriaOS anything, or type /tools or /call <connector> <tool> {json}...")
            self.input.returnPressed.connect(self._on_submit)
            layout.addWidget(self.input)

            self.status_label = QLabel(f"Socket: {client.socket_path}  |  Press Esc to close")
            self.status_label.setObjectName("status")
            layout.addWidget(self.status_label)

            self.tools_list = QListWidget()
            self.tools_list.setMaximumHeight(110)
            self.tools_list.hide()
            self.tools_list.itemActivated.connect(self._on_tool_clicked)
            layout.addWidget(self.tools_list)

            self.output = QTextEdit()
            self.output.setReadOnly(True)
            self.output.setPlainText(HELP_TEXT)
            layout.addWidget(self.output)

            QShortcut(QKeySequence("Escape"), self).activated.connect(self.close)
            self._load_tools_preview()

        def _load_tools_preview(self) -> None:
            try:
                resp = client.list_tools()
                if resp.get("ok"):
                    self.tools_list.clear()
                    count = 0
                    for conn in resp.get("connectors", []):
                        cid = conn.get("id", "")
                        for tool in conn.get("tools", []):
                            tname = tool.get("name", "")
                            risk = tool.get("risk_level", "read")
                            self.tools_list.addItem(f"/call {cid} {tname} {{}}  [{risk}]")
                            count += 1
                    if count:
                        self.tools_list.show()
                        self.status_label.setText(
                            f"Connected ({len(resp.get('connectors', []))} connectors, {count} tools) | Esc to close"
                        )
            except Exception:
                self.status_label.setText(
                    f"Waiting for aria-daemon ({client.socket_path}) | Start: systemctl start aria-daemon"
                )

        def _on_tool_clicked(self, item: Any) -> None:
            cmd = item.text().split("  [", 1)[0]
            self.input.setText(cmd)
            self.input.setFocus()

        def _on_submit(self) -> None:
            raw = self.input.text()
            intent = parse_command(raw)
            kind = intent["kind"]
            if kind == "empty":
                return
            if kind == "help":
                self.output.setPlainText(HELP_TEXT)
                return
            if kind == "error":
                self.output.setPlainText(f"Error: {intent['error']}")
                return
            self._run_worker(intent, approved=False)

        def _run_worker(self, intent: dict[str, Any], approved: bool) -> None:
            self.input.setEnabled(False)
            self.status_label.setText("Running via aria-daemon...")
            self._worker = DaemonWorker(intent, approved=approved)
            self._worker.finished_payload.connect(self._on_result)
            self._worker.start()

        def _on_result(self, intent: dict[str, Any], resp: dict[str, Any]) -> None:
            self.input.setEnabled(True)
            self.input.setFocus()

            if not resp.get("ok") and resp.get("requires_confirmation"):
                risk = resp.get("risk_level", "write")
                reply = QMessageBox.question(
                    self,
                    "AriaOS Permission Request",
                    f"Approve {risk.upper()} action?\n\n"
                    f"Tool: {intent['connector']}.{intent['tool']}\n"
                    f"Arguments: {json.dumps(intent['arguments'], indent=2)}",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Cancel,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self._run_worker(intent, approved=True)
                    return
                self.output.setPlainText("Action cancelled by user.")
                self.status_label.setText("Cancelled")
                return

            self.status_label.setText("Ready | Esc to close")
            if resp.get("ok") and "answer" in resp:
                self.output.setPlainText(resp["answer"])
            else:
                self.output.setPlainText(json.dumps(resp, indent=2, ensure_ascii=False))

    app = QApplication(sys.argv)
    window = AriaCommandBar()
    screen = app.primaryScreen()
    if screen:
        geo = screen.availableGeometry()
        window.move(geo.center().x() - window.width() // 2, geo.top() + geo.height() // 6)
    window.show()
    window.input.setFocus()
    return app.exec()


def main() -> int:
    parser = argparse.ArgumentParser(description="AriaOS Floating Command Bar")
    parser.add_argument("--socket", help="Override aria-daemon Unix socket path")
    parser.add_argument("--cli", action="store_true", help="Run in headless CLI mode")
    parser.add_argument("--prompt", help="Execute a single command/prompt in CLI mode and exit")
    parser.add_argument("--check", action="store_true", help="Verify Command Bar imports cleanly and exit")
    args = parser.parse_args()

    if args.check:
        print(json.dumps({"ok": True, "component": "aria-command-bar"}))
        return 0

    client = AriaDaemonClient(args.socket)
    if args.cli or args.prompt:
        return _run_cli(client, args.prompt)
    return _launch_gui(client)


if __name__ == "__main__":
    raise SystemExit(main())

