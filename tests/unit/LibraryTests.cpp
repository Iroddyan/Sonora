#include "database/LibraryDatabase.h"
#include "library/LibraryService.h"
#include "library/TrackListModel.h"
#include "library/CollectionModels.h"
#include "playback/PlaybackService.h"
#include "scanner/ScannerWorker.h"
#include "artwork/ArtworkResolver.h"

#include <QFile>
#include <QFileInfo>
#include <QStandardPaths>
#include <QAudioDevice>
#include <QMediaDevices>
#include <QTemporaryDir>
#include <QDir>
#include <QImage>
#include <QSqlDatabase>
#include <QSqlQuery>
#include <QUuid>
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

    void albumAndArtistModelsGroupTracksInDiscOrder()
    {
        Track second;
        second.path = QStringLiteral("/music/second.flac");
        second.title = QStringLiteral("Second");
        second.artist = QStringLiteral("Guest");
        second.albumArtist = QStringLiteral("The Example Band");
        second.album = QStringLiteral("Greatest Hits");
        second.trackNumber = 2;
        second.durationMs = 2000;
        Track first = second;
        first.path = QStringLiteral("/music/first.flac");
        first.title = QStringLiteral("First");
        first.trackNumber = 1;
        first.year = 1998;
        first.artworkPath = QStringLiteral("/cache/cover.png");
        first.artworkAccent = QStringLiteral("#7255aa");
        Track discTwo = first;
        discTwo.path = QStringLiteral("/music/disc-two.flac");
        discTwo.title = QStringLiteral("Disc Two");
        discTwo.trackNumber = 1;
        discTwo.discNumber = 2;
        Track secondAlbum = first;
        secondAlbum.path = QStringLiteral("/music/another.flac");
        secondAlbum.album = QStringLiteral("Other Album");
        secondAlbum.artist = QStringLiteral("The Example Band");
        secondAlbum.albumArtist.clear();
        Track withoutAlbum = first;
        withoutAlbum.album.clear();

        AlbumListModel albums;
        albums.setTracks({second, secondAlbum, withoutAlbum, discTwo, first});
        QCOMPARE(albums.count(), 2);
        const QModelIndex albumIndex = albums.index(0);
        QCOMPARE(albums.data(albumIndex, AlbumListModel::TitleRole).toString(), QStringLiteral("Greatest Hits"));
        QCOMPARE(albums.data(albumIndex, AlbumListModel::ArtistRole).toString(), QStringLiteral("The Example Band"));
        QCOMPARE(albums.data(albumIndex, AlbumListModel::YearRole).toInt(), 1998);
        QCOMPARE(albums.data(albumIndex, AlbumListModel::TrackCountRole).toInt(), 3);
        QCOMPARE(albums.data(albumIndex, AlbumListModel::AccentRole).toString(), QStringLiteral("#7255aa"));
        const QVariantList albumTracks = albums.data(albumIndex, AlbumListModel::TracksRole).toList();
        QCOMPARE(albumTracks.size(), 3);
        QCOMPARE(albumTracks.at(0).toMap().value(QStringLiteral("title")).toString(), QStringLiteral("First"));
        QCOMPARE(albumTracks.at(1).toMap().value(QStringLiteral("title")).toString(), QStringLiteral("Second"));
        QCOMPARE(albumTracks.at(2).toMap().value(QStringLiteral("title")).toString(), QStringLiteral("Disc Two"));

        ArtistListModel artists;
        artists.setTracks({second, secondAlbum, withoutAlbum, discTwo, first});
        QCOMPARE(artists.count(), 1);
        QCOMPARE(artists.data(artists.index(0), ArtistListModel::NameRole).toString(), QStringLiteral("The Example Band"));
        QCOMPARE(artists.data(artists.index(0), ArtistListModel::TrackCountRole).toInt(), 5);
        QCOMPARE(artists.data(artists.index(0), ArtistListModel::AlbumCountRole).toInt(), 2);
    }

    void artworkResolverFindsLocalCoverAndExtractsAccent()
    {
        QTemporaryDir temporaryDirectory;
        QVERIFY(temporaryDirectory.isValid());
        const QString audioPath = temporaryDirectory.filePath(QStringLiteral("track.wav"));
        QFile audio(audioPath);
        QVERIFY(audio.open(QIODevice::WriteOnly));
        audio.write("not a real audio file");
        audio.close();

        QImage cover(32, 32, QImage::Format_RGB32);
        cover.fill(QColor(QStringLiteral("#5076a8")));
        const QString coverPath = temporaryDirectory.filePath(QStringLiteral("cover.png"));
        QVERIFY(cover.save(coverPath));

        const ResolvedArtwork artwork = ArtworkResolver::resolve(audioPath, temporaryDirectory.path());
        QCOMPARE(artwork.path, QFileInfo(coverPath).canonicalFilePath());
        QCOMPARE(artwork.accent, QStringLiteral("#5076a8"));
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
        track.artworkPath = QStringLiteral("/cache/album.png");
        track.artworkAccent = QStringLiteral("#556677");
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
        QCOMPARE(loaded.front().artworkPath, track.artworkPath);
        QCOMPARE(loaded.front().artworkAccent, track.artworkAccent);

        ScanResult inaccessible;
        inaccessible.errors.push_back(QStringLiteral("folder unavailable"));
        QVERIFY2(database.applyScan(inaccessible, &error), qPrintable(error));
        QCOMPARE(database.loadTracks(&error).size(), 2);

        QVERIFY2(database.removeFolder(folder, &error), qPrintable(error));
        QCOMPARE(database.loadFolders(&error).size(), 0);
        QCOMPARE(database.loadTracks(&error).size(), 0);
        QVERIFY(QFileInfo::exists(folder));
    }

    void databaseMigratesVersionOneToArtworkSchema()
    {
        QTemporaryDir temporaryDirectory;
        QVERIFY(temporaryDirectory.isValid());
        const QString databasePath = temporaryDirectory.filePath(QStringLiteral("legacy.sqlite"));
        const QString connection = QStringLiteral("legacy-%1").arg(QUuid::createUuid().toString(QUuid::WithoutBraces));
        {
            QSqlDatabase legacy = QSqlDatabase::addDatabase(QStringLiteral("QSQLITE"), connection);
            legacy.setDatabaseName(databasePath);
            QVERIFY(legacy.open());
            QSqlQuery query(legacy);
            QVERIFY(query.exec(QStringLiteral("CREATE TABLE library_folders (path TEXT PRIMARY KEY NOT NULL, added_at TEXT NOT NULL, last_scanned_at TEXT)")));
            QVERIFY(query.exec(QStringLiteral("CREATE TABLE tracks (id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE, source_root TEXT NOT NULL, title TEXT NOT NULL, artist TEXT NOT NULL DEFAULT '', album_artist TEXT NOT NULL DEFAULT '', album TEXT NOT NULL DEFAULT '', genre TEXT NOT NULL DEFAULT '', composer TEXT NOT NULL DEFAULT '', track_number INTEGER NOT NULL DEFAULT 0, disc_number INTEGER NOT NULL DEFAULT 0, year INTEGER NOT NULL DEFAULT 0, duration_ms INTEGER NOT NULL DEFAULT 0, size_bytes INTEGER NOT NULL DEFAULT 0, modified_ms INTEGER NOT NULL DEFAULT 0, last_scanned_at TEXT NOT NULL)")));
            QVERIFY(query.exec(QStringLiteral("INSERT INTO tracks(path, source_root, title, last_scanned_at) VALUES('/legacy/song.flac', '/legacy', 'Legacy Song', '2026-10-15T00:00:00Z')")));
            QVERIFY(query.exec(QStringLiteral("PRAGMA user_version = 1")));
            legacy.close();
        }
        QSqlDatabase::removeDatabase(connection);

        LibraryDatabase database;
        QString error;
        QVERIFY2(database.open(databasePath, &error), qPrintable(error));
        const QVector<Track> migratedTracks = database.loadTracks(&error);
        QCOMPARE(migratedTracks.size(), 1);
        QCOMPARE(migratedTracks.front().title, QStringLiteral("Legacy Song"));
        QVERIFY(migratedTracks.front().artworkPath.isEmpty());
        QVERIFY(error.isEmpty());
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
        QImage cover(24, 24, QImage::Format_RGB32);
        cover.fill(QColor(QStringLiteral("#5076a8")));
        const QString coverPath = folder + QStringLiteral("/cover.png");
        QVERIFY(cover.save(coverPath));

        LibraryService library(temporaryDirectory.filePath(QStringLiteral("library.sqlite")));
        QVERIFY(library.ready());
        library.addFolder(folder);
        QTRY_VERIFY_WITH_TIMEOUT(!library.scanning(), 5000);
        QCOMPARE(library.tracks()->count(), 1);
        QCOMPARE(library.tracks()->allTracks().front().artworkPath, QFileInfo(coverPath).canonicalFilePath());
        QCOMPARE(library.tracks()->allTracks().front().artworkAccent, QStringLiteral("#5076a8"));
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

    void playbackKeepsTheSelectedCollectionOrder()
    {
        const QString systemSample = QStringLiteral("/usr/share/sounds/alsa/Noise.wav");
        if (!QFileInfo::exists(systemSample))
            QSKIP("Fedora ALSA test sound is not installed.");
        QTemporaryDir temporaryDirectory;
        QVERIFY(temporaryDirectory.isValid());
        Track first;
        first.path = temporaryDirectory.filePath(QStringLiteral("first.wav"));
        first.title = QStringLiteral("First");
        QVERIFY(QFile::copy(systemSample, first.path));
        Track second;
        second.path = temporaryDirectory.filePath(QStringLiteral("second.wav"));
        second.title = QStringLiteral("Second");
        QVERIFY(QFile::copy(systemSample, second.path));
        Track third;
        third.path = temporaryDirectory.filePath(QStringLiteral("third.wav"));
        third.title = QStringLiteral("Third");
        QVERIFY(QFile::copy(systemSample, third.path));
        TrackListModel model;
        model.setTracks({first, second, third});
        PlaybackService playback(&model);

        playback.playPaths({third.path, first.path});
        QCOMPARE(playback.currentPath(), third.path);
        playback.next();
        QCOMPARE(playback.currentPath(), first.path);
        playback.previous();
        QCOMPARE(playback.currentPath(), third.path);
        playback.playPaths({first.path, second.path}, false, second.path);
        QCOMPARE(playback.currentPath(), second.path);
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
