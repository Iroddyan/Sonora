# Sonora roadmap

This checklist records behavior in the active Python/GTK application. The Qt implementation remains temporarily as a migration reference and does not count as current product behavior.

## GNOME platform pivot and foundation

- [x] Python + GTK 4 + libadwaita application entry point.
- [x] Adaptive `AdwNavigationSplitView` shell and native sidebar/header/player widgets.
- [x] System-following, dark, and light appearances.
- [x] Reuse the existing SQLite path and preserve earlier rows during schema migration.
- [x] Background scan for MP3/M4A, real tags, local artwork, progress, cancellation, and recoverable scan errors.
- [x] Real GStreamer playback with transport, seeking, volume, repeat, and shuffle service behavior.
- [x] Songs, Albums, and Artists views populated from the local index.
- [x] Local fuzzy search and MPRIS media controls.
- [x] Fedora setup notes, desktop entry, and initial AppStream metadata.

## Next milestone — complete library workflows

- [ ] Album and artist detail views with ordered real track lists.
- [ ] Persistent library settings and remembered appearance choice.
- [ ] Test folder scan, cancellation, and playback against the user's MP3/M4A library after the user selects it.
- [ ] Verify seeking, repeat, shuffle, and MPRIS state changes with a real audio sink.
- [ ] Keyboard, screen-reader, and compact-window review on GNOME.

## Later milestones

- [ ] Persistent queue with reorder and removal controls.
- [ ] Playlist create, rename, track membership, reorder, and delete.
- [ ] Recently played/added sections backed by real playback history.
- [ ] RPM and Flatpak packaging with codec behavior documented for each runtime.
- [ ] Now Playing and local lyrics.
- [ ] Safe metadata editing and optional online enrichment.

Nothing is considered done merely because a page exists. All visible playback and library actions must operate on real local tracks.
