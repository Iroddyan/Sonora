from __future__ import annotations

import random
import time
from pathlib import Path

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gio, Gst

from sonora.models import Track

Gst.init(None)


class PlaybackService:
    """GStreamer playback with a current-first queue and explicit history."""

    def __init__(self, on_changed=None, on_session_started=None, on_listened=None,
                 on_session_ended=None, on_error=None):
        self._player = Gst.ElementFactory.make("playbin", "sonora-player")
        if self._player is None:
            raise RuntimeError("GStreamer playbin is unavailable")
        self._bus = self._player.get_bus()
        self._bus.add_signal_watch()
        self._bus.connect("message", self._on_bus_message)
        self._on_changed = on_changed or (lambda: None)
        self._on_session_started = on_session_started or (lambda _track: None)
        self._on_listened = on_listened or (lambda _session_id, _listened_ms: None)
        self._on_session_ended = on_session_ended or (lambda _session_id, _reason: None)
        self._on_error = on_error or (lambda _message: None)
        self._session_id = None
        self._session_track = None
        self._last_position_ms = 0
        self._last_sample_time = 0.0
        self._last_checkpoint = 0.0
        self._pending_listened_ms = 0
        self._restore_position_ms = None
        self.queue: list[Track] = []  # Current track followed by upcoming tracks.
        self._natural_queue: list[Track] = []
        self.history: list[Track] = []
        self.index = -1
        self.error = ""
        self.playing = False
        self.stopped = True
        self.loop_status = "None"
        self.shuffle_enabled = False
        self._volume = 0.8
        self._muted = False
        self._volume_before_mute = self._volume
        self._player.set_property("volume", self._volume)

    @property
    def current_track(self) -> Track | None:
        return self.queue[0] if self.queue else None

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

    @property
    def muted(self) -> bool:
        return self._muted

    @property
    def can_next(self) -> bool:
        return len(self.queue) > 1 or self.loop_status == "Playlist" and bool(self._natural_queue)

    @property
    def can_previous(self) -> bool:
        return bool(self.history) or self.position_us > 3_000_000

    def set_volume(self, value: float) -> None:
        self._volume = min(1.0, max(0.0, float(value)))
        if not self._muted:
            self._player.set_property("volume", self._volume)
        self._on_changed()

    def set_muted(self, value: bool) -> None:
        value = bool(value)
        if value == self._muted:
            return
        if value:
            self._volume_before_mute = self._volume if self._volume > 0 else self._volume_before_mute
            self._muted = True
            self._player.set_property("volume", 0.0)
        else:
            self._muted = False
            if self._volume <= 0:
                self._volume = self._volume_before_mute or 0.8
            self._player.set_property("volume", self._volume)
        self._on_changed()

    def play_track(self, track: Track, queue: list[Track] | None = None) -> None:
        source = list(queue or [track])
        selected = next((index for index, item in enumerate(source) if item.path == track.path), None)
        if selected is None:
            source = [track]
        else:
            source = source[selected:]
        self._finish_session("track_changed")
        self._natural_queue = list(source)
        self.queue = list(source)
        self.history.clear()
        self.index = 0 if self.queue else -1
        self.shuffle_enabled = False
        self.error = ""
        self._start_current()

    def restore_state(self, queue: list[Track], position_ms: int, volume: float = 0.8,
                      muted: bool = False, shuffle: bool = False, loop_status: str = "None") -> None:
        self._finish_session("app_closed")
        self._natural_queue = list(queue)
        self.queue = list(queue)
        self.history.clear()
        self.index = 0 if self.queue else -1
        self.shuffle_enabled = bool(shuffle)
        self.loop_status = loop_status if loop_status in {"None", "Playlist", "Track"} else "None"
        self._volume = min(1.0, max(0.0, float(volume)))
        self._volume_before_mute = self._volume or 0.8
        self._muted = bool(muted)
        self._player.set_property("volume", 0.0 if self._muted else self._volume)
        while self.queue and not Path(self.queue[0].path).is_file():
            missing = self.queue.pop(0)
            self.history.append(missing)
            self._on_error(f"Could not find {missing.title}; skipped it.")
        self._natural_queue = [item for item in self._natural_queue if Path(item.path).is_file()]
        track = self.current_track
        if track is None:
            self.queue.clear()
            self.index = -1
            self.stopped = True
            self.playing = False
            self._on_changed()
            return
        self._player.set_state(Gst.State.NULL)
        self._player.set_property("uri", Gio.File.new_for_path(track.path).get_uri())
        self._player.set_state(Gst.State.PAUSED)
        self._restore_position_ms = max(0, int(position_ms))
        self.playing = False
        self.stopped = False
        self._on_changed()

    def _start_current(self) -> None:
        self._finish_session("track_changed")
        track = self.current_track
        if track is None:
            self.playing = False
            self.stopped = True
            self._on_changed()
            return
        if not Path(track.path).is_file():
            self._skip_unplayable(f"Could not find {track.title}; skipped it.")
            return
        self._player.set_state(Gst.State.NULL)
        self._player.set_property("uri", Gio.File.new_for_path(track.path).get_uri())
        self._player.set_state(Gst.State.PLAYING)
        self.playing = True
        self.stopped = False
        self.error = ""
        self._session_track = track
        self._session_id = self._on_session_started(track)
        self._last_position_ms = self.position_us // 1000
        self._last_sample_time = time.monotonic()
        self._last_checkpoint = self._last_sample_time
        self._pending_listened_ms = 0
        self._on_changed()

    def _skip_unplayable(self, message: str) -> None:
        self._on_error(message)
        if self.queue:
            self.history.append(self.queue.pop(0))
        if self.queue:
            self._start_current()
        else:
            self.index = -1
            self.playing = False
            self.stopped = True
            self._on_changed()

    def record_progress(self) -> None:
        """Accumulate actual forward playback progress, excluding pauses and seeks."""
        if self._session_id is None or self._session_track is None:
            return
        now = time.monotonic()
        position_ms = self.position_us // 1000
        elapsed_ms = max(1.0, (now - self._last_sample_time) * 1000)
        delta_ms = position_ms - self._last_position_ms
        if self.playing and 0 < delta_ms <= max(2500, elapsed_ms * 2):
            self._pending_listened_ms += int(delta_ms)
        self._last_position_ms = position_ms
        self._last_sample_time = now
        if self._pending_listened_ms >= 10_000 or now - self._last_checkpoint >= 15:
            self._flush_listened_time()
            self._last_checkpoint = now

    def _flush_listened_time(self) -> None:
        if self._session_id is not None and self._pending_listened_ms:
            self._on_listened(self._session_id, self._pending_listened_ms)
            self._pending_listened_ms = 0

    def _finish_session(self, reason: str) -> None:
        if self._session_id is None:
            return
        self.record_progress()
        self._flush_listened_time()
        session_id = self._session_id
        self._session_id = None
        self._session_track = None
        self._on_session_ended(session_id, reason)

    def _begin_restored_session(self) -> None:
        track = self.current_track
        if track and self._session_id is None:
            self._session_track = track
            self._session_id = self._on_session_started(track)
            self._last_position_ms = self.position_us // 1000
            self._last_sample_time = time.monotonic()
            self._last_checkpoint = self._last_sample_time
            self._pending_listened_ms = 0

    def toggle(self) -> None:
        if self.current_track is None:
            return
        if self.playing:
            self.record_progress()
            self._player.set_state(Gst.State.PAUSED)
            self.playing = False
        else:
            if self._restore_position_ms is not None:
                self._seek_restored_position()
            elif self.duration_us and self.position_us >= self.duration_us - 100_000:
                self.seek(0)
            self._player.set_state(Gst.State.PLAYING)
            self._begin_restored_session()
            self.playing = True
            self.stopped = False
            self._last_position_ms = self.position_us // 1000
            self._last_sample_time = time.monotonic()
        self._on_changed()

    def next(self) -> bool:
        if self.current_track is None:
            return False
        if len(self.queue) > 1:
            self.history.append(self.queue.pop(0))
            self.history = self.history[-500:]
            self._start_current()
            return True
        elif self.loop_status == "Playlist" and self._natural_queue:
            current = self.queue[0]
            self.history.append(current)
            others = [track for track in self._natural_queue if track.path != current.path]
            if self.shuffle_enabled:
                random.shuffle(others)
            self.queue = [current] + others + [current]
            self.queue.pop(0)
            self._start_current()
            return True
        return False

    def previous(self) -> None:
        if self.position_us > 3_000_000:
            self.seek(0)
            return
        if not self.history:
            return
        previous = self.history.pop()
        current = self.queue.pop(0) if self.queue else None
        self.queue.insert(0, previous)
        if current:
            self.queue.insert(1, current)
        self._start_current()

    def set_loop_status(self, value: str) -> None:
        if value in {"None", "Track", "Playlist"}:
            self.loop_status = value
            self._on_changed()

    def set_shuffle(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self.shuffle_enabled:
            return
        self.shuffle_enabled = enabled
        current = self.current_track
        if current:
            queued = self.queue[1:]
            played_paths = {track.path for track in self.history}
            if enabled:
                random.shuffle(queued)
            else:
                queued.sort(key=lambda item: self._natural_index(item.path))
            queued = [track for track in queued if track.path not in played_paths and track.path != current.path]
            self.queue = [current] + queued
        self._on_changed()

    def _natural_index(self, path: str) -> int:
        return next((index for index, item in enumerate(self._natural_queue) if item.path == path), 10**9)

    def play_next(self, tracks: list[Track] | Track) -> None:
        additions = [tracks] if isinstance(tracks, Track) else list(tracks)
        if not self.queue:
            self.queue = additions
            self._natural_queue = list(additions)
            self.history.clear()
            self.index = 0 if self.queue else -1
            self._start_current()
        else:
            existing = {track.path for track in self.queue[:1]}
            additions = [track for track in additions if track.path not in existing]
            paths = {track.path for track in additions}
            self.queue = self.queue[:1] + [track for track in self.queue[1:] if track.path not in paths]
            self.queue[1:1] = additions
            self._natural_queue.extend(track for track in additions
                                      if all(item.path != track.path for item in self._natural_queue))
            self._on_changed()

    def add_to_queue(self, tracks: list[Track] | Track) -> None:
        additions = [tracks] if isinstance(tracks, Track) else list(tracks)
        existing = {track.path for track in self.queue}
        additions = [track for track in additions if track.path not in existing]
        if not self.queue and additions:
            self.play_next(additions)
            return
        self.queue.extend(additions)
        self._natural_queue.extend(track for track in additions
                                  if all(item.path != track.path for item in self._natural_queue))
        self._on_changed()

    def move_queue_item(self, source: int, destination: int) -> bool:
        if not (1 <= source < len(self.queue) and 1 <= destination < len(self.queue)):
            return False
        track = self.queue.pop(source)
        self.queue.insert(destination, track)
        if any(item.path == track.path for item in self._natural_queue):
            natural_index = next(i for i, item in enumerate(self._natural_queue) if item.path == track.path)
            self._natural_queue.pop(natural_index)
            self._natural_queue.insert(min(destination, len(self._natural_queue)), track)
        self._on_changed()
        return True

    def remove_queue_item(self, position: int) -> bool:
        if not 1 <= position < len(self.queue):
            return False
        removed = self.queue.pop(position)
        if all(item.path != removed.path for item in self.queue):
            self._natural_queue = [item for item in self._natural_queue if item.path != removed.path]
        self._on_changed()
        return True

    def clear_upcoming(self) -> None:
        current = self.current_track
        self.queue = [current] if current else []
        self._natural_queue = list(self.queue)
        self.history.clear()
        self._on_changed()

    def stop(self) -> None:
        if self.current_track is not None:
            self._finish_session("stopped")
            self._player.set_state(Gst.State.READY)
        self.playing = False
        self.stopped = True
        self._on_changed()

    def seek(self, position_ms: int) -> None:
        self.record_progress()
        self._player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                                 max(0, int(position_ms)) * Gst.MSECOND)
        self._last_position_ms = max(0, int(position_ms))
        self._last_sample_time = time.monotonic()
        self._restore_position_ms = None

    def _seek_restored_position(self) -> None:
        if self._restore_position_ms is None:
            return
        self._player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                                 self._restore_position_ms * Gst.MSECOND)
        self._last_position_ms = self._restore_position_ms
        self._restore_position_ms = None

    def _on_bus_message(self, _bus, message) -> None:
        if message.type == Gst.MessageType.ASYNC_DONE and self._restore_position_ms is not None:
            self._seek_restored_position()
        elif message.type == Gst.MessageType.EOS:
            if self.loop_status == "Track" and self.current_track:
                self._start_current()
            elif not self.next():
                self._finish_session("finished")
                self.playing = False
                self.stopped = True
                self._player.set_state(Gst.State.READY)
                self._on_changed()
        elif message.type == Gst.MessageType.ERROR:
            error, _debug = message.parse_error()
            self.error = error.message
            self._finish_session("error")
            self._skip_unplayable(f"{self.error}; skipped this track.")

    def close(self) -> None:
        self._finish_session("app_closed")
        self._bus.remove_signal_watch()
        self._player.set_state(Gst.State.NULL)
