# Architecture

The active application uses the GNOME stack:

- `sonora/app.py` builds the `Adw.Application`, adaptive split view, native navigation, pages, dialogs, and player controls.
- `sonora/database.py` owns the local SQLite index and the fuzzy search query. It uses the existing `~/.local/share/Sonora/Sonora/library.sqlite` path and migrates the earlier artwork columns in place without discarding rows.
- `sonora/scanner.py` discovers MP3/M4A files, reads tags and embedded/neighbouring artwork with Mutagen, caches embedded covers, derives a supporting accent color, and writes scanned rows from a worker thread.
- `sonora/library.py` coordinates folder selection, scans, cancellation, and UI notifications.
- `sonora/playback.py` owns one GStreamer `playbin`, its ordered play sequence, transport state, repeat and shuffle behavior, seeking, and volume.
- `sonora/mpris.py` exports the MPRIS root and player interfaces over the session D-Bus.
- `sonora/models.py` holds immutable track records shared by the UI and services.
- `tests/` exercises schema migration, folder overlap, fuzzy matching, scanner metadata/artwork, and MPRIS registration.

GTK widgets are assembled in Python and styled primarily through libadwaita’s native components and system color scheme. The navigation split view collapses at narrow widths. Artwork accent color is confined to a subtle player detail; it does not recolor the whole application.

The scanner works off the UI thread and commits a completed folder scan as one transaction. Cancelling leaves the previous index intact. No metadata is written back to the audio files. Removing an indexed folder only removes rows from the database.

## Compatibility and migration

The SQLite file path and the previous schema are retained. The new application adds the artwork fields only when they are missing. The database is currently empty on the development machine, but the migration test inserts and verifies a pre-artwork track row. The former Qt source is preserved in Git history rather than in the active tree.

## Not implemented yet

There is no persistent queue, playlist editor, full album/artist detail screen, lyric view, metadata editor, or online enrichment. The current Albums and Artists pages are real grouped lists with working play actions. RPM and Flatpak manifests are also not complete.
