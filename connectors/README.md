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

## Adding a New Connector

## Adding a New Program

See [docs/CONNECTOR_GUIDE.md](../docs/CONNECTOR_GUIDE.md) and copy `_template/`.
