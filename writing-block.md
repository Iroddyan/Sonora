# SONORA
## Product Requirements, UX Design & Technical Implementation Plan

**Project type:** Native Linux desktop music player  
**Primary platform:** Fedora Linux / GNOME  
**Architecture:** Offline-first, local-library-centric  
**Primary languages:** C++ and QML  
**Framework:** Qt 6  
**Build system:** CMake  
**Product philosophy:** Local music first. Online enrichment by choice. Premium design without sacrificing usability.

---

# 1. Product Vision

Sonora is a modern desktop music player designed for people who maintain their own music libraries and want a beautiful, organized, reliable way to enjoy them.

It should combine:

- The polish and visual hierarchy associated with Apple Music.
- The customization and openness expected of Linux software.
- The speed and reliability of a native desktop application.
- A local-first music library that works without internet access.
- Optional online metadata enrichment, artist imagery, and synchronized lyrics.
- Thoughtful glassmorphism and floating elements that enhance the experience instead of making it harder to use.

Sonora is not a web music streaming service. It should not require an account, subscription, internet connection, or external service to play music stored on the user's computer.

## Core principles

1. **Local-first:** Music playback, browsing, search, playlists, queues, and core metadata must work offline.
2. **User ownership:** Users control their files and decide when metadata is changed.
3. **Beautiful but functional:** Every visual effect must serve a purpose.
4. **Native desktop experience:** Support Linux file paths, keyboard shortcuts, desktop integration, and predictable window behavior.
5. **No destructive surprises:** Never overwrite metadata or reorganize files without explicit permission.
6. **Incremental enrichment:** Online services improve the library but are never a requirement for using it.
7. **Respectful resource usage:** Avoid unnecessary background scanning, network requests, memory usage, and repeated artwork downloads.
8. **Accessible by default:** Provide readable contrast, keyboard navigation, scalable layouts, and reduced-transparency alternatives.

## Definition of success

A user should be able to install Sonora, select a music folder, let it scan their library, and begin playing music without creating an account or connecting to the internet.

After that, the user should be able to explore a visually rich library, manage playlists, edit metadata, retrieve optional artwork, and view synchronized lyrics without compromising their local music collection.

---

# 2. Technology Stack

Use a native Qt application with C++ for core logic and QML for the user interface.

## Core stack

| Component | Technology | Responsibility |
|---|---|---|
| Application framework | Qt 6 | Desktop application foundation |
| UI | Qt Quick and QML | Layouts, animation, interaction |
| UI components | Qt Quick Controls 2 | Inputs, menus, dialogs, buttons |
| Styling | Custom QML components and themes | Sonora's visual identity |
| Core language | Modern C++ | Library, playback, scanning, services |
| Build system | CMake | Compilation and dependency management |
| Playback | Qt Multimedia | Audio output and media playback |
| Metadata | TagLib | Reading and writing audio tags |
| Local database | SQLite via Qt SQL | Library index and application state |
| Networking | Qt Network | Optional metadata, artwork, and lyrics |
| Image handling | Qt image facilities | Artwork rendering and caching |
| Testing | Qt Test and CTest | Unit and integration tests |
| Packaging | RPM, Flatpak where practical, and documented source builds | Distribution |

Use the Qt 6 version available from the target distribution's supported development repositories. Check actual package availability before writing installation instructions.

**Important:** Qt Multimedia's supported codecs and behavior depend partly on the Linux multimedia backend and installed codecs. Verify playback on Fedora rather than assuming every format works automatically.

Use a modular architecture so that playback, metadata, artwork, lyrics, and storage can be replaced or improved independently.

## Suggested dependencies

- Qt 6 Core
- Qt 6 Gui
- Qt 6 Qml
- Qt 6 Quick
- Qt 6 Quick Controls 2
- Qt 6 Multimedia
- Qt 6 Network
- Qt 6 Sql
- TagLib
- SQLite
- Qt Test

Add other dependencies only when a concrete requirement justifies them.

Avoid introducing a web frontend, a local web server, Electron, or a large JavaScript runtime for the initial application.

---

# 3. Application Architecture

Organize Sonora into clear modules.

```text
sonora/
├── CMakeLists.txt
├── README.md
├── LICENSE
├── docs/
│   ├── architecture.md
│   ├── design-system.md
│   ├── development.md
│   └── roadmap.md
├── src/
│   ├── main.cpp
│   ├── app/
│   ├── database/
│   ├── library/
│   ├── scanner/
│   ├── playback/
│   ├── metadata/
│   ├── playlists/
│   ├── queue/
│   ├── lyrics/
│   ├── artwork/
│   ├── online/
│   └── settings/
├── qml/
│   ├── Main.qml
│   ├── components/
│   ├── pages/
│   ├── dialogs/
│   ├── overlays/
│   └── themes/
├── resources/
│   ├── icons/
│   ├── fonts/
│   └── placeholders/
└── tests/
    ├── unit/
    ├── integration/
    └── fixtures/
```

This is a proposed starting structure, not a requirement to create empty directories for every future feature. Add modules as they become necessary.

## Architectural rules

