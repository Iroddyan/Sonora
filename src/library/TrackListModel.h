#pragma once

#include "Track.h"

#include <QAbstractListModel>

namespace Sonora {

class TrackListModel final : public QAbstractListModel {
    Q_OBJECT
    Q_PROPERTY(int count READ count NOTIFY countChanged)

public:
    enum Role {
        PathRole = Qt::UserRole + 1,
        TitleRole,
        ArtistRole,
        AlbumArtistRole,
        AlbumRole,
        GenreRole,
        DurationRole,
        TrackNumberRole,
        DiscNumberRole,
        YearRole,
        SourceRootRole
    };
    Q_ENUM(Role)

    explicit TrackListModel(QObject *parent = nullptr);

    int rowCount(const QModelIndex &parent = {}) const override;
    QVariant data(const QModelIndex &index, int role = Qt::DisplayRole) const override;
    QHash<int, QByteArray> roleNames() const override;
    int count() const;
    const QVector<Track> &allTracks() const;
    const Track *trackAt(int index) const;
    int indexOfPath(const QString &path) const;

    Q_INVOKABLE void setSearchText(const QString &text);

    void setTracks(QVector<Track> tracks);

signals:
    void countChanged();

private:
    void rebuildVisibleRows();

    QVector<Track> m_tracks;
    QVector<int> m_visibleRows;
    QString m_searchText;
};

} // namespace Sonora
