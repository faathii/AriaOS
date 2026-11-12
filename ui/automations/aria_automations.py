#!/usr/bin/env python3
"""AriaOS Neural Memory & Scheduled Automations Hub — Visual Self-Learning & Task Scheduler."""

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
            QLineEdit,
            QPushButton,
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
            QWidget,
        )
    except ImportError:
        print("PyQt6 is required to launch ariaos-automations.", file=sys.stderr)
        return 1

    class AriaAutomationsWindow(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("AriaOS Neural Memory & Scheduled Automations")
            self.setWindowIcon(QIcon.fromTheme("ariaos-logo"))
            self.resize(940, 650)

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

            # Header
            lbl_t = QLabel("🧠 AriaOS Neural Memory & Scheduled Automations")
            lbl_t.setObjectName("title")
            lbl_s = QLabel(
                "Entrena reglas de lenguaje natural en la memoria sináptica de Aria y programa tareas autónomas del sistema"
            )
            lbl_s.setObjectName("subtitle")
            root.addWidget(lbl_t)
            root.addWidget(lbl_s)

            # Section 1: Teach New Synaptic Rule
            teach_card = QFrame()
            teach_card.setProperty("class", "card")
            teach_lay = QVBoxLayout(teach_card)
            lbl_sec1 = QLabel("✨ Enseñar Nueva Regla o Macro a Aria (Ejecución <0.5 ms)")
            lbl_sec1.setProperty("class", "section_title")
            teach_lay.addWidget(lbl_sec1)

            form_row = QHBoxLayout()
            self.in_trigger = QLineEdit()
            self.in_trigger.setPlaceholderText("Cuando diga... (ej. «modo stream», «preparar trabajo»)")
            self.in_action = QLineEdit()
            self.in_action.setPlaceholderText("Ejecutar acción... (ej. «abre obs y vscodium», «optimizar ram»)")
            btn_teach = QPushButton("➕ Guardar en Memoria Neuronal")
            btn_teach.setProperty("class", "primary")
            btn_teach.clicked.connect(self._teach_new_rule)

            form_row.addWidget(self.in_trigger, 1)
            form_row.addWidget(self.in_action, 2)
            form_row.addWidget(btn_teach)
            teach_lay.addLayout(form_row)

            self.rules_table = QTableWidget(0, 3)
            self.rules_table.setHorizontalHeaderLabels(
                ["Frase Disparadora (Trigger)", "Acción / Macro Asociada", "Usos (Hits)"]
            )
            self.rules_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            self.rules_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.rules_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            teach_lay.addWidget(self.rules_table)

            rule_btns = QHBoxLayout()
            btn_test = QPushButton("⚡ Ejecutar Regla Seleccionada Ahora")
            btn_test.setProperty("class", "primary")
            btn_test.clicked.connect(self._execute_selected_rule)
            btn_del = QPushButton("🗑️ Eliminar Regla Seleccionada")
            btn_del.setProperty("class", "danger")
            btn_del.clicked.connect(self._delete_selected_rule)
            rule_btns.addWidget(btn_test)
            rule_btns.addWidget(btn_del)
            rule_btns.addStretch()
            teach_lay.addLayout(rule_btns)
            root.addWidget(teach_card, 1)

            # Section 2: Scheduled Background Automations
            sched_card = QFrame()
            sched_card.setProperty("class", "card")
            sched_lay = QVBoxLayout(sched_card)
            lbl_sec2 = QLabel("⏱️ Automatizaciones Autónomas en Segundo Plano")
            lbl_sec2.setProperty("class", "section_title")
            sched_lay.addWidget(lbl_sec2)

            self.sched_table = QTableWidget(0, 4)
            self.sched_table.setHorizontalHeaderLabels(["ID", "Tarea Autónoma", "Estado", "Intervalo"])
            self.sched_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            self.sched_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.sched_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            sched_lay.addWidget(self.sched_table)

            sched_ctrl = QHBoxLayout()
            self.combo_interval = QComboBox()
            self.combo_interval.addItems(["15m", "1h", "6h", "24h"])
            btn_enable = QPushButton("✅ Activar / Actualizar Intervalo")
            btn_enable.setProperty("class", "primary")
            btn_enable.clicked.connect(lambda: self._toggle_schedule(True))
            btn_disable = QPushButton("⏸️ Pausar Automatización")
            btn_disable.setProperty("class", "danger")
            btn_disable.clicked.connect(lambda: self._toggle_schedule(False))

            sched_ctrl.addWidget(QLabel("Frecuencia:"))
            sched_ctrl.addWidget(self.combo_interval)
            sched_ctrl.addWidget(btn_enable)
            sched_ctrl.addWidget(btn_disable)
            sched_ctrl.addStretch()
            sched_lay.addLayout(sched_ctrl)
            root.addWidget(sched_card, 1)

            self.status_lbl = QLabel("Memoria sináptica cargada")
            self.status_lbl.setObjectName("subtitle")
            root.addWidget(self.status_lbl)

            self._refresh_data()

        def _refresh_data(self) -> None:
            try:
                resp = client.call_tool("os-automation", "list_automations", {}, approved=True)
                if not resp.get("ok"):
                    return
                res = resp.get("result", {})
                mem = res.get("neural_memory", {})
                rules: list[dict[str, Any]] = mem.get("rules", [])
                self.rules_table.setRowCount(len(rules))
                for idx, r in enumerate(rules):
                    self.rules_table.setItem(idx, 0, QTableWidgetItem(str(r.get("trigger", ""))))
                    action = r.get("target_prompt") or r.get("action") or ""
                    self.rules_table.setItem(idx, 1, QTableWidgetItem(str(action)))
                    self.rules_table.setItem(idx, 2, QTableWidgetItem(str(r.get("hits", 0))))

                tasks: list[dict[str, Any]] = res.get("scheduled_tasks", [])
                self.sched_table.setRowCount(len(tasks))
                for idx, t in enumerate(tasks):
                    self.sched_table.setItem(idx, 0, QTableWidgetItem(str(t.get("id", ""))))
                    name = f"{t.get('icon', '⚡')} {t.get('name', '')}"
                    self.sched_table.setItem(idx, 1, QTableWidgetItem(name))
                    state = "🟢 ACTIVA" if t.get("enabled") else "⚪ PAUSADA"
                    self.sched_table.setItem(idx, 2, QTableWidgetItem(state))
                    self.sched_table.setItem(idx, 3, QTableWidgetItem(str(t.get("interval", "1h"))))
            except Exception as exc:
                self.status_lbl.setText(f"Error cargando automatizaciones: {exc}")

        def _teach_new_rule(self) -> None:
            trig = self.in_trigger.text().strip()
            act = self.in_action.text().strip()
            if not trig or not act:
                return
            try:
                client.call_tool(
                    "os-automation",
                    "teach_rule",
                    {"trigger": trig, "action": act},
                    approved=True,
                )
                self.in_trigger.clear()
                self.in_action.clear()
                self.status_lbl.setText(f"🧠 Regla aprendida: «{trig}» -> «{act}»")
                self._refresh_data()
            except Exception as exc:
                self.status_lbl.setText(f"Error guardando regla: {exc}")

        def _execute_selected_rule(self) -> None:
            row = self.rules_table.currentRow()
            if row < 0:
                return
            trig_item = self.rules_table.item(row, 0)
            if not trig_item:
                return
            trig = trig_item.text()
            try:
                resp = client.ask(trig)
                ans = resp.get("answer", "Ejecutado")
                first_line = ans.splitlines()[0] if ans else "Completado"
                self.status_lbl.setText(f"⚡ Resultado: {first_line}")
                self._refresh_data()
            except Exception as exc:
                self.status_lbl.setText(f"Error ejecutando regla: {exc}")

        def _delete_selected_rule(self) -> None:
            row = self.rules_table.currentRow()
            if row < 0:
                return
            trig_item = self.rules_table.item(row, 0)
            if not trig_item:
                return
            trig = trig_item.text()
            try:
                client.call_tool("os-automation", "delete_rule", {"trigger": trig}, approved=True)
                self.status_lbl.setText(f"🗑️ Regla «{trig}» eliminada.")
                self._refresh_data()
            except Exception as exc:
                self.status_lbl.setText(f"Error eliminando regla: {exc}")

        def _toggle_schedule(self, enabled: bool) -> None:
            row = self.sched_table.currentRow()
            if row < 0:
                return
            id_item = self.sched_table.item(row, 0)
            if not id_item:
                return
            task_id = id_item.text()
            interval = self.combo_interval.currentText()
            try:
                client.call_tool(
                    "os-automation",
                    "configure_schedule",
                    {"task_id": task_id, "enabled": enabled, "interval": interval},
                    approved=True,
                )
                self.status_lbl.setText(
                    f"⏱️ Tarea '{task_id}' actualizada (Activa={enabled}, Intervalo={interval})"
                )
                self._refresh_data()
            except Exception as exc:
                self.status_lbl.setText(f"Error configurando tarea: {exc}")

    app = QApplication(sys.argv)
    win = AriaAutomationsWindow()
    win.show()
    return app.exec()


def main() -> int:
    parser = argparse.ArgumentParser(description="AriaOS Neural Memory & Scheduled Automations")
    parser.add_argument("--socket", help="Override aria-daemon socket path")
    parser.add_argument("--check", action="store_true", help="Validate imports and exit")
    args = parser.parse_args()

    if args.check:
        print(json.dumps({"ok": True, "component": "ariaos-automations"}))
        return 0

    client = AriaDaemonClient(args.socket)
    return launch_gui(client)


if __name__ == "__main__":
    raise SystemExit(main())