- Keep business logic out of QML.
- Keep database operations out of visual components.
- Expose C++ models and services to QML through deliberate, documented interfaces.
- Do not let individual pages independently implement music playback.
- Do not couple the core library to any particular online metadata provider.
- Do not run expensive scanning, tagging, or network work synchronously on the UI thread.
- Use asynchronous jobs with cancellation and meaningful progress reporting.
- Keep application state in appropriate models rather than duplicating it throughout the interface.
- Handle errors as normal application states, not as application crashes.

## Main services

### `LibraryService`

Provides library queries, album and artist groupings, filtering, sorting, and track retrieval.

### `ScannerService`

Discovers audio files, extracts metadata, detects changes, and updates the library index.

### `PlaybackService`

Owns the player, current track, playback state, position, duration, volume, repeat, and shuffle.

### `QueueService`

Maintains the upcoming playback queue and handles queue modifications.

### `PlaylistService`

Creates and manages playlists and their ordered track membership.

### `MetadataService`

Reads tags, proposes metadata corrections, and writes approved changes through TagLib.

### `ArtworkService`

Retrieves embedded artwork, resolves local artwork files, downloads optional remote artwork, and manages the artwork cache.

### `LyricsService`

Loads local lyrics, parses timed lyrics, retrieves optional online lyrics, and exposes synchronized lyric state.

### `OnlineMetadataService`

Coordinates optional online lookups through provider interfaces, without making network availability a dependency of the rest of the application.

### `SettingsService`

Stores preferences, library locations, appearance settings, and application behavior.

---

# 4. Visual Identity and Design System

Sonora should look premium, calm, and modern — not like a generic media player covered in gradients.

## Design direction

- Dark mode as the initial default.
- Light mode supported as a first-class alternative.
- Balanced glassmorphism.
- Selective floating surfaces.
- Artwork-driven accent colors.
- Rounded corners used consistently.
- Restrained motion and soft transitions.
- High-quality album art as a primary visual element.
- Clear hierarchy between navigation, library content, and playback controls.

Avoid excessive borders, excessive shadows, constant animations, unnecessary gradients, and glass applied to every surface.

## 4.1 Color system

Use semantic theme tokens rather than scattering hard-coded colors throughout QML.

Example starting tokens:

| Token | Dark-mode direction |
|---|---|
| `background` | Deep charcoal, near-black |
| `surface` | Slightly lighter charcoal |
| `surfaceElevated` | Raised dark surface |
| `surfaceGlass` | Translucent dark surface |
| `textPrimary` | Near-white |
| `textSecondary` | Muted neutral gray |
| `textDisabled` | Low-emphasis neutral gray |
| `accent` | Adaptive accent derived from artwork or theme |
| `borderSubtle` | Low-contrast neutral border |
| `success` | Accessible green |
| `warning` | Accessible amber |
| `error` | Accessible red |

Treat these as semantic roles, not final pixel-perfect color values.

## 4.2 Typography

Use a clean, readable sans-serif typeface available on Linux.

- Large titles for the current page and album details.
- Medium-weight section headings.
- Regular-weight body text.
- Smaller secondary metadata.
- Tabular numerals where appropriate for timestamps.
- Clear distinction between song title, artist, album, and duration.

Prefer system fonts or bundled fonts with appropriate licensing. Avoid depending on an unavailable proprietary font.

## 4.3 Spacing and geometry

Adopt a consistent spacing scale based on 4-pixel increments.

Suggested starting values:

- 4 px: compact icon-to-label spacing.
- 8 px: tight component spacing.
- 12 px: standard compact padding.
- 16 px: normal component padding.
- 24 px: section spacing.
- 32 px: major content separation.

Use a consistent radius system for cards, controls, overlays, and dialogs. Do not round every element indiscriminately.

## 4.4 Glassmorphism

Use translucent materials selectively.

Appropriate glass surfaces:

- Floating playback bar.
- Queue drawer.
- Lyrics overlay.
- Search overlay.
- Context menus and selected popovers.
- Certain transient controls over album artwork.

Glass surfaces should use a combination of translucent fills, subtle borders, and carefully controlled shadows. Blur should be used sparingly.

Do not rely on background blur alone to separate a panel from the content behind it. Use a sufficiently opaque tint and clear foreground contrast.

**Fallback behavior:** If transparency is disabled, unsupported, expensive, or inaccessible, render the same surface as a solid elevated panel.

## 4.5 Floating UI

Floating elements should feel intentional.

- The playback bar can float above the bottom edge of the application content.
- The queue can open as a right-side drawer.
- Lyrics can appear as a floating or expanded panel.
- Search can use a centered overlay or command-palette-like surface.
- Contextual actions can use lightweight popovers.

Floating elements must not obscure essential content permanently. Provide dismissal behavior, sensible stacking order, keyboard access, and predictable focus management.

## 4.6 Adaptive artwork colors

Extract a representative accent color from album artwork when it is available.

Use it for selected controls, subtle highlights, and certain Now Playing backgrounds.

Rules:

1. Never let an album's colors dictate the entire application's theme.
2. Keep text contrast accessible regardless of the source artwork.
3. Avoid rapid color changes during playback transitions.
4. Cache extracted colors.
5. Fall back to the theme accent when artwork is absent or unsuitable.
6. Do not perform expensive image analysis on the UI thread.

Artwork-derived colors should be a supporting visual feature, not a replacement for a coherent design system.

## 4.7 Motion

