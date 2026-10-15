import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import QtQuick.Dialogs
import Sonora

ApplicationWindow {
    id: window
    width: 1360
    height: 860
    minimumWidth: 760
    minimumHeight: 560
    visible: true
    title: "Sonora"
    color: Theme.background
    property int selectedIndex: 0
    property bool compactSidebar: width < 900
    property bool opaqueSurfaces: false

    function formatTime(milliseconds) {
        const seconds = Math.floor(Math.max(0, milliseconds) / 1000)
        return Math.floor(seconds / 60) + ":" + ("0" + (seconds % 60)).slice(-2)
    }

    ListModel {
        id: destinations
        ListElement { label: "Listen Now"; iconCode: 0xe405; heading: "Listen Now" }
        ListElement { label: "Songs"; iconCode: 0xe030; heading: "Songs" }
        ListElement { label: "Albums"; iconCode: 0xe019; heading: "Albums" }
        ListElement { label: "Artists"; iconCode: 0xe7fd; heading: "Artists" }
        ListElement { label: "Playlists"; iconCode: 0xe03d; heading: "Playlists" }
        ListElement { label: "Queue"; iconCode: 0xe03c; heading: "Queue" }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: window.compactSidebar ? 72 : 236
            color: Theme.sidebar
            border.width: 0

            ColumnLayout {
                anchors.fill: parent
                anchors.leftMargin: window.compactSidebar ? 10 : 18
                anchors.rightMargin: window.compactSidebar ? 10 : 18
                anchors.topMargin: 23
                anchors.bottomMargin: 16
                spacing: 0

                RowLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: window.compactSidebar ? 0 : 4
                    Layout.bottomMargin: 35
                    spacing: 12
                    Rectangle {
                        Layout.preferredWidth: 40
                        Layout.preferredHeight: 40
                        radius: 14
                        color: Theme.accentSoft
                        MaterialIcon { anchors.centerIn: parent; codepoint: 0xe405; iconColor: Theme.accent; font.pixelSize: 23 }
                    }
                    Column {
                        visible: !window.compactSidebar
                        spacing: 1
                        Text { text: "Sonora"; color: Theme.text; font.pixelSize: 17; font.weight: Font.Bold }
                        Text { text: "YOUR MUSIC"; color: Theme.mutedText; font.family: Theme.fontFamily; font.pixelSize: 9; font.weight: Font.DemiBold; font.letterSpacing: 1.2 }
                    }
                }

                Text {
                    visible: !window.compactSidebar
                    Layout.leftMargin: 12
                    Layout.bottomMargin: 10
                    text: "LIBRARY"
                    color: Theme.mutedText
                    font.pixelSize: 10
                    font.weight: Font.DemiBold
                    font.letterSpacing: 1.4
                }

                Repeater {
                    model: destinations
                    delegate: NavButton {
                        Layout.fillWidth: true
                        label: model.label
                        iconCode: model.iconCode
                        selected: window.selectedIndex === index
                        compact: window.compactSidebar
                        onActivated: window.selectedIndex = index
                    }
                }

                Item { Layout.fillHeight: true }

                Rectangle {
                    visible: !window.compactSidebar
                    Layout.fillWidth: true
                    Layout.bottomMargin: 15
                    height: 1
                    color: Theme.border
                }

                NavButton {
                    Layout.fillWidth: true
                    label: "Settings"
                    iconCode: 0xe8b8
                    selected: window.selectedIndex === destinations.count
                    compact: window.compactSidebar
                    onActivated: window.selectedIndex = destinations.count
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Theme.background

            ColumnLayout {
                anchors.fill: parent
                anchors.leftMargin: window.compactSidebar ? 22 : 38
                anchors.rightMargin: window.compactSidebar ? 22 : 38
                anchors.topMargin: 30
                anchors.bottomMargin: 20
                spacing: 0

                RowLayout {
                    Layout.fillWidth: true
                    Layout.bottomMargin: 30
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 5
                        Text {
                            text: window.selectedIndex === 2 && albumsPage.selectedAlbum
                                  ? albumsPage.selectedAlbum.title
                                  : window.selectedIndex === 3 && artistsPage.selectedArtist
                                        ? (artistsPage.selectedAlbum ? artistsPage.selectedAlbum.title : artistsPage.selectedArtist.name)
                                        : window.selectedIndex < destinations.count ? destinations.get(window.selectedIndex).heading : "Settings"
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: 30
                            font.weight: Font.Bold
                        }
                        Text {
                            text: window.selectedIndex < destinations.count ? "A quiet home for the music you already own." : "Make Sonora feel like yours."
                            color: Theme.secondaryText
                            font.family: Theme.fontFamily
                            font.pixelSize: 13
                        }
                    }
                }

                StackLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    currentIndex: window.selectedIndex

                    Item {
                        ColumnLayout {
                            anchors.centerIn: parent
                            width: Math.min(parent.width - 48, 540)
                            spacing: 13
                            Rectangle {
                                Layout.alignment: Qt.AlignHCenter
                                Layout.preferredWidth: 68
                                Layout.preferredHeight: 68
                                radius: 24
                                color: Theme.accentSoft
                                MaterialIcon { anchors.centerIn: parent; codepoint: 0xe405; iconColor: Theme.accent; font.pixelSize: 33 }
                            }
                            Text {
                                Layout.fillWidth: true
                                visible: Library.tracks.count === 0
                                text: "Start with your music folder"
                                color: Theme.text
                                font.family: Theme.fontFamily
                                font.pixelSize: 25
                                font.weight: Font.DemiBold
                                horizontalAlignment: Text.AlignHCenter
                            }
                            Text {
                                Layout.fillWidth: true
                                visible: Library.tracks.count > 0
                                text: "Your library is ready"
                                color: Theme.text
                                font.family: Theme.fontFamily
                                font.pixelSize: 24
                                font.weight: Font.DemiBold
                                horizontalAlignment: Text.AlignHCenter
                            }
                            Text {
                                Layout.fillWidth: true
                                text: Library.tracks.count > 0
                                      ? Library.tracks.count + (Library.tracks.count === 1 ? " song is" : " songs are") + " indexed from your folders."
                                      : "Sonora will organize local audio files without moving or changing them."
                                color: Theme.secondaryText
                                font.family: Theme.fontFamily
                                font.pixelSize: 14
                                wrapMode: Text.WordWrap
                                horizontalAlignment: Text.AlignHCenter
                            }
                            Button {
                                Layout.alignment: Qt.AlignHCenter
                                visible: Library.tracks.count === 0
                                text: "Add a music folder"
                                onClicked: folderDialog.open()
                                contentItem: Text { text: parent.text; color: Theme.dark ? "#282317" : "#ffffff"; font.family: Theme.fontFamily; font.pixelSize: 13; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                background: Rectangle { radius: 13; color: Theme.accent }
                                implicitWidth: 174
                                implicitHeight: 42
                            }
                            Button {
                                Layout.alignment: Qt.AlignHCenter
                                visible: Library.tracks.count > 0
                                text: "Browse songs"
                                onClicked: window.selectedIndex = 1
                                contentItem: Text { text: parent.text; color: Theme.dark ? "#282317" : "#ffffff"; font.family: Theme.fontFamily; font.pixelSize: 13; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                background: Rectangle { radius: 13; color: Theme.accent }
                                implicitWidth: 144
                                implicitHeight: 42
                            }
                        }
                    }

                    SongsPage {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        onAddFolderRequested: folderDialog.open()
                    }

                    AlbumsPage { id: albumsPage; Layout.fillWidth: true; Layout.fillHeight: true }
                    ArtistsPage { id: artistsPage; Layout.fillWidth: true; Layout.fillHeight: true }
                    EmptyPage { Layout.fillWidth: true; Layout.fillHeight: true; heading: "Playlists arrive in Phase 5"; detail: "Playlist editing will be added after the library and player workflows are stable."; iconCode: 0xe03d }
                    EmptyPage { Layout.fillWidth: true; Layout.fillHeight: true; heading: "Queue management arrives in Phase 5"; detail: "Playback works from the Songs page. A managed, reorderable queue is a later milestone."; iconCode: 0xe03c }

                    Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        LibrarySettingsPage {
                            anchors.fill: parent
                            opaqueSurfaces: window.opaqueSurfaces
                            onOpaqueSurfacesChanged: window.opaqueSurfaces = opaqueSurfaces
                            onAddFolderRequested: folderDialog.open()
                        }
                    }
                }

                Rectangle {
                    id: playerSurface
                    Layout.fillWidth: true
                    Layout.preferredHeight: 82
                    Layout.topMargin: 17
                    radius: Theme.radiusLarge
                    color: window.opaqueSurfaces ? Theme.elevated : Theme.glass
                    border.width: 1
                    border.color: Theme.border

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 14
                        anchors.rightMargin: 18
                        spacing: 13
                        ArtworkTile {
                            Layout.preferredWidth: 46
                            Layout.preferredHeight: 46
                            artworkUrl: Playback.currentArtworkUrl
                            accentColor: Playback.currentAccentColor
                            cornerRadius: 13
                        }
                        ColumnLayout {
                            Layout.preferredWidth: window.compactSidebar ? 130 : 220
                            spacing: 3
                            Text {
                                Layout.fillWidth: true
                                text: Playback.hasTrack ? Playback.currentTitle : "Nothing playing"
                                color: Theme.text
                                font.family: Theme.fontFamily
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }
                            Text {
                                Layout.fillWidth: true
                                text: Playback.errorMessage.length > 0
                                      ? Playback.errorMessage
                                      : Playback.hasTrack
                                            ? (Playback.currentArtist.length > 0 ? Playback.currentArtist : "Unknown artist")
                                            : "Choose a song to start playback"
                                color: Playback.errorMessage.length > 0 ? Theme.error : Theme.secondaryText
                                font.family: Theme.fontFamily
                                font.pixelSize: 11
                                elide: Text.ElideRight
                            }
                        }

                        Button {
                            visible: !Playback.hasTrack
                            text: Library.tracks.count > 0 ? "Browse songs" : "Add folder"
                            onClicked: Library.tracks.count > 0 ? window.selectedIndex = 1 : folderDialog.open()
                            contentItem: Text {
                                text: parent.text
                                color: Theme.accent
                                font.family: Theme.fontFamily
                                font.pixelSize: 12
                                font.weight: Font.DemiBold
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            background: Rectangle { radius: 11; color: Theme.accentSoft }
                            implicitWidth: 112
                            implicitHeight: 38
                        }

                        RowLayout {
                            visible: Playback.hasTrack
                            spacing: 7
                            Button {
                                text: ""
                                onClicked: Playback.previous()
                                Accessible.name: "Previous track"
                                contentItem: MaterialIcon { codepoint: 0xe045; iconColor: Theme.text; font.pixelSize: 21 }
                                background: Rectangle { radius: 10; color: "transparent" }
                                implicitWidth: 36
                                implicitHeight: 38
                            }
                            Button {
                                text: ""
                                onClicked: Playback.togglePlayback()
                                Accessible.name: Playback.playing ? "Pause playback" : "Resume playback"
                                contentItem: MaterialIcon { codepoint: Playback.playing ? 0xe034 : 0xe037; iconColor: Theme.dark ? "#282317" : "#ffffff"; font.pixelSize: 23 }
                                background: Rectangle { radius: 14; color: Theme.accent }
                                implicitWidth: 46
                                implicitHeight: 46
                            }
                            Button {
                                text: ""
                                onClicked: Playback.next()
                                Accessible.name: "Next track"
                                contentItem: MaterialIcon { codepoint: 0xe044; iconColor: Theme.text; font.pixelSize: 21 }
                                background: Rectangle { radius: 10; color: "transparent" }
                                implicitWidth: 36
                                implicitHeight: 38
                            }
                        }

                        Text {
                            visible: Playback.hasTrack && !window.compactSidebar
                            text: window.formatTime(Playback.position)
                            color: Theme.secondaryText
                            font.pixelSize: 10
                            font.family: "monospace"
                        }
                        Slider {
                            visible: Playback.hasTrack
                            Layout.fillWidth: true
                            Layout.minimumWidth: 56
                            from: 0
                            to: Math.max(Playback.duration, 1)
                            value: Playback.position
                            enabled: Playback.hasTrack && Playback.duration > 0
                            onMoved: Playback.seek(value)
                            Accessible.name: "Seek position"
                        }
                        Text {
                            visible: Playback.hasTrack && !window.compactSidebar
                            text: window.formatTime(Playback.duration)
                            color: Theme.secondaryText
                            font.pixelSize: 10
                            font.family: "monospace"
                        }
                        RowLayout {
                            visible: Playback.hasTrack && !window.compactSidebar
                            spacing: 4
                            MaterialIcon { codepoint: 0xe050; iconColor: Theme.secondaryText; font.pixelSize: 19 }
                            Slider {
                                Layout.preferredWidth: 84
                                from: 0
                                to: 1
                                value: Playback.volume
                                onMoved: Playback.setVolume(value)
                                Accessible.name: "Volume"
                            }
                        }
                    }
                }
            }
        }
    }

    FolderDialog {
        id: folderDialog
        title: "Choose a music folder"
        onAccepted: Library.addFolder(selectedFolder.toLocalFile())
    }
}
