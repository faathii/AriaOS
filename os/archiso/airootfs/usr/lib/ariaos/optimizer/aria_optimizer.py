#!/usr/bin/env python3
"""AriaOS Boot Analyzer & Deep System Optimizer — Cyber Obsidian Edition."""

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
            QFrame,
            QHBoxLayout,
            QHeaderView,
            QLabel,
            QPushButton,
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
            QWidget,
        )
    except ImportError:
        print("PyQt6 is required to launch ariaos-optimizer.", file=sys.stderr)
        return 1

    class AriaOptimizerWindow(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("AriaOS Boot Analyzer & Deep System Optimizer")
            self.setWindowIcon(QIcon.fromTheme("ariaos-logo"))
            self.resize(940, 640)
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
                QLabel.section_title {
                    color: #00f0ff;
                    font-size: 14px;
                    font-weight: bold;
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

            header = QHBoxLayout()
            col = QVBoxLayout()
            lbl_t = QLabel("🧹 AriaOS Boot Analyzer & Deep System Optimizer")
            lbl_t.setObjectName("title")
            self.lbl_sub = QLabel("Análisis de arranque del Kernel/systemd y limpieza profunda de cachés y logs")
            self.lbl_sub.setObjectName("subtitle")
            col.addWidget(lbl_t)
            col.addWidget(self.lbl_sub)
            header.addLayout(col)
            header.addStretch()

            btn_clean = QPushButton("🚀 Ejecutar Limpieza Profunda Ahora")
            btn_clean.setProperty("class", "primary")
            btn_clean.clicked.connect(self._run_deep_clean)
            header.addWidget(btn_clean)
            root.addLayout(header)

            # Boot time card
            boot_card = QFrame()
            boot_card.setProperty("class", "card")
            b_lay = QVBoxLayout(boot_card)
            self.lbl_boot = QLabel("⏱️ Tiempo de Arranque (systemd-analyze)")
            self.lbl_boot.setProperty("class", "section_title")
            b_lay.addWidget(self.lbl_boot)

            self.boot_table = QTableWidget(0, 3)
            self.boot_table.setHorizontalHeaderLabels(["Servicio / Unidad", "Tiempo / Latencia", "Recomendación"])
            self.boot_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            self.boot_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            b_lay.addWidget(self.boot_table)
            root.addWidget(boot_card, 1)

            # Junk data card
            junk_card = QFrame()
            junk_card.setProperty("class", "card")
            j_lay = QVBoxLayout(junk_card)
            self.lbl_junk = QLabel("🗑️ Cachés, Logs y Archivos Temporales Recuperables")
            self.lbl_junk.setProperty("class", "section_title")
            j_lay.addWidget(self.lbl_junk)

            self.junk_table = QTableWidget(0, 3)
            self.junk_table.setHorizontalHeaderLabels(["Categoría", "Descripción", "Espacio Recuperable (MB)"])
            self.junk_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            self.junk_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            j_lay.addWidget(self.junk_table)
            root.addWidget(junk_card, 1)

            self.status_lbl = QLabel("Optimizador listo")
            self.status_lbl.setObjectName("subtitle")
            root.addWidget(self.status_lbl)

            self._refresh()

        def _refresh(self) -> None:
            try:
                b_resp = client.call_tool("os-optimizer", "analyze_boot_time", {}, approved=True)
                if b_resp.get("ok"):
                    res = b_resp.get("result", {})
                    self.lbl_boot.setText(f"⏱️ {res.get('boot_summary', 'Boot Analyzer')}")
                    units: list[dict[str, Any]] = res.get("slowest_units", [])
                    self.boot_table.setRowCount(len(units))
                    for idx, u in enumerate(units):
                        self.boot_table.setItem(idx, 0, QTableWidgetItem(str(u.get("unit", ""))))
                        t_val = str(u.get("time") or f"{u.get('time_ms', 0)} ms")
                        self.boot_table.setItem(idx, 1, QTableWidgetItem(t_val))
                        self.boot_table.setItem(idx, 2, QTableWidgetItem(str(u.get("recommendation", ""))))

                j_resp = client.call_tool("os-optimizer", "scan_junk_data", {}, approved=True)
                if j_resp.get("ok"):
                    j_res = j_resp.get("result", {})
                    tot = j_res.get("total_reclaimable_mb", 0)
                    self.lbl_junk.setText(f"🗑️ Espacio Total Recuperable: {tot} MB")
                    cats: list[dict[str, Any]] = j_res.get("categories", [])
                    self.junk_table.setRowCount(len(cats))
                    for idx, c in enumerate(cats):
                        self.junk_table.setItem(idx, 0, QTableWidgetItem(str(c.get("id", ""))))
                        self.junk_table.setItem(idx, 1, QTableWidgetItem(str(c.get("label", ""))))
                        self.junk_table.setItem(idx, 2, QTableWidgetItem(str(c.get("size_mb", ""))))
            except Exception as exc:
                self.status_lbl.setText(f"Esperando a aria-daemon: {exc}")

        def _run_deep_clean(self) -> None:
            try:
                resp = client.call_tool(
                    "os-optimizer",
                    "deep_clean_system",
                    {"targets": ["user_cache", "journal_logs", "pacman_cache", "tmp_files"]},
                    approved=True,
                )
                if resp.get("ok"):
                    res = resp.get("result", {})
                    self.status_lbl.setText(
                        f"🧹 Limpieza completada: {res.get('freed_mb')} MB liberados ({', '.join(res.get('targets_cleaned', []))})"
                    )
                self._refresh()
            except Exception as exc:
                self.status_lbl.setText(f"Error en limpieza: {exc}")

    app = QApplication(sys.argv)
    win = AriaOptimizerWindow()
    win.show()
    return app.exec()


def main() -> int:
    parser = argparse.ArgumentParser(description="AriaOS Boot Analyzer & Deep System Optimizer")
    parser.add_argument("--socket", help="Override aria-daemon socket path")
    parser.add_argument("--check", action="store_true", help="Validate imports and exit")
    args = parser.parse_args()

    if args.check:
        print(json.dumps({"ok": True, "component": "ariaos-optimizer"}))
        return 0

    client = AriaDaemonClient(args.socket)
    return launch_gui(client)


if __name__ == "__main__":
    raise SystemExit(main())