Use subtle animations for:

- Hover and pressed states.
- Panel opening and closing.
- Track transitions.
- Artwork expansion.
- Queue changes.
- Page navigation.
- Accent-color changes.

Keep animations short and interruptible. Avoid elaborate animation chains.

Respect reduced-motion preferences where practical, and ensure all core functionality works without animation.

---

# 5. Application Window and Navigation

The main application window should have three principal regions:

1. Left navigation sidebar.
2. Main content area.
3. Persistent playback area.

The layout must adapt to smaller windows without breaking core functionality.

## 5.1 Sidebar

Include:

- Sonora logo and application name.
- Listen Now.
- Songs.
- Albums.
- Artists.
- Playlists.
- Queue, when useful as a navigation destination.
- Settings near the bottom.

Library sections should appear only when meaningful, or remain available with helpful empty states when the library is empty.

The sidebar should support a compact presentation at narrow window widths. If icons are used without labels, provide accessible names and tooltips.

Use a clear active-navigation indicator without excessive visual emphasis.

## 5.2 Main content area

The main area should host navigable pages with a consistent title area, optional controls, and scrollable content.

Avoid recreating the sidebar or player on each page. They are shared application-level components.

## 5.3 Responsive behavior

On narrower windows:

- Reduce grid column count.
- Allow the sidebar to collapse.
- Hide nonessential secondary columns.
- Preserve the song title and essential playback controls.
- Allow Now Playing and queue views to become dedicated pages or larger overlays.

Do not assume every user has a high-resolution display.

---

# 6. First-Run Experience

The first launch should be simple and transparent.

## First-run sequence

1. Display a brief welcome screen introducing Sonora.
2. Explain that Sonora plays locally stored music and works offline.
3. Let the user select one or more music folders.
4. Offer an option to scan immediately or do it later.
5. Show scanning progress.
6. Display the library when scanning finishes.
7. Offer optional online enrichment separately from library setup.

Do not require sign-in, an account, or an internet connection.

The application should not automatically download metadata or modify tags simply because a folder was selected.

## Empty states

Provide useful empty states for:

- No library folders configured.
- A folder with no supported audio files.
- No albums.
- No artists.
- No playlists.
- No search results.
- Missing artwork.
- Unavailable online services.

Each empty state should explain what is happening and offer an appropriate next action.

---

# 7. Music Library and Scanning

The library is the foundation of Sonora.

## 7.1 Supported file discovery

Initially support common local audio formats, subject to playback backend and codec availability:

- MP3
- FLAC
- M4A/AAC
- Ogg Vorbis
- Opus
- WAV

Consider additional formats after validating metadata and playback behavior on supported Linux environments.

Do not assume that a file is playable merely because its extension is recognized. Handle unsupported codecs and malformed files gracefully.

## 7.2 Folder management

Allow users to:

- Add library folders.
- Remove folders from the library index.
- Rescan a folder.
- Rescan the entire library.
- Exclude folders from scanning.
- See the last successful scan time.
- Cancel an active scan.

Removing a folder from Sonora's index must not delete the actual folder or its music.

## 7.3 Scanning behavior

The scanner should:

1. Enumerate supported files.
2. Read available embedded metadata.
3. Identify the file using its canonical path and filesystem information.
4. Compare it with the existing database record.
5. Update changed records.
6. Detect files that no longer exist.
7. Report inaccessible files and recoverable errors.
8. Update library models without blocking playback.

Use file modification time and file size as inexpensive initial change indicators. Where necessary, offer a more thorough verification scan.

Do not hash every file on every startup. If stronger identity checks are needed, perform them selectively.

## 7.4 Metadata handling

Read, when available:

- Track title.
- Artist.
- Album artist.
- Album.
- Track number.
- Disc number.
- Year or release date.
- Genre.
- Composer.
- Track duration.
- Embedded artwork.
- Track-level identifiers, where available.

Missing metadata is normal. Do not invent values or silently replace blank fields with guessed information.

Use stable fallback labels in the UI, such as “Unknown Artist,” without writing those labels into the file's tags.

## 7.5 Duplicate handling

Different files may contain the same recording. Do not automatically remove or merge them.

Provide a future duplicate-finding feature that identifies possible duplicates and lets users review them.

---

# 8. Listen Now Page

Listen Now should be the primary landing page after the library has been indexed.

It should help users resume listening and discover music already in their collection.

## Suggested sections

### Recently Played

Show recently played tracks or albums, ordered by playback activity.

### Continue Listening

Provide a convenient way to resume the current track or recently active album when applicable.

### Recently Added

Show recently imported or discovered music.

### Albums

Display a curated selection of the user's own albums, not online recommendations.

### Quick Picks

Offer local-library tracks based on recent activity, playlists, or lightweight deterministic rules.

These sections must remain useful offline.

Do not introduce fake recommendations or present arbitrary selections as sophisticated AI recommendations.

If a section has insufficient data, hide it or display an appropriate empty state.

---

# 9. Songs Page

The Songs page provides a comprehensive view of the indexed track collection.

## Table columns

- Track number, where meaningful.
- Title.
- Artist.
- Album.
- Duration.
- Optional album artwork thumbnail.
- Optional genre or date.

Users should be able to:

