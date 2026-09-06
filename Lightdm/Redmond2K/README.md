Redmond2K
=========

Redmond2K is a greeter (a login screen) for `lightdm-webkit2-greeter`, styled after the classic Windows 2000 logon dialog.

It has very limited functionality, but reminds you of that Y2K aesthetic.

It's a fork of / heavily inspired by [Chicago95](https://github.com/grassmunk/Chicago95)'s lightdm greeter theme, adapted from the Windows 9x/98 "Chicago" look to the Windows 2000 "Redmond" one - hence the name.

Documentation
-------------

You'll need `lightdm` and `lightdm-webkit2-greeter` for this to work. On Debian/Ubuntu-based distros it's typically `lightdm-webkit2-greeter` from apt; on Arch it's in the AUR.

On Fedora there's a COPR (`antergos/lightdm-webkit2-greeter` or `rmnscnce/lightdm-webkit2-greeter`), but it may not have a working build for your release - it didn't for Fedora 44 at the time of writing, since it was built against the older `webkit2gtk-4.0`/libsoup2 stack, which Fedora 44 doesn't ship (only `webkit2gtk4.1` is available). If so, you'll need to compile it yourself:

```
sudo dnf install meson lightdm-gobject-devel gtk3 webkit2gtk4.1 dbus-glib -y

git clone https://github.com/MerkeX/lightdm-webkit2-greeter.git /tmp/greeter
cd /tmp/greeter
```

Upstream's `meson.build` still hard-requires `webkit2gtk-4.0`, which doesn't exist on Fedora 44, so the build fails unless you patch it to try 4.1 first:

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

Then build and install:

```
meson setup build --prefix=/usr --libdir=lib --buildtype=release
ninja -C build
sudo ninja -C build install
```

First, configure lightdm to use `lightdm-webkit2-greeter` if you haven't already. Open `/etc/lightdm/lightdm.conf` and set:

```
[Seat:*]
greeter-session=lightdm-webkit2-greeter
```

Second, this theme uses **Tahoma** as its UI font (the actual Windows 2000 default). Tahoma is a proprietary Microsoft font and isn't bundled with this repo or redistributable, so you'll need to source it yourself (e.g. extract it from a licensed Windows installation) and install it to somewhere `fc-list` picks up, such as `~/.local/share/fonts` or `/usr/share/fonts`. Without it, the theme falls back to `MS Sans Serif` / your system's default sans-serif.

Next, configure `lightdm-webkit2-greeter` to use *Redmond2K*. Edit `/etc/lightdm/lightdm-webkit2-greeter.conf` and set `webkit_theme` under `[greeter]`:

```
[greeter]
webkit_theme = Redmond2K
```

Finally, install the theme itself. From the `Lightdm/` directory of this repo, run:

```
./install.sh
```

This copies `Redmond2K/` into `/usr/share/lightdm-webkit/themes/Redmond2K` (elevating with `sudo` as needed). To install somewhere else, set `THEMES_DIR`:

```
THEMES_DIR=/custom/path ./install.sh
```

Dependencies
------------

`lightdm`, `lightdm-webkit2-greeter`, the Tahoma font, and a taste for Y2K nostalgia.

License
-------

This greeter is MIT-licensed, but few people care. Check out the LICENSE file if you think you've got what it takes.

Credits
-------

This theme is a fork of / directly inspired by:

*   [Chicago95](https://github.com/grassmunk/Chicago95) by [grassmunk](https://github.com/grassmunk), which this theme's structure and markup were adapted from

Which was itself based on paddy-greeter:

*   [Paddy-Greeter](https://github.com/kalmanolah/paddy-greeter/) by [Kalman Olah](https://github.com/kalmanolah/)

Button theming was copied from win95.css:
*   [Win95.CSS](https://github.com/AlexBSoft/win95.css) by [Aleksander Bakukhin](https://github.com/AlexBSoft)

The dialog icons (`img/dialog-error.png`, `img/dialog-info.png`) come from:
*   [Win98SE](https://github.com/nestoris/Win98SE) by [nestoris](https://github.com/nestoris)
