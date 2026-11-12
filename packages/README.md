# AriaOS Arch Linux Packages (`packages/`)

This directory holds Arch Linux `PKGBUILD` recipes, custom configurations, and upstream patches for AriaOS-specific packages and customized third-party programs.

| Package Directory | Purpose |
| :--- | :--- |
| [`ariaos-core/`](ariaos-core/README.md) | Packages `aria-daemon`, `core/sdk/python`, `connectors/`, and systemd units |
| [`ariaos-command-bar/`](ariaos-command-bar/README.md) | Packages `ariaOS-Command-Bar` UI and global KDE shortcut bindings |
| [`ariaos-theme/`](ariaos-theme/README.md) | `ariaOS-Theme` (KDE Plasma Breeze Dark, color schemes, fonts, branding) |
| [`ariaos-app-integrations/`](ariaos-app-integrations/README.md) | Pre-configured API hooks (LibreOffice UNO, OBS WebSocket, Browser CDP/Native Messaging, AUR builds) |

## Building Packages

Inside `AriaOS-Builder` (Arch Linux):
- Build a package: `makepkg -s` inside its directory.
- Fetch & patch any upstream Arch package source: `pkgctl repo clone <pkg>` (from `devtools`).