- Sort by title, artist, album, duration, and date added.
- Search or filter the collection.
- Select one or multiple tracks.
- Play a track.
- Play selected tracks.
- Add tracks to the queue.
- Add tracks to a playlist.
- Reveal a file in the system file manager.
- Open a context menu for track actions.

Keep the primary columns readable. Allow less important columns to be hidden or omitted at smaller widths.

Use stable identifiers for track selection so sorting or refreshing the model does not unexpectedly select a different song.

## Context menu

Include relevant actions such as:

- Play.
- Play next.
- Add to queue.
- Add to playlist.
- Go to album.
- Go to artist.
- Edit metadata.
- Show file location.
- Remove from library.

Distinguish removing a track from Sonora's library from deleting the underlying file. File deletion, if ever implemented, must require a separate explicit confirmation.

---

# 10. Albums Page

The Albums page is the main visual browsing experience.

## Album grid

Display:

- Square cover artwork.
- Album title.
- Album artist.
- Optional year.
- A consistent card layout.

Use a responsive grid that adapts to the available content width.

Cards should have subtle hover effects, a clear selected or focused state, and contextual actions.

Avoid permanent borders around every album card.

## Album detail page

When an album is selected, display:

- Large album artwork.
- Album title.
- Album artist.
- Release year, when available.
- Track count.
- Total duration.
- Track listing.
- Play album.
- Shuffle album.
- Add album to queue.
- Add album to playlist.

The track listing should support track numbers, title, duration, and artist where appropriate.

For multi-disc albums, group tracks by disc and preserve the intended ordering.

Missing artwork should use a designed placeholder rather than a broken image.

---

# 11. Artists Page

The Artists page should help users navigate their local music collection.

## Artist grid or list

Show:

- Artist image, when available.
- Artist name.
- Optional track or album count.

The user should still be able to browse artists without downloading any images.

## Artist detail page

Display:

- Artist name.
- Artist image or placeholder.
- Albums in the library associated with that artist.
- Tracks associated with that artist.
- A play action.
- A shuffle action.
- An add-to-queue action.

Do not assume that artist names are globally unique. Treat online artist identification as a separate, optional enrichment task.

Avoid fabricated biographies, discographies, or external popularity metrics in the initial release.

---

# 12. Playback Engine

Playback is a core requirement, not a future placeholder.

## 12.1 PlaybackService responsibilities

The service should own:

- Current track.
- Playback state.
- Position.
- Duration.
- Volume.
- Mute state.
- Repeat mode.
- Shuffle mode.
- Track transition handling.
- Playback errors.
- End-of-track behavior.

Expose the required state to QML through properties and signals.

## 12.2 Essential controls

Implement:

- Play.
- Pause.
- Previous.
- Next.
- Seek.
- Volume.
- Mute.
- Shuffle.
- Repeat off.
- Repeat all.
- Repeat one.

The progress indicator must update smoothly without forcing unnecessary full-page UI refreshes.

Seeking should be accurate within the capabilities of the underlying backend.

## 12.3 Playback transitions

Handle:

- Track finished naturally.
- Next track requested manually.
- Previous track requested manually.
- Current track removed from the queue.
- Current file missing.
- Playback backend error.
- Application closing during playback.

The application should not crash if a track disappears or becomes unreadable.

## 12.4 Playback persistence

Where appropriate, restore the last session's playback context.

Persist the last track and position without necessarily auto-playing on launch. Make automatic playback behavior a user preference if implemented.

## 12.5 System integration

Plan for:

- Media keys.
- Desktop media controls.
- Track title and artist notifications through the supported Linux integration.
- MPRIS support for GNOME and other compatible desktop environments.

MPRIS is an important Linux integration goal, but it should be added after the core playback model is stable.

---

# 13. Persistent Floating Player

The playback bar is a signature part of Sonora's visual identity.

## Layout

Left:
- Small album artwork.
- Track title.
- Artist.

Center:
- Previous.
- Play/pause.
- Next.
- Progress bar.
- Current time and duration.

Right:
- Shuffle.
- Repeat.
- Queue.
- Lyrics.
- Volume.

The precise arrangement should adapt to available width.

## Visual treatment

Use a lightly translucent floating surface with restrained blur, a subtle outline, and a soft shadow.

Keep it visually distinct from the main content without looking detached from the application.

The player should not obscure the bottom rows of the library. Reserve content space for it or use an appropriate layout inset.

## Interaction

- Clicking the track information opens Now Playing.
- Clicking the queue button opens the queue drawer.
- Clicking the lyrics button opens lyrics when available.
- Seeking updates playback position.
- Volume can be adjusted with a slider and keyboard where practical.

Provide tooltips and accessible names for icon-only controls.

---

# 14. Queue Management

The queue should be a first-class feature.

## Queue view

Show:

- Currently playing track.
- Upcoming tracks.
- Track title.
- Artist.
- Optional artwork.
- Duration.

Allow users to:

- Remove an upcoming track.
- Clear upcoming tracks.
- Move a track up or down.
- Reorder tracks using drag and drop where practical.
- Play a selected queued track.
- Add songs, albums, or playlists.
- Save the queue as a playlist, if implemented.

## Queue rules

Keep the queue's behavior predictable.

