# Sonora

Sonora is a native Linux music player built with C++ and Qt 6/QML. It is an offline-first application for locally owned music. The current build includes the Phase 0 foundation, Phase 1 shell, Phase 2 library indexing, Phase 3 playback, and Phase 4 album, artist, and artwork browsing.

## Current state

- A native, resizable Qt Quick application with a navigable sidebar.
- Empty states for Listen Now, Songs, Albums, Artists, Playlists, and Queue. They do not contain invented library content.
- SQLite-backed folders and track metadata, indexed by a cancellable background scanner using TagLib.
- A real Songs page with metadata search, folder management, scan status, and error reporting.
- Local audio playback through Qt Multimedia with play/pause, previous/next, seeking, and volume controls.
- Album and artist browsing, detail pages, collection playback, and shuffle using indexed tags.
- Embedded and nearby local cover art, cached away from music files with artwork-based accent colors.
- Dark and light theme tokens, a settings surface toggle, and an opaque surface fallback.
- Warm dark and parchment light palettes, a clearer sidebar, more useful empty states, and a bundled Material Icons font.
- A persistent player bar that only shows transport controls when a real track is loaded.
- CTest coverage for the shell, database migrations, metadata grouping, local cover discovery, scanning, and collection playback order.

## Build on Fedora

Install the build dependencies:

```sh
sudo dnf install cmake gcc-c++ qt6-qtbase-devel qt6-qtdeclarative-devel qt6-qtmultimedia-devel taglib-devel
```

Configure, compile, and run the shell and library tests:

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
ctest --test-dir build --output-on-failure
```

Launch the application with `./build/sonora`.

The project requests Qt 6.5 or newer. Fedora's Qt 6 development packages provide the CMake targets and QML/Quick modules used here. On other distributions, install the equivalent Qt 6 Core, Gui, Qml, and Quick development packages.

The Material Icons font is distributed under Apache License 2.0. Its license is included in the source tree and installed under `share/licenses/sonora`.

## Distribution direction

Flatpak and RPM are the planned Linux distribution formats. Packaging manifests and release workflows are planned for Phase 8. Sonora does not currently install a desktop entry or produce an RPM/Flatpak bundle.

## Project notes

- [Roadmap](docs/roadmap.md)
- [Architecture](docs/architecture.md)
- [Design system](docs/design-system.md)

## Current limitations

Library indexing, album/artist browsing, artwork, and playback work with local files. Managed queue, playlists, lyrics, metadata editing, online enrichment, artist portraits, and RPM/Flatpak packaging are still planned. Playback codec support depends on the multimedia codecs available on the host.
