#!/usr/bin/env bash
# Plays every mapped sound in the Redmond2K theme via the freedesktop
# sound theme lookup (canberra), so it tests exactly what XFCE plays.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STEREO_DIR="$SCRIPT_DIR/Redmond2K/stereo"

if ! command -v canberra-gtk-play >/dev/null 2>&1; then
    echo "canberra-gtk-play not found - install libcanberra-gtk3 / libcanberra-utils" >&2
    exit 1
fi

for wav in "$STEREO_DIR"/*.wav; do
    event="$(basename "$wav" .wav)"
    echo "Playing: $event"
    canberra-gtk-play -i "$event" -d "redmond2k-test-$event"
    sleep 0.5
done