- Distinguish the current track from upcoming tracks.
- Do not silently discard queued tracks when opening another page.
- Define what happens when a new album is played while a queue already exists.
- Define repeat and shuffle interactions.
- Persist the queue if appropriate, without assuming it must always be restored.

Shuffle should not repeatedly pick the same track when a reasonable alternative exists.

A repeat-one mode should repeat the current track without unexpectedly rebuilding the entire queue.

---

# 15. Now Playing Experience

Now Playing should be Sonora's most immersive screen.

## Layout

A flexible composition featuring:

- Prominent album artwork.
- Track title.
- Artist.
- Album.
- Playback controls.
- Progress and duration.
- Optional synchronized lyrics.
- Optional queue access.

Use a composition that can expand or contract based on the window size.

## Artwork backgrounds

An enlarged or blurred version of the album artwork can serve as a background, with a dark or light overlay that preserves readability.

Apply adaptive accents sparingly.

When artwork is missing, use a consistent background and placeholder.

## Interaction

Allow users to move between the artwork-focused view and lyrics view without interrupting playback.

The screen must remain usable when:

- The track has no artwork.
- The track has no lyrics.
- Online enrichment is disabled.
- The network is unavailable.
- Lyrics are available only as unsynchronized text.

---

# 16. Lyrics System

Lyrics are optional enrichment, not a playback dependency.

## Lyrics priority

Try sources in this order:

1. Embedded lyrics, when available and supported.
2. A local sidecar lyrics file.
3. Cached lyrics previously retrieved by the user.
4. An optional online provider, when enabled.

Support plain text lyrics and timed LRC lyrics.

A local `.lrc` file should be associated with the correct track using a sensible filename convention and, where necessary, additional verification.

## Synchronized lyrics

For timed lyrics:

- Parse timestamps.
- Match the current playback position to the active line.
- Highlight the current line.
- Scroll smoothly as the song progresses.
- Allow clicking a timed line to seek to its timestamp, where appropriate.

Do not update lyric highlighting at an unnecessarily high frequency.

## Unsynchronized lyrics

Display plain lyrics in a readable layout without pretending that they are synchronized.

## Missing lyrics

Show a helpful message and, if online retrieval is enabled, an action to search for lyrics.

Do not repeatedly contact online providers when lyrics are missing.

## Provider architecture

Implement a provider interface instead of coupling the UI to one service.

Provider behavior should account for:

- Network errors.
- Rate limits.
- Missing results.
- Matching confidence.
- Licensing and attribution requirements.
- Service availability changes.

Do not bypass authentication, paywalls, or access restrictions.

---

# 17. Metadata Editing and Automatic Tagging

Metadata editing should be powerful but conservative.

## 17.1 Manual editing

Provide a metadata editor for:

- Title.
- Artist.
- Album artist.
- Album.
- Track number.
- Disc number.
- Year or release date.
- Genre.
- Composer.

Allow editing a single track initially. Add batch editing after the basic workflow is reliable.

## 17.2 Automatic tagging workflow

The intended workflow:

1. The user selects a track or album.
2. Sonora reads the existing tags.
3. Sonora searches supported metadata sources if online enrichment is enabled.
4. Sonora presents proposed matches.
5. The user reviews the candidate metadata.
6. The user chooses which fields to apply.
7. Sonora previews the intended changes.
8. The user confirms the operation.
9. Sonora writes the approved metadata.
10. Sonora refreshes the library index.

Do not silently rewrite a music collection in the background.

## 17.3 Confidence and ambiguity

Display multiple candidates when a match is uncertain.

Use available information such as:

- Title.
- Artist.
- Album.
- Track duration.
- Track number.
- Album identifiers.

Do not automatically apply an ambiguous match simply because it is the first result.

## 17.4 Safe writes

Before modifying a file:

- Read the current metadata.
- Record which fields will change.
- Preserve unrelated tags where possible.
- Create a backup or recovery mechanism for supported operations.
- Report errors clearly.
- Refresh the library only after a successful write.

Writing tags can fail because of file permissions, unsupported formats, or corrupt files. Treat these as recoverable errors.

## 17.5 Automatic tagging modes

Provide clear settings:

- **Manual only:** No automatic metadata changes.
- **Suggest corrections:** Fetch candidates but require confirmation.
- **Confirm before writing:** Allow assisted application of proposed changes.

Default to the safest behavior.

---

# 18. Artwork System

Artwork is central to Sonora's presentation, so it needs a consistent resolution strategy.

## Artwork lookup priority

1. Embedded artwork in the audio file.
2. Recognized local artwork files.
3. Previously cached artwork.
4. Optional online artwork retrieval.

Common local filenames may include `cover.jpg`, `folder.jpg`, `front.png`, and similar conventions.

## Artwork behavior

- Display a placeholder when artwork is missing.
- Cache generated thumbnails.
- Avoid repeatedly decoding large images.
- Use stable artwork identifiers.
- Update affected album cards after artwork changes.
- Keep artwork retrieval separate from playback.
- Never replace embedded artwork without permission.

## Online artwork

Use supported services with appropriate terms and request limits.

The Cover Art Archive can be considered for release-linked artwork. Other services should be added only after checking their current APIs, access rules, and licensing conditions.

Do not scrape arbitrary websites as the default artwork strategy.

## Artist imagery

Artist imagery should be optional and cached locally.

