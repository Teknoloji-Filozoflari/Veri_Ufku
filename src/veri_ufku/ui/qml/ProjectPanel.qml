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
    property bool recoveryRequested: false
    Connections {
        target: projects
        function onChanged() {
            if (panel.recoveryRequested && !projects.busy) {
                panel.recoveryRequested = false
                if (!projects.errorText && projects.recoveryPreview.commit_id) recoveryDialog.open()
            }
        }
    }
    property string projectPath: ""
    property string chosenFolder: ""
    background: Rectangle { color: Theme.surface; border.color: Theme.border; radius: Theme.radius }
    ColumnLayout {
        id: projectContent
        width: panel.availableWidth
        enabled: !projects.busy
        spacing: Theme.md
        UiLabel { text: qsTr("Proje"); font.pixelSize: Theme.subheading; font.bold: true }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.sm
            UiButton { objectName: "newProjectButton"; width: Math.min(implicitWidth, parent.width); multiline: true; helpContext: "project"; text: qsTr("Yeni proje"); onClicked: { panel.targetAction = "create"; panel.projectPath = ""; panel.chosenFolder = ""; pathDialog.open() } }
            UiButton { objectName: "openProjectButton"; width: Math.min(implicitWidth, parent.width); multiline: true; helpContext: "project"; text: qsTr("Proje aç"); onClicked: openDialog.open() }
            UiButton { objectName: "saveProjectButton"; width: Math.min(implicitWidth, parent.width); multiline: true; helpContext: "project"; text: qsTr("Kaydet"); primary: true; enabled: projects.opened && !projects.readOnly; onClicked: projects.request("save") }
            UiButton { objectName: "saveAsProjectButton"; width: Math.min(implicitWidth, parent.width); multiline: true; helpContext: "project"; text: qsTr("Farklı kaydet"); enabled: projects.opened; onClicked: { panel.targetAction = "saveAs"; panel.projectPath = ""; panel.chosenFolder = ""; pathDialog.open() } }
            UiButton { objectName: "closeProjectButton"; width: Math.min(implicitWidth, parent.width); multiline: true; helpContext: "project"; text: qsTr("Projeyi kapat"); enabled: projects.opened; onClicked: projects.closeProject(false) }
            UiButton { width: Math.min(implicitWidth, parent.width); multiline: true; helpContext: "project"; text: qsTr("Değişiklikleri bırak"); visible: projects.dirty; onClicked: discardDialog.open() }
        }
        UiLabel { visible: false; text: projects.context; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
        UiLabel { visible: projects.opened && projects.message.length > 0; text: projects.message; wrapMode: Text.WordWrap; Layout.fillWidth: true; color: Theme.secondary }
        UiLabel { text: projects.errorText; visible: text.length > 0; wrapMode: Text.WordWrap; Layout.fillWidth: true; color: Theme.error }
        UiLabel { text: qsTr("Proje adı"); visible: projects.opened }
        UiTextField {
            objectName: "projectNameField"
            Layout.fillWidth: true
            visible: projects.opened
            enabled: !projects.readOnly
            text: projects.name
            maximumLength: 200
            placeholderText: qsTr("Proje adı")
            Accessible.name: qsTr("Proje adı")
            onTextEdited: projects.setName(text)
        }
        UiCheckBox { id: advancedProject; objectName: "projectDetailsToggle"; text: qsTr("Proje ayrıntıları"); visible: projects.opened; Layout.fillWidth: true }
        ColumnLayout {
            visible: advancedProject.checked && projects.opened
            Layout.fillWidth: true
        UiLabel { text: qsTr("Seed — tekrarlanabilir seçim için sayı (isteğe bağlı)"); visible: projects.opened; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        UiTextField {
            objectName: "projectSeedField"
            Layout.fillWidth: true
            visible: projects.opened
            enabled: !projects.readOnly
            text: projects.seedText
            placeholderText: qsTr("Seed — tekrarlanabilir seçim için sayı (isteğe bağlı)")
            Accessible.name: qsTr("Seed")
            onEditingFinished: projects.setSeed(text)
        }
        UiLabel {
            text: qsTr("Kaynak referansı yalnız dosyanın yolunu ve içerik izini saklar; taşıma sırasında dosyayı ayrıca götürmelisin. Taşınabilir kopya dosyayı projeye ekler ve disk kullanır. Kaynak dosyana yazılmaz.")
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.secondary
        }
        UiCheckBox { id: portable; Layout.fillWidth: true; contentItem: UiLabel { text: portable.text; leftPadding: portable.indicator.width + portable.spacing; wrapMode: Text.WordWrap; color: Theme.text } text: qsTr("Kaynak dosyanın taşınabilir kopyasını ekle"); enabled: projects.opened && !projects.readOnly; palette.windowText: Theme.text }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.sm
            UiButton { objectName: "attachSourceButton"; width: Math.min(implicitWidth, parent.width); multiline: true; helpContext: "project.source"; text: qsTr("Kaynak dosyası bağla"); enabled: projects.opened && !projects.readOnly; onClicked: { panel.relinkId = ""; sourceDialog.open() } }
            UiButton { width: Math.min(implicitWidth, parent.width); multiline: true; helpContext: "project.source"; text: qsTr("Kaynak durumunu kontrol et"); enabled: projects.opened; onClicked: projects.refreshSources() }
            UiButton { objectName: "recoverLockButton"; width: Math.min(implicitWidth, parent.width); multiline: true; helpContext: "project.recovery"; text: qsTr("Eski kilidi kontrollü kurtar"); visible: projects.readOnly; onClicked: projects.request("recover") }
            UiButton { objectName: "restoreAutosaveButton"; width: Math.min(implicitWidth, parent.width); multiline: true; helpContext: "project.recovery"; text: qsTr("Kurtarma kaydını yükle"); enabled: projects.opened && !projects.readOnly && !projects.busy; onClicked: { panel.recoveryRequested = true; projects.request("previewRecovery") } }
        }
        UiLabel { text: projects.sourceSummary; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
        Repeater {
            model: projects.sources
            UiButton {
                required property var modelData
                Layout.fillWidth: true
                multiline: true
                helpContext: "project.source"
                text: qsTr("Yeniden bağla: ") + modelData.path
                visible: !modelData.connector
                enabled: !projects.readOnly
                onClicked: { panel.relinkId = modelData.id; sourceDialog.open() }
            }
        }
        UiLabel { text: projects.resultSummary; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
        UiCheckBox { id: recoverOpen; Layout.fillWidth: true; contentItem: UiLabel { text: recoverOpen.text; leftPadding: recoverOpen.indicator.width + recoverOpen.spacing; wrapMode: Text.WordWrap; color: Theme.text } text: qsTr("Önceki kilidi kurtararak aç (aktif yazıcı korunur)"); palette.windowText: Theme.text }
        }
        UiLabel { visible: projects.recentProjects.length > 0; text: qsTr("Son projeler"); font.bold: true }
        Flow {
            objectName: "recentProjectsFlow"
            Layout.fillWidth: true
            spacing: Theme.sm
            Repeater {
                model: projects.recentProjects
                UiButton { required property var modelData; objectName: "recentProject_" + modelData.name; width: Math.min(implicitWidth, parent.width); multiline: true; text: modelData.name; helpContext: "project"; onClicked: projects.request("open", modelData.path) }
            }
        }
    }
    Connections { target: projects; function onChanged() { if (panel.pathRequestPending && !projects.busy) { panel.pathRequestPending = false; if (!projects.errorText && projects.opened) pathDialog.close() } } }
    BusyIndicator { anchors.right: parent.right; running: projects.busy; visible: running }
    FolderPicker { id: openDialog; objectName: "openProjectFolderPicker"; title: qsTr("Proje aç"); acceptText: qsTr("Projeyi aç"); onChosen: function(folder) { projects.request(recoverOpen.checked ? "openRecover" : "open", folder) } }
    FolderPicker { id: locationDialog; objectName: "projectLocationPicker"; title: qsTr("Proje için konum seç"); onChosen: function(folder) { panel.projectPath = projects.newProjectPath(folder); panel.chosenFolder = projects.folderName(folder) } }
    FileDialog { id: sourceDialog; title: panel.relinkId ? qsTr("Aynı kaynak veriyi yeniden bağla") : qsTr("Kaynak referansı / kopyası ekle"); onAccepted: { if (panel.relinkId) projects.request("relink", selectedFile.toString(), panel.relinkId); else projects.request("addSource", selectedFile.toString(), "", portable.checked) } }
    Dialog {
        parent: Overlay.overlay
        id: pathDialog
        objectName: "projectPathDialog"
        padding: Theme.lg
        background: Rectangle { color: Theme.surface; border.color: Theme.border; radius: Theme.radius + 4 }
        header: UiLabel { text: pathDialog.title; padding: Theme.lg; font.pixelSize: Theme.subheading; font.bold: true }
        title: panel.targetAction === "create" ? qsTr("Yeni proje") : qsTr("Farklı kaydet")
        modal: true
        anchors.centerIn: parent
        width: Math.min(440 * Theme.scale, Overlay.overlay.width - 32)
        ColumnLayout {
            property string helpContext: "project"
            anchors.fill: parent
            UiLabel { text: qsTr("Projenin kaydedileceği klasörü seç."); wrapMode: Text.WordWrap; Layout.fillWidth: true }
            UiButton { objectName: "chooseProjectLocationButton"; text: qsTr("Klasör seç"); primary: panel.projectPath.length === 0; helpContext: "project"; Layout.fillWidth: true; onClicked: locationDialog.open() }
            UiLabel { text: panel.chosenFolder ? qsTr("Seçilen klasör: ") + panel.chosenFolder : qsTr("Henüz klasör seçilmedi"); Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.secondary }
            UiLabel { text: projects.errorText; visible: text.length > 0; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.error }
            Flow { Layout.fillWidth: true; spacing: Theme.sm
                UiButton { text: qsTr("Vazgeç"); onClicked: pathDialog.close() }
                UiButton { objectName: "confirmProjectPathButton"; enabled: !projects.busy && panel.projectPath.length > 0; text: panel.targetAction === "create" ? qsTr("Proje oluştur") : qsTr("Kopyayı kaydet"); primary: true; Layout.fillWidth: true; onClicked: { panel.pathRequestPending = true; projects.request(panel.targetAction, panel.projectPath) } }
            }
        }
    }
    Dialog {
        parent: Overlay.overlay
        id: recoveryDialog
        objectName: "recoveryDialog"
        implicitHeight: Math.min(recoveryText.implicitHeight + 120 * Theme.scale, parent.height - 32)
        title: qsTr("Kurtarma kaydını yükle")
        modal: true
        anchors.centerIn: parent
        width: Math.min(480, panel.width)
        standardButtons: Dialog.Ok | Dialog.Cancel
        contentHeight: recoveryText.implicitHeight
        contentItem: ScrollView {
            contentWidth: availableWidth
            clip: true
            UiLabel { id: recoveryText; objectName: "recoveryPreviewText"; width: parent.width; wrapMode: Text.Wrap; text: qsTr("Yüklenecek otomatik kayıt:") + "\n" + (projects.recoveryPreview.name || "") + "\n" + (projects.recoveryPreview.created_at || "") + "\n" + qsTr("Veri / işlem / sonuç sayısı:") + " " + (projects.recoveryPreview.datasets || 0) + " / " + (projects.recoveryPreview.operations || 0) + " / " + (projects.recoveryPreview.results || 0) + "\n" + qsTr("Ekrandaki değişikliklerin yerini bu kayıt alacak. Manuel kayıt korunur; kaynak dosyalar yeniden işlenmez. İnceleyip ayrıca Kaydet seçebilirsiniz.") }
        }
        onAccepted: projects.request("restore")
    }
    Dialog {
        parent: Overlay.overlay
        id: discardDialog
        title: qsTr("Değişiklikler bırakılacak")
        modal: true
        anchors.centerIn: parent
        standardButtons: Dialog.Discard | Dialog.Cancel
        onDiscarded: projects.closeProject(true)
    }
}
