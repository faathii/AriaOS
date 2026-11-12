#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ARCHISO_SRC="$(cd "${SCRIPT_DIR}/../archiso" && pwd)"

# Use native Linux temp storage for staging, Rust target, and mkarchiso work_dir
# so POSIX symlinks/permissions work cleanly even over VirtualBox shared folders.
STAGE_DIR="${ARIAOS_STAGE_DIR:-/var/tmp/ariaos-profile}"
WORK_DIR="${ARIAOS_WORK_DIR:-/var/tmp/ariaos-work}"
OUT_DIR="${ARIAOS_OUT_DIR:-${ARCHISO_SRC}/out}"
CARGO_TARGET="${ARIAOS_CARGO_TARGET:-/var/tmp/aria-target}"

if ! command -v mkarchiso >/dev/null 2>&1; then
  echo "Error: mkarchiso not found. Run this script on Arch Linux with 'archiso' installed." >&2
  exit 1
fi
if ! command -v cargo >/dev/null 2>&1; then
  echo "Error: cargo not found. Install 'rust' to compile aria-daemon before building the ISO." >&2
  exit 1
fi

echo "[1/4] Building aria-daemon (release)..."
cargo build --release \
  --manifest-path "${REPO_ROOT}/core/daemon/Cargo.toml" \
  --target-dir "${CARGO_TARGET}"

echo "[2/4] Staging archiso profile in ${STAGE_DIR}..."
sudo rm -rf "${STAGE_DIR}" "${WORK_DIR}"
mkdir -p "${STAGE_DIR}" "${WORK_DIR}" "${OUT_DIR}"
cp -a "${ARCHISO_SRC}/." "${STAGE_DIR}/"
rm -rf "${STAGE_DIR}/out"

# Install compiled aria-daemon binary
install -Dm755 "${CARGO_TARGET}/release/aria-daemon" "${STAGE_DIR}/airootfs/usr/bin/aria-daemon"

# Install AriaOS Python SDK, active connectors, and Command Bar UI
mkdir -p "${STAGE_DIR}/airootfs/usr/lib/ariaos/core/sdk/python"
cp -a "${REPO_ROOT}/core/sdk/python/aria_sdk" "${STAGE_DIR}/airootfs/usr/lib/ariaos/core/sdk/python/"
mkdir -p "${STAGE_DIR}/airootfs/usr/lib/ariaos/connectors"
cp -a "${REPO_ROOT}/connectors/." "${STAGE_DIR}/airootfs/usr/lib/ariaos/connectors/"
mkdir -p "${STAGE_DIR}/airootfs/usr/lib/ariaos/command-bar"
cp -a "${REPO_ROOT}/ui/command-bar/." "${STAGE_DIR}/airootfs/usr/lib/ariaos/command-bar/"
install -Dm644 "${REPO_ROOT}/ui/command-bar/ariaos-command-bar.desktop" \
  "${STAGE_DIR}/airootfs/usr/share/applications/ariaos-command-bar.desktop"
mkdir -p "${STAGE_DIR}/airootfs/usr/lib/ariaos/welcome"
cp -a "${REPO_ROOT}/ui/welcome/." "${STAGE_DIR}/airootfs/usr/lib/ariaos/welcome/"
install -Dm644 "${REPO_ROOT}/ui/welcome/ariaos-welcome.desktop" \
  "${STAGE_DIR}/airootfs/usr/share/applications/ariaos-welcome.desktop"
mkdir -p "${STAGE_DIR}/airootfs/usr/lib/ariaos/settings"
cp -a "${REPO_ROOT}/ui/settings/." "${STAGE_DIR}/airootfs/usr/lib/ariaos/settings/"
install -Dm644 "${REPO_ROOT}/ui/settings/ariaos-settings.desktop" \
  "${STAGE_DIR}/airootfs/usr/share/applications/ariaos-settings.desktop"
mkdir -p "${STAGE_DIR}/airootfs/usr/lib/ariaos/antivirus"
cp -a "${REPO_ROOT}/ui/antivirus/." "${STAGE_DIR}/airootfs/usr/lib/ariaos/antivirus/"
mkdir -p "${STAGE_DIR}/airootfs/usr/lib/ariaos/monitor"
cp -a "${REPO_ROOT}/ui/monitor/." "${STAGE_DIR}/airootfs/usr/lib/ariaos/monitor/"
install -Dm644 "${REPO_ROOT}/ui/monitor/ariaos-monitor.desktop" \
  "${STAGE_DIR}/airootfs/usr/share/applications/ariaos-monitor.desktop"
