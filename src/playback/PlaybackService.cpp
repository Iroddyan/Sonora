#include "PlaybackService.h"

#include <QUrl>
#include <QSet>
#include <algorithm>
#include <random>

namespace Sonora {

PlaybackService::PlaybackService(TrackListModel *library, QObject *parent)
    : QObject(parent)
    , m_library(library)
{
    m_player.setAudioOutput(&m_audioOutput);
    m_audioOutput.setVolume(0.65);

    connect(&m_player, &QMediaPlayer::playbackStateChanged, this,
            [this](QMediaPlayer::PlaybackState state) {
                const bool nowPlaying = state == QMediaPlayer::PlayingState;
                if (m_playing != nowPlaying) {
                    m_playing = nowPlaying;
                    emit playingChanged();
                }
            });
    connect(&m_player, &QMediaPlayer::positionChanged, this, [this](qint64) {
        emit positionChanged();
    });
    connect(&m_player, &QMediaPlayer::durationChanged, this, [this](qint64) {
        emit durationChanged();
    });
    connect(&m_audioOutput, &QAudioOutput::volumeChanged, this, &PlaybackService::volumeChanged);
    connect(&m_player, &QMediaPlayer::mediaStatusChanged, this,
            [this](QMediaPlayer::MediaStatus status) {
                if (status == QMediaPlayer::EndOfMedia)
                    next();
            });
    connect(&m_player, &QMediaPlayer::errorOccurred, this,
            [this](QMediaPlayer::Error, const QString &message) {
                setErrorMessage(message.isEmpty()
                                    ? QStringLiteral("Sonora could not play this audio file.")
                                    : message);
            });
}

bool PlaybackService::hasTrack() const { return m_hasTrack; }
bool PlaybackService::playing() const { return m_playing; }
QString PlaybackService::currentTitle() const { return m_currentTitle; }
QString PlaybackService::currentArtist() const { return m_currentArtist; }
QString PlaybackService::currentPath() const { return m_currentPath; }
QString PlaybackService::currentArtworkUrl() const { return m_currentArtworkUrl; }
QString PlaybackService::currentAccentColor() const { return m_currentAccentColor; }
qint64 PlaybackService::position() const { return m_player.position(); }
qint64 PlaybackService::duration() const { return m_player.duration(); }
qreal PlaybackService::volume() const { return m_audioOutput.volume(); }
QString PlaybackService::errorMessage() const { return m_errorMessage; }

void PlaybackService::playPath(const QString &path)
{
    if (!m_library)
        return;
    const int index = m_library->indexOfPath(path);
    if (index < 0) {
        setErrorMessage(QStringLiteral("This song is no longer in the indexed library. Rescan its folder and try again."));
        return;
    }
    m_playSequence.clear();
    for (const Track &track : m_library->allTracks())
        m_playSequence.push_back(track.path);
    m_sequenceIndex = index;
    playIndex(index);
}

void PlaybackService::playPaths(const QStringList &paths, bool shuffle, const QString &startPath)
{
    if (!m_library)
        return;
    QStringList available;
    available.reserve(paths.size());
    QSet<QString> seen;
    for (const QString &path : paths) {
        if (m_library->indexOfPath(path) >= 0 && !seen.contains(path)) {
            available.push_back(path);
            seen.insert(path);
        }
    }
    if (available.isEmpty()) {
        setErrorMessage(QStringLiteral("No tracks from this collection are currently indexed."));
        return;
    }
    if (shuffle) {
        std::mt19937 generator(std::random_device{}());
        std::shuffle(available.begin(), available.end(), generator);
    }
    m_playSequence = std::move(available);
    m_sequenceIndex = startPath.isEmpty() ? 0 : m_playSequence.indexOf(startPath);
    if (m_sequenceIndex < 0)
        m_sequenceIndex = 0;
    playSequenceAt(m_sequenceIndex);
}

void PlaybackService::togglePlayback()
{
    if (!m_hasTrack)
        return;
    setErrorMessage({});
    if (m_player.playbackState() == QMediaPlayer::PlayingState)
        m_player.pause();
    else
        m_player.play();
}

void PlaybackService::previous()
{
    if (!m_hasTrack || !m_library)
        return;
    if (m_sequenceIndex < 0 || m_sequenceIndex >= m_playSequence.size()) {
        stopAfterLastTrack();
        return;
    }
    if (position() > 3000 || m_sequenceIndex == 0)
        playSequenceAt(m_sequenceIndex);
    else
        playSequenceAt(m_sequenceIndex - 1);
}

void PlaybackService::next()
{
    if (!m_hasTrack || !m_library)
        return;
    if (m_sequenceIndex < 0 || m_sequenceIndex + 1 >= m_playSequence.size()) {
        stopAfterLastTrack();
        return;
    }
    playSequenceAt(m_sequenceIndex + 1);
}

void PlaybackService::seek(qint64 positionMs)
{
    if (!m_hasTrack || duration() <= 0)
        return;
    m_player.setPosition(qBound<qint64>(0, positionMs, duration()));
}

void PlaybackService::setVolume(qreal volume)
{
    m_audioOutput.setVolume(qBound<qreal>(0.0, volume, 1.0));
}

void PlaybackService::playIndex(int index)
{
    if (!m_library)
        return;
    const Track *track = m_library->trackAt(index);
    if (!track)
        return;
    m_currentTitle = track->title;
    m_currentArtist = track->artist;
    m_currentPath = track->path;
    m_currentArtworkUrl = track->artworkPath.isEmpty()
                              ? QString{}
                              : QUrl::fromLocalFile(track->artworkPath).toString();
    m_currentAccentColor = track->artworkAccent;
    m_hasTrack = true;
    emit currentTrackChanged();
    setErrorMessage({});
    emit positionChanged();
    emit durationChanged();
    m_player.setSource(QUrl::fromLocalFile(track->path));
    m_player.play();
}

void PlaybackService::playSequenceAt(int index)
{
    if (!m_library || index < 0 || index >= m_playSequence.size()) {
        stopAfterLastTrack();
        return;
    }
    const int libraryIndex = m_library->indexOfPath(m_playSequence.at(index));
    if (libraryIndex < 0) {
        stopAfterLastTrack();
        setErrorMessage(QStringLiteral("A track in this collection is no longer indexed. Rescan the folder and try again."));
        return;
    }
    m_sequenceIndex = index;
    playIndex(libraryIndex);
}

void PlaybackService::stopAfterLastTrack()
{
    m_player.stop();
    m_hasTrack = false;
    m_currentTitle.clear();
    m_currentArtist.clear();
    m_currentPath.clear();
    m_currentArtworkUrl.clear();
    m_currentAccentColor.clear();
    m_sequenceIndex = -1;
    emit currentTrackChanged();
    emit positionChanged();
    emit durationChanged();
}

void PlaybackService::setErrorMessage(const QString &message)
{
    if (m_errorMessage == message)
        return;
    m_errorMessage = message;
    emit errorMessageChanged();
}

} // namespace Sonora
