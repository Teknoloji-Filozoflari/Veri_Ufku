import QtQuick

Image {
    readonly property bool ready: status === Image.Ready
    source: "../../assets/branding/icon-128.png"
    width: 36
    height: 36
    fillMode: Image.PreserveAspectFit
    smooth: true
    mipmap: true
    Accessible.ignored: true
}
