#!/usr/bin/env bash
# Plays the Win2K "Start Navigation" click when Thunar changes folder.
# Thunar has no hook for this, so we watch the active window's title: a
# title change on the *same* Thunar window means it navigated. A different
# window (new window, dialog, focus change) only resets the state, so
# opening or switching windows stays silent. Switching Thunar tabs also
# changes the title, so it clicks too. X11 only (xdotool/xprop).
set -euo pipefail

SOUND="$HOME/.local/share/sounds/Redmond2K/stereo/menu-click.wav"
prev_win=""
prev_title=""
while sleep 0.1; do
    # Either call can fail if the window closes mid-poll; treat as no window.
    win=$(xdotool getactivewindow 2>/dev/null) \
        && class=$(xprop -id "$win" WM_CLASS 2>/dev/null) \
        && [[ $class == *[Tt]hunar* ]] \
        && title=$(xdotool getwindowname "$win" 2>/dev/null) \
        || { prev_win=""; prev_title=""; continue; }
    if [[ $win == "$prev_win" && $title != "$prev_title" ]]; then
        paplay "$SOUND" &
    fi
    prev_win=$win
    prev_title=$title
done
