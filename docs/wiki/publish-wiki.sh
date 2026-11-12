#!/usr/bin/env bash
set -euo pipefail

# Publishes docs/wiki/*.md to the GitHub Wiki repository (AriaOS.wiki.git).
# Prerequisite: click "Wiki -> Create the first page" once on GitHub.com so AriaOS.wiki.git exists.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WIKI_URL="${1:-https://github.com/faathii/AriaOS.wiki.git}"
TMP_WIKI="$(mktemp -d)"
trap 'rm -rf "${TMP_WIKI}"' EXIT

git clone "${WIKI_URL}" "${TMP_WIKI}"
cp -f "${SCRIPT_DIR}"/*.md "${TMP_WIKI}/"
(
  cd "${TMP_WIKI}"
  git add *.md
  git commit -m "docs(wiki): publish complete AriaOS documentation wiki"
  git push origin master || git push origin main
)
