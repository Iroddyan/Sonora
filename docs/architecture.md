# Architecture

The active application uses the GNOME stack:

- `sonora/app.py` builds the `Adw.Application`, adaptive split view, native navigation, pages, dialogs, and player controls.
- `sonora/database.py` owns the local SQLite index, schema migrations, Unicode-normalized artist/album entities, track credits, favorites, playlists, metadata overrides, duplicate candidates, search, first-seen timestamps, and playback-history events. It uses the existing `~/.local/share/Sonora/Sonora/library.sqlite` path and migrates earlier indexes in place without discarding rows.
- `sonora/scanner.py` discovers MP3/M4A files, reads tags and embedded/neighbouring artwork with Mutagen, caches embedded covers, derives a supporting accent color, applies local metadata overrides, skips unchanged path/size/mtime records, and writes scanned rows from a worker thread. Files that disappear are marked missing and retained.
- `sonora/library.py` coordinates folder selection, scans, cancellation, and UI notifications.
- `sonora/playback.py` owns one GStreamer `playbin`, its ordered play sequence, transport state, repeat and shuffle behavior, seeking, volume, and measured listening progress callbacks.
- `sonora/mpris.py` exports the MPRIS root and player interfaces over the session D-Bus.
- `sonora/models.py` holds immutable track records shared by the UI and services.
- `tests/` exercises schema migration, folder overlap, fuzzy matching, scanner metadata/artwork, and MPRIS registration.

GTK widgets are assembled in Python and styled primarily through libadwaita’s native components and system color scheme. The navigation split view collapses at narrow widths. Artwork accent color is confined to a subtle player detail; it does not recolor the whole application.

The scanner works off the UI thread and commits a completed folder scan as one transaction. Cancelling leaves the previous index intact. No metadata is written back to the audio files. Removing a folder marks its indexed tracks unavailable and forgets the folder registration; it does not delete the track history or files.

Tracks keep a `first_seen_at` timestamp which scans never overwrite. Existing indexes seed it from stored file modification time where available, falling back to the previous first-added or scan timestamp. New tracks use their first indexing time. Playback sessions snapshot the track's path and display metadata, and accumulate forward GStreamer position progress while playing; paused time and detected seek jumps are excluded. Play counts and last-played times update when a play session starts. A play is marked qualified after 30 seconds, or half the track duration for tracks shorter than one minute. Incomplete sessions are closed as interrupted the next time Sonora starts.

Artist names are normalized with Unicode NFKC and case folding. Multi-value artist tags are preferred; combined strings split on common feature and collaboration separators. Settings stores editable exact-name exceptions such as “Tyler, The Creator”, “Earth, Wind & Fire”, and “AC/DC”. Album identity uses normalized album title plus normalized album artist, while source folder provides a deterministic tie-breaker. Possible duplicates are saved as candidate pairs when normalized title and primary artist match and duration differs by at most two seconds; the application never removes them automatically.

## Compatibility and migration

The SQLite file path and previous track rows are retained. Schema-v4 adds normalized artist/album entities, track credits, first-seen and play statistics, missing-file state, favorites, playlists, persistent metadata overrides, artist-split exceptions, and duplicate-candidate storage. Existing first-seen values are seeded from file mtime when it was stored, with older timestamp fields as fallback. The former Qt source is preserved in Git history rather than in the active tree.

## Not implemented yet

There is no persistent queue, playlist editor, full album/artist detail screen, lyric view, metadata editor, or online enrichment. The current Albums and Artists pages are real grouped lists with working play actions. RPM and Flatpak manifests are also not complete.
