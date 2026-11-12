# ISO Build & Arch Packaging

AriaOS builds both **native Arch Linux packages** (`packages/`) and **bootable hybrid BIOS/UEFI Live & Install ISOs** (`os/archiso/`).

## Building the Bootable ISO (`os/scripts/build-iso.sh`)

Run inside an Arch Linux environment with `archiso`, `rust`, and `ffmpeg` installed (such as the `AriaOS-Builder` VM):

```bash
ARIAOS_OUT_DIR=/var/tmp/ariaos-out bash os/scripts/build-iso.sh
```

### What `build-iso.sh` Does in 4 Stages

1. **Builds `aria-daemon`** in `--release` mode (`core/daemon/Cargo.toml`, native target dir `/var/tmp/aria-target`).
2. **Stages `os/archiso/`** into `/var/tmp/ariaos-profile` (so POSIX symlinks and permissions remain intact even when building from a VirtualBox shared folder):
   - Installs `/usr/bin/aria-daemon` and `/usr/bin/aria-command-bar`.
   - Installs `core/sdk/python/aria_sdk`, all 28 connectors, and `ui/command-bar/` into `/usr/lib/ariaos/`.
   - Installs wallpapers, logos, icons, and extracts 120 Plymouth animation frames from `assets/branding/ariaos-inicio.mp4`.
   - Normalizes any CRLF line endings from Windows checkouts.
3. **Enables Systemd Units** (`aria-daemon.service`, `ollama.service`, `NetworkManager.service`, `display-manager.service -> sddm.service`).
4. **Runs `mkarchiso`** with `zstd` SquashFS compression (`profiledef.sh`) to emit `ariaos-YYYY.MM.DD-x86_64.iso`.

## Native Arch `PKGBUILD` Recipes (`packages/`)

- `packages/ariaos-core/PKGBUILD` — `aria-daemon`, Python SDK, 28 connectors, `aria-daemon.service`
- `packages/ariaos-command-bar/PKGBUILD` — Floating PyQt6 Command Bar & desktop entry
- `packages/ariaos-theme/PKGBUILD` — Wallpaper, Plymouth assets, system icons, first-login script
- `packages/ariaos-app-integrations/PKGBUILD` — `ariaos-install-apps` & full/AUR suite manifests

Build any package inside Arch Linux with `makepkg -s` in its directory, or compile all AUR packages into a local pacman repository using:

```bash
bash packages/aur/build-aur-repo.sh
```
