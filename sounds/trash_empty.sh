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
HOME_TRASH="${XDG_DATA_HOME:-$HOME/.local/share}/Trash"
uid=$(id -u)

# Files trashed on other drives live in that drive's own trash
# ($topdir/.Trash-$UID or $topdir/.Trash/$UID) and are expunged there, so
# watch those too. A drive without one yet gets its root watched, so we
# rescan once gvfs creates .Trash-$UID on the first trash there.
scan() {
    EXPUNGED=("$HOME_TRASH/expunged")
    ROOTS=()
    local mnt trash found
    while read -r mnt; do
        found=
        for trash in "$mnt/.Trash-$uid" "$mnt/.Trash/$uid"; do
            if [[ -d $trash && -w $trash ]]; then
                EXPUNGED+=("$trash/expunged")
                found=1
            fi
        done
        if [[ -z $found && -w $mnt ]]; then
            ROOTS+=("$mnt")
        fi
    done < <(findmnt -rno TARGET --real | sed 's/\\x20/ /g')
    mkdir -p "${EXPUNGED[@]}"
}

# gio monitor's events, plus a "rescan" line when anything is mounted or
# unmounted (findmnt --poll blocks until the mount table changes).
events() {
    gio monitor "${EXPUNGED[@]}" "${ROOTS[@]}" &
    local gio_pid=$!
    findmnt --poll --first-only >/dev/null || true
    echo rescan 2>/dev/null || true
    kill "$gio_pid" 2>/dev/null || true
}

needs_rescan() {
    [[ $1 == rescan || $1 == *"/.Trash-$uid: created" ]]
}

# Lines look like "<watched dir>: <path>: <event>"; only items landing in
# an expunged folder count, not other activity in a watched drive root.
is_expunge() {
    [[ $1 == *"/expunged: "* && ($1 == *": moved in" || $1 == *": created") ]]
}

while :; do
    scan
    while read -r line; do
        if needs_rescan "$line"; then break; fi
        if is_expunge "$line"; then
            paplay "$SOUND" &
            # Swallow the rest of the burst, but still notice mount changes.
            while read -r -t 1 line && ! needs_rescan "$line"; do :; done
            if needs_rescan "$line"; then break; fi
        fi
    done < <(events)
    # Stop this round's gio monitor / findmnt before starting the next.
    pkill -P "$!" 2>/dev/null || true
done
