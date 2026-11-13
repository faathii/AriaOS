#!/usr/bin/env python3
"""AriaOS Neural Clipboard & Smart Transformer — Cyber Obsidian Edition."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
COMMAND_BAR_DIR = HERE.parent / "command-bar"
if str(COMMAND_BAR_DIR) not in sys.path:
    sys.path.insert(0, str(COMMAND_BAR_DIR))
SYSTEM_CB_DIR = Path("/usr/lib/ariaos/command-bar")
if SYSTEM_CB_DIR.exists() and str(SYSTEM_CB_DIR) not in sys.path:
    sys.path.insert(0, str(SYSTEM_CB_DIR))

from aria_ipc import AriaDaemonClient  # noqa: E402


def launch_gui(client: AriaDaemonClient) -> int:
    try:
        from PyQt6.QtGui import QIcon
        from PyQt6.QtWidgets import (
            QApplication,
            QComboBox,
            QFrame,
            QHBoxLayout,
            QHeaderView,
            QLabel,
            QPushButton,
            QTableWidget,
            QTableWidgetItem,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except ImportError:
        print("PyQt6 is required to launch ariaos-clipboard.", file=sys.stderr)
        return 1

    class AriaClipboardWindow(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("AriaOS Neural Clipboard & Smart Transformer")
            self.setWindowIcon(QIcon.fromTheme("ariaos-logo"))
            self.resize(920, 620)
            self.setStyleSheet(
                """
                QWidget {
                    background-color: #0d1117;
                    color: #e2e8f0;
                    font-family: "Noto Sans", sans-serif;
                    font-size: 13px;
                }
                QFrame.card {
                    background-color: #161b22;
                    border: 1px solid #30363d;
                    border-radius: 12px;
                    padding: 12px;
                }
                QLabel#title {
                    color: #3b82f6;
                    font-size: 20px;
                    font-weight: bold;
                }
                QLabel#subtitle {
                    color: #94a3b8;
                    font-size: 12px;
                }
                QComboBox, QTextEdit {
                    background-color: #161b22;
                    border: 1px solid #30363d;
                    border-radius: 8px;
                    padding: 8px 12px;
                    color: #ffffff;
                }
                QPushButton.primary {
                    background-color: #0d1b33;
                    border: 1px solid #3b82f6;
                    border-radius: 8px;
                    padding: 8px 14px;
                    color: #3b82f6;
                    font-weight: bold;
                }
                QPushButton.primary:hover {
                    background-color: #3b82f6;
                    color: #0d1117;
                }
                QPushButton.danger {
                    background-color: #2a0f18;
                    border: 1px solid #ff2a85;
                    border-radius: 8px;
                    padding: 8px 14px;
                    color: #ff2a85;
                    font-weight: bold;
                }
                QPushButton.danger:hover {
                    background-color: #ff2a85;
                    color: #0d1117;
                }
                QTableWidget {
                    background-color: #161b22;
                    border: 1px solid #30363d;
                    border-radius: 8px;
                    gridline-color: #30363d;
                }
                QHeaderView::section {
                    background-color: #161b22;
                    color: #3b82f6;
                    padding: 6px;
                    border: none;
                    font-weight: bold;
                }
                """
            )

            root = QVBoxLayout(self)
            root.setContentsMargins(18, 18, 18, 18)
            root.setSpacing(12)

            header = QHBoxLayout()
            col = QVBoxLayout()
            lbl_t = QLabel("📋 AriaOS Neural Clipboard & Smart Transformer")
            lbl_t.setObjectName("title")
            lbl_sub = QLabel(
                "Historial semántico de fragmentos copiados (JSON, URL, código, bash) y transformación en 1 clic"
            )
            lbl_sub.setObjectName("subtitle")
            col.addWidget(lbl_t)
            col.addWidget(lbl_sub)
            header.addLayout(col)
            header.addStretch()

            btn_clear = QPushButton("🧹 Vaciar Portapapeles")
            btn_clear.setProperty("class", "danger")
            btn_clear.clicked.connect(self._clear_all)
            header.addWidget(btn_clear)
            root.addLayout(header)

            card = QFrame()
            card.setProperty("class", "card")
            c_lay = QVBoxLayout(card)

            self.table = QTableWidget(0, 2)
            self.table.setHorizontalHeaderLabels(["Tipo Semántico", "Contenido Copiado"])
            self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            self.table.itemSelectionChanged.connect(self._on_select)
            c_lay.addWidget(self.table)

            t_row = QHBoxLayout()
            self.combo_op = QComboBox()
            self.combo_op.addItems(
                [
                    "format_json",
                    "extract_urls",
                    "base64_encode",
                    "base64_decode",
                    "sha256_hash",
                    "uppercase",
                    "lowercase",
                ]
            )
            btn_transform = QPushButton("✨ Transformar Fragmento")
            btn_transform.setProperty("class", "primary")
            btn_transform.clicked.connect(self._transform)

            btn_copy = QPushButton("📋 Volver a Copiar")
            btn_copy.setProperty("class", "primary")
            btn_copy.clicked.connect(self._copy_editor)

            t_row.addWidget(self.combo_op, 1)
            t_row.addWidget(btn_transform)
            t_row.addWidget(btn_copy)
            c_lay.addLayout(t_row)

            self.editor = QTextEdit()
            self.editor.setPlaceholderText("Selecciona un elemento del historial o escribe texto para transformar...")
            c_lay.addWidget(self.editor)
            root.addWidget(card, 1)

            self.status_lbl = QLabel("Portapapeles neuronal activo")
            self.status_lbl.setObjectName("subtitle")
            root.addWidget(self.status_lbl)

            self._refresh()

        def _refresh(self) -> None:
            try:
                resp = client.call_tool("os-clipboard", "clipboard_history", {"limit": 25}, approved=True)
                if resp.get("ok"):
                    entries: list[dict[str, Any]] = resp.get("result", {}).get("entries", [])
                    self.table.setRowCount(len(entries))
                    for idx, e in enumerate(entries):
                        self.table.setItem(idx, 0, QTableWidgetItem(str(e.get("kind", "text"))))
                        self.table.setItem(idx, 1, QTableWidgetItem(str(e.get("text", ""))))
            except Exception as exc:
                self.status_lbl.setText(f"Esperando a aria-daemon: {exc}")

        def _on_select(self) -> None:
            row = self.table.currentRow()
            if row < 0:
                return
            item = self.table.item(row, 1)
            if item:
                self.editor.setPlainText(item.text())

        def _transform(self) -> None:
            op = self.combo_op.currentText()
            txt = self.editor.toPlainText().strip()
            try:
                resp = client.call_tool(
                    "os-clipboard",
                    "transform_clipboard",
                    {"operation": op, "input_text": txt},
                    approved=True,
                )
                if resp.get("ok"):
                    out = resp.get("result", {}).get("output", "")
                    self.editor.setPlainText(str(out))
                    self.status_lbl.setText(f"✨ Transformación '{op}' aplicada y copiada al portapapeles.")
            except Exception as exc:
                self.status_lbl.setText(f"Error transformando: {exc}")

        def _copy_editor(self) -> None:
            txt = self.editor.toPlainText().strip()
            if not txt:
                return
            try:
                client.call_tool("os-clipboard", "copy_to_clipboard", {"text": txt}, approved=True)
                self.status_lbl.setText("📋 Copiado al portapapeles del sistema y guardado en el historial.")
                self._refresh()
            except Exception as exc:
                self.status_lbl.setText(f"Error copiando: {exc}")

        def _clear_all(self) -> None:
            try:
                client.call_tool("os-clipboard", "clear_clipboard", {}, approved=True)
                self.editor.clear()
                self.status_lbl.setText("🧹 Portapapeles vaciado de forma segura.")
                self._refresh()
            except Exception as exc:
                self.status_lbl.setText(f"Error vaciando portapapeles: {exc}")

    app = QApplication(sys.argv)
    win = AriaClipboardWindow()
    win.show()
    return app.exec()


def main() -> int:
    parser = argparse.ArgumentParser(description="AriaOS Neural Clipboard & Smart Transformer")
    parser.add_argument("--socket", help="Override aria-daemon socket path")
    parser.add_argument("--check", action="store_true", help="Validate imports and exit")
    args = parser.parse_args()

    if args.check:
        print(json.dumps({"ok": True, "component": "ariaos-clipboard"}))
        return 0

    client = AriaDaemonClient(args.socket)
    return launch_gui(client)


if __name__ == "__main__":
    raise SystemExit(main())

