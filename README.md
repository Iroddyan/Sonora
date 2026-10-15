# Sonora

Sonora is a local-first music player for GNOME, built with Python, GTK 4, and libadwaita. It scans local MP3 and M4A files, stores their index in SQLite, and plays them through GStreamer. No account or network connection is required.

The active application is now GNOME-native. The former Qt/C++ implementation has been removed from the working tree; its completed milestones remain recoverable in Git history. The new app retains the database location and compatible schema.

## Current GTK implementation

- Adaptive `AdwNavigationSplitView` shell with native GNOME sidebar, header bar, empty states, and a compact persistent player.
- First-run folder selection and cancellable background indexing for MP3 and M4A.
- Mutagen metadata reading, neighboring/embedded cover discovery, cached embedded art, and a restrained artwork accent.
- SQLite data stored at the existing Sonora path and kept compatible with the prior schema.
- Local Songs, Albums, and Artists lists, with real track/collection playback actions.
- Phase 1 collection workflows: album and artist detail pages, album track order/disc numbering, featured appearances, and linked album/artist navigation.
- Albums and Artists artwork grids with name/recent/year sorting and alphabet jump filters; collection cards open details with a distinct always-visible play action.
- Grouped live Songs/Albums/Artists search, accent-insensitive matching, `/` and Ctrl+F focus shortcuts, and Back/Alt+Left/Escape navigation with list position restoration.
- GStreamer playback with previous/next, play/pause, seeking, and volume.
- Phase 2 playback queue: selecting a song queues the visible list from that point, with shuffle-bag order, Previous history, and Repeat Off/All/One.
- Queue popover with Play next, Add to queue, drag reordering, per-track removal, and Clear upcoming actions.
- Now Playing detail page opens from player artwork or title; elapsed/remaining time toggles and seek hover shows the target time.
- Volume and mute controls, Space/Ctrl+Arrow/media volume shortcuts, Linux MPRIS control, and playback error notifications for skipped files.
- Playback state restores paused after restart, including the current/upcoming queue, position, volume, mute, shuffle, and repeat.
- Phase 3 history counts a play at half the track or four minutes, whichever comes first; the Listen Now shelves use real recent, frequent, rediscovery, and saved-session data.
- Track favorites appear as hearts in rows and the player, with a dedicated Favorites view.
- Playlists can be created, renamed, filled from track/collection menus, reordered by drag and drop, and deleted; M3U import/export is supported.
- Song and collection menus include queue actions, playlist actions, navigation, Show in Files, and metadata editing.
- First-seen timestamps preserved across scans, plus local playback history and measured listen time for future homepage personalization.
- Phase 0 library foundation: normalized artist and album identities, primary/featured artist credits, favorites and playlist storage, persistent metadata overrides, track play statistics, and duplicate-candidate flags.
- Incremental background scans keyed by file path, size, and modification time. Disappeared files are retained as unavailable instead of being deleted from the index.
- First-seen dates migrate from indexed file modification times. Common artist separators are split conservatively, with an editable exceptions list in Settings.
- Artwork-led Listen Now homepage with recently added tracks and real album, artist, and song shelves.
- Refined library layout with one clear page heading, a sidebar folder-import action, wider search, and consistently sized artwork cards with full-text tooltips.
- Songs view uses separate, ellipsized Title, Artist, Album, and Time columns so long metadata stays readable without wrapping.
- Player keeps elapsed and total time beside a taller seek control and exposes a persistent volume slider with a level-aware icon.
- Local-library fuzzy search.
- MPRIS D-Bus controls for desktop media keys and shell integration.
- Follow-system, dark, and light appearance selection through libadwaita.

No sample tracks or fake library content are included. M3U imports add only local tracks already indexed by Sonora and report entries that are missing or outside the library.

## Fedora setup

Install the runtime packages:

```sh
sudo dnf install python3 python3-gobject python3-mutagen gtk4 libadwaita gstreamer1 gstreamer1-plugins-base gstreamer1-plugins-good gstreamer1-plugins-bad-free gstreamer1-plugins-ugly-free gstreamer1-plugin-libav
```

Run directly from the repository:

```sh
python3 -m sonora
```

For an editable installation, create a venv that can see Fedora’s GTK bindings:

```sh
python3 -m venv --system-site-packages .venv
. .venv/bin/activate
python -m pip install -e .
sonora
```

Some audio codecs are provided by optional GStreamer plugins. The application reports playback errors when the host cannot decode a particular file; available codecs depend on the installed plugin set.

## Tests and smoke run

```sh
GTK_A11Y=none dbus-run-session -- python3 -m unittest discover -s tests -v
GTK_A11Y=none dbus-run-session -- python3 -m sonora --smoke-test
```

The MPRIS registration test uses a session bus. The GTK smoke run creates no music entries and does not scan folders. Queue transitions are covered by service tests; codec and media-key behavior still needs a pass against a user's actual library and GNOME session.

## Distribution

RPM and Flatpak remain the intended distribution formats. The desktop entry and AppStream metadata are in `data/`; package definitions and release automation are still pending.

## Project notes

- [Roadmap](docs/roadmap.md)
- [Architecture](docs/architecture.md)
- [Design system](docs/design-system.md)
- [Product blueprint](writing-block.md)
