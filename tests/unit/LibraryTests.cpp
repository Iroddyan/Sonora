#include "database/LibraryDatabase.h"
#include "library/LibraryService.h"
#include "library/TrackListModel.h"
#include "playback/PlaybackService.h"
#include "scanner/ScannerWorker.h"

#include <QFile>
#include <QFileInfo>
#include <QStandardPaths>
#include <QAudioDevice>
#include <QMediaDevices>
#include <QTemporaryDir>
#include <QDir>
#include <QtTest>

#include <atomic>
#include <memory>

using namespace Sonora;

class LibraryTests final : public QObject {
    Q_OBJECT

private slots:
    void modelFiltersAcrossMetadata()
    {
        TrackListModel model;
        Track first;
        first.path = QStringLiteral("/music/quiet-song.flac");
        first.title = QStringLiteral("Quiet Song");
        first.artist = QStringLiteral("Nina Example");
        first.album = QStringLiteral("Evening");
        Track second;
        second.path = QStringLiteral("/music/other-track.mp3");
        second.title = QStringLiteral("Other Track");
        second.artist = QStringLiteral("Sam Example");
        model.setTracks({first, second});

        QCOMPARE(model.count(), 2);
        QCOMPARE(model.rowCount(), 2);
        model.setSearchText(QStringLiteral("NINA"));
        QCOMPARE(model.rowCount(), 1);
        QCOMPARE(model.data(model.index(0), TrackListModel::TitleRole).toString(),
                 QStringLiteral("Quiet Song"));
        model.setSearchText(QStringLiteral("missing"));
        QCOMPARE(model.rowCount(), 0);
        QCOMPARE(model.count(), 2);
    }

    void databaseMigratesPersistsAndRemovesIndexOnly()
    {
        QTemporaryDir temporaryDirectory;
        QVERIFY(temporaryDirectory.isValid());
        const QString databasePath = temporaryDirectory.filePath(QStringLiteral("library.sqlite"));
        const QString folder = temporaryDirectory.filePath(QStringLiteral("Music"));
        QVERIFY(QDir().mkpath(folder));

        LibraryDatabase database;
        QString error;
        QVERIFY2(database.open(databasePath, &error), qPrintable(error));
        QCOMPARE(database.loadFolders(&error).size(), 0);
        QVERIFY2(database.addFolder(folder, &error), qPrintable(error));
        QCOMPARE(database.loadFolders(&error), QStringList{folder});

        Track track;
        track.path = folder + QStringLiteral("/track.flac");
        track.sourceRoot = folder;
        track.title = QStringLiteral("Test Track");
        track.artist = QStringLiteral("Test Artist");
        track.durationMs = 1234;
        Track secondTrack = track;
        secondTrack.path = folder + QStringLiteral("/second-track.mp3");
        secondTrack.title = QStringLiteral("ZZZ Secondary");
        ScanResult scan;
        scan.successfulRoots.push_back(folder);
        scan.tracks = {track, secondTrack};
        QVERIFY2(database.applyScan(scan, &error), qPrintable(error));

        const QVector<Track> loaded = database.loadTracks(&error);
        QCOMPARE(loaded.size(), 2);
        QCOMPARE(loaded.front().title, track.title);
        QCOMPARE(loaded.front().durationMs, track.durationMs);

        ScanResult inaccessible;
        inaccessible.errors.push_back(QStringLiteral("folder unavailable"));
        QVERIFY2(database.applyScan(inaccessible, &error), qPrintable(error));
        QCOMPARE(database.loadTracks(&error).size(), 2);

        QVERIFY2(database.removeFolder(folder, &error), qPrintable(error));
        QCOMPARE(database.loadFolders(&error).size(), 0);
        QCOMPARE(database.loadTracks(&error).size(), 0);
        QVERIFY(QFileInfo::exists(folder));
    }

    void scannerIgnoresUnsupportedFiles()
    {
        QTemporaryDir temporaryDirectory;
        QVERIFY(temporaryDirectory.isValid());
        QFile note(temporaryDirectory.filePath(QStringLiteral("notes.txt")));
        QVERIFY(note.open(QIODevice::WriteOnly));
        note.write("not an audio file");
        note.close();

        auto cancelled = std::make_shared<std::atomic_bool>(false);
        ScannerWorker worker({temporaryDirectory.path()}, cancelled);
        qRegisterMetaType<ScanResult>();
        QSignalSpy completed(&worker, &ScannerWorker::completed);
        worker.scan();
        QCOMPARE(completed.count(), 1);
        const ScanResult result = qvariant_cast<ScanResult>(completed.takeFirst().at(0));
        QCOMPARE(result.successfulRoots, QStringList{QFileInfo(temporaryDirectory.path()).canonicalFilePath()});
        QCOMPARE(result.scannedAudioFiles, 0);
        QVERIFY(result.tracks.isEmpty());
        QVERIFY(!result.cancelled);
    }

