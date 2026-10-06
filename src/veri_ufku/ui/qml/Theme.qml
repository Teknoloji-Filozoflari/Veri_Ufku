pragma Singleton
import QtQuick

QtObject {
    property SystemPalette systemPalette: SystemPalette {}
    readonly property bool systemDark: Application.styleHints.colorScheme === Qt.Dark || (Application.styleHints.colorScheme === Qt.Unknown && systemPalette.window.hslLightness < 0.5)
    readonly property bool dark: preferences && (preferences.theme === "dark" || (preferences.theme === "system" && systemDark))
    readonly property real scale: preferences ? preferences.textScale : 1
    readonly property color background: dark ? "#111827" : "#F4F6F8"
    readonly property color surface: dark ? "#1F2937" : "#FFFFFF"
    readonly property color text: dark ? "#F3F4F6" : "#17212B"
    readonly property color secondary: dark ? "#CBD5E1" : "#475569"
    readonly property color accent: dark ? "#8CC9E0" : "#245C74"
    readonly property color onAccent: dark ? "#111827" : "#FFFFFF"
    readonly property color border: dark ? "#64748B" : "#CBD5E1"
    readonly property color warning: dark ? "#FDE68A" : "#713F12"
    readonly property color warningSurface: dark ? "#422006" : "#FEF3C7"
    readonly property color error: dark ? "#FECACA" : "#991B1B"
    readonly property color errorSurface: dark ? "#450A0A" : "#FEF2F2"
    readonly property int xs: 4
    readonly property int sm: 8
    readonly property int md: 12
    readonly property int lg: 16
    readonly property int xl: 24
    readonly property int xxl: 32
    readonly property int radius: 6
    readonly property int body: Math.round(Math.max(14, Qt.application.font.pixelSize) * scale)
    readonly property int small: Math.round(12 * scale)
    readonly property int heading: Math.round(24 * scale)
    readonly property int subheading: Math.round(18 * scale)
    readonly property int controlHeight: Math.max(40, body + 24)
}
