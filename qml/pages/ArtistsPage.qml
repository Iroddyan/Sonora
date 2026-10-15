import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Sonora

Item {
    id: root
    property var selectedArtist: null
    property var selectedAlbum: null

    function artistPaths() {
        const paths = []
        if (selectedArtist) {
            for (let i = 0; i < selectedArtist.tracks.length; ++i)
                paths.push(selectedArtist.tracks[i].path)
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
        id: artistsGrid
        anchors.fill: parent
        visible: !root.selectedArtist && Library.artists.count > 0
        clip: true
        cellWidth: Math.max(180, Math.min(250, width / Math.max(1, Math.floor(width / 228))))
        cellHeight: 230
        model: Library.artists
        ScrollBar.vertical: ScrollBar { }

        delegate: Item {
            id: artistCard
            required property string name
            required property int albumCount
            required property int trackCount
            required property string artworkUrl
            required property string accentColor
            required property var tracks
            required property var albums
            width: artistsGrid.cellWidth
            height: artistsGrid.cellHeight
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8
                ArtworkTile {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.preferredWidth: Math.min(artistCard.width - 20, 148)
                    Layout.preferredHeight: Layout.preferredWidth
                    artworkUrl: artistCard.artworkUrl
                    accentColor: artistCard.accentColor
                    cornerRadius: 74
                }
                Text { Layout.fillWidth: true; text: artistCard.name; color: Theme.text; font.pixelSize: 13; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; elide: Text.ElideRight }
                Text { Layout.fillWidth: true; text: artistCard.albumCount + (artistCard.albumCount === 1 ? " album" : " albums") + " · " + artistCard.trackCount + (artistCard.trackCount === 1 ? " track" : " tracks"); color: Theme.secondaryText; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter }
            }
            MouseArea {
                id: artistMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                Accessible.name: artistCard.name + ", " + artistCard.albumCount + " albums"
                onClicked: root.selectedArtist = ({ name: artistCard.name, albumCount: artistCard.albumCount,
                    trackCount: artistCard.trackCount, artworkUrl: artistCard.artworkUrl,
                    accentColor: artistCard.accentColor, tracks: artistCard.tracks, albums: artistCard.albums })
            }
            Rectangle { anchors.fill: parent; z: -1; radius: 15; color: artistMouse.containsMouse ? Theme.surface : "transparent" }
        }
    }

    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(parent.width - 48, 430)
        visible: !root.selectedArtist && Library.artists.count === 0
        spacing: 10
        Text { Layout.fillWidth: true; text: Library.tracks.count === 0 ? "No artists yet" : "No artist tags found"; color: Theme.text; font.pixelSize: 20; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter }
        Text { Layout.fillWidth: true; text: Library.tracks.count === 0 ? "Add a music folder from Songs to browse artists from your collection." : "Sonora needs artist or album artist metadata to build artist pages."; color: Theme.secondaryText; font.pixelSize: 13; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter }
    }

    ColumnLayout {
        anchors.fill: parent
        visible: root.selectedArtist !== null && root.selectedAlbum === null
        spacing: 14
        RowLayout {
            Layout.fillWidth: true
            ActionButton { text: "‹ Artists"; onClicked: root.selectedArtist = null; Accessible.name: "Back to artists" }
            Item { Layout.fillWidth: true }
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 170
            spacing: 18
            ArtworkTile {
                Layout.preferredWidth: 150
                Layout.preferredHeight: 150
                artworkUrl: root.selectedArtist ? root.selectedArtist.artworkUrl : ""
                accentColor: root.selectedArtist ? root.selectedArtist.accentColor : ""
                cornerRadius: 75
            }
            ColumnLayout {
                Layout.fillWidth: true
                Text { Layout.fillWidth: true; text: root.selectedArtist ? root.selectedArtist.name : ""; color: Theme.text; font.pixelSize: 28; font.weight: Font.Bold; elide: Text.ElideRight }
                Text { Layout.fillWidth: true; text: root.selectedArtist ? root.selectedArtist.albumCount + " albums · " + root.selectedArtist.trackCount + " tracks" : ""; color: Theme.secondaryText; font.pixelSize: 13 }
                RowLayout {
                    ActionButton { text: "Play artist"; primary: true; enabled: root.selectedArtist && root.selectedArtist.tracks.length > 0; onClicked: Playback.playPaths(root.artistPaths(), false); Accessible.name: "Play artist tracks" }
                    ActionButton { text: "Shuffle"; enabled: root.selectedArtist && root.selectedArtist.tracks.length > 0; onClicked: Playback.playPaths(root.artistPaths(), true); Accessible.name: "Shuffle artist tracks" }
                }
                Item { Layout.fillHeight: true }
            }
        }
        Text { text: "Albums"; color: Theme.text; font.pixelSize: 17; font.weight: Font.DemiBold }
        GridView {
            id: artistAlbums
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(contentHeight, 250)
            visible: root.selectedArtist && root.selectedArtist.albums.length > 0
            clip: true
            cellWidth: 166
            cellHeight: 220
            model: root.selectedArtist ? root.selectedArtist.albums : []
            delegate: Item {
                required property var modelData
                width: artistAlbums.cellWidth
                height: artistAlbums.cellHeight
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 7
                    spacing: 6
                    ArtworkTile { Layout.fillWidth: true; Layout.preferredHeight: width; artworkUrl: modelData.artworkUrl; accentColor: modelData.accentColor; cornerRadius: 12 }
                    Text { Layout.fillWidth: true; text: modelData.title; color: Theme.text; font.pixelSize: 12; font.weight: Font.Medium; elide: Text.ElideRight }
                    Text { Layout.fillWidth: true; text: modelData.year > 0 ? String(modelData.year) : modelData.tracks.length + " tracks"; color: Theme.secondaryText; font.pixelSize: 10; elide: Text.ElideRight }
                }
                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.selectedAlbum = modelData }
            }
        }
        Text { visible: root.selectedArtist && root.selectedArtist.albums.length === 0; text: "No album tags for this artist yet."; color: Theme.secondaryText; font.pixelSize: 12 }
        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }
        Text { text: "Tracks"; color: Theme.text; font.pixelSize: 17; font.weight: Font.DemiBold }
        ListView {
            id: artistTracks
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 2
            model: root.selectedArtist ? root.selectedArtist.tracks : []
            ScrollBar.vertical: ScrollBar { }
            delegate: Rectangle {
                required property var modelData
                required property int index
                width: artistTracks.width
                height: 48
                radius: 9
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 12
                    Text { Layout.preferredWidth: 24; text: index + 1; color: Theme.mutedText; font.pixelSize: 11; horizontalAlignment: Text.AlignRight }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Text { Layout.fillWidth: true; text: modelData.title; color: Theme.text; font.pixelSize: 13; elide: Text.ElideRight }
                        Text { Layout.fillWidth: true; text: modelData.album.length > 0 ? modelData.album : modelData.artist; color: Theme.secondaryText; font.pixelSize: 11; elide: Text.ElideRight }
                    }
                    Text { text: modelData.durationMs > 0 ? Math.floor(modelData.durationMs / 60000) + ":" + ("0" + Math.floor((modelData.durationMs % 60000) / 1000)).slice(-2) : "—"; color: Theme.mutedText; font.pixelSize: 11; font.family: "monospace" }
                    ActionButton { text: "Play"; onClicked: Playback.playPaths(root.artistPaths(), false, modelData.path); Accessible.name: "Play " + modelData.title }
                }
                TapHandler { onDoubleTapped: Playback.playPaths(root.artistPaths(), false, modelData.path) }
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        visible: root.selectedArtist !== null && root.selectedAlbum !== null
        spacing: 12
        RowLayout {
            Layout.fillWidth: true
            ActionButton { text: "‹ " + (root.selectedArtist ? root.selectedArtist.name : "Artist"); onClicked: root.selectedAlbum = null }
            Item { Layout.fillWidth: true }
            ActionButton { text: "Play album"; primary: true; onClicked: Playback.playPaths(albumPaths(), false) }
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 176
            spacing: 16
            ArtworkTile { Layout.preferredWidth: 160; Layout.preferredHeight: 160; artworkUrl: root.selectedAlbum ? root.selectedAlbum.artworkUrl : ""; accentColor: root.selectedAlbum ? root.selectedAlbum.accentColor : ""; cornerRadius: 14 }
            ColumnLayout {
                Layout.fillWidth: true
                Text { Layout.fillWidth: true; text: root.selectedAlbum ? root.selectedAlbum.title : ""; color: Theme.text; font.pixelSize: 24; font.weight: Font.Bold; elide: Text.ElideRight }
                Text { text: root.selectedAlbum ? root.selectedAlbum.year > 0 ? String(root.selectedAlbum.year) : root.selectedAlbum.tracks.length + " tracks" : ""; color: Theme.secondaryText; font.pixelSize: 12 }
                Item { Layout.fillHeight: true }
            }
        }
        ListView {
            id: artistAlbumTracks
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: root.selectedAlbum ? root.selectedAlbum.tracks : []
            delegate: Rectangle {
                required property var modelData
                required property int index
                property bool showDiscHeader: root.selectedAlbum && root.hasMultipleDiscs(root.selectedAlbum.tracks)
                                              && (index === 0 || root.discNumber(modelData) !== root.discNumber(root.selectedAlbum.tracks[index - 1]))
                width: artistAlbumTracks.width
                height: showDiscHeader ? 68 : 48
                Text { visible: albumTrackRow.showDiscHeader; anchors.left: parent.left; anchors.leftMargin: 12; anchors.top: parent.top; anchors.topMargin: 3; text: "Disc " + root.discNumber(albumTrackRow.modelData); color: Theme.mutedText; font.pixelSize: 10; font.weight: Font.DemiBold }
                id: albumTrackRow
                RowLayout {
                    anchors.fill: parent
                    anchors.topMargin: albumTrackRow.showDiscHeader ? 18 : 0
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    Text { Layout.preferredWidth: 24; text: modelData.trackNumber > 0 ? modelData.trackNumber : index + 1; color: Theme.mutedText }
                    Text { Layout.fillWidth: true; text: modelData.title; color: Theme.text; font.pixelSize: 13; elide: Text.ElideRight }
                    Text { text: modelData.durationMs > 0 ? Math.floor(modelData.durationMs / 60000) + ":" + ("0" + Math.floor((modelData.durationMs % 60000) / 1000)).slice(-2) : "—"; color: Theme.mutedText; font.family: "monospace" }
                    ActionButton { text: "Play"; onClicked: Playback.playPaths(albumPaths(), false, modelData.path); Accessible.name: "Play " + modelData.title }
                }
                TapHandler { onDoubleTapped: Playback.playPaths(albumPaths(), false, modelData.path) }
            }
        }
    }

    function albumPaths() {
        const paths = []
        if (selectedAlbum) {
            for (let i = 0; i < selectedAlbum.tracks.length; ++i)
                paths.push(selectedAlbum.tracks[i].path)
        }
        return paths
    }
}
