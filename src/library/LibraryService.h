#pragma once

#include "TrackListModel.h"
#include "CollectionModels.h"
#include "../database/LibraryDatabase.h"

#include <QObject>
#include <QPointer>
#include <QStringList>
#include <atomic>
#include <memory>

class QThread;

namespace Sonora {

class LibraryService final : public QObject {
    Q_OBJECT
    Q_PROPERTY(Sonora::TrackListModel *tracks READ tracks CONSTANT)
    Q_PROPERTY(Sonora::AlbumListModel *albums READ albums CONSTANT)
    Q_PROPERTY(Sonora::ArtistListModel *artists READ artists CONSTANT)
    Q_PROPERTY(QStringList folders READ folders NOTIFY foldersChanged)
    Q_PROPERTY(bool scanning READ scanning NOTIFY scanningChanged)
    Q_PROPERTY(int scannedAudioFiles READ scannedAudioFiles NOTIFY scanProgressChanged)
    Q_PROPERTY(QString statusMessage READ statusMessage NOTIFY statusMessageChanged)
    Q_PROPERTY(QString errorMessage READ errorMessage NOTIFY errorMessageChanged)
    Q_PROPERTY(bool ready READ ready CONSTANT)

public:
    explicit LibraryService(const QString &databasePath, QObject *parent = nullptr);
    ~LibraryService() override;

    TrackListModel *tracks();
    AlbumListModel *albums();
    ArtistListModel *artists();
    QStringList folders() const;
    bool scanning() const;
    int scannedAudioFiles() const;
    QString statusMessage() const;
    QString errorMessage() const;
    bool ready() const;

    Q_INVOKABLE void addFolder(const QString &path);
    Q_INVOKABLE void removeFolder(const QString &path);
    Q_INVOKABLE void rescanAll();
    Q_INVOKABLE void cancelScan();

signals:
    void foldersChanged();
    void scanningChanged();
    void scanProgressChanged();
    void statusMessageChanged();
    void errorMessageChanged();

private:
    void startScan(const QStringList &roots);
    void onScanProgress(int scannedAudioFiles);
    void onScanCompleted(const ScanResult &result);
    void refreshModels();
    void setStatusMessage(const QString &message);
    void setErrorMessage(const QString &message);
    bool hasOverlappingFolder(const QString &path) const;

    LibraryDatabase m_database;
    TrackListModel m_tracks;
    AlbumListModel m_albums;
    ArtistListModel m_artists;
    QStringList m_folders;
    QString m_statusMessage;
    QString m_errorMessage;
    int m_scannedAudioFiles = 0;
    bool m_scanning = false;
    bool m_ready = false;
    QPointer<QThread> m_workerThread;
    std::shared_ptr<std::atomic_bool> m_cancelled;
};

} // namespace Sonora
