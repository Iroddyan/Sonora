# Sonora

Sonora is a native Linux music player built with C++ and Qt 6/QML, focused on locally owned music. The current build includes the Phase 0 foundation, initial Phase 1 shell, and Phase 2 local library indexing. Playback controls are planned for Phase 3.

## Current state

- Native Qt Quick window with navigable sidebar, dark/light tokens, and opaque surface fallback.
- SQLite-backed library folders and track metadata.
- Background scanner with TagLib metadata extraction, progress, cancellation, and recoverable errors.
- Songs page with local search, folder management, and scan status.
- Removing a folder clears its index records and leaves files untouched.
- Honest empty states; no invented music data.

## Build on Fedora

Install the build dependencies:

```sh
sudo dnf install cmake gcc-c++ qt6-qtbase-devel qt6-qtdeclarative-devel taglib-devel
```

Configure, compile, and run the smoke and library tests:

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
ctest --test-dir build --output-on-failure
```

Launch with `./build/sonora`. The project requests Qt 6.5 or newer.

## Distribution direction

Flatpak and RPM are planned. Packaging manifests and release workflows are scheduled for Phase 8.

## Project notes

- [Roadmap](docs/roadmap.md)
- [Architecture](docs/architecture.md)
- [Design system](docs/design-system.md)

## Current limitations

Playback, album and artist grouping, queue, playlists, lyrics, metadata editing, online enrichment, desktop integration, and RPM/Flatpak packaging remain planned.
