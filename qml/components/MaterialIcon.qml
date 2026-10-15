import QtQuick
import Sonora

Text {
    id: root
    property int codepoint: 0xe88a
    property color iconColor: Theme.secondaryText
    text: String.fromCharCode(codepoint)
    color: iconColor
    font.family: Theme.iconFamily
    font.pixelSize: 20
    horizontalAlignment: Text.AlignHCenter
    verticalAlignment: Text.AlignVCenter
    renderType: Text.NativeRendering
}
