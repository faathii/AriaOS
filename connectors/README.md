# AriaOS Connectors

Each directory here represents **one application, system service, or tool domain** that the AriaOS AI can control through a unified API contract.

## Active & Planned Connectors

| Directory | Tier | Transport | Purpose |
| :--- | :--- | :--- | :--- |
| `_template/` | — | `stdio` | Starter template for adding new programs |
| `os-files/` | `program_api` | `stdio` | File inspection, smart organization, duplicate detection |
| `os-system/` | `os_ipc` | `dbus` | `systemd` services, hardware health, disk/RAM, `pacman` queries |
| `os-desktop/` | `os_ipc` | `dbus` | KDE Plasma / KWin windows, notifications, clipboard, UI fallback |
| `multimedia-ffmpeg/` | `program_api` | `stdio` | Video, audio, and image processing via FFmpeg & ImageMagick |

## Adding a New Program

See [docs/CONNECTOR_GUIDE.md](../docs/CONNECTOR_GUIDE.md) and copy `_template/`.

