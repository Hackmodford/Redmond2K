#!/usr/bin/python3
"""Redmond2K Screen Saver: the Win2K "Display Properties > Screen Saver" tab.

Lists the Windows screen savers (*.scr) found in a folder of your choosing and
previews them through Wine. No .scr files ship with Redmond2K (they are
copyrighted); point the app at your own folder with "Browse..." or by passing
it on the command line:

    redmond2k-screensaver [FOLDER]
    redmond2k-screensaver --hack SAVER.scr   (run by xscreensaver)

The folder, the chosen screen saver and the full-screen resolution are saved
to ~/.config/redmond2k/screensaver.ini on OK/Apply.

Savers run in their own Wine prefix (~/.local/share/redmond2k-screensaver/
prefix, made by install.sh) at 96 DPI: a high-DPI prefix makes Wine render
old programs at half resolution and double them up. Full screen goes through
gamescope when it's installed, so savers get a real 640x480-1024x768 screen,
scaled up with black bars like a 4:3 monitor.

Screen saver command line conventions (same as Windows):
    /s  run full screen      /c  show the settings dialog
"""

import configparser
import ctypes
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

import cairo
import gi

gi.require_version("Gdk", "3.0")
gi.require_version("GdkX11", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GdkX11, GLib, Gtk  # noqa: E402

APP_TITLE = "Display Properties"
CONFIG = Path(GLib.get_user_config_dir()) / "redmond2k" / "screensaver.ini"
NONE_ID = ""

# Size of the screen inside the Win2K monitor picture.
SCREEN_W, SCREEN_H = 152, 112
DATA = Path(GLib.get_user_data_dir()) / "redmond2k-screensaver"
WINEPREFIX = DATA / "prefix"
RESOLUTIONS = ("640x480", "800x600", "1024x768")
# Wine desktop that full-screen savers run in; unique so end_saver() can
# find exactly ours.
SAVER_DESKTOP = f"Redmond2KSaver{os.getpid()}"
DEFAULT_RESOLUTION = "800x600"
# Monitor effects: ReShade shaders in crt/ (see crt/README.md), by file stem.
EFFECTS = (("none", "None"), ("CRTLottes", "Shadow mask"),
           ("CRTGeom", "Scanlines"), ("zfast_crt", "Soft scanlines"))
CRT_DIR = Path(__file__).resolve().parent / "crt"
# Timer granularity savers get (see saver-timer.c): (id, label, tick in us).
TIMINGS = (("win2000", "Windows 2000", 15625), ("win98", "Windows 98", 54925),
           ("modern", "Modern (unchanged)", 0))
DEFAULT_TIMING = "win2000"
GAMESCOPE_SHADERS = (Path(GLib.get_user_data_dir()) / "gamescope" / "reshade"
                     / "Shaders")

# Win2K's default desktop colour, shown on the little screen when no saver
# is selected.
DESKTOP_BLUE = (0x3A / 255, 0x6E / 255, 0xA5 / 255)


def load_config():
    config = configparser.ConfigParser()
    config.read(CONFIG)
    if not config.has_section("screensaver"):
        config.add_section("screensaver")
    return config


def save_config(folder, saver, resolution, effect, timing):
    config = load_config()
    config["screensaver"]["folder"] = folder or ""
    config["screensaver"]["saver"] = saver or ""
    config["screensaver"]["resolution"] = resolution
    config["screensaver"]["effect"] = effect
    config["screensaver"]["timing"] = timing
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG, "w") as f:
        config.write(f)


XSCREENSAVER = Path.home() / ".xscreensaver"
# Prefix for our savers' names in xscreensaver's list, so they're easy to
# tell apart from (and find among) its ~300 built-in ones.
XSCREENSAVER_PREFIX = "Wine: "
# How xscreensaver runs us; the absolute, unresolved path keeps working
# through the ~/.local/bin symlink install.sh makes.
SELF = os.path.abspath(sys.argv[0])


