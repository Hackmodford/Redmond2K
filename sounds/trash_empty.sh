#!/usr/bin/env bash
# Plays the Win2K "Empty Recycle Bin" sound when the trash is emptied.
# Thunar doesn't use libcanberra, so the theme's trash-empty event never
# fires. Instead we watch gvfs's expunge folder: when items are permanently
# deleted from the trash (Empty Trash, or Delete inside trash:///), gvfs
# first moves each one into Trash/expunged and then removes it. Restoring
# from the trash doesn't touch that folder, so it stays silent. Emptying
# many items sends a burst of events; play once, then wait for 1s of quiet.
set -euo pipefail

SOUND="$HOME/.local/share/sounds/Redmond2K/stereo/trash-empty.wav"
EXPUNGED="${XDG_DATA_HOME:-$HOME/.local/share}/Trash/expunged"

mkdir -p "$EXPUNGED"
gio monitor "$EXPUNGED" | while read -r line; do
    [[ $line == *": moved in" || $line == *": created" ]] || continue
    paplay "$SOUND" &
    while read -r -t 1 _; do :; done
done
