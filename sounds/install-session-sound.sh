#!/usr/bin/env bash
# Installs a root daemon that plays the Redmond2K sound whenever a desktop
# session ends - logout, shutdown and restart alike. Must be run with sudo.
#
# It runs as root, outside any session, because a user's access to
# /dev/snd/* comes from a logind ACL that is revoked the instant their
# session ends, and because a stranded session scope (Fedora ships
# KillUserProcesses=no) means user@$UID.service may never stop at all.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "Run this with sudo (it installs a system service)" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_USER="${SUDO_USER:-$(logname 2>/dev/null || true)}"
ALSA_DEVICE="${REDMOND2K_ALSA_DEVICE:-plughw:0,0}"

if [ -z "$TARGET_USER" ]; then
    echo "Could not determine which user's sound theme to use - run via sudo, not as root directly" >&2
    exit 1
fi

TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"
SOUND_FILE="$TARGET_HOME/.local/share/sounds/Redmond2K/stereo/desktop-logout.wav"

if [ ! -f "$SOUND_FILE" ]; then
    echo "Sound theme not found at $SOUND_FILE - run ./install.sh as $TARGET_USER first" >&2
    exit 1
fi

if ! python3 -c "import gi; gi.require_version('Gio','2.0'); from gi.repository import Gio" 2>/dev/null; then
    echo "python3-gobject-base is required (dnf install python3-gobject-base)" >&2
    exit 1
fi

DAEMON=/usr/local/bin/redmond2k-session-sound
UNIT=/etc/systemd/system/redmond2k-session-sound.service
DROPIN_DIR=/etc/systemd/logind.conf.d
DROPIN="$DROPIN_DIR/redmond2k-inhibit-delay.conf"

sed -e "s#__SOUND_FILE__#$SOUND_FILE#" \
    -e "s#__ALSA_DEVICE__#$ALSA_DEVICE#" \
    "$SCRIPT_DIR/systemd/redmond2k-session-sound.py" > "$DAEMON"
chmod 755 "$DAEMON"
chown root:root "$DAEMON"

install -m 644 -o root -g root "$SCRIPT_DIR/systemd/redmond2k-session-sound.service" "$UNIT"

mkdir -p "$DROPIN_DIR"
install -m 644 -o root -g root "$SCRIPT_DIR/systemd/logind-inhibit-delay.conf" "$DROPIN"

systemctl daemon-reload
systemctl enable --now redmond2k-session-sound.service

echo "Installed $DAEMON (plays $SOUND_FILE on $ALSA_DEVICE)"
echo "Installed and started $UNIT"

# Superseded earlier attempt at the same job, which hung the sound off the
# user manager stopping. Harmless but redundant, and it can double-play.
OLD_USER_UNIT="$TARGET_HOME/.config/systemd/user/redmond2k-logout-sound.service"
if [ -f "$OLD_USER_UNIT" ]; then
    rm -f "$OLD_USER_UNIT" \
          "$TARGET_HOME/.config/systemd/user/default.target.wants/redmond2k-logout-sound.service"
    echo "Removed superseded user unit: $OLD_USER_UNIT"
    echo "  (run 'systemctl --user daemon-reload' as $TARGET_USER)"
fi

CURRENT_DELAY=$(busctl get-property org.freedesktop.login1 /org/freedesktop/login1 \
    org.freedesktop.login1.Manager InhibitDelayMaxUSec 2>/dev/null | awk '{print $2}')
if [ -n "${CURRENT_DELAY:-}" ] && [ "$CURRENT_DELAY" -lt 10000000 ] 2>/dev/null; then
    echo
    echo "NOTE: logind's InhibitDelayMaxSec is currently $((CURRENT_DELAY / 1000000))s."
    echo "      $DROPIN raises it to 10s, which takes effect after a reboot"
    echo "      (or 'systemctl restart systemd-logind')."
fi

echo
echo "Test the audio path without logging out:"
echo "  sudo $DAEMON --test"
echo "Watch it work:"
echo "  journalctl -fu redmond2k-session-sound.service"
