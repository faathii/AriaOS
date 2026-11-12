# 🧠 Manual Maestro de IA, Conectores, APIs y Comandos de Actuación — AriaOS Cyber Obsidian

> **Filosofía de AriaOS:** *"La IA no es un programa; la IA ES el Sistema Operativo."*
> Aria opera directamente desde el Kernel de Linux y el demonio nativo en Rust/Ensamblador x86_64 (`aria-daemon`), gobernando **39 conectores oficiales**, **146 herramientas de API** y **más de 66 aplicaciones de escritorio**.

---

## 1. Arquitectura de Actuación Neuronal en 3 Capas

| Capa | Motor | Latencia | Consumo RAM Extra | Función Principal |
| :--- | :--- | :---: | :---: | :--- |
| **Tier-0 (Kernel Reflex)** | Rust + Inline ASM x86_64 (`kernel.rs`, `neural.rs`) | **`< 0.5 ms`** | **0 MB** | Lectura directa de `/proc`, `/sys`, registros `CPUID`/`RDTSC`, compactación de RAM/ZRAM y despacho instantáneo a los 32 conectores. |
| **Memoria Sináptica** | Auto-Aprendizaje Persistente (`memory.rs` / `neural_memory.json`) | **`< 0.3 ms`** | **0 MB** | 15 perfiles y macros pre-entrenados de fábrica + aprendizaje continuo en vivo (`aprende: X -> Y`). |
| **Tier-1 (Neural LLM)** | `aria-core` (`qwen2.5:0.5b` Q4_K_M + `ollama.rs`) | **`150–600 ms`** | **~380 MB** (adaptativo) | Razonamiento encadenado multi-herramienta JSON-RPC con filtrado inteligente de conectores por contexto. |

---

## 2. Cómo Invocar Comandos (3 Vías simultáneas)

1. **Lenguaje Natural (Voz / Texto en `Alt + Espacio` o CLI):**
   Escribe directamente lo que necesitas en el **Aria Neural HUD** (`Alt+Space`):
   - Ejemplo: `«optimizar ram»`, `«modo gaming»`, `«escanear descargas»`, `«abre vscodium y terminal»`.
2. **Inspección de API en Vivo desde el HUD:**
   - `/apis` o `/comandos` o `«qué sabes hacer»` → Muestra el mapa completo de capacidades.
   - `«api de <programa o conector>»` (ej. `«api de obs»`, `«api de docker»`, `«api de antivirus»`) → Muestra todas las funciones API exactas de ese conector.
3. **Invocación Técnica Directa a la API (JSON-RPC 2.0):**
   - Desde el HUD: `/call <conector> <herramienta> {"param": "valor"}`
   - Desde terminal: `aria-daemon call <conector> <herramienta> '{"param": "valor"}' --yes`

---

## 3. Los 5 Modos de Trabajo Pre-entrenados del Kernel (`os-power-modes`)

| Comando para Nosotros (HUD / Voz) | Comando de API Directa | Actuación en el Kernel y Sistema |
| :--- | :--- | :--- |
| **`«modo gaming»`** / `«modo juego»` | `/call os-power-modes apply_work_mode {"mode":"gaming"}` | Gobernador CPU en `performance`, `vm.swappiness=10`, `drop_caches=3`, `compact_memory=1`, brillo 100% y lanza `steam`/`lutris`. |
| **`«modo desarrollo»`** / `«modo código»` | `/call os-power-modes apply_work_mode {"mode":"development"}` | Gobernador `schedutil`, `vm.swappiness=30`, `vfs_cache_pressure=60`, compacta RAM y lanza `codium` + `konsole`. |
| **`«modo creativo»`** / `«modo estudio»` | `/call os-power-modes apply_work_mode {"mode":"creative"}` | Gobernador `performance`, `vm.swappiness=20`, prioriza buffers para render/audio PipeWire y lanza `kdenlive`/`obs`/`gimp`/`blender`. |
| **`«modo ahorro extremo»`** / `«modo batería»` | `/call os-power-modes apply_work_mode {"mode":"powersave"}` | Gobernador `powersave`, máxima compresión ZRAM (`swappiness=100`), purga cachés inactivas y reduce brillo al 40%. |
| **`«modo seguridad»`** / `«modo blindaje»` | `/call os-power-modes apply_work_mode {"mode":"security"}` | Activa perfil defensivo y abre el centro **Aria Shield Antivirus** (`ariaos-antivirus`). |

---

## 4. Aplicaciones Nativas de AriaOS Cyber Obsidian

