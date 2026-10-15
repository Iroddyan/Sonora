# Sonora roadmap

This checklist records behavior in the active Python/GTK application. The earlier Qt implementation remains in Git history and does not count as current product behavior.

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
- [x] UX refinement pass: remove duplicated homepage heading, relocate folder import, widen responsive search, align card sizing, add structured song columns, and improve player slider affordances.

## Next milestone — complete library workflows

- [ ] Album and artist detail views with ordered real track lists.
- [ ] Persistent library settings and remembered appearance choice.
- [ ] Test folder scan, cancellation, and playback against the user's MP3/M4A library after the user selects it.
- [ ] Verify seeking, repeat, shuffle, and MPRIS state changes with a real audio sink.
- [ ] Keyboard, screen-reader, and compact-window review on GNOME.

## Homepage data foundation

- [x] Preserve each track's first-added timestamp across rescans; migrate older indexes using their last scan time as the best available baseline.
- [x] Persist playback sessions with real listened-time progress and track metadata snapshots.
- [x] Mark qualifying plays using a 30-second threshold, or half the duration for tracks shorter than one minute.
- [x] Recover unfinished sessions as interrupted after an unclean exit.
- [x] Build an artwork-led homepage from recently added tracks and the existing album/artist library data.
- [ ] Add playback-history-powered recently played and listening highlights after collecting real sessions.

## Later milestones

- [ ] Persistent queue with reorder and removal controls.
- [ ] Playlist create, rename, track membership, reorder, and delete.
- [ ] Recently played/added sections backed by real playback history.
- [ ] RPM and Flatpak packaging with codec behavior documented for each runtime.
- [ ] Now Playing and local lyrics.
- [ ] Safe metadata editing and optional online enrichment.

Nothing is considered done merely because a page exists. All visible playback and library actions must operate on real local tracks.
