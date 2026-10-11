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

# Thunar navigation click: a user script started by XFCE autostart.
CLICK_BIN="$HOME/.local/bin/redmond2k-navigation-click"
CLICK_DESKTOP="$HOME/.config/autostart/redmond2k-navigation-click.desktop"
mkdir -p "$(dirname "$CLICK_BIN")" "$(dirname "$CLICK_DESKTOP")"
install -m 755 "$SCRIPT_DIR/navigation_click.sh" "$CLICK_BIN"
cat > "$CLICK_DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Name=Redmond2K Navigation Click
Comment=Plays the click sound when Thunar changes folder
Exec=$CLICK_BIN
OnlyShowIn=XFCE;
StartupNotify=false
Terminal=false
EOF
echo "Installed navigation click to $CLICK_BIN (autostarts on login)"

for dep in xdotool xprop paplay; do
    command -v "$dep" >/dev/null 2>&1 \
        || echo "Warning: $dep not found - navigation click needs it" >&2
done

# Empty-trash sound: watches gvfs's expunge folder, see trash_empty.sh.
TRASH_BIN="$HOME/.local/bin/redmond2k-trash-sound"
TRASH_DESKTOP="$HOME/.config/autostart/redmond2k-trash-sound.desktop"
install -m 755 "$SCRIPT_DIR/trash_empty.sh" "$TRASH_BIN"
cat > "$TRASH_DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Name=Redmond2K Empty Trash Sound
Comment=Plays the empty recycle bin sound when the trash is emptied
Exec=$TRASH_BIN
OnlyShowIn=XFCE;
StartupNotify=false
Terminal=false
EOF
echo "Installed empty-trash sound to $TRASH_BIN (autostarts on login)"

# Restart both now so a reinstall picks up the new scripts without re-login.
for bin in "$CLICK_BIN" "$TRASH_BIN"; do
    pkill -f "$bin" 2>/dev/null || true
    if [[ -n "${DISPLAY:-}" ]]; then
        setsid -f "$bin" >/dev/null 2>&1
    fi
done
