#!/usr/bin/env bash
set -euo pipefail

# Build AUR packages listed in os/archiso/packages.aur into a local pacman repo
# inside AriaOS-Builder so future `mkarchiso` runs can embed them directly.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
AUR_LIST="${REPO_ROOT}/os/archiso/packages.aur"
LOCAL_REPO="${ARIAOS_LOCAL_REPO:-/var/tmp/ariaos-local-repo}"

if [ "$(id -u)" -eq 0 ]; then
  echo "Run this script as a regular user (makepkg cannot run as root)." >&2
  exit 1
fi

mkdir -p "${LOCAL_REPO}"
BUILD_TMP="$(mktemp -d)"
trap 'rm -rf "${BUILD_TMP}"' EXIT

while IFS= read -r line; do
  pkg="$(echo "${line}" | sed 's/#.*//' | xargs)"
  [ -z "${pkg}" ] && continue
  echo "==> Building AUR package: ${pkg}"
  git clone --depth 1 "https://aur.archlinux.org/${pkg}.git" "${BUILD_TMP}/${pkg}"
  (
    cd "${BUILD_TMP}/${pkg}"
    makepkg -s --noconfirm --needed
    cp -f ./*.pkg.tar.zst "${LOCAL_REPO}/"
  )
done < "${AUR_LIST}"

repo-add "${LOCAL_REPO}/ariaos-local.db.tar.gz" "${LOCAL_REPO}"/*.pkg.tar.zst
echo "Local AUR repo ready at ${LOCAL_REPO}"
