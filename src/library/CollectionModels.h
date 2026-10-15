#pragma once

#include "Track.h"

#include <QAbstractListModel>
#include <QVariantList>

namespace Sonora {

class AlbumListModel final : public QAbstractListModel {
    Q_OBJECT
    Q_PROPERTY(int count READ count NOTIFY countChanged)

public:
    enum Role { TitleRole = Qt::UserRole + 1, ArtistRole, YearRole, TrackCountRole,
                DurationRole, ArtworkUrlRole, AccentRole, TracksRole };
    Q_ENUM(Role)

    explicit AlbumListModel(QObject *parent = nullptr);
    int rowCount(const QModelIndex &parent = {}) const override;
    QVariant data(const QModelIndex &index, int role = Qt::DisplayRole) const override;
    QHash<int, QByteArray> roleNames() const override;
    int count() const;
    void setTracks(const QVector<Track> &tracks);

signals:
    void countChanged();

private:
    struct Album {
        QString title;
        QString artist;
        int year = 0;
        qint64 durationMs = 0;
        QString artworkUrl;
        QString accent;
        QVariantList tracks;
    };
    QVector<Album> m_albums;
};

class ArtistListModel final : public QAbstractListModel {
    Q_OBJECT
    Q_PROPERTY(int count READ count NOTIFY countChanged)

public:
    enum Role { NameRole = Qt::UserRole + 1, AlbumCountRole, TrackCountRole,
                ArtworkUrlRole, AccentRole, TracksRole, AlbumsRole };
    Q_ENUM(Role)

    explicit ArtistListModel(QObject *parent = nullptr);
    int rowCount(const QModelIndex &parent = {}) const override;
    QVariant data(const QModelIndex &index, int role = Qt::DisplayRole) const override;
    QHash<int, QByteArray> roleNames() const override;
    int count() const;
    void setTracks(const QVector<Track> &tracks);

signals:
    void countChanged();

private:
    struct Artist {
        QString name;
        QString artworkUrl;
        QString accent;
        QVariantList tracks;
        QVariantList albums;
    };
    QVector<Artist> m_artists;
};

} // namespace Sonora