If a reliable image cannot be found, display a designed placeholder.

Do not block the Artists page while waiting for remote images.

---

# 19. Search

Search should be fast and useful across the entire library.

## Search targets

- Tracks.
- Artists.
- Albums.
- Playlists.

Search should initially cover locally indexed data and work offline.

## Search behavior

- Filter results as the user types.
- Debounce expensive operations where necessary.
- Support keyboard navigation.
- Highlight matching text where practical.
- Display results grouped by type.
- Offer a clear action when no results are found.

## Search overlay

Use a lightweight floating overlay or command-palette-style surface.

Provide a keyboard shortcut to open search and a clear way to dismiss it.

Search should never require network access to return local results.

---

# 20. Playlists

Playlists are essential for a usable music player.

## Initial functionality

Users should be able to:

- Create a playlist.
- Name and rename playlists.
- Add tracks.
- Remove tracks.
- Reorder tracks.
- Play a playlist.
- Shuffle a playlist.
- Delete a playlist.
- Persist playlists across restarts.

Deleting a playlist must not delete its audio files.

## Storage

Use stable track references in the database. Handle playlist entries whose underlying files have disappeared.

Show missing entries clearly or offer to remove them from the playlist.

## Future functionality

Consider importing and exporting common playlist formats, such as M3U, after the core playlist workflow is stable.

---

# 21. Database Design

Use SQLite for persistent application state.

The database is an index and state store, not a replacement for the user's music files.

## Proposed tables

### `tracks`

Store:

- Internal ID.
- Canonical file path.
- Title.
- Artist.
- Album artist.
- Album.
- Track number.
- Disc number.
- Release date or year.
- Genre.
- Composer.
- Duration.
- File size.
- Modification time.
- Last scan time.
- Optional stable identifiers.
- Optional artwork reference.

### `albums`

Store:

- Internal ID.
- Album title.
- Album artist.
- Release date or year.
- Artwork reference.
- Optional external identifier.

### `artists`

Store:

- Internal ID.
- Artist name.
- Optional image reference.
- Optional external identifier.

### `library_folders`

Store:

- Folder path.
- Scan status.
- Last successful scan.
- Relevant scan settings.

### `playlists`

Store:

- Playlist ID.
- Name.
- Creation time.
- Modification time.

### `playlist_tracks`

Store:

- Playlist ID.
- Track ID.
- Position.

### `playback_history`

Store:

- Track ID.
- Last played time.
- Play count, if implemented.

### `artwork_cache`

Store:

- Artwork identifier.
- Cache path or resource reference.
- Source.
- Dimensions.
- Last access time.

### `lyrics_cache`

Store:

- Track association.
- Lyrics content or cache reference.
- Provider.
- Timing format.
- Retrieval time.

### `application_settings`

Store appropriate persistent settings if they are not better handled by Qt's settings facilities.

## Database rules

- Use parameterized SQL statements.
- Use transactions for multi-record changes.
- Add indexes for frequently queried fields.
- Use schema migrations.
- Handle corrupted or incompatible databases gracefully.
- Avoid storing the entire audio file in SQLite.
- Avoid storing duplicate copies of large artwork when file-based caching is more suitable.
- Define how library records are updated when a file is moved or renamed.

Do not treat artist and album names as globally unique identifiers. The same artist or album name may refer to different entities.

---

# 22. Settings

Create a dedicated Settings page.

## Appearance

- Dark mode.
- Light mode.
- Follow system preference, where supported.
- Glass intensity.
- Transparency toggle.
- Animation preference.
- Album-art adaptive accents.
- Interface scaling where appropriate.

## Library

- Music folder management.
- Automatic scanning behavior.
- Startup scan options.
- Excluded folders.
- Missing-file cleanup behavior.

## Playback

- Volume.
- Repeat and shuffle defaults.
- Playback restoration.
- Automatic next-track behavior.
- Crossfade, only if implemented and tested.

## Online services

- Enable or disable online enrichment.
- Enable or disable online lyrics.
- Enable or disable online artwork.
- Metadata provider selection where multiple providers exist.
- Cache management.

## Privacy

- Explain what information is sent to external providers.
- Avoid sending file contents unnecessarily.
- Do not transmit local file paths to online services.
- Use only the minimum metadata needed for a lookup.
- Allow online services to be disabled completely.

## Accessibility

- Reduced transparency.
- Reduced motion.
- Readability-related options where practical.

---

# 23. Error Handling and Reliability

Sonora should be robust when the user's library is imperfect.

Handle:

- Corrupt audio files.
- Unsupported codecs.
- Missing folders.
- Unreadable files.
- Invalid tags.
- Malformed artwork.
- Missing lyrics.
- Network timeouts.
- Rate limits.
- Metadata write failures.
- Database migration errors.
- Interrupted scans.
- Application restarts during an operation.

Show useful error messages with clear next steps.

Avoid exposing raw stack traces to normal users. Detailed diagnostics can be written to logs.

Use structured logging with appropriate severity levels. Avoid logging unnecessary personal file paths or metadata to remote services.

---

# 24. Accessibility and Linux Desktop Integration

Support:

