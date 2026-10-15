from __future__ import annotations

import gi
gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib


OBJECT_PATH = "/org/mpris/MediaPlayer2"
BUS_NAME = "org.mpris.MediaPlayer2.Sonora"
PLAYER_INTERFACE = "org.mpris.MediaPlayer2.Player"
ROOT_INTERFACE = "org.mpris.MediaPlayer2"

INTROSPECTION_XML = """<node>
  <interface name="org.mpris.MediaPlayer2">
    <method name="Raise"/><method name="Quit"/>
    <property name="CanQuit" type="b" access="read"/>
    <property name="CanRaise" type="b" access="read"/>
    <property name="Identity" type="s" access="read"/>
    <property name="DesktopEntry" type="s" access="read"/>
    <property name="HasTrackList" type="b" access="read"/>
    <property name="SupportedUriSchemes" type="as" access="read"/>
    <property name="SupportedMimeTypes" type="as" access="read"/>
  </interface>
  <interface name="org.mpris.MediaPlayer2.Player">
    <method name="Next"/><method name="Previous"/><method name="Pause"/>
    <method name="PlayPause"/><method name="Stop"/><method name="Play"/>
    <method name="Seek"><arg direction="in" name="Offset" type="x"/></method>
    <method name="SetPosition"><arg direction="in" name="TrackId" type="o"/><arg direction="in" name="Position" type="x"/></method>
    <method name="OpenUri"><arg direction="in" name="Uri" type="s"/></method>
    <property name="PlaybackStatus" type="s" access="read"/>
    <property name="LoopStatus" type="s" access="readwrite"/>
    <property name="Rate" type="d" access="readwrite"/>
    <property name="Shuffle" type="b" access="readwrite"/>
    <property name="Metadata" type="a{sv}" access="read"/>
    <property name="Volume" type="d" access="readwrite"/>
    <property name="Position" type="x" access="read"/>
    <property name="MinimumRate" type="d" access="read"/>
    <property name="MaximumRate" type="d" access="read"/>
    <property name="CanGoNext" type="b" access="read"/>
    <property name="CanGoPrevious" type="b" access="read"/>
    <property name="CanPlay" type="b" access="read"/>
    <property name="CanPause" type="b" access="read"/>
    <property name="CanSeek" type="b" access="read"/>
    <property name="CanControl" type="b" access="read"/>
  </interface>
</node>"""


