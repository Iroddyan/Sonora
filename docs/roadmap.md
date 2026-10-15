# Sonora roadmap

This checklist records delivered behavior, not UI placeholders.

## Phase 0 — Repository and build foundation

- [x] CMake project and Qt 6 application entry point.
- [x] Minimal native QML application window.
- [x] Fedora build instructions.
- [x] Debug build and launch smoke test.

## Phase 1 — Design system and application shell

- [x] Shared dark/light semantic theme tokens.
- [x] Responsive sidebar and working navigation destinations.
- [x] Honest empty states for each destination.
- [x] Persistent player layout without inactive transport controls.
- [x] Selective translucent footer surface and user-selectable opaque fallback.
- [x] Functional dark/light appearance selection.
- [ ] Keyboard navigation and accessibility review across supported desktop environments.
- [ ] Validate reduced-motion and system transparency preferences.

## Phase 2 — Database and library scanning

- [x] SQLite schema version 1 and persistent library folders/tracks.
- [x] Folder selection, overlap protection, and safe local audio-file discovery.
- [x] TagLib metadata extraction in a cancellable background scan with progress and recoverable errors.
- [x] Real library model and Songs page with empty, loading, and error states.
- [x] Case-insensitive local search across title, artist, album, genre, and filename.
- [x] Remove a folder from the index without changing files on disk.

## Phase 3 — Real playback

- [ ] Qt Multimedia PlaybackService with actual local-file playback.
- [ ] Play/pause, previous/next, seeking, and volume controls.
- [ ] Handle end of track and report recoverable playback errors.

## Later phases

- [ ] Phase 4: album/artist views and local artwork.
- [ ] Phase 5: queue and playlists.
- [ ] Phase 6: Now Playing and local lyrics.
- [ ] Phase 7: metadata editing and optional online enrichment.
- [ ] Phase 8: accessibility/performance polish, desktop integration, RPM and Flatpak packaging.

No feature is marked complete solely because a destination or visual component exists.
