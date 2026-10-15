#include "TrackListModel.h"

#include <QFileInfo>

namespace Sonora {

TrackListModel::TrackListModel(QObject *parent)
    : QAbstractListModel(parent)
{
}

int TrackListModel::rowCount(const QModelIndex &parent) const
{
    return parent.isValid() ? 0 : m_visibleRows.size();
}

QVariant TrackListModel::data(const QModelIndex &index, int role) const
{
    if (!index.isValid() || index.row() < 0 || index.row() >= m_visibleRows.size())
        return {};

    const Track &track = m_tracks.at(m_visibleRows.at(index.row()));
    switch (role) {
    case PathRole: return track.path;
    case TitleRole: return track.title;
    case ArtistRole: return track.artist;
    case AlbumArtistRole: return track.albumArtist;
    case AlbumRole: return track.album;
    case GenreRole: return track.genre;
    case DurationRole: return track.durationMs;
    case TrackNumberRole: return track.trackNumber;
    case DiscNumberRole: return track.discNumber;
    case YearRole: return track.year;
    case SourceRootRole: return track.sourceRoot;
    case Qt::DisplayRole: return track.title;
    default: return {};
    }
}

QHash<int, QByteArray> TrackListModel::roleNames() const
{
    return {
        {PathRole, "path"}, {TitleRole, "title"}, {ArtistRole, "artist"},
        {AlbumArtistRole, "albumArtist"}, {AlbumRole, "album"}, {GenreRole, "genre"},
        {DurationRole, "durationMs"}, {TrackNumberRole, "trackNumber"},
        {DiscNumberRole, "discNumber"}, {YearRole, "year"}, {SourceRootRole, "sourceRoot"}
    };
}

int TrackListModel::count() const
{
    return m_tracks.size();
}

const QVector<Track> &TrackListModel::allTracks() const
{
    return m_tracks;
}

const Track *TrackListModel::trackAt(int index) const
{
    return index >= 0 && index < m_tracks.size() ? &m_tracks.at(index) : nullptr;
}

int TrackListModel::indexOfPath(const QString &path) const
{
    for (qsizetype index = 0; index < m_tracks.size(); ++index) {
        if (m_tracks.at(index).path == path)
            return static_cast<int>(index);
    }
    return -1;
}

void TrackListModel::setSearchText(const QString &text)
{
    const QString normalized = text.trimmed();
    if (m_searchText == normalized)
        return;
    beginResetModel();
    m_searchText = normalized;
    rebuildVisibleRows();
    endResetModel();
    emit countChanged();
}

void TrackListModel::setTracks(QVector<Track> tracks)
{
    beginResetModel();
    m_tracks = std::move(tracks);
    rebuildVisibleRows();
    endResetModel();
    emit countChanged();
}

void TrackListModel::rebuildVisibleRows()
{
    m_visibleRows.clear();
    const QString query = m_searchText.toCaseFolded();
    for (qsizetype i = 0; i < m_tracks.size(); ++i) {
        const Track &track = m_tracks.at(i);
        const QString searchable = QStringList{track.title, track.artist, track.albumArtist,
                                               track.album, track.genre, track.composer,
                                               QFileInfo(track.path).fileName()}
                                      .join(u' ')
                                      .toCaseFolded();
        if (query.isEmpty() || searchable.contains(query))
            m_visibleRows.push_back(static_cast<int>(i));
    }
}

} // namespace Sonora
