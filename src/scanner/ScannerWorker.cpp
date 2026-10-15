#include "ScannerWorker.h"

#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <QSet>
#include <utility>

#include <taglib/fileref.h>
#include <taglib/audioproperties.h>
#include <taglib/tpropertymap.h>
#include <taglib/tag.h>

namespace Sonora {
namespace {

QString fromTagLib(const TagLib::String &value)
{
    const std::string utf8 = value.to8Bit(true);
    return QString::fromUtf8(utf8.data(), static_cast<qsizetype>(utf8.size()));
}

QString firstProperty(const TagLib::PropertyMap &properties, const char *key)
{
    const auto values = properties[TagLib::String(key)];
    return values.isEmpty() ? QString{} : fromTagLib(values.front());
}

bool isSupportedAudioFile(const QFileInfo &fileInfo)
{
    static const QSet<QString> extensions{
        QStringLiteral("mp3"), QStringLiteral("flac"), QStringLiteral("m4a"),
        QStringLiteral("m4b"), QStringLiteral("aac"), QStringLiteral("ogg"),
        QStringLiteral("oga"), QStringLiteral("opus"), QStringLiteral("wav")
    };
    return extensions.contains(fileInfo.suffix().toLower());
}

Track readTrack(const QFileInfo &fileInfo, const QString &sourceRoot)
{
    Track track;
    track.path = fileInfo.canonicalFilePath();
    if (track.path.isEmpty())
        track.path = QDir::cleanPath(fileInfo.absoluteFilePath());
    track.sourceRoot = sourceRoot;
    track.sizeBytes = fileInfo.size();
    track.modifiedMs = fileInfo.lastModified().toMSecsSinceEpoch();

    const QByteArray fileName = QFile::encodeName(track.path);
    TagLib::FileRef file(fileName.constData(), true, TagLib::AudioProperties::Fast);
    if (file.isNull() || !file.tag())
        return {};

    const TagLib::Tag *tag = file.tag();
    track.title = fromTagLib(tag->title()).trimmed();
    if (track.title.isEmpty())
        track.title = fileInfo.completeBaseName();
    track.artist = fromTagLib(tag->artist()).trimmed();
    track.album = fromTagLib(tag->album()).trimmed();
    track.genre = fromTagLib(tag->genre()).trimmed();
    track.trackNumber = static_cast<int>(tag->track());
    track.year = static_cast<int>(tag->year());

    const TagLib::PropertyMap properties = file.file()->properties();
    track.albumArtist = firstProperty(properties, "ALBUMARTIST");
    if (track.albumArtist.isEmpty())
        track.albumArtist = firstProperty(properties, "ALBUM ARTIST");
    track.composer = firstProperty(properties, "COMPOSER");
    track.discNumber = firstProperty(properties, "DISCNUMBER").section(u'/', 0, 0).toInt();
    if (const TagLib::AudioProperties *audio = file.audioProperties()) {
        track.durationMs = audio->lengthInMilliseconds();
    }
    return track;
}

} // namespace

ScannerWorker::ScannerWorker(QStringList roots, std::shared_ptr<std::atomic_bool> cancelled)
    : m_roots(std::move(roots)), m_cancelled(std::move(cancelled))
{
}

void ScannerWorker::scan()
{
    ScanResult result;
    for (const QString &requestedRoot : std::as_const(m_roots)) {
        if (m_cancelled->load()) {
            result.cancelled = true;
            break;
        }

        const QFileInfo rootInfo(requestedRoot);
        const QString root = rootInfo.canonicalFilePath();
        if (!rootInfo.exists() || !rootInfo.isDir() || !rootInfo.isReadable() || root.isEmpty()) {
            result.errors.push_back(QStringLiteral("Cannot scan folder: %1").arg(requestedRoot));
            continue;
        }

        result.successfulRoots.push_back(root);
        QDirIterator iterator(root, QDir::Files | QDir::NoDotAndDotDot,
                              QDirIterator::Subdirectories);
        while (iterator.hasNext()) {
            if (m_cancelled->load()) {
                result.cancelled = true;
                break;
            }
            const QString path = iterator.next();
            const QFileInfo info = iterator.fileInfo();
            if (!isSupportedAudioFile(info))
                continue;
            ++result.scannedAudioFiles;
            if (!info.isReadable()) {
                result.errors.push_back(QStringLiteral("Cannot read audio file: %1").arg(path));
                continue;
            }
            Track track = readTrack(info, root);
            if (track.path.isEmpty()) {
                result.errors.push_back(QStringLiteral("Could not read audio metadata: %1").arg(path));
                continue;
            }
            result.tracks.push_back(std::move(track));
            if (result.scannedAudioFiles % 16 == 0)
                emit progressChanged(result.scannedAudioFiles);
        }
        if (result.cancelled)
            break;
    }
    emit progressChanged(result.scannedAudioFiles);
    emit completed(result);
}

} // namespace Sonora
