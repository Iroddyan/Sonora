#pragma once

#include "../library/TrackListModel.h"

#include <QAudioOutput>
#include <QMediaPlayer>
#include <QObject>

namespace Sonora {

class PlaybackService final : public QObject {
    Q_OBJECT
    Q_PROPERTY(bool hasTrack READ hasTrack NOTIFY currentTrackChanged)
    Q_PROPERTY(bool playing READ playing NOTIFY playingChanged)
    Q_PROPERTY(QString currentTitle READ currentTitle NOTIFY currentTrackChanged)
    Q_PROPERTY(QString currentArtist READ currentArtist NOTIFY currentTrackChanged)
    Q_PROPERTY(QString currentPath READ currentPath NOTIFY currentTrackChanged)
    Q_PROPERTY(qint64 position READ position NOTIFY positionChanged)
    Q_PROPERTY(qint64 duration READ duration NOTIFY durationChanged)
    Q_PROPERTY(qreal volume READ volume NOTIFY volumeChanged)
    Q_PROPERTY(QString errorMessage READ errorMessage NOTIFY errorMessageChanged)

public:
    explicit PlaybackService(TrackListModel *library, QObject *parent = nullptr);

    bool hasTrack() const;
    bool playing() const;
    QString currentTitle() const;
    QString currentArtist() const;
    QString currentPath() const;
    qint64 position() const;
    qint64 duration() const;
    qreal volume() const;
    QString errorMessage() const;

    Q_INVOKABLE void playPath(const QString &path);
    Q_INVOKABLE void togglePlayback();
    Q_INVOKABLE void previous();
    Q_INVOKABLE void next();
    Q_INVOKABLE void seek(qint64 positionMs);
    Q_INVOKABLE void setVolume(qreal volume);

signals:
    void currentTrackChanged();
    void playingChanged();
    void positionChanged();
    void durationChanged();
    void volumeChanged();
    void errorMessageChanged();

private:
    void playIndex(int index);
    void stopAfterLastTrack();
    void setErrorMessage(const QString &message);

    TrackListModel *m_library = nullptr;
    QMediaPlayer m_player;
    QAudioOutput m_audioOutput;
    QString m_currentTitle;
    QString m_currentArtist;
    QString m_currentPath;
    QString m_errorMessage;
    bool m_hasTrack = false;
    bool m_playing = false;
};

} // namespace Sonora
