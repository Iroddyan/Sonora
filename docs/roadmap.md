# Sonora roadmap

This checklist records delivered behavior, not UI placeholders.

## Phase 0 — Repository and build foundation

- [x] CMake project and Qt 6 application entry point.
- [x] Minimal native QML application window.
- [x] Fedora build instructions.
- [x] Debug build and launch smoke test.

## Phase 1 — Design system and application shell (initial foundation)

- [x] Shared dark/light semantic theme tokens.
- [x] Responsive sidebar and working navigation destinations.
- [x] Honest empty states for each destination.
- [x] Persistent player layout with transport controls connected to real playback.
- [x] Selective translucent footer surface and user-selectable opaque fallback.
- [x] Functional dark/light appearance selection.
- [ ] Keyboard navigation and accessibility review across supported desktop environments.
- [ ] Reusable dialogs and broader button/card patterns as real workflows require them.
- [ ] Validate reduced-motion and system transparency preferences.

## Phase 2 — Database and library scanning

- [x] SQLite-backed persistent library folders/tracks (current schema version 2).
- [x] Folder selection, overlap protection, and safe local audio-file discovery.
- [x] TagLib metadata extraction in a cancellable background scan with progress and recoverable errors.
- [x] Real library model and Songs page with empty, loading, and error states.
- [x] Case-insensitive local search across title, artist, album, genre, and filename.
- [x] Remove a folder from the index without changing files on disk.

## Phase 3 — Real playback

- [x] Qt Multimedia PlaybackService with actual local-file playback.
- [x] Play/pause, previous/next, seeking, and volume controls.
- [x] Handle end of track and report recoverable playback errors.

## Phase 4 — Albums, artists, and local artwork

- [x] Album and artist groups derived from indexed album artist, artist, album, year, track, and disc metadata.
- [x] Responsive album and artist grids with detail views and real track listings.
- [x] Play and shuffle actions scoped to the selected album or artist.
- [x] Extract embedded artwork from MP3, FLAC, MP4, and Xiph-comment audio tags.
- [x] Resolve recognized neighboring cover files and use a designed missing-artwork placeholder.
- [x] Cache embedded artwork and calculate a supporting artwork accent during background scanning.
- [x] Migrate the library database to schema version 2 for artwork references.

## Later phases
- [ ] Phase 5: queue and playlists.
- [ ] Phase 6: Now Playing and local lyrics.
- [ ] Phase 7: metadata editing and optional online enrichment.
- [ ] Phase 8: accessibility/performance polish, desktop integration, RPM and Flatpak packaging.

No feature is marked complete solely because a destination or visual component exists.
