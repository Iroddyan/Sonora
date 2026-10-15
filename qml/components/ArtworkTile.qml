import QtQuick
import QtQuick.Controls

Rectangle {
    id: tile
    property string artworkUrl: ""
    property string accentColor: ""
    property real cornerRadius: 12
    color: accentColor.length > 0 ? Qt.darker(accentColor, 1.6) : Theme.elevated
    radius: cornerRadius
    clip: true
    border.width: 1
    border.color: Theme.border

    Image {
        id: artwork
        anchors.fill: parent
        source: tile.artworkUrl
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        cache: true
        sourceSize.width: Math.ceil(width * Screen.devicePixelRatio)
        sourceSize.height: Math.ceil(height * Screen.devicePixelRatio)
        visible: status === Image.Ready
    }

    Text {
        anchors.centerIn: parent
        visible: artwork.status !== Image.Ready
        text: "♫"
        color: tile.accentColor.length > 0 ? tile.accentColor : Theme.accent
        font.pixelSize: Math.max(30, Math.min(tile.width, tile.height) * 0.36)
        font.weight: Font.Light
    }
}
