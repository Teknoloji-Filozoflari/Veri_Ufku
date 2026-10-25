import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "RoadmapSteps.js" as Roadmap
import "UxStages.js" as UxStages

ApplicationWindow {
    id: window
    objectName: "mainWindow"
    width: 1200
    height: 800
    minimumWidth: 720
    minimumHeight: 560
    visible: true
    title: "Veri_Ufku"
    color: Theme.background
    font.pixelSize: Theme.body
    palette.window: Theme.background
    palette.windowText: Theme.text
    palette.text: Theme.text
    palette.buttonText: Theme.text
    palette.brightText: Theme.text
    palette.button: Theme.raised
    palette.base: Theme.field
    palette.alternateBase: Theme.background
    palette.highlight: window.sectionAccent
    palette.highlightedText: Theme.accentText
    palette.light: Theme.surface
    palette.mid: Theme.controlBorder
    palette.dark: Theme.secondary
    palette.placeholderText: Theme.secondary
    property int selectedSection: 0
    property int uxStage: 0
    property bool contextPanelOpen: false
    property string centerView: "table"
    readonly property var uxStageInfo: UxStages.stageAt(uxStage)
    readonly property var uxStageQuestions: [
        qsTr("Ne öğrenmek istiyorum?"),
        qsTr("Dosya doğru okundu mu?"),
        qsTr("Her sütun ne demek?"),
        qsTr("Veri genel olarak neye benziyor?"),
        qsTr("Ne kadarı eksik, silersem ne olur?"),
        qsTr("Dağılım ve ilişkiler nasıl?"),
        qsTr("Sıra dışı gözlemler hangileri?"),
        qsTr("Bu bulgulara göre ne yapmalıyım?"),
        qsTr("Bu soruya hangi yöntem uyar?"),
        qsTr("Ne buldum, ne kadar güvenebilirim?")
    ]
    // -1 follows the window; an explicit user choice lasts for this session.
    property int navigationMode: -1
    readonly property bool compactNavigation: navigationMode < 0 ? width < 1000 * Theme.scale : navigationMode === 1
    property string dataPane: ""
    function openDataPane(pane) {
        dataPane = pane
        dataTabs.currentIndex = pane === "import" ? 1 : pane === "quality" ? 2 : pane ? 0 : -1
        window.syncUxStageFromSection()
        if (pane) Qt.callLater(function() {
            let name = pane === "profile" ? "inventoryTable" : pane === "describe" ? "computeDescribe" : pane === "values" ? "valuesColumn" : pane === "rows" ? "loadDatasetButton" : ""
            let control = name ? window.findVisibleItem(window.contentItem, name) : null
            if (control && control.enabled) control.forceActiveFocus()
        })
    }
    function syncUxStageFromSection() {
        uxStage = UxStages.indexForSection(selectedSection, dataPane)
    }
    function navigateUxStage(index, origin) {
        let stage = UxStages.stageAt(index)
        uxStage = index
        selectedSection = stage.section
        if (stage.section === 1) openDataPane(stage.pane || "profile")
        else dataPane = ""
        if (origin) origin.forceActiveFocus()
        workspace.contentItem.contentY = 0
    }
    readonly property var sectionTones: ["warm", "cyan", "violet", "cyan", "violet", "violet", "warm", "mint"]
    readonly property color sectionAccent: Theme.toneColor(sectionTones[selectedSection])
    property bool showDemo: false
    property bool infoOpen: false
    property bool readingOpen: false
    readonly property bool dockInfo: width >= 1100 * Theme.scale
    readonly property bool advanced: preferences && preferences.view === "advanced"
    readonly property bool darkTheme: Theme.dark
    property var helpOrigin: null
    property string helpOriginName: ""
    readonly property var sections: !advanced ? [
        qsTr("Başlangıç"), qsTr("Veriyi tanı"), qsTr("Veriyi hazırla"),
        qsTr("Desenleri keşfet"), qsTr("Farkları karşılaştır"), qsTr("Model kur"),
        qsTr("Bulguları paylaş"), qsTr("Öğren")
    ] : [
        qsTranslate("Shell", "Home"), qsTranslate("Shell", "Data"),
        qsTranslate("Shell", "Prepare"), qsTranslate("Shell", "Explore"),
        qsTranslate("Shell", "Compare"), qsTranslate("Shell", "Model"),
        qsTranslate("Shell", "Report"), qsTranslate("Shell", "Learn")
    ]
    readonly property var descriptions: [
        window.advanced ? qsTr("Proje ve araçlarına doğrudan eriş.") : qsTr("Bir sorudan bulguya: verinin yolculuğunu adım adım izle."),
        qsTr("Kaynağı içe aktarın; sütunları, kayıtları ve veri kalitesini inceleyin."),
        qsTr("Değişiklikleri önce önizleyin; yeni veri sürümüne açıkça uygulayın."),
        qsTr("İstatistik özetini ve grafiklerle dağılım, grup, zaman, ilişki ve eksikleri inceleyin."),
        "Sorundan hareketle grup farkını veya sayısal/kategorik ilişkiyi araştır; önce varsayımları incele.",
        "Model amacına göre uygunluğu incele ve eğitim katında öğrenilecek hazırlama planını kaydet.",
        qsTr("Temizlenmiş veriyi dışa aktarın ve yerel HTML/PDF raporunu kaydedin."),
        "Merak ettiğin konuyu çevrimdışı ara; özet, örnek veya rehber olarak oku."
    ]
    function navigate(index, origin) {
        selectedSection = index
        window.syncUxStageFromSection()
        if (infoOpen) learning.openContext(learning.screenContexts[index])
        if (origin) origin.forceActiveFocus()
        workspace.contentItem.contentY = 0
    }
    onSelectedSectionChanged: {
        workspace.contentItem.contentY = 0
        window.syncUxStageFromSection()
    }
    onDataPaneChanged: window.syncUxStageFromSection()
    function openReading(origin, articleId) {
        helpOrigin = origin
        helpOriginName = origin.objectName
        learning.openArticle(articleId)
        readingOpen = true
        infoOpen = true
        articleReader.open()
    }
    function openInformation(origin, articleId, context) {
        if (readingOpen) closeInformation()
        helpOrigin = origin || helpButton
        helpOriginName = helpOrigin.objectName
        if (articleId) learning.openArticle(articleId)
        else learning.openContext(context || learning.screenContexts[selectedSection])
        infoOpen = true
        if (!dockInfo) infoDrawer.open()
        else dockPanel.focusFirst()
    }
    function focusedHelpContext() {
        let item = activeFocusItem
        while (item) {
            if (item.helpContext) return item.helpContext
            item = item.parent
        }
        return learning.screenContexts[selectedSection]
    }
    function findVisibleItem(item, name) {
        if (!item || !item.visible) return null
        if (item.objectName === name) return item
        for (let child of item.children) {
            let found = findVisibleItem(child, name)
            if (found) return found
        }
        return null
    }
    function restoreHelpFocus() {
        let origin = helpOriginName ? findVisibleItem(window.contentItem, helpOriginName) : helpOrigin
        if (!origin && helpOriginName) origin = findVisibleItem(window.header, helpOriginName) || findVisibleItem(window.footer, helpOriginName)
        if (!origin && selectedSection === 7) origin = findVisibleItem(window.contentItem, "learningSearch")
        if (!origin || !origin.visible || !origin.enabled) origin = helpButton.visible ? helpButton : headerBeginner
        origin.forceActiveFocus()
    }
    function closeInformation() {
        infoOpen = false
        readingOpen = false
        articleReader.close()
        infoDrawer.close()
        restoreHelpFocus()
    }
    onDockInfoChanged: {
        if (infoOpen && !readingOpen) {
            if (dockInfo) infoDrawer.close()
            else infoDrawer.open()
        }
    }
    Shortcut { sequence: "Ctrl+K"; onActivated: { expertWorkspace.search(""); commandPalette.open() } }
    Dialog {
        id: commandPalette
        objectName: "commandPalette"
        title: "Komut paleti — yöntem ve amaç ara"
        modal: true
        anchors.centerIn: parent
        width: Math.min(window.width - 40, 800)
        standardButtons: Dialog.Close
        contentItem: ModuleDiscovery { }
        onOpened: {
            let search = window.findVisibleItem(contentItem, "moduleSearch")
            if (search) search.forceActiveFocus()
        }
    }
    Connections {
        target: expertWorkspace
        function onNavigate(section, capability) {
            if (capability.indexOf("learn.") !== 0) preferences.setView("advanced")
            window.selectedSection = section
            if(capability.indexOf("learn.lab.")===0)learningLab.startLesson(capability.substring("learn.lab.".length))
            if(capability.indexOf("environment.")===0) {
                Qt.callLater(function(){let control=window.findVisibleItem(window.contentItem,"environmentExpanded");if(control){control.checked=true;control.forceActiveFocus()}})
            }
            if(capability.indexOf("plugin.")===0) {
                Qt.callLater(function(){let control=window.findVisibleItem(window.contentItem,"pluginsExpanded");if(control){control.checked=true;control.forceActiveFocus()}})
            }
            if(capability.indexOf("privacy.")===0) {
                Qt.callLater(function(){let control=window.findVisibleItem(window.contentItem,"privacyExpanded");if(control){control.checked=true;control.forceActiveFocus()}})
            }
            if(capability.indexOf("share.")===0) {
                Qt.callLater(function(){let control=window.findVisibleItem(window.contentItem,"sharingExpanded");if(control){control.checked=true;control.forceActiveFocus()}})
            }
            if(capability.indexOf("report.")===0) {
                Qt.callLater(function(){let control=window.findVisibleItem(window.contentItem,"reportBuilderExpanded");if(control){control.checked=true;control.forceActiveFocus()}})
            }
            if(capability.indexOf("scenario.")===0) {
                modelPath.currentIndex=0
                Qt.callLater(function(){
                    let control=window.findVisibleItem(window.contentItem,"scenarioExpanded")
                    if(control){control.checked=true;control.forceActiveFocus()}
                })
            }
            if(capability.indexOf("model.monitor.")===0) {
                modelPath.currentIndex=0
                Qt.callLater(function(){
                    let control=window.findVisibleItem(window.contentItem,"monitoringExpanded")
                    if(control){control.checked=true;control.forceActiveFocus()}
                })
            }
            if(capability.indexOf("text.nlp.")===0)modelPath.currentIndex=2
            if(capability.indexOf("model.temporal.")===0||capability.indexOf("model.signal.")===0)modelPath.currentIndex=1
            let clusterIds=["model.kmeans","model.dbscan","model.agglomerative","model.gmm","model.optics","model.hdbscan"]
            let anomalyIds=["model.isolation-forest","model.iqr","model.lof","model.one-class-svm","model.robust-covariance"]
            if(section===5&&(clusterIds.indexOf(capability)>=0||anomalyIds.indexOf(capability)>=0))Qt.callLater(function(){
                modelPath.currentIndex=0
                let settings=window.findVisibleItem(window.contentItem,"preparationSettings")
                if(settings)settings.checked=true
                Qt.callLater(function(){
                    let purpose=window.findVisibleItem(window.contentItem,"preparationPurpose")
                    let clustering=clusterIds.indexOf(capability)>=0
                    if(purpose){purpose.currentIndex=clustering?2:3;purpose.activated(purpose.currentIndex)}
                    Qt.callLater(function(){let choice=window.findVisibleItem(window.contentItem,"unsupervisedMethod");if(choice){choice.currentIndex=(clustering?clusterIds:anomalyIds).indexOf(capability);choice.forceActiveFocus()}})
                })
            })
            if (capability === "dashboard.canvas" || capability === "figure.compose") Qt.callLater(function() { let control = window.findVisibleItem(window.contentItem,"dashboardExpanded"); if(control)control.checked=true })
            if (section === 1) window.openDataPane(capability.startsWith("import.") ? "import" : "profile")
            if (["operation.schema-contract", "operation.contract-check", "operation.entity-candidates", "operation.entity-merge", "operation.category-candidates", "operation.category-map"].indexOf(capability) >= 0) datasetViewPanel.contractExpanded = true
            commandPalette.close()
        }
    }
    Dialog {
        id: computeDialog
        objectName: "computeBudgetDialog"
        title: qsTr("Hesaplama bütçesi ve ölçümler")
        width: Math.min(window.width - 24, 900 * Theme.scale)
        height: Math.min(window.height - 24, 650 * Theme.scale)
        anchors.centerIn: parent
        modal: true
        standardButtons: Dialog.Close
        ScrollView {
            anchors.fill: parent
            clip: true
            ColumnLayout {
                width: computeDialog.availableWidth - 24
                spacing: Theme.md
                UiLabel { text: "RAM: " + Math.round((computeResources.report.rss_bytes || 0)/1048576) + " / " + Math.round((computeResources.report.ram_limit || 0)/1048576) + " MiB · süreç: " + (computeResources.report.processes || 0) + " / " + (computeResources.report.process_limit || 0); Layout.fillWidth: true; wrapMode: Text.WordWrap }
                UiLabel { text: "Toplam native thread bütçesi: " + (computeResources.report.cpu_threads || 0) + " · geçici disk zirvesi: " + Math.round((computeResources.report.temp_bytes || 0)/1048576) + " MiB"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                UiLabel { text: computeResources.report.note || "Ölçüm bekleniyor"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                UiLabel { text: "Profil, join, tuning, açıklama ve tensor işleri aynı panelde görünür. Son 64 biten süreç yalnız ölçüm kaydıdır; başarı durumu ilgili sonuç ekranındadır."; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                Repeater {
                    model: computeResources.report.rows || []
                    UiLabel { required property var modelData; text: modelData.kind + " · PID " + modelData.pid + " · " + modelData.seconds + " s · " + (modelData.peak_rss_bytes ? Math.round(modelData.peak_rss_bytes/1048576) + " MiB" : "RSS örneklenemedi") + " · " + modelData.native_threads + " thread · " + modelData.device + " · " + modelData.state; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
                }
                UiLabel { text: "Yöntem bazında çalışma belleği (ilk 50 eşleşme)"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                UiTextField { id: computeMethodQuery; objectName: "computeMethodQuery"; property string helpContext: "compute.resources"; Accessible.name: "Yöntem kimliği ara"; placeholderText: "Yöntem kimliği ara"; text: "dataset.profile"; Layout.fillWidth: true }
                Repeater {
                    model: computeResources.methods(computeMethodQuery.text)
                    UiLabel { required property var modelData; text: modelData.id + " · " + modelData.memory + " · sparse: " + modelData.sparse + " · device: " + modelData.devices.join(", ") + " · limits: " + JSON.stringify(modelData.limits); Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
                }
                UiButton { text: "Bu ne işe yarar?"; helpContext: "compute.resources"; onClicked: window.openInformation(this, "", "compute.resources") }
                UiLabel { text: "Dask: isteğe bağlı, bu kurulumda runtime doğrulanmadı. Remote çalıştırma ve GPU yürütme bu panelden başlatılamaz. Yerel veri otomatik gönderilmez."; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            }
        }
    }
    Shortcut { sequence: "Ctrl+,"; onActivated: displayDialog.open() }
    Dialog {
        id: displayDialog
        objectName: "displayDialog"
        title: qsTr("Görünüm ve dil")
        modal: true
        x: Math.max(0, (window.width - width) / 2)
        y: Math.max(0, (window.height - height) / 2)
        width: Math.min(window.width - 32, 460)
        height: Math.min(window.height - 32, implicitHeight)
        onOpened: displayTheme.forceActiveFocus()
        onClosed: displayButton.forceActiveFocus()
        contentItem: ScrollView {
            contentWidth: availableWidth
            clip: true
            ColumnLayout {
                width: parent.width
                spacing: Theme.md
                UiLabel { text: qsTr("Tema"); Layout.fillWidth: true; wrapMode: Text.Wrap }
                UiCombo { id: displayTheme; objectName: "displayTheme"; accessibleLabel: qsTr("Tema"); model: [qsTr("Koyu"), qsTr("Açık")]; currentIndex: preferences && preferences.theme === "light" ? 1 : 0; Layout.fillWidth: true; onActivated: preferences.setTheme(currentIndex === 1 ? "light" : "dark") }
                UiLabel { text: qsTr("Yazı boyutu"); Layout.fillWidth: true; wrapMode: Text.Wrap }
                UiCombo { objectName: "displayTextScale"; accessibleLabel: qsTr("Yazı boyutu"); model: ["100%", "125%", "150%", "200%"]; currentIndex: preferences ? [1, 1.25, 1.5, 2].indexOf(preferences.textScale) : 0; Layout.fillWidth: true; onActivated: preferences.setTextScale([1, 1.25, 1.5, 2][currentIndex]) }
                UiLabel { text: qsTr("Arayüz dili"); Layout.fillWidth: true; wrapMode: Text.Wrap }
                UiCombo { objectName: "displayLocale"; accessibleLabel: qsTr("Arayüz dili"); model: ["Türkçe", "English"]; currentIndex: preferences && preferences.locale === "en" ? 1 : 0; Layout.fillWidth: true; onActivated: preferences.setLocale(currentIndex === 1 ? "en" : "tr") }
                UiLabel { objectName: "localeBoundaryNotice"; text: qsTr("Temel arayüz İngilizceye çevrilmiştir; ayrıntılı yardım ve bazı analiz metinleri Türkçedir. Dil ve görünüm değişikliği dosyanın sayı/tarih okuma ayarlarını değiştirmez."); Layout.fillWidth: true; wrapMode: Text.Wrap }
                UiButton { objectName: "displayClose"; text: qsTr("Kapat"); onClicked: displayDialog.close() }
            }
        }
    }
    property bool discardOnExit: false
    property bool closeAfterSave: false
    onClosing: function(event) {
        if (projects.projectTaskBusy) {
            event.accepted = false
            return
        }
        if (projects.dirty && !discardOnExit) {
            event.accepted = false
            unsavedDialog.open()
            return
        }
        lessonLab.close()
        learningExample.close()
        if (bridge && !bridge.closed) {
            event.accepted = false
            bridge.shutdown()
        }
    }
    Shortcut { sequence: "F1"; onActivated: window.openInformation(window.activeFocusItem || helpButton, "", window.focusedHelpContext()) }
    Shortcut { sequence: "Escape"; enabled: window.infoOpen && window.dockInfo; onActivated: window.closeInformation() }

    header: Rectangle {
        color: Theme.chrome
        implicitHeight: headerBody.implicitHeight + 2 * Theme.lg
        ColumnLayout {
            id: headerBody
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: Theme.lg
            spacing: Theme.md
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.xl
                UiIconButton {
                    objectName: "navigationToggle"
                    symbol: "sidebar"
                    accessibleLabel: window.compactNavigation ? qsTr("Gezinme menüsünü genişlet") : qsTr("Gezinme menüsünü daralt")
                    onClicked: window.navigationMode = window.compactNavigation ? 0 : 1
                }
                RowLayout {
                    spacing: Theme.sm

                    Layout.fillWidth: window.width < 1000 * Theme.scale
                    BrandMark { objectName: "applicationLogo"; Layout.preferredWidth: 36; Layout.preferredHeight: 36 }
                    UiLabel { text: "Veri_Ufku"; font.pixelSize: Theme.subheading; font.bold: true }
                }
                UiLabel {
                    objectName: "datasetContext"
                    visible: window.width >= 1000 * Theme.scale
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    text: projects.context
                    color: Theme.secondary
                    wrapMode: Text.WordWrap
                }
                RowLayout {
                    spacing: Theme.sm
                    UiIconButton {
                        objectName: "commandSearchButton"
                        symbol: "search"
                        accessibleLabel: qsTr("Yöntem ve amaç ara (Ctrl+K)")
                        onClicked: { expertWorkspace.search(""); commandPalette.open() }
                    }
                    UiLabel { objectName: "levelLabel"; visible: window.width >= 1000 * Theme.scale; text: window.advanced ? qsTr("Gelişmiş çalışma") : qsTr("Başlangıç · adım adım"); color: Theme.secondary; font.pixelSize: Theme.small }
                    UiIconButton {
                        id: headerBeginner
                        objectName: "beginnerButton"
                        symbol: "sprout"
                        accessibleLabel: qsTranslate("Shell", "Beginner")
                        checked: !window.advanced
                        onClicked: preferences.setView("beginner")
                    }
                    UiIconButton {
                        objectName: "advancedButton"
                        tone: "violet"
                        symbol: "sliders"
                        accessibleLabel: qsTranslate("Shell", "Advanced")
                        checked: window.advanced
                        onClicked: preferences.setView("advanced")
                    }
                    UiIconButton {
                        objectName: "contextPanelToggle"
                        symbol: "sliders"
                        accessibleLabel: window.contextPanelOpen ? qsTr("Bağlam panelini kapat") : qsTr("Bağlam panelini aç")
                        checked: window.contextPanelOpen
                        onClicked: window.contextPanelOpen = !window.contextPanelOpen
                    }
                    UiIconButton {
                        id: displayButton
                        objectName: "displayButton"
                        symbol: "settings"
                        accessibleLabel: qsTr("Görünüm ve dil")
                        onClicked: displayDialog.open()
                    }
                    UiIconButton {
                        objectName: "closeButton"
                        symbol: "close"
                        accessibleLabel: qsTr("Uygulamayı kapat")
                        onClicked: window.close()
                    }
                }
            }
            UiLabel {
                visible: window.width < 1000 * Theme.scale
                text: projects.context
                color: Theme.secondary
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                elide: Text.ElideRight
            }
            UiLabel {
                objectName: "startupWarning"
                visible: !!startupError
                text: startupError
                color: Theme.error
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
        }
        Rectangle { height: 1; anchors.bottom: parent.bottom; width: parent.width; color: Theme.border }
    }

    footer: Rectangle {
        color: Theme.chrome
        implicitHeight: statusRow.implicitHeight + 2 * Theme.sm
        Rectangle { width: parent.width; height: 1; color: Theme.border }
        RowLayout {
            id: statusRow
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: Theme.sm
            spacing: Theme.md
            UiLabel {
                objectName: "workspaceStatus"
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                text: projects.busy ? qsTr("Proje işlemi sürüyor…") : projects.dirty ? qsTr("Kaydedilmemiş değişiklikler") : projects.opened ? qsTr("Proje açık") : qsTr("Proje açık değil")
                font.pixelSize: Theme.small
                color: projects.dirty ? Theme.warning : Theme.secondary
                elide: Text.ElideRight
            }
            UiLabel {
                objectName: "uxStageStatus"
                visible: window.width >= 900 * Theme.scale
                text: qsTr("Aşama") + " " + window.uxStage + " · " + window.uxStageInfo.shortTitle
                font.pixelSize: Theme.small
                color: Theme.secondary
                elide: Text.ElideRight
            }
            UiLabel {
                objectName: "datasetScopeStatus"
                visible: window.width >= 1100 * Theme.scale && dataView && dataView.datasets && dataView.datasets.length > 0
                text: dataView.viewSummary || ""
                font.pixelSize: Theme.small
                color: Theme.secondary
                elide: Text.ElideRight
                Layout.maximumWidth: window.width * 0.28
            }
            UiLabel {
                visible: window.width >= 1000 * Theme.scale
                text: qsTr("Yardım F1 · Yöntem ara Ctrl+K")
                font.pixelSize: Theme.small
                color: Theme.secondary
            }
            UiButton {
                objectName: "statusResources"
                quiet: true
                text: qsTr("Kaynaklar") + " · " + Math.round((computeResources.report.rss_bytes || 0) / 1048576) + " MiB"
                helpContext: "compute.resources"
                onClicked: computeDialog.open()
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0
        Rectangle {
            objectName: "navigationRail"
            Layout.fillHeight: true
            Layout.preferredWidth: window.compactNavigation ? 68 : 212 * Math.min(Theme.scale, 1.25)
            color: Theme.chrome
            ScrollView {
                anchors.fill: parent
                anchors.margins: Theme.md
                clip: true
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: Theme.sm
                    StageStrip {
                        visible: !window.advanced
                        compact: window.compactNavigation
                        currentStage: window.uxStage
                        Layout.fillWidth: true
                        onStageChosen: function(index, origin) { window.navigateUxStage(index, origin) }
                    }
                    UiLabel {
                        visible: !window.compactNavigation
                        text: window.advanced ? qsTr("ÇALIŞMA ALANI") : qsTr("BÖLÜMLER")
                        color: Theme.muted
                        font.pixelSize: Theme.small
                        font.letterSpacing: 1
                        Layout.leftMargin: Theme.md
                        Layout.topMargin: Theme.md
                        Layout.bottomMargin: Theme.sm
                    }
                    Repeater {
                        model: window.sections
                        UiNavigationButton {
                            id: navButton
                            required property int index
                            required property string modelData
                            objectName: "nav" + index
                            compact: window.compactNavigation
                            Layout.fillWidth: true
                            symbol: ["home", "table", "prepare", "chart", "compare", "model", "report", "book"][index]
                            tone: window.sectionTones[index]
                            symbolColor: index === 6 ? Theme.reportTone : Theme.toneColor(tone)
                            text: modelData
                            checked: window.selectedSection === index
                            Accessible.description: modelData
                            onClicked: window.navigate(index, this)
                            Keys.onDownPressed: nextItemInFocusChain().forceActiveFocus()
                            Keys.onUpPressed: nextItemInFocusChain(false).forceActiveFocus()
                            Shortcut { sequence: "Ctrl+" + (navButton.index + 1); onActivated: window.navigate(navButton.index, navButton) }
                        }
                    }
                }
            }
        }
        ScrollView {
            id: workspace
            objectName: "workspace"
            enabled: !startupError || window.selectedSection === 7
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: availableWidth
            ColumnLayout {
                width: workspace.availableWidth
                spacing: Theme.xl
                Item { Layout.preferredHeight: Theme.xs }
                GridLayout {
                    columns: workspace.availableWidth < 650 * Theme.scale ? 1 : 2
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    UiLabel {
                        Layout.fillWidth: true
                        text: window.sections[window.selectedSection]
                        color: window.sectionAccent
                        font.pixelSize: Theme.heading
                        font.bold: true
                        wrapMode: Text.WrapAnywhere
                    }
                    UiButton {
                        id: helpButton
                        objectName: "helpButton"
                        visible: true
                        quiet: true
                        tone: "mint"
                        text: qsTranslate("Shell", "What is this for?")
                        glyph: "?"
                        multiline: true
                        Layout.maximumWidth: workspace.availableWidth < 650 * Theme.scale ? workspace.availableWidth - 2 * Theme.xl : workspace.availableWidth * 0.5
                        onClicked: window.openInformation(this)
                    }
                }
                UiLabel {
                    text: window.descriptions[window.selectedSection]
                    color: Theme.secondary
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    wrapMode: Text.WordWrap
                }
                StateNotice {
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    visible: preferences && preferences.errorText.length > 0
                    kind: "error"
                    heading: qsTranslate("Shell", "Display preferences")
                    detail: preferences ? preferences.errorText : ""
                }
                GuidePanel {
                    id: homeGuide
                    compactHome: window.selectedSection === 0
                    Layout.fillWidth:true
                    Layout.leftMargin:Theme.xl
                    Layout.rightMargin:Theme.xl
                    visible:guide.active && window.selectedSection!==0 && window.selectedSection!==7
                    onHelpRequested:function(origin,context){window.openInformation(origin,"",context)}
                }
                Connections { target:guide; function onNavigate(section,tab) { window.selectedSection=section; if(section===1) dataTabs.currentIndex=tab } }
                Connections { target:launchRequests; function onNavigate(section,tab) { window.selectedSection=section; if(section===1) dataTabs.currentIndex=tab } }
                JourneyGuide {
                    visible: !window.advanced && window.selectedSection > 0 && window.selectedSection < 7
                    section: window.selectedSection
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    onLearnRequested: function(articleId, origin) { window.selectedSection=7; window.openReading(origin, articleId) }
                    onNavigate: function(section) {
                        window.navigate(section, null)
                        if (section === 0) Qt.callLater(function() {
                            let target=window.findVisibleItem(window.contentItem, projects.opened ? "saveProjectButton" : "newProjectButton")
                            if (target) target.forceActiveFocus()
                        })
                    }
                }
                UiButton {
                    objectName: "expertToolsEntry"
                    visible: !window.advanced && window.selectedSection > 0 && window.selectedSection < 7
                    text: qsTr("Daha fazla araç · Gelişmiş görünüme geç")
                    quiet: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    onClicked: preferences.setView("advanced")
                }
                WorkspacePanel {
                    objectName: "deferredReportBuilderPanel"
                    requested: window.selectedSection===6
                    sourceComponent: ReportBuilderPanel {
                        onHelpRequested:function(origin,context){window.openInformation(origin,"",context)}
                    }
                }
                WorkspacePanel {
                    objectName: "deferredReportPanel"
                    requested: window.selectedSection===6
                    sourceComponent: ReportPanel {
                        onHelpRequested:function(origin,context){window.openInformation(origin,"",context)}
                    }
                }
                WorkspacePanel {
                    objectName: "deferredReproPanel"
                    requested: window.advanced && window.selectedSection===6
                    sourceComponent: ReproPanel {
                        onHelpRequested:function(origin,context){window.openInformation(origin,"",context)}
                    }
                }
                WorkspacePanel {
                    objectName: "deferredCodePanel"
                    requested: window.advanced && window.selectedSection===6
                    sourceComponent: CodePanel {
                        onHelpRequested:function(origin,context){window.openInformation(origin,"",context)}
                    }
                }
                WorkspacePanel {
                    objectName: "deferredEnvironmentPanel"
                    requested: window.advanced && window.selectedSection===6
                    sourceComponent: EnvironmentPanel {
                        onHelpRequested:function(origin,context){window.openInformation(origin,"",context)}
                    }
                }
                WorkspacePanel {
                    objectName: "deferredPluginsPanel"
                    requested: window.advanced && window.selectedSection===6
                    sourceComponent: PluginsPanel {
                        onHelpRequested:function(origin,context){window.openInformation(origin,"",context)}
                    }
                }
                WorkspacePanel {
                    objectName: "deferredPrivacyPanel"
                    requested: window.selectedSection===6
                    sourceComponent: PrivacyPanel {
                        onHelpRequested:function(origin,context){window.openInformation(origin,"",context)}
                    }
                }
                WorkspacePanel {
                    objectName: "deferredSharingPanel"
                    requested: window.advanced && window.selectedSection===6
                    sourceComponent: SharingPanel {
                        onHelpRequested:function(origin,context){window.openInformation(origin,"",context)}
                    }
                }


                GridLayout {
                    id: dataSections
                    objectName: "dataSectionHeadings"
                    columns: window.dataPane && width > 650 * Theme.scale ? 3 : 1
                    function body(pane) {
                        for (let i = 0; i < dataHeadings.count; i++) {
                            let entry = dataHeadings.itemAt(i)
                            if (entry && entry.modelData.id === pane) return entry.body
                        }
                        return hiddenBody
                    }
                    Item { id: hiddenBody; visible: false; Layout.fillWidth: true }
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    visible: window.selectedSection === 1
                    columnSpacing: Theme.sm
                    rowSpacing: Theme.sm
                    Repeater {
                        id: dataHeadings
                        model: [
                            {id:"rows", title:"Veri tablosu", detail:"Ana yüzey: kayıtları satır satır incele; sütun seç, sırala, filtrele."},
                            {id:"import", title:"Veriyi projeye aktar", detail:"Dosyanı seç, önizle ve projenle birlikte sakla."},
                            {id:"profile", title:"Veri profili", detail:"Sütun başlıklarını ve veri türlerini birlikte gör."},
                            {id:"values", title:"Sütun değerleri", detail:"Bir sütundaki değerleri ve tekrarlarını incele."},
                            {id:"describe", title:"Özet istatistikler", detail:"Sayısal sütunların dağılımını ve temel ölçülerini gör."},
                            {id:"quality", title:"Veri kalitesi", detail:"Eksik ve şüpheli kayıtları değerlendir."}
                        ]
                        ColumnLayout {
                            id: entry
                            required property var modelData
                            required property int index
                            property alias body: bodyLayout
                            Layout.fillWidth: true
                            Layout.columnSpan: window.dataPane === modelData.id ? dataSections.columns : 1
                            spacing: Theme.md
                            Button {
                                id: sectionHeading
                                objectName: "dataHeading_" + entry.modelData.id
                                text: entry.modelData.title
                                checkable: true
                                checked: window.dataPane === entry.modelData.id
                                Accessible.name: text
                                Accessible.description: entry.modelData.detail
                                Layout.fillWidth: true
                                implicitHeight: headingContent.implicitHeight + 2 * (window.dataPane ? Theme.sm : Theme.lg)
                                leftPadding: Theme.lg
                                rightPadding: Theme.lg
                                topPadding: window.dataPane ? Theme.sm : Theme.lg
                                bottomPadding: window.dataPane ? Theme.sm : Theme.lg
                                background: Rectangle {
                                    color: sectionHeading.checked ? Theme.cyanSurface : sectionHeading.hovered ? Theme.raised : Theme.surface
                                    radius: Theme.radius
                                    border.width: sectionHeading.visualFocus ? 2 : 1
                                    border.color: sectionHeading.checked || sectionHeading.visualFocus ? Theme.dataTone : Theme.border
                                    Rectangle { anchors.left: parent.left; anchors.leftMargin: 1; anchors.verticalCenter: parent.verticalCenter; width: 3; height: parent.height - 24; radius: 2; color: Theme.dataTone; visible: sectionHeading.checked }
                                }
                                contentItem: RowLayout {
                                    id: headingContent
                                    spacing: Theme.lg
                                    Rectangle {
                                        Layout.preferredWidth: (window.dataPane ? 28 : 38) * Theme.scale
                                        Layout.preferredHeight: (window.dataPane ? 28 : 38) * Theme.scale
                                        radius: Theme.radius
                                        color: sectionHeading.checked ? Theme.field : Theme.cyanSurface
                                        UiLabel { anchors.centerIn: parent; text: "0" + (entry.index + 1); font.bold: true; color: Theme.dataTone }
                                    }
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: Theme.xs
                                        UiLabel { text: entry.modelData.title; font.pixelSize: window.dataPane ? Theme.body : Theme.subheading; font.bold: true; Layout.fillWidth: true; wrapMode: Text.Wrap }
                                        UiLabel { visible: !window.dataPane; text: entry.modelData.detail; color: Theme.secondary; Layout.fillWidth: true; wrapMode: Text.Wrap }
                                    }
                                    UiLabel { text: sectionHeading.checked ? "−" : "+"; color: Theme.dataTone; font.pixelSize: Theme.heading }
                                }
                                onClicked: window.openDataPane(window.dataPane === entry.modelData.id ? "" : entry.modelData.id)
                            }
                            ColumnLayout {
                                id: bodyLayout
                                visible: window.dataPane === entry.modelData.id
                                Layout.fillWidth: true
                                Layout.leftMargin: Theme.lg
                                Layout.rightMargin: Theme.lg
                                Layout.bottomMargin: Theme.lg
                            }
                        }
                    }
                }
                QtObject {
                    id: dataTabs
                    objectName: "datasetTabs"
                    property int currentIndex: -1
                    function setCurrentIndex(index) { currentIndex = index }
                    onCurrentIndexChanged: {
                        if (currentIndex === 1) window.dataPane = "import"
                        else if (currentIndex === 2) window.dataPane = "quality"
                        else if (currentIndex === 0 && (!window.dataPane || window.dataPane === "import" || window.dataPane === "quality")) window.dataPane = "profile"
                    }
                }
                Connections { target: imports; function onChanged() { if (imports.busy) dataTabs.currentIndex = 1 } }
                DatasetPanel {
                    id: datasetViewPanel
                    parent: dataSections.body(window.dataPane)
                    pane: window.dataPane
                    onShowValues: window.openDataPane("values")
                    Layout.fillWidth: true
                    visible: window.selectedSection === 1 && dataTabs.currentIndex === 0 && window.dataPane !== ""
                    onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                }
                QualityPanel {
                    parent: dataSections.body("quality")
                    Layout.fillWidth: true
                    visible: window.selectedSection === 1 && dataTabs.currentIndex === 2
                    onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                }
                ImportPanel {
                    parent: dataSections.body("import")
                    onProjectRequested: { window.selectedSection = 0; Qt.callLater(function() { let control = window.findVisibleItem(window.contentItem, "newProjectButton"); if (control) control.forceActiveFocus() }) }
                    id: importPanel
                    Layout.fillWidth: true
                    visible: window.selectedSection === 1 && dataTabs.currentIndex === 1
                    onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                }
                WorkspacePanel {
                    objectName: "deferredChartPanel"
                    requested: window.selectedSection === 3
                    sourceComponent: ChartPanel {
                        onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                    }
                }
                WorkspacePanel {
                    objectName: "deferredDashboardPanel"
                    requested: window.advanced && window.selectedSection === 3
                    sourceComponent: DashboardPanel {
                        onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                    }
                }
                WorkspacePanel {
                    objectName: "deferredOperationsPanel"
                    requested: window.selectedSection === 2
                    sourceComponent: OperationsPanel {
                        onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                    }
                }
                WorkspacePanel {
                    objectName: "deferredWorkflowPanel"
                    requested: window.advanced && window.selectedSection === 2
                    sourceComponent: WorkflowPanel {
                        onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                    }
                }
                WorkspacePanel {
                    objectName: "deferredRecipePanel"
                    requested: window.advanced && window.selectedSection === 2
                    sourceComponent: RecipePanel {
                        onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                    }
                }
                Loader {
                    id: dimensionTools
                    property bool visited: false
                    readonly property bool expanded: item ? item.expanded : false
                    active: visited
                    Connections { target: window; function onAdvancedChanged() { if (window.advanced && window.selectedSection === 4) dimensionTools.visited = true } }
                    Component.onCompleted: if (window.advanced && window.selectedSection === 4) visited = true
                    Connections { target: window; function onSelectedSectionChanged() { if (window.advanced && window.selectedSection === 4) dimensionTools.visited = true } }
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    visible: window.advanced && window.selectedSection === 4 && !survivalTools.expanded && !causalTools.expanded && !bayesTools.expanded && !statisticalModels.expanded && !resamplingTools.expanded && !experimentTools.expanded
                    sourceComponent: DimensionsPanel { onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) } }
                }
                Loader {
                    id: survivalTools
                    property bool visited: false
                    readonly property bool expanded: item ? item.expanded : false
                    active: visited
                    Connections { target: window; function onAdvancedChanged() { if (window.advanced && window.selectedSection === 4) survivalTools.visited = true } }
                    Component.onCompleted: if (window.advanced && window.selectedSection === 4) visited = true
                    Connections { target: window; function onSelectedSectionChanged() { if (window.advanced && window.selectedSection === 4) survivalTools.visited = true } }
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    visible: window.advanced && window.selectedSection === 4 && !dimensionTools.expanded && !causalTools.expanded && !bayesTools.expanded && !statisticalModels.expanded && !resamplingTools.expanded && !experimentTools.expanded
                    sourceComponent: SurvivalPanel {
                        onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                    }
                }
                Loader {
                    id: causalTools
                    property bool visited: false
                    readonly property bool expanded: item ? item.expanded : false
                    active: visited
                    Connections { target: window; function onAdvancedChanged() { if (window.advanced && window.selectedSection === 4) causalTools.visited = true } }
                    Component.onCompleted: if (window.advanced && window.selectedSection === 4) visited = true
                    Connections { target: window; function onSelectedSectionChanged() { if (window.advanced && window.selectedSection === 4) causalTools.visited = true } }
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    visible: window.advanced && window.selectedSection === 4 && !dimensionTools.expanded && !survivalTools.expanded && !bayesTools.expanded && !statisticalModels.expanded && !resamplingTools.expanded && !experimentTools.expanded
                    sourceComponent: CausalPanel {
                        onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                    }
                }
                Loader {
                    id: bayesTools
                    property bool visited: false
                    readonly property bool expanded: item ? item.expanded : false
                    active: visited
                    Connections { target: window; function onAdvancedChanged() { if (window.advanced && window.selectedSection === 4) bayesTools.visited = true } }
                    Component.onCompleted: if (window.advanced && window.selectedSection === 4) visited = true
                    Connections { target: window; function onSelectedSectionChanged() { if (window.advanced && window.selectedSection === 4) bayesTools.visited = true } }
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    visible: window.advanced && window.selectedSection === 4 && !dimensionTools.expanded && !survivalTools.expanded && !causalTools.expanded && !statisticalModels.expanded && !resamplingTools.expanded && !experimentTools.expanded
                    sourceComponent: BayesPanel {
                        onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                    }
                }
                Loader {
                    id: experimentTools
                    property bool visited: false
                    readonly property bool expanded: item ? item.expanded : false
                    active: visited
                    Connections { target: window; function onAdvancedChanged() { if (window.advanced && window.selectedSection === 4) experimentTools.visited = true } }
                    Component.onCompleted: if (window.advanced && window.selectedSection === 4) visited = true
                    Connections { target: window; function onSelectedSectionChanged() { if (window.advanced && window.selectedSection === 4) experimentTools.visited = true } }
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    visible: window.advanced && window.selectedSection === 4 && !dimensionTools.expanded && !survivalTools.expanded && !causalTools.expanded && !statisticalModels.expanded && !resamplingTools.expanded && !bayesTools.expanded
                    sourceComponent: ExperimentPanel {
                        onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                    }
                }
                Loader {
                    id: resamplingTools
                    property bool visited: false
                    readonly property bool expanded: item ? item.expanded : false
                    active: visited
                    Connections { target: window; function onAdvancedChanged() { if (window.advanced && window.selectedSection === 4) resamplingTools.visited = true } }
                    Component.onCompleted: if (window.advanced && window.selectedSection === 4) visited = true
                    Connections { target: window; function onSelectedSectionChanged() { if (window.advanced && window.selectedSection === 4) resamplingTools.visited = true } }
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    visible: window.advanced && window.selectedSection === 4 && !dimensionTools.expanded && !survivalTools.expanded && !causalTools.expanded && !statisticalModels.expanded && !experimentTools.expanded && !bayesTools.expanded
                    sourceComponent: ResamplingPanel {
                        onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                    }
                }
                Loader {
                    id: statisticalModels
                    property bool visited: false
                    readonly property bool expanded: item ? item.expanded : false
                    active: visited
                    Connections { target: window; function onAdvancedChanged() { if (window.advanced && window.selectedSection === 4) statisticalModels.visited = true } }
                    Component.onCompleted: if (window.advanced && window.selectedSection === 4) visited = true
                    Connections {
                        target: window
                        function onSelectedSectionChanged() {
                            if (window.advanced && window.selectedSection === 4) statisticalModels.visited = true
                        }
                    }
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    visible: window.advanced && window.selectedSection === 4 && !dimensionTools.expanded && !survivalTools.expanded && !causalTools.expanded && !resamplingTools.expanded && !experimentTools.expanded && !bayesTools.expanded
                    sourceComponent: StatisticalModelsPanel {
                        onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                    }
                }
                StatisticsPanel {
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    visible: window.selectedSection === 4 && (!window.advanced || (!dimensionTools.expanded && !survivalTools.expanded && !causalTools.expanded && !statisticalModels.expanded && !resamplingTools.expanded && !experimentTools.expanded && !bayesTools.expanded))
                    onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                }
                ResultPanel {
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    expert: window.advanced
                    visible: window.advanced || (window.selectedSection === 4 && !!expertWorkspace.selected.id)
                    onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                }
                UiCombo {
                    id:modelPath
                    objectName:"modelPath"
                    visible:window.selectedSection===5
                    model:["Kayıt bazlı modelleme","Zaman serisi — geçmişten geleceğe","Yerel metin incelemesi"]
                    Layout.fillWidth:true;Layout.leftMargin:Theme.xl;Layout.rightMargin:Theme.xl
                    Accessible.name:"Modelleme yolu"
                }
                WorkspacePanel {
                    objectName: "deferredTextPanel"
                    requested: window.selectedSection===5&&modelPath.currentIndex===2
                    sourceComponent: TextPanel {
                        onHelpRequested:function(origin,context){window.openInformation(origin,"",context)}
                    }
                }
                WorkspacePanel {
                    objectName: "deferredTimeSeriesPanel"
                    requested: window.selectedSection===5&&modelPath.currentIndex===1
                    sourceComponent: TimeSeriesPanel {
                        onHelpRequested:function(origin,context){window.openInformation(origin,"",context)}
                    }
                }
                WorkspacePanel {
                    objectName: "deferredScenarioPanel"
                    requested: window.advanced && window.selectedSection === 5 && modelPath.currentIndex === 0
                    sourceComponent: ScenarioPanel {
                        onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                    }
                }
                WorkspacePanel {
                    objectName: "deferredMonitoringPanel"
                    requested: window.advanced && window.selectedSection === 5 && modelPath.currentIndex === 0
                    sourceComponent: MonitoringPanel {
                        onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                    }
                }
                WorkspacePanel {
                    objectName: "deferredPreparationPanel"
                    requested: window.selectedSection === 5 && modelPath.currentIndex === 0
                    sourceComponent: PreparationPanel {
                        onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                    }
                }
                StateNotice { objectName: "availabilityNotice"; visible: false; heading: "Henüz mevcut değil" }
                ScienceRoadmap {
                    Layout.fillWidth:true
                    Layout.leftMargin:Theme.xl
                    Layout.rightMargin:Theme.xl
                    visible:window.selectedSection===0 && !window.advanced
                    onNavigate:function(section,tab,origin){
                        if(origin && origin.expertRoute) preferences.setView("advanced")
                        window.navigate(section,window.findVisibleItem(window.contentItem,"nav"+section))
                        if(section===1){ window.openDataPane(tab<0 ? "" : origin && origin.route ? origin.route : tab===1?"import":"profile") }
                        const route=origin&&origin.route?origin.route:""
                        if(section===2&&route)Qt.callLater(function(){
                            let kind=window.findVisibleItem(window.contentItem,"operationKind")
                            if(!kind||!kind.enabled)return
                            kind.currentIndex=route==="clean"?3:4
                            kind.activated(kind.currentIndex)
                            kind.forceActiveFocus()
                            if(route==="join")Qt.callLater(function(){
                                let method=window.findVisibleItem(window.contentItem,"transformMethod")
                                if(method&&method.enabled){method.currentIndex=8;method.activated(8);method.forceActiveFocus()}
                            })
                        })
                        if(section===5&&route)Qt.callLater(function(){
                            if(route==="scenario" || route==="monitoring"){
                                modelPath.currentIndex=0
                                Qt.callLater(function(){let control=window.findVisibleItem(window.contentItem,route+"Expanded");if(control){control.checked=true;control.forceActiveFocus()}})
                                return
                            }
                            let clusterIds=["model.kmeans","model.dbscan","model.agglomerative","model.gmm","model.optics","model.hdbscan"]
                            let anomalyIds=["model.isolation-forest","model.iqr","model.lof","model.one-class-svm","model.robust-covariance"]
                            if(clusterIds.indexOf(route)>=0||anomalyIds.indexOf(route)>=0){
                                modelPath.currentIndex=0
                                let purpose=window.findVisibleItem(window.contentItem,"preparationPurpose")
                                let clustering=clusterIds.indexOf(route)>=0
                                if(purpose&&purpose.enabled){purpose.currentIndex=clustering?2:3;purpose.activated(purpose.currentIndex)}
                                Qt.callLater(function(){let choice=window.findVisibleItem(window.contentItem,"unsupervisedMethod");if(choice){choice.currentIndex=(clustering?clusterIds:anomalyIds).indexOf(route);choice.forceActiveFocus()}})
                                return
                            }

                            modelPath.currentIndex=route==="timeseries"?1:route==="text"?2:0
                            if(route==="timeseries"||route==="text")return
                            if(route==="classification"||route==="clustering"||route==="anomaly"){
                                let purpose=window.findVisibleItem(window.contentItem,"preparationPurpose")
                                if(purpose&&purpose.enabled){purpose.currentIndex=route==="classification"?1:route==="clustering"?2:3;purpose.activated(purpose.currentIndex);purpose.forceActiveFocus()}
                                return
                            }
                            let name=route==="validation"?"validationSettings":route==="regression"?"regressionUnit":"preparationSettings"
                            let control=window.findVisibleItem(window.contentItem,name)
                            if(control&&control.enabled)control.forceActiveFocus()
                        })
                        if(section===0)Qt.callLater(function(){
                            let button=window.findVisibleItem(window.contentItem,"newProjectButton")
                            if(button)button.forceActiveFocus()
                        })
                    }
                }

                UiLabel {
                    objectName: "journeyProjectHeading"
                    visible: window.selectedSection === 0 && !window.advanced
                    text: qsTr("Kendi yolculuğunu başlat")
                    font.pixelSize: Theme.heading; font.bold: true
                    Layout.fillWidth: true; Layout.leftMargin: Theme.xl; Layout.rightMargin: Theme.xl
                    wrapMode: Text.Wrap
                }
                UiLabel {
                    visible: window.selectedSection === 0 && !window.advanced
                    text: qsTr("Yeni bir proje oluştur veya kayıtlı çalışmanı aç. Veriyi ekledikten sonra haritadaki adımlara istediğin sırada dönebilirsin; kaydetmek çalışmanı korur.")
                    color: Theme.secondary; wrapMode: Text.Wrap
                    Layout.fillWidth: true; Layout.leftMargin: Theme.xl; Layout.rightMargin: Theme.xl
                }
                ProjectPanel {
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    visible: window.selectedSection === 0
                    onHelpRequested: function(origin) { window.openInformation(origin, "", "project") }
                }

                LearningCenter {
                    objectName: "learningCenter"
                    visible: window.selectedSection === 7
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    library: learning
                    onArticleRequested: function(articleId, origin) { window.openReading(origin, articleId) }
                }
                // Results and errors remain visible in either view, even if trial controls are collapsed.
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    spacing: Theme.md
                    StateNotice {
                        objectName: "taskNotice"
                        visible: !!startupError || !!(bridge && bridge.jobId)
                        Layout.fillWidth: true
                        kind: startupError || (bridge && bridge.errorText) ? "error" : (bridge && bridge.active ? "loading" : (bridge && bridge.stateCode === "canceled" ? "canceled" : "empty"))
                        heading: startupError ? qsTranslate("Shell", "Unavailable") : (bridge && bridge.jobId ? qsTranslate("Main", "Task infrastructure test") + " · " + bridge.stateText : qsTranslate("Shell", "Local workspace ready"))
                        detail: bridge && bridge.jobId ? qsTranslate("Shell", "Infrastructure trial · No dataset analysis") : qsTranslate("Shell", "View is saved on this computer.")
                    }
                    UiLabel { visible: !!(bridge && bridge.jobId); objectName: "stateLabel"; text: bridge ? bridge.stateText : qsTranslate("Main", "Unavailable"); Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    UiLabel { objectName: "resultLabel"; text: bridge ? bridge.resultText : ""; visible: text.length > 0; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    UiLabel { objectName: "errorLabel"; text: startupError || (bridge ? bridge.errorText : ""); visible: text.length > 0; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere; color: Theme.error }
                    ProgressBar {
                        objectName: "jobProgress"
                        Layout.fillWidth: true
                        indeterminate: bridge && bridge.active && bridge.progress < 0
                        value: bridge && bridge.progress >= 0 ? bridge.progress : 0
                        visible: bridge && bridge.active
                        Accessible.name: qsTranslate("Shell", "Task progress")
                    }
                    UiButton { objectName: "cancelButton"; helpContext: "demo.cpu"; text: qsTranslate("Main", "Cancel task"); glyph: "×"; visible: bridge && bridge.active; enabled: bridge && bridge.active && !bridge.closing; onClicked: bridge.cancel() }
                    UiButton {
                        objectName: "demoToggle"
                        visible: window.advanced || window.showDemo
                        text: qsTranslate("Shell", "Infrastructure trials")
                        glyph: window.showDemo ? "−" : "+"
                        checkable: true
                        checked: window.showDemo
                        onClicked: window.showDemo = !window.showDemo
                    }
                    Frame {
                        Layout.fillWidth: true
                        visible: window.showDemo
                        padding: Theme.lg
                        background: Rectangle { color: Theme.surface; border.color: Theme.border; radius: Theme.radius }
                        ColumnLayout {
                            width: parent.width
                            spacing: Theme.lg
                            UiLabel { text: qsTranslate("Shell", "These trials check the app. They do not load or analyze data."); Layout.fillWidth: true; wrapMode: Text.WordWrap }
                            Flow {
                                Layout.fillWidth: true
                                spacing: Theme.sm
                                UiButton { objectName: "cpuButton"; helpContext: "demo.cpu"; width: Math.min(implicitWidth, parent.width); multiline: true; text: qsTranslate("Main", "Run CPU test"); enabled: bridge && !bridge.active && !bridge.closing; onClicked: bridge.start("demo.cpu") }
                                UiButton { objectName: "ioButton"; helpContext: "demo.io"; width: Math.min(implicitWidth, parent.width); multiline: true; text: qsTranslate("Main", "Run I/O test"); enabled: bridge && !bridge.active && !bridge.closing; onClicked: bridge.start("demo.io") }
                                UiButton { objectName: "unknownButton"; helpContext: "demo.unknown"; width: Math.min(implicitWidth, parent.width); multiline: true; text: qsTranslate("Main", "Test unknown progress"); enabled: bridge && !bridge.active && !bridge.closing; onClicked: bridge.start("demo.unknown") }
                            }
                        }
                    }
                    UiButton {
                        objectName: "computeBudgetButton"
                        text: qsTr("Hesaplama bütçesi ve ölçümler")
                        helpContext: "compute.resources"
                        Layout.fillWidth: true
                        onClicked: computeDialog.open()
                    }
                    Frame {
                        objectName: "technicalSettings"
                        Layout.fillWidth: true
                        visible: window.advanced
                        padding: Theme.lg
                        background: Rectangle { color: Theme.surface; border.color: Theme.border; radius: Theme.radius }
                        ColumnLayout {
                            width: parent.width
                            spacing: Theme.md
                            UiLabel { text: qsTranslate("Shell", "Technical details"); font.pixelSize: Theme.subheading; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                            UiLabel { text: qsTranslate("Main", "Change the test configuration while a task is running to verify that old results are not applied."); Layout.fillWidth: true; wrapMode: Text.WordWrap }
                            UiLabel { objectName: "bindingLabel"; text: qsTranslate("Shell", "Session:") + " " + (bridge ? bridge.sessionVersion : "—"); Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
                            UiLabel { text: qsTranslate("Main", "Task ID:") + " " + (bridge ? bridge.jobId : "—"); Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
                            UiLabel { text: qsTranslate("Main", "Configuration revision:") + " " + (bridge ? bridge.revision : 0); Layout.fillWidth: true; wrapMode: Text.WordWrap }
                            Flow {
                                Layout.fillWidth: true
                                spacing: Theme.sm
                                UiButton { objectName: "contextButton"; width: Math.min(implicitWidth, parent.width); multiline: true; text: qsTranslate("Main", "Change test configuration"); enabled: bridge && !bridge.closing; onClicked: bridge.changeConfiguration() }
                                UiButton { objectName: "failureButton"; helpContext: "demo.failure"; width: Math.min(implicitWidth, parent.width); multiline: true; text: qsTranslate("Main", "Test error transfer"); enabled: bridge && !bridge.active && !bridge.closing; onClicked: bridge.start("demo.failure") }
                            }
                        }
                    }
                }
                Item { Layout.preferredHeight: Theme.xl }
            }
        }
        ContextSidePanel {
            id: contextPanel
            objectName: "contextSidePanelHost"
            Layout.fillHeight: true
            Layout.preferredWidth: Math.min(300 * Theme.scale, Math.max(220, window.width * 0.22))
            visible: window.contextPanelOpen && !(window.dockInfo && window.infoOpen && !window.readingOpen)
            uxStage: window.uxStage
            stageTitle: window.uxStageInfo.title
            stageQuestion: window.uxStageQuestions[window.uxStage] || ""
            onCloseRequested: window.contextPanelOpen = false
            onLearnRequested: function(origin) { window.openInformation(origin) }
            onColumnChosen: function(columnId) {
                if (window.selectedSection !== 1) window.navigate(1, null)
                if (!window.dataPane || window.dataPane === "import") window.openDataPane("profile")
            }
        }
        InfoPanel {
            id: dockPanel
            objectName: "dockedInformation"
            Layout.fillHeight: true
            Layout.preferredWidth: 320 * Theme.scale
            visible: window.dockInfo && window.infoOpen && !window.readingOpen
            heading: window.sections[window.selectedSection]
            detail: window.descriptions[window.selectedSection]
            onCloseRequested: window.closeInformation()
        }
    }
    Dialog {
        id: unsavedDialog
        objectName: "unsavedProjectDialog"
        title: qsTr("Kaydedilmemiş değişiklikler")
        modal: true
        anchors.centerIn: parent
        width: Math.min(520, window.width - 40)
        ColumnLayout {
            anchors.fill: parent
            UiLabel { text: qsTr("Kapanmadan önce proje değişikliklerini kaydetmek ister misiniz?"); Layout.fillWidth: true; wrapMode: Text.WordWrap }
            UiLabel { text: projects.errorText; visible: text.length > 0; color: Theme.error; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            UiButton { text: qsTr("Kaydet ve kapat"); Layout.fillWidth: true; onClicked: { window.closeAfterSave = true; projects.request("save") } }
            UiButton { text: qsTr("Değişiklikleri bırak ve kapat"); Layout.fillWidth: true; onClicked: { window.discardOnExit = true; unsavedDialog.close(); window.close() } }
            UiButton { text: qsTr("Çalışmaya dön"); Layout.fillWidth: true; onClicked: unsavedDialog.close() }
        }
    }
    Connections { target: projects; function onSaveFinished(success) { if (window.closeAfterSave) { window.closeAfterSave = false; if (success) { unsavedDialog.close(); window.close() } } } }
    Shortcut { objectName: "saveProjectShortcut"; sequence: "Ctrl+S"; enabled: !startupError; onActivated: projects.request("save") }
    Shortcut { objectName: "openProjectShortcut"; sequence: "Ctrl+O"; enabled: !startupError; onActivated: { window.selectedSection = 0; window.findVisibleItem(window.contentItem, "openProjectButton").clicked() } }
    LaboratoryWindow { id: lessonLab; library: learning; lab: learningLab; onArticleRequested: function(articleId, origin) { window.openReading(origin, articleId); window.requestActivate() } }
    Connections { target: learningLab; function onOpened() { lessonLab.show(); lessonLab.requestActivate() } }
    ExampleWindow {
        id: learningExample
        library: learning.exampleLibrary
        onClosing: { window.requestActivate(); window.restoreHelpFocus() }
    }
    Connections { target: learning; function onExampleRequested() { learningExample.show(); learningExample.requestActivate() } }
    Dialog {
        id: articleReader
        objectName: "learningReader"
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(850 * Theme.scale, window.width - 32)
        height: Math.min(820 * Theme.scale, window.height - 48)
        modal: true
        focus: true
        padding: Theme.lg
        closePolicy: Popup.CloseOnEscape
        background: Rectangle { color: Theme.surface; radius: Theme.radius; border.color: Theme.learningTone }
        onClosed: if (window.readingOpen) window.closeInformation()
        header: RowLayout {
            spacing: Theme.md
            UiLabel { text: qsTr("Öğren · ") + learning.article.category; color: Theme.learningTone; font.bold: true; Layout.fillWidth: true; Layout.leftMargin: Theme.lg; wrapMode: Text.WordWrap }
            UiIconButton { objectName: "learningReaderClose"; symbol: "close"; accessibleLabel: qsTr("Okuma penceresini kapat"); Layout.rightMargin: Theme.md; onClicked: window.closeInformation() }
        }
        contentItem: ScrollView {
            id: readerScroll
            clip: true
            contentWidth: availableWidth
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ArticleView { width: readerScroll.availableWidth; library: learning; readingMode: true }
        }
        onOpened: { readerScroll.contentItem.contentY = 0; readerScroll.forceActiveFocus() }
        Connections { target: learning; function onChanged() { if (window.readingOpen) readerScroll.contentItem.contentY = 0 } }
    }
    Drawer {
        id: infoDrawer
        objectName: "informationDrawer"
        edge: Qt.RightEdge
        y: window.header.height
        width: Math.min(400 * Theme.scale, window.width - 32)
        height: window.height - y
        modal: true
        focus: true
        dim: false
        interactive: true
        dragMargin: 0
        closePolicy: Popup.CloseOnEscape
        padding: 0
        onClosed: { if (!window.dockInfo && window.infoOpen) window.closeInformation() }
        InfoPanel {
            anchors.fill: parent
            heading: window.sections[window.selectedSection]
            detail: window.descriptions[window.selectedSection]
            onCloseRequested: window.closeInformation()
        }
    }
}