mkdir -p "${STAGE_DIR}/airootfs/usr/lib/ariaos/store"
cp -a "${REPO_ROOT}/ui/store/." "${STAGE_DIR}/airootfs/usr/lib/ariaos/store/"
install -Dm644 "${REPO_ROOT}/ui/store/ariaos-store.desktop" \
  "${STAGE_DIR}/airootfs/usr/share/applications/ariaos-store.desktop"
mkdir -p "${STAGE_DIR}/airootfs/usr/lib/ariaos/automations"
cp -a "${REPO_ROOT}/ui/automations/." "${STAGE_DIR}/airootfs/usr/lib/ariaos/automations/"
install -Dm644 "${REPO_ROOT}/ui/automations/ariaos-automations.desktop" \
  "${STAGE_DIR}/airootfs/usr/share/applications/ariaos-automations.desktop"
mkdir -p "${STAGE_DIR}/airootfs/usr/lib/ariaos/firewall"
cp -a "${REPO_ROOT}/ui/firewall/." "${STAGE_DIR}/airootfs/usr/lib/ariaos/firewall/"
install -Dm644 "${REPO_ROOT}/ui/firewall/ariaos-firewall.desktop" \
  "${STAGE_DIR}/airootfs/usr/share/applications/ariaos-firewall.desktop"
mkdir -p "${STAGE_DIR}/airootfs/usr/lib/ariaos/installer"
cp -a "${REPO_ROOT}/ui/installer/." "${STAGE_DIR}/airootfs/usr/lib/ariaos/installer/"
install -Dm644 "${REPO_ROOT}/ui/installer/ariaos-installer.desktop" \
  "${STAGE_DIR}/airootfs/usr/share/applications/ariaos-installer.desktop"

# Install AriaOS visual branding (boot splash, menu/system icon, wallpaper, face icon)
if [ -f "${REPO_ROOT}/assets/branding/ariaos-wallpaper.jpg" ]; then
  install -Dm644 "${REPO_ROOT}/assets/branding/ariaos-wallpaper.jpg" \
    "${STAGE_DIR}/airootfs/usr/share/wallpapers/AriaOS/contents/images/2816x1536.jpg"
fi
if [ -f "${REPO_ROOT}/assets/branding/ariaos-logo.png" ]; then
  install -Dm644 "${REPO_ROOT}/assets/branding/ariaos-logo.png" \
    "${STAGE_DIR}/airootfs/usr/share/icons/hicolor/512x512/apps/ariaos-logo.png"
  install -Dm644 "${REPO_ROOT}/assets/branding/ariaos-logo.png" \
    "${STAGE_DIR}/airootfs/usr/share/pixmaps/ariaos-logo.png"
  install -Dm644 "${REPO_ROOT}/assets/branding/ariaos-logo.png" \
    "${STAGE_DIR}/airootfs/home/aria/.face.icon"
  install -Dm644 "${REPO_ROOT}/assets/branding/ariaos-logo.png" \
    "${STAGE_DIR}/airootfs/etc/skel/.face.icon"
fi
if [ -f "${REPO_ROOT}/assets/branding/ariaos-boot-logo.png" ]; then
  install -Dm644 "${REPO_ROOT}/assets/branding/ariaos-boot-logo.png" \
    "${STAGE_DIR}/airootfs/usr/share/plymouth/themes/ariaos/logo.png"
fi
if [ -f "${REPO_ROOT}/assets/branding/ariaos-inicio.mp4" ]; then
  install -Dm644 "${REPO_ROOT}/assets/branding/ariaos-inicio.mp4" \
    "${STAGE_DIR}/airootfs/usr/share/ariaos/ariaos-inicio.mp4"
  if command -v ffmpeg >/dev/null 2>&1; then
    echo "  Extracting Plymouth boot animation frames from ariaos-inicio.mp4..."
    FRAMES_DIR="${STAGE_DIR}/airootfs/usr/share/plymouth/themes/ariaos/frames"
    mkdir -p "${FRAMES_DIR}"
    ffmpeg -v error -y -i "${REPO_ROOT}/assets/branding/ariaos-inicio.mp4" \
      -vf "fps=12,scale=768:432" -frames:v 120 "${FRAMES_DIR}/frame-%04d.png"
  fi
fi

