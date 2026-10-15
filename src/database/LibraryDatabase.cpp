#include "LibraryDatabase.h"

#include <QDateTime>
#include <QSqlError>
#include <QSqlQuery>
#include <QUuid>

namespace Sonora {

LibraryDatabase::LibraryDatabase()
    : m_connectionName(QStringLiteral("sonora-library-%1").arg(QUuid::createUuid().toString(QUuid::WithoutBraces)))
{
}

LibraryDatabase::~LibraryDatabase()
{
    if (m_database.isValid()) {
        m_database.close();
        m_database = {};
        QSqlDatabase::removeDatabase(m_connectionName);
    }
}

bool LibraryDatabase::open(const QString &filePath, QString *error)
{
    m_database = QSqlDatabase::addDatabase(QStringLiteral("QSQLITE"), m_connectionName);
    m_database.setDatabaseName(filePath);
    if (!m_database.open()) {
        if (error)
            *error = lastError(QStringLiteral("Open library database"));
        return false;
    }

    if (!execute(QStringLiteral("PRAGMA foreign_keys = ON"), error))
        return false;

    QSqlQuery versionQuery(m_database);
    if (!versionQuery.exec(QStringLiteral("PRAGMA user_version")) || !versionQuery.next()) {
        if (error)
            *error = lastError(QStringLiteral("Read database version"));
        return false;
    }
    const int version = versionQuery.value(0).toInt();
    if (version > 2) {
        if (error)
            *error = QStringLiteral("The library database was created by a newer Sonora version.");
        return false;
    }
    if (version == 2)
        return true;

    if (version == 0) {
        if (!m_database.transaction()) {
            if (error)
                *error = lastError(QStringLiteral("Start database migration"));
            return false;
        }
        const QStringList statements{
            QStringLiteral("CREATE TABLE library_folders (path TEXT PRIMARY KEY NOT NULL, added_at TEXT NOT NULL, last_scanned_at TEXT)"),
            QStringLiteral("CREATE TABLE tracks (id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE, source_root TEXT NOT NULL, title TEXT NOT NULL, artist TEXT NOT NULL DEFAULT '', album_artist TEXT NOT NULL DEFAULT '', album TEXT NOT NULL DEFAULT '', genre TEXT NOT NULL DEFAULT '', composer TEXT NOT NULL DEFAULT '', track_number INTEGER NOT NULL DEFAULT 0, disc_number INTEGER NOT NULL DEFAULT 0, year INTEGER NOT NULL DEFAULT 0, duration_ms INTEGER NOT NULL DEFAULT 0, size_bytes INTEGER NOT NULL DEFAULT 0, modified_ms INTEGER NOT NULL DEFAULT 0, last_scanned_at TEXT NOT NULL)"),
            QStringLiteral("CREATE INDEX tracks_title_idx ON tracks(title COLLATE NOCASE)"),
            QStringLiteral("CREATE INDEX tracks_artist_idx ON tracks(artist COLLATE NOCASE)"),
            QStringLiteral("CREATE INDEX tracks_album_idx ON tracks(album COLLATE NOCASE)"),
            QStringLiteral("PRAGMA user_version = 1")
        };
        for (const QString &sql : statements) {
            if (!execute(sql, error)) {
                m_database.rollback();
                return false;
            }
        }
        if (!m_database.commit()) {
            if (error)
                *error = lastError(QStringLiteral("Commit database migration"));
            return false;
        }
    }

    if (!m_database.transaction()) {
        if (error)
            *error = lastError(QStringLiteral("Start artwork database migration"));
        return false;
    }
    const QStringList artworkMigration{
        QStringLiteral("ALTER TABLE tracks ADD COLUMN artwork_path TEXT NOT NULL DEFAULT ''"),
        QStringLiteral("ALTER TABLE tracks ADD COLUMN artwork_accent TEXT NOT NULL DEFAULT ''"),
        QStringLiteral("PRAGMA user_version = 2")
    };
    for (const QString &sql : artworkMigration) {
        if (!execute(sql, error)) {
            m_database.rollback();
            return false;
        }
    }
    if (!m_database.commit()) {
        if (error)
            *error = lastError(QStringLiteral("Commit artwork database migration"));
        return false;
    }
    return true;
}

QVector<Track> LibraryDatabase::loadTracks(QString *error) const
{
    QVector<Track> tracks;
    QSqlQuery query(m_database);
    query.prepare(QStringLiteral("SELECT path, source_root, title, artist, album_artist, album, genre, composer, track_number, disc_number, year, duration_ms, size_bytes, modified_ms, artwork_path, artwork_accent FROM tracks ORDER BY artist COLLATE NOCASE, album COLLATE NOCASE, disc_number, track_number, title COLLATE NOCASE"));
    if (!query.exec()) {
        if (error)
            *error = lastError(QStringLiteral("Load tracks"));
        return tracks;
    }
    while (query.next()) {
        Track track;
        track.path = query.value(0).toString();
        track.sourceRoot = query.value(1).toString();
        track.title = query.value(2).toString();
        track.artist = query.value(3).toString();
        track.albumArtist = query.value(4).toString();
        track.album = query.value(5).toString();
        track.genre = query.value(6).toString();
        track.composer = query.value(7).toString();
        track.trackNumber = query.value(8).toInt();
        track.discNumber = query.value(9).toInt();
        track.year = query.value(10).toInt();
        track.durationMs = query.value(11).toLongLong();
        track.sizeBytes = query.value(12).toLongLong();
        track.modifiedMs = query.value(13).toLongLong();
        track.artworkPath = query.value(14).toString();
        track.artworkAccent = query.value(15).toString();
        tracks.push_back(std::move(track));
    }
    return tracks;
}

QStringList LibraryDatabase::loadFolders(QString *error) const
{
    QStringList folders;
    QSqlQuery query(m_database);
    query.prepare(QStringLiteral("SELECT path FROM library_folders ORDER BY path COLLATE NOCASE"));
    if (!query.exec()) {
        if (error)
            *error = lastError(QStringLiteral("Load library folders"));
        return folders;
    }
    while (query.next())
        folders.push_back(query.value(0).toString());
    return folders;
}

bool LibraryDatabase::addFolder(const QString &path, QString *error)
{
    QSqlQuery query(m_database);
    query.prepare(QStringLiteral("INSERT OR IGNORE INTO library_folders(path, added_at) VALUES(?, ?)"));
    query.addBindValue(path);
    query.addBindValue(QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs));
    if (!query.exec()) {
        if (error)
            *error = lastError(QStringLiteral("Add library folder"));
        return false;
    }
    return true;
}

