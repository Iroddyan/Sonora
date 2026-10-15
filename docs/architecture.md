# Architecture notes

The current application is a deliberately small Qt Quick shell:

- `src/main.cpp` starts `QGuiApplication` and loads the QML module.
- `qml/Main.qml` owns window layout and navigation state.
- `qml/Theme.qml` is the singleton for semantic appearance tokens.
- `qml/components/NavButton.qml` and `EmptyPage.qml` are reusable shell primitives.
- `CMakeLists.txt` defines the executable, embedded QML module, install target, and smoke test.

Business services are not introduced before their workflows exist. Planned services such as the library scanner, persistent database, and playback service should live in focused C++ modules and expose explicit models/interfaces to QML. File scanning, metadata extraction, and other long-running work must not block the UI thread.

The player area is a visual placeholder with explanatory copy only. It has no playback model or transport actions.
