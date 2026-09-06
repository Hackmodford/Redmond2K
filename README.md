# Redmond2K

## Light DM

### Install Dependencies

`sudo dnf install meson lightdm-gobject-devel gtk3 webkit2gtk4.1 dbus-glib -y`

Clone this repo

`git clone https://github.com/MerkeX/lightdm-webkit2-greeter.git`

Fedora 44 only ships the `webkit2gtk4.1` devel package, but upstream's `meson.build` hard-requires `webkit2gtk-4.0`, so the build fails as-is. Patch `meson.build` to try 4.1 first and fall back to 4.0:

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

This is what actually let it build here - the COPR package didn't work on Fedora 44 for the same reason (built against the older webkit2gtk-4.0/libsoup2 stack).

Install from Source

`meson setup build --prefix=/usr --libdir=lib --buildtype=release`
`ninja -C build`
`sudo ninja -C build install`

Steps to copy lightdm theme and maybe font

Steps to modify config

---

Cursor: [ModernXP-cursor-theme](https://github.com/na0miluv/modernXP-cursor-theme)
