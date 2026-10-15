import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Sonora

Item {
    id: root
    property var selectedAlbum: null

    function durationLabel(milliseconds) {
        const totalMinutes = Math.floor(Math.max(0, milliseconds) / 60000)
        const hours = Math.floor(totalMinutes / 60)
        const minutes = totalMinutes % 60
        return hours > 0 ? hours + " hr " + minutes + " min" : totalMinutes + " min"
    }

    function albumPaths() {
        const paths = []
        if (selectedAlbum) {
            for (let i = 0; i < selectedAlbum.tracks.length; ++i)
                paths.push(selectedAlbum.tracks[i].path)
        }
        return paths
    }

    function hasMultipleDiscs(tracks) {
        if (!tracks || tracks.length < 2)
            return false
        const discs = new Set()
        for (let i = 0; i < tracks.length; ++i)
            discs.add(tracks[i].discNumber > 0 ? tracks[i].discNumber : 1)
        return discs.size > 1
    }

    function discNumber(track) {
        return track.discNumber > 0 ? track.discNumber : 1
    }

    GridView {
        id: albumsGrid
        anchors.fill: parent
        visible: !root.selectedAlbum && Library.albums.count > 0
        clip: true
        cellWidth: Math.max(176, Math.min(242, width / Math.max(1, Math.floor(width / 220))))
        cellHeight: 300
        model: Library.albums
        ScrollBar.vertical: ScrollBar { }

        delegate: Item {
            id: albumCard
            required property string title
            required property string artist
            required property int year
            required property int trackCount
            required property string artworkUrl
            required property string accentColor
            required property var tracks
            width: albumsGrid.cellWidth
            height: albumsGrid.cellHeight

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 9
                spacing: 8
                ArtworkTile {
                    Layout.fillWidth: true
                    Layout.preferredHeight: width
                    artworkUrl: albumCard.artworkUrl
                    accentColor: albumCard.accentColor
                    cornerRadius: 15
                }
                Text {
                    Layout.fillWidth: true
                    text: albumCard.title
                    color: Theme.text
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }
                Text {
                    Layout.fillWidth: true
                    text: albumCard.artist + (albumCard.year > 0 ? " · " + albumCard.year : "")
                    color: Theme.secondaryText
                    font.pixelSize: 11
                    elide: Text.ElideRight
                }
            }
            Rectangle {
                anchors.fill: parent
                radius: 15
                color: cardMouse.containsMouse ? Theme.surface : "transparent"
                z: -1
            }
            MouseArea {
                id: cardMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                Accessible.name: albumCard.title + " by " + albumCard.artist
                onClicked: root.selectedAlbum = ({ title: albumCard.title, artist: albumCard.artist,
                    year: albumCard.year, trackCount: albumCard.trackCount, artworkUrl: albumCard.artworkUrl,
                    accentColor: albumCard.accentColor, tracks: albumCard.tracks })
            }
        }
    }

    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(parent.width - 48, 430)
        visible: !root.selectedAlbum && Library.albums.count === 0
        spacing: 10
        Text { Layout.fillWidth: true; text: Library.tracks.count === 0 ? "No albums yet" : "No album tags found"; color: Theme.text; font.pixelSize: 20; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter }
        Text {
            Layout.fillWidth: true
            text: Library.tracks.count === 0
                  ? "Add a music folder from Songs to browse albums from your own collection."
                  : "Sonora needs album metadata to group these songs. The indexed tracks are still available in Songs."
            color: Theme.secondaryText
            font.pixelSize: 13
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
        }
    }

    ColumnLayout {
        anchors.fill: parent
        visible: root.selectedAlbum !== null
        spacing: 14
        RowLayout {
            Layout.fillWidth: true
            ActionButton { text: "‹ Albums"; onClicked: root.selectedAlbum = null; Accessible.name: "Back to albums" }
            Item { Layout.fillWidth: true }
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(250, parent.height * 0.34)
            spacing: 20
            ArtworkTile {
                Layout.preferredWidth: Math.min(parent.height, 230)
                Layout.preferredHeight: Layout.preferredWidth
                artworkUrl: root.selectedAlbum ? root.selectedAlbum.artworkUrl : ""
                accentColor: root.selectedAlbum ? root.selectedAlbum.accentColor : ""
                cornerRadius: 16
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8
                Text { Layout.fillWidth: true; text: root.selectedAlbum ? root.selectedAlbum.title : ""; color: Theme.text; font.pixelSize: 27; font.weight: Font.Bold; wrapMode: Text.WordWrap }
                Text { Layout.fillWidth: true; text: root.selectedAlbum ? root.selectedAlbum.artist + (root.selectedAlbum.year > 0 ? " · " + root.selectedAlbum.year : "") : ""; color: Theme.secondaryText; font.pixelSize: 14; wrapMode: Text.WordWrap }
                Text { Layout.fillWidth: true; text: root.selectedAlbum ? root.selectedAlbum.trackCount + " tracks · " + root.durationLabel(root.selectedAlbum.tracks.reduce((sum, track) => sum + track.durationMs, 0)) : ""; color: Theme.mutedText; font.pixelSize: 12 }
                RowLayout {
                    spacing: 8
                    ActionButton { text: "Play album"; primary: true; enabled: root.selectedAlbum && root.selectedAlbum.tracks.length > 0; onClicked: Playback.playPaths(root.albumPaths(), false); Accessible.name: "Play album" }
                    ActionButton { text: "Shuffle"; enabled: root.selectedAlbum && root.selectedAlbum.tracks.length > 0; onClicked: Playback.playPaths(root.albumPaths(), true); Accessible.name: "Shuffle album" }
                }
                Item { Layout.fillHeight: true }
            }
        }
        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }
        ListView {
            id: albumTracks
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 2
            model: root.selectedAlbum ? root.selectedAlbum.tracks : []
            ScrollBar.vertical: ScrollBar { }
            delegate: Rectangle {
                required property var modelData
                required property int index
                property bool showDiscHeader: root.selectedAlbum && root.hasMultipleDiscs(root.selectedAlbum.tracks)
                                              && (index === 0 || root.discNumber(modelData) !== root.discNumber(root.selectedAlbum.tracks[index - 1]))
                width: albumTracks.width
                height: showDiscHeader ? 70 : 50
                radius: 9
                color: trackMouse.containsMouse ? Theme.surface : "transparent"
                Text {
                    visible: albumRow.showDiscHeader
                    anchors.left: parent.left
                    anchors.leftMargin: 12
                    anchors.top: parent.top
                    anchors.topMargin: 4
                    text: "Disc " + root.discNumber(albumRow.modelData)
                    color: Theme.mutedText
                    font.pixelSize: 10
                    font.weight: Font.DemiBold
                }
                id: albumRow
                RowLayout {
                    anchors.fill: parent
                    anchors.topMargin: albumRow.showDiscHeader ? 18 : 0
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 12
                    Text { Layout.preferredWidth: 28; text: modelData.trackNumber > 0 ? modelData.trackNumber : index + 1; color: Theme.mutedText; font.pixelSize: 11; horizontalAlignment: Text.AlignRight }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Text { Layout.fillWidth: true; text: modelData.title; color: Theme.text; font.pixelSize: 13; elide: Text.ElideRight }
                        Text { Layout.fillWidth: true; text: modelData.artist; color: Theme.secondaryText; font.pixelSize: 11; elide: Text.ElideRight }
                    }
                    Text { text: modelData.durationMs > 0 ? Math.floor(modelData.durationMs / 60000) + ":" + ("0" + Math.floor((modelData.durationMs % 60000) / 1000)).slice(-2) : "—"; color: Theme.mutedText; font.pixelSize: 11; font.family: "monospace" }
                    ActionButton { text: "Play"; onClicked: Playback.playPaths(root.albumPaths(), false, modelData.path); Accessible.name: "Play " + modelData.title }
                }
                TapHandler { onDoubleTapped: Playback.playPaths(root.albumPaths(), false, modelData.path) }
            }
        }
    }
}
