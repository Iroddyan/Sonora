#include "CollectionModels.h"

#include <QUrl>
#include <algorithm>

namespace Sonora {
namespace {

QString albumArtistFor(const Track &track)
{
    return track.albumArtist.trimmed().isEmpty() ? track.artist.trimmed() : track.albumArtist.trimmed();
}

QString artistKeyFor(const Track &track)
{
    return albumArtistFor(track).toCaseFolded();
}

QString artworkUrlFor(const Track &track)
{
    return track.artworkPath.isEmpty() ? QString{} : QUrl::fromLocalFile(track.artworkPath).toString();
}

QVariantMap trackMap(const Track &track)
{
    return {
        {QStringLiteral("path"), track.path},
        {QStringLiteral("title"), track.title},
        {QStringLiteral("artist"), track.artist.isEmpty() ? QStringLiteral("Unknown artist") : track.artist},
        {QStringLiteral("album"), track.album},
        {QStringLiteral("durationMs"), track.durationMs},
        {QStringLiteral("trackNumber"), track.trackNumber},
        {QStringLiteral("discNumber"), track.discNumber}
    };
}

} // namespace

AlbumListModel::AlbumListModel(QObject *parent) : QAbstractListModel(parent) {}

int AlbumListModel::rowCount(const QModelIndex &parent) const
{
    return parent.isValid() ? 0 : m_albums.size();
}

QVariant AlbumListModel::data(const QModelIndex &index, int role) const
{
    if (!index.isValid() || index.row() < 0 || index.row() >= m_albums.size())
        return {};
    const Album &album = m_albums.at(index.row());
    switch (role) {
    case TitleRole: return album.title;
    case ArtistRole: return album.artist;
    case YearRole: return album.year;
    case TrackCountRole: return album.tracks.size();
    case DurationRole: return album.durationMs;
    case ArtworkUrlRole: return album.artworkUrl;
    case AccentRole: return album.accent;
    case TracksRole: return album.tracks;
    case Qt::DisplayRole: return album.title;
    default: return {};
    }
}

QHash<int, QByteArray> AlbumListModel::roleNames() const
{
    return {{TitleRole, "title"}, {ArtistRole, "artist"}, {YearRole, "year"},
            {TrackCountRole, "trackCount"}, {DurationRole, "durationMs"},
            {ArtworkUrlRole, "artworkUrl"}, {AccentRole, "accentColor"}, {TracksRole, "tracks"}};
}

int AlbumListModel::count() const { return m_albums.size(); }

void AlbumListModel::setTracks(const QVector<Track> &tracks)
{
    beginResetModel();
    m_albums.clear();
    QHash<QString, int> albumIndexes;
    for (const Track &track : tracks) {
        const QString title = track.album.trimmed();
        if (title.isEmpty())
            continue;
        const QString artist = albumArtistFor(track);
        const QString key = title.toCaseFolded() + QChar(0x1f) + artist.toCaseFolded();
        int index = albumIndexes.value(key, -1);
        if (index < 0) {
            index = m_albums.size();
            albumIndexes.insert(key, index);
            Album album;
            album.title = title;
            album.artist = artist.isEmpty() ? QStringLiteral("Unknown artist") : artist;
            m_albums.push_back(std::move(album));
        }
        Album &album = m_albums[index];
        if (album.year == 0 && track.year > 0)
            album.year = track.year;
        if (album.artworkUrl.isEmpty() && !track.artworkPath.isEmpty()) {
            album.artworkUrl = artworkUrlFor(track);
            album.accent = track.artworkAccent;
        }
        album.durationMs += track.durationMs;
        album.tracks.push_back(trackMap(track));
    }
    for (Album &album : m_albums) {
        std::sort(album.tracks.begin(), album.tracks.end(), [](const QVariant &left, const QVariant &right) {
            const QVariantMap a = left.toMap();
            const QVariantMap b = right.toMap();
            const int discA = a.value(QStringLiteral("discNumber")).toInt();
            const int discB = b.value(QStringLiteral("discNumber")).toInt();
            if (discA != discB) return discA < discB;
            const int numberA = a.value(QStringLiteral("trackNumber")).toInt();
            const int numberB = b.value(QStringLiteral("trackNumber")).toInt();
            if (numberA != numberB && numberA > 0 && numberB > 0) return numberA < numberB;
            if (numberA > 0 && numberB == 0) return true;
            if (numberA == 0 && numberB > 0) return false;
            return QString::compare(a.value(QStringLiteral("title")).toString(),
                                   b.value(QStringLiteral("title")).toString(), Qt::CaseInsensitive) < 0;
        });
    }
    std::sort(m_albums.begin(), m_albums.end(), [](const Album &a, const Album &b) {
        const int artist = QString::compare(a.artist, b.artist, Qt::CaseInsensitive);
        return artist == 0 ? QString::compare(a.title, b.title, Qt::CaseInsensitive) < 0 : artist < 0;
    });
    endResetModel();
    emit countChanged();
}

ArtistListModel::ArtistListModel(QObject *parent) : QAbstractListModel(parent) {}

int ArtistListModel::rowCount(const QModelIndex &parent) const
{
    return parent.isValid() ? 0 : m_artists.size();
}

QVariant ArtistListModel::data(const QModelIndex &index, int role) const
{
    if (!index.isValid() || index.row() < 0 || index.row() >= m_artists.size())
        return {};
    const Artist &artist = m_artists.at(index.row());
    switch (role) {
    case NameRole: return artist.name;
    case AlbumCountRole: return artist.albums.size();
    case TrackCountRole: return artist.tracks.size();
    case ArtworkUrlRole: return artist.artworkUrl;
    case AccentRole: return artist.accent;
    case TracksRole: return artist.tracks;
    case AlbumsRole: return artist.albums;
    case Qt::DisplayRole: return artist.name;
    default: return {};
    }
}

QHash<int, QByteArray> ArtistListModel::roleNames() const
{
    return {{NameRole, "name"}, {AlbumCountRole, "albumCount"}, {TrackCountRole, "trackCount"},
            {ArtworkUrlRole, "artworkUrl"}, {AccentRole, "accentColor"},
            {TracksRole, "tracks"}, {AlbumsRole, "albums"}};
}

int ArtistListModel::count() const { return m_artists.size(); }

void ArtistListModel::setTracks(const QVector<Track> &tracks)
{
    beginResetModel();
    m_artists.clear();
    QHash<QString, int> indexes;
    QHash<QString, QHash<QString, int>> artistAlbumIndexes;
    for (const Track &track : tracks) {
        const QString name = albumArtistFor(track);
        if (name.isEmpty())
            continue;
        const QString key = artistKeyFor(track);
        int index = indexes.value(key, -1);
        if (index < 0) {
            index = m_artists.size();
            indexes.insert(key, index);
            Artist artist;
            artist.name = name;
            m_artists.push_back(std::move(artist));
        }
        Artist &artist = m_artists[index];
        artist.tracks.push_back(trackMap(track));
        if (artist.artworkUrl.isEmpty() && !track.artworkPath.isEmpty()) {
            artist.artworkUrl = artworkUrlFor(track);
            artist.accent = track.artworkAccent;
        }
        if (track.album.trimmed().isEmpty())
            continue;
        const QString albumKey = track.album.toCaseFolded();
        auto &albumMap = artistAlbumIndexes[key];
        int albumIndex = albumMap.value(albumKey, -1);
        if (albumIndex < 0) {
            albumIndex = artist.albums.size();
            albumMap.insert(albumKey, albumIndex);
            QVariantMap album{{QStringLiteral("title"), track.album.trimmed()},
                              {QStringLiteral("artist"), name},
                              {QStringLiteral("year"), track.year},
                              {QStringLiteral("artworkUrl"), artworkUrlFor(track)},
                              {QStringLiteral("accentColor"), track.artworkAccent},
                              {QStringLiteral("tracks"), QVariantList{}}};
            artist.albums.push_back(album);
        }
        QVariantMap album = artist.albums[albumIndex].toMap();
        if (album.value(QStringLiteral("year")).toInt() == 0 && track.year > 0)
            album.insert(QStringLiteral("year"), track.year);
        if (album.value(QStringLiteral("artworkUrl")).toString().isEmpty() && !track.artworkPath.isEmpty()) {
            album.insert(QStringLiteral("artworkUrl"), artworkUrlFor(track));
            album.insert(QStringLiteral("accentColor"), track.artworkAccent);
        }
        QVariantList albumTracks = album.value(QStringLiteral("tracks")).toList();
        albumTracks.push_back(trackMap(track));
        album.insert(QStringLiteral("tracks"), albumTracks);
        artist.albums[albumIndex] = album;
    }
    for (Artist &artist : m_artists) {
        std::sort(artist.tracks.begin(), artist.tracks.end(), [](const QVariant &left, const QVariant &right) {
            const QVariantMap a = left.toMap();
            const QVariantMap b = right.toMap();
            const int album = QString::compare(a.value(QStringLiteral("album")).toString(),
                                               b.value(QStringLiteral("album")).toString(), Qt::CaseInsensitive);
            if (album != 0)
                return album < 0;
            const int discA = a.value(QStringLiteral("discNumber")).toInt();
            const int discB = b.value(QStringLiteral("discNumber")).toInt();
            if (discA != discB)
                return discA < discB;
            const int numberA = a.value(QStringLiteral("trackNumber")).toInt();
            const int numberB = b.value(QStringLiteral("trackNumber")).toInt();
            if (numberA != numberB && numberA > 0 && numberB > 0)
                return numberA < numberB;
            return QString::compare(a.value(QStringLiteral("title")).toString(),
                                    b.value(QStringLiteral("title")).toString(), Qt::CaseInsensitive) < 0;
        });
        for (QVariant &value : artist.albums) {
            QVariantMap album = value.toMap();
            QVariantList albumTracks = album.value(QStringLiteral("tracks")).toList();
            std::sort(albumTracks.begin(), albumTracks.end(), [](const QVariant &left, const QVariant &right) {
                const QVariantMap a = left.toMap();
                const QVariantMap b = right.toMap();
                const int discA = a.value(QStringLiteral("discNumber")).toInt();
                const int discB = b.value(QStringLiteral("discNumber")).toInt();
                if (discA != discB) return discA < discB;
                const int numberA = a.value(QStringLiteral("trackNumber")).toInt();
                const int numberB = b.value(QStringLiteral("trackNumber")).toInt();
                if (numberA != numberB && numberA > 0 && numberB > 0) return numberA < numberB;
                return QString::compare(a.value(QStringLiteral("title")).toString(),
                                        b.value(QStringLiteral("title")).toString(), Qt::CaseInsensitive) < 0;
            });
            album.insert(QStringLiteral("tracks"), albumTracks);
            value = album;
        }
        std::sort(artist.albums.begin(), artist.albums.end(), [](const QVariant &left, const QVariant &right) {
            return QString::compare(left.toMap().value(QStringLiteral("title")).toString(),
                                    right.toMap().value(QStringLiteral("title")).toString(), Qt::CaseInsensitive) < 0;
        });
    }
    std::sort(m_artists.begin(), m_artists.end(), [](const Artist &a, const Artist &b) {
        return QString::compare(a.name, b.name, Qt::CaseInsensitive) < 0;
    });
    endResetModel();
    emit countChanged();
}

} // namespace Sonora
