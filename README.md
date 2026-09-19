# Redmond2K

A Windows 2000 desktop for XFCE on Linux, assembled piece by piece: the widget
theme, the window borders, the login screen, the taskbar, the event sounds, and
even the browser chrome.

Built and tested on Fedora 44 + XFCE. Most of it is portable; the parts that
aren't are called out below.

## What's in here

| Directory | What it is |
| --- | --- |
| [theme/](theme/) | The GTK 2/3/4 + xfwm4 theme, plus a Wine colour scheme |
| [Lightdm/](Lightdm/) | A `lightdm-webkit2-greeter` theme styled after the Win2K logon dialog |
| [sounds/](sounds/) | A freedesktop sound theme built from the Windows ME sounds, with a session-end daemon |
| [xfce4-panel/](xfce4-panel/) | A saved panel profile: Start button, quick launch, tasklist, tray, clock |
| [waterfox/](waterfox/) | A `userChrome.css` that makes Waterfox/Firefox look period-correct |

Each directory with anything non-obvious has its own readme. This page is the
tour and the install order.

## Install order

The pieces are independent, but this order avoids looking at a half-themed
desktop:

1. [Fonts](#fonts) — everything else references them
2. [GTK + xfwm4 theme](#gtk--xfwm4-theme)
3. [Icons and cursors](#icons-and-cursors)
4. [Panel](#panel)
5. [Sounds](#sounds)
6. [LightDM greeter](#lightdm-greeter)
7. [Waterfox](#waterfox)

## Fonts

The look depends on **Tahoma** (the Windows 2000 UI font) and **Lucida Sans
Unicode** (the panel clock's date line).

**You have to source both fonts yourself.** They are proprietary Microsoft
fonts, so they aren't bundled in this repo and aren't redistributable. Take
them from a licensed Windows installation, where they live in
`C:\Windows\Fonts`:

| File | Font |
| --- | --- |
| `tahoma.ttf` | Tahoma Regular |
| `tahomabd.ttf` | Tahoma Bold |
| `l_10646.ttf` | Lucida Sans Unicode |

**Install them system-wide, not per-user.** The LightDM greeter runs as the
`lightdm` user before you log in, so anything under your `~/.local/share/fonts`
is invisible to it and the login screen falls back to a generic sans-serif.

```
sudo mkdir -p /usr/local/share/fonts/win2k
sudo cp tahoma.ttf tahomabd.ttf l_10646.ttf /usr/local/share/fonts/win2k/
sudo chmod 644 /usr/local/share/fonts/win2k/*.ttf
sudo fc-cache -f
```

Check it took:

```
fc-list | grep -i tahoma
```

Without Tahoma, everything falls back to `MS Sans Serif` or your default
sans-serif. It still works; it just isn't right.

## GTK + xfwm4 theme

`theme/Redmond2K` covers GTK 2, GTK 3, GTK 4, xfwm4 window decorations, and a
Wine registry file. Install it for your user:

```
mkdir -p ~/.local/share/themes
cp -r theme/Redmond2K ~/.local/share/themes/
```

Then select it. Via the GUI that's Settings → Appearance → Style for the widget
theme and Settings → Window Manager → Style for the borders. Via `xfconf`:

```
xfconf-query -c xsettings    -p /Net/ThemeName    -s Redmond2K
xfconf-query -c xfwm4        -p /general/theme    -s Redmond2K
xfconf-query -c xsettings    -p /Gtk/FontName     -s "Tahoma 9"
```

A few settings that matter for the illusion, all under Settings → Window
Manager → Advanced or `xfwm4` xfconf:

- Window animations off (the theme's `settings.ini` already disables GTK
  animations)
- Title button layout `O|HMC` — the theme's `themerc` sets this

For Wine applications, apply the matching colour scheme:

```
wine regedit "theme/Redmond2K/wine/Redmond97 SE Millennium.reg"
```

## Icons and cursors

Neither is bundled here — both are separate projects, and
`theme/Redmond2K/index.theme` just names the icon theme it expects (`SE98`).

**Icons: [SE98](https://github.com/nestoris/Win98SE)**, a Win98 SE icon theme.
Install it, then switch it to the Windows 2000 icon variants — the theme ships
both sets, and the awk script hardlinks the `*_win2k.png` files over the
defaults and refreshes the icon cache:

Install it to `/usr/share/icons`, not `~/.local/share/icons`, for the same
reason as the fonts — the greeter and any other user's session need to resolve
it too.

```
git clone https://github.com/nestoris/Win98SE.git
sudo cp -r Win98SE/SE98 /usr/share/icons/
cd /usr/share/icons/SE98
sudo ./win2k_icons.awk
```

`./win98_icons.awk` in the same directory puts the Win98 icons back.

Then select it:

```
xfconf-query -c xsettings -p /Net/IconThemeName -s SE98
```

**Cursors: [ModernXP](https://github.com/na0miluv/modernXP-cursor-theme)**.

## Panel

`xfce4-panel/redmond2k-panel.md.tar.bz2` is an
[xfce4-panel-profiles](https://docs.xfce.org/apps/xfce4-panel-profiles/start)
backup: a single 28px bottom panel with a Whisker Menu titled ` Start `, three
quick-launch buttons, a tasklist with labels, the system tray, a PulseAudio
plugin, a show-desktop button, and a clock set to `%-I:%M %p` over `%m/%d/%Y`.

```
sudo dnf install xfce4-panel-profiles xfce4-whiskermenu-plugin
xfce4-panel-profiles load xfce4-panel/redmond2k-panel.md.tar.bz2
```

**This replaces your current panel layout.** Save your own first
(`xfce4-panel-profiles save mine`) if you want it back.

The three launchers point at applications from the machine this was captured
on, so expect to re-point them at your own. The tray's `known-items` list is
likewise a snapshot and is harmless if the applications aren't installed.

## Sounds

A freedesktop sound theme built from the Windows ME sound set, plus a small
root daemon that plays the shutdown sound at session end — which is harder than
it sounds, because the audio device is revoked with the session.

```
cd sounds
./install.sh                    # theme, for the current user
sudo ./install-session-sound.sh # session-end sound (logout/shutdown/restart)
./test.sh                       # play everything in order
```

[sounds/readme.md](sounds/readme.md) explains why the daemon runs as root, how
each of logout/shutdown/restart is detected, and how to uninstall it.

## LightDM greeter

A Win2K logon dialog for `lightdm-webkit2-greeter`, forked from
[Chicago95](https://github.com/grassmunk/Chicago95)'s greeter.

```
cd Lightdm
./install.sh                    # into /usr/share/lightdm-webkit/themes
```

You also need `lightdm-webkit2-greeter` itself, and `/etc/lightdm/lightdm.conf`
pointed at it:

```
[Seat:*]
greeter-session=lightdm-webkit2-greeter
```

...plus `webkit_theme = Redmond2K` under `[greeter]` in
`/etc/lightdm/lightdm-webkit2-greeter.conf`.

On Fedora 44 the greeter has to be built from source — the COPR packages were
built against the older `webkit2gtk-4.0`/libsoup2 stack, which Fedora 44
doesn't ship. Upstream's `meson.build` hard-requires 4.0, so it needs a patch
to try 4.1 first:

```diff
 gtk3            = dependency('gtk+-3.0',                     version: '>=3.18')
-webkit2         = dependency('webkit2gtk-4.0',               version: '>=2.12')
-webkit2_webext  = dependency('webkit2gtk-web-extension-4.0', version: '>=2.12')
+webkit2         = dependency('webkit2gtk-4.1',               version: '>=2.12', required: false)
+if webkit2.found()
+  webkit2_webext = dependency('webkit2gtk-web-extension-4.1', version: '>=2.12')
+else
+  webkit2        = dependency('webkit2gtk-4.0',               version: '>=2.12')
+  webkit2_webext = dependency('webkit2gtk-web-extension-4.0', version: '>=2.12')
+endif
```

Full build steps, dependencies and credits are in
[Lightdm/Redmond2K/README.md](Lightdm/Redmond2K/README.md).

## Waterfox

`waterfox/userChrome.css` restyles the browser chrome: bitmap navigation icons,
Win2K bevels around the toolbars, flat square tabs, and a recessed content
frame. It works in Firefox too.

Find your profile directory (`about:profiles` → Root Directory), then:

```
mkdir -p <profile>/chrome
cp -r waterfox/userChrome.css waterfox/icons <profile>/chrome/
```

Custom stylesheets are off by default. In `about:config`, set:

```
toolkit.legacyUserProfileCustomizations.stylesheets = true
```

Restart the browser.

## Credits

- The GTK/xfwm4 theme is a fork of **Redmond97 SE — Millennium**, itself a port
  of the original Redmond97 "windows" theme
- The greeter is forked from [Chicago95](https://github.com/grassmunk/Chicago95)
  by [grassmunk](https://github.com/grassmunk) — see
  [its readme](Lightdm/Redmond2K/README.md#credits) for the full chain
- Icons are [SE98](https://github.com/nestoris/Win98SE) by
  [nestoris](https://github.com/nestoris), switched to its Win2K variants
- Sounds are the Windows ME set, included here for personal-use theming

## License

The theme carries the GPLv3 ([theme/Redmond2K/LICENSE](theme/Redmond2K/LICENSE)).
The greeter is MIT ([Lightdm/Redmond2K/LICENSE](Lightdm/Redmond2K/LICENSE)).
Microsoft fonts and sounds are not covered by either and are not redistributed
by this repo.
