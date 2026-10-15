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
- [x] Persistent player layout with an explicit Phase 3 note and no pretend controls.
- [x] Selective translucent footer surface and user-selectable opaque fallback.
- [x] Functional dark/light appearance selection.
- [ ] Keyboard navigation and accessibility review across supported desktop environments.
- [ ] Reusable dialogs and broader button/card patterns as real workflows require them.
- [ ] Validate reduced-motion and system transparency preferences.

## Phase 2 — Database and library scanning (recommended next)

- [ ] SQLite schema and migrations.
- [ ] Folder selection and safe local audio-file discovery.
- [ ] TagLib metadata extraction and background scan progress.
- [ ] Real library models and Songs page.
- [ ] Basic local search.

## Later phases

- [ ] Phase 3: real Qt Multimedia playback and working transport controls.
- [ ] Phase 4: album/artist views and local artwork.
- [ ] Phase 5: queue and playlists.
- [ ] Phase 6: Now Playing and local lyrics.
- [ ] Phase 7: metadata editing and optional online enrichment.
- [ ] Phase 8: accessibility/performance polish, desktop integration, RPM and Flatpak packaging.

No feature is marked complete solely because a destination or visual component exists.
