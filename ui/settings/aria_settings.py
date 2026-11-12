#!/usr/bin/env python3
"""AriaOS AI Settings Panel: configure language, local LLM, security policy, and audit log."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
SDK_PATH = REPO_ROOT / "core" / "sdk" / "python"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))
SYSTEM_SDK = Path("/usr/lib/ariaos/core/sdk/python")
if SYSTEM_SDK.exists() and str(SYSTEM_SDK) not in sys.path:
    sys.path.insert(0, str(SYSTEM_SDK))

from aria_sdk import (  # noqa: E402
    DEFAULT_CONFIG,
    SUPPORTED_LANGUAGES,
    get_current_language,
    load_ariaos_config,
    save_ariaos_config,
    t,
)


def _list_ollama_models(endpoint: str) -> List[str]:
    url = f"{endpoint.rstrip('/')}/api/tags"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AriaOS-Settings"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    except Exception:
        return []


def _read_audit_entries(max_lines: int = 80) -> List[Dict[str, Any]]:
    audit_file = Path(os.environ.get("ARIAOS_AUDIT_LOG", "/tmp/ariaos-audit.jsonl"))
    if not audit_file.exists():
        return []
    entries = []
    try:
        lines = audit_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        for raw in lines[-max_lines:]:
            if not raw.strip():
                continue
            try:
                entries.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    except OSError:
        pass
    return list(reversed(entries))


def main() -> int:
    parser = argparse.ArgumentParser(description="AriaOS AI Settings Panel")
    parser.add_argument("--check", action="store_true", help="Self-check imports and exit")
    parser.add_argument("--get", help="Print configuration key value")
    parser.add_argument("--set", nargs=2, metavar=("KEY", "VALUE"), help="Set configuration key")
    args = parser.parse_args()

    if args.check:
        print(json.dumps({
            "ok": True,
            "app": "ariaos-settings",
            "languages": list(SUPPORTED_LANGUAGES.keys()),
            "config": load_ariaos_config(),
        }))
        return 0

    if args.get:
        cfg = load_ariaos_config()
        print(cfg.get(args.get, ""))
        return 0

    if args.set:
        k, v = args.set
        cfg = load_ariaos_config()
        try:
            parsed_v = json.loads(v)
        except Exception:
            parsed_v = v
        cfg[k] = parsed_v
        p = save_ariaos_config(cfg)
        print(f"Updated {k} -> {parsed_v} in {p}")
        return 0

    try:
        from PyQt6.QtCore import Qt, QThread, pyqtSignal
        from PyQt6.QtGui import QFont, QIcon, QPixmap
        from PyQt6.QtWidgets import (
            QApplication,
            QButtonGroup,
            QCheckBox,
            QComboBox,
            QFormLayout,
            QFrame,
            QHBoxLayout,
            QHeaderView,
            QLabel,
            QLineEdit,
            QMessageBox,
            QPushButton,
            QRadioButton,
            QSlider,
            QTabWidget,
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
            QWidget,
        )
    except ImportError:
        print("AriaOS Settings: PyQt6 not available. Install python-pyqt6.", file=sys.stderr)
        return 1

    class OllamaProbeThread(QThread):
        models_ready = pyqtSignal(list, bool)

        def __init__(self, endpoint: str) -> None:
            super().__init__()
            self.endpoint = endpoint

        def run(self) -> None:
            models = _list_ollama_models(self.endpoint)
            self.models_ready.emit(models, len(models) > 0)

    class SettingsWindow(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.cfg = load_ariaos_config()
            self.current_lang = get_current_language()
            self._probe_thread: OllamaProbeThread | None = None

            self.setWindowTitle(t("settings_title", self.current_lang))
            self.setWindowIcon(QIcon.fromTheme("ariaos-logo"))
            self.resize(780, 560)
            self._apply_style()
            self._init_ui()

        def _apply_style(self) -> None:
            self.setStyleSheet("""
                QWidget {
                    background-color: #0b0f19;
                    color: #f1f5f9;
                    font-family: "Noto Sans", sans-serif;
                    font-size: 13px;
                }
                QTabWidget::pane {
                    border: 1px solid #1e293b;
                    background: #111827;
                    border-radius: 8px;
                    padding: 12px;
                }
                QTabBar::tab {
                    background: #0f172a;
                    color: #94a3b8;
                    padding: 8px 18px;
                    border-top-left-radius: 6px;
                    border-top-right-radius: 6px;
                    margin-right: 3px;
                }
                QTabBar::tab:selected {
                    background: #1e293b;
                    color: #38bdf8;
                    font-weight: bold;
                }
                QLineEdit, QComboBox {
                    background-color: #1a2234;
                    border: 1px solid #334155;
                    border-radius: 6px;
                    padding: 6px 10px;
                    color: #ffffff;
                }
                QLineEdit:focus, QComboBox:focus {
                    border-color: #38bdf8;
                }
                QPushButton {
                    background-color: #1e293b;
                    color: #ffffff;
                    border: 1px solid #334155;
                    border-radius: 6px;
                    padding: 7px 14px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #2563eb;
                    border-color: #38bdf8;
                }
                QPushButton#primary {
                    background-color: #2563eb;
                    border-color: #3b82f6;
                    font-weight: bold;
                }
                QPushButton#primary:hover {
                    background-color: #1d4ed8;
                }
                QTableWidget {
                    background-color: #0e121c;
                    border: 1px solid #1e293b;
                    border-radius: 6px;
                    gridline-color: #1e293b;
                }
                QHeaderView::section {
                    background-color: #1a2234;
                    color: #94a3b8;
                    padding: 4px;
                    border: none;
                    font-weight: bold;
                }
            """)

        def _init_ui(self) -> None:
            root = QVBoxLayout(self)
            root.setContentsMargins(16, 14, 16, 14)
            root.setSpacing(12)

            # Header
            header = QHBoxLayout()
            logo_lbl = QLabel()
            pix = QPixmap("/usr/share/pixmaps/ariaos-logo.png")
            if pix.isNull():
                pix = QPixmap("c:/Users/hamza/Desktop/AriaOS/assets/branding/ariaos-logo.png")
            if not pix.isNull():
                logo_lbl.setPixmap(pix.scaled(44, 44, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            header.addWidget(logo_lbl)

            title_box = QVBoxLayout()
            self.title_lbl = QLabel(t("settings_title", self.current_lang))
            self.title_lbl.setStyleSheet("font-size: 19px; font-weight: bold; color: #38bdf8;")
            self.sub_lbl = QLabel("AriaOS AI Subsystem Control Panel")
            self.sub_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
            title_box.addWidget(self.title_lbl)
            title_box.addWidget(self.sub_lbl)
            header.addLayout(title_box)
            header.addStretch()
            root.addLayout(header)

            # Tab Widget
            self.tabs = QTabWidget()
            self.tabs.addTab(self._tab_general(), t("tab_general", self.current_lang))
            self.tabs.addTab(self._tab_model(), t("tab_model", self.current_lang))
            self.tabs.addTab(self._tab_security(), t("tab_security", self.current_lang))
            self.tabs.addTab(self._tab_audit(), t("tab_audit", self.current_lang))
            root.addWidget(self.tabs)

            # Footer
            footer = QHBoxLayout()
            self.status_feedback = QLabel("")
            self.status_feedback.setStyleSheet("color: #10b981; font-weight: 500;")
            footer.addWidget(self.status_feedback)
            footer.addStretch()

            self.btn_save = QPushButton(t("btn_save", self.current_lang), objectName="primary")
            self.btn_save.clicked.connect(self._on_save)
            footer.addWidget(self.btn_save)

            self.btn_close = QPushButton(t("btn_close", self.current_lang))
            self.btn_close.clicked.connect(self.close)
            footer.addWidget(self.btn_close)
            root.addLayout(footer)

        def _tab_general(self) -> QWidget:
            w = QWidget()
            layout = QVBoxLayout(w)
            layout.setSpacing(14)

            form = QFormLayout()
            form.setSpacing(12)

            self.lang_combo = QComboBox()
            for code, name in SUPPORTED_LANGUAGES.items():
                self.lang_combo.addItem(f"{name} ({code})", code)
            curr_idx = self.lang_combo.findData(self.cfg.get("language", "es"))
            if curr_idx >= 0:
                self.lang_combo.setCurrentIndex(curr_idx)
            self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
            form.addRow(t("language_label", self.current_lang), self.lang_combo)

            self.hotkey_combo = QComboBox()
            self.hotkey_combo.setEditable(True)
            self.hotkey_combo.addItems(["Alt+Space", "Meta+Space", "Ctrl+Space", "Ctrl+Alt+A"])
            self.hotkey_combo.setCurrentText(self.cfg.get("hotkey", "Alt+Space"))
            form.addRow(t("hotkey_label", self.current_lang), self.hotkey_combo)

            layout.addLayout(form)

            self.autostart_chk = QCheckBox(t("autostart_label", self.current_lang))
            self.autostart_chk.setChecked(True)
            layout.addWidget(self.autostart_chk)

            layout.addStretch()
            return w

        def _tab_model(self) -> QWidget:
            w = QWidget()
            layout = QVBoxLayout(w)
            layout.setSpacing(14)

            form = QFormLayout()
            form.setSpacing(10)

            endpoint_box = QHBoxLayout()
            self.endpoint_edit = QLineEdit(self.cfg.get("ollama_url", "http://127.0.0.1:11434"))
            endpoint_box.addWidget(self.endpoint_edit)
            btn_test = QPushButton(t("btn_test_ollama", self.current_lang))
            btn_test.clicked.connect(self._on_test_ollama)
            endpoint_box.addWidget(btn_test)
            form.addRow(t("ollama_url_label", self.current_lang), endpoint_box)

            model_box = QHBoxLayout()
            self.model_combo = QComboBox()
            self.model_combo.setEditable(True)
            self.model_combo.addItems(["qwen2.5:3b", "llama3.2:3b", "deepseek-r1:1.5b", "mistral:7b"])
            self.model_combo.setCurrentText(self.cfg.get("model", "qwen2.5:3b"))
            model_box.addWidget(self.model_combo)
            btn_pull = QPushButton(t("btn_pull_model", self.current_lang))
            btn_pull.clicked.connect(self._on_pull_model)
            model_box.addWidget(btn_pull)
            form.addRow(t("model_select_label", self.current_lang), model_box)

            self.ctx_combo = QComboBox()
            self.ctx_combo.addItems(["4096", "8192", "16384"])
            self.ctx_combo.setCurrentText(str(self.cfg.get("num_ctx", 8192)))
            form.addRow(t("context_size_label", self.current_lang), self.ctx_combo)

            temp_box = QHBoxLayout()
            self.temp_slider = QSlider(Qt.Orientation.Horizontal)
            self.temp_slider.setRange(0, 100)
            initial_temp = int(float(self.cfg.get("temperature", 0.3)) * 100)
            self.temp_slider.setValue(initial_temp)
            self.temp_lbl = QLabel(f"{initial_temp / 100.0:.2f}")
            self.temp_slider.valueChanged.connect(lambda v: self.temp_lbl.setText(f"{v / 100.0:.2f}"))
            temp_box.addWidget(self.temp_slider)
            temp_box.addWidget(self.temp_lbl)
            form.addRow(t("temperature_label", self.current_lang), temp_box)

            layout.addLayout(form)
            layout.addStretch()
            return w

        def _tab_security(self) -> QWidget:
            w = QWidget()
            layout = QVBoxLayout(w)
            layout.setSpacing(12)

            sec_lbl = QLabel(t("approval_mode_label", self.current_lang))
            sec_lbl.setStyleSheet("font-weight: bold; color: #38bdf8;")
            layout.addWidget(sec_lbl)

            self.radio_interactive = QRadioButton(t("mode_interactive", self.current_lang))
            self.radio_autowrite = QRadioButton(t("mode_autowrite", self.current_lang))
            self.radio_readonly = QRadioButton(t("mode_readonly", self.current_lang))

            mode = str(self.cfg.get("approval_mode", "interactive")).lower()
            if mode == "autowrite":
                self.radio_autowrite.setChecked(True)
            elif mode == "readonly":
                self.radio_readonly.setChecked(True)
            else:
                self.radio_interactive.setChecked(True)

            self.sec_group = QButtonGroup(self)
            self.sec_group.addButton(self.radio_interactive)
            self.sec_group.addButton(self.radio_autowrite)
            self.sec_group.addButton(self.radio_readonly)

            layout.addWidget(self.radio_interactive)
            layout.addWidget(self.radio_autowrite)
            layout.addWidget(self.radio_readonly)
            layout.addSpacing(10)

            conn_lbl = QLabel(t("connector_groups_label", self.current_lang))
            conn_lbl.setStyleSheet("font-weight: bold; color: #38bdf8;")
            layout.addWidget(conn_lbl)

            groups = self.cfg.get("enabled_connector_groups", {})
            self.group_chks: Dict[str, QCheckBox] = {}
            labels = {
                "core_os": "Core OS & Kernel (os-kernel, os-system, os-files, os-storage, os-packages, os-desktop)",
                "security": "Seguridad & Antivirus (security-antivirus ClamAV, security-vault-crypto, security-net-audit)",
                "development": "Desarrollo (dev-git, dev-vscodium, dev-containers-vm, dev-api-databases)",
                "creative": "Creatividad & Multimedia (GIMP, Krita, Blender, Audacity, Kdenlive, HandBrake, Inkscape)",
                "office": "Oficina & Documentos (LibreOffice, Okular Poppler, Obsidian, Calibre)",
                "browser": "Navegador Web (Brave CDP, Firefox)",
                "comms_gaming": "Comunicaciones & Gaming (Syncthing, qBittorrent, Steam, Lutris, RetroArch, Comms)",
            }
            for k, label in labels.items():
                chk = QCheckBox(label)
                chk.setChecked(bool(groups.get(k, True)))
                self.group_chks[k] = chk
                layout.addWidget(chk)

            layout.addStretch()
            return w

        def _tab_audit(self) -> QWidget:
            w = QWidget()
            layout = QVBoxLayout(w)
            layout.setSpacing(10)

            top_box = QHBoxLayout()
            top_box.addWidget(QLabel(t("audit_title", self.current_lang)))
            top_box.addStretch()
            btn_clear = QPushButton(t("btn_clear_audit", self.current_lang))
            btn_clear.clicked.connect(self._on_clear_audit)
            top_box.addWidget(btn_clear)
            layout.addLayout(top_box)

            self.audit_table = QTableWidget()
            self.audit_table.setColumnCount(5)
            self.audit_table.setHorizontalHeaderLabels(["Fecha / Hora", "Conector", "Herramienta", "Riesgo", "Estado"])
            self.audit_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            self.audit_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            layout.addWidget(self.audit_table)
            self._load_audit_entries()

            return w

        def _load_audit_entries(self) -> None:
            entries = _read_audit_entries(100)
            self.audit_table.setRowCount(len(entries))
            for row, e in enumerate(entries):
                ts = e.get("ts", 0)
                time_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if ts else "-"
                self.audit_table.setItem(row, 0, QTableWidgetItem(time_str))
                self.audit_table.setItem(row, 1, QTableWidgetItem(str(e.get("connector", ""))))
                self.audit_table.setItem(row, 2, QTableWidgetItem(str(e.get("tool", ""))))
                self.audit_table.setItem(row, 3, QTableWidgetItem(str(e.get("risk_level", ""))))
                self.audit_table.setItem(row, 4, QTableWidgetItem(str(e.get("status", ""))))

        def _on_clear_audit(self) -> None:
            audit_file = Path(os.environ.get("ARIAOS_AUDIT_LOG", "/tmp/ariaos-audit.jsonl"))
            if audit_file.exists():
                try:
                    audit_file.write_text("", encoding="utf-8")
                except OSError:
                    pass
            self._load_audit_entries()

        def _on_test_ollama(self) -> None:
            endpoint = self.endpoint_edit.text().strip()
            self._probe_thread = OllamaProbeThread(endpoint)
            self._probe_thread.models_ready.connect(self._on_models_probed)
            self._probe_thread.start()

        def _on_models_probed(self, models: list, ok: bool) -> None:
            if not ok or not models:
                QMessageBox.warning(self, "Ollama", f"No se pudo conectar a Ollama en {self.endpoint_edit.text()}.\nVerifica que ollama.service esté activo.")
                return
            curr = self.model_combo.currentText()
            self.model_combo.clear()
            self.model_combo.addItems(models)
            idx = self.model_combo.findText(curr)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)
            QMessageBox.information(self, "Ollama", f"Conexión exitosa. {len(models)} modelo(s) disponibles.")

        def _on_pull_model(self) -> None:
            target_model = self.model_combo.currentText().strip()
            if not target_model:
                return
            if shutil.which("konsole"):
                subprocess.Popen(["konsole", "--title", f"AriaOS - Descargar {target_model}", "-e", "bash", "-c", f"ollama pull {target_model}; echo; read -p 'Presiona Enter para cerrar...'"])
            elif shutil.which("xterm"):
                subprocess.Popen(["xterm", "-title", f"AriaOS - Descargar {target_model}", "-e", "bash", "-c", f"ollama pull {target_model}; echo; read -p 'Presiona Enter para cerrar...'"])
            else:
                subprocess.Popen(["ollama", "pull", target_model])

        def _on_lang_changed(self) -> None:
            code = self.lang_combo.currentData()
            if code in SUPPORTED_LANGUAGES:
                self.current_lang = code
                self.title_lbl.setText(t("settings_title", code))
                self.tabs.setTabText(0, t("tab_general", code))
                self.tabs.setTabText(1, t("tab_model", code))
                self.tabs.setTabText(2, t("tab_security", code))
                self.tabs.setTabText(3, t("tab_audit", code))
                self.btn_save.setText(t("btn_save", code))
                self.btn_close.setText(t("btn_close", code))

        def _on_save(self) -> None:
            selected_mode = "interactive"
            if self.radio_autowrite.isChecked():
                selected_mode = "autowrite"
            elif self.radio_readonly.isChecked():
                selected_mode = "readonly"

            new_cfg: Dict[str, Any] = {
                "language": self.lang_combo.currentData() or "es",
                "hotkey": self.hotkey_combo.currentText().strip(),
                "ollama_url": self.endpoint_edit.text().strip(),
                "model": self.model_combo.currentText().strip(),
                "num_ctx": int(self.ctx_combo.currentText() or 8192),
                "temperature": round(self.temp_slider.value() / 100.0, 2),
                "approval_mode": selected_mode,
                "enabled_connector_groups": {
                    k: chk.isChecked() for k, chk in self.group_chks.items()
                },
            }
            saved_path = save_ariaos_config(new_cfg)
            self.cfg = new_cfg
            self.status_feedback.setText(f"✓ {t('saved_success', self.current_lang)} ({saved_path.name})")

    app = QApplication(sys.argv)
    win = SettingsWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