class MprisService:
    def __init__(self, playback, on_raise, on_quit, on_open_uri):
        self.playback = playback
        self.on_raise = on_raise
        self.on_quit = on_quit
        self.on_open_uri = on_open_uri
        self._registrations = []
        self.connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        node = Gio.DBusNodeInfo.new_for_xml(INTROSPECTION_XML)
        for name in (ROOT_INTERFACE, PLAYER_INTERFACE):
            info = node.lookup_interface(name)
            reg_id = self.connection.register_object(
                OBJECT_PATH, info, self._method_call, self._get_property, self._set_property
            )
            self._registrations.append(reg_id)
        result = self.connection.call_sync(
            "org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus", "RequestName",
            GLib.Variant("(su)", (BUS_NAME, 4)), GLib.VariantType.new("(u)"),
            Gio.DBusCallFlags.NONE, -1, None,
        )
        self._owner_result = result.unpack()[0]

    def _method_call(self, _connection, _sender, _path, interface, method, parameters, invocation):
        if interface == ROOT_INTERFACE:
            if method == "Raise":
                self.on_raise()
            elif method == "Quit":
                self.on_quit()
        else:
            if method == "Next":
                self.playback.next()
            elif method == "Previous":
                self.playback.previous()
            elif method == "Pause":
                if self.playback.playing:
                    self.playback.toggle()
            elif method == "PlayPause":
                self.playback.toggle()
            elif method == "Stop":
                self.playback.stop()
            elif method == "Play":
                if self.playback.current_track and not self.playback.playing:
                    self.playback.toggle()
            elif method == "Seek":
                offset = parameters.unpack()[0]
                self.playback.seek((self.playback.position_us + offset) // 1000)
                self._emit_seeked()
            elif method == "SetPosition":
                track_id, position = parameters.unpack()
                if track_id == self._track_id():
                    self.playback.seek(position // 1000)
                    self._emit_seeked()
            elif method == "OpenUri":
                uri = parameters.unpack()[0]
                if not self.on_open_uri(uri):
                    invocation.return_dbus_error("org.mpris.MediaPlayer2.Player.NotSupported", "Only local MP3 and M4A files can be opened")
                    return
        invocation.return_value(GLib.Variant("()", ()))

    def _get_property(self, _connection, _sender, _path, interface, name):
        if interface == ROOT_INTERFACE:
            values = {
                "CanQuit": True, "CanRaise": True, "Identity": "Sonora",
                "DesktopEntry": "io.github.Iroddyan.Sonora", "HasTrackList": False,
                "SupportedUriSchemes": ["file"], "SupportedMimeTypes": ["audio/mpeg", "audio/mp4"],
            }
            return _variant_for(name, values[name])
        track = self.playback.current_track
        values = {
            "PlaybackStatus": "Playing" if self.playback.playing else ("Stopped" if self.playback.stopped else ("Paused" if track else "Stopped")),
            "LoopStatus": self.playback.loop_status, "Rate": 1.0, "Shuffle": self.playback.shuffle_enabled,
            "Metadata": self._metadata(), "Volume": self.playback.volume,
            "Position": self.playback.position_us, "MinimumRate": 1.0, "MaximumRate": 1.0,
            "CanGoNext": self.playback.index + 1 < len(self.playback.queue) or self.playback.loop_status == "Playlist",
            "CanGoPrevious": self.playback.index > 0 or self.playback.position_us > 3_000_000,
            "CanPlay": track is not None, "CanPause": track is not None,
            "CanSeek": track is not None and self.playback.duration_us > 0, "CanControl": True,
        }
        return _variant_for(name, values[name])

    def _set_property(self, _connection, _sender, _path, interface, name, value):
        if interface != PLAYER_INTERFACE:
            return False
        if name == "Volume":
            self.playback.set_volume(value.unpack())
        elif name == "LoopStatus":
            if value.unpack() not in {"None", "Track", "Playlist"}:
                return False
            self.playback.set_loop_status(value.unpack())
        elif name == "Shuffle":
            self.playback.set_shuffle(value.unpack())
        else:
            return False
        self.emit_changed()
        return True

    def _track_id(self) -> str:
        track = self.playback.current_track
        return f"/org/mpris/MediaPlayer2/Track/{track.id}" if track else "/org/mpris/MediaPlayer2/Track/0"

    def _metadata(self):
        track = self.playback.current_track
        if not track:
            return GLib.Variant("a{sv}", {})
        values = {
            "mpris:trackid": GLib.Variant("o", self._track_id()),
            "mpris:length": GLib.Variant("x", track.duration_ms * 1000),
            "xesam:title": GLib.Variant("s", track.title),
            "xesam:artist": GLib.Variant("as", [track.display_artist]),
            "xesam:album": GLib.Variant("s", track.album),
            "xesam:url": GLib.Variant("s", Gio.File.new_for_path(track.path).get_uri()),
        }
        if track.artwork_path:
            values["mpris:artUrl"] = GLib.Variant("s", Gio.File.new_for_path(track.artwork_path).get_uri())
        return GLib.Variant("a{sv}", values)

    def emit_changed(self):
        for interface, values in ((PLAYER_INTERFACE, {
            "PlaybackStatus": _variant_for("PlaybackStatus", "Playing" if self.playback.playing else ("Stopped" if self.playback.stopped else ("Paused" if self.playback.current_track else "Stopped"))),
            "Metadata": self._metadata(), "Volume": _variant_for("Volume", self.playback.volume),
            "LoopStatus": _variant_for("LoopStatus", self.playback.loop_status),
            "Shuffle": _variant_for("Shuffle", self.playback.shuffle_enabled),
            "CanGoNext": _variant_for("CanGoNext", self.playback.index + 1 < len(self.playback.queue) or self.playback.loop_status == "Playlist"),
            "CanGoPrevious": _variant_for("CanGoPrevious", self.playback.index > 0 or self.playback.position_us > 3_000_000),
            "CanPlay": _variant_for("CanPlay", self.playback.current_track is not None),
            "CanPause": _variant_for("CanPause", self.playback.current_track is not None),
            "CanSeek": _variant_for("CanSeek", self.playback.current_track is not None and self.playback.duration_us > 0),
        }),):
            try:
                self.connection.emit_signal(None, OBJECT_PATH, "org.freedesktop.DBus.Properties", "PropertiesChanged",
                                            GLib.Variant("(sa{sv}as)", (interface, values, [])))
            except GLib.Error:
                pass

    def _emit_seeked(self):
        try:
            self.connection.emit_signal(None, OBJECT_PATH, PLAYER_INTERFACE, "Seeked",
                                        GLib.Variant("(x)", (self.playback.position_us,)))
        except GLib.Error:
            pass

    def close(self):
        for registration in self._registrations:
            self.connection.unregister_object(registration)
        try:
            self.connection.call_sync("org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus", "ReleaseName",
                                      GLib.Variant("(s)", (BUS_NAME,)), GLib.VariantType.new("(u)"),
                                      Gio.DBusCallFlags.NONE, -1, None)
        except GLib.Error:
            pass


def _variant_for(name, value):
    signature = {
        "CanQuit": "b", "CanRaise": "b", "Identity": "s", "DesktopEntry": "s", "HasTrackList": "b",
        "SupportedUriSchemes": "as", "SupportedMimeTypes": "as", "PlaybackStatus": "s", "LoopStatus": "s",
        "Rate": "d", "Shuffle": "b", "Volume": "d", "Position": "x", "MinimumRate": "d", "MaximumRate": "d",
        "CanGoNext": "b", "CanGoPrevious": "b", "CanPlay": "b", "CanPause": "b", "CanSeek": "b", "CanControl": "b",
    }.get(name)
    if name == "Metadata":
        return value
    return GLib.Variant(signature, value)
