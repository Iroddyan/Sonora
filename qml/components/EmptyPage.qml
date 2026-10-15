import QtQuick
import Sonora

Item {
    id: root
    required property string heading
    required property string detail
    required property int iconCode

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(parent.width - 48, 560)
        height: 270
        radius: Theme.radiusLarge
        color: "transparent"

        Column {
            anchors.centerIn: parent
            width: parent.width - 64
            spacing: 15
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 64
                height: 64
                radius: 22
                color: Theme.accentSoft
                MaterialIcon { anchors.centerIn: parent; codepoint: root.iconCode; iconColor: Theme.accent; font.pixelSize: 31 }
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: heading
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: 21
                font.weight: Font.DemiBold
                horizontalAlignment: Text.AlignHCenter
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width
                text: detail
                color: Theme.secondaryText
                font.family: Theme.fontFamily
                font.pixelSize: 14
                lineHeight: 1.35
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }
}