- Keyboard navigation throughout the interface.
- Accessible labels for icon-only controls.
- Visible keyboard focus.
- Readable text contrast.
- Tooltips where helpful.
- Screen-reader-friendly control semantics.
- Reduced transparency.
- Reduced motion.
- Sensible window resizing.
- High-DPI displays.
- Desktop media keys.
- MPRIS integration.
- Standard file and folder dialogs.
- Appropriate application icon and desktop entry.

Do not make essential controls available only through hover interactions.

Test with GNOME first, then validate behavior on another supported Linux desktop environment.

---

# 25. Performance Targets

Treat these as design goals to validate, not unverified guarantees.

- The main window should appear promptly without waiting for a full library scan.
- Existing library data should be displayed before background scanning finishes.
- Search should feel immediate on typical personal music libraries.
- Playback should not stutter while scanning or downloading artwork.
- Artwork loading should not block scrolling.
- Queue operations should remain responsive.
- Database queries should be paginated or bounded where appropriate.
- Background operations should be cancellable when practical.
- Network activity should be minimal and purposeful.

Do not optimize prematurely with elaborate caching systems before measuring actual performance.

Start with a simple architecture, profile representative workloads, and optimize the genuine bottlenecks.

---

# 26. Testing Strategy

Testing should accompany implementation rather than being postponed until the end.

## Unit tests

Test:

- Metadata extraction.
- Tag writing and preservation.
- Filename and path normalization.
- LRC parsing.
- Track ordering.
- Queue behavior.
- Shuffle behavior.
- Repeat behavior.
- Playlist ordering.
- Database migrations.
- Search filtering.
- Artwork cache identifiers.

## Integration tests

Test:

- Adding and scanning a music folder.
- Rescanning changed files.
- Detecting missing files.
- Playing a track.
- Advancing to the next track.
- Creating a playlist.
- Restarting the app and restoring appropriate state.
- Applying metadata edits.
- Loading cached lyrics without a network connection.

## Manual testing

Use a small fixture library containing:

- MP3 with complete tags.
- FLAC with embedded artwork.
- M4A with incomplete tags.
- An audio file with no artwork.
- A track with local LRC lyrics.
- A track with plain text lyrics.
- A file with unusual characters in its path.
- A deliberately unreadable or invalid file.

Keep test fixtures small and legally redistributable.

Do not rely exclusively on online services for automated tests. Use mocks for provider behavior and separate manual tests for real integrations.

---

# 27. Development Roadmap

Build Sonora in the following phases.

## Phase 0 — Repository and build foundation

Deliverables:

- Project structure.
- CMake configuration.
- Qt 6 application entry point.
- Minimal QML window.
- Dependency checks.
- README with build instructions.
- A working debug build.

Acceptance criteria:

- The project compiles.
- The application launches.
- Build instructions work on the target Fedora environment.
- No fake functionality is presented as implemented.

## Phase 1 — Design system and application shell

Deliverables:

- Main window.
- Sidebar.
- Navigation.
- Theme tokens.
- Dark and light modes.
- Reusable buttons, cards, and dialogs.
- Responsive layout.
- Initial glass surfaces.
- Solid-surface fallback.

Acceptance criteria:

- All primary navigation destinations exist.
- Empty states look intentional.
- Resizing does not break the interface.
- Glass effects remain readable.
- The application is navigable by keyboard.

## Phase 2 — Database and library scanning

Deliverables:

- SQLite schema and migrations.
- Folder selection.
- Audio-file discovery.
- TagLib metadata extraction.
- Background scanner.
- Scan progress.
- Library models.
- Songs page.
- Basic search.

Acceptance criteria:

- A real music folder can be indexed.
- Track metadata appears correctly.
- Scanning does not block the UI.
- Reopening the application preserves the library.
- Offline operation works.

## Phase 3 — Real playback

Deliverables:

- PlaybackService.
- Qt Multimedia integration.
- Play/pause/previous/next.
- Seeking.
- Volume.
- Playback state.
- Track completion handling.
- Persistent player bar.

Acceptance criteria:

- Real local files play.
- Playback controls update the actual player.
- Unsupported files produce recoverable errors.
- Scanning and playback can operate concurrently.
- No network connection is required.

## Phase 4 — Albums, artists, and artwork

Deliverables:

- Album grouping.
- Album grid.
- Album detail page.
- Artist grouping.
- Artist detail page.
- Embedded artwork extraction.
- Local artwork discovery.
- Artwork cache.
- Adaptive accent colors.

Acceptance criteria:

- Albums and artists are derived from actual indexed metadata.
- Missing artwork has a proper placeholder.
- Album ordering and track ordering are consistent.
- Artwork loading does not freeze scrolling.

## Phase 5 — Queue and playlists

Deliverables:

- QueueService.
- Queue drawer.
- Queue reordering.
- Shuffle and repeat.
- Playlist creation and editing.
- Persistent playlists.

Acceptance criteria:

- Queue actions affect real playback.
- Queue order remains predictable.
- Playlists survive application restarts.
- Removing a track from a playlist does not delete its file.

## Phase 6 — Now Playing and lyrics

Deliverables:

- Expanded Now Playing view.
- Artwork-focused presentation.
- Local LRC parser.
- Plain-text lyrics support.
- Synchronized lyric highlighting.
- Lyrics panel.
- Optional online lyrics provider.

Acceptance criteria:

