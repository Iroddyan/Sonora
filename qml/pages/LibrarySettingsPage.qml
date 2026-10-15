import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Sonora

Item {
    id: root
    signal addFolderRequested()

    ColumnLayout {
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter
        width: Math.min(parent.width, 920)
        height: parent.height
        spacing: 14

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 194
            radius: Theme.radiusLarge
            color: Theme.surface
            border.width: 1
            border.color: Theme.border
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 12
                Text { text: "Appearance"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 17; font.weight: Font.DemiBold }
                Text { text: "Choose a theme"; color: Theme.secondaryText; font.family: Theme.fontFamily; font.pixelSize: 12 }
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
                                font.family: Theme.fontFamily
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            background: Rectangle {
                                radius: 11
                                color: parent.checked ? Theme.accentSoft : Theme.elevated
                                border.width: parent.checked ? 1 : 0
                                border.color: parent.checked ? Theme.accent : Theme.border
                            }
                            implicitWidth: 100
                            implicitHeight: 40
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        Text { text: "Translucent surfaces"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 13; font.weight: Font.Medium }
                        Text { text: opaqueSurfaces ? "Solid panels are active." : "Subtle transparency is active where supported."; color: Theme.secondaryText; font.family: Theme.fontFamily; font.pixelSize: 11 }
                    }
                    Switch { checked: !opaqueSurfaces; onToggled: opaqueSurfaces = !checked; Accessible.name: "Translucent surfaces" }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(360, Math.max(150, parent.height - 208))
            radius: Theme.radiusLarge
            color: Theme.surface
            border.width: 1
            border.color: Theme.border
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 10
                RowLayout {
                    Layout.fillWidth: true
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        Text { text: "Music folders"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 17; font.weight: Font.DemiBold }
                        Text { text: "Removing a folder only removes its index from Sonora; your files stay where they are."; color: Theme.secondaryText; font.family: Theme.fontFamily; font.pixelSize: 11; wrapMode: Text.WordWrap }
                    }
                    Button {
                        text: "Add folder"
                        enabled: Library.ready && !Library.scanning
                        onClicked: addFolderRequested()
                        contentItem: Text { text: parent.text; color: Theme.dark ? "#282317" : "#ffffff"; font.family: Theme.fontFamily; font.pixelSize: 12; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        background: Rectangle { radius: 12; color: Theme.accent }
                        implicitWidth: 112
                        implicitHeight: 40
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    Text { Layout.fillWidth: true; text: Library.statusMessage; color: Library.errorMessage.length > 0 ? Theme.error : Theme.secondaryText; font.family: Theme.fontFamily; font.pixelSize: 11; elide: Text.ElideRight }
                    Button { visible: Library.folders.length > 0 && !Library.scanning; text: "Rescan"; onClicked: Library.rescanAll() }
                    Button { visible: Library.scanning; text: "Cancel scan"; onClicked: Library.cancelScan() }
                    BusyIndicator { visible: Library.scanning; running: visible; implicitWidth: 24; implicitHeight: 24 }
                }
                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: Library.folders
                    spacing: 4
                    ScrollBar.vertical: ScrollBar { }
                    delegate: Rectangle {
                        required property string modelData
                        width: ListView.view.width
                        height: 48
                        radius: 11
                        color: Theme.elevated
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 8
                            Text { Layout.fillWidth: true; text: modelData; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12; elide: Text.ElideMiddle }
                            Button { text: "Remove"; enabled: !Library.scanning; onClicked: Library.removeFolder(modelData) }
                        }
                    }
                        Text {
                        anchors.centerIn: parent
                        visible: Library.folders.length === 0
                        text: "Add a folder to start building your library."
                            color: Theme.mutedText
                            font.family: Theme.fontFamily
                            font.pixelSize: 13
                        }
                }
            }
        }
    }

    required property bool opaqueSurfaces
}