# Strip any CRLF line endings if staged from a Windows working tree
find "${STAGE_DIR}" -maxdepth 7 -type f \( -name "*.sh" -o -name "*.service" -o -name "*.conf" -o -name "*.desktop" -o -name "*.py" -o -name "*.cfg" -o -name "*.plymouth" -o -name "*.script" -o -name "*.user" -o -name "*.colors" -o -name "*.json" -o -name "Modelfile*" -o -name "*rc" -o -name "kdeglobals" -o -name "colors" \) -exec sed -i 's/\r$//' {} +
sed -i 's/\r$//' \
  "${STAGE_DIR}/profiledef.sh" \
  "${STAGE_DIR}/packages.x86_64" \
  "${STAGE_DIR}/pacman.conf" \
  "${STAGE_DIR}/airootfs/etc/hostname" \
  "${STAGE_DIR}/airootfs/etc/os-release" \
  "${STAGE_DIR}/airootfs/etc/passwd" \
  "${STAGE_DIR}/airootfs/etc/group" \
  "${STAGE_DIR}/airootfs/etc/shadow" \
  "${STAGE_DIR}/airootfs/etc/xdg/kscreenlockerrc" \
  "${STAGE_DIR}/airootfs/home/aria/.config/dolphinrc" \
  "${STAGE_DIR}/airootfs/etc/skel/.config/dolphinrc" \
  "${STAGE_DIR}/airootfs/usr/bin/aria-command-bar" \
  "${STAGE_DIR}/airootfs/usr/bin/ariaos-apply-branding" \
  "${STAGE_DIR}/airootfs/usr/bin/ariaos-av-scan" \
  "${STAGE_DIR}/airootfs/usr/bin/ariaos-clamav-sync" \
  "${STAGE_DIR}/airootfs/usr/bin/ariaos-file-action" \
  "${STAGE_DIR}/airootfs/usr/bin/ariaos-install-apps" \
  "${STAGE_DIR}/airootfs/usr/bin/ariaos-onboarding" \
  "${STAGE_DIR}/airootfs/usr/bin/ariaos-settings" \
  "${STAGE_DIR}/airootfs/usr/bin/ariaos-welcome" \
  "${STAGE_DIR}/airootfs/usr/bin/ariaos-monitor" \
  "${STAGE_DIR}/airootfs/usr/bin/ariaos-store" \
  "${STAGE_DIR}/airootfs/usr/bin/ariaos-automations" \
  "${STAGE_DIR}/airootfs/usr/bin/ariaos-firewall" \
  "${STAGE_DIR}/airootfs/usr/bin/ariaos-installer"

# Pre-package lightweight Aria Neural Model (aria-core / qwen2.5:0.5b ~350MB) inside ISO if ollama is available on build host
if command -v ollama >/dev/null 2>&1; then
  echo "  Pre-packaging lightweight Aria Neural Model (aria-core / qwen2.5:0.5b) into ISO..."
  OLLAMA_MODELS_STAGE="${STAGE_DIR}/airootfs/usr/share/ollama/.ollama/models"
  mkdir -p "${OLLAMA_MODELS_STAGE}"
  if [ -d "/usr/share/ollama/.ollama/models" ]; then
    cp -a /usr/share/ollama/.ollama/models/. "${OLLAMA_MODELS_STAGE}/" || true
  fi
fi

echo "[3/4] Enabling systemd units inside airootfs..."
WANTS_DIR="${STAGE_DIR}/airootfs/etc/systemd/system/multi-user.target.wants"
mkdir -p "${WANTS_DIR}"
ln -sf "/etc/systemd/system/aria-daemon.service" "${WANTS_DIR}/aria-daemon.service"
ln -sf "/etc/systemd/system/ariaos-onboarding.service" "${WANTS_DIR}/ariaos-onboarding.service"
ln -sf "/usr/lib/systemd/system/ollama.service" "${WANTS_DIR}/ollama.service"
ln -sf "/usr/lib/systemd/system/NetworkManager.service" "${WANTS_DIR}/NetworkManager.service"
# Note: ClamAV services (clamd/clamonacc/freshclam) are intentionally kept on-demand via Aria Shield
# to save >2GB of RAM during boot and prevent Live ISO tmpfs exhaustion.
ln -sf "/usr/lib/systemd/system/sddm.service" "${STAGE_DIR}/airootfs/etc/systemd/system/display-manager.service"

echo "[4/4] Running mkarchiso..."
sudo mkarchiso -v -w "${WORK_DIR}" -o "${OUT_DIR}" "${STAGE_DIR}"
echo "ISO build complete in: ${OUT_DIR}"
