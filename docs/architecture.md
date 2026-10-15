# Architecture notes

The current application is a native Qt Quick player with a deliberately focused local-library scope:

- `src/main.cpp` starts `QGuiApplication`, creates the local library and playback services, and exposes them to the QML module.
- `src/database/LibraryDatabase.*` owns the SQLite schema and transactional reads/writes.
- `src/scanner/ScannerWorker.*` discovers supported files and reads metadata off the UI thread.
- `src/library/LibraryService.*` coordinates folder management, scans, persistence, and the track model.
- `src/library/TrackListModel.*` supplies track roles and in-memory search to QML.
- `src/playback/PlaybackService.*` owns `QMediaPlayer`, `QAudioOutput`, and the active library track sequence.
- `qml/Main.qml` owns the shared window layout and navigation state.
- `qml/pages/` contains the Songs and library settings workflows.
- `qml/Theme.qml` is the singleton for semantic appearance tokens.
- `qml/components/NavButton.qml` and `EmptyPage.qml` are reusable shell primitives.
- `CMakeLists.txt` defines the executable, embedded QML module, install target, and smoke test.

Scanning and metadata extraction run on a dedicated worker thread; all SQLite access remains on the service/UI thread. Playback is owned by one C++ service rather than individual QML pages. Future queue and playlist services can build on the library model without taking ownership of audio output.