| Aplicación | Binario | Comando para Nosotros | Propósito y Conexión con el Kernel |
| :--- | :--- | :--- | :--- |
| **Aria Neural HUD** | `aria-command-bar` | `Alt + Espacio` / `«abrir hud»` | Barra de mando flotante conectada por socket Unix a `aria-daemon`. |
| **Monitor de Kernel, GPU y Procesos** | `ariaos-monitor` | `«abrir monitor»` / `«gestor de procesos»` | Telemetría CPUID/PSI/ZRAM/GPU en tiempo real, selector de Modos del Kernel y terminación `SIGTERM`/`SIGKILL`. |
| **Centro de Software y Paquetes** | `ariaos-store` | `«abrir tienda»` / `«centro de software»` | Instalador visual de las 9 Suites Modulares (58+ apps), buscador `pacman` y comprobador de actualizaciones. |
| **Centro de Automatizaciones e IA** | `ariaos-automations` | `«abrir automatizaciones»` / `«reglas ia»` | Editor visual de reglas sinápticas (`neural_memory.json`) y programador de tareas autónomas (`15m`, `1h`, `6h`, `24h`). |
| **Aria Shield Antivirus** | `ariaos-antivirus` | `«abrir antivirus»` / `«abrir escudo»` | Centro de seguridad ClamAV bajo demanda (0 MB RAM en reposo), cuarentena reversible y whitelist SHA-256. |
| **Cortafuegos y Monitor de Red** | `ariaos-firewall` | `«abrir cortafuegos»` / `«conexiones activas»` | Monitor en vivo de sockets TCP/UDP (`/proc/net/tcp`, `ss`), bloqueo de puertos en 1 clic y Modo Aislamiento de Emergencia. |
| **Instalador Gráfico de Sistema** | `ariaos-installer` | `«instalar ariaos»` / `«abrir instalador»` | Asistente visual Cyber Obsidian para particionado NVMe/SSD (`ext4`/`btrfs`/`xfs`), cifrado LUKS2 e instalación de AriaOS + IA. |
| **Máquina del Tiempo (Snapshots)** | `ariaos-snapshots` | `«abrir snapshots»` / `«crear snapshot»` | Puntos de restauración instantáneos (Btrfs, Timeshift y configuración neuronal AriaOS) con reversión en 1 clic. |
| **Bóveda Criptográfica y Secretos** | `ariaos-vault` | `«abrir boveda»` / `«generar clave segura»` | Gestor local cifrado (`PBKDF2-HMAC-SHA256`), generador CSPRNG de alta entropía y auditor de llaves SSH (`~/.ssh`). |
| **Laboratorio de IA Local (AI Studio)** | `ariaos-ai-studio` | `«abrir ai studio»` / `«benchmark de ia»` | Conmutador de modelos locales (`aria-core`, `qwen2.5`, `llama3.2`), benchmark de tokens/s y editor de memoria neuronal. |
| **Radar de Red y DNS Privado** | `ariaos-netradar` | `«abrir netradar»` / `«dispositivos en mi red»` | Escáner de dispositivos LAN (ARP/NDP), selector de DNS cifrado (`Cloudflare`, `Quad9`, `Mullvad`) y radar de latencia. |
| **Optimizador de Boot y Limpiador** | `ariaos-optimizer` | `«abrir optimizador»` / `«analizar tiempo de arranque»` | Analizador de tiempos de arranque (`systemd-analyze`) y limpiador profundo de cachés Pacman, logs `journald` y miniaturas. |
| **Portapapeles Inteligente IA** | `ariaos-clipboard` | `«abrir portapapeles»` / `«historial del portapapeles»` | Historial semántico de elementos copiados (JSON, URL, código, bash) y transformador en 1 clic (JSON, Base64, SHA-256). |
| **Centro de Control AriaOS** | `ariaos-settings` | `«abrir ajustes»` / `«configuración»` | Selector de modelo neuronal (`aria-core` 0.5B / 1.5B / 3B), idioma (8 idiomas) y optimización de memoria. |
| **Centro Neuronal de Bienvenida** | `ariaos-welcome` | `«abrir bienvenida»` | Panel de estado del Kernel, instalación en disco y acceso rápido a herramientas. |
| **Menú Contextual IA en Dolphin** | `ariaos-file-action` | Clic derecho en cualquier archivo/carpeta en Dolphin → **⚡ AriaOS Gestor IA** | Analiza metadatos + SHA-256 + cabeceras ELF/PDF/Office, convierte formatos (Doc→PDF, Vídeo→MP3, SVG→PNG, Carpeta→ZIP), organiza y busca duplicados. |
| **Guardián de Auto-Reparación** | `aria-daemon heal` | `«auto reparar»` / `«procesos zombis»` | Hilo autónomo en `kernel.rs` (cada 18 s) que limpia procesos zombis (`State: Z`), recupera servicios caídos y compacta RAM ante bloqueos PSI. |

---

## 5. Diccionario Completo de los 32 Conectores, sus APIs y Comandos de Actuación

