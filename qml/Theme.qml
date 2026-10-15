pragma Singleton
import QtQuick

QtObject {
    property bool dark: true

    readonly property string fontFamily: "Noto Sans"
    readonly property string iconFamily: "Material Icons"
    readonly property color background: dark ? "#121510" : "#f5f3ed"
    readonly property color sidebar: dark ? "#171b15" : "#ebe9e0"
    readonly property color surface: dark ? "#1c211a" : "#fbfaf5"
    readonly property color elevated: dark ? "#242a21" : "#ffffff"
    readonly property color glass: dark ? "#df20271e" : "#e8fffef8"
    readonly property color text: dark ? "#f1f2e9" : "#272a23"
    readonly property color secondaryText: dark ? "#a8afa0" : "#64685e"
    readonly property color mutedText: dark ? "#778071" : "#898c80"
    readonly property color accent: dark ? "#d8bd83" : "#765a2d"
    readonly property color accentSoft: dark ? "#342f2417" : "#e9dfc9"
    readonly property color border: dark ? "#30382d" : "#dedbd0"
    readonly property color shadow: dark ? "#66000000" : "#180d1208"
    readonly property color success: dark ? "#9acb9a" : "#287d46"
    readonly property color warning: dark ? "#e5bf78" : "#8d610f"
    readonly property color error: dark ? "#e99589" : "#a2382d"
    readonly property int radiusSmall: 9
    readonly property int radiusMedium: 14
    readonly property int radiusLarge: 20
}
