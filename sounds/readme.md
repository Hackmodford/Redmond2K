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

## Session-end sound (logout / shutdown / restart)

One rule: **when a desktop session ends, play the sound.** Logout, shutdown
and restart are just three ways that happens, and all three go through the
same code path.

Install with `./install.sh` first (so the theme is in place), then:

```
sudo ./install-session-sound.sh
```

This installs `redmond2k-session-sound.service`, a small root daemon
(`systemd/redmond2k-session-sound.py`) that watches logind.

### Why a root daemon, and not something simpler

Two things rule out playing the sound from inside the session, which is what
XFCE's `RunHook=1/2/3` autostart entries and a `systemd --user` unit both do:

- **The audio device goes away with the session.** `/dev/snd/*` is
  `root:audio 0660`, and a normal user's access comes from a logind uaccess
  ACL granted to the *active session*. It is revoked the moment the session
  ends, so anything playing audio after that gets
  `aplay: audio open error: Permission denied`. Root is not subject to it.
- **The session may never finish closing.** Fedora ships
  `KillUserProcesses=no`, so stray daemons (`localsearch`, `geoclue`, ...)
  keep the session scope alive after logout. The session sits in
  `State=closing` indefinitely, `user@$UID.service` never stops, and any hook
  waiting on that never runs. `SessionRemoved` never arrives either.

Running outside the session sidesteps both.

### How each case is detected

| Case | Trigger | Why it isn't cut off |
| --- | --- | --- |
| Logout | A `Class=user` session leaves the open set (disappears or goes `State=closing`), polled once a second | Nothing is shutting down; the daemon is not in the dying session |
| Shutdown / restart | logind's `PrepareForShutdown` signal | The daemon holds a `delay` shutdown inhibitor, so logind waits for the sound to finish before proceeding |
| From the LightDM greeter | No `Class=user` session exists | Stays silent, which is correct |

The `logind-inhibit-delay.conf` drop-in raises `InhibitDelayMaxSec` to 10s;
the 5s default is uncomfortably close to the ~4.2s the sound takes. It
applies after a reboot or `systemctl restart systemd-logind`.

A shutdown plays the sound once, not twice: `PrepareForShutdown` sets a flag
that suppresses the logout path when the sessions are torn down afterwards.

### Testing

```
sudo /usr/local/bin/redmond2k-session-sound --test   # audio path only
journalctl -fu redmond2k-session-sound.service       # watch it decide
```

To uninstall:

```
sudo systemctl disable --now redmond2k-session-sound.service
sudo rm /usr/local/bin/redmond2k-session-sound \
        /etc/systemd/system/redmond2k-session-sound.service \
        /etc/systemd/logind.conf.d/redmond2k-inhibit-delay.conf
sudo systemctl daemon-reload
```

## Test

After installing (so `Redmond2K` is the active theme), run `./test.sh`
to play every mapped sound in order via `canberra-gtk-play`. Requires
`libcanberra-gtk3` / `libcanberra-utils`.

## Notes

- Files ending in `.disabled` are unmapped/unused theme events - rename
  to `.wav` to enable them if you add a matching source sound.
- `stereo/` is currently the only output profile provided.
