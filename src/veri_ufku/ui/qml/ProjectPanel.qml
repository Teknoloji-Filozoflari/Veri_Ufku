import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Frame {
    id: panel
    objectName: "projectPanel"
    padding: Theme.lg
    implicitHeight: projectContent.implicitHeight + topPadding + bottomPadding
    signal helpRequested(var origin)
    property string targetAction: "create"
    property string relinkId: ""
    property bool pathRequestPending: false
    background: Rectangle { color: Theme.surface; border.color: Theme.border; radius: Theme.radius }
    ColumnLayout {
        id: projectContent
        width: panel.availableWidth
        enabled: !projects.busy
        spacing: Theme.md
        Label { text: "Projen"; font.pixelSize: Theme.subheading; font.bold: true }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.sm
            UiButton { objectName: "newProjectButton"; width: Math.min(implicitWidth, parent.width); multiline: true; helpContext: "project"; text: "Yeni proje"; onClicked: { panel.targetAction = "create"; pathDialog.open() } }
            UiButton { objectName: "openProjectButton"; width: Math.min(implicitWidth, parent.width); multiline: true; helpContext: "project"; text: "Proje aç"; onClicked: openDialog.open() }
            UiButton { objectName: "saveProjectButton"; width: Math.min(implicitWidth, parent.width); multiline: true; helpContext: "project"; text: "Kaydet"; primary: true; enabled: projects.opened && !projects.readOnly; onClicked: projects.request("save") }
            UiButton { objectName: "saveAsProjectButton"; width: Math.min(implicitWidth, parent.width); multiline: true; helpContext: "project"; text: "Farklı kaydet"; enabled: projects.opened; onClicked: { panel.targetAction = "saveAs"; pathDialog.open() } }
            UiButton { objectName: "closeProjectButton"; width: Math.min(implicitWidth, parent.width); multiline: true; helpContext: "project"; text: "Projeyi kapat"; enabled: projects.opened; onClicked: projects.closeProject(false) }
            UiButton { width: Math.min(implicitWidth, parent.width); multiline: true; helpContext: "project"; text: "Değişiklikleri bırak"; visible: projects.dirty; onClicked: discardDialog.open() }
            UiButton { objectName: "projectHelpButton"; width: Math.min(implicitWidth, parent.width); multiline: true; helpContext: "project"; text: "Bu ne işe yarar?"; onClicked: panel.helpRequested(this) }
        }
        Label { text: projects.context; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
        Label { text: projects.message; wrapMode: Text.WordWrap; Layout.fillWidth: true; color: Theme.secondary }
        Label { text: projects.errorText; visible: text.length > 0; wrapMode: Text.WordWrap; Layout.fillWidth: true; color: Theme.error }
        Label { text: "Proje adı"; visible: projects.opened }
        TextField {
            objectName: "projectNameField"
            Layout.fillWidth: true
            visible: projects.opened
            enabled: !projects.readOnly
            text: projects.name
            maximumLength: 200
            placeholderText: "Proje adı"
            Accessible.name: "Proje adı"
            onTextEdited: projects.setName(text)
        }
        Label { text: "Seed — tekrarlanabilir seçim için sayı (isteğe bağlı)"; visible: projects.opened; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        TextField {
            objectName: "projectSeedField"
            Layout.fillWidth: true
            visible: projects.opened
            enabled: !projects.readOnly
            text: projects.seedText
            placeholderText: "Seed — tekrarlanabilir seçim için sayı (isteğe bağlı)"
            Accessible.name: "Seed"
            onEditingFinished: projects.setSeed(text)
        }
        Label {
            text: "Kaynak referansı yalnız dosyanın yolunu ve içerik izini saklar; taşıma sırasında dosyayı ayrıca götürmelisin. Taşınabilir kopya dosyayı projeye ekler ve disk kullanır. Kaynak dosyana yazılmaz."
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.secondary
        }
        CheckBox { id: portable; Layout.fillWidth: true; contentItem: Label { text: portable.text; leftPadding: portable.indicator.width + portable.spacing; wrapMode: Text.WordWrap; color: Theme.text } text: "Kaynak dosyanın taşınabilir kopyasını ekle"; enabled: projects.opened && !projects.readOnly; palette.windowText: Theme.text }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.sm
            UiButton { objectName: "attachSourceButton"; width: Math.min(implicitWidth, parent.width); multiline: true; helpContext: "project.source"; text: "Kaynak dosyası bağla"; enabled: projects.opened && !projects.readOnly; onClicked: { panel.relinkId = ""; sourceDialog.open() } }
            UiButton { width: Math.min(implicitWidth, parent.width); multiline: true; helpContext: "project.source"; text: "Kaynak durumunu kontrol et"; enabled: projects.opened; onClicked: projects.refreshSources() }
            UiButton { objectName: "recoverLockButton"; width: Math.min(implicitWidth, parent.width); multiline: true; helpContext: "project.recovery"; text: "Eski kilidi kontrollü kurtar"; visible: projects.readOnly; onClicked: projects.request("recover") }
            UiButton { objectName: "restoreAutosaveButton"; width: Math.min(implicitWidth, parent.width); multiline: true; helpContext: "project.recovery"; text: "Kurtarma kaydını yükle"; enabled: projects.opened && !projects.readOnly; onClicked: recoveryDialog.open() }
        }
        Label { text: projects.sourceSummary; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
        Repeater {
            model: projects.sources
            UiButton {
                required property var modelData
                Layout.fillWidth: true
                multiline: true
                helpContext: "project.source"
                text: "Yeniden bağla: " + modelData.path
                enabled: !projects.readOnly
                onClicked: { panel.relinkId = modelData.id; sourceDialog.open() }
            }
        }
        Label { text: projects.resultSummary; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
        CheckBox { id: recoverOpen; Layout.fillWidth: true; contentItem: Label { text: recoverOpen.text; leftPadding: recoverOpen.indicator.width + recoverOpen.spacing; wrapMode: Text.WordWrap; color: Theme.text } text: "Önceki kilidi kurtararak aç (aktif yazıcı korunur)"; palette.windowText: Theme.text }
        Label { text: "Son projeler"; font.bold: true }
        Repeater {
            model: projects.recent
            UiButton { required property string modelData; Layout.fillWidth: true; multiline: true; text: modelData; helpContext: "project"; onClicked: projects.request("open", modelData) }
        }
    }
    Connections { target: projects; function onChanged() { if (panel.pathRequestPending && !projects.busy) { panel.pathRequestPending = false; if (!projects.errorText && projects.opened) pathDialog.close() } } }
    BusyIndicator { anchors.right: parent.right; running: projects.busy; visible: running }
    FolderDialog { id: openDialog; title: "Proje dizinini aç"; onAccepted: projects.request(recoverOpen.checked ? "openRecover" : "open", selectedFolder.toString()) }
    FolderDialog { id: locationDialog; title: "Yeni projenin oluşturulacağı klasörü seç"; onAccepted: projectPath.text = projects.newProjectPath(selectedFolder.toString()) }
    FileDialog { id: sourceDialog; title: panel.relinkId ? "Aynı kaynak veriyi yeniden bağla" : "Kaynak referansı / kopyası ekle"; onAccepted: { if (panel.relinkId) projects.request("relink", selectedFile.toString(), panel.relinkId); else projects.request("addSource", selectedFile.toString(), "", portable.checked) } }
    Dialog {
        parent: Overlay.overlay
        id: pathDialog
        objectName: "projectPathDialog"
        title: panel.targetAction === "create" ? "Yeni proje dizini" : "Yeni bir kopya kaydet"
        modal: true
        anchors.centerIn: parent
        width: Math.min(480, panel.width)
        ColumnLayout {
            anchors.fill: parent
            Label { text: "Var olan bir üst klasör seç veya tam dizin yolu gir. Yeni proje klasörünün adı yolun sonunda olmalı; hedef henüz mevcut olmamalı."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            UiButton { objectName: "chooseProjectLocationButton"; text: "Klasör seç"; helpContext: "project"; Layout.fillWidth: true; onClicked: locationDialog.open() }
            TextField { id: projectPath; objectName: "projectPathField"; Layout.fillWidth: true; placeholderText: "/home/kullanıcı/Belgeler/Projem"; Accessible.name: "Yeni proje dizin yolu" }
            Label { text: projects.errorText; visible: text.length > 0; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.error }
            UiButton { objectName: "confirmProjectPathButton"; enabled: !projects.busy; text: "Oluştur / kaydet"; primary: true; Layout.fillWidth: true; onClicked: { panel.pathRequestPending = true; projects.request(panel.targetAction, projectPath.text) } }
            UiButton { text: "Vazgeç"; Layout.fillWidth: true; onClicked: pathDialog.close() }
        }
    }
    Dialog {
        parent: Overlay.overlay
        id: recoveryDialog
        implicitHeight: recoveryText.implicitHeight + 120 * Theme.scale
        title: "Kurtarma kaydını yükle"
        modal: true
        anchors.centerIn: parent
        width: Math.min(480, panel.width)
        standardButtons: Dialog.Ok | Dialog.Cancel
        contentHeight: recoveryText.implicitHeight
        contentItem: Label { id: recoveryText; width: recoveryDialog.width - recoveryDialog.leftPadding - recoveryDialog.rightPadding; wrapMode: Text.WordWrap; text: "Ekrandaki değişikliklerin yerini otomatik kayıt alacak. Manuel kayıt korunur. Devam etmek istiyor musunuz?" }
        onAccepted: projects.request("restore")
    }
    Dialog {
        parent: Overlay.overlay
        id: discardDialog
        title: "Değişiklikler bırakılacak"
        modal: true
        anchors.centerIn: parent
        standardButtons: Dialog.Discard | Dialog.Cancel
        onDiscarded: projects.closeProject(true)
    }
}
