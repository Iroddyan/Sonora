# Sonora

Sonora is a native Linux music player built with C++ and Qt 6/QML. It is being developed as an offline-first application for locally owned music. This repository currently contains the Phase 0 foundation and the initial Phase 1 application shell; it does not scan a library or play audio yet.

## Current state

- A native, resizable Qt Quick application with a navigable sidebar.
- Empty states for Listen Now, Songs, Albums, Artists, Playlists, and Queue. They do not contain invented library content.
- Dark and light theme tokens, a settings surface toggle, and an opaque surface fallback.
- A persistent player layout that explicitly identifies itself as a preview. It has no inactive transport controls.
- A CTest launch smoke test for the QML application shell.

## Build on Fedora

Install the build dependencies:

```sh
sudo dnf install cmake gcc-c++ qt6-qtbase-devel qt6-qtdeclarative-devel
```

Configure, compile, and run the smoke test:

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
ctest --test-dir build --output-on-failure
```

Launch the application with `./build/sonora`.

The project requests Qt 6.5 or newer. Fedora's Qt 6 development packages provide the CMake targets and QML/Quick modules used here. On other distributions, install the equivalent Qt 6 Core, Gui, Qml, and Quick development packages.

## Distribution direction

Flatpak and RPM are the planned Linux distribution formats. Packaging manifests and release workflows are intentionally deferred until the application has core library and playback behavior to package and validate. Sonora does not currently install a desktop entry or produce an RPM/Flatpak bundle.

## Project notes

- [Roadmap](docs/roadmap.md)
- [Architecture](docs/architecture.md)
- [Design system](docs/design-system.md)

## Integrity

Navigation and appearance settings work in this shell. Music import, library scanning, playback, playlists, artwork, and online services are not implemented yet. The player area is informational only.
