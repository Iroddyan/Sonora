# Sonora roadmap

This checklist records behavior in the active Python/GTK application. The earlier Qt implementation remains in Git history and does not count as current product behavior.

## GNOME platform pivot and foundation

- [x] Python + GTK 4 + libadwaita application entry point.
- [x] Adaptive `AdwNavigationSplitView` shell and native sidebar/header/player widgets.
- [x] System-following, dark, and light appearances.
- [x] Reuse the existing SQLite path and preserve earlier rows during schema migration.
- [x] Background scan for MP3/M4A, real tags, local artwork, progress, cancellation, and recoverable scan errors.
- [x] Real GStreamer playback with transport, seeking, volume, repeat, and shuffle service behavior.
- [x] Songs, Albums, and Artists views populated from the local index.
- [x] Local fuzzy search and MPRIS media controls.
- [x] Fedora setup notes, desktop entry, and initial AppStream metadata.
- [x] UX refinement pass: remove duplicated homepage heading, relocate folder import, widen responsive search, align card sizing, add structured song columns, and improve player slider affordances.

## Phase 0 — data foundation

- [x] Create normalized artist and album entities, per-track primary/featured credits, playback history, favorites, playlists, and metadata overrides.
- [x] Store file path, size, mtime, duration, first-seen time, play count, last-played time, and missing-file state per track.
- [x] Skip unchanged files using path + size + mtime; keep missing tracks in the database rather than deleting their records.
- [x] Split common artist separators while preferring multi-value tags; keep configurable separator exceptions in Settings.
- [x] Group albums by Unicode-normalized title and album artist; keep a deterministic source-folder tie-breaker.
- [x] Seed existing first-seen dates from file mtime where available and order recent additions by date, album, then track number.
- [x] Flag possible duplicates by normalized title and primary artist with durations within two seconds; never delete automatically.
- [x] Apply saved field overrides on rescans so local corrections persist.

## Phase 1 — pages and navigation

- [x] Album detail pages show artwork, title, linked album artist, year, song count, total duration, Play and Shuffle, and a disc/track-ordered list with a live playing marker.
- [x] Artist detail pages show their albums, songs, Play and Shuffle, and a separate `Appears on` list for featured credits.
- [x] Listen Now, Albums, and Artists collection cards open their detail pages; their separate play actions play real indexed tracks and remain visible for touch users.
- [x] Link artist names from song rows, album pages, and the player; link album names from song rows and the player.
- [x] Add Back, Alt+Left, and Escape navigation, restoring list scroll position, collection sort, and letter filter.
- [x] Show Albums and Artists as artwork grids with name/recent/year sorting, alphabet and `#` filters, and sorting that ignores a leading `The`.
- [x] Show grouped live Songs, Albums, and Artists search results; search ignores diacritics and `/` or Ctrl+F focuses search.

## Phase 2 — playback core

- [x] Clicking a song starts a queue from that song onward in the current list order, including the active Songs search filter.
- [x] Shuffle randomizes the remaining queue as a bag; Previous follows play history, and repeat supports Off, All, and One.
- [x] Add songs as Play next or Add to queue; reorder upcoming songs by drag and drop, remove individual entries, or clear upcoming songs.
- [x] Open a Now Playing detail view from the player artwork or title.
- [x] Persist volume, mute, queue, last track, position, shuffle, and repeat; resume the saved track paused.
- [x] Space toggles playback, Ctrl+Left/Right changes tracks, volume keys adjust level, and MPRIS exposes Linux media-key controls.
- [x] Keep player metadata at a fixed width, show seek-position tooltips, and toggle elapsed/remaining time.
- [x] Skip vanished or undecodable tracks with a notification instead of leaving playback stuck.
- [ ] Verify codec coverage and media-key handling across the user's chosen MP3/M4A library and GNOME session.
- [ ] Review keyboard focus, screen-reader labels, drag/drop discoverability, and compact-window behavior.

## Homepage data foundation

- [x] Preserve each track's first-seen timestamp across rescans; seed existing indexes from file mtime where available.
- [x] Persist playback sessions with real listened-time progress and track metadata snapshots.
- [x] Count a play after half the track or four minutes, whichever comes first; update play statistics as soon as the threshold is reached.
- [x] Recover unfinished sessions as interrupted after an unclean exit.
- [x] Build an artwork-led homepage with Jump back in, Recently played, Most played, Recently added, Rediscover, and Random albums; hide empty shelves.

## Phase 3 — make Listen Now earn its name

- [x] Record track sessions and listened time; qualify a play at half duration or four minutes, whichever comes first.
- [x] Replace the filler homepage shelves with history-based listening picks and real recently-added, most-played, rediscovery, and random-album sections.
- [x] Add favorite toggles to track rows and the player, plus a Favorites view.
- [x] Create, rename, populate, and delete playlists; reorder tracks by drag and drop.
- [x] Import and export M3U playlists, resolving local entries to indexed tracks and reporting skipped entries.
- [x] Add track and collection action menus for queue actions, playlist membership, navigation, file location, and metadata editing.
- [ ] Verify M3U compatibility with exported playlists from other players and accessibility of menu and drag actions.

## Later milestones

- [ ] RPM and Flatpak packaging with codec behavior documented for each runtime.
- [ ] Local lyrics display and synchronized lyrics.
- [ ] Safe metadata editing and optional online enrichment.

Nothing is considered done merely because a page exists. All visible playback and library actions must operate on real local tracks.
