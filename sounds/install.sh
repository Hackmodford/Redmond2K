#!/usr/bin/env bash
# Installs the Redmond2K sound theme for the current user on XFCE.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.local/share/sounds/Redmond2K"

mkdir -p "$(dirname "$DEST")"
rm -rf "$DEST"
cp -r "$SCRIPT_DIR/Redmond2K" "$DEST"
echo "Installed theme to $DEST"

if command -v xfconf-query >/dev/null 2>&1; then
    xfconf-query -c xsettings -p /Net/SoundThemeName -s "Redmond2K" 2>/dev/null \
        || xfconf-query -c xsettings -p /Net/SoundThemeName -n -t string -s "Redmond2K"
    xfconf-query -c xsettings -p /Net/EnableEventSounds -s true 2>/dev/null \
        || xfconf-query -c xsettings -p /Net/EnableEventSounds -n -t bool -s true
    echo "Set Redmond2K as active XFCE sound theme and enabled event sounds"
else
    echo "xfconf-query not found - install the theme manually via" \
         "Settings > Appearance / Sound"
fi
