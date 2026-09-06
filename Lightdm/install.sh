#!/usr/bin/env bash
#
# Installs the Redmond2K lightdm-webkit greeter theme into the system themes
# directory. Re-run this after editing files under Lightdm/Redmond2K/.
#
# Usage:
#   ./install.sh                 # install to the default location
#   THEMES_DIR=/custom/path ./install.sh
#
set -euo pipefail

THEME_NAME="Redmond2K"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="${SCRIPT_DIR}/${THEME_NAME}"
THEMES_DIR="${THEMES_DIR:-/usr/share/lightdm-webkit/themes}"
DEST_DIR="${THEMES_DIR}/${THEME_NAME}"

if [[ ! -d "${SRC_DIR}" ]]; then
    echo "error: theme source not found at ${SRC_DIR}" >&2
    exit 1
fi

# Installing into a system directory needs root; re-exec through sudo if needed.
if [[ "${EUID}" -ne 0 ]]; then
    if command -v sudo >/dev/null 2>&1; then
        echo "Elevating with sudo to write to ${THEMES_DIR}..."
        exec sudo --preserve-env=THEMES_DIR "${BASH_SOURCE[0]}" "$@"
    fi
    echo "error: must be run as root (sudo not available)" >&2
    exit 1
fi

mkdir -p "${THEMES_DIR}"

# Prefer rsync so removed files are pruned; fall back to a clean cp otherwise.
if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete "${SRC_DIR}/" "${DEST_DIR}/"
else
    rm -rf "${DEST_DIR}"
    mkdir -p "${DEST_DIR}"
    cp -a "${SRC_DIR}/." "${DEST_DIR}/"
fi

echo "Installed ${THEME_NAME} to ${DEST_DIR}"
echo "Set 'webkit-theme=${THEME_NAME}' in /etc/lightdm/lightdm-webkit-greeter.conf (or the webkit2 equivalent) to use it."
