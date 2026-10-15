#include "LibraryService.h"

#include "../scanner/ScannerWorker.h"

#include <QDir>
#include <QFileInfo>
#include <QMetaObject>
#include <QThread>
#include <QTimer>

namespace Sonora {

LibraryService::LibraryService(const QString &databasePath, QObject *parent)
    : QObject(parent)
    , m_tracks(this)
{
    qRegisterMetaType<ScanResult>();
    qRegisterMetaType<QVector<Track>>();

    QString error;
    if (!m_database.open(databasePath, &error)) {
        setErrorMessage(error);
        setStatusMessage(QStringLiteral("Library database unavailable"));
        return;
    }
    m_ready = true;
    refreshModels();
    setStatusMessage(m_tracks.count() == 0
                         ? QStringLiteral("Add a music folder to build your library.")
                         : QStringLiteral("%1 tracks in your library.").arg(m_tracks.count()));
    if (!m_folders.isEmpty())
        QTimer::singleShot(0, this, &LibraryService::rescanAll);
}

LibraryService::~LibraryService()
{
    if (m_cancelled)
        m_cancelled->store(true);
    if (m_workerThread && m_workerThread->isRunning())
        m_workerThread->wait();
}

TrackListModel *LibraryService::tracks() { return &m_tracks; }
QStringList LibraryService::folders() const { return m_folders; }
bool LibraryService::scanning() const { return m_scanning; }
int LibraryService::scannedAudioFiles() const { return m_scannedAudioFiles; }
QString LibraryService::statusMessage() const { return m_statusMessage; }
QString LibraryService::errorMessage() const { return m_errorMessage; }
bool LibraryService::ready() const { return m_ready; }

void LibraryService::addFolder(const QString &path)
{
    if (!m_ready || m_scanning)
        return;
    const QFileInfo info(path);
    const QString canonical = info.canonicalFilePath();
    if (!info.exists() || !info.isDir() || !info.isReadable() || canonical.isEmpty()) {
        setErrorMessage(QStringLiteral("Choose a readable music folder."));
        return;
    }
    if (m_folders.contains(canonical)) {
        setStatusMessage(QStringLiteral("That folder is already in your library."));
        return;
    }
    if (hasOverlappingFolder(canonical)) {
        setErrorMessage(QStringLiteral("This folder overlaps a folder already in your library. Choose a parent folder or remove the existing entry first."));
        return;
    }

    QString error;
    if (!m_database.addFolder(canonical, &error)) {
        setErrorMessage(error);
        return;
    }
    m_folders.push_back(canonical);
    emit foldersChanged();
    setErrorMessage({});
    startScan({canonical});
}

void LibraryService::removeFolder(const QString &path)
{
    if (!m_ready || m_scanning)
        return;
    QString error;
    if (!m_database.removeFolder(path, &error)) {
        setErrorMessage(error);
        return;
    }
    m_folders.removeAll(path);
    emit foldersChanged();
    refreshModels();
    setErrorMessage({});
    setStatusMessage(QStringLiteral("Folder removed from Sonora. Your files were not changed."));
}

void LibraryService::rescanAll()
{
    if (!m_ready || m_scanning)
        return;
    if (m_folders.isEmpty()) {
        setStatusMessage(QStringLiteral("Add a music folder before scanning."));
        return;
    }
    startScan(m_folders);
}

void LibraryService::cancelScan()
{
    if (!m_scanning || !m_cancelled)
        return;
    m_cancelled->store(true);
    setStatusMessage(QStringLiteral("Stopping scan…"));
}

void LibraryService::startScan(const QStringList &roots)
{
    if (roots.isEmpty() || m_scanning)
        return;
    m_scanning = true;
    m_scannedAudioFiles = 0;
    setErrorMessage({});
    setStatusMessage(QStringLiteral("Starting library scan…"));
    emit scanningChanged();
    emit scanProgressChanged();

    m_cancelled = std::make_shared<std::atomic_bool>(false);
    auto *thread = new QThread(this);
    auto *worker = new ScannerWorker(roots, m_cancelled);
    worker->moveToThread(thread);
    m_workerThread = thread;
    connect(thread, &QThread::started, worker, &ScannerWorker::scan);
    connect(worker, &ScannerWorker::progressChanged, this, &LibraryService::onScanProgress,
            Qt::QueuedConnection);
    connect(worker, &ScannerWorker::completed, this, &LibraryService::onScanCompleted,
            Qt::QueuedConnection);
    connect(worker, &ScannerWorker::completed, thread, &QThread::quit, Qt::DirectConnection);
    connect(thread, &QThread::finished, worker, &QObject::deleteLater);
    connect(thread, &QThread::finished, thread, &QObject::deleteLater);
    thread->start();
}

void LibraryService::onScanProgress(int scannedAudioFiles)
{
    m_scannedAudioFiles = scannedAudioFiles;
    emit scanProgressChanged();
    setStatusMessage(QStringLiteral("Scanning audio files: %1 inspected…").arg(scannedAudioFiles));
}

void LibraryService::onScanCompleted(const ScanResult &result)
{
    m_scanning = false;
    emit scanningChanged();

    if (result.cancelled) {
        setStatusMessage(QStringLiteral("Scan canceled. No partial changes were saved."));
    } else {
        QString error;
        if (!m_database.applyScan(result, &error)) {
            setErrorMessage(error);
            setStatusMessage(QStringLiteral("Could not save scan results."));
        } else {
            refreshModels();
            setErrorMessage(result.errors.join(u'\n'));
            if (result.successfulRoots.isEmpty()) {
                setStatusMessage(QStringLiteral("No folders could be scanned. Existing indexed tracks were kept."));
            } else if (result.errors.isEmpty()) {
                setStatusMessage(QStringLiteral("Scan complete: %1 tracks indexed.").arg(m_tracks.count()));
            } else {
                setStatusMessage(QStringLiteral("Scan complete with %1 issue(s). Indexed %2 tracks.")
                                     .arg(result.errors.size())
                                     .arg(m_tracks.count()));
            }
        }
    }
}

void LibraryService::refreshModels()
{
    QString error;
    const QStringList folders = m_database.loadFolders(&error);
    if (!error.isEmpty())
        setErrorMessage(error);
    if (m_folders != folders) {
        m_folders = folders;
        emit foldersChanged();
    }
    const QVector<Track> tracks = m_database.loadTracks(&error);
    if (!error.isEmpty())
        setErrorMessage(error);
    m_tracks.setTracks(tracks);
}

void LibraryService::setStatusMessage(const QString &message)
{
    if (m_statusMessage == message)
        return;
    m_statusMessage = message;
    emit statusMessageChanged();
}

void LibraryService::setErrorMessage(const QString &message)
{
    if (m_errorMessage == message)
        return;
    m_errorMessage = message;
    emit errorMessageChanged();
}

bool LibraryService::hasOverlappingFolder(const QString &path) const
{
    const QString normalized = QDir::cleanPath(path);
    const auto containsPath = [](const QString &parent, const QString &child) {
        const QString prefix = parent.endsWith(QDir::separator())
                                   ? parent
                                   : parent + QDir::separator();
        return child.startsWith(prefix);
    };
    for (const QString &existingPath : m_folders) {
        const QString existing = QDir::cleanPath(existingPath);
        if (containsPath(existing, normalized) || containsPath(normalized, existing))
            return true;
    }
    return false;
}

} // namespace Sonora
