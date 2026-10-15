# Architecture notes

The current application is a native Qt Quick shell with a local library workflow:

- `src/main.cpp` starts `QGuiApplication`, creates the library service, and exposes it to QML.
- `src/database/LibraryDatabase.*` owns the SQLite schema and transactional reads/writes.
- `src/scanner/ScannerWorker.*` discovers supported files and reads metadata off the UI thread.
- `src/library/LibraryService.*` coordinates folder management, scans, persistence, and the track model.
- `src/library/TrackListModel.*` supplies track roles and in-memory search to QML.
- `qml/Main.qml` owns the shared window layout and navigation state.
- `qml/pages/` contains the Songs and library settings workflows.
- `qml/Theme.qml` is the singleton for semantic appearance tokens.
- `qml/components/` contains reusable shell primitives.
- `CMakeLists.txt` defines the executable, embedded QML module, install target, and tests.

Scanning and metadata extraction run on a dedicated worker thread; all SQLite access remains on the service/UI thread. Playback is the next planned phase.