    void scannerHonorsCancellation()
    {
        QTemporaryDir temporaryDirectory;
        QVERIFY(temporaryDirectory.isValid());
        auto cancelled = std::make_shared<std::atomic_bool>(true);
        ScannerWorker worker({temporaryDirectory.path()}, cancelled);
        QSignalSpy completed(&worker, &ScannerWorker::completed);
        worker.scan();
        QCOMPARE(completed.count(), 1);
        const ScanResult result = qvariant_cast<ScanResult>(completed.takeFirst().at(0));
        QVERIFY(result.cancelled);
        QVERIFY(result.successfulRoots.isEmpty());
    }

    void libraryScansAndRemovesIndexWithoutDeletingFiles()
    {
        const QString systemSample = QStringLiteral("/usr/share/sounds/alsa/Front_Center.wav");
        if (!QFileInfo::exists(systemSample))
            QSKIP("Fedora ALSA test sound is not installed.");

        QTemporaryDir temporaryDirectory;
        QVERIFY(temporaryDirectory.isValid());
        const QString folder = temporaryDirectory.filePath(QStringLiteral("Music"));
        QVERIFY(QDir().mkpath(folder));
        const QString copiedSample = folder + QStringLiteral("/Front_Center.wav");
        QVERIFY(QFile::copy(systemSample, copiedSample));

        LibraryService library(temporaryDirectory.filePath(QStringLiteral("library.sqlite")));
        QVERIFY(library.ready());
        library.addFolder(folder);
        QTRY_VERIFY_WITH_TIMEOUT(!library.scanning(), 5000);
        QCOMPARE(library.tracks()->count(), 1);
        QVERIFY(library.errorMessage().isEmpty());

        library.removeFolder(QFileInfo(folder).canonicalFilePath());
        QCOMPARE(library.tracks()->count(), 0);
        QVERIFY(QFileInfo::exists(copiedSample));
    }

    void playbackStartsIdleAndClampsVolume()
    {
        TrackListModel model;
        PlaybackService playback(&model);
        QVERIFY(!playback.hasTrack());
        QVERIFY(!playback.playing());
        QCOMPARE(playback.position(), 0);
        QCOMPARE(playback.duration(), 0);
        playback.setVolume(1.5);
        QCOMPARE(playback.volume(), 1.0);
        playback.setVolume(-0.5);
        QCOMPARE(playback.volume(), 0.0);
        playback.togglePlayback();
        QVERIFY(!playback.hasTrack());
    }

    void playbackStartsARealLocalAudioFileWhenOutputIsAvailable()
    {
        const QString systemSample = QStringLiteral("/usr/share/sounds/alsa/Noise.wav");
        if (!QFileInfo::exists(systemSample))
            QSKIP("Fedora ALSA test sound is not installed.");
        if (QMediaDevices::defaultAudioOutput().isNull())
            QSKIP("No Qt audio output is available in this test session.");

        QTemporaryDir temporaryDirectory;
        QVERIFY(temporaryDirectory.isValid());
        const QString audioPath = temporaryDirectory.filePath(QStringLiteral("noise.wav"));
        QVERIFY(QFile::copy(systemSample, audioPath));
        Track track;
        track.path = QFileInfo(audioPath).canonicalFilePath();
        track.title = QStringLiteral("Noise");
        TrackListModel model;
        model.setTracks({track});
        PlaybackService playback(&model);
        playback.setVolume(0.0);
        QSignalSpy playingSpy(&playback, &PlaybackService::playingChanged);

        playback.playPath(track.path);
        QTRY_VERIFY_WITH_TIMEOUT(playingSpy.count() > 0, 5000);
        QVERIFY(playback.hasTrack());
        QCOMPARE(playback.currentPath(), track.path);
        QVERIFY(playback.errorMessage().isEmpty());
    }
};

QTEST_GUILESS_MAIN(LibraryTests)
#include "LibraryTests.moc"
