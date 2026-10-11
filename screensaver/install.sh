#!/usr/bin/env bash
# Installs the Redmond2K screen saver picker for the current user.
# Needs wine, xdotool and python3-gobject; the live preview inside the monitor
# also needs a 32-bit MinGW compiler (sudo dnf install mingw32-gcc), and
# full screen at a period resolution needs gamescope.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${XDG_DATA_HOME:-$HOME/.local/share}/redmond2k-screensaver"
BIN="$HOME/.local/bin/redmond2k-screensaver"
DESKTOP="${XDG_DATA_HOME:-$HOME/.local/share}/applications/redmond2k-screensaver.desktop"

mkdir -p "$DEST" "$(dirname "$BIN")" "$(dirname "$DESKTOP")"
install -m 755 "$SCRIPT_DIR/redmond2k-screensaver.py" "$DEST/"
# CRT shaders for "Monitor effect"; see crt/README.md.
rm -rf "$DEST/crt"
cp -r "$SCRIPT_DIR/crt" "$DEST/crt"
ln -sf "$DEST/redmond2k-screensaver.py" "$BIN"
# Menu launchers don't always have ~/.local/bin on PATH.
sed "s|^Exec=.*|Exec=$BIN|" "$SCRIPT_DIR/redmond2k-screensaver.desktop" > "$DESKTOP"
echo "Installed $BIN"

if command -v i686-w64-mingw32-gcc >/dev/null 2>&1; then
    for exe in preview-host saver-run; do
        i686-w64-mingw32-gcc -municode -mwindows -Os -s \
            -o "$DEST/$exe.exe" "$SCRIPT_DIR/$exe.c"
    done
    # Static libgcc: the rounding's 64-bit division would otherwise need
    # libgcc_s_dw2-1.dll, which Wine doesn't have.
    i686-w64-mingw32-gcc -shared -static-libgcc -Os -s \
        -o "$DEST/saver-timer.dll" "$SCRIPT_DIR/saver-timer.c"
    echo "Built preview-host.exe, saver-run.exe and saver-timer.dll"
else
    echo "i686-w64-mingw32-gcc not found - no live preview in the monitor" \
         "and no period timer speeds (sudo dnf install mingw32-gcc, then" \
         "re-run)"
fi

for tool in wine xdotool gamescope xscreensaver; do
    command -v "$tool" >/dev/null 2>&1 || echo "Warning: $tool is not installed"
done

# Savers get their own prefix so it can stay at 96 DPI whatever ~/.wine uses:
# at a higher DPI Wine draws old programs at a fraction of the resolution and
# scales them up, and the Settings dialogs are stored here too.
if command -v wine >/dev/null 2>&1; then
    export WINEPREFIX="$DEST/prefix" WINEDEBUG=-all
    if [ ! -d "$WINEPREFIX" ]; then
        echo "Creating the screen saver Wine prefix (about a minute)..."
        wineboot -i >/dev/null 2>&1
    fi
    wine reg add 'HKCU\Control Panel\Desktop' /v LogPixels \
        /t REG_DWORD /d 96 /f >/dev/null
    # Wine's newer EGL backend (the default since 10.17) can't draw straight
    # to the screen, so single-buffered savers like 3D Pipes stay black
    # (https://bugs.winehq.org/show_bug.cgi?id=59819). GLX still can.
    wine reg add 'HKCU\Software\Wine\X11 Driver' /v UseEGL \
        /t REG_SZ /d N /f >/dev/null
    # Win2K colours for the savers' Settings dialogs.
    wine regedit "$SCRIPT_DIR/../theme/Redmond2K/wine/Redmond97 SE Millennium.reg"
    # After the scheme, which sets its own desktop colour: full screen runs
    # inside a Wine virtual desktop, which shows that colour until the saver
    # draws; black blends into the saver instead.
    wine reg add 'HKCU\Control Panel\Colors' /v Background \
        /t REG_SZ /d '0 0 0' /f >/dev/null
    wineserver -w
    echo "Wine prefix: $WINEPREFIX"
fi
