# AriaOS Connectors

Each directory here represents **one application, system service, or tool domain** that the AriaOS AI can control through a unified API contract.

## Implemented Connectors (Active)

| Directory | Tier | Transport | Purpose |
| :--- | :--- | :--- | :--- |
| [`_template/`](_template/README.md) | — | `stdio` | Starter template for adding new programs |
| [`os-kernel/`](os-kernel/manifest.json) | `os_ipc` | `stdio` | Linux Kernel telemetry, PSI/thermal sensors, `dmesg`, `lspci`/`lsusb`/IP, `sysctl`, and `modprobe` |
| [`os-power-modes/`](os-power-modes/manifest.json) | `os_ipc` | `stdio` | Kernel Work Modes (`gaming`, `development`, `creative`, `powersave`, `security`) & GPU/DRM telemetry |
| [`os-automation/`](os-automation/manifest.json) | `os_ipc` | `stdio` | Persistent Synaptic Neural Memory (`neural_memory.json`) and scheduled background OS automations |
| [`os-files/`](os-files/manifest.json) | `program_api` | `stdio` | KDE Dolphin integration, search, metadata, duplicates, XDG Trash, and safe folder organization |
| [`os-system/`](os-system/README.md) | `os_ipc` | `stdio` | `systemd` services, hardware health, CPU/RAM/disk, top processes (`KInfoCenter`) |
| [`os-desktop/`](os-desktop/README.md) | `os_ipc` | `stdio` | KDE Plasma / KWin session info, notifications, application launcher |
| [`os-packages/`](os-packages/README.md) | `program_api` | `stdio` | `pacman` package search/install, update checks, and safe `paccache` cleanup |
| [`os-storage/`](os-storage/README.md) | `program_api` | `stdio` | Disk/partition inspection (`lsblk`) and safe `.zip`/`.tar.gz` archive operations |
| [`multimedia-ffmpeg/`](multimedia-ffmpeg/README.md) | `program_api` | `stdio` | Video, audio, and image processing via FFmpeg & ImageMagick |
| [`dev-git/`](dev-git/README.md) | `program_api` | `stdio` | Git repository status, logs, diffs, and safe commits |
| [`dev-vscodium/`](dev-vscodium/README.md) | `program_api` | `stdio` | Open files at line/col in VSCodium or Kate, list extensions |
| [`office-libreoffice/`](office-libreoffice/README.md) | `program_api` | `stdio` | Inspect ODF/OOXML docs, UNO probe, and headless LibreOffice conversion |
| [`office-okular/`](office-okular/README.md) | `program_api` | `stdio` | Inspect PDFs, extract text (`poppler`), and open docs in Okular |
| [`comms-thunderbird/`](comms-thunderbird/README.md) | `program_api` | `stdio` | Inspect Thunderbird profiles, read-only SQLite search, safe compose |
| [`browser-web/`](browser-web/README.md) | `program_api` | `stdio` | Brave CDP tabs, bookmarks search, and Brave/Firefox URL launcher |
| [`net-filezilla/`](net-filezilla/README.md) | `program_api` | `stdio` | Redacted FileZilla `sitemanager.xml` reader and `sftp` directory listing |
| [`media-obs/`](media-obs/README.md) | `program_api` | `stdio` | OBS WebSocket v5 client (status, scenes, record/stream) and Kamoso launcher |
| [`media-players/`](media-players/README.md) | `program_api` | `stdio` | VLC, Elisa, and MPRIS2 D-Bus playback inspection and control |
| [`creative-gimp/`](creative-gimp/README.md) | `program_api` | `stdio` | Image/XCF header inspection and headless GIMP Script-Fu |
| [`creative-krita/`](creative-krita/README.md) | `program_api` | `stdio` | `.kra` layer/canvas inspector and headless Krita CLI export |
| [`creative-blender/`](creative-blender/README.md) | `program_api` | `stdio` | `.blend` scene inspection via `bpy` and headless frame rendering |
| [`creative-audacity/`](creative-audacity/README.md) | `program_api` | `stdio` | Audacity `mod-script-pipe` FIFO status and command bridge |
| [`creative-kdenlive/`](creative-kdenlive/README.md) | `program_api` | `stdio` | `.kdenlive` MLT timeline inspector and headless `melt` render |
| [`creative-design-photo/`](creative-design-photo/manifest.json) | `program_api` | `stdio` | Inkscape SVG inspection/export and Darktable/RawTherapee RAW export |
| [`creative-video-transcode/`](creative-video-transcode/manifest.json) | `program_api` | `stdio` | HandBrakeCLI transcoding and Shotcut/Pitivi project inspection |
| [`knowledge-notes-ebooks/`](knowledge-notes-ebooks/manifest.json) | `program_api` | `stdio` | Obsidian vault search/notes and Calibre library/conversion |
| [`security-antivirus/`](security-antivirus/manifest.json) | `program_api` | `stdio` | 100% free ClamAV malware scanning, signature updates (`freshclam`), and reversible quarantine vault |
| [`security-firewall/`](security-firewall/manifest.json) | `os_ipc` | `stdio` | Intelligent Firewall (`nftables`/`ufw`), live TCP/UDP socket monitor (`/proc/net/tcp`, `ss`), and emergency network lockdown |
| [`security-vault-crypto/`](security-vault-crypto/manifest.json) | `program_api` | `stdio` | KeePassXC `.kdbx` check, VeraCrypt volumes, Timeshift, Flameshot |
| [`security-net-audit/`](security-net-audit/manifest.json) | `program_api` | `stdio` | Wireshark/tshark PCAP, ELF/PE headers (Ghidra/Cutter), Nmap & suite status |
| [`dev-containers-vm/`](dev-containers-vm/manifest.json) | `program_api` | `stdio` | Docker/Podman/Portainer containers and VirtualBox/QEMU-KVM control |
| [`dev-api-databases/`](dev-api-databases/manifest.json) | `program_api` | `stdio` | DBeaver/MySQL Workbench connections, HTTP preview, Postman/Insomnia |
| [`net-sync-comms-gaming/`](net-sync-comms-gaming/manifest.json) | `program_api` | `stdio` | Syncthing, qBittorrent APIs and Steam/Lutris/Emulators/Comms launcher |

## Adding a New Connector

## Adding a New Program

See [docs/CONNECTOR_GUIDE.md](../docs/CONNECTOR_GUIDE.md) and copy `_template/`.
