import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import QtQuick.Dialogs
import Sonora

ApplicationWindow {
    id: window
    width: 1280
    height: 820
    minimumWidth: 760
    minimumHeight: 560
    visible: true
    title: "Sonora"
    color: Theme.background
    property int selectedIndex: 0
    property bool compactSidebar: width < 930
    property bool opaqueSurfaces: false

    ListModel {
        id: destinations
        ListElement { label: "Listen Now"; glyph: "◉"; heading: "Listen Now"; detail: "Browse and play music from your local collection."; emptyGlyph: "♫" }
        ListElement { label: "Songs"; glyph: "♪"; heading: "Songs"; detail: "Songs from your indexed folders."; emptyGlyph: "♪" }
        ListElement { label: "Albums"; glyph: "▣"; heading: "Albums"; detail: "Album browsing will follow in Phase 4."; emptyGlyph: "▣" }
        ListElement { label: "Artists"; glyph: "♙"; heading: "Artists"; detail: "Artists will appear here when Sonora has read real track metadata from your local library."; emptyGlyph: "♙" }
        ListElement { label: "Playlists"; glyph: "≡"; heading: "Playlists"; detail: "Playlist creation and editing are planned after library indexing and playback are in place."; emptyGlyph: "≡" }
        ListElement { label: "Queue"; glyph: "☷"; heading: "Queue"; detail: "Queue management is planned for Phase 5."; emptyGlyph: "☷" }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: window.compactSidebar ? 76 : 252
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
                    Layout.bottomMargin: 32
                    spacing: 11
                    Rectangle {
                        Layout.preferredWidth: 38
                        Layout.preferredHeight: 38
                        radius: 12
                        color: Theme.accent
                        Text {
                            anchors.centerIn: parent
                            text: "♫"
                            color: Theme.dark ? "#17121f" : "#ffffff"
                            font.pixelSize: 22
                            font.weight: Font.DemiBold
                        }
                    }
                    Column {
                        visible: !window.compactSidebar
                        spacing: 1
                        Text { text: "Sonora"; color: Theme.text; font.pixelSize: 17; font.weight: Font.Bold }
                        Text { text: "LOCAL MUSIC"; color: Theme.mutedText; font.pixelSize: 9; font.weight: Font.DemiBold; font.letterSpacing: 1.4 }
                    }
                }

                Text {
                    visible: !window.compactSidebar
                    Layout.leftMargin: 12
                    Layout.bottomMargin: 10
                    text: "YOUR SPACE"
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
                        glyph: model.glyph
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
                    glyph: "⚙"
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
                anchors.leftMargin: window.compactSidebar ? 26 : 42
                anchors.rightMargin: window.compactSidebar ? 26 : 42
                anchors.topMargin: 28
                anchors.bottomMargin: 20
                spacing: 0

                RowLayout {
                    Layout.fillWidth: true
                    Layout.bottomMargin: 24
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 5
                        Text {
                            text: window.selectedIndex < destinations.count ? destinations.get(window.selectedIndex).heading : "Settings"
                            color: Theme.text
                            font.pixelSize: 29
                            font.weight: Font.Bold
                        }
                        Text {
                            text: window.selectedIndex < destinations.count ? "Your music, on your terms." : "Make Sonora feel like yours."
                            color: Theme.secondaryText
                            font.pixelSize: 13
                        }
                    }
                    Rectangle {
                        Layout.preferredWidth: 42
                        Layout.preferredHeight: 42
                        radius: 21
                        color: Theme.elevated
                        border.width: 1
                        border.color: Theme.border
                        Text { anchors.centerIn: parent; text: "S"; color: Theme.accent; font.pixelSize: 15; font.weight: Font.DemiBold }
                    }
                }

                StackLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    currentIndex: window.selectedIndex

                    Item {
                        ColumnLayout {
                            anchors.centerIn: parent
                            width: Math.min(parent.width - 48, 520)
                            spacing: 14
                            Text {
                                Layout.fillWidth: true
                                text: Library.tracks.count > 0 ? "Your library is ready" : "A quieter kind of listening"
                                color: Theme.text
                                font.pixelSize: 24
                                font.weight: Font.DemiBold
                                horizontalAlignment: Text.AlignHCenter
                            }
                            Text {
                                Layout.fillWidth: true
                                text: Library.tracks.count > 0
                                      ? Library.tracks.count + (Library.tracks.count === 1 ? " song is" : " songs are") + " indexed from your folders."
                                      : "Choose a local music folder from Songs or Settings to start building your library. Sonora works with your files and does not change them."
                                color: Theme.secondaryText
                                font.pixelSize: 14
                                wrapMode: Text.WordWrap
                                horizontalAlignment: Text.AlignHCenter
                            }
                            Button {
                                Layout.alignment: Qt.AlignHCenter
                                visible: Library.tracks.count > 0
                                text: "Browse songs"
                                onClicked: window.selectedIndex = 1
                                contentItem: Text { text: parent.text; color: Theme.dark ? "#17121f" : "#ffffff"; font.pixelSize: 13; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                background: Rectangle { radius: 12; color: Theme.accent }
                                implicitWidth: 136
                                implicitHeight: 42
                            }
                        }
                    }

                    SongsPage {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        onAddFolderRequested: folderDialog.open()
                    }

                    EmptyPage { Layout.fillWidth: true; Layout.fillHeight: true; heading: "Albums arrive in Phase 4"; detail: "Sonora is indexing your songs now. Album grouping will be built from their real metadata."; glyph: "▣" }
                    EmptyPage { Layout.fillWidth: true; Layout.fillHeight: true; heading: "Artists arrive in Phase 4"; detail: "Artist views will be based on metadata from your local library."; glyph: "♙" }
                    EmptyPage { Layout.fillWidth: true; Layout.fillHeight: true; heading: "Playlists arrive in Phase 5"; detail: "Playlist editing will be added after the library and player workflows are stable."; glyph: "≡" }
                    EmptyPage { Layout.fillWidth: true; Layout.fillHeight: true; heading: "Queue management arrives in Phase 5"; detail: "Playback works from the Songs page. A managed, reorderable queue is a later milestone."; glyph: "☷" }

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
                    Layout.preferredHeight: 76
                    Layout.topMargin: 18
                    radius: Theme.radiusMedium
                    color: window.opaqueSurfaces ? Theme.elevated : Theme.glass
                    border.width: 1
                    border.color: Theme.border

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 16
                        anchors.rightMargin: 20
                        spacing: 13
                        Rectangle {
                            Layout.preferredWidth: 46
                            Layout.preferredHeight: 46
                            radius: 11
                            color: Theme.accentSoft
                            Text { anchors.centerIn: parent; text: "♫"; color: Theme.accent; font.pixelSize: 21 }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 3
                            Text { text: "Nothing playing"; color: Theme.text; font.pixelSize: 13; font.weight: Font.DemiBold }
                            Text { text: "Playback controls will arrive with Phase 3"; color: Theme.secondaryText; font.pixelSize: 11 }
                        }
                        Text {
                            text: "PLAYER PREVIEW"
                            color: Theme.mutedText
                            font.pixelSize: 9
                            font.weight: Font.DemiBold
                            font.letterSpacing: 1.2
                            visible: !window.compactSidebar
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
