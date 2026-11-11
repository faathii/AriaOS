#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARCHISO_DIR="$(cd "${SCRIPT_DIR}/../archiso" && pwd)"
# Use native Linux temp storage for mkarchiso work_dir so POSIX symlinks/permissions
# work cleanly even when the repo is mounted over a VirtualBox shared folder.
WORK_DIR="${ARIAOS_WORK_DIR:-/var/tmp/ariaos-work}"
OUT_DIR="${ARIAOS_OUT_DIR:-${ARCHISO_DIR}/out}"

if ! command -v mkarchiso >/dev/null 2>&1; then
  echo "Error: mkarchiso not found. Run this script on Arch Linux with 'archiso' installed." >&2
  exit 1
fi

sudo rm -rf "${WORK_DIR}"
mkdir -p "${WORK_DIR}" "${OUT_DIR}"
sudo mkarchiso -v -w "${WORK_DIR}" -o "${OUT_DIR}" "${ARCHISO_DIR}"
