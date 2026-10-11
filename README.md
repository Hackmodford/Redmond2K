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
| [screensaver/](screensaver/) | Wine Saver: a Win2K-style Screen Saver dialog that previews and runs `.scr` files through Wine |

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
8. [Wine Saver](#wine-saver)

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
xfconf-query -c xsettings    -p /Gtk/FontName     -s "Tahoma 8.25"
xfconf-query -c xfwm4        -p /general/title_font -s "Tahoma Bold 8.25"
```

Windows 2000 used Tahoma 8pt at 96 DPI, which Windows rounds to 11px. At 96
DPI Pango renders 8pt as 10.67px, so 8.25pt is used to land on exactly 11px.

With display scaling (Settings → Appearance → Settings → Window Scaling),
check that GTK's unscaled DPI is 96. It is stored in 1/1024ths, so the value
should be 98304:

```
xfconf-query -c xsettings    -p /Gdk/UnscaledDPI  -s 98304
```

A wrong value (`96000`, i.e. 93.75 DPI, has been seen) shrinks every GTK
app's text and makes Waterfox render at a fractional scale such as 1.94,
which puts the theme's 1px bevels between device pixels.

A few settings that matter for the illusion, all under Settings → Window
Manager → Advanced or `xfwm4` xfconf:

- Window animations off (the theme's `settings.ini` already disables GTK
  animations)
- Title button layout `O|HMC` — the theme's `themerc` sets this

The titlebar buttons ship in two styles. `smooth` is the default and draws the
close button's X one pixel per row, which reads as a clean diagonal at 2x;
`classic` is the original artwork, doubled 2x2 throughout so it downscales
without artefacts. Switch with:

```
./theme/set-button-style.sh           # list styles, mark the active one
./theme/set-button-style.sh classic
```

See [theme/Redmond2K/xfwm4/button-styles/](theme/Redmond2K/xfwm4/button-styles/).

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
Win2K bevels around the toolbars, flat square tabs, a recessed content frame,
and the status bar. It works in Firefox too.

Find your profile directory (`about:profiles` → Root Directory), then:

```
mkdir -p <profile>/chrome
cp -r waterfox/userChrome.css waterfox/icons waterfox/assets <profile>/chrome/
```

Custom stylesheets are off by default. In `about:config`, set:

```
toolkit.legacyUserProfileCustomizations.stylesheets = true
```

The bevels are drawn in whole pixels, so the browser needs a whole-number
scale. Waterfox takes it from the desktop; if it renders slightly small or
lines look blended, check `Gdk/UnscaledDPI` (see the GTK theme section).

Restart the browser.

## Wine Saver

Wine Saver (`screensaver/redmond2k-screensaver.py`) is the Win2K "Display Properties →
Screen Saver" tab: pick a `.scr`, watch it in the little monitor, open its
Settings, or Preview it full screen. Everything runs through Wine, and
[XScreenSaver](https://www.jwz.org/xscreensaver/) runs the chosen one when
you're idle.

No screen savers ship with Redmond2K (they're copyrighted). Copy your own
`.scr` files into any folder and point the dialog at it with **Browse...**, or
pass the folder on the command line:

```
redmond2k-screensaver ~/screensavers
```

Install it for the current user (adds a "Wine Saver" menu entry):

```
sudo dnf install wine xdotool mingw32-gcc gamescope xscreensaver
screensaver/install.sh
```

- `mingw32-gcc` builds `preview-host.exe`, a tiny Wine program that gives the
  saver a window to draw its preview into (`/p <HWND>`, as on Windows).
  Without it everything else works, but the monitor stays blue.
- `gamescope` runs Preview at a period resolution (640×480, 800×600 or
  1024×768, chosen in the dialog), scaled up to full screen with black bars
  like a 4:3 monitor. Without it, savers run at your real resolution.
  It also drives the "Monitor effect" option: a CRT shader (shadow mask,
  scanlines or soft scanlines) drawn over full screen. The shaders and their
  credits are in [screensaver/crt/](screensaver/crt/).
- "Timing" slows savers back to their original speed. They step their
  animation once per Windows timer tick, and Wine's timers are far more
  precise than Windows 2000's (15.6 ms) or Windows 98's (55 ms), so 3D Maze
  runs about twice as fast as it did. A small DLL, also built with
  `mingw32-gcc`, rounds the saver's timers up to the old tick.
- The installer creates a separate Wine prefix for savers
  (`~/.local/share/redmond2k-screensaver/prefix`, about 1.6 GB) and keeps it at
  96 DPI. A high-DPI `~/.wine` would make Wine draw them at a fraction of the
  resolution and scale them up. Saver settings are stored in that prefix, and
  their dialogs open at 96 DPI too, so they're small on a HiDPI screen (at a
  raised DPI, some savers' fixed-size dialogs cut off options). It uses
  Wine's GLX backend rather than EGL, which leaves 3D Pipes black. The prefix
  also gets the Wine colour
  scheme from the [GTK + xfwm4 theme](#gtk--xfwm4-theme) section.

The choices are saved to `~/.config/redmond2k/screensaver.ini`.

**Running as your screen saver.** OK/Apply also writes the folder's savers
into `~/.xscreensaver`'s program list and selects the chosen one (`mode: one`),
or disables the screen saver for "(None)". Your original file is backed up
once to `~/.xscreensaver.redmond2k-backup`, and xscreensaver-settings must
have created `~/.xscreensaver` first. The idle time, locking and power
saving stay in xscreensaver-settings; the savers also show up in its list.

XScreenSaver runs `redmond2k-screensaver --hack SAVER.scr`, which plays the
saver in gamescope (at the dialog's resolution) inside XScreenSaver's own
window, so XScreenSaver keeps the mouse and keyboard and stops it when you
come back.

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
