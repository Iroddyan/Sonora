import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Sonora

Item {
    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            TextField {
                id: searchField
                Layout.fillWidth: true
                placeholderText: "Search songs, artists, albums…"
                placeholderTextColor: Theme.mutedText
                color: Theme.text
                selectByMouse: true
                onTextChanged: Library.tracks.setSearchText(text)
                background: Rectangle {
                    radius: 12
                    color: Theme.surface
                    border.width: 1
                    border.color: searchField.activeFocus ? Theme.accent : Theme.border
                }
                leftPadding: 14
                rightPadding: 14
            }
            Button {
                text: "Add folder"
                enabled: Library.ready && !Library.scanning
                onClicked: addFolderRequested()
                contentItem: Text {
                    text: parent.text
                    color: Theme.dark ? "#17121f" : "#ffffff"
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle { radius: 12; color: Theme.accent }
                implicitWidth: 112
                implicitHeight: 40
            }
            Button {
                visible: Library.folders.length > 0 && !Library.scanning
                text: "Rescan"
                onClicked: Library.rescanAll()
                contentItem: Text {
                    text: parent.text
                    color: Theme.text
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle { radius: 12; color: Theme.elevated; border.width: 1; border.color: Theme.border }
                implicitWidth: 84
                implicitHeight: 40
            }
            Button {
                visible: Library.scanning
                text: "Cancel"
                onClicked: Library.cancelScan()
                contentItem: Text {
                    text: parent.text
                    color: Theme.text
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle { radius: 12; color: Theme.elevated; border.width: 1; border.color: Theme.border }
                implicitWidth: 84
                implicitHeight: 40
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            BusyIndicator { running: Library.scanning; visible: running; implicitWidth: 20; implicitHeight: 20 }
            Text {
                Layout.fillWidth: true
                text: Playback.errorMessage.length > 0 ? Playback.errorMessage : Library.statusMessage
                color: Library.errorMessage.length > 0 || Playback.errorMessage.length > 0 ? Theme.error : Theme.secondaryText
                font.pixelSize: 12
                elide: Text.ElideRight
            }
            Text {
                visible: Library.tracks.count > 0
                text: Library.tracks.count + (Library.tracks.count === 1 ? " track" : " tracks")
                color: Theme.mutedText
                font.pixelSize: 11
            }
        }

        Text {
            Layout.fillWidth: true
            visible: Library.errorMessage.length > 0
            text: Library.errorMessage
            color: Theme.error
            font.pixelSize: 11
            wrapMode: Text.Wrap
            maximumLineCount: 3
            elide: Text.ElideRight
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout {
                anchors.centerIn: parent
                width: Math.min(parent.width - 40, 420)
                spacing: 12
                visible: Library.tracks.count === 0
                Text {
                    Layout.fillWidth: true
                    text: Library.folders.length === 0 ? "Start with a music folder" : (Library.scanning ? "Building your library" : "No supported audio files found")
                    color: Theme.text
                    font.pixelSize: 20
                    font.weight: Font.DemiBold
                    horizontalAlignment: Text.AlignHCenter
                }
                Text {
                    Layout.fillWidth: true
                    text: Library.folders.length === 0
                          ? "Sonora indexes local files only. Choose a folder to scan MP3, FLAC, M4A, AAC, Ogg, Opus, or WAV files."
                          : (Library.scanning ? "Files are inspected in the background. You can cancel without saving partial results." : "The selected folders are indexed, but no supported audio files were found.")
                    color: Theme.secondaryText
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignHCenter
                }
                Button {
                    Layout.alignment: Qt.AlignHCenter
                    visible: Library.folders.length === 0 && !Library.scanning
                    text: "Choose music folder"
                    onClicked: addFolderRequested()
                    contentItem: Text {
                        text: parent.text
                        color: Theme.dark ? "#17121f" : "#ffffff"
                        font.pixelSize: 13
                        font.weight: Font.DemiBold
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle { radius: 12; color: Theme.accent }
                    implicitWidth: 172
                    implicitHeight: 42
                }
            }

            ListView {
                id: tracksList
                anchors.fill: parent
                visible: Library.tracks.count > 0
                clip: true
                spacing: 3
                model: Library.tracks
                ScrollBar.vertical: ScrollBar { }

                delegate: Rectangle {
                    id: trackRow
                    required property string path
                    required property string title
                    required property string artist
                    required property string album
                    required property int durationMs
                    required property int index

                    width: tracksList.width
                    height: 58
                    radius: 10
                    color: rowMouse.containsMouse ? Theme.surface : "transparent"

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 16
                        spacing: 12
                        Rectangle {
                            Layout.preferredWidth: 34
                            Layout.preferredHeight: 34
                            radius: 9
                            color: Theme.accentSoft
                            MaterialIcon { anchors.centerIn: parent; codepoint: 0xe030; iconColor: Theme.accent; font.pixelSize: 18 }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 3
                            Text { Layout.fillWidth: true; text: trackRow.title; color: Theme.text; font.pixelSize: 13; font.weight: Font.Medium; elide: Text.ElideRight }
                            Text { Layout.fillWidth: true; text: trackRow.artist.length > 0 ? trackRow.artist : "Unknown artist"; color: Theme.secondaryText; font.pixelSize: 11; elide: Text.ElideRight }
                        }
                        Text {
                            Layout.preferredWidth: 170
                            visible: trackRow.width > 760
                            text: trackRow.album.length > 0 ? trackRow.album : "—"
                            color: Theme.secondaryText
                            font.pixelSize: 12
                            elide: Text.ElideRight
                        }
                        Text {
                            text: trackRow.durationMs > 0
                                  ? Math.floor(trackRow.durationMs / 60000) + ":" + ("0" + Math.floor((trackRow.durationMs % 60000) / 1000)).slice(-2)
                                  : "—"
                            color: Theme.mutedText
                            font.pixelSize: 11
                            font.family: "monospace"
                        }
                        Button {
                            text: ""
                            onClicked: Playback.playPath(trackRow.path)
                            Accessible.name: "Play " + trackRow.title
                            contentItem: MaterialIcon { codepoint: 0xe037; iconColor: Theme.accent; font.pixelSize: 19 }
                            background: Rectangle { radius: 10; color: Theme.accentSoft }
                            implicitWidth: 34
                            implicitHeight: 34
                        }
                    }
                    MouseArea {
                        id: rowMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        acceptedButtons: Qt.NoButton
                    }
                }
            }

            Text {
                anchors.centerIn: parent
                visible: Library.tracks.count > 0 && tracksList.count === 0
                text: "No songs match your search."
                color: Theme.secondaryText
                font.pixelSize: 13
            }
        }
    }

    signal addFolderRequested()
}
