# Titlebar button styles

Alternate artwork for the xfwm4 titlebar buttons. Switch with
[`theme/set-button-style.sh`](../../../set-button-style.sh), which copies a
style's `.xpm`s over the ones in `xfwm4/` and reloads the window manager:

```sh
./theme/set-button-style.sh          # list styles, mark the active one
./theme/set-button-style.sh classic
```

xfwm4 reads a fixed set of filenames out of the theme directory and ignores
subdirectories, so nothing in here is live until the script copies it up.

| Style | What it is |
| --- | --- |
| `smooth` | The default. The close button's X steps 1px per row, so the diagonals read as diagonals at 2x. |
| `classic` | The original artwork, drawn as 2x2 blocks throughout. Every pixel is doubled, so it downscales cleanly to a 1x build of the theme — at the cost of a chunkier X at 2x. |

Only the close button differs between the two; the other buttons have no
diagonals to smooth. A style may hold any subset of the button `.xpm`s, and the
script copies whatever it finds.