### A. Núcleo del Sistema, Kernel, Energía y Automatización (7 Conectores)

#### 1. `os-kernel` — Capa Directa del Kernel de Linux y Hardware
* **Protocolo:** Lectura directa de `/proc`, `/sys/class/thermal`, `/proc/pressure`, `sysctl`, `dmesg`, `lspci`, `lsusb`, `modprobe`.
* **Herramientas API y Comandos:**
  - `os-kernel.kernel_telemetry` (`read`):
    - **Nosotros:** `«estado del sistema»`, `«salud del kernel»`, `«telemetría»`, `/kernel`
    - **API:** `/call os-kernel kernel_telemetry {}`
  - `os-kernel.dmesg_inspect` (`read`):
    - **Nosotros:** `«dmesg»`, `«logs del kernel»`, `«errores del kernel»`
    - **API:** `/call os-kernel dmesg_inspect {"lines": 50, "level": "err,warn"}`
  - `os-kernel.hardware_pci_usb` (`read`):
    - **Nosotros:** `«hardware pci»`, `«dispositivos usb»`, `«hardware conectado»`
    - **API:** `/call os-kernel hardware_pci_usb {}`
  - `os-kernel.sysctl_read` / `os-kernel.sysctl_write` (`read` / `privileged`):
    - **API:** `/call os-kernel sysctl_read {"key": "vm.swappiness"}`
    - **API:** `/call os-kernel sysctl_write {"key": "vm.swappiness", "value": "20"}`
  - `os-kernel.kernel_module_manage` (`privileged`):
    - **API:** `/call os-kernel kernel_module_manage {"module": "loop", "action": "load"}`

#### 2. `os-power-modes` — Perfiles del Kernel y Telemetría GPU/DRM
* **Protocolo:** `/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor`, `/sys/class/drm/card*`, `nvidia-smi`, `/proc/sys/vm/*`.
* **Herramientas API y Comandos:**
  - `os-power-modes.list_work_modes` (`read`):
    - **Nosotros:** `«modos de trabajo»`, `«perfiles de rendimiento»`
    - **API:** `/call os-power-modes list_work_modes {}`
  - `os-power-modes.apply_work_mode` (`read`):
    - **Nosotros:** `«modo gaming»`, `«modo desarrollo»`, `«modo creativo»`, `«modo ahorro extremo»`, `«modo seguridad»`
    - **API:** `/call os-power-modes apply_work_mode {"mode": "gaming", "launch_apps": true}`
  - `os-power-modes.gpu_telemetry` (`read`):
    - **Nosotros:** `«estado gpu»`, `«telemetría gpu»`, `«vram»`
    - **API:** `/call os-power-modes gpu_telemetry {}`

#### 3. `os-automation` — Memoria Sináptica y Tareas Programadas
* **Protocolo:** Persistencia JSON en `~/.local/share/ariaos/neural_memory.json` y `scheduled_tasks.json`.
* **Herramientas API y Comandos:**
  - `os-automation.list_automations` (`read`):
    - **Nosotros:** `«automatizaciones activas»`, `«tareas programadas»`, `/memory`
    - **API:** `/call os-automation list_automations {}`
  - `os-automation.teach_rule` (`read`):
    - **Nosotros:** `«aprende: cuando diga X -> Y»`, `/learn X = Y`
    - **API:** `/call os-automation teach_rule {"trigger": "modo stream", "action": "abre obs y vscodium"}`
  - `os-automation.delete_rule` (`write`):
    - **API:** `/call os-automation delete_rule {"trigger": "modo stream"}`
  - `os-automation.configure_schedule` (`read`):
    - **API:** `/call os-automation configure_schedule {"task_id": "auto_ram_purge", "enabled": true, "interval": "15m"}`

#### 4. `os-system` — Procesos y Servicios `systemd`
* **Protocolo:** Escáner nativo `/proc/[pid]/statm` en Rust (`<0.1 ms`) y `systemctl`/`journalctl`.
* **Herramientas API y Comandos:**
  - `os-system.system_health_summary` (`read`):
    - **Nosotros:** `«salud del sistema»`, `«uso de ram»`
    - **API:** `/call os-system system_health_summary {}`
  - `os-system.list_top_processes` (`read`):
    - **Nosotros:** `«procesos»`, `«top procesos»`, `«qué consume memoria»`
    - **API:** `/call os-system list_top_processes {"sort_by": "memory", "limit": 10}`
  - `os-system.service_status` / `os-system.restart_service` (`read` / `privileged`):
    - **API:** `/call os-system service_status {"unit": "ollama.service", "lines": 15}`
    - **API:** `/call os-system restart_service {"unit": "ollama.service"}`

