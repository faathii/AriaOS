#!/usr/bin/env python3
"""AriaOS Neural HUD — Futuristic Minimalist Kernel-Integrated AI Command Bar."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

SDK_PATH = HERE.parents[1] / "core" / "sdk" / "python"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))
SYSTEM_SDK = Path("/usr/lib/ariaos/core/sdk/python")
if SYSTEM_SDK.exists() and str(SYSTEM_SDK) not in sys.path:
    sys.path.insert(0, str(SYSTEM_SDK))

from aria_ipc import AriaDaemonClient, parse_command  # noqa: E402

try:
    from aria_sdk import get_current_language, t  # noqa: E402
except ImportError:
    def get_current_language() -> str:
        return "es"

    def t(key: str, _lang: str | None = None, **_kwargs: Any) -> str:
        return key


HELP_TEXT = (
    "### ⚡ AriaOS Neural HUD\n"
    "- **Modos Pre-entrenados del Kernel:** *«Modo gaming»*, *«Modo desarrollo»*, *«Modo creativo»*, *«Modo ahorro extremo»*, *«Modo seguridad»*\n"
    "- **Control Natural del Sistema:** *«Estado del sistema»*, *«Optimizar RAM»*, *«Procesos»*, *«Espacio en disco»*, *«Red / IP»*\n"
    "- **Herramientas Nativas Cyber Obsidian:** *«Abrir monitor»*, *«Abrir tienda»*, *«Abrir automatizaciones»*, *«Abrir antivirus»*\n"
    "- **Auto-Aprendizaje Neuronal:** *«aprende: cuando diga modo stream -> abre obs y vscodium»*, `/memory`, `/catalog`\n"
    "- **Hardware:** *«Volumen al 75%»*, *«Brillo al 80%»*, *«Hardware PCI/USB»*\n"
    "- Pulsa **Esc** para ocultar el HUD."
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
            elif kind == "kernel":
                resp = client.kernel_telemetry()
            elif kind == "optimize":
                resp = client.optimize_kernel()
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
                approved_tools: list[str] = []
                resp = client.ask(intent["prompt"], approved_tools=approved_tools)
                while not resp.get("ok") and resp.get("requires_confirmation") and resp.get("pending_call"):
                    pc = resp["pending_call"]
                    risk = resp.get("risk_level", "write")
                    tool_key = f"{pc['connector']}.{pc['tool']}"
                    ans = input(
                        f"Allow {risk} action {tool_key} "
                        f"with {json.dumps(pc.get('arguments', {}))}? [y/N]: "
                    ).strip().lower()
                    if ans not in {"y", "yes", "s", "si"}:
                        break
                    approved_tools.append(tool_key)
                    resp = client.ask(intent["prompt"], approved_tools=approved_tools)
            print(json.dumps(resp, indent=2, ensure_ascii=False))
        except Exception as exc:
            print(f"Daemon error: {exc}", file=sys.stderr)

    if prompt:
        handle_one(prompt)
        return 0

    print("AriaOS Neural HUD CLI (type /help or Ctrl-D to exit)")
    for line in sys.stdin:
        handle_one(line)
    return 0


def _launch_gui(client: AriaDaemonClient) -> int:
    import socket as py_socket
    _lock = py_socket.socket(py_socket.AF_INET, py_socket.SOCK_STREAM)
    try:
        _lock.bind(("127.0.0.1", 47788))
    except OSError:
        return 0

    try:
        from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
        from PyQt6.QtGui import QIcon, QKeySequence, QShortcut
        from PyQt6.QtWidgets import (
            QApplication,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QMessageBox,
            QPushButton,
            QTextBrowser,
            QVBoxLayout,
            QWidget,
        )
    except ImportError:
        print(
            "PyQt6 not installed; falling back to CLI mode. Install python-pyqt6 for the graphical HUD.",
            file=sys.stderr,
        )
        return _run_cli(client, None)

    class DaemonWorker(QThread):
        finished_payload = pyqtSignal(dict, dict)

        def __init__(
            self,
            intent: dict[str, Any],
            approved: bool = False,
            approved_tools: list[str] | None = None,
        ) -> None:
            super().__init__()
            self.intent = intent
            self.approved = approved
            self.approved_tools = approved_tools or []

        def run(self) -> None:
            kind = self.intent["kind"]
            try:
                if kind == "tools":
                    resp = client.list_tools()
                elif kind == "kernel":
                    resp = client.kernel_telemetry()
                elif kind == "optimize":
                    resp = client.optimize_kernel()
                elif kind == "call":
                    resp = client.call_tool(
                        self.intent["connector"],
                        self.intent["tool"],
                        self.intent["arguments"],
                        approved=self.approved,
                    )
                else:
                    resp = client.ask(self.intent["prompt"], approved_tools=self.approved_tools)
            except Exception as exc:
                resp = {"ok": False, "error": str(exc)}
            self.finished_payload.emit(self.intent, resp)

    class AriaCommandBar(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self._worker: DaemonWorker | None = None
            self.lang = get_current_language()
            self.setWindowTitle("AriaOS Neural HUD")
            self.setWindowIcon(QIcon.fromTheme("ariaos-logo"))
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Tool
            )
            self.resize(800, 470)
            self.setStyleSheet(
                """
                QWidget {
                    background-color: #12161f;
                    color: #e6edf3;
                    border: 1px solid rgba(255, 255, 255, 30);
                    border-radius: 14px;
                    font-family: "Noto Sans", sans-serif;
                    font-size: 13px;
                }
                QLabel#telemetry_strip {
                    background-color: #161b24;
                    border: 1px solid rgba(255, 255, 255, 18);
                    border-radius: 8px;
                    padding: 6px 12px;
                    color: #8b949e;
                    font-family: monospace;
                    font-size: 11px;
                }
                QLineEdit {
                    background-color: #181d28;
                    border: 1px solid rgba(255, 255, 255, 24);
                    border-radius: 10px;
                    padding: 12px 14px;
                    font-size: 14px;
                    color: #ffffff;
                }
                QLineEdit:focus {
                    border: 1.5px solid #3b82f6;
                    background-color: #1c2230;
                }
                QPushButton.pill {
                    background-color: rgba(255, 255, 255, 14);
                    border: 1px solid rgba(255, 255, 255, 20);
                    border-radius: 7px;
                    padding: 6px 10px;
                    font-size: 12px;
                    color: #c9d1d9;
                }
                QPushButton.pill:hover {
                    background-color: #3b82f6;
                    color: #ffffff;
                    border-color: #3b82f6;
                }
                QPushButton#btn_settings {
                    background-color: rgba(255, 255, 255, 14);
                    border: 1px solid rgba(255, 255, 255, 20);
                    border-radius: 10px;
                    font-size: 16px;
                    color: #e6edf3;
                }
                QPushButton#btn_settings:hover {
                    background-color: #3b82f6;
                    color: #ffffff;
                }
                QPushButton#btn_close_hud {
                    background-color: rgba(239, 68, 68, 40);
                    color: #f87171;
                    border: 1px solid rgba(239, 68, 68, 60);
                    border-radius: 6px;
                    font-size: 11px;
                    padding: 2px 8px;
                }
                QPushButton#btn_close_hud:hover {
                    background-color: #ef4444;
                    color: #ffffff;
                }
                QTextBrowser {
                    background-color: #141822;
                    border: 1px solid rgba(255, 255, 255, 18);
                    border-radius: 10px;
                    padding: 12px;
                    color: #e6edf3;
                    font-size: 13px;
                }
                QLabel#status {
                    border: none;
                    color: #8b949e;
                    font-size: 11px;
                }
                """
            )

            layout = QVBoxLayout(self)
            layout.setContentsMargins(16, 16, 16, 14)
            layout.setSpacing(10)

            # Top Header with Kernel Telemetry & Close button
            top_header = QHBoxLayout()
            self.telemetry_strip = QLabel("⚡ ARIA NEURAL CORE • ENLAZANDO CON EL KERNEL...")
            self.telemetry_strip.setObjectName("telemetry_strip")
            top_header.addWidget(self.telemetry_strip, 1)

            btn_close = QPushButton("✕")
            btn_close.setObjectName("btn_close_hud")
            btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_close.setFixedSize(26, 26)
            btn_close.clicked.connect(self.close)
            top_header.addWidget(btn_close)
            layout.addLayout(top_header)

            # Main Search & Command Input Bar
            input_bar = QHBoxLayout()
            self.input = QLineEdit()
            self.input.setPlaceholderText("Habla con Aria (ej. «Optimizar RAM», «Estado del sistema», «Abrir terminal»)...")
            self.input.returnPressed.connect(self._on_submit)
            input_bar.addWidget(self.input)

            self.btn_settings = QPushButton("⚙️")
            self.btn_settings.setObjectName("btn_settings")
            self.btn_settings.setFixedSize(44, 44)
            self.btn_settings.setToolTip("Centro de Control AriaOS")
            self.btn_settings.clicked.connect(self._open_settings)
            input_bar.addWidget(self.btn_settings)
            layout.addLayout(input_bar)

            # Quick-Action Cyber Pills
            pills_bar = QHBoxLayout()
            pills_bar.setSpacing(8)
            quick_actions = [
                ("⚡ Optimizar RAM", "optimizar ram"),
                ("🎛️ Modos Kernel", "modos de trabajo"),
                ("🧠 Salud Kernel", "estado del sistema"),
                ("📊 Top Procesos", "procesos"),
                ("🛡️ Antivirus", "antivirus"),
                ("📖 APIs & Comandos", "/apis"),
                ("📚 Memoria IA", "/memory"),
            ]
            for label, cmd in quick_actions:
                btn = QPushButton(label)
                btn.setProperty("class", "pill")
                btn.clicked.connect(lambda _checked=False, c=cmd: self._run_quick_prompt(c))
                pills_bar.addWidget(btn)
            layout.addLayout(pills_bar)

            # Rich Markdown Output Display
            self.output = QTextBrowser()
            self.output.setOpenExternalLinks(False)
            self.output.setMarkdown(HELP_TEXT)
            layout.addWidget(self.output)

            # Bottom Status Bar
            self.status_label = QLabel("⚡ Motor Neuronal Híbrido Activo (<1ms)  |  Atajo: Alt+Space  |  Esc para cerrar")
            self.status_label.setObjectName("status")
            layout.addWidget(self.status_label)

            QShortcut(QKeySequence("Escape"), self).activated.connect(self.close)

            # Periodic Kernel Telemetry Refresh (every 3 seconds)
            self.timer = QTimer(self)
            self.timer.timeout.connect(self._refresh_telemetry)
            self.timer.start(3000)
            self._refresh_telemetry()

            # Trigger instant welcome pulse
            self._run_quick_prompt("hola")

        def mousePressEvent(self, event) -> None:
            if event.button() == Qt.MouseButton.LeftButton:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()

        def mouseMoveEvent(self, event) -> None:
            if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, "_drag_pos"):
                self.move(event.globalPosition().toPoint() - self._drag_pos)
                event.accept()

        def _refresh_telemetry(self) -> None:
            try:
                resp = client.kernel_telemetry()
                if resp.get("ok") and "telemetry" in resp:
                    t_data = resp["telemetry"]
                    mem = t_data.get("memory", {})
                    psi = t_data.get("psi", {})
                    load = t_data.get("load_avg", [0.0])[0]
                    used = mem.get("used_mb", 0)
                    total = mem.get("total_mb", 0)
                    pct = mem.get("usage_pct", 0)
                    psi_mem = psi.get("memory_avg10", 0.0)
                    tier = t_data.get("hardware_tier", "Tier-A")
                    avx2 = "AVX2" if t_data.get("silicon", {}).get("avx2") else "SSE4.2"
                    self.telemetry_strip.setText(
                        f"🧠 {tier} [{avx2}]  |  ⚡ CPU: {load:.2f}  |  "
                        f"💾 RAM: {used}/{total} MB ({pct}%)  |  🟢 PSI: {psi_mem:.1f}%"
                    )
            except Exception:
                self.telemetry_strip.setText(
                    "⚠️ ARIA DAEMON OFFLINE — Ejecuta: sudo systemctl start aria-daemon"
                )

        def _run_quick_prompt(self, prompt_text: str) -> None:
            self.input.setText(prompt_text)
            self._on_submit()

        def _on_submit(self) -> None:
            raw = self.input.text()
            intent = parse_command(raw)
            kind = intent["kind"]
            if kind == "empty":
                return
            if kind == "help":
                self.output.setMarkdown(HELP_TEXT)
                return
            if kind == "error":
                self.output.setPlainText(f"Error: {intent['error']}")
                return
            self._run_worker(intent, approved=False)

        def _run_worker(
            self,
            intent: dict[str, Any],
            approved: bool = False,
            approved_tools: list[str] | None = None,
        ) -> None:
            self.input.setEnabled(False)
            self.status_label.setText("⚡ Procesando en el Núcleo Neuronal de AriaOS...")
            self._worker = DaemonWorker(intent, approved=approved, approved_tools=approved_tools)
            self._worker.finished_payload.connect(self._on_result)
            self._worker.start()

        def _on_result(self, intent: dict[str, Any], resp: dict[str, Any]) -> None:
            self.input.setEnabled(True)
            self.input.setFocus()
            self._refresh_telemetry()

            if not resp.get("ok") and resp.get("requires_confirmation"):
                risk = resp.get("risk_level", "write")
                pc = resp.get("pending_call")
                if pc:
                    tool_key = f"{pc['connector']}.{pc['tool']}"
                    tool_args = pc.get("arguments", {})
                else:
                    tool_key = f"{intent['connector']}.{intent['tool']}"
                    tool_args = intent["arguments"]
                prompt_text = t(
                    "permission_approve_prompt",
                    self.lang,
                    risk=risk.upper(),
                    tool=tool_key,
                    args=json.dumps(tool_args, indent=2, ensure_ascii=False),
                )
                reply = QMessageBox.question(
                    self,
                    t("permission_request_title", self.lang),
                    prompt_text,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Cancel,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    if pc:
                        approved_list = list(intent.get("approved_tools", []))
                        approved_list.append(tool_key)
                        intent["approved_tools"] = approved_list
                        self._run_worker(intent, approved_tools=approved_list)
                    else:
                        self._run_worker(intent, approved=True)
                    return
                self.output.setPlainText("Acción cancelada por el usuario.")
                self.status_label.setText("Cancelado")
                return

            self.status_label.setText("⚡ Respuesta completada  |  Esc para cerrar")
            if resp.get("ok") and "answer" in resp:
                self.output.setMarkdown(resp["answer"])
            else:
                self.output.setPlainText(json.dumps(resp, indent=2, ensure_ascii=False))

        def _open_settings(self) -> None:
            if shutil.which("ariaos-settings"):
                subprocess.Popen(["ariaos-settings"])
            else:
                settings_script = HERE.parent / "settings" / "aria_settings.py"
                if settings_script.exists():
                    subprocess.Popen([sys.executable, str(settings_script)])

    app = QApplication(sys.argv)
    window = AriaCommandBar()
    screen = app.primaryScreen()
    if screen:
        geo = screen.availableGeometry()
        window.move(geo.center().x() - window.width() // 2, geo.top() + geo.height() // 7)
    window.show()
    window.input.setFocus()
    return app.exec()


def main() -> int:
    parser = argparse.ArgumentParser(description="AriaOS Neural HUD")
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
