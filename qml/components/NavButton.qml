import QtQuick
import QtQuick.Controls
import Sonora

Item {
    id: root
    required property string label
    required property string glyph
    required property bool selected
    property bool compact: false
    signal activated()

    implicitHeight: 44
    implicitWidth: 220

    Rectangle {
        anchors.fill: parent
        radius: 12
        color: root.selected ? Theme.accentSoft : (hit.containsMouse ? Theme.elevated : "transparent")
        border.width: root.selected || root.activeFocus ? 1 : 0
        border.color: root.activeFocus ? Theme.accent : Theme.border
        Behavior on color { ColorAnimation { duration: 130 } }
    }

    Row {
        anchors.fill: parent
        anchors.leftMargin: root.compact ? 0 : 12
        anchors.rightMargin: root.compact ? 0 : 10
        spacing: 12

        Item {
            width: 42
            height: 44
            Text {
                anchors.centerIn: parent
                text: root.glyph
                color: root.selected ? Theme.accent : Theme.secondaryText
                font.pixelSize: 19
                font.weight: Font.Medium
            }
        }
        Text {
            visible: !root.compact
            anchors.verticalCenter: parent.verticalCenter
            text: root.label
            color: root.selected ? Theme.text : Theme.secondaryText
            font.pixelSize: 14
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
