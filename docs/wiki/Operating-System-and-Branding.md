# Operating System & Branding

AriaOS is built directly from Arch Linux (`archiso` releng base) paired with **KDE Plasma 6** (Wayland + X11 support via `qt6-wayland` and `sddm`).

## System Identity & Live Session

- **Hostname**: `ariaos` (`os/archiso/airootfs/etc/hostname`)
- **OS Identity**: `/etc/os-release` defines `NAME="AriaOS"`, `PRETTY_NAME="AriaOS Linux"`, `ID=ariaos`, `ID_LIKE=arch`, and `LOGO=ariaos-logo` so **KInfoCenter** and System Settings display AriaOS branding natively.
- **Default Live User**: `aria` (UID `1000`, member of `wheel` with passwordless `sudo` configured in `/etc/sudoers.d/10-wheel`, shell `/usr/bin/zsh`).
- **Display Manager**: SDDM configured for automatic login into Plasma (`os/archiso/airootfs/etc/sddm.conf.d/autologin.conf`).
- **Systemd Services Enabled by Default**:
  - `aria-daemon.service` (`/usr/bin/aria-daemon`, creates `/run/ariaos/`)
  - `ollama.service` (configured with drop-in `override.conf` binding `127.0.0.1:11434`)
  - `ariaos-onboarding.service` (runs on first internet connection to pre-warm `qwen2.5:3b` and initialize ClamAV)
  - `clamav-freshclam.service`, `clamav-daemon.service` & `clamav-clamonacc.service` (configured via `/usr/bin/ariaos-clamav-sync` with `OnAccessExcludeRootUID yes`, `/var/lib/clamav/ariaos-trusted.fp` SHA-256 whitelist, and `ExcludePath` guards so ClamAV protects user data without blocking or freezing the AI/OS daemon)
  - `NetworkManager.service` & `sddm.service`

## Welcome Center, Live Desktop & Disk Installer

- **Welcome Center (`ariaos-welcome`)**:
  - Automatically launches on first login (`/etc/xdg/autostart/ariaos-welcome.desktop`) to provide a central control panel:
    - Live checks for Internet, Ollama model status (`qwen2.5:3b`), and ClamAV database freshness.
    - One-click buttons to download/update the AI model, refresh virus signatures, launch the AI Command Bar, or open Dolphin.
    - Guided installation links for extra software suites (`ariaos-install-apps`) and full disk installation.
- **Desktop Launchers**:
  - Live user desktop (`/home/aria/Desktop/`) and new user template (`/etc/skel/Desktop/`) include:
    - **Bienvenido a AriaOS** (`ariaos-welcome.desktop`)
    - **Barra IA de AriaOS** (`ariaos-command-bar.desktop`)
    - **Instalar AriaOS en Disco** (`ariaos-installer.desktop`) launching guided `archinstall` in Konsole.

## File Manager (KDE Dolphin) & Built-In Free Antivirus (ClamAV)

- **KDE Dolphin Enhanced Suite**:
  - Live ISO installs `dolphin`, `dolphin-plugins`, `kio-extras`, `kio-admin`, `ffmpegthumbs`, `kdegraphics-thumbnailers`, and `kimageformats` for SFTP/SMB/MTP shares, inline renaming, status-bar free space (`dolphinrc`), and rich video/RAW/PDF/archive previews.
  - Right-click KIO Service Menus (`/usr/share/kio/servicemenus/ariaos-files-ai.desktop`) expose **Organize folder (safe dry-run)**, **Find duplicates (SHA-256)**, and **AriaOS AI Command Bar** directly inside Dolphin (`ariaos-file-action`).
- **100% Free Open-Source Antivirus (`clamav` + `security-antivirus`)**:
  - Zero-cost, GPLv2 ClamAV engine preinstalled in the base system (`clamscan`, `clamdscan`, `freshclam`, `clamonacc`).
  - Right-click any file or folder in Dolphin via **Scan with AriaOS Antivirus (ClamAV)** (`/usr/share/kio/servicemenus/ariaos-antivirus.desktop` -> `ariaos-av-scan`), with desktop notifications and one-click isolation into `~/.local/share/ariaos/quarantine/`.
  - Controlled naturally via the AI connector `security-antivirus` (scan paths, inspect status/DB freshness, update definitions, and safely quarantine or restore files).

## Visual Branding Pipeline (`AriaOS.jpeg` & `ariaos-inicio.mp4`)

AriaOS integrates native branding from power-on through the desktop session:

1. **Bootloader Menus**:
   - **BIOS (`syslinux`)**: Uses `os/archiso/syslinux/splash.png` (640x480 derived from `AriaOS.jpeg`) with `MENU TITLE AriaOS` and `quiet splash loglevel=3 vt.global_cursor_default=0`.
   - **UEFI (`systemd-boot`)**: Entry `os/archiso/efiboot/loader/entries/01-archiso-linux.conf` titled `AriaOS (%ARCH%, UEFI)` with silent splash kernel parameters.
2. **Animated Kernel Boot Splash (Plymouth)**:
   - `mkinitcpio` (`os/archiso/airootfs/etc/mkinitcpio.conf.d/archiso.conf`) enables `kms` and `plymouth` hooks with `zstd` initramfs compression.
   - During ISO staging, `os/scripts/build-iso.sh` uses `ffmpeg` to extract 120 frames (`12 fps`, `768x432`) from `assets/branding/ariaos-inicio.mp4` into `/usr/share/plymouth/themes/ariaos/frames/`.
   - `/usr/share/plymouth/themes/ariaos/ariaos.script` renders the smooth startup animation centered on a `#05080d` canvas (falling back to static `logo.png` if frames are absent) until SDDM takes over.
3. **SDDM Login, Lock Screen & KDE Plasma 6 Desktop**:
   - **Wallpaper**: `assets/branding/ariaos-wallpaper.jpg` (`2816x1536`) is installed as `/usr/share/wallpapers/AriaOS/contents/images/2816x1536.jpg` and configured on SDDM (`theme.conf.user`), Lock Screen (`/etc/xdg/kscreenlockerrc`), and Plasma desktop.
   - **Menu & System Icons**: `assets/branding/ariaos-logo.png` (`512x512` circular emblem) is installed into hicolor icons (`/usr/share/icons/hicolor/512x512/apps/ariaos-logo.png`), `/usr/share/pixmaps/ariaos-logo.png`, `/home/aria/.face.icon`, and `/etc/skel/.face.icon`.
   - **First-Login Autostart**: `/etc/xdg/autostart/ariaos-branding.desktop` invokes `/usr/bin/ariaos-apply-branding` once per user (`~/.config/.ariaos-branded-v1`) to apply the desktop wallpaper via `plasma-apply-wallpaperimage` and set the Kickoff/Kicker Start Menu icon to `ariaos-logo` via `qdbus6`.