- Local lyrics work offline.
- Timed lyrics follow playback position.
- Missing lyrics do not disrupt playback.
- Online failure leaves the player fully usable.

## Phase 7 — Metadata editing and online enrichment

Deliverables:

- Manual metadata editor.
- TagLib write support.
- Candidate metadata search.
- Confirmation workflow.
- Optional online artwork.
- Optional artist imagery.
- Provider abstraction.
- Cache controls.

Acceptance criteria:

- Changes are previewed before writing.
- Unrelated tags are preserved where possible.
- Ambiguous matches are not silently applied.
- Disabling online services disables their network activity.
- Failed writes leave the application in a consistent state.

## Phase 8 — Polish and distribution

Deliverables:

- Keyboard shortcuts.
- MPRIS integration.
- Desktop media keys.
- Accessibility improvements.
- Performance profiling.
- Error handling review.
- Fedora packaging.
- Optional Flatpak packaging.
- Final documentation.

Acceptance criteria:

- The app can be installed and launched through a documented workflow.
- Playback works through the normal desktop integration.
- Offline behavior is verified.
- A clean build can be reproduced.
- Known limitations are documented.

---

# 28. Minimum Viable Product

The first genuinely useful release should contain:

1. A native application window.
2. A polished sidebar and page layout.
3. Folder selection.
4. Library scanning.
5. Metadata extraction.
6. Songs page.
7. Album grouping and album grid.
8. Real audio playback.
9. Persistent playback controls.
10. Queue management.
11. Basic playlists.
12. Local search.
13. Artwork display and placeholders.
14. SQLite persistence.
15. Graceful error handling.
16. A working offline workflow.

Do not delay the first working release until every animation, metadata provider, synchronized lyric feature, or advanced artist page is complete.

A reliable player with a polished interface is a better foundation than a gorgeous mockup with no real playback.

---

# 29. Explicit Non-Goals for the Initial Release

Do not implement these unless the core product is stable:

- Cloud music storage.
- User accounts.
- Subscription-based streaming.
- Social features.
- Remote music synchronization.
- AI-generated recommendations.
- Automatic destructive tagging.
- Automatic file reorganization.
- A built-in audio editor.
- An elaborate plugin ecosystem.
- Unverified online scraping.
- A custom audio engine without a demonstrated need.
- Complex visual effects that compromise accessibility or performance.

Keep the architecture extensible without building speculative systems in advance.

---

# 30. Codex Execution Rules

Codex should treat this document as the project's guiding specification.

## Working procedure

1. Inspect the repository before making changes.
2. Determine the installed Qt version and available development dependencies.
3. Identify the existing code, build configuration, and project constraints.
4. Write a concise implementation plan for the current phase.
5. Implement the smallest coherent feature set.
6. Compile the project.
7. Run relevant tests.
8. Fix regressions before proceeding.
9. Update the documentation.
10. Summarize what changed, what was tested, and what remains incomplete.

## Code quality

- Use clear, descriptive names.
- Keep functions and classes focused.
- Avoid giant QML files.
- Avoid unnecessary abstraction.
- Keep the UI responsive.
- Handle errors explicitly.
- Add tests for important behavior.
- Avoid unused dependencies.
- Do not hard-code credentials or API keys.
- Do not claim that untested functionality works.
- Do not replace a working feature with a mockup without explicit reason.

## Product integrity

- No mandatory online services.
- No mandatory account.
- No surprise metadata writes.
- No destructive file operations by default.
- No fake playback.
- No fabricated library entries.
- No fake progress indicators.
- No buttons that look functional but do nothing.
- No network dependency for ordinary local playback.
- No blocking the UI while scanning, tagging, or downloading artwork.

If a requested feature cannot yet be implemented correctly, expose it as a clearly identified incomplete feature or leave it out of the current phase.

## Progress reporting

Maintain a project checklist in `docs/roadmap.md`.

After each phase, report:

- Features implemented.
- Files added or changed.
- Dependencies introduced.
- Build result.
- Tests run and their results.
- Known issues.
- Next recommended milestone.

Do not mark a feature complete merely because its UI exists.

---

# 31. Initial Codex Task

Begin with Phase 0 and only the foundations of Phase 1.

First inspect the repository and environment. Then:

1. Establish the Qt 6 and CMake project.
2. Create the minimal application entry point.
3. Build a launchable QML window.
4. Implement Sonora's theme tokens and reusable visual primitives.
5. Build the sidebar and main-content shell.
6. Add navigation destinations with honest empty states.
7. Establish the persistent-player layout as a visual component, clearly separating its future playback integration from actual working playback.
8. Implement the first balanced-glass visual treatment and its opaque fallback.
9. Add basic documentation and a roadmap.
10. Compile and run the application, fixing build errors before reporting completion.

Do not implement the entire roadmap in one pass. Once the foundation is working, propose Phase 2 as the next task.

**The immediate objective is a launchable native Sonora application with a coherent design system and maintainable architecture — not a collection of disconnected mockup screens.**

---

# Final Product Standard

Sonora should feel like a thoughtfully designed Linux application: visually rich without being wasteful, familiar without being a clone, and powerful without making the user fight the interface.

Its signature experience is simple:

**Open Sonora. Browse your own music. Press play. Everything else is an enhancement.**