#### 5. `os-desktop` — Escritorio KDE Plasma 6, Audio, Brillo y Red
* **Protocolo:** PipeWire (`wpctl`/`pactl`), `/sys/class/backlight` (`brightnessctl`), `ip -j addr`, `notify-send`.
* **Herramientas API y Comandos:**
  - `os-desktop.set_volume` (`write`):
    - **Nosotros:** `«volumen al 75%»`, `«subir volumen al 90%»`
    - **API:** `/call os-desktop set_volume {"level": 75}`
  - `os-desktop.set_brightness` (`write`):
    - **Nosotros:** `«brillo al 60%»`
    - **API:** `/call os-desktop set_brightness {"level": 60}`
  - `os-desktop.network_status` (`read`):
    - **Nosotros:** `«mi ip»`, `«estado de red»`, `«interfaces de red»`
    - **API:** `/call os-desktop network_status {}`
  - `os-desktop.launch_application` (`write`):
    - **Nosotros:** `«abre firefox y vscodium»`, `«inicia terminal»`
    - **API:** `/call os-desktop launch_application {"app": "konsole"}`
  - `os-desktop.desktop_environment_info` / `os-desktop.send_notification`:
    - **API:** `/call os-desktop desktop_environment_info {}`
    - **API:** `/call os-desktop send_notification {"title": "AriaOS", "body": "Tarea completada"}`

#### 6. `os-storage` — Discos, Particiones y Archivos Comprimidos
* **Protocolo:** `lsblk --json`, `df -h`, `zipfile` y `tarfile`.
* **Herramientas API y Comandos:**
  - `os-storage.list_block_devices` (`read`):
    - **Nosotros:** `«espacio en disco»`, `«particiones»`, `«almacenamiento»`
    - **API:** `/call os-storage list_block_devices {}`
  - `os-storage.inspect_archive` / `create_archive` / `extract_archive`:
    - **API:** `/call os-storage inspect_archive {"archive_path": "/ruta/archivo.zip"}`
    - **API:** `/call os-storage create_archive {"source_path": "/ruta/carpeta", "archive_path": "/ruta/backup.zip"}`
    - **API:** `/call os-storage extract_archive {"archive_path": "/ruta/backup.zip", "destination_dir": "/ruta/destino"}`

#### 7. `os-packages` — Gestor de Paquetes `pacman` y Caché
* **Protocolo:** `pacman -Q`, `pacman -Ss`, `pacman -Qu`, `paccache`.
* **Herramientas API y Comandos:**
  - `os-packages.check_system_updates` (`read`):
    - **Nosotros:** `«actualizaciones»`, `«hay updates»`
    - **API:** `/call os-packages check_system_updates {}`
  - `os-packages.search_packages` / `list_installed_packages` (`read`):
    - **API:** `/call os-packages search_packages {"query": "neovim", "limit": 10}`
    - **API:** `/call os-packages list_installed_packages {"query": "plasma"}`
  - `os-packages.clean_package_cache` / `install_package`:
    - **API:** `/call os-packages clean_package_cache {"keep_versions": 2, "dry_run": true}`
    - **API:** `/call os-packages install_package {"package": "htop"}`

---

### B. Gestor de Archivos KDE Dolphin (`os-files`)

#### 8. `os-files` — Organización Inteligente, Duplicados SHA-256 y Papelera XDG
* **Protocolo:** Escaneo recursivo, hashing SHA-256, especificación FreeDesktop Trash (`~/.local/share/Trash`) y `dolphin --select`.
* **Herramientas API y Comandos:**
  - `os-files.scan_directory` (`read`):
    - **Nosotros:** `«analizar descargas»`, `«escanear carpeta descargas»`
    - **API:** `/call os-files scan_directory {"path": "~/Downloads", "recursive": false}`
  - `os-files.find_duplicates` (`read`):
    - **Nosotros:** `«buscar duplicados»`, `«archivos duplicados»`
    - **API:** `/call os-files find_duplicates {"path": "~/Downloads", "recursive": true}`
  - `os-files.organize_directory` (`write`):
    - **Nosotros:** `«organizar descargas»`, `«simular organizacion»`
    - **API:** `/call os-files organize_directory {"path": "~/Downloads", "apply": false}`
  - `os-files.search_files` / `file_info` / `move_to_trash` / `open_in_dolphin`:
    - **API:** `/call os-files search_files {"path": "~", "query": "*.pdf", "text_query": "factura"}`
    - **API:** `/call os-files file_info {"path": "~/documento.pdf", "include_hash": true}`
    - **API:** `/call os-files move_to_trash {"path": "~/archivo_viejo.tmp"}`
    - **API:** `/call os-files open_in_dolphin {"path": "~/Downloads"}`

---

### C. Ciberseguridad, Antivirus, Cifrado y Pentesting (3 Conectores)

