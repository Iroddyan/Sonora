# Architecture

The active application uses the GNOME stack:

- `sonora/app.py` builds the `Adw.Application`, adaptive split view, native navigation, pages, dialogs, and player controls.
- `sonora/database.py` owns the local SQLite index, schema migrations, fuzzy search, first-added timestamps, and playback-history events. It uses the existing `~/.local/share/Sonora/Sonora/library.sqlite` path and migrates earlier indexes in place without discarding rows.
- `sonora/scanner.py` discovers MP3/M4A files, reads tags and embedded/neighbouring artwork with Mutagen, caches embedded covers, derives a supporting accent color, and writes scanned rows from a worker thread.
- `sonora/library.py` coordinates folder selection, scans, cancellation, and UI notifications.
- `sonora/playback.py` owns one GStreamer `playbin`, its ordered play sequence, transport state, repeat and shuffle behavior, seeking, volume, and measured listening progress callbacks.
- `sonora/mpris.py` exports the MPRIS root and player interfaces over the session D-Bus.
- `sonora/models.py` holds immutable track records shared by the UI and services.
- `tests/` exercises schema migration, folder overlap, fuzzy matching, scanner metadata/artwork, and MPRIS registration.

GTK widgets are assembled in Python and styled primarily through libadwaita’s native components and system color scheme. The navigation split view collapses at narrow widths. Artwork accent color is confined to a subtle player detail; it does not recolor the whole application.

The scanner works off the UI thread and commits a completed folder scan as one transaction. Cancelling leaves the previous index intact. No metadata is written back to the audio files. Removing an indexed folder only removes rows from the database.

Tracks keep a `first_added_at` timestamp which scans never overwrite. Existing schema-v2 indexes are backfilled from their last recorded scan timestamp because older versions did not preserve the original add date. Playback sessions snapshot the track's path and display metadata, and accumulate forward GStreamer position progress while playing; paused time and detected seek jumps are excluded. A play is marked qualified after 30 seconds, or half the track duration for tracks shorter than one minute. Incomplete sessions are closed as interrupted the next time Sonora starts.

## Compatibility and migration

The SQLite file path and previous track rows are retained. Schema-v3 adds the first-added timestamp and playback-history table. Existing track rows are backfilled from their previous `last_scanned_at` value because the older schema did not keep an original add date. The former Qt source is preserved in Git history rather than in the active tree.

## Not implemented yet

There is no persistent queue, playlist editor, full album/artist detail screen, lyric view, metadata editor, or online enrichment. The current Albums and Artists pages are real grouped lists with working play actions. RPM and Flatpak manifests are also not complete.
