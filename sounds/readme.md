# Redmond2K Sound Theme

The `originals` folder contains the source sounds from Windows ME.

The `Redmond2K` folder is the finished sound theme, mapped onto the
freedesktop sound theme spec (`index.theme` + `stereo/*.wav`).

## Install

### XFCE

Run `./install.sh`. It copies the theme to
`~/.local/share/sounds/Redmond2K` and sets it as the active sound theme
via `xfconf-query`.

### Manual

Copy the `Redmond2K` folder into a sound theme directory:

```
cp -r Redmond2K ~/.local/share/sounds/
```

(or `/usr/share/sounds/` for a system-wide install), then select
`Redmond2K` as the sound theme in your desktop's sound settings.

## Test

After installing (so `Redmond2K` is the active theme), run `./test.sh`
to play every mapped sound in order via `canberra-gtk-play`. Requires
`libcanberra-gtk3` / `libcanberra-utils`.

## Notes

- Files ending in `.disabled` are unmapped/unused theme events - rename
  to `.wav` to enable them if you add a matching source sound.
- `stereo/` is currently the only output profile provided.