#### 9. `security-antivirus` — Motor Aria Shield (ClamAV + Cuarentena + Whitelist SHA-256)
* **Protocolo:** `clamscan`/`clamdscan`, `freshclam`, bóveda de cuarentena con manifiesto JSON y whitelist nativa `.fp`.
* **Herramientas API y Comandos:**
  - `security-antivirus.av_status` (`read`):
    - **Nosotros:** `«antivirus»`, `«estado antivirus»`, `«escudo»`
    - **API:** `/call security-antivirus av_status {}`
  - `security-antivirus.av_scan_path` (`read`):
    - **Nosotros:** `«escanear descargas»`, `«analizar virus en descargas»`
    - **API:** `/call security-antivirus av_scan_path {"path": "~/Downloads", "recursive": true}`
  - `security-antivirus.av_quarantine_list` / `av_quarantine_file` / `av_restore_file`:
    - **Nosotros:** `«archivos en cuarentena»`, `«listar cuarentena»`
    - **API:** `/call security-antivirus av_quarantine_list {}`
    - **API:** `/call security-antivirus av_quarantine_file {"path": "/ruta/sospechoso.bin", "reason": "Sospechoso"}`
    - **API:** `/call security-antivirus av_restore_file {"quarantine_id": "ID"}`
  - `security-antivirus.av_get_config` / `av_set_exclusion` / `av_read_logs` / `av_shield_control`:
    - **Nosotros:** `«configuracion antivirus»`, `«exclusiones clamav»`
    - **API:** `/call security-antivirus av_get_config {}`
    - **API:** `/call security-antivirus av_set_exclusion {"kind": "trust_binary", "action": "add", "target": "/usr/bin/aria-daemon"}`

#### 10. `security-vault-crypto` — KeePassXC, VeraCrypt, Timeshift y Flameshot
* **Protocolo:** Verificación de cabeceras `.kdbx`, `veracrypt --text --list`, `timeshift --list`, `flameshot`.
* **Herramientas API y Comandos:**
  - `security-vault-crypto.veracrypt_list_volumes` (`read`):
    - **Nosotros:** `«volumenes veracrypt»`, `«discos cifrados»`
    - **API:** `/call security-vault-crypto veracrypt_list_volumes {}`
  - `security-vault-crypto.timeshift_list_snapshots` (`read`):
    - **Nosotros:** `«snapshots timeshift»`, `«puntos de restauracion»`
    - **API:** `/call security-vault-crypto timeshift_list_snapshots {}`
  - `security-vault-crypto.keepassxc_check_db` / `flameshot_capture`:
    - **API:** `/call security-vault-crypto keepassxc_check_db {"path": "~/passwords.kdbx"}`
    - **API:** `/call security-vault-crypto flameshot_capture {"mode": "gui"}`

#### 11. `security-net-audit` — Wireshark (`tshark`), Nmap, Ghidra y Cutter
* **Protocolo:** `tshark -r`, inspección binaria ELF/PE/Mach-O, `nmap`.
* **Herramientas API y Comandos:**
  - `security-net-audit.security_suite_status` (`read`):
    - **Nosotros:** `«estado suite seguridad»`, `«auditoria de seguridad»`, `«herramientas pentesting»`
    - **API:** `/call security-net-audit security_suite_status {}`
  - `security-net-audit.inspect_binary` / `inspect_pcap` / `nmap_scan`:
    - **API:** `/call security-net-audit inspect_binary {"path": "/usr/bin/aria-daemon"}`
    - **API:** `/call security-net-audit inspect_pcap {"path": "~/captura.pcap", "max_packets": 40}`
    - **API:** `/call security-net-audit nmap_scan {"target": "127.0.0.1", "mode": "top_ports"}`

---

### D. Ingeniería de Software, Contenedores, VMs y Bases de Datos (4 Conectores)

#### 12. `dev-git` — Control de Versiones Git
* **Herramientas API y Comandos:**
  - `dev-git.repo_status` / `repo_log` / `repo_diff` / `stage_and_commit`:
    - **Nosotros:** `«estado de git»`, `«git log»`, `«ultimos commits»`, `«git diff»`
    - **API:** `/call dev-git repo_status {"repo_path": "."}`
    - **API:** `/call dev-git repo_log {"repo_path": ".", "limit": 5}`
    - **API:** `/call dev-git repo_diff {"repo_path": ".", "staged": false}`
    - **API:** `/call dev-git stage_and_commit {"repo_path": ".", "files": ["README.md"], "message": "docs: update"}`

#### 13. `dev-vscodium` — Editores de Código VSCodium y Kate
* **Herramientas API y Comandos:**
  - `dev-vscodium.list_extensions` (`read`):
    - **Nosotros:** `«extensiones vscodium»`, `«plugins vscodium»`
    - **API:** `/call dev-vscodium list_extensions {}`
  - `dev-vscodium.open_in_editor` (`write`):
    - **API:** `/call dev-vscodium open_in_editor {"path": "/ruta/archivo.rs", "line": 42, "editor": "vscodium"}`

