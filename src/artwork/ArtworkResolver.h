#pragma once

#include <QString>

namespace TagLib { class File; }

namespace Sonora {

struct ResolvedArtwork {
    QString path;
    QString accent;
};

class ArtworkResolver final {
public:
    static ResolvedArtwork resolve(const QString &audioPath, const QString &cacheDirectory,
                                   TagLib::File *audioFile = nullptr);
};

} // namespace Sonora
