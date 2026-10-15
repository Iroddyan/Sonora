#include "ArtworkResolver.h"

#include <QBuffer>
#include <QColor>
#include <QCryptographicHash>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QImage>
#include <QImageReader>
#include <QSaveFile>

#include <taglib/attachedpictureframe.h>
#include <taglib/flacfile.h>
#include <taglib/fileref.h>
#include <taglib/id3v2tag.h>
#include <taglib/mp4coverart.h>
#include <taglib/mp4file.h>
#include <taglib/mpegfile.h>
#include <taglib/xiphcomment.h>

namespace Sonora {
namespace {

QByteArray embeddedImage(TagLib::File *file)
{
    if (!file)
        return {};

    if (auto *mpeg = dynamic_cast<TagLib::MPEG::File *>(file)) {
        if (TagLib::ID3v2::Tag *tag = mpeg->ID3v2Tag(false)) {
            const auto frames = tag->frameList(TagLib::ByteVector("APIC"));
            for (TagLib::ID3v2::Frame *frame : frames) {
                if (auto *picture = dynamic_cast<TagLib::ID3v2::AttachedPictureFrame *>(frame)) {
                    const TagLib::ByteVector bytes = picture->picture();
                    return QByteArray(bytes.data(), static_cast<qsizetype>(bytes.size()));
                }
            }
        }
    }
    if (auto *flac = dynamic_cast<TagLib::FLAC::File *>(file)) {
        const auto pictures = flac->pictureList();
        if (!pictures.isEmpty()) {
            const TagLib::ByteVector bytes = pictures.front()->data();
            return QByteArray(bytes.data(), static_cast<qsizetype>(bytes.size()));
        }
    }
    if (auto *mp4 = dynamic_cast<TagLib::MP4::File *>(file)) {
        if (mp4->tag()->item("covr").isValid()) {
            const auto covers = mp4->tag()->item("covr").toCoverArtList();
            if (!covers.isEmpty()) {
                const TagLib::ByteVector bytes = covers.front().data();
                return QByteArray(bytes.data(), static_cast<qsizetype>(bytes.size()));
            }
        }
    }
    if (auto *xiph = dynamic_cast<TagLib::Ogg::XiphComment *>(file->tag())) {
        const auto pictures = xiph->pictureList();
        if (!pictures.isEmpty()) {
            const TagLib::ByteVector bytes = pictures.front()->data();
            return QByteArray(bytes.data(), static_cast<qsizetype>(bytes.size()));
        }
    }
    return {};
}

QImage decodeImage(const QByteArray &bytes)
{
    QBuffer buffer;
    buffer.setData(bytes);
    if (!buffer.open(QIODevice::ReadOnly))
        return {};
    QImageReader reader(&buffer);
    reader.setAutoTransform(true);
    const QSize dimensions = reader.size();
    if (dimensions.isValid())
        reader.setScaledSize(dimensions.scaled(QSize(1200, 1200), Qt::KeepAspectRatio));
    return reader.read();
}

QImage decodeImage(const QString &path)
{
    QImageReader reader(path);
    reader.setAutoTransform(true);
    const QSize dimensions = reader.size();
    if (dimensions.isValid())
        reader.setScaledSize(dimensions.scaled(QSize(1200, 1200), Qt::KeepAspectRatio));
    return reader.read();
}

QString accentFromImage(const QImage &image)
{
    if (image.isNull())
        return {};
    const QImage sample = image.scaled(24, 24, Qt::IgnoreAspectRatio, Qt::SmoothTransformation)
                              .convertToFormat(QImage::Format_ARGB32);
    quint64 red = 0, green = 0, blue = 0, count = 0;
    for (int y = 0; y < sample.height(); ++y) {
        const auto *line = reinterpret_cast<const QRgb *>(sample.constScanLine(y));
        for (int x = 0; x < sample.width(); ++x) {
            const QColor color = QColor::fromRgba(line[x]);
            if (color.alpha() < 32)
                continue;
            red += color.red();
            green += color.green();
            blue += color.blue();
            ++count;
        }
    }
    if (count == 0)
        return {};
    return QColor(static_cast<int>(red / count), static_cast<int>(green / count),
                  static_cast<int>(blue / count)).name(QColor::HexRgb);
}

QString cacheEmbedded(const QByteArray &bytes, const QString &cacheDirectory, QImage *imageOut)
{
    QImage image = decodeImage(bytes);
    if (image.isNull())
        return {};
    *imageOut = image;
    if (cacheDirectory.isEmpty())
        return {};
    const QString digest = QString::fromLatin1(QCryptographicHash::hash(bytes, QCryptographicHash::Sha256).toHex());
    const QString directory = QDir(cacheDirectory).filePath(QStringLiteral("artwork"));
    if (!QDir().mkpath(directory))
        return {};
    const QString target = QDir(directory).filePath(digest + QStringLiteral(".png"));
    if (QFileInfo::exists(target))
        return target;
    QSaveFile output(target);
    if (!output.open(QIODevice::WriteOnly) || !image.save(&output, "PNG") || !output.commit())
        return {};
    return target;
}

QString localArtwork(const QString &audioPath)
{
    const QDir directory = QFileInfo(audioPath).dir();
    const QStringList names{QStringLiteral("cover"), QStringLiteral("folder"),
                            QStringLiteral("front"), QStringLiteral("album"), QStringLiteral("artwork")};
    const QFileInfoList entries = directory.entryInfoList(QDir::Files | QDir::Readable, QDir::Name);
    for (const QString &name : names) {
        for (const QFileInfo &info : entries) {
            if (info.completeBaseName().compare(name, Qt::CaseInsensitive) != 0
                || !QStringList{QStringLiteral("jpg"), QStringLiteral("jpeg"),
                                QStringLiteral("png"), QStringLiteral("webp")}
                       .contains(info.suffix().toLower()))
                continue;
            QImageReader reader(info.absoluteFilePath());
            if (reader.canRead())
                return info.canonicalFilePath();
        }
    }
    return {};
}

} // namespace

ResolvedArtwork ArtworkResolver::resolve(const QString &audioPath, const QString &cacheDirectory,
                                         TagLib::File *audioFile)
{
    ResolvedArtwork resolved;
    QImage image;
    const QByteArray embedded = embeddedImage(audioFile);
    if (!embedded.isEmpty()) {
        resolved.path = cacheEmbedded(embedded, cacheDirectory, &image);
    }
    if (resolved.path.isEmpty()) {
        resolved.path = localArtwork(audioPath);
        if (!resolved.path.isEmpty())
            image = decodeImage(resolved.path);
    }
    if (!image.isNull())
        resolved.accent = accentFromImage(image);
    return resolved;
}

} // namespace Sonora
