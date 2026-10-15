# Architecture notes

The current application is a native Qt Quick player with a deliberately focused local-library scope:

- `src/main.cpp` starts `QGuiApplication`, creates the local library and playback services, and exposes them to the QML module.
- `src/database/LibraryDatabase.*` owns the SQLite schema and transactional reads/writes.
- `src/scanner/ScannerWorker.*` discovers supported files and reads metadata and artwork off the UI thread.
- `src/artwork/ArtworkResolver.*` extracts embedded covers, finds nearby cover files, creates cache images, and calculates artwork accent colors.
- `src/library/LibraryService.*` coordinates folder management, scans, persistence, and library models.
- `src/library/TrackListModel.*` supplies track roles and in-memory search to QML.
- `src/library/CollectionModels.*` groups indexed tracks into ordered album and artist models.
- `src/playback/PlaybackService.*` owns `QMediaPlayer`, `QAudioOutput`, and the active library track sequence.
- `qml/Main.qml` owns the shared window layout and navigation state.
- `qml/pages/` contains the Songs, Albums, Artists, and library settings workflows.
- `qml/Theme.qml` is the singleton for semantic appearance tokens.
- `qml/components/NavButton.qml` and `EmptyPage.qml` are reusable shell primitives.
- `CMakeLists.txt` defines the executable, embedded QML module, install target, shell smoke test, and library tests.

Scanning, metadata extraction, artwork decoding, and accent calculation run on a dedicated worker thread; all SQLite access remains on the service/UI thread. Embedded covers are cached under the application cache directory, while recognized nearby image files remain referenced in place. Playback is owned by one C++ service rather than individual QML pages. Collection playback uses a selected album or artist's ordered track paths; persistent queue management remains a later phase.
