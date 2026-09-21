# AGENTS.md

Win2K theme for XFCE (Fedora 44). No build/tests; verify visually. Install docs: README.md.

## Where things go
- GTK3: `theme/Redmond2K/gtk-3.0/gtk.css` = palette + imports of `gtk-*.css`. XFCE app fixes (panel, whisker, thunar, alt-tab…) → `gtk-xfce4.css`.
- GTK4: `gtk-4.0/gtk.css` imports gtk-3.0 first; only put GTK4-specific overrides there.
- xfwm4: `themerc` + baked-colour `.xpm`s. gtk-2.0 is legacy.
- Greeter: `Lightdm/Redmond2K/`; `js/mock.js` lets `index.html` run in a browser.
- Panel `.tar.bz2` is binary — regenerate via `xfce4-panel-profiles save`, never hand-edit.
- `sounds/systemd/` daemon: read `sounds/readme.md` first. `*.disabled` sounds are placeholders, keep them.

## Palette is duplicated — keep in sync
`#D4D0C8` face, `#FFFFFF` light, `#7F7F77` shadow, `#3F3F3F` border, `#002468` selection, `#7191C2`/`#808080` active/inactive title, `#A9A6A0` disabled.
Copies: gtk-3 `@define-color`, gtk-2 `gtk_color_scheme`, xfwm4 `themerc`+xpm, `wine/*.reg` (decimal RGB), `waterfox/userChrome.css` (lowercase hex), `Lightdm/.../layout.css`. Changing one → grep repo case-insensitively, update all. In GTK CSS use `@names`, not literals.

## Testing
- `~/.themes/Redmond2K` symlinks to the repo: edits are live. Reload GTK/xfwm4 by toggling `xfconf-query -c xsettings -p /Net/ThemeName` (or `-c xfwm4 -p /general/theme`) away and back; panel: `xfce4-panel -r`.
- Launching a GTK app from terminal prints CSS parse errors; `GTK_DEBUG=interactive` for inspector; `gtk3-widget-factory` available.
- Sounds, greeter, waterfox need their install step (greeter uses sudo).
- You can't see the screen: tell the user what to check; don't claim visual fixes.

## Rules
- Match real Win2K: 1px bevels, square corners, no animations/rounding. Comment *why* for hacks.
- Never add MS fonts. Keep upstream credits (Chicago95, win95.css, SE98). Theme GPLv3, greeter MIT.
- Scripts: `bash`, `set -euo pipefail`, sudo only for system paths.
- Commits: short lowercase, one component (e.g. "fix gtk 4 menus").
- Don't commit `__pycache__` (tracked by mistake, no .gitignore).
