pragma Singleton
import QtQuick

QtObject {
    property bool dark: true

    readonly property color background: dark ? "#111317" : "#f4f5f7"
    readonly property color sidebar: dark ? "#15171c" : "#eceef2"
    readonly property color surface: dark ? "#1a1d23" : "#ffffff"
    readonly property color elevated: dark ? "#22262e" : "#ffffff"
    readonly property color glass: dark ? "#df1c2028" : "#e8ffffff"
    readonly property color text: dark ? "#f3f4f6" : "#20232a"
    readonly property color secondaryText: dark ? "#a0a5b0" : "#656b76"
    readonly property color mutedText: dark ? "#737985" : "#9298a3"
    readonly property color accent: dark ? "#c4a7ff" : "#6846bd"
    readonly property color accentSoft: dark ? "#332b4050" : "#e8e0fa"
    readonly property color border: dark ? "#2b3039" : "#dfe2e8"
    readonly property color shadow: dark ? "#66000000" : "#180c1020"
    readonly property color success: dark ? "#81c995" : "#287d46"
    readonly property color warning: dark ? "#f6c177" : "#9a6500"
    readonly property color error: dark ? "#ff8b8b" : "#b3261e"
    readonly property int radiusSmall: 10
    readonly property int radiusMedium: 16
    readonly property int radiusLarge: 22
}