#### 14. `dev-containers-vm` — Docker, Podman, VirtualBox y QEMU/KVM (`libvirt`)
* **Herramientas API y Comandos:**
  - `dev-containers-vm.container_list` / `container_logs` (`read`):
    - **Nosotros:** `«contenedores activos»`, `«estado contenedores»`, `«docker ps»`
    - **API:** `/call dev-containers-vm container_list {"runtime": "auto"}`
    - **API:** `/call dev-containers-vm container_logs {"container": "mi-app", "tail": 50}`
  - `dev-containers-vm.vm_list` / `vm_power` (`read` / `privileged`):
    - **Nosotros:** `«maquinas virtuales»`, `«estado virtualizacion»`, `«listar vms»`
    - **API:** `/call dev-containers-vm vm_list {}`
    - **API:** `/call dev-containers-vm vm_power {"hypervisor": "libvirt", "name": "arch-vm", "action": "start"}`

#### 15. `dev-api-databases` — DBeaver, MySQL Workbench, Postman e Insomnia
* **Herramientas API y Comandos:**
  - `dev-api-databases.list_db_connections` (`read`):
    - **Nosotros:** `«conexiones dbeaver»`, `«conexiones base de datos»`
    - **API:** `/call dev-api-databases list_db_connections {}`
  - `dev-api-databases.http_get_preview` / `launch_dev_client`:
    - **API:** `/call dev-api-databases http_get_preview {"url": "https://api.github.com"}`
    - **API:** `/call dev-api-databases launch_dev_client {"app": "dbeaver"}`

---

### E. Estudio Creativo 3D, Diseño, Vídeo, Audio y Streaming (9 Conectores)

#### 16. `media-obs` — OBS Studio (Protocolo WebSocket v5 en `127.0.0.1:4455`)
* **Herramientas API y Comandos:**
  - `media-obs.obs_websocket_status` (`read`):
    - **Nosotros:** `«estado obs»`, `«iniciar streaming»`
    - **API:** `/call media-obs obs_websocket_status {"port": 4455}`
  - `media-obs.obs_request` (`write`):
    - **API:** `/call media-obs obs_request {"request_type": "StartRecord"}`
    - **API:** `/call media-obs obs_request {"request_type": "StopRecord"}`
    - **API:** `/call media-obs obs_request {"request_type": "GetSceneList"}`
  - `media-obs.launch_capture_app` (`write`):
    - **API:** `/call media-obs launch_capture_app {"app": "obs"}`

#### 17. `media-players` — Reproductores VLC y Elisa (Protocolo D-Bus `org.mpris.MediaPlayer2`)
* **Herramientas API y Comandos:**
  - `media-players.list_players` / `get_playback_status` (`read`):
    - **Nosotros:** `«reproductores activos»`, `«qué suena»`
    - **API:** `/call media-players list_players {}`
  - `media-players.control_playback` / `play_media` (`write`):
    - **API:** `/call media-players control_playback {"service": "org.mpris.MediaPlayer2.vlc", "action": "PlayPause"}`
    - **API:** `/call media-players play_media {"path": "~/Music/tema.mp3", "player": "vlc"}`

#### 18. `multimedia-ffmpeg` — Motor FFmpeg y `ffprobe`
* **Herramientas API:**
  - `/call multimedia-ffmpeg inspect_media {"path": "~/Videos/clip.mp4"}`
  - `/call multimedia-ffmpeg convert_media {"input_path": "~/Videos/clip.mp4", "output_path": "~/Videos/audio.mp3", "preset": "audio_only"}`

#### 19. `creative-gimp` — GIMP (Inspección Binaria + Script-Fu Batch)
* **Herramientas API:**
  - `/call creative-gimp inspect_image {"path": "~/Pictures/foto.png"}`
  - `/call creative-gimp run_script_fu {"expression": "(gimp-version)"}`

#### 20. `creative-krita` — Krita (Inspector de Capas `.kra` + Exportación Headless)
* **Herramientas API:**
  - `/call creative-krita inspect_krita_doc {"path": "~/arte.kra"}`
  - `/call creative-krita export_krita {"input_path": "~/arte.kra", "output_path": "~/arte.png"}`

#### 21. `creative-blender` — Blender 3D (Puente Python `bpy` + Renderizado de Frames)
* **Herramientas API:**
  - `/call creative-blender inspect_blend_scene {"path": "~/escena.blend"}`
  - `/call creative-blender render_frame {"blend_path": "~/escena.blend", "output_prefix": "~/render_", "frame": 1}`

