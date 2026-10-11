#!/usr/bin/env bash
# Swaps the xfwm4 titlebar button artwork between the styles in
# Redmond2K/xfwm4/button-styles/ and reloads the window manager.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
XFWM_DIR="$SCRIPT_DIR/Redmond2K/xfwm4"
STYLES_DIR="$XFWM_DIR/button-styles"

[ -d "$STYLES_DIR" ] || { echo "No button-styles/ in $XFWM_DIR" >&2; exit 1; }

list_styles() {
    find "$STYLES_DIR" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort
}

# A style is "active" when every .xpm it holds matches the installed copy.
is_active() {
    local style_dir="$1" f
    for f in "$style_dir"/*.xpm; do
        cmp -s "$f" "$XFWM_DIR/$(basename "$f")" || return 1
    done
    return 0
}

current_style() {
    local d
    for d in "$STYLES_DIR"/*/; do
        if is_active "${d%/}"; then basename "${d%/}"; return; fi
    done
    echo "custom"
}

if [ $# -eq 0 ]; then
    echo "Usage: $(basename "$0") <style>"
    echo
    echo "Available styles:"
    current="$(current_style)"
    while read -r s; do
        [ "$s" = "$current" ] && echo "  * $s (active)" || echo "    $s"
    done < <(list_styles)
    [ "$current" = "custom" ] && echo "  * custom (installed buttons match no style)"
    exit 0
fi

STYLE="$1"
STYLE_DIR="$STYLES_DIR/$STYLE"

if [ ! -d "$STYLE_DIR" ]; then
    echo "Unknown style '$STYLE'. Available: $(list_styles | tr '\n' ' ')" >&2
    exit 1
fi

for f in "$STYLE_DIR"/*.xpm; do
    cp "$f" "$XFWM_DIR/$(basename "$f")"
    echo "Installed $(basename "$f")"
done

# xfwm4 only rereads a theme when the setting changes, so toggle it away and back.
if command -v xfconf-query >/dev/null 2>&1 && [ -n "${DISPLAY:-}" ]; then
    theme="$(xfconf-query -c xfwm4 -p /general/theme 2>/dev/null || true)"
    if [ -n "$theme" ]; then
        xfconf-query -c xfwm4 -p /general/theme -s "Default"
        xfconf-query -c xfwm4 -p /general/theme -s "$theme"
        echo "Reloaded xfwm4 theme '$theme'"
    fi
else
    echo "Not on a running XFCE session - restart xfwm4 to see the change"
fi

echo "Button style is now '$STYLE'"
