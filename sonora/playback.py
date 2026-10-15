from __future__ import annotations

import gi
import random
gi.require_version("Gst", "1.0")
from gi.repository import Gio, Gst

from sonora.models import Track

Gst.init(None)


class PlaybackService:
    def __init__(self, on_changed=None):
        self._player = Gst.ElementFactory.make("playbin", "sonora-player")
        if self._player is None:
            raise RuntimeError("GStreamer playbin is unavailable")
        self._bus = self._player.get_bus()
        self._bus.add_signal_watch()
        self._bus.connect("message", self._on_bus_message)
        self._on_changed = on_changed or (lambda: None)
        self.queue: list[Track] = []
        self._natural_queue: list[Track] = []
        self.index = -1
        self.error = ""
        self.playing = False
        self.stopped = True
        self.loop_status = "None"
        self.shuffle_enabled = False
        self._volume = 0.8
        self._player.set_property("volume", self._volume)

    @property
    def current_track(self) -> Track | None:
        return self.queue[self.index] if 0 <= self.index < len(self.queue) else None

    @property
    def position_us(self) -> int:
        ok, value = self._player.query_position(Gst.Format.TIME)
        return max(0, value // 1000) if ok else 0

    @property
    def duration_us(self) -> int:
        ok, value = self._player.query_duration(Gst.Format.TIME)
        return max(0, value // 1000) if ok else 0

    @property
    def volume(self) -> float:
        return self._volume

    def set_volume(self, value: float) -> None:
        self._volume = min(1.0, max(0.0, value))
        self._player.set_property("volume", self._volume)

    def play_track(self, track: Track, queue: list[Track] | None = None) -> None:
        self._natural_queue = list(queue or [track])
        self.queue = list(self._natural_queue)
        self.shuffle_enabled = False
        try:
            self.index = next(index for index, queued in enumerate(self.queue) if queued.path == track.path)
        except StopIteration:
            self.queue = [track]
            self.index = 0
        self.error = ""
        self._start_current()

    def _start_current(self) -> None:
        track = self.current_track
        if track is None:
            return
        self._player.set_state(Gst.State.NULL)
        self._player.set_property("uri", Gio.File.new_for_path(track.path).get_uri())
        self._player.set_state(Gst.State.PLAYING)
        self.playing = True
        self.stopped = False
        self._on_changed()

    def toggle(self) -> None:
        if self.current_track is None:
            return
        if self.playing:
            self._player.set_state(Gst.State.PAUSED)
            self.playing = False
        else:
            self._player.set_state(Gst.State.PLAYING)
            self.playing = True
            self.stopped = False
        self._on_changed()

    def next(self) -> None:
        if self.index + 1 < len(self.queue):
            self.index += 1
            self._start_current()
        elif self.loop_status == "Playlist" and self.queue:
            self.index = 0
            self._start_current()

    def previous(self) -> None:
        if self.position_us > 3000:
            self.seek(0)
        elif self.index > 0:
            self.index -= 1
            self._start_current()
        elif self.loop_status == "Playlist" and self.queue:
            self.index = len(self.queue) - 1
            self._start_current()

    def set_loop_status(self, value: str) -> None:
        if value in {"None", "Track", "Playlist"}:
            self.loop_status = value

    def set_shuffle(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self.shuffle_enabled:
            return
        current = self.current_track
        self.shuffle_enabled = enabled
        if enabled:
            current_path = current.path if current else ""
            remaining = [track for track in self.queue if track.path != current_path]
            random.shuffle(remaining)
            self.queue = ([current] if current else []) + remaining
            self.index = 0 if current else -1
        else:
            current_path = current.path if current else ""
            self.queue = list(self._natural_queue)
            self.index = next((i for i, track in enumerate(self.queue) if track.path == current_path), -1)
        self._on_changed()

    def stop(self) -> None:
        if self.current_track is not None:
            self._player.set_state(Gst.State.READY)
        self.playing = False
        self.stopped = True
        self._on_changed()

    def seek(self, position_ms: int) -> None:
        self._player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                                 max(0, position_ms) * Gst.MSECOND)

    def _on_bus_message(self, _bus, message) -> None:
        if message.type == Gst.MessageType.EOS:
            if self.loop_status == "Track" and self.current_track:
                self._start_current()
            elif self.index + 1 < len(self.queue) or self.loop_status == "Playlist":
                self.next()
            else:
                self.playing = False
                self.stopped = True
                self._player.set_state(Gst.State.READY)
                self._on_changed()
        elif message.type == Gst.MessageType.ERROR:
            error, debug = message.parse_error()
            self.error = error.message
            self.playing = False
            self.stopped = True
            self._player.set_state(Gst.State.READY)
            self._on_changed()

    def close(self) -> None:
        self._bus.remove_signal_watch()
        self._player.set_state(Gst.State.NULL)
