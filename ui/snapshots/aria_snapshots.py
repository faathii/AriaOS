#!/usr/bin/env python3
"""AriaOS Time Machine & System Snapshots — Cyber Obsidian Edition."""

from __future__ import annotations

import argparse
import datetime
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
            QLineEdit,
            QPushButton,
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
            QWidget,
        )
    except ImportError:
        print("PyQt6 is required to launch ariaos-snapshots.", file=sys.stderr)
        return 1

    class AriaSnapshotsWindow(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("AriaOS Time Machine — Puntos de Restauración y Snapshots")
            self.setWindowIcon(QIcon.fromTheme("ariaos-logo"))
            self.resize(940, 620)
            self.setStyleSheet(
                """
                QWidget {
                    background-color: #070a12;
                    color: #e2e8f0;
                    font-family: "Noto Sans", sans-serif;
                    font-size: 13px;
                }
                QFrame.card {
                    background-color: #0c1222;
                    border: 1px solid #1e293b;
                    border-radius: 12px;
                    padding: 12px;
                }
                QLabel#title {
                    color: #00f0ff;
                    font-size: 20px;
                    font-weight: bold;
                }
                QLabel#subtitle {
                    color: #94a3b8;
                    font-size: 12px;
                }
                QLineEdit, QComboBox {
                    background-color: #0d1424;
                    border: 1px solid #1e3a5f;
                    border-radius: 8px;
                    padding: 8px 12px;
                    color: #ffffff;
                }
                QPushButton.primary {
                    background-color: #0d1b33;
                    border: 1px solid #00f0ff;
                    border-radius: 8px;
                    padding: 8px 14px;
                    color: #00f0ff;
                    font-weight: bold;
                }
                QPushButton.primary:hover {
                    background-color: #00f0ff;
                    color: #070a12;
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
                    color: #070a12;
                }
                QTableWidget {
                    background-color: #090d18;
                    border: 1px solid #162238;
                    border-radius: 8px;
                    gridline-color: #162238;
                }
                QHeaderView::section {
                    background-color: #0c1222;
                    color: #00f0ff;
                    padding: 6px;
                    border: none;
                    font-weight: bold;
                }
                """
            )

            root = QVBoxLayout(self)
            root.setContentsMargins(18, 18, 18, 18)
            root.setSpacing(12)

            lbl_t = QLabel("⏪ AriaOS Time Machine & System Snapshots")
            lbl_t.setObjectName("title")
            self.lbl_sub = QLabel(
                "Puntos de restauración instantáneos (Btrfs / Timeshift / Configuración Neuronal AriaOS)"
            )
            self.lbl_sub.setObjectName("subtitle")
            root.addWidget(lbl_t)
            root.addWidget(self.lbl_sub)

            card = QFrame()
            card.setProperty("class", "card")
            c_lay = QVBoxLayout(card)

            form = QHBoxLayout()
            self.in_label = QLineEdit()
            self.in_label.setPlaceholderText("Etiqueta del punto de restauración (ej. Antes de actualizar drivers GPU)")
            self.combo_scope = QComboBox()
            self.combo_scope.addItems(["config", "full_system"])

            btn_create = QPushButton("📸 Crear Snapshot Ahora")
            btn_create.setProperty("class", "primary")
            btn_create.clicked.connect(self._create_snapshot)

            btn_restore = QPushButton("⏪ Restaurar Seleccionado")
            btn_restore.setProperty("class", "primary")
            btn_restore.clicked.connect(self._restore_selected)

            btn_del = QPushButton("🗑️ Eliminar")
            btn_del.setProperty("class", "danger")
            btn_del.clicked.connect(self._delete_selected)

            form.addWidget(self.in_label, 2)
            form.addWidget(self.combo_scope)
            form.addWidget(btn_create)
            form.addWidget(btn_restore)
            form.addWidget(btn_del)
            c_lay.addLayout(form)

            self.table = QTableWidget(0, 6)
            self.table.setHorizontalHeaderLabels(
                ["ID Snapshot", "Descripción", "Alcance", "Motor Backend", "Tamaño (MB)", "Fecha"]
            )
            self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            c_lay.addWidget(self.table)
            root.addWidget(card, 1)

            self.status_lbl = QLabel("Listo • Protección atómica de configuraciones activa")
            self.status_lbl.setObjectName("subtitle")
            root.addWidget(self.status_lbl)

            self._refresh()

        def _refresh(self) -> None:
            try:
                resp = client.call_tool("os-snapshots", "list_snapshots", {}, approved=True)
                if resp.get("ok"):
                    res = resp.get("result", {})
                    snaps: list[dict[str, Any]] = res.get("snapshots", [])
                    self.table.setRowCount(len(snaps))
                    for idx, s in enumerate(snaps):
                        self.table.setItem(idx, 0, QTableWidgetItem(str(s.get("id", ""))))
                        self.table.setItem(idx, 1, QTableWidgetItem(str(s.get("label", ""))))
                        self.table.setItem(idx, 2, QTableWidgetItem(str(s.get("scope", "config"))))
                        self.table.setItem(idx, 3, QTableWidgetItem(str(s.get("backend", ""))))
                        self.table.setItem(idx, 4, QTableWidgetItem(str(s.get("size_mb", 0.5))))
                        ts = int(s.get("created_at") or 0)
                        dt = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else "-"
                        self.table.setItem(idx, 5, QTableWidgetItem(dt))
            except Exception as exc:
                self.status_lbl.setText(f"Esperando a aria-daemon: {exc}")

        def _create_snapshot(self) -> None:
            lbl = self.in_label.text().strip() or "Snapshot manual desde AriaOS Time Machine"
            scope = self.combo_scope.currentText()
            try:
                resp = client.call_tool(
                    "os-snapshots",
                    "create_snapshot",
                    {"label": lbl, "scope": scope},
                    approved=True,
                )
                if resp.get("ok"):
                    snap = resp.get("result", {}).get("snapshot", {})
                    self.status_lbl.setText(f"✅ Snapshot '{snap.get('id')}' creado correctamente.")
                    self.in_label.clear()
                self._refresh()
            except Exception as exc:
                self.status_lbl.setText(f"Error creando snapshot: {exc}")

        def _restore_selected(self) -> None:
            row = self.table.currentRow()
            if row < 0:
                return
            item = self.table.item(row, 0)
            if not item:
                return
            snap_id = item.text()
            try:
                resp = client.call_tool(
                    "os-snapshots",
                    "restore_snapshot",
                    {"snapshot_id": snap_id, "dry_run": False},
                    approved=True,
                )
                if resp.get("ok"):
                    files = resp.get("result", {}).get("restored_files", [])
                    self.status_lbl.setText(
                        f"⏪ Restaurado '{snap_id}' ({len(files)} archivos de configuración recuperados)."
                    )
            except Exception as exc:
                self.status_lbl.setText(f"Error restaurando snapshot: {exc}")

        def _delete_selected(self) -> None:
            row = self.table.currentRow()
            if row < 0:
                return
            item = self.table.item(row, 0)
            if not item:
                return
            snap_id = item.text()
            try:
                client.call_tool("os-snapshots", "delete_snapshot", {"snapshot_id": snap_id}, approved=True)
                self.status_lbl.setText(f"🗑️ Snapshot '{snap_id}' eliminado.")
                self._refresh()
            except Exception as exc:
                self.status_lbl.setText(f"Error eliminando snapshot: {exc}")

    app = QApplication(sys.argv)
    win = AriaSnapshotsWindow()
    win.show()
    return app.exec()


def main() -> int:
    parser = argparse.ArgumentParser(description="AriaOS Time Machine & System Snapshots")
    parser.add_argument("--socket", help="Override aria-daemon socket path")
    parser.add_argument("--check", action="store_true", help="Validate imports and exit")
    args = parser.parse_args()

    if args.check:
        print(json.dumps({"ok": True, "component": "ariaos-snapshots"}))
        return 0

    client = AriaDaemonClient(args.socket)
    return launch_gui(client)


if __name__ == "__main__":
    raise SystemExit(main())
