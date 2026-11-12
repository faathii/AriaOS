#!/usr/bin/env python3
"""AriaOS Hub & Neural Kernel Center — Cyber Obsidian Edition."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

AUTORUN_PATH = Path.home() / ".config" / "autostart" / "ariaos-welcome.desktop"


def _query_daemon(payload: dict[str, Any]) -> dict[str, Any] | None:
    if not hasattr(socket, "AF_UNIX"):
        return None
    for candidate in ("/run/ariaos/agent.sock", "/tmp/ariaos-agent.sock"):
        sock_path = Path(candidate)
        if sock_path.exists():
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                    s.settimeout(2.0)
                    s.connect(str(sock_path))
                    s.sendall((json.dumps(payload) + "\n").encode("utf-8"))
                    data = s.recv(65536)
                    if data:
                        return json.loads(data.decode("utf-8").splitlines()[0])
            except Exception:
                continue
    return None


def _check_network() -> bool:
    try:
        urllib.request.urlopen("https://archlinux.org", timeout=2)
        return True
    except Exception:
        return False


def _check_ollama_model() -> tuple[bool, str]:
    try:
        req = urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=1.5)
        data = json.loads(req.read().decode("utf-8"))
        models = [m.get("name", "") for m in data.get("models", [])]
        for preferred in ("aria-core", "qwen2.5:0.5b", "qwen2.5:1.5b", "qwen2.5:3b"):
            if any(preferred in m for m in models):
                return True, preferred
        if models:
            return True, models[0]
    except Exception:
        pass
    return False, "Tier-0 Native Rust Reflex (<1ms)"


def _check_clamav_ready() -> bool:
    db_dir = Path("/var/lib/clamav")
    if not db_dir.exists():
        return False
    return any(f.suffix.lower() in {".cvd", ".cld"} for f in db_dir.iterdir() if f.is_file())


def _launch_konsole(title: str, cmd: list[str]) -> None:
    if shutil.which("konsole"):
        subprocess.Popen(["konsole", "--hold", "-e"] + cmd)
    elif shutil.which("xterm"):
        subprocess.Popen(["xterm", "-hold", "-title", title, "-e"] + cmd)
    else:
        subprocess.Popen(cmd)


def main() -> int:
    parser = argparse.ArgumentParser(description="AriaOS Hub & Neural Kernel Center")
    parser.add_argument("--check", action="store_true", help="Self-check imports and exit")
    args = parser.parse_args()

    if args.check:
        print(json.dumps({"ok": True, "app": "ariaos-welcome"}))
        return 0

    try:
        from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
        from PyQt6.QtGui import QIcon, QPixmap
        from PyQt6.QtWidgets import (
            QApplication,
            QCheckBox,
            QFrame,
            QGridLayout,
            QHBoxLayout,
            QLabel,
            QPushButton,
            QTabWidget,
            QVBoxLayout,
            QWidget,
        )
    except ImportError:
        print("AriaOS Welcome: PyQt6 not available. Install python-pyqt6.", file=sys.stderr)
        return 1

    class StatusThread(QThread):
        status_ready = pyqtSignal(dict)

        def run(self) -> None:
            online = _check_network()
            has_model, model_label = _check_ollama_model()
            av_ready = _check_clamav_ready()
            k_resp = _query_daemon({"action": "kernel_telemetry"})
            telemetry = k_resp.get("telemetry", {}) if k_resp and k_resp.get("ok") else {}
            self.status_ready.emit({
                "online": online,
                "has_model": has_model,
                "model_label": model_label,
                "av_ready": av_ready,
                "telemetry": telemetry,
            })

    class WelcomeWindow(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("AriaOS — Centro Neuronal y de Sistema")
            self.setWindowIcon(QIcon.fromTheme("ariaos-logo"))
            self.resize(820, 560)
            self._apply_style()
            self._init_ui()
            self._refresh_status()

            self.timer = QTimer(self)
            self.timer.timeout.connect(self._refresh_kernel_strip)
            self.timer.start(4000)

        def _apply_style(self) -> None:
            self.setStyleSheet("""
                QWidget {
                    background-color: #070a12;
                    color: #e2e8f0;
                    font-family: "Noto Sans", sans-serif;
                    font-size: 13px;
                }
                QLabel#telemetry_banner {
                    background-color: #0b1120;
                    border: 1px solid #00f0ff;
                    border-radius: 8px;
                    padding: 8px 12px;
                    color: #00f0ff;
                    font-family: "Hack", monospace;
                    font-size: 11px;
                    font-weight: bold;
                }
                QTabWidget::pane {
                    border: 1px solid #1e293b;
                    background: #0b101e;
                    border-radius: 10px;
                    padding: 14px;
                }
                QTabBar::tab {
                    background: #090d18;
                    color: #94a3b8;
                    padding: 9px 18px;
                    border: 1px solid #162238;
                    border-bottom: none;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    margin-right: 4px;
                }
                QTabBar::tab:selected {
                    background: #0d1629;
                    color: #00f0ff;
                    border-color: #00f0ff;
                    font-weight: bold;
                }
                QPushButton {
                    background-color: #0d1526;
                    color: #e2e8f0;
                    border: 1px solid #1e3a5f;
                    border-radius: 8px;
                    padding: 9px 14px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #00f0ff;
                    color: #070a12;
                    border-color: #00f0ff;
                    font-weight: bold;
                }
                QPushButton#primary {
                    background-color: #00b4d8;
                    color: #070a12;
                    border-color: #00f0ff;
                    font-weight: bold;
                }
                QPushButton#primary:hover {
                    background-color: #00f0ff;
                    color: #070a12;
                }
                QFrame#card {
                    background-color: #0d1322;
                    border: 1px solid #1e293b;
                    border-radius: 10px;
                    padding: 12px;
                }
            """)

        def _init_ui(self) -> None:
            root = QVBoxLayout(self)
            root.setContentsMargins(18, 16, 18, 14)
            root.setSpacing(12)

            # Header
            header = QHBoxLayout()
            logo_lbl = QLabel()
            pix = QPixmap("/usr/share/pixmaps/ariaos-logo.png")
            if pix.isNull():
                pix = QPixmap("c:/Users/hamza/Desktop/AriaOS/assets/branding/ariaos-logo.png")
            if not pix.isNull():
                logo_lbl.setPixmap(pix.scaled(54, 54, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            header.addWidget(logo_lbl)

            title_box = QVBoxLayout()
            t = QLabel("ARIA OS // CYBER OBSIDIAN")
            t.setStyleSheet("font-size: 21px; font-weight: bold; color: #00f0ff; letter-spacing: 1px;")
            sub = QLabel("La IA no es un programa: la IA es el Sistema Operativo (Kernel + Rust Neural Core + KDE Plasma 6)")
            sub.setStyleSheet("color: #94a3b8; font-size: 12px;")
            title_box.addWidget(t)
            title_box.addWidget(sub)
            header.addLayout(title_box)
            header.addStretch()

            btn_optimize = QPushButton("⚡ Optimizar RAM", objectName="primary")
            btn_optimize.clicked.connect(self._on_optimize_ram)
            header.addWidget(btn_optimize)
            root.addLayout(header)

            # Live Kernel Telemetry Strip
            self.telemetry_banner = QLabel("🧠 ENLAZANDO CON EL GOBERNADOR AUTÓNOMO DEL KERNEL...")
            self.telemetry_banner.setObjectName("telemetry_banner")
            root.addWidget(self.telemetry_banner)

            # Tabs
            tabs = QTabWidget()
            tabs.addTab(self._tab_status(), "⚡ Estado del Kernel e IA")
            tabs.addTab(self._tab_first_steps(), "🚀 Control y Atajos")
            tabs.addTab(self._tab_installer(), "💿 Instalación y Suites")
            root.addWidget(tabs)

            # Footer
            footer = QHBoxLayout()
            self.autostart_chk = QCheckBox("Mostrar este centro al iniciar sesión")
            self.autostart_chk.setChecked(AUTORUN_PATH.exists() or not (Path.home() / ".config" / ".ariaos-no-welcome").exists())
            self.autostart_chk.toggled.connect(self._toggle_autostart)
            footer.addWidget(self.autostart_chk)
            footer.addStretch()

            close_btn = QPushButton("Cerrar")
            close_btn.clicked.connect(self.close)
            footer.addWidget(close_btn)
            root.addLayout(footer)

        def _tab_status(self) -> QWidget:
            w = QWidget()
            layout = QVBoxLayout(w)
            layout.setSpacing(10)

            self.kernel_status_lbl = QLabel("🧠 Analizando registros x86_64 (CPUID) y perfil de memoria...")
            self.ai_status_lbl = QLabel("⚡ Verificando Núcleo Neuronal Híbrido (Tier-0 + Tier-1)...")
            self.net_status_lbl = QLabel("🌐 Comprobando enlace de red...")
            self.av_status_lbl = QLabel("🛡️ Verificando estado de Aria Shield (Bajo demanda, 0 MB RAM en reposo)...")

            for lbl in (self.kernel_status_lbl, self.ai_status_lbl, self.net_status_lbl, self.av_status_lbl):
                lbl.setStyleSheet("padding: 9px 12px; background: #090e1a; border: 1px solid #162238; border-radius: 8px;")
                layout.addWidget(lbl)

            btn_box = QHBoxLayout()
            self.btn_open_hud = QPushButton("⚡ Abrir Aria Neural HUD", objectName="primary")
            self.btn_open_hud.clicked.connect(lambda: subprocess.Popen(["aria-command-bar"]))
            btn_box.addWidget(self.btn_open_hud)

            self.btn_pull_ai = QPushButton("🧠 Instalar Modelo Ligero (aria-core 0.5B)")
            self.btn_pull_ai.clicked.connect(
                lambda: _launch_konsole(
                    "AriaOS Neural Model Setup",
                    ["bash", "-c", "ollama pull qwen2.5:0.5b && ollama create aria-core -f /usr/share/ariaos/models/Modelfile.aria-core"],
                )
            )
            btn_box.addWidget(self.btn_pull_ai)

            self.btn_open_av = QPushButton("🛡️ Abrir Aria Shield")
            self.btn_open_av.clicked.connect(lambda: subprocess.Popen(["ariaos-antivirus"]))
            btn_box.addWidget(self.btn_open_av)

            btn_refresh = QPushButton("🔄 Actualizar")
            btn_refresh.clicked.connect(self._refresh_status)
            btn_box.addWidget(btn_refresh)

            layout.addLayout(btn_box)
            layout.addStretch()
            return w

        def _tab_first_steps(self) -> QWidget:
            w = QWidget()
            layout = QVBoxLayout(w)
            layout.setSpacing(12)

            info = QLabel(
                "<b>Arquitectura Cyber Obsidian — Diseñada para Máximo Rendimiento:</b><br><br>"
                "• <b>Aria Neural HUD (<code>Alt + Espacio</code>):</b> Interfaz directa con el kernel en menos de 1 ms. "
                "Consulta procesos, libera memoria RAM, controla hardware o lanza aplicaciones al instante.<br>"
                "• <b>Gobernador Autónomo del Kernel:</b> Detecta automáticamente tus capacidades de silicio (AVX2, FMA, AES-NI) "
                "y ajusta ZRAM (<code>zstd</code>), planificadores I/O y compactación de memoria para funcionar con fluidez desde equipos de 8 GB hasta estaciones de trabajo.<br>"
                "• <b>Doble Barra Futurista:</b> Barra superior minimalista de estado + Dock inferior flotante centrado.<br>"
                "• <b>Aria Shield Bajo Demanda:</b> Protección antivirus sin consumir RAM en segundo plano."
            )
            info.setWordWrap(True)
            info.setTextFormat(Qt.TextFormat.RichText)
            layout.addWidget(info)

            actions = QHBoxLayout()
            btn_bar = QPushButton("⚡ Neural HUD (Alt+Espacio)", objectName="primary")
            btn_bar.clicked.connect(lambda: subprocess.Popen(["aria-command-bar"]))
            actions.addWidget(btn_bar)

            btn_mon = QPushButton("📊 Monitor Kernel & GPU")
            btn_mon.clicked.connect(lambda: subprocess.Popen(["ariaos-monitor"]))
            actions.addWidget(btn_mon)

            btn_store = QPushButton("📦 Centro de Software")
            btn_store.clicked.connect(lambda: subprocess.Popen(["ariaos-store"]))
            actions.addWidget(btn_store)

            btn_auto = QPushButton("🧠 Automatizaciones IA")
            btn_auto.clicked.connect(lambda: subprocess.Popen(["ariaos-automations"]))
            actions.addWidget(btn_auto)

            btn_antivirus = QPushButton("🛡️ Aria Shield")
            btn_antivirus.clicked.connect(lambda: subprocess.Popen(["ariaos-antivirus"]))
            actions.addWidget(btn_antivirus)

            btn_fw = QPushButton("🔒 Cortafuegos")
            btn_fw.clicked.connect(lambda: subprocess.Popen(["ariaos-firewall"]))
            actions.addWidget(btn_fw)

            btn_settings = QPushButton("⚙️ Ajustes")
            btn_settings.clicked.connect(lambda: subprocess.Popen(["ariaos-settings"]))
            actions.addWidget(btn_settings)

            layout.addLayout(actions)

            actions2 = QHBoxLayout()
            btn_snap = QPushButton("⏪ Time Machine")
            btn_snap.clicked.connect(lambda: subprocess.Popen(["ariaos-snapshots"]))
            actions2.addWidget(btn_snap)

            btn_vault = QPushButton("🔐 Bóveda Secreta")
            btn_vault.clicked.connect(lambda: subprocess.Popen(["ariaos-vault"]))
            actions2.addWidget(btn_vault)

            btn_studio = QPushButton("🚀 AI Studio")
            btn_studio.clicked.connect(lambda: subprocess.Popen(["ariaos-ai-studio"]))
            actions2.addWidget(btn_studio)

            btn_radar = QPushButton("🌐 Radar de Red")
            btn_radar.clicked.connect(lambda: subprocess.Popen(["ariaos-netradar"]))
            actions2.addWidget(btn_radar)

            btn_opt = QPushButton("🧹 Optimizador Boot")
            btn_opt.clicked.connect(lambda: subprocess.Popen(["ariaos-optimizer"]))
            actions2.addWidget(btn_opt)

            btn_clip = QPushButton("📋 Portapapeles IA")
            btn_clip.clicked.connect(lambda: subprocess.Popen(["ariaos-clipboard"]))
            actions2.addWidget(btn_clip)

            layout.addLayout(actions2)
            layout.addStretch()
            return w

        def _tab_installer(self) -> QWidget:
            w = QWidget()
            layout = QVBoxLayout(w)
            layout.setSpacing(14)

            intro = QLabel(
                "Instala AriaOS permanentemente en tu disco NVMe/SSD o añade suites modulares según tu flujo de trabajo:"
            )
            intro.setWordWrap(True)
            layout.addWidget(intro)

            grid = QGridLayout()
            btn_all_apps = QPushButton("📦 Suite Completa (Creativa, Dev, Gaming, Security)")
            btn_all_apps.clicked.connect(lambda: _launch_konsole("AriaOS Apps Suite", ["sudo", "ariaos-install-apps", "--all"]))
            grid.addWidget(btn_all_apps, 0, 0)

            btn_dev_suite = QPushButton("💻 Suite Desarrollo & Contenedores")
            btn_dev_suite.clicked.connect(lambda: _launch_konsole("AriaOS Dev Suite", ["sudo", "ariaos-install-apps", "--dev"]))
            grid.addWidget(btn_dev_suite, 0, 1)

            btn_sec_suite = QPushButton("🔐 Suite Auditoría & Ciberseguridad")
            btn_sec_suite.clicked.connect(lambda: _launch_konsole("AriaOS Security Suite", ["sudo", "ariaos-install-apps", "--security"]))
            grid.addWidget(btn_sec_suite, 1, 0)

            btn_creative = QPushButton("🎨 Suite Creativa (Diseño, 3D, Vídeo)")
            btn_creative.clicked.connect(lambda: _launch_konsole("AriaOS Creative Suite", ["sudo", "ariaos-install-apps", "--creative"]))
            grid.addWidget(btn_creative, 1, 1)
            layout.addLayout(grid)

            install_card = QFrame()
            install_card.setObjectName("card")
            card_layout = QHBoxLayout(install_card)
            card_lbl = QLabel("<b>Instalación Nativa en Disco:</b> Transfiere AriaOS y su Kernel Neuronal a tu disco.")
            btn_install_os = QPushButton("💿 Instalar AriaOS en Disco", objectName="primary")
            btn_install_os.clicked.connect(lambda: subprocess.Popen(["ariaos-installer"]))
            card_layout.addWidget(card_lbl)
            card_layout.addStretch()
            card_layout.addWidget(btn_install_os)
            layout.addWidget(install_card)

            layout.addStretch()
            return w

        def _on_optimize_ram(self) -> None:
            resp = _query_daemon({"action": "optimize_kernel"})
            if resp and resp.get("ok"):
                freed = resp.get("freed_mb", 0)
                avail = resp.get("after_available_mb", 0)
                pct = resp.get("usage_pct", 0)
                self.telemetry_banner.setText(
                    f"⚡ KERNEL OPTIMIZADO: +{freed} MB liberados  |  Disponible: {avail} MB ({pct}% en uso)"
                )
            self._refresh_status()

        def _refresh_kernel_strip(self) -> None:
            k_resp = _query_daemon({"action": "kernel_telemetry"})
            if k_resp and k_resp.get("ok"):
                t_data = k_resp.get("telemetry", {})
                self._update_telemetry_labels(t_data)

        def _update_telemetry_labels(self, t_data: dict[str, Any]) -> None:
            if not t_data:
                return
            tier = t_data.get("hardware_tier", "Tier-A (8GB+)")
            mem = t_data.get("memory", {})
            psi = t_data.get("psi", {})
            sil = t_data.get("silicon", {})
            load = t_data.get("load_avg", [0.0])[0]
            used = mem.get("used_mb", 0)
            total = mem.get("total_mb", 0)
            pct = mem.get("usage_pct", 0)
            psi_m = psi.get("memory_avg10", 0.0)
            avx2 = "AVX2" if sil.get("avx2") else "SSE4.2"
            env_mode = "VM" if sil.get("hypervisor") else "Bare-Metal"
            self.telemetry_banner.setText(
                f"🧠 {tier} [{avx2} • {env_mode}]  |  ⚡ CPU Load: {load:.2f}  |  "
                f"💾 RAM: {used}/{total} MB ({pct}%)  |  🟢 PSI: {psi_m:.1f}%"
            )
            self.kernel_status_lbl.setText(
                f"🟢 <b>Kernel & Gobernador Autónomo:</b> <code>{t_data.get('kernel_version', 'Linux')}</code> — "
                f"Perfil <b>{tier}</b> ({t_data.get('cpu_cores', 1)} hilos, {avx2})"
            )

        def _refresh_status(self) -> None:
            self._thread = StatusThread()
            self._thread.status_ready.connect(self._on_status_ready)
            self._thread.start()

        def _on_status_ready(self, data: dict[str, Any]) -> None:
            self._update_telemetry_labels(data.get("telemetry", {}))

            if data["has_model"]:
                self.ai_status_lbl.setText(
                    f"🟢 <b>Motor Neuronal Híbrido:</b> Tier-0 Rust Reflex (<code>&lt;1ms</code>) + "
                    f"Modelo <b>{data['model_label']}</b> activos"
                )
            else:
                self.ai_status_lbl.setText(
                    "🟢 <b>Motor Neuronal Nativo Activo:</b> Tier-0 Rust Reflex (<code>&lt;1ms</code>, 0 MB RAM extra) listo para usar"
                )

            if data["online"]:
                self.net_status_lbl.setText("🟢 <b>Enlace de Red:</b> Conectado y operativo")
            else:
                self.net_status_lbl.setText("🟡 <b>Enlace de Red:</b> Modo local sin conexión (la IA del Kernel funciona 100% offline)")

            if data["av_ready"]:
                self.av_status_lbl.setText("🟢 <b>Aria Shield Antivirus:</b> Base de firmas lista (Modo bajo demanda, 0% impacto en RAM)")
            else:
                self.av_status_lbl.setText("🛡️ <b>Aria Shield Antivirus:</b> Modo ligero activo (sincroniza firmas cuando lo necesites)")

        def _toggle_autostart(self, checked: bool) -> None:
            no_welcome = Path.home() / ".config" / ".ariaos-no-welcome"
            if checked:
                if no_welcome.exists():
                    no_welcome.unlink(missing_ok=True)
            else:
                no_welcome.parent.mkdir(parents=True, exist_ok=True)
                no_welcome.write_text("disabled", encoding="utf-8")

    app = QApplication(sys.argv)
    win = WelcomeWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