#### 22. `creative-audacity` — Audacity (Tuberías FIFO `mod-script-pipe`)
* **Herramientas API y Comandos:**
  - **Nosotros:** `«estado audacity»`
  - `/call creative-audacity pipe_status {}`
  - `/call creative-audacity send_pipe_command {"command": "GetInfo: Type=Tracks"}`

#### 23. `creative-kdenlive` — Kdenlive y Motor MLT (`melt`)
* **Herramientas API:**
  - `/call creative-kdenlive inspect_project {"path": "~/proyecto.kdenlive"}`
  - `/call creative-kdenlive render_project {"project_path": "~/proyecto.kdenlive", "output_path": "~/video_final.mp4"}`

#### 24. `creative-design-photo` — Inkscape SVG, Darktable y RawTherapee
* **Herramientas API:**
  - `/call creative-design-photo inspect_svg {"path": "~/logo.svg"}`
  - `/call creative-design-photo inkscape_export {"input_path": "~/logo.svg", "output_path": "~/logo.png", "dpi": 300}`
  - `/call creative-design-photo darktable_export {"input_path": "~/foto.RAW", "output_path": "~/foto_revelada.jpg"}`

#### 25. `creative-video-transcode` — HandBrakeCLI, Shotcut y Pitivi
* **Herramientas API:**
  - `/call creative-video-transcode inspect_video_project {"path": "~/edicion.mlt"}`
  - `/call creative-video-transcode handbrake_transcode {"input_path": "~/bruto.mkv", "output_path": "~/optimizado.mp4", "preset": "Fast 1080p30"}`

---

### F. Oficina, Conocimiento, Navegador, Correo, FTP y Gaming (7 Conectores)

#### 26. `office-libreoffice` — LibreOffice (Inspección ODF/OOXML, Puente UNO y Conversión)
* **Herramientas API y Comandos:**
  - **Nosotros:** `«estado libreoffice»`
  - `/call office-libreoffice uno_status {}`
  - `/call office-libreoffice inspect_document {"path": "~/informe.docx"}`
  - `/call office-libreoffice convert_document {"input_path": "~/informe.docx", "target_format": "pdf"}`

#### 27. `office-okular` — Visor Okular y Extractor PDF (`poppler`)
* **Herramientas API:**
  - `/call office-okular inspect_pdf {"path": "~/manual.pdf"}`
  - `/call office-okular extract_pdf_text {"path": "~/manual.pdf", "first_page": 1, "last_page": 3}`
  - `/call office-okular open_document {"path": "~/manual.pdf", "page": 5}`

#### 28. `knowledge-notes-ebooks` — Segundo Cerebro Obsidian y Biblioteca Calibre
* **Herramientas API y Comandos:**
  - **Nosotros:** `«libros calibre»`, `«biblioteca calibre»`
  - `/call knowledge-notes-ebooks search_obsidian_vault {"vault_dir": "~/Obsidian", "query": "AriaOS"}`
  - `/call knowledge-notes-ebooks create_obsidian_note {"vault_dir": "~/Obsidian", "relative_path": "Notas/Idea.md", "content": "# Nueva Idea"}`
  - `/call knowledge-notes-ebooks calibre_list_books {}`
  - `/call knowledge-notes-ebooks calibre_convert_ebook {"input_path": "~/libro.epub", "output_path": "~/libro.pdf"}`

#### 29. `browser-web` — Brave y Firefox (Protocolo Chromium CDP HTTP en puerto `9222`)
* **Herramientas API y Comandos:**
  - **Nosotros:** `«pestañas abiertas»`, `«tabs del navegador»`
  - `/call browser-web list_tabs {"cdp_port": 9222}`
  - `/call browser-web search_bookmarks {"query": "github"}`
  - `/call browser-web open_url {"url": "https://archlinux.org", "browser": "auto"}`

#### 30. `comms-thunderbird` — Cliente de Correo Mozilla Thunderbird (SQLite Read-Only)
* **Herramientas API y Comandos:**
  - **Nosotros:** `«perfiles thunderbird»`, `«cuentas de correo»`
  - `/call comms-thunderbird list_profiles {}`
  - `/call comms-thunderbird search_messages {"query": "factura", "limit": 10}`
  - `/call comms-thunderbird compose_email {"to": "usuario@dominio.com", "subject": "Hola", "body": "Mensaje"}`

#### 31. `net-filezilla` — Cliente FTP/SFTP FileZilla (con Redacción Automática de Contraseñas)
* **Herramientas API y Comandos:**
  - **Nosotros:** `«sitios filezilla»`, `«servidores ftp»`, `«estado servidores»`
  - `/call net-filezilla list_sites {}`
  - `/call net-filezilla list_remote_dir {"host": "servidor.com", "user": "admin", "remote_path": "/var/www"}`

