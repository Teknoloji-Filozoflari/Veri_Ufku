pragma Singleton
import QtQuick

QtObject {
    readonly property bool dark: !preferences || preferences.theme !== "light"
    readonly property real scale: 1
    readonly property color background: dark ? "#10151C" : "#F5F7FA"
    readonly property color surface: dark ? "#1B2330" : "#FFFFFF"
    readonly property color text: dark ? "#F4F7FB" : "#1C2838"
    readonly property color secondary: dark ? "#B7C3D4" : "#4E5E74"
    readonly property color accent: dark ? "#9DC4FF" : "#1F4E79"
    readonly property color accentText: dark ? "#0C1B33" : "#FFFFFF"
    readonly property color action: accent
    readonly property color actionText: accentText
    readonly property color actionHover: dark ? "#C5DCFF" : "#173E61"
    readonly property color actionPressed: dark ? "#7EB0F5" : "#14324F"
    readonly property color border: dark ? "#344155" : "#D5DEE8"
    readonly property color chrome: dark ? "#171E29" : "#FFFFFF"
    readonly property color raised: dark ? "#253145" : "#E7EEF6"
    readonly property color field: dark ? "#131C29" : "#FFFFFF"
    readonly property color hover: dark ? "#2D3D52" : "#E3EBF4"
    readonly property color alternateRow: dark ? "#1E2938" : "#F4F7FB"
    readonly property color accentSoft: dark ? "#1A2C44" : "#E7F0FA"
    readonly property color accentHover: actionHover
    readonly property color accentPressed: actionPressed
    readonly property color controlBorder: dark ? "#7D88A2" : "#6A7C92"
    readonly property color muted: dark ? "#919CAD" : "#54657A"
    readonly property color dataTone: dark ? "#94C9DF" : "#18536D"
    readonly property color prepareTone: dark ? "#C3A6EF" : "#66379D"
    readonly property color modelTone: dark ? "#C3A6EF" : "#66379D"
    readonly property color reportTone: dark ? "#D9C28C" : "#6B5419"
    readonly property color learningTone: dark ? "#91D7B2" : "#20603F"
    readonly property color violetSurface: dark ? "#30273F" : "#EEE5F7"
    readonly property color violetHover: dark ? "#D2B9FA" : "#572E85"
    readonly property color violetPressed: dark ? "#AE8DD9" : "#49266F"
    readonly property color mintSurface: dark ? "#20372F" : "#E0F1E7"
    readonly property color mintHover: dark ? "#ADE9C7" : "#194F34"
    readonly property color mintPressed: dark ? "#79BD99" : "#143F2A"
    readonly property color cyanSurface: dark ? "#223541" : "#E2F0F5"
    readonly property color cyanHover: dark ? "#B2E0ED" : "#12455A"
    readonly property color cyanPressed: dark ? "#79ADC3" : "#103849"
    function toneColor(tone) {
        return tone === "violet" ? modelTone : tone === "mint" ? learningTone : tone === "cyan" ? dataTone : accent
    }
    function toneSurface(tone) {
        return tone === "violet" ? violetSurface : tone === "mint" ? mintSurface : tone === "cyan" ? cyanSurface : accentSoft
    }
    function toneHover(tone) {
        return tone === "violet" ? violetHover : tone === "mint" ? mintHover : tone === "cyan" ? cyanHover : accentHover
    }
    function tonePressed(tone) {
        return tone === "violet" ? violetPressed : tone === "mint" ? mintPressed : tone === "cyan" ? cyanPressed : accentPressed
    }
    readonly property color warning: dark ? "#FDE68A" : "#694400"
    readonly property color warningSurface: dark ? "#422006" : "#FFF0C2"
    readonly property color error: dark ? "#FECACA" : "#8C1C1C"
    readonly property color errorSurface: dark ? "#450A0A" : "#FFE7E7"
    readonly property int xs: 4
    readonly property int sm: 8
    readonly property int md: 12
    readonly property int lg: 16
    readonly property int xl: 24
    readonly property int xxl: 32
    readonly property int radius: 6
    readonly property int body: Math.round(14 * scale)
    readonly property int small: Math.round(12 * scale)
    readonly property int heading: Math.round(24 * scale)
    readonly property int subheading: Math.round(18 * scale)
    readonly property int controlHeight: Math.max(40, body + 24)
}
