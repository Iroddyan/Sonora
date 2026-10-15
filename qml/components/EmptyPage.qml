import QtQuick
import Sonora

Item {
    required property string heading
    required property string detail
    required property string glyph

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(parent.width - 48, 560)
        height: 320
        radius: Theme.radiusLarge
        color: Theme.surface
        border.width: 1
        border.color: Theme.border

        Column {
            anchors.centerIn: parent
            width: parent.width - 64
            spacing: 14
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: glyph
                color: Theme.accent
                font.pixelSize: 38
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: heading
                color: Theme.text
                font.pixelSize: 21
                font.weight: Font.DemiBold
                horizontalAlignment: Text.AlignHCenter
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width
                text: detail
                color: Theme.secondaryText
                font.pixelSize: 14
                lineHeight: 1.35
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }
}
