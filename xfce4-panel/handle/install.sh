#!/usr/bin/env bash
# Build the Grab Handle panel plugin and install it for the current user.
# xfce4-panel also looks for plugins under ~/.local, so no sudo is needed.
#   ./install.sh            build + install
#   ./install.sh uninstall  remove
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
module=redmond2k-handle

if ! pkg-config --exists libxfce4panel-2.0; then
    echo "Missing panel headers: sudo dnf install xfce4-panel-devel" >&2
    exit 1
fi

# The panel pairs ~/.local/share with ~/.local/<its own libdir suffix>
# (lib64 on Fedora), so derive the suffix rather than hardcode it.
prefix="$(pkg-config --variable=prefix libxfce4panel-2.0)"
libdir="$(pkg-config --variable=libdir libxfce4panel-2.0)"
datadir="${XDG_DATA_HOME:-$HOME/.local/share}/xfce4/panel/plugins"
plugindir="$HOME/.local${libdir#"$prefix"}/xfce4/panel/plugins"

if [[ "${1:-}" == uninstall ]]; then
    rm -f "$datadir/$module.desktop" "$plugindir/lib$module.so"
    echo "Removed. Remove any Grab Handle items from the panel, then: xfce4-panel -r"
    exit 0
fi

mkdir -p "$datadir" "$plugindir"
# shellcheck disable=SC2046 # pkg-config output must word-split
gcc -shared -fPIC -O2 -Wall -o "$plugindir/lib$module.so" "$here/handle.c" \
    $(pkg-config --cflags --libs libxfce4panel-2.0 gtk+-3.0)
install -m 644 "$here/$module.desktop" "$datadir/$module.desktop"

echo "Installed. Restart the panel (xfce4-panel -r), then add \"Grab Handle\" from Panel > Add New Items."