def configure_xscreensaver(savers, selected):
    """Lists savers in ~/.xscreensaver and makes it run selected.

    savers is [(name, path)]; selected is one of the paths, or NONE_ID for
    xscreensaver's "Disable Screen Saver" (like Windows' "(None)", the
    monitor still powers down if DPMS is on). Our entries are the ones that
    run "--hack"; they're replaced wholesale and appended to the end of the
    list, so the indices of everything else stay put. xscreensaver notices
    the file has changed by itself.
    """
    if not XSCREENSAVER.is_file():
        raise FileNotFoundError(
            f"{XSCREENSAVER} doesn't exist yet. Open xscreensaver-settings "
            "once to create it, then try again.")
    backup = XSCREENSAVER.with_name(".xscreensaver.redmond2k-backup")
    if not backup.exists():
        shutil.copy2(XSCREENSAVER, backup)

    lines = XSCREENSAVER.read_text().splitlines()
    start = next(i for i, line in enumerate(lines)
                 if line.startswith("programs:"))
    # Every line of the list ends in a backslash continuation; the first
    # line without one ends it. Each entry ends in "\n\", but
    # xscreensaver-settings wraps long entries over several lines.
    end = start + 1
    while end < len(lines) and lines[end].endswith("\\"):
        end += 1
    entries, entry = [], []
    for line in lines[start + 1:end]:
        entry.append(line)
        if line.rstrip().endswith("\\n\\"):
            entries.append(entry)
            entry = []
    if entry:
        entries.append(entry)
    entries = [entry for entry in entries
               if not re.search(r"\s--hack\s", " ".join(entry))]
    index = None
    for name, path in savers:
        if path == selected:
            index = len(entries)
        # No whitespace in the command: xscreensaver-settings wraps at any
        # space, quotes or not, which would split a path like "3D Maze".
        entries.append([f'  "{XSCREENSAVER_PREFIX}{name}"  '
                        f'{shlex.quote(SELF)} --hack '
                        f'{urllib.parse.quote(path)} --root \\n\\'])
    lines[start + 1:end] = [line for entry in entries for line in entry]

    settings = {"mode": "off"} if index is None else {
        "mode": "one", "selected": str(index)}
    for i, line in enumerate(lines):
        key = line.split(":", 1)[0]
        if key in settings:
            lines[i] = f"{key}:\t\t{settings.pop(key)}"
    lines += [f"{key}:\t\t{value}" for key, value in settings.items()]
    XSCREENSAVER.write_text("\n".join(lines) + "\n")


def find_savers(folder):
    """Returns [(display name, path)] for every .scr in folder, sorted."""
    if not folder or not os.path.isdir(folder):
        return []
    savers = [p for p in Path(folder).iterdir()
              if p.is_file() and p.suffix.lower() == ".scr"]
    return sorted(((p.stem, str(p)) for p in savers),
                  key=lambda s: s[0].lower())


def find_helper(name, missing):
    """The Wine helpers are built by install.sh, next to the installed
    script."""
    for folder in (Path(__file__).resolve().parent, DATA):
        if (folder / name).is_file():
            return str(folder / name)
    print(f"{name} not found; run install.sh {missing}", file=sys.stderr)
    return None


# Without it the monitor just shows the desktop colour.
PREVIEW_HOST = find_helper("preview-host.exe", "for live previews")
# Without these, savers keep Wine's precise timers.
SAVER_RUN = (find_helper("saver-timer.dll", "for period timer speeds")
             and find_helper("saver-run.exe", "for period timer speeds"))
# Microseconds per timer tick for the savers we start; 0 leaves timers be.
# The window sets it from its Timing drop-down, the hack from the config.
timer_tick_us = 0


def timing_tick(timing):
    return next((tick for id_, _, tick in TIMINGS if id_ == timing), 0)


def saver_command(path, flag):
    """The Windows command line that runs a saver, through saver-run.exe
    when its timers should be rounded to old Windows ticks."""
    if timer_tick_us and SAVER_RUN:
        return [windows_path(SAVER_RUN), windows_path(path), flag]
    return [path, flag]


def windows_path(path):
    """Wine maps Z: to / by default."""
    return "Z:" + path.replace("/", "\\")


def launch(*argv, env=None):
    """Starts argv in its own process group so stop() can kill it."""
    env = dict(os.environ, WINEDEBUG="-all", WINEPREFIX=str(WINEPREFIX),
               **(env or {}))
    if timer_tick_us:
        # Read by saver-timer.dll, which saver-run.exe and preview-host.exe
        # load into the saver.
        env["REDMOND2K_TIMER_TICK_US"] = str(timer_tick_us)
    return subprocess.Popen(argv, env=env, start_new_session=True,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)


def wine(*args):
    return launch("wine", *args)


def run_saver(path, flag):
    """Runs a saver with /s or /c and waits for it. "wine x.scr" alone hands
    the .scr to start.exe, which returns at once."""
    return wine("start", "/wait", "/unix", path, flag)


def configured(key, choices, default):
    value = load_config()["screensaver"].get(key, default)
    return value if value in choices else default


def crt_shader(effect, resolution):
    """Writes a copy of the effect with its source size set to resolution
    where gamescope looks for shaders, and returns the name to pass it.

    gamescope can't set a shader's options, and these default to an
    emulator's 320x240, so the width and height ones get rewritten.
    """
    width, height = resolution.split("x")
    folder = GAMESCOPE_SHADERS / "redmond2k"
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copy(CRT_DIR / "ReShade.fxh", folder)

    def resize(match):
        name, value = match.group(2).lower(), float(match.group(3))
        if (value in (224, 240, 256, 320)
                and re.search(r"res|size|texture|video", name)):
            if re.search(r"(x|width|w)$", name):
                return f"{match.group(1)}{width}.0{match.group(4)}"
            if re.search(r"(y|height|h)$", name):
                return f"{match.group(1)}{height}.0{match.group(4)}"
        return match.group(0)
    source = (CRT_DIR / f"{effect}.fx").read_text(errors="replace")
    source = re.sub(
        r"(uniform\s+float\s+(\w+)\s*<.*?>\s*=\s*)([0-9.]+)(\s*;)", resize,
        source, flags=re.S)
    # CRT-Geom treats anything over 400 lines as an interlaced TV picture,
    # drawing every other scanline and alternating them each frame. A
    # desktop monitor at 600 or 768 lines wasn't interlaced; 5 moves the
    # threshold to 1000 lines. (Its INTERLACED option isn't actually used.)
    source = re.sub(
        r"(uniform\s+float\s+interlace_toggle\s*<.*?>\s*=\s*)[0-9.]+",
        r"\g<1>5.0", source, flags=re.S)
    name = f"{effect}-{resolution}.fx"
    (folder / name).write_text(source)
    return f"redmond2k/{name}"


