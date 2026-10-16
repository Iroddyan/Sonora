from __future__ import annotations

import threading
import os
from pathlib import Path

import gi
gi.require_version("GLib", "2.0")
from gi.repository import Gio, GLib

from sonora.database import LibraryDatabase
from sonora.models import Track
from sonora.scanner import FolderScanner


class LibraryService:
    def __init__(self, on_changed=None, on_progress=None):
        self.database = LibraryDatabase()
        self.scanner = FolderScanner(self.database)
        self._on_changed = on_changed or (lambda: None)
        self._on_progress = on_progress or (lambda _current, _total: None)
        self.tracks: list[Track] = self.database.tracks()
        self.folders: list[str] = self.database.folders()
        self.status = ""
        self.error = ""
        self.scan_progress = (0, 0)
        self._scan_folders: list[str] = []
        self._scan_lock = threading.Lock()
        self._watch_enabled = self.database.setting("watch_folders", "true") == "true"
        self._monitors = {}
        self._watch_timers = {}
        self._refresh_monitors()
        if self.folders and self.database.needs_reindex():
            GLib.idle_add(self.scan_all)

    @property
    def scanning(self) -> bool:
        return self.scanner.running or bool(self._scan_folders)

    @property
    def watch_enabled(self) -> bool:
        return self._watch_enabled

    def refresh(self) -> None:
        self.tracks = self.database.tracks()
        self.folders = self.database.folders()
        self._on_changed()

    def add_folder(self, path: str) -> bool:
        if not self.database.add_folder(path):
            self.error = "That folder is already indexed or overlaps an indexed folder."
            self._on_changed()
            return False
        self.folders = self.database.folders()
        self.error = ""
        self._on_changed()
        self._scan_folders.append(str(Path(path).resolve()))
        if len(self._scan_folders) == 1:
            self._start_next_folder()
        return True

    def scan_all(self) -> None:
        if self.scanning:
            return
        self._scan_folders = list(self.folders)
        self.error = ""
        self._start_next_folder()

    def _start_next_folder(self) -> None:
        if not self._scan_folders:
            self.status = "Library is up to date."
            self.refresh()
            return
        folder = self._scan_folders[0]
        self.status = f"Scanning {folder}…"
        self._on_changed()

        def progress(current, total):
            GLib.idle_add(self._update_progress, current, total)

        def complete(count, error):
            GLib.idle_add(self._folder_complete, folder, count, error)

        if not self.scanner.start(folder, progress, complete):
            self.error = "A scan is already running."
            self._scan_folders.clear()
            self._on_changed()

    def _update_progress(self, current: int, total: int) -> bool:
        self.scan_progress = (current, total)
        if total:
            self.status = f"Scanning files: {current} of {total}"
        self._on_progress(current, total)
        return GLib.SOURCE_REMOVE

    def _folder_complete(self, folder: str, count: int, error: str | None) -> bool:
        if self._scan_folders and self._scan_folders[0] == folder:
            self._scan_folders.pop(0)
        if error and error != "Scan cancelled":
            self.error = error
        elif error == "Scan cancelled":
            self.status = "Scan cancelled."
            self._scan_folders.clear()
        else:
            self.status = f"Indexed {count} audio files in {Path(folder).name}."
        self.refresh()
        self._refresh_monitors()
        if self._scan_folders:
            GLib.timeout_add(50, self._start_next_folder)
        return GLib.SOURCE_REMOVE

    def cancel_scan(self) -> None:
        if self.scanning:
            self.scanner.cancel()

    def set_watch_changes(self, enabled: bool) -> None:
        self._watch_enabled = bool(enabled)
        self.database.set_setting("watch_folders", "true" if enabled else "false")
        if not enabled:
            for timer in self._watch_timers.values():
                GLib.source_remove(timer)
            self._watch_timers.clear()
        self._refresh_monitors()

    def _refresh_monitors(self) -> None:
        for monitor in self._monitors.values():
            monitor.cancel()
        self._monitors.clear()
        if not self._watch_enabled:
            return
        for root in self.folders:
            for directory, subdirectories, _files in os.walk(root):
                subdirectories[:] = [name for name in subdirectories if not name.startswith(".")]
                try:
                    file = Gio.File.new_for_path(directory)
                    monitor = file.monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, None)
                    monitor.connect("changed", self._directory_changed, root)
                    self._monitors[directory] = monitor
                except GLib.Error:
                    continue

    def _directory_changed(self, _monitor, file, _other, event, root) -> None:
        interesting = {
            Gio.FileMonitorEvent.CREATED, Gio.FileMonitorEvent.DELETED,
            Gio.FileMonitorEvent.CHANGES_DONE_HINT, Gio.FileMonitorEvent.MOVED,
            Gio.FileMonitorEvent.RENAMED, Gio.FileMonitorEvent.MOVED_IN,
            Gio.FileMonitorEvent.MOVED_OUT,
        }
        if event not in interesting:
            return
        if file:
            suffix = Path(file.get_basename() or "").suffix.casefold()
            if suffix not in {"", ".mp3", ".m4a", ".jpg", ".jpeg", ".png", ".webp"}:
                return
            if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
                self.database.mark_folder_for_reindex(root)
        previous = self._watch_timers.pop(root, None)
        if previous:
            GLib.source_remove(previous)
        self._watch_timers[root] = GLib.timeout_add_seconds(2, self._watch_rescan, root)

    def _watch_rescan(self, root: str) -> bool:
        self._watch_timers.pop(root, None)
        if self.scanner.running and self._scan_folders and self._scan_folders[0] == root:
            if root not in self._scan_folders[1:]:
                self._scan_folders.append(root)
        elif root not in self._scan_folders:
            self._scan_folders.append(root)
        if not self.scanner.running and len(self._scan_folders) == 1:
            self._start_next_folder()
        return GLib.SOURCE_REMOVE

    def rebuild_index(self) -> None:
        if self.scanning:
            self.error = "Wait for the current scan to finish before rebuilding the index."
            self._on_changed()
            return
        self.database.mark_for_reindex()
        self.scan_all()

    def remove_folder(self, path: str) -> None:
        self.database.remove_folder(path)
        self.status = "Folder removed from Sonora's index. Music files were left in place."
        self.refresh()

    def search(self, query: str) -> list[Track]:
        return self.database.search(query)
