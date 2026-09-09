#!/usr/bin/python3
"""Plays the Redmond2K sound whenever a desktop session ends.

Installed as /usr/local/bin/redmond2k-session-sound by
../install-session-sound.sh, which substitutes the two placeholders below.

Runs as root, outside any login session, for two reasons:

  * /dev/snd/* is root:audio 0660, and a normal user's access to it comes
    from a logind uaccess ACL that is granted to the *active session* and
    revoked the moment that session ends. Anything trying to play audio
    after logout gets "audio open error: Permission denied". Root bypasses
    that entirely.
  * It must not depend on user@$UID.service stopping. With Fedora's
    KillUserProcesses=no, stray daemons (localsearch, geoclue, ...) keep
    the session scope alive after logout, so the user manager may never
    stop at all.

Two events end a session, and both are handled here:

  logout            a Class=user session leaves the "open" set (it either
                    disappears or goes State=closing). Detected by polling
                    once a second - logind does not reliably emit a
                    PropertiesChanged for State, and SessionRemoved never
                    arrives for a scope stranded by leftover processes.

  shutdown/restart  logind's PrepareForShutdown signal, which fires before
                    anything is torn down. A "delay" inhibitor is held from
                    startup so that logind waits for us here; the sound is
                    played synchronously and the inhibitor released, which
                    lets the shutdown continue.
"""

import os
import subprocess
import sys
import time

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

SOUND_FILE = "__SOUND_FILE__"
ALSA_DEVICE = "__ALSA_DEVICE__"

LOGIN1 = "org.freedesktop.login1"
MANAGER_PATH = "/org/freedesktop/login1"
MANAGER_IFACE = "org.freedesktop.login1.Manager"
SESSION_IFACE = "org.freedesktop.login1.Session"

PLAY_TIMEOUT = 15
PLAY_ATTEMPTS = 3


def log(message):
    print(message, file=sys.stderr, flush=True)


def play_sound(reason):
    """Play the sound synchronously, retrying if the card is still busy."""
    log("playing session-end sound (%s)" % reason)
    for attempt in range(1, PLAY_ATTEMPTS + 1):
        try:
            result = subprocess.run(
                ["/usr/bin/aplay", "-q", "-D", ALSA_DEVICE, SOUND_FILE],
                stdin=subprocess.DEVNULL, capture_output=True,
                timeout=PLAY_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            log("aplay timed out")
            return
        if result.returncode == 0:
            return
        # Most likely the card is still held by a not-yet-idle PipeWire.
        log("aplay failed (attempt %d/%d): %s" % (
            attempt, PLAY_ATTEMPTS,
            result.stderr.decode(errors="replace").strip(),
        ))
        time.sleep(0.4)


class SessionSound:
    def __init__(self):
        self.bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        self.inhibit_fds = []
        self.shutting_down = False

        # Seed the set so sessions that are already open (or already
        # stranded in "closing") don't fire the sound at startup.
        self.open_sessions = self.user_sessions()
        log("watching sessions: %s" % (sorted(self.open_sessions) or "none"))

        self.take_inhibitor()
        self.bus.signal_subscribe(
            LOGIN1, MANAGER_IFACE, "PrepareForShutdown", MANAGER_PATH,
            None, Gio.DBusSignalFlags.NONE, self.on_prepare_for_shutdown, None,
        )
        GLib.timeout_add_seconds(1, self.poll_sessions)

    # -- logind helpers ----------------------------------------------------

    def session_properties(self, path):
        try:
            reply = self.bus.call_sync(
                LOGIN1, path, "org.freedesktop.DBus.Properties", "GetAll",
                GLib.Variant("(s)", (SESSION_IFACE,)), None,
                Gio.DBusCallFlags.NONE, -1, None,
            )
            return reply.unpack()[0]
        except GLib.Error:
            # The session can disappear between listing and querying it.
            return {}

    def user_sessions(self):
        """Session ids of real logins that are still open.

        Excludes the LightDM greeter (Class=greeter) and the user manager's
        own session (Class=manager), so shutting down from the login screen
        stays silent.
        """
        try:
            reply = self.bus.call_sync(
                LOGIN1, MANAGER_PATH, MANAGER_IFACE, "ListSessions", None,
                None, Gio.DBusCallFlags.NONE, -1, None,
            )
        except GLib.Error as error:
            log("could not list sessions: %s" % error.message)
            return set()

        sessions = set()
        for session_id, _uid, _user, _seat, path in reply.unpack()[0]:
            properties = self.session_properties(path)
            if properties.get("Class") != "user":
                continue
            if properties.get("State") == "closing":
                continue
            sessions.add(session_id)
        return sessions

    def take_inhibitor(self):
        if self.inhibit_fds:
            return
        try:
            _reply, fd_list = self.bus.call_with_unix_fd_list_sync(
                LOGIN1, MANAGER_PATH, MANAGER_IFACE, "Inhibit",
                GLib.Variant("(ssss)", (
                    "shutdown",
                    "Redmond2K session sound",
                    "Playing the session-end sound",
                    "delay",
                )),
                GLib.VariantType("(h)"), Gio.DBusCallFlags.NONE, -1, None, None,
            )
            self.inhibit_fds = fd_list.steal_fds()
            log("holding shutdown delay inhibitor")
        except GLib.Error as error:
            log("could not take inhibitor: %s" % error.message)

    def release_inhibitor(self):
        for fd in self.inhibit_fds:
            try:
                os.close(fd)
            except OSError:
                pass
        if self.inhibit_fds:
            log("released shutdown delay inhibitor")
        self.inhibit_fds = []

    # -- event handlers ----------------------------------------------------

    def poll_sessions(self):
        current = self.user_sessions()
        ended = self.open_sessions - current
        self.open_sessions = current
        if ended and not self.shutting_down:
            play_sound("logout of session %s" % ",".join(sorted(ended)))
        return GLib.SOURCE_CONTINUE

    def on_prepare_for_shutdown(self, _conn, _sender, _path, _iface,
                                _signal, params, _user_data):
        starting = params.unpack()[0]
        if not starting:
            # A scheduled shutdown was cancelled; re-arm for the next one.
            log("shutdown cancelled")
            self.shutting_down = False
            self.take_inhibitor()
            return

        # Only for a real login - shutting down from the greeter is silent.
        self.shutting_down = True
        if self.open_sessions:
            play_sound("shutdown/restart")
        else:
            log("shutdown with no user session - staying silent")
        self.release_inhibitor()


def main():
    if not os.path.exists(SOUND_FILE):
        log("sound file not found: %s" % SOUND_FILE)
        return 1

    # `redmond2k-session-sound --test` plays the sound the same way the
    # daemon would, so the audio device and path can be checked without
    # logging out or rebooting.
    if "--test" in sys.argv[1:]:
        play_sound("manual test")
        return 0

    SessionSound()
    GLib.MainLoop().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
