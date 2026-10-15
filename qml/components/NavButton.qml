import QtQuick
import QtQuick.Controls
import Sonora

Item {
    id: root
    required property string label
    required property int iconCode
    required property bool selected
    property bool compact: false
    signal activated()

    implicitHeight: 46
    implicitWidth: 220

    Rectangle {
        anchors.fill: parent
        radius: 13
        color: root.selected ? Theme.accentSoft : (hit.containsMouse ? Theme.elevated : "transparent")
        border.width: root.activeFocus ? 1 : 0
        border.color: Theme.accent
        Behavior on color { ColorAnimation { duration: 130 } }
    }

    Row {
        anchors.fill: parent
        anchors.leftMargin: root.compact ? 0 : 12
        anchors.rightMargin: root.compact ? 0 : 10
        spacing: 10

        Item {
            width: 38
            height: 46
            MaterialIcon {
                anchors.centerIn: parent
                codepoint: root.iconCode
                iconColor: root.selected ? Theme.accent : Theme.secondaryText
                font.pixelSize: 21
            }
        }
        Text {
            visible: !root.compact
            anchors.verticalCenter: parent.verticalCenter
            text: root.label
            color: root.selected ? Theme.text : Theme.secondaryText
            font.family: Theme.fontFamily
            font.pixelSize: 13
            font.weight: root.selected ? Font.DemiBold : Font.Medium
            elide: Text.ElideRight
        }
    }

    ToolTip.visible: root.compact && hit.containsMouse
    ToolTip.text: root.label
    ToolTip.delay: 500

    MouseArea {
        id: hit
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton
        cursorShape: Qt.PointingHandCursor
        onClicked: root.activated()
        Accessible.role: Accessible.Button
        Accessible.name: root.label
        Accessible.checked: root.selected
    }
    Keys.onReturnPressed: root.activated()
    Keys.onSpacePressed: root.activated()
    activeFocusOnTab: true
}
