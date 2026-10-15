import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
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
        ListElement { label: "Listen Now"; glyph: "◉"; heading: "Listen Now"; detail: "Your listening space is ready. Once your local library is indexed, recent and favorite music will appear here. Library setup arrives in Phase 2."; emptyGlyph: "♫" }
        ListElement { label: "Songs"; glyph: "♪"; heading: "Songs"; detail: "Your songs will appear here after you choose a music folder and Sonora indexes its contents in Phase 2."; emptyGlyph: "♪" }
        ListElement { label: "Albums"; glyph: "▣"; heading: "Albums"; detail: "Albums will be grouped from the music files in your library. No sample or placeholder albums are shown."; emptyGlyph: "▣" }
        ListElement { label: "Artists"; glyph: "♙"; heading: "Artists"; detail: "Artists will appear here when Sonora has read real track metadata from your local library."; emptyGlyph: "♙" }
        ListElement { label: "Playlists"; glyph: "≡"; heading: "Playlists"; detail: "Playlist creation and editing are planned after library indexing and playback are in place."; emptyGlyph: "≡" }
        ListElement { label: "Queue"; glyph: "☷"; heading: "Queue"; detail: "The queue will be connected to real playback in a later phase. No tracks are queued in this shell."; emptyGlyph: "☷" }
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

                    Repeater {
                        model: destinations
                        delegate: EmptyPage {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            heading: model.heading === "Listen Now" ? "A quieter kind of listening" : "Nothing here yet"
                            detail: model.detail
                            glyph: model.emptyGlyph
                        }
                    }

                    Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Rectangle {
                            anchors.top: parent.top
                            anchors.left: parent.left
                            anchors.right: parent.right
                            height: Math.min(parent.height, 390)
                            radius: Theme.radiusLarge
                            color: Theme.surface
                            border.width: 1
                            border.color: Theme.border
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 24
                                spacing: 16
                                Text { text: "Appearance"; color: Theme.text; font.pixelSize: 18; font.weight: Font.DemiBold }
                                Text { text: "Choose a theme"; color: Theme.secondaryText; font.pixelSize: 13 }
                                RowLayout {
                                    spacing: 10
                                    Repeater {
                                        model: [{ label: "Dark", value: true }, { label: "Light", value: false }]
                                        delegate: Button {
                                            text: modelData.label
                                            checkable: true
                                            checked: Theme.dark === modelData.value
                                            onClicked: Theme.dark = modelData.value
                                            contentItem: Text {
                                                text: parent.text
                                                color: parent.checked ? Theme.accent : Theme.secondaryText
                                                font.pixelSize: 13
                                                font.weight: Font.DemiBold
                                                horizontalAlignment: Text.AlignHCenter
                                                verticalAlignment: Text.AlignVCenter
                                            }
                                            background: Rectangle {
                                                radius: 11
                                                color: parent.checked ? Theme.accentSoft : Theme.elevated
                                                border.width: 1
                                                border.color: parent.checked ? Theme.accent : Theme.border
                                            }
                                            implicitWidth: 100
                                            implicitHeight: 40
                                        }
                                    }
                                }
                                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border; Layout.topMargin: 2; Layout.bottomMargin: 2 }
                                RowLayout {
                                    Layout.fillWidth: true
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 4
                                        Text { text: "Translucent surfaces"; color: Theme.text; font.pixelSize: 14; font.weight: Font.Medium }
                                        Text { text: window.opaqueSurfaces ? "Solid panels are active." : "Subtle transparency is active where supported."; color: Theme.secondaryText; font.pixelSize: 12; wrapMode: Text.WordWrap }
                                    }
                                    Switch {
                                        checked: !window.opaqueSurfaces
                                        onToggled: window.opaqueSurfaces = !checked
                                        Accessible.name: "Translucent surfaces"
                                    }
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: "Switching this off uses opaque elevated surfaces throughout the shell for readability and reduced transparency."
                                    color: Theme.mutedText
                                    font.pixelSize: 12
                                    wrapMode: Text.WordWrap
                                }
                            }
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
}
