#pragma once

#include "../library/Track.h"

#include <QSqlDatabase>
#include <QStringList>

namespace Sonora {

class LibraryDatabase final {
public:
    LibraryDatabase();
    ~LibraryDatabase();

    bool open(const QString &filePath, QString *error);
    QVector<Track> loadTracks(QString *error) const;
    QStringList loadFolders(QString *error) const;
    bool addFolder(const QString &path, QString *error);
    bool removeFolder(const QString &path, QString *error);
    bool applyScan(const ScanResult &result, QString *error);

private:
    bool execute(const QString &sql, QString *error) const;
    QString lastError(const QString &operation) const;

    QSqlDatabase m_database;
    QString m_connectionName;
};

} // namespace Sonora
