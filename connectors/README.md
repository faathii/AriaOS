# AriaOS Connectors

Each directory here represents **one application, system service, or tool domain** that the AriaOS AI can control through a unified API contract.

## Implemented Connectors (Active)

| Directory | Tier | Transport | Purpose |
| :--- | :--- | :--- | :--- |
| [`_template/`](_template/README.md) | — | `stdio` | Starter template for adding new programs |
| [`os-files/`](os-files/manifest.json) | `program_api` | `stdio` | File inspection, smart organization, duplicate detection (Dolphin / `fd` / `rg`) |
| [`os-system/`](os-system/README.md) | `os_ipc` | `stdio` | `systemd` services, hardware health, CPU/RAM/disk, top processes (`KInfoCenter`) |
| [`os-desktop/`](os-desktop/README.md) | `os_ipc` | `stdio` | KDE Plasma / KWin session info, notifications, application launcher |
| [`os-packages/`](os-packages/README.md) | `program_api` | `stdio` | `pacman` package search/install, update checks, and safe `paccache` cleanup |
| [`os-storage/`](os-storage/README.md) | `program_api` | `stdio` | Disk/partition inspection (`lsblk`) and safe `.zip`/`.tar.gz` archive operations |
| [`multimedia-ffmpeg/`](multimedia-ffmpeg/README.md) | `program_api` | `stdio` | Video, audio, and image processing via FFmpeg & ImageMagick |
| [`dev-git/`](dev-git/README.md) | `program_api` | `stdio` | Git repository status, logs, diffs, and safe commits |

## Planned Program Connectors (Scaffolded)

| Directory | Target Programs | API / Bridge |
| :--- | :--- | :--- |
| [`office-libreoffice/`](office-libreoffice/README.md) | LibreOffice Writer, Calc, Impress, Base | UNO API (`pyuno`) + headless CLI |
| [`office-okular/`](office-okular/README.md) | Okular | KDE D-Bus + `poppler` |
| [`comms-thunderbird/`](comms-thunderbird/README.md) | Thunderbird | Native Messaging / profile bridge |
| [`browser-web/`](browser-web/README.md) | Brave Browser, Firefox | CDP / WebDriver BiDi / Native Messaging |
| [`net-filezilla/`](net-filezilla/README.md) | FileZilla | Site config + `sftp`/`lftp` |
| [`media-obs/`](media-obs/README.md) | OBS Studio, Kamoso | OBS WebSocket v5 API |
| [`media-players/`](media-players/README.md) | VLC, Elisa, Kaffeine | MPRIS2 D-Bus |
| [`creative-gimp/`](creative-gimp/README.md) | GIMP | Script-Fu / Python-Fu |
| [`creative-krita/`](creative-krita/README.md) | Krita | Krita Python Scripting API |
| [`creative-blender/`](creative-blender/README.md) | Blender | `bpy` Python API |
| [`creative-audacity/`](creative-audacity/README.md) | Audacity | `mod-script-pipe` |
| [`creative-kdenlive/`](creative-kdenlive/README.md) | Kdenlive | MLT (`melt`) + Kdenlive D-Bus |
| [`dev-vscodium/`](dev-vscodium/README.md) | VSCodium, Kate | CLI + companion extension RPC |

## Adding a New Program

See [docs/CONNECTOR_GUIDE.md](../docs/CONNECTOR_GUIDE.md) and copy `_template/`.
