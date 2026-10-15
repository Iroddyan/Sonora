# Sonora

Sonora is a local-first music player for GNOME, built with Python, GTK 4, and libadwaita. It scans local MP3 and M4A files, stores their index in SQLite, and plays them through GStreamer. No account or network connection is required.

The active application is now GNOME-native. The former Qt/C++ implementation has been removed from the working tree; its completed milestones remain recoverable in Git history. The new app retains the database location and compatible schema.

## Current GTK implementation

- Adaptive `AdwNavigationSplitView` shell with native GNOME sidebar, header bar, empty states, and a compact persistent player.
- First-run folder selection and cancellable background indexing for MP3 and M4A.
- Mutagen metadata reading, neighboring/embedded cover discovery, cached embedded art, and a restrained artwork accent.
- SQLite data stored at the existing Sonora path and kept compatible with the prior schema.
- Local Songs, Albums, and Artists lists, with real track/collection playback actions.
- GStreamer playback with previous/next, play/pause, seeking, and volume.
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

No sample tracks or fake library content are included. Playlists and a dedicated queue page remain future work and are intentionally absent from the sidebar.

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

The MPRIS registration test uses a session bus. The GTK smoke run creates no music entries and does not scan folders.

## Distribution

RPM and Flatpak remain the intended distribution formats. The desktop entry and AppStream metadata are in `data/`; package definitions and release automation are still pending.

## Project notes

- [Roadmap](docs/roadmap.md)
- [Architecture](docs/architecture.md)
- [Design system](docs/design-system.md)
- [Product blueprint](writing-block.md)
