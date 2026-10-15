import QtQuick
import QtQuick.Controls

Button {
    id: control
    property bool primary: false
    implicitHeight: 38
    leftPadding: 13
    rightPadding: 13
    contentItem: Text {
        text: control.text
        color: control.primary ? (Theme.dark ? "#17121f" : "#ffffff") : Theme.text
        font.pixelSize: 12
        font.weight: Font.DemiBold
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    background: Rectangle {
        radius: 10
        color: control.primary ? Theme.accent
                               : control.down ? Theme.accentSoft
                                              : control.hovered ? Theme.surface : Theme.elevated
        border.width: control.primary ? 0 : 1
        border.color: Theme.border
    }
}
