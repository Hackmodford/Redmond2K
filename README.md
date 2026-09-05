# Redmond2K

## Light DM

### Install Dependencies

`sudo dnf install meson lightdm-gobject-devel gtk3 webkit2gtk4.1 dbus-glib -y`

Clone this repo

`git clone https://github.com/MerkeX/lightdm-webkit2-greeter.git`

Install from Source

`meson setup build --prefix=/usr --libdir=lib --buildtype=release`
`ninja -C build`
`sudo ninja -C build install`

Steps to copy lightdm theme and maybe font

Steps to modify config

---

Cursor: [ModernXP-cursor-theme](https://github.com/na0miluv/modernXP-cursor-theme)