#### 32. `net-sync-comms-gaming` — Syncthing REST, qBittorrent WebUI v2 y Lanzador Gaming/Emuladores
* **Herramientas API y Comandos:**
  - **Nosotros:** `«estado syncthing»`, `«estado p2p»`, `«torrents activos»`, `«estado suite gaming»`
  - `/call net-sync-comms-gaming ecosystem_apps_status {}`
  - `/call net-sync-comms-gaming syncthing_status {"port": 8384}`
  - `/call net-sync-comms-gaming qbittorrent_torrents {"port": 8080}`
  - `/call net-sync-comms-gaming launch_ecosystem_app {"app": "steam"}`

---

### G. Subsistemas Avanzados Cyber Obsidian (7 Conectores Nuevos)

#### 33. `security-firewall` — Cortafuegos Inteligente y Monitor de Conexiones en Vivo
* **Herramientas API y Comandos:**
  - **Nosotros:** `«estado cortafuegos»`, `«conexiones activas»`, `«puertos abiertos»`
  - `/call security-firewall firewall_status {}`
  - `/call security-firewall active_connections {"limit": 50}`
  - `/call security-firewall manage_port_rule {"action": "block", "port": 8080, "protocol": "tcp"}`
  - `/call security-firewall network_lockdown {"enabled": true}`

#### 34. `os-snapshots` — Máquina del Tiempo y Puntos de Restauración del Sistema
* **Herramientas API y Comandos:**
  - **Nosotros:** `«listar snapshots»`, `«puntos de restauracion»`, `«crear snapshot»`
  - `/call os-snapshots list_snapshots {}`
  - `/call os-snapshots create_snapshot {"label": "Antes de actualizar kernel", "scope": "config"}`
  - `/call os-snapshots restore_snapshot {"snapshot_id": "snap-baseline-cyber-obsidian", "dry_run": false}`
  - `/call os-snapshots delete_snapshot {"snapshot_id": "snap-123"}`

#### 35. `security-vault` — Bóveda Criptográfica Local, Auditor SSH y Generador CSPRNG
* **Herramientas API y Comandos:**
  - **Nosotros:** `«estado boveda»`, `«auditar llaves ssh»`, `«generar clave segura»`
  - `/call security-vault vault_status {}`
  - `/call security-vault store_secret {"label": "GitHub Token", "category": "api_token", "secret_value": "ghp_xxx"}`
  - `/call security-vault list_secrets {"reveal_label": ""}`
  - `/call security-vault generate_entropy_key {"length": 28, "include_symbols": true}`

#### 36. `ai-model-manager` — Laboratorio de Modelos Locales (AI Studio) y Benchmark Neuronal
* **Herramientas API y Comandos:**
  - **Nosotros:** `«modelos de ia»`, `«benchmark de ia»`, `«velocidad de inferencia»`
  - `/call ai-model-manager list_models {}`
  - `/call ai-model-manager benchmark_inference {}`
  - `/call ai-model-manager switch_active_model {"model_name": "qwen2.5-coder:1.5b"}`
  - `/call ai-model-manager inspect_neural_memory {"add_alias_trigger": "modo código", "add_alias_target": "modo desarrollo"}`

#### 37. `network-radar` — Radar de Red, Escáner de Dispositivos LAN y DNS Privado
* **Herramientas API y Comandos:**
  - **Nosotros:** `«dispositivos en mi red»`, `«escanear red local»`, `«activar dns seguro»`, `«radar de latencia»`
  - `/call network-radar scan_lan_devices {}`
  - `/call network-radar dns_privacy_status {}`
  - `/call network-radar set_secure_dns {"provider": "quad9", "adblock_hosts": true}`
  - `/call network-radar latency_radar {}`

#### 38. `os-optimizer` — Analizador de Arranque (`systemd-analyze`) y Limpiador Profundo
* **Herramientas API y Comandos:**
  - **Nosotros:** `«analizar tiempo de arranque»`, `«limpiar sistema a fondo»`, `«espacio recuperable»`
  - `/call os-optimizer analyze_boot_time {}`
  - `/call os-optimizer scan_junk_data {}`
  - `/call os-optimizer deep_clean_system {"targets": ["user_cache", "journal_logs", "pacman_cache", "tmp_files"]}`
  - `/call os-optimizer optimize_services {"action": "list"}`

#### 39. `os-clipboard` — Portapapeles Inteligente e Historial Semántico
* **Herramientas API y Comandos:**
  - **Nosotros:** `«historial del portapapeles»`, `«que he copiado»`, `«limpiar portapapeles»`
  - `/call os-clipboard clipboard_history {"limit": 20}`
  - `/call os-clipboard copy_to_clipboard {"text": "aria-daemon telemetry"}`
  - `/call os-clipboard transform_clipboard {"operation": "format_json"}`
  - `/call os-clipboard clear_clipboard {}`

