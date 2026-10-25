import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Popup {
    id: tour
    objectName: "firstRunTour"
    modal: true
    focus: true
    anchors.centerIn: Overlay.overlay
    width: Math.min(520 * Theme.scale, parent ? parent.width - 32 : 520)
    padding: Theme.lg
    closePolicy: Popup.CloseOnEscape
    background: Rectangle {
        color: Theme.surface
        radius: Theme.radius
        border.color: Theme.learningTone
    }

    ColumnLayout {
        width: tour.availableWidth
        spacing: Theme.md
        UiLabel {
            text: qsTr("Kısa tur (isteğe bağlı)")
            font.pixelSize: Theme.heading
            font.bold: true
            Layout.fillWidth: true
            wrapMode: Text.Wrap
        }
        UiLabel {
            text: qsTr("En fazla bir dakika. Turu kapatmak çalışmanı etkilemez; istediğin zaman yeniden açabilirsin.")
            color: Theme.secondary
            Layout.fillWidth: true
            wrapMode: Text.Wrap
        }
        UiLabel { text: "1. " + qsTr("Merkezdeki tablo ana yüzeyindir; sayfa tüm veri değildir."); Layout.fillWidth: true; wrapMode: Text.Wrap }
        UiLabel { text: "2. " + qsTr("Sağ bağlam panelinde sütunları seç ve «Bu adımı öğren»e bak."); Layout.fillWidth: true; wrapMode: Text.Wrap }
        UiLabel { text: "3. " + qsTr("Soldaki aşama şeridi yolculuktur; zorunlu sihirbaz değildir."); Layout.fillWidth: true; wrapMode: Text.Wrap }
        UiLabel {
            text: uxContent.draftStatus
            color: Theme.warning
            font.pixelSize: Theme.small
            Layout.fillWidth: true
            wrapMode: Text.Wrap
        }
        RowLayout {
            Layout.fillWidth: true
            UiButton {
                objectName: "tourDismissButton"
                text: qsTr("Anladım, bir daha gösterme")
                tone: "mint"
                Layout.fillWidth: true
                multiline: true
                onClicked: { uxContent.dismissTour(); tour.close() }
            }
            UiButton {
                objectName: "tourSkipButton"
                text: qsTr("Şimdilik atla")
                Layout.fillWidth: true
                multiline: true
                onClicked: { uxContent.closeTourKeepUnseen(); tour.close() }
            }
        }
    }
}