def gamescope_saver(path, resolution, *window_args, env=None, effect="none",
                    screen_height=None):
    """gamescope running the saver at resolution, scaled up to its window,
    optionally through a monitor effect.

    The saver runs inside a Wine desktop rather than as gamescope's own
    window: gamescope warps the pointer onto each new window it shows, and
    a saver started directly sees that as the mouse moving and quits. The
    desktop window takes the warp before the saver starts. Wine's desktop
    also exits by itself once the saver does.
    """
    width, height = resolution.split("x")
    # Start wineserver out here: one started by the first Wine program
    # inside gamescope lands in gamescope's process group, so gamescope
    # kills it on exit before it can stop Wine's background services. Those
    # are then orphaned and gamescope's reaper waits for them forever. It
    # daemonizes; if one is already running this just exits.
    subprocess.run(["wineserver"], env=dict(os.environ,
                                             WINEPREFIX=str(WINEPREFIX)),
                   stderr=subprocess.DEVNULL)
    saver = ["wine", "explorer", f"/desktop={SAVER_DESKTOP},{resolution}",
             *saver_command(path, "/s")]
    if effect == "none" or not screen_height:
        return launch("gamescope", "--backend", "sdl", "-w", width,
                      "-h", height, *window_args, "-S", "fit", "-F", "pixel",
                      "--", *saver, env=env)
    # gamescope applies a ReShade effect to the app's image before scaling
    # it up, which would draw a CRT's mask and scanlines at 800x600 and then
    # blow them up into a coarse checkerboard. So nest two: the inner one
    # does the crisp upscale onto a 4:3 canvas as tall as the screen, and
    # the outer one runs the shader over that and adds the side bars.
    canvas_height = str(screen_height)
    canvas_width = str(screen_height * 4 // 3)
    inner = ["gamescope", "--backend", "sdl", "-w", width, "-h", height,
             "-W", canvas_width, "-H", canvas_height, "-f", "-S", "fit",
             "-F", "pixel", "--", *saver]
    # The outer gamescope's Vulkan layer would hook the inner one's own
    # window ("Creating swapchain for non-Gamescope swapchain") and stop it.
    return launch("gamescope", "--backend", "sdl", "-w", canvas_width,
                  "-h", canvas_height, *window_args, "-S", "fit",
                  "-F", "linear",
                  "--reshade-effect", crt_shader(effect, resolution), "--",
                  "env", "DISABLE_GAMESCOPE_WSI=1", *inner, env=env)


def run_fullscreen(path, resolution, effect, screen_height):
    if not shutil.which("gamescope"):
        if timer_tick_us and SAVER_RUN:
            return wine(*saver_command(path, "/s"))
        return run_saver(path, "/s")
    return gamescope_saver(path, resolution, "-f", effect=effect,
                           screen_height=screen_height)


def end_saver(proc):
    """Ends a full-screen saver started with SAVER_DESKTOP.

    Ending just the Wine desktop process lets the saver and gamescope
    wind down normally. gamescope doesn't, though, once xscreensaver has
    destroyed the window it was drawing in, so after a second its process
    group gets killed. (That's safe because gamescope_saver() starts
    wineserver outside the group.)
    """
    if proc is None or proc.poll() is not None:
        return
    found = subprocess.run(["pkill", "-f", f"/desktop={SAVER_DESKTOP},"])
    try:
        proc.wait(timeout=1 if found.returncode == 0 else 0)
    except subprocess.TimeoutExpired:
        stop(proc)


class HiddenCursor:
    """Hides the mouse pointer on the whole screen until close().

    The saver hides its own cursor, but that only applies inside gamescope;
    gamescope's window on our display still shows one. XFixesHideCursor
    hides it whatever window it's over, and X undoes it by itself when our
    connection closes, so a crash can't leave the pointer gone.
    """

    def __init__(self):
        self.x11 = ctypes.CDLL("libX11.so.6")
        self.x11.XOpenDisplay.restype = ctypes.c_void_p
        self.x11.XDefaultRootWindow.restype = ctypes.c_ulong
        self.x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        self.x11.XFlush.argtypes = [ctypes.c_void_p]
        self.x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        self.display = self.x11.XOpenDisplay(None)
        if not self.display:
            return
        xfixes = ctypes.CDLL("libXfixes.so.3")
        xfixes.XFixesHideCursor.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        xfixes.XFixesHideCursor(self.display,
                                self.x11.XDefaultRootWindow(self.display))
        self.x11.XFlush(self.display)

    def close(self):
        if self.display:
            self.x11.XCloseDisplay(self.display)
            self.display = None


def find_window(*search, tries=150):
    """xdotool search, polling every 100ms; returns the newest match."""
    for _ in range(tries):
        found = subprocess.run(["xdotool", "search", *search],
                               capture_output=True, text=True).stdout.split()
        if found:
            return found[-1]
        time.sleep(0.1)
    return None


def dpms_sleep_after():
    """Seconds of idle after which X would power the monitor down, if it's
    set to (xscreensaver-settings' Display Power Management)."""
    xset = subprocess.run(["xset", "q"], capture_output=True,
                          text=True).stdout
    times = re.search(r"Standby:\s*(\d+)\s+Suspend:\s*(\d+)\s+Off:\s*(\d+)",
                      xset)
    if "DPMS is Enabled" not in xset or not times:
        return None
    return min((int(t) for t in times.groups() if int(t) > 0), default=None)


def idle_clock():
    """Returns a function giving seconds since the last keyboard or mouse
    input, which is what X's DPMS timeouts count."""
    class Info(ctypes.Structure):
        _fields_ = [("window", ctypes.c_ulong), ("state", ctypes.c_int),
                    ("kind", ctypes.c_int), ("til_or_since", ctypes.c_ulong),
                    ("idle", ctypes.c_ulong), ("event_mask", ctypes.c_ulong)]
    x11 = ctypes.CDLL("libX11.so.6")
    xss = ctypes.CDLL("libXss.so.1")
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    x11.XDefaultRootWindow.restype = ctypes.c_ulong
    xss.XScreenSaverQueryInfo.argtypes = [ctypes.c_void_p, ctypes.c_ulong,
                                          ctypes.POINTER(Info)]
    display = x11.XOpenDisplay(None)
    root = x11.XDefaultRootWindow(display)
    info = Info()

    def idle():
        xss.XScreenSaverQueryInfo(display, root, ctypes.byref(info))
        return info.idle / 1000
    return idle


def is_toplevel(xid):
    """Whether the window sits directly on the root window."""
    x11 = ctypes.CDLL("libX11.so.6")
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XQueryTree.argtypes = [ctypes.c_void_p, ctypes.c_ulong] + [
        ctypes.c_void_p] * 4
    x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
    x11.XFree.argtypes = [ctypes.c_void_p]
    display = x11.XOpenDisplay(None)
    root, parent = ctypes.c_ulong(), ctypes.c_ulong()
    children, count = ctypes.c_void_p(), ctypes.c_uint()
    x11.XQueryTree(display, int(xid), ctypes.byref(root),
                   ctypes.byref(parent), ctypes.byref(children),
                   ctypes.byref(count))
    if children:
        x11.XFree(children)
    x11.XCloseDisplay(display)
    return parent.value == root.value


def ignore_input(xid):
    """Gives the window an empty input shape, so the pointer passes
    through it to whatever is underneath."""
    x11 = ctypes.CDLL("libX11.so.6")
    xext = ctypes.CDLL("libXext.so.6")
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
    xext.XShapeCombineRectangles.argtypes = [
        ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
        ctypes.c_int]
    display = x11.XOpenDisplay(None)
    shape_input, shape_set, unsorted = 2, 0, 0
    xext.XShapeCombineRectangles(display, int(xid), shape_input, 0, 0, None,
                                 0, shape_set, unsorted)
    x11.XCloseDisplay(display)  # flushes the request


def window_exists(xid):
    return subprocess.run(["xdotool", "getwindowgeometry", xid],
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode == 0


def run_hack(path):
    """xscreensaver hack mode: draws the saver in $XSCREENSAVER_WINDOW.

    xscreensaver hands hacks a full-screen window of its own and SIGTERMs
    them when the user comes back; it holds the mouse and keyboard, so the
    saver never sees input and can't quit early. We start gamescope (or,
    without it, a screen-sized Wine desktop) and reparent its window into
    xscreensaver's, the same trick as the little preview.
    """
    global timer_tick_us
    timer_tick_us = timing_tick(configured(
        "timing", [t for t, _, _ in TIMINGS], DEFAULT_TIMING))
    target = os.environ.get("XSCREENSAVER_WINDOW")
    if not target:
        sys.exit("--hack is for xscreensaver: XSCREENSAVER_WINDOW is not set")
    target = str(int(target, 0))
    geometry = dict(line.split("=") for line in subprocess.run(
        ["xdotool", "getwindowgeometry", "--shell", target],
        capture_output=True, text=True).stdout.split())
    width, height = geometry["WIDTH"], geometry["HEIGHT"]

    if shutil.which("gamescope"):
        resolution = configured("resolution", RESOLUTIONS,
                                DEFAULT_RESOLUTION)
        effect = configured("effect", [e for e, _ in EFFECTS], "none")
        # gamescope asks the session's org.freedesktop.ScreenSaver to inhibit
        # (SDL_DisableScreenSaver, which SDL_VIDEO_ALLOW_SCREENSAVER doesn't
        # override), and xscreensaver-systemd answers by unblanking, which
        # kills us a few seconds in. Without a session bus there's no one to
        # ask; neither gamescope nor a Wine saver needs it otherwise.
        proc = gamescope_saver(
            path, resolution, "-W", width, "-H", height, "-b",
            env={"DBUS_SESSION_BUS_ADDRESS": "unix:path=/nonexistent"},
            effect=effect, screen_height=int(height))
        search = ("--pid", str(proc.pid))
    else:
        proc = wine("explorer", f"/desktop={SAVER_DESKTOP},{width}x{height}",
                    *saver_command(path, "/s"))
        search = ("--name", SAVER_DESKTOP)

    cursor = None

    def quit(*_):
        # Pointer first: ending the saver can take seconds, and the user
        # is already back at the desktop by the time we're told to stop.
        if cursor:
            cursor.close()
        end_saver(proc)
        sys.exit(0)
    signal.signal(signal.SIGTERM, quit)
    signal.signal(signal.SIGINT, quit)

    # xscreensaver-settings also runs us, as a preview in a window inside
    # its dialog. Only xscreensaver's real blanking windows sit on the root;
    # anywhere else, leave the pointer and the monitor alone.
    blanking = is_toplevel(target)
    # Kept until quit(), or our exit if that never comes.
    cursor = HiddenCursor() if blanking else None
    xid = find_window(*search)
    if xid:
        # In xscreensaver-settings' preview nothing grabs the mouse, and
        # gamescope would pass any movement over it on to the saver, which
        # quits as if the user were back. (When blanking, xscreensaver
        # holds the mouse anyway.)
        ignore_input(xid)
        for command in (["windowreparent", xid, target],
                        ["windowmove", xid, "0", "0"],
                        ["windowsize", xid, width, height]):
            subprocess.run(["xdotool", *command])
    # Poll rather than proc.wait(): quit() waits on proc too, and a signal
    # handler waiting while the main code is inside wait() deadlocks on
    # Popen's internal lock.
    sleep_after = dpms_sleep_after() if blanking else None
    idle = idle_clock()
    checked = time.monotonic()
    while proc.poll() is None:
        time.sleep(0.5)
        # Nobody SIGTERMs us when a settings preview's window goes away.
        if time.monotonic() - checked > 2:
            checked = time.monotonic()
            if not window_exists(target):
                quit()
        if sleep_after and idle() >= sleep_after:
            # gamescope's SDL window suspends X's screen saver timers, DPMS
            # included, so X never powers the monitor down while it runs.
            # Do it ourselves, and stop drawing to a dark screen.
            end_saver(proc)
            subprocess.run(["xset", "dpms", "force", "off"])
    # Stay until xscreensaver stops us (exiting early would make it start
    # another hack) or our window is gone.
    while window_exists(target):
        time.sleep(2)


def stop(proc, timeout=2):
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=timeout)
    except ProcessLookupError:
        pass
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()


class MiniPreview(Gtk.DrawingArea):
    """The little screen inside the monitor picture.

    Windows previews a saver by running it with "/p <HWND>" so it draws into
    a child window of the dialog. A GTK window has no HWND, so
    preview-host.exe (see preview-host.c) opens a Wine window of this
    widget's size, runs the saver against it, and we reparent that window's
    X window in here.

    (Running the saver with "/s" in a tiny Wine virtual desktop doesn't work:
    Wine won't make a desktop smaller than 640x480.)
    """

    def __init__(self):
        super().__init__()
        self.set_size_request(SCREEN_W, SCREEN_H)
        self.proc = None
        self.poll_id = 0
        self.serial = 0
        self.tries = 0
        # Needs its own X window to be a reparent target.
        self.connect("realize", lambda w: w.get_window().ensure_native())
        self.connect("draw", self.on_draw)
        self.connect("destroy", lambda w: self.stop())

    def on_draw(self, _widget, cr):
        running = self.proc is not None and self.proc.poll() is None
        cr.set_source_rgb(*((0, 0, 0) if running else DESKTOP_BLUE))
        cr.paint()

    def stop(self):
        if self.poll_id:
            GLib.source_remove(self.poll_id)
            self.poll_id = 0
        stop(self.proc)
        self.proc = None
        self.queue_draw()

    def show_saver(self, path):
        self.stop()
        if not path or not PREVIEW_HOST:
            return
        # Unique title so a dying earlier preview is never adopted.
        self.serial += 1
        name = f"Redmond2KPreview{os.getpid()}x{self.serial}"
        # Wine works in device pixels; GTK sizes are scaled on HiDPI.
        scale = self.get_scale_factor()
        _, x, y = self.get_window().get_origin()
        size = (x * scale, y * scale, SCREEN_W * scale, SCREEN_H * scale)
        self.proc = wine(PREVIEW_HOST, name, *map(str, size),
                         windows_path(path))
        self.tries = 0
        self.poll_id = GLib.timeout_add(100, self.adopt, name)
        self.queue_draw()

    def adopt(self, name):
        """Polls until the preview host's window exists, then pulls it in."""
        if self.proc is None or self.proc.poll() is not None:
            self.poll_id = 0
            self.queue_draw()
            return False
        found = subprocess.run(["xdotool", "search", "--name", name],
                               capture_output=True, text=True).stdout.split()
        if not found:
            self.tries += 1
            if self.tries > 150:  # 15s: wine never came up, give up.
                self.poll_id = 0
                self.stop()
                return False
            return True
        self.poll_id = 0
        xid = int(found[-1])
        # An empty input shape makes the pointer pass straight through to
        # our window. Without it, hovering over the preview sends the saver
        # mouse moves and it quits, like a real full-screen saver would.
        foreign = GdkX11.X11Window.foreign_new_for_display(
            self.get_display(), xid)
        foreign.input_shape_combine_region(cairo.Region(), 0, 0)
        parent = self.get_window().get_xid()
        subprocess.run(["xdotool", "windowreparent", str(xid), str(parent)])
        subprocess.run(["xdotool", "windowmove", str(xid), "0", "0"])
        return False


class Monitor(Gtk.Fixed):
    """The Win2K beige monitor picture with the preview as its screen."""

    BODY_W, BODY_H = 184, 140
    SCREEN_X, SCREEN_Y = 16, 14

    def __init__(self):
        super().__init__()
        self.set_size_request(self.BODY_W, 166)
        self.art = Gtk.DrawingArea()
        self.art.set_size_request(self.BODY_W, 166)
        self.art.connect("draw", self.on_draw)
        self.put(self.art, 0, 0)
        self.preview = MiniPreview()
        self.put(self.preview, self.SCREEN_X, self.SCREEN_Y)

    def colour(self, name, fallback):
        found, rgba = self.get_style_context().lookup_color(name)
        if not found:
            rgba = Gdk.RGBA()
            rgba.parse(fallback)
        return rgba.red, rgba.green, rgba.blue

    def bevel(self, cr, x, y, w, h, top_left, bottom_right):
        """1px Win2K bevel just inside the rectangle."""
        cr.set_source_rgb(*top_left)
        cr.rectangle(x, y, w - 1, 1)
        cr.rectangle(x, y, 1, h - 1)
        cr.fill()
        cr.set_source_rgb(*bottom_right)
        cr.rectangle(x, y + h - 1, w, 1)
        cr.rectangle(x + w - 1, y, 1, h)
        cr.fill()

    def raised(self, cr, x, y, w, h):
        face = self.colour("bg_color", "#D4D0C8")
        light = self.colour("light_shadow", "#FFFFFF")
        shadow = self.colour("dark_shadow", "#7F7F7F")
        border = self.colour("borders", "#3F3F3F")
        cr.set_source_rgb(*face)
        cr.rectangle(x, y, w, h)
        cr.fill()
        self.bevel(cr, x, y, w, h, face, border)
        self.bevel(cr, x + 1, y + 1, w - 2, h - 2, light, shadow)

    def on_draw(self, _widget, cr):
        light = self.colour("light_shadow", "#FFFFFF")
        shadow = self.colour("dark_shadow", "#7F7F7F")
        border = self.colour("borders", "#3F3F3F")

        # Stand first so the body overlaps its top edge.
        self.raised(cr, 44, 152, 96, 14)
        self.raised(cr, 72, 138, 40, 16)
        self.raised(cr, 0, 0, self.BODY_W, self.BODY_H)

        # Sunken bezel around the screen.
        x, y = self.SCREEN_X, self.SCREEN_Y
        self.bevel(cr, x - 2, y - 2, SCREEN_W + 4, SCREEN_H + 4,
                   shadow, light)
        self.bevel(cr, x - 1, y - 1, SCREEN_W + 2, SCREEN_H + 2,
                   border, self.colour("bg_color", "#D4D0C8"))

        # Power LED.
        cr.set_source_rgb(0, 0.8, 0)
        cr.rectangle(self.BODY_W - 22, self.BODY_H - 10, 6, 3)
        cr.fill()
        return False


class ScreenSaverWindow(Gtk.Window):
    def __init__(self, folder=None):
        super().__init__(title=APP_TITLE)
        self.set_resizable(False)
        self.set_icon_name("preferences-desktop-screensaver")
        self.connect("destroy", self.on_destroy)
        self.fullscreen_proc = None
        self.hidden_cursor = None
        self.settings_proc = None

        config = load_config()["screensaver"]
        self.folder = folder or config.get("folder", "")
        resolution = configured("resolution", RESOLUTIONS,
                                DEFAULT_RESOLUTION)
        effect = configured("effect", [e for e, _ in EFFECTS], "none")
        timing = configured("timing", [t for t, _, _ in TIMINGS],
                            DEFAULT_TIMING)
        global timer_tick_us
        timer_tick_us = timing_tick(timing)
        self.saved = (self.folder, config.get("saver", ""), resolution,
                      effect, timing)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                        border_width=6)
        self.add(outer)

        notebook = Gtk.Notebook()
        outer.pack_start(notebook, True, True, 0)

        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                       border_width=10)
        notebook.append_page(page, Gtk.Label(label="Screen Saver",
                                             use_underline=True))

        self.monitor = Monitor()
        self.monitor.set_halign(Gtk.Align.CENTER)
        page.pack_start(self.monitor, False, False, 4)

        frame = Gtk.Frame(label="Screen Saver")
        page.pack_start(frame, False, False, 0)
        grid = Gtk.Grid(row_spacing=8, column_spacing=6, border_width=10)
        frame.add(grid)

        self.combo = Gtk.ComboBoxText(hexpand=True)
        self.combo.set_size_request(180, -1)
        self.combo.connect("changed", self.on_saver_changed)
        grid.attach(self.combo, 0, 0, 2, 1)

        self.settings_button = Gtk.Button.new_with_mnemonic("Se_ttings")
        self.settings_button.connect("clicked", self.on_settings)
        grid.attach(self.settings_button, 2, 0, 1, 1)

        self.preview_button = Gtk.Button.new_with_mnemonic("Pre_view")
        self.preview_button.connect("clicked", self.on_preview)
        grid.attach(self.preview_button, 3, 0, 1, 1)

        # Not in the real dialog (Windows always used system32), but the
        # .scr files can't ship with the theme, so the folder is the user's.
        folder_row = Gtk.Box(spacing=6)
        grid.attach(folder_row, 0, 1, 4, 1)
        folder_row.pack_start(Gtk.Label(label="Folder:"), False, False, 0)
        self.folder_entry = Gtk.Entry(editable=False, can_focus=False)
        folder_row.pack_start(self.folder_entry, True, True, 0)
        browse = Gtk.Button.new_with_mnemonic("_Browse...")
        browse.connect("clicked", self.on_browse)
        folder_row.pack_start(browse, False, False, 0)

        # Also not in Windows: the screen size the saver sees in full screen
        # (needs gamescope; without it savers get the real screen).
        size_row = Gtk.Box(spacing=6)
        grid.attach(size_row, 0, 2, 4, 1)
        size_row.pack_start(Gtk.Label(label="Full screen at:"),
                            False, False, 0)
        self.size_combo = Gtk.ComboBoxText()
        for size in RESOLUTIONS:
            self.size_combo.append(size, size.replace("x", " by ") +
                                   " pixels")
        self.size_combo.set_active_id(resolution)
        self.size_combo.set_sensitive(bool(shutil.which("gamescope")))
        self.size_combo.connect("changed", lambda c: self.update_buttons())
        size_row.pack_start(self.size_combo, False, False, 0)

        # Also not in Windows: a CRT shader over full screen (gamescope).
        effect_row = Gtk.Box(spacing=6)
        grid.attach(effect_row, 0, 3, 4, 1)
        effect_row.pack_start(Gtk.Label(label="Monitor effect:"),
                              False, False, 0)
        self.effect_combo = Gtk.ComboBoxText()
        for effect_id, label in EFFECTS:
            self.effect_combo.append(effect_id, label)
        self.effect_combo.set_active_id(effect)
        self.effect_combo.set_sensitive(bool(shutil.which("gamescope")))
        self.effect_combo.connect("changed", lambda c: self.update_buttons())
        effect_row.pack_start(self.effect_combo, False, False, 0)

        # Also not in Windows: how coarse the savers' timers are. Old savers
        # step their animation per timer tick, so Wine's precise timers make
        # them run faster than they did (see saver-timer.c).
        timing_row = Gtk.Box(spacing=6)
        grid.attach(timing_row, 0, 4, 4, 1)
        timing_row.pack_start(Gtk.Label(label="Timing:"), False, False, 0)
        self.timing_combo = Gtk.ComboBoxText()
        for timing_id, label, _ in TIMINGS:
            self.timing_combo.append(timing_id, label)
        self.timing_combo.set_active_id(timing)
        self.timing_combo.set_sensitive(bool(SAVER_RUN))
        self.timing_combo.connect("changed", self.on_timing_changed)
        timing_row.pack_start(self.timing_combo, False, False, 0)

        buttons = Gtk.ButtonBox(spacing=6, layout_style=Gtk.ButtonBoxStyle.END)
        outer.pack_start(buttons, False, False, 0)
        ok = Gtk.Button(label="OK")
        ok.connect("clicked", self.on_ok)
        cancel = Gtk.Button(label="Cancel")
        cancel.connect("clicked", lambda b: self.destroy())
        self.apply_button = Gtk.Button.new_with_mnemonic("_Apply")
        self.apply_button.connect("clicked", lambda b: self.apply())
        for button in (ok, cancel, self.apply_button):
            buttons.add(button)
        ok.set_can_default(True)
        self.set_default(ok)

        self.load_folder(self.folder, select=self.saved[1])
        self.connect("map-event", self.on_map)

    # -- state ----------------------------------------------------------

    def selected(self):
        return self.combo.get_active_id() or NONE_ID

    def load_folder(self, folder, select=NONE_ID):
        self.folder = folder
        self.folder_entry.set_text(folder or "")
        self.combo.remove_all()
        self.combo.append(NONE_ID, "(None)")
        for name, path in find_savers(folder):
            self.combo.append(path, name)
        # Savers are stored by full path; keep the selection if it still
        # exists after a folder change, otherwise fall back to (None).
        if not self.combo.set_active_id(select):
            self.combo.set_active_id(NONE_ID)

    def update_buttons(self):
        has_saver = self.selected() != NONE_ID
        self.settings_button.set_sensitive(has_saver)
        self.preview_button.set_sensitive(has_saver)
        self.apply_button.set_sensitive(self.state() != self.saved)

    def state(self):
        return (self.folder, self.selected(), self.size_combo.get_active_id(),
                self.effect_combo.get_active_id(),
                self.timing_combo.get_active_id())

    def apply(self):
        save_config(*self.state())
        try:
            configure_xscreensaver(find_savers(self.folder), self.selected())
        except (OSError, StopIteration) as error:
            dialog = Gtk.MessageDialog(
                transient_for=self, message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Couldn't update the XScreenSaver settings.",
                secondary_text=str(error) or "No programs list found.")
            dialog.run()
            dialog.destroy()
            return False
        self.saved = self.state()
        self.update_buttons()
        return True

    # -- signals --------------------------------------------------------

    def on_saver_changed(self, _combo):
        self.update_buttons()
        # Before the window is mapped there is no reparent target yet;
        # on_map starts the first preview.
        if self.monitor.preview.get_mapped():
            self.monitor.preview.show_saver(self.selected())

    def on_timing_changed(self, combo):
        global timer_tick_us
        timer_tick_us = timing_tick(combo.get_active_id())
        self.update_buttons()
        # Show the new speed in the little preview straight away.
        if self.monitor.preview.get_mapped():
            self.monitor.preview.show_saver(self.selected())

    def on_map(self, _window, _event):
        self.monitor.preview.show_saver(self.selected())
        return False

    def on_settings(self, _button):
        if self.settings_proc is not None:
            return
        # The saver's own dialog, at the prefix's 96 DPI. Raising the DPI
        # for it made the text bigger but cut off options in some savers'
        # fixed-size dialogs.
        self.settings_proc = run_saver(self.selected(), "/c")
        # Like Windows, the dialog is modal to Display Properties.
        self.get_child().set_sensitive(False)
        GLib.timeout_add(250, self.wait_settings)

    def wait_settings(self):
        if self.settings_proc.poll() is None:
            return True
        self.settings_proc = None
        self.get_child().set_sensitive(True)
        return False

    def screen_height(self):
        """Height in device pixels of the monitor this window is on."""
        display = self.get_display()
        monitor = display.get_monitor_at_window(self.get_window())
        return monitor.get_geometry().height * monitor.get_scale_factor()

    def on_preview(self, _button):
        if self.fullscreen_proc is not None:
            return
        # Like Windows: the little preview stops while the real one runs.
        self.monitor.preview.stop()
        self.fullscreen_proc = run_fullscreen(
            self.selected(), self.size_combo.get_active_id(),
            self.effect_combo.get_active_id(), self.screen_height())
        self.hidden_cursor = HiddenCursor()
        GLib.timeout_add(250, self.wait_fullscreen)

    def wait_fullscreen(self):
        if self.fullscreen_proc.poll() is None:
            return True
        self.fullscreen_proc = None
        self.hidden_cursor.close()
        self.monitor.preview.show_saver(self.selected())
        return False

    def on_browse(self, _button):
        dialog = Gtk.FileChooserDialog(
            title="Browse for Folder", transient_for=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER)
        dialog.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                           "OK", Gtk.ResponseType.OK)
        if self.folder and os.path.isdir(self.folder):
            dialog.set_current_folder(self.folder)
        if dialog.run() == Gtk.ResponseType.OK:
            self.load_folder(dialog.get_filename(), select=self.selected())
        dialog.destroy()

    def on_ok(self, _button):
        if self.apply():
            self.destroy()

    def on_destroy(self, _window):
        self.monitor.preview.stop()
        end_saver(self.fullscreen_proc)
        stop(self.settings_proc)
        # After a Preview, the little preview's restart leaves Wine's desktop
        # process (explorer.exe /desktop) in a session of its own, which
        # outlives its helper and keeps wineserver and Wine's services up for
        # good. Shut the prefix down, unless xscreensaver (or its settings'
        # preview) is running a saver in it right now.
        if subprocess.run(["pgrep", "-f", r"redmond2k-screensaver\S* --hack "],
                          stdout=subprocess.DEVNULL).returncode != 0:
            subprocess.run(["wineserver", "-k"],
                           env=dict(os.environ, WINEPREFIX=str(WINEPREFIX)),
                           stderr=subprocess.DEVNULL)
        Gtk.main_quit()


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--hack":
        # Percent-encoded by configure_xscreensaver(); xscreensaver also
        # passes --root, which we ignore.
        run_hack(urllib.parse.unquote(sys.argv[2]))
        return
    folder = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else None
    window = ScreenSaverWindow(folder)
    window.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
