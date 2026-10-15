#pragma once

#include <QMetaType>
#include <QString>
#include <QVector>

namespace Sonora {

struct Track {
    QString path;
    QString sourceRoot;
    QString title;
    QString artist;
    QString albumArtist;
    QString album;
    QString genre;
    QString composer;
    QString artworkPath;
    QString artworkAccent;
    int trackNumber = 0;
    int discNumber = 0;
    int year = 0;
    qint64 durationMs = 0;
    qint64 sizeBytes = 0;
    qint64 modifiedMs = 0;
};

struct ScanResult {
    QVector<Track> tracks;
    QStringList successfulRoots;
    QStringList errors;
    int scannedAudioFiles = 0;
    bool cancelled = false;
};

} // namespace Sonora

Q_DECLARE_METATYPE(Sonora::Track)
Q_DECLARE_METATYPE(QVector<Sonora::Track>)
Q_DECLARE_METATYPE(Sonora::ScanResult)