bool LibraryDatabase::removeFolder(const QString &path, QString *error)
{
    if (!m_database.transaction()) {
        if (error)
            *error = lastError(QStringLiteral("Start folder removal"));
        return false;
    }
    QSqlQuery removeTracks(m_database);
    removeTracks.prepare(QStringLiteral("DELETE FROM tracks WHERE source_root = ?"));
    removeTracks.addBindValue(path);
    if (!removeTracks.exec()) {
        m_database.rollback();
        if (error)
            *error = lastError(QStringLiteral("Remove indexed tracks"));
        return false;
    }
    QSqlQuery removeFolder(m_database);
    removeFolder.prepare(QStringLiteral("DELETE FROM library_folders WHERE path = ?"));
    removeFolder.addBindValue(path);
    if (!removeFolder.exec() || !m_database.commit()) {
        m_database.rollback();
        if (error)
            *error = lastError(QStringLiteral("Remove library folder"));
        return false;
    }
    return true;
}

bool LibraryDatabase::applyScan(const ScanResult &result, QString *error)
{
    if (!m_database.transaction()) {
        if (error)
            *error = lastError(QStringLiteral("Start library scan update"));
        return false;
    }

    const QString scannedAt = QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs);
    for (const QString &root : result.successfulRoots) {
        QSqlQuery removePrevious(m_database);
        removePrevious.prepare(QStringLiteral("DELETE FROM tracks WHERE source_root = ?"));
        removePrevious.addBindValue(root);
        if (!removePrevious.exec()) {
            m_database.rollback();
            if (error)
                *error = lastError(QStringLiteral("Replace indexed folder contents"));
            return false;
        }

        QSqlQuery updateFolder(m_database);
        updateFolder.prepare(QStringLiteral("UPDATE library_folders SET last_scanned_at = ? WHERE path = ?"));
        updateFolder.addBindValue(scannedAt);
        updateFolder.addBindValue(root);
        if (!updateFolder.exec()) {
            m_database.rollback();
            if (error)
                *error = lastError(QStringLiteral("Update folder scan time"));
            return false;
        }
    }

    QSqlQuery insert(m_database);
    insert.prepare(QStringLiteral("INSERT INTO tracks(path, source_root, title, artist, album_artist, album, genre, composer, track_number, disc_number, year, duration_ms, size_bytes, modified_ms, artwork_path, artwork_accent, last_scanned_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(path) DO UPDATE SET source_root=excluded.source_root, title=excluded.title, artist=excluded.artist, album_artist=excluded.album_artist, album=excluded.album, genre=excluded.genre, composer=excluded.composer, track_number=excluded.track_number, disc_number=excluded.disc_number, year=excluded.year, duration_ms=excluded.duration_ms, size_bytes=excluded.size_bytes, modified_ms=excluded.modified_ms, artwork_path=excluded.artwork_path, artwork_accent=excluded.artwork_accent, last_scanned_at=excluded.last_scanned_at"));
    const auto nonNullText = [](const QString &value) {
        return value.isNull() ? QStringLiteral("") : value;
    };
    for (const Track &track : result.tracks) {
        insert.addBindValue(track.path);
        insert.addBindValue(track.sourceRoot);
        insert.addBindValue(nonNullText(track.title));
        insert.addBindValue(nonNullText(track.artist));
        insert.addBindValue(nonNullText(track.albumArtist));
        insert.addBindValue(nonNullText(track.album));
        insert.addBindValue(nonNullText(track.genre));
        insert.addBindValue(nonNullText(track.composer));
        insert.addBindValue(track.trackNumber);
        insert.addBindValue(track.discNumber);
        insert.addBindValue(track.year);
        insert.addBindValue(track.durationMs);
        insert.addBindValue(track.sizeBytes);
        insert.addBindValue(track.modifiedMs);
        insert.addBindValue(nonNullText(track.artworkPath));
        insert.addBindValue(nonNullText(track.artworkAccent));
        insert.addBindValue(scannedAt);
        if (!insert.exec()) {
            const QString queryError = insert.lastError().text();
            m_database.rollback();
            if (error)
                *error = QStringLiteral("Index track: %1").arg(queryError);
            return false;
        }
    }

    if (!m_database.commit()) {
        if (error)
            *error = lastError(QStringLiteral("Save library scan"));
        return false;
    }
    return true;
}

bool LibraryDatabase::execute(const QString &sql, QString *error) const
{
    QSqlQuery query(m_database);
    if (query.exec(sql))
        return true;
    if (error)
        *error = lastError(QStringLiteral("Run database statement"));
    return false;
}

QString LibraryDatabase::lastError(const QString &operation) const
{
    return QStringLiteral("%1: %2").arg(operation, m_database.lastError().text());
}

} // namespace Sonora
