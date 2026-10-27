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
    property int selectedSection: 1
    property int prepareTool: 0
    property int chartTool: 0
    property int examineTool: 0
    property int reportTool: 0
    property bool sawProject: false
    property bool dockDismissed: false
    readonly property bool veriEmpty: {
        if (selectedSection !== 1)
            return false
        let sets = dataView && dataView.datasets ? dataView.datasets.length : 0
        return sets === 0
    }
    readonly property bool dockRequested: {
        if (selectedSection === 0 || selectedSection === 7)
            return true
        if (selectedSection >= 2 && selectedSection <= 6)
            return true
        if (selectedSection !== 1)
            return false
        if (dataPane === "quality")
            return true
        let sets = dataView && dataView.datasets ? dataView.datasets.length : 0
        return sets > 0
    }
    readonly property bool dockOpen: dockRequested && !dockDismissed
    readonly property bool inceleOpen: {
        if (selectedSection !== 1 || dataPane !== "quality")
            return false
        let sets = dataView && dataView.datasets ? dataView.datasets.length : 0
        return sets > 0
    }
    readonly property bool veriWorkspaceDock: selectedSection === 1 && dataPane !== "quality" && dataView && dataView.datasets && dataView.datasets.length > 0
    readonly property bool inspectWorkspaceDock: inceleOpen
    readonly property bool gorsellestirOpen: {
        if (selectedSection !== 3 || chartTool !== 0)
            return false
        let sets = dataView && dataView.datasets ? dataView.datasets.length : 0
        return sets > 0
    }
    readonly property bool visualizeWorkspaceDock: gorsellestirOpen
    readonly property bool hazirlaOpen: {
        if (selectedSection !== 2 || prepareTool !== 0)
            return false
        let sets = dataView && dataView.datasets ? dataView.datasets.length : 0
        return sets > 0
    }
    readonly property bool prepareWorkspaceDock: hazirlaOpen
    readonly property bool istatistikOpen: {
        if (selectedSection !== 4 || examineTool !== 0)
            return false
        let sets = dataView && dataView.datasets ? dataView.datasets.length : 0
        return sets > 0
    }
    readonly property bool statisticsWorkspaceDock: istatistikOpen
    readonly property bool modelInstalled: expertWorkspace.modelModule.installed === true
    readonly property bool modelOpen: {
        if (selectedSection !== 5 || !modelInstalled)
            return false
        let sets = dataView && dataView.datasets ? dataView.datasets.length : 0
        return sets > 0
    }
    readonly property bool modelWorkspaceDock: modelOpen
    readonly property bool raporlaOpen: selectedSection === 6 && reportTool === 0 && projects.opened
    readonly property bool reportWorkspaceDock: raporlaOpen
    readonly property bool slimToolDock: veriWorkspaceDock || inspectWorkspaceDock || visualizeWorkspaceDock || prepareWorkspaceDock || statisticsWorkspaceDock || modelWorkspaceDock || reportWorkspaceDock
    readonly property bool quietHeader: selectedSection === 1 || gorsellestirOpen || hazirlaOpen || istatistikOpen || modelOpen || raporlaOpen
    readonly property string moduleKey: {
        if (selectedSection === 0)
            return ""
        if (selectedSection === 7)
            return "ogren"
        if (selectedSection === 3)
            return "gorsellestir"
        if (selectedSection === 2)
            return "hazirla"
        if (selectedSection === 4)
            return "istatistik"
        if (selectedSection === 5)
            return "model"
        if (selectedSection === 6)
            return "raporla"
        if (selectedSection === 1 && dataPane === "quality")
            return "incele"
        if (selectedSection === 1)
            return "veri"
        return ""
    }
    function openIncele(origin) {
        let hasData = dataView && dataView.datasets && dataView.datasets.length > 0
        if (!projects.opened || !hasData) {
            openVeri(origin)
            return
        }
        navigate(1, origin)
        openDataPane("quality")
    }
    function openVeri(origin) {
        navigate(1, origin)
        let hasData = dataView && dataView.datasets && dataView.datasets.length > 0
        openDataPane(hasData ? "rows" : "")
        dockDismissed = false
    }
    function openModel(origin) {
        navigate(modelInstalled ? 5 : 6, origin)
    }
    readonly property bool showTable: {
        if (selectedSection !== 1 || dataPane !== "rows")
            return false
        let sets = dataView && dataView.datasets ? dataView.datasets.length : 0
        return sets > 0
    }
    readonly property bool centerOpen: showTable || window.veriEmpty || window.inceleOpen || window.gorsellestirOpen || window.hazirlaOpen || window.istatistikOpen || window.modelOpen || window.raporlaOpen
    readonly property string veriContextLine: {
        if (selectedSection !== 1 && !gorsellestirOpen && !hazirlaOpen && !istatistikOpen && !modelOpen && !raporlaOpen)
            return projects.context
        if (!projects.opened)
            return qsTr("Proje açık değil")
        let content = dataView && dataView.dataContent ? dataView.dataContent : ({})
        let ver = content.version ? (qsTr("sürüm ") + String(content.version).slice(-8)) : ""
        let src = content.source ? (qsTr("kaynak ") + content.source) : ""
        let parts = [projects.name]
        if (ver)
            parts.push(ver)
        if (src)
            parts.push(src)
        return parts.join(" · ")
    }
    readonly property string veriScopeLine: {
        if ((!window.showTable && !window.inceleOpen && !window.gorsellestirOpen && !window.hazirlaOpen && !window.istatistikOpen) || !dataView)
            return ""
        let content = dataView.dataContent || ({})
        let total = dataView.totalRows || content.rows || 0
        let cols = content.columns || 0
        let start = total === 0 ? 0 : dataView.pageOffset + 1
        let end = Math.min(total, dataView.pageOffset + dataView.pageRowCount)
        let ver = content.version ? (qsTr("sürüm ") + String(content.version).slice(-8)) : ""
        let line = total + qsTr(" satır · ") + cols + qsTr(" sütun")
              + (ver ? (" · " + ver) : "")
        // Veri tablosu: mockup sakin satır (sayfa aralığı yok). Diğer modüller sayfa penceresini korur.
        let veriTableOnly = window.showTable && !window.inceleOpen && !window.gorsellestirOpen && !window.hazirlaOpen && !window.istatistikOpen
        if (!veriTableOnly && total > 0)
            line += " · " + qsTr("satır ") + start + "–" + end + " / " + total
        if (window.inceleOpen) {
            let q = dataView.qualityResult || ({})
            if (q.dataset_version) {
                let scope = ({ full: qsTr("tam veri"), filtered: qsTr("filtreli"), sample: qsTr("örneklem") })[q.scope] || q.scope
                line += " · " + qsTr("tarama ") + scope + " " + q.used_n + "/" + q.population_n
            } else {
                line += " · " + qsTr("tarama yok")
            }
        }
        if (window.gorsellestirOpen) {
            let c = charts.chartResult || ({})
            if (c.dataset_version) {
                let scope = ({ full: qsTr("tam veri"), view: qsTr("filtreli"), sample: qsTr("örneklem") })[c.scope] || c.scope
                if (c.scope === "sample")
                    line += " · " + qsTr("grafik örneklem ") + c.used_n + "/" + c.population_n
                else
                    line += " · " + qsTr("grafik ") + scope + " " + c.used_n + "/" + c.population_n
            } else {
                line += " · " + qsTr("grafik yok")
            }
        }
        if (window.hazirlaOpen) {
            let impact = (operations.previewResult && operations.previewResult.impact) ? operations.previewResult.impact : null
            if (impact && impact.before_rows !== undefined) {
                let scope = ({ full: qsTr("tam veri"), view: qsTr("görünüm"), sample: qsTr("örneklem") })[impact.scope] || impact.scope || qsTr("tam veri")
                line += " · " + qsTr("önizleme ") + scope + " · " + qsTr("etkilenen ") + (impact.changed_rows || 0)
            } else {
                line += " · " + qsTr("önizleme yok")
            }
        }
        if (window.istatistikOpen) {
            let a = statistics.analysisResult || ({})
            if (a.primary) {
                line += " · " + qsTr("analiz n=") + JSON.stringify(a.n) + qsTr(" · dışlanan ") + (a.excluded_rows || 0)
            } else if (statistics.preflightCurrent) {
                let p = statistics.preflightResult || ({})
                line += " · " + qsTr("önkontrol ") + (p.used_rows || 0) + "/" + (p.population_n || 0)
            } else {
                line += " · " + qsTr("analiz yok")
            }
        }
        return line
    }
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
        if (workspace.contentItem)
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
        if (origin) origin.forceActiveFocus()
        if (workspace.contentItem)
            workspace.contentItem.contentY = 0
    }
    onSelectedSectionChanged: {
        if (selectedSection === 5 && !modelInstalled) {
            selectedSection = 6
            return
        }
        dockDismissed = false
        if (workspace.contentItem)
            workspace.contentItem.contentY = 0
        window.syncUxStageFromSection()
    }
    onDataPaneChanged: {
        if (dataPane === "import" || dataPane === "quality")
            dockDismissed = false
        window.syncUxStageFromSection()
    }
    function openReading(origin, articleId) {}
    function openInformation(origin, articleId, context) {}
    function focusedHelpContext() {
        return ""
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
        if (displayButton && displayButton.visible)
            displayButton.forceActiveFocus()
    }
    function closeInformation() {
        infoOpen = false
        readingOpen = false
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
                UiLabel { text: qsTr("Arayüz dili"); Layout.fillWidth: true; wrapMode: Text.Wrap }
                UiCombo {
                    id: displayLocale
                    objectName: "displayLocale"
                    accessibleLabel: qsTr("Arayüz dili")
                    model: ["Türkçe", "English", "Azərbaycan", "Türkmençe", "Қазақша", "Oʻzbekcha", "Русский", "Español"]
                    readonly property var localeCodes: ["tr", "en", "az", "tk", "kk", "uz", "ru", "es"]
                    currentIndex: Math.max(0, localeCodes.indexOf(preferences ? preferences.locale : "tr"))
                    Layout.fillWidth: true
                    onActivated: preferences.setLocale(localeCodes[currentIndex])
                }
                UiLabel { objectName: "localeBoundaryNotice"; text: qsTr("Menü, tablo, içe aktarma, kalite, grafik, hazırlık, istatistik, rapor ve proje metinleri seçilen dile çevrilir. Uzman analiz formları ve öğrenme yazıları Türkçe kalır. Dil, dosyanın sayı ve tarih okuma ayarlarını değiştirmez."); Layout.fillWidth: true; wrapMode: Text.Wrap }
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
        if (bridge && !bridge.closed) {
            event.accepted = false
            bridge.shutdown()
        }
    }
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
                    visible: !window.quietHeader
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
                    text: (window.selectedSection === 1 || window.gorsellestirOpen || window.hazirlaOpen || window.istatistikOpen || window.modelOpen || window.raporlaOpen) ? window.veriContextLine : projects.context
                    color: Theme.secondary
                    wrapMode: Text.WordWrap
                    elide: Text.ElideMiddle
                }
                RowLayout {
                    spacing: Theme.sm
                    UiIconButton {
                        objectName: "commandSearchButton"
                        visible: !window.quietHeader
                        symbol: "search"
                        accessibleLabel: qsTr("Yöntem ve amaç ara (Ctrl+K)")
                        onClicked: { expertWorkspace.search(""); commandPalette.open() }
                    }
                    UiButton {
                        objectName: "headerBack"
                        text: qsTr("Geri")
                        quiet: true
                        onClicked: {
                            if (window.selectedSection === 1)
                                window.navigate(0, null)
                            else if (window.selectedSection > 0)
                                window.openVeri(null)
                            else
                                window.navigate(0, null)
                        }
                    }
                    UiButton {
                        objectName: "headerOpenProject"
                        visible: !window.quietHeader
                        text: qsTr("Aç")
                        quiet: true
                        onClicked: {
                            window.navigate(0, null)
                            Qt.callLater(function() {
                                let button = window.findVisibleItem(window.contentItem, "openProjectButton")
                                if (button) button.clicked()
                            })
                        }
                    }
                    UiButton {
                        objectName: "headerSaveProject"
                        text: qsTr("Kaydet")
                        quiet: true
                        enabled: projects.opened && !projects.readOnly
                        onClicked: projects.request("save")
                    }
                    UiIconButton {
                        id: displayButton
                        objectName: "displayButton"
                        visible: !window.quietHeader
                        symbol: "settings"
                        accessibleLabel: qsTr("Görünüm ve dil")
                        onClicked: displayDialog.open()
                    }
                    UiIconButton {
                        objectName: "closeButton"
                        visible: !window.quietHeader
                        symbol: "close"
                        accessibleLabel: qsTr("Uygulamayı kapat")
                        onClicked: window.close()
                    }
                }
            }
            UiLabel {
                visible: window.width < 1000 * Theme.scale
                text: (window.selectedSection === 1 || window.gorsellestirOpen || window.hazirlaOpen || window.istatistikOpen || window.modelOpen || window.raporlaOpen) ? window.veriContextLine : projects.context
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
                text: projects.busy ? qsTr("Proje işlemi sürüyor…") : (projects.opened && projects.dirty) ? qsTr("Kaydedilmemiş değişiklikler") : projects.opened ? qsTr("Proje açık") : qsTr("Proje açık değil")
                font.pixelSize: Theme.small
                color: projects.opened && projects.dirty ? Theme.warning : Theme.secondary
                elide: Text.ElideRight
            }
            UiButton {
                objectName: "statusSaveProject"
                visible: projects.opened && projects.dirty && !projects.readOnly && !projects.busy
                text: qsTr("Kaydet")
                primary: true
                onClicked: projects.request("save")
            }
            UiLabel {
                objectName: "datasetPageScope"
                visible: (window.showTable || window.inceleOpen || window.gorsellestirOpen || window.hazirlaOpen || window.istatistikOpen) && window.veriScopeLine.length > 0
                text: window.veriScopeLine
                font.pixelSize: Theme.small
                color: Theme.secondary
                elide: Text.ElideRight
                Layout.fillWidth: true
                Layout.minimumWidth: 0
            }
            UiLabel {
                objectName: "datasetScopeStatus"
                visible: window.width >= 1100 * Theme.scale
                         && (window.inceleOpen || window.gorsellestirOpen || window.hazirlaOpen || window.istatistikOpen)
                         && !window.showTable
                text: qsTr("Sayfa en fazla 200 satır.")
                font.pixelSize: Theme.small
                color: Theme.secondary
                elide: Text.ElideRight
                Layout.maximumWidth: window.width * 0.28
            }
            UiLabel {
                visible: window.width >= 1000 * Theme.scale && !window.showTable
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
                    ModuleRail {
                        compact: window.compactNavigation
                        currentSection: window.selectedSection
                        currentKey: window.moduleKey
                        modelInstalled: window.modelInstalled
                        Layout.fillWidth: true
                        onModuleChosen: function(section, key, origin) {
                            if (key === "veri")
                                window.openVeri(origin)
                            else if (key === "incele")
                                window.openIncele(origin)
                            else if (key === "model")
                                window.openModel(origin)
                            else
                                window.navigate(section, origin)
                        }
                    }
                }
            }
        }
        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal
            handle: Rectangle {
                implicitWidth: 8
                color: Theme.border
                Rectangle {
                    anchors.centerIn: parent
                    width: 2
                    height: 28
                    radius: 1
                    color: Theme.controlBorder
                }
            }
        Item {
            id: centerPane
            objectName: "workspace"
            visible: window.centerOpen
            SplitView.fillWidth: window.centerOpen
            SplitView.minimumWidth: window.centerOpen ? 280 : 0
            SplitView.preferredWidth: window.centerOpen ? 640 : 0
            SplitView.maximumWidth: window.centerOpen ? 100000 : 0
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.lg
                spacing: Theme.lg
                UiCombo {
                    objectName: "dataTool"
                    visible: false
                    accessibleLabel: qsTr("Veri aracı")
                    model: [qsTr("Tablo"), qsTr("İçe aktar"), qsTr("Kalite")]
                    currentIndex: window.dataPane === "import" ? 1 : window.dataPane === "quality" ? 2 : 0
                    Layout.fillWidth: true
                    onActivated: window.openDataPane(currentIndex === 1 ? "import" : currentIndex === 2 ? "quality" : "rows")
                }
                DataEmptyCard {
                    visible: window.veriEmpty
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                }
                ColumnLayout {
                    id: tableHost
                    visible: window.showTable || window.inceleOpen
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: Theme.sm
                    InspectScanStrip {
                        id: inspectScanStrip
                        visible: window.inceleOpen
                        Layout.fillWidth: true
                        selectedBlock: inspectWorkspacePanel.selectedBlock
                        onCardChosen: function(block) { inspectWorkspacePanel.selectedBlock = block }
                    }
                    Item {
                        id: tableBody
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 160
                    }
                }
                VisualizeWorkspace {
                    id: visualizeWorkspace
                    visible: window.gorsellestirOpen
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    chartControls: deferredChartPanel.item
                    onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                }
                PrepareWorkspace {
                    id: prepareWorkspace
                    visible: window.hazirlaOpen
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    catalogControls: deferredOperationsPanel.item
                    onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                }
                StatisticsWorkspace {
                    id: statisticsWorkspace
                    visible: window.istatistikOpen
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    catalogControls: deferredStatisticsPanel.item
                    onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                }
                ModelWorkspace {
                    id: modelWorkspace
                    visible: window.modelOpen
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    catalogControls: deferredModelCatalogPanel.item
                    onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                }
                ReportWorkspace {
                    id: reportWorkspace
                    visible: window.raporlaOpen
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    catalogControls: deferredReportCatalogPanel.item
                    onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                }
            }
        }
        ScrollView {
            id: workspace
            objectName: "toolDock"
            enabled: !startupError || window.selectedSection === 7
            visible: window.dockOpen
            SplitView.fillWidth: window.dockOpen && !window.centerOpen
            SplitView.preferredWidth: !window.dockOpen ? 0 : window.centerOpen ? Math.min(420, Math.round(window.width * 0.34)) : Math.max(280, window.width)
            SplitView.minimumWidth: window.dockOpen ? 280 : 0
            SplitView.maximumWidth: !window.dockOpen ? 0 : window.centerOpen ? Math.max(280, Math.round(window.width * 0.5)) : 100000
            clip: true
            contentWidth: availableWidth
            ColumnLayout {
                width: workspace.availableWidth
                spacing: Theme.xl
                Item { Layout.preferredHeight: Theme.xs }
                GridLayout {
                    visible: !window.slimToolDock
                    columns: workspace.availableWidth < 650 * Theme.scale ? 1 : 2
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    UiLabel {
                        Layout.fillWidth: true
                        text: window.moduleKey === "incele" ? qsTr("İncele") : window.moduleKey === "gorsellestir" ? qsTr("Grafik") : window.sections[window.selectedSection]
                        color: window.sectionAccent
                        font.pixelSize: Theme.heading
                        font.bold: true
                        wrapMode: Text.WrapAnywhere
                    }
                }
                UiLabel {
                    visible: !window.slimToolDock
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
                UiButton {
                    objectName: "dockClose"
                    visible: !window.slimToolDock
                    text: qsTr("Kapat")
                    quiet: true
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    onClicked: window.dockDismissed = true
                }
                UiCombo {
                    objectName: "chartToolPicker"
                    visible: window.selectedSection === 3 && !window.slimToolDock
                    accessibleLabel: qsTr("Grafik aracı")
                    model: [qsTr("Grafik"), qsTr("Pano")]
                    currentIndex: window.chartTool
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    onActivated: window.chartTool = currentIndex
                }
                UiCombo {
                    objectName: "chartToolPickerSlim"
                    visible: window.gorsellestirOpen
                    accessibleLabel: qsTr("Grafik aracı")
                    model: [qsTr("Grafik"), qsTr("Pano")]
                    currentIndex: window.chartTool
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    onActivated: window.chartTool = currentIndex
                }
                UiCombo {
                    objectName: "examineToolPicker"
                    visible: window.selectedSection === 4
                    accessibleLabel: qsTr("İnceleme aracı")
                    model: [qsTr("İstatistik"), qsTr("Boyut"), qsTr("Sağkalım"), qsTr("Nedensel"), qsTr("Bayes"), qsTr("Deney"), qsTr("Yeniden örnekleme"), qsTr("Modeller")]
                    currentIndex: window.examineTool
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    onActivated: window.examineTool = currentIndex
                }
                UiCombo {
                    objectName: "prepareToolPicker"
                    visible: window.selectedSection === 2
                    accessibleLabel: qsTr("Hazırlık aracı")
                    model: [qsTr("İşlemler"), qsTr("İş akışı"), qsTr("Tarif")]
                    currentIndex: window.prepareTool
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    onActivated: window.prepareTool = currentIndex
                }
                UiCombo {
                    objectName: "reportToolPicker"
                    visible: window.selectedSection === 6
                    accessibleLabel: qsTr("Rapor aracı")
                    model: [qsTr("Rapor"), qsTr("Yeniden üretilebilirlik"), qsTr("Kod"), qsTr("Ortam"), qsTr("Eklentiler"), qsTr("Paylaşım")]
                    currentIndex: window.reportTool
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    onActivated: window.reportTool = currentIndex
                }
                Connections { target:launchRequests; function onNavigate(section,tab) { window.selectedSection=section; if(section===1) dataTabs.currentIndex=tab } }
                UiButton {
                    objectName: "expertToolsEntry"
                    visible: false
                    quiet: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    onClicked: preferences.setView("advanced")
                }
                UiLabel {
                    objectName: "reportWithoutModel"
                    visible: window.selectedSection === 6 && !window.modelInstalled
                    text: "Model modülü kurulu değil. Kayıtlı istatistik bulguları rapora gelir. Model metriği uydurulmaz."
                    color: Theme.warning
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    wrapMode: Text.Wrap
                }
                WorkspacePanel {
                    id: deferredReportCatalogPanel
                    objectName: "deferredReportCatalogPanel"
                    requested: window.raporlaOpen
                    sourceComponent: ReportCatalogPanel {
                        onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                    }
                }
                WorkspacePanel {
                    objectName: "deferredReportBuilderPanel"
                    requested: window.selectedSection===6 && (window.advanced || window.reportTool===0)
                    visible: requested && (!window.raporlaOpen || window.advanced)
                    sourceComponent: ReportBuilderPanel {
                        onHelpRequested:function(origin,context){window.openInformation(origin,"",context)}
                    }
                }
                WorkspacePanel {
                    objectName: "deferredReportPanel"
                    requested: window.selectedSection===6 && (window.advanced || window.reportTool===0)
                    visible: requested && (!window.raporlaOpen || window.advanced)
                    sourceComponent: ReportPanel {
                        onHelpRequested:function(origin,context){window.openInformation(origin,"",context)}
                    }
                }
                WorkspacePanel {
                    objectName: "deferredReproPanel"
                    requested: window.selectedSection===6 && (window.advanced || window.reportTool===1)
                    sourceComponent: ReproPanel {
                        onHelpRequested:function(origin,context){window.openInformation(origin,"",context)}
                    }
                }
                WorkspacePanel {
                    objectName: "deferredCodePanel"
                    requested: window.selectedSection===6 && (window.advanced || window.reportTool===2)
                    sourceComponent: CodePanel {
                        onHelpRequested:function(origin,context){window.openInformation(origin,"",context)}
                    }
                }
                WorkspacePanel {
                    objectName: "deferredEnvironmentPanel"
                    requested: window.selectedSection===6 && (window.advanced || window.reportTool===3)
                    sourceComponent: EnvironmentPanel {
                        onHelpRequested:function(origin,context){window.openInformation(origin,"",context)}
                    }
                }
                WorkspacePanel {
                    objectName: "deferredPluginsPanel"
                    requested: window.selectedSection===6 && (window.advanced || window.reportTool===4)
                    sourceComponent: PluginsPanel {
                        onHelpRequested:function(origin,context){window.openInformation(origin,"",context)}
                    }
                }
                WorkspacePanel {
                    objectName: "deferredPrivacyPanel"
                    requested: window.selectedSection===6 && (window.advanced || window.reportTool===0)
                    visible: requested && (!window.raporlaOpen || window.advanced)
                    sourceComponent: PrivacyPanel {
                        onHelpRequested:function(origin,context){window.openInformation(origin,"",context)}
                    }
                }
                WorkspacePanel {
                    objectName: "deferredSharingPanel"
                    requested: window.selectedSection===6 && (window.advanced || window.reportTool===5)
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
                    visible: false
                    columnSpacing: Theme.sm
                    rowSpacing: Theme.sm
                    Repeater {
                        id: dataHeadings
                        model: [
                            {id:"rows", title:"Veri tablosu", detail:"Ana yüzey: kayıtları satır satır incele; sütun seç, sırala, filtrele."},
                            {id:"import", title:"Veriyi projeye aktar", detail:"Dosyanı seç, önizle ve projenle birlikte sakla."},
                            {id:"quality", title:"İncele", detail:"Tarama şeridi ve kalite bulguları İncele modülündedir."}
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
                        else if (currentIndex === 0 && (!window.dataPane || window.dataPane === "import" || window.dataPane === "quality")) window.dataPane = "rows"
                    }
                }
                Connections { target: imports; function onChanged() { if (imports.busy) dataTabs.currentIndex = 1 } }
                DatasetPanel {
                    id: datasetViewPanel
                    parent: tableBody
                    pane: "rows"
                    autoLoad: window.selectedSection === 1
                    inspectMode: window.inceleOpen
                    onShowValues: {
                        window.openIncele(null)
                        inspectWorkspacePanel.selectedBlock = 1
                    }
                    anchors.fill: parent
                    visible: window.showTable || window.inceleOpen
                    onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                }
                InspectWorkspacePanel {
                    id: inspectWorkspacePanel
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    visible: window.inceleOpen
                    onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                    onPrepareRequested: {
                        window.navigate(2, null)
                        window.prepareTool = 0
                        window.dockDismissed = false
                    }
                }
                DataWorkspacePanel {
                    id: dataWorkspacePanel
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    visible: window.selectedSection === 1 && window.dataPane !== "quality" && dataView.datasets.length > 0
                }
                ImportPanel {
                    onProjectRequested: { window.selectedSection = 0; Qt.callLater(function() { let control = window.findVisibleItem(window.contentItem, "newProjectButton"); if (control) control.forceActiveFocus() }) }
                    id: importPanel
                    Layout.fillWidth: true
                    visible: false
                    onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                }
                WorkspacePanel {
                    id: deferredChartPanel
                    objectName: "deferredChartPanel"
                    requested: window.selectedSection === 3 && (window.advanced || window.chartTool === 0)
                    sourceComponent: ChartPanel {
                        onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                    }
                }
                WorkspacePanel {
                    objectName: "deferredDashboardPanel"
                    requested: window.selectedSection === 3 && (window.advanced || window.chartTool === 1)
                    sourceComponent: DashboardPanel {
                        onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                    }
                }
                WorkspacePanel {
                    id: deferredOperationsPanel
                    objectName: "deferredOperationsPanel"
                    requested: window.selectedSection === 2 && (window.advanced || window.prepareTool === 0)
                    sourceComponent: PrepareCatalogPanel {
                        onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                    }
                }
                WorkspacePanel {
                    objectName: "deferredWorkflowPanel"
                    requested: window.selectedSection === 2 && (window.advanced || window.prepareTool === 1)
                    sourceComponent: WorkflowPanel {
                        onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                    }
                }
                WorkspacePanel {
                    objectName: "deferredRecipePanel"
                    requested: window.selectedSection === 2 && (window.advanced || window.prepareTool === 2)
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
                    Connections { target: window; function onSelectedSectionChanged() { if (window.selectedSection === 4 && (window.advanced || window.examineTool === 1)) dimensionTools.visited = true } }
                    Connections { target: window; function onExamineToolChanged() { if (window.selectedSection === 4 && window.examineTool === 1) dimensionTools.visited = true } }
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    visible: window.selectedSection === 4 && ((window.advanced && !survivalTools.expanded && !causalTools.expanded && !bayesTools.expanded && !statisticalModels.expanded && !resamplingTools.expanded && !experimentTools.expanded) || (!window.advanced && window.examineTool === 1))
                    sourceComponent: DimensionsPanel { onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) } }
                }
                Loader {
                    id: survivalTools
                    property bool visited: false
                    readonly property bool expanded: item ? item.expanded : false
                    active: visited
                    Connections { target: window; function onAdvancedChanged() { if (window.advanced && window.selectedSection === 4) survivalTools.visited = true } }
                    Component.onCompleted: if (window.advanced && window.selectedSection === 4) visited = true
                    Connections { target: window; function onSelectedSectionChanged() { if (window.selectedSection === 4 && (window.advanced || window.examineTool === 2)) survivalTools.visited = true } }
                    Connections { target: window; function onExamineToolChanged() { if (window.examineTool === 2) survivalTools.visited = true } }
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    visible: window.selectedSection === 4 && ((window.advanced && !dimensionTools.expanded && !causalTools.expanded && !bayesTools.expanded && !statisticalModels.expanded && !resamplingTools.expanded && !experimentTools.expanded) || (!window.advanced && window.examineTool === 2))
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
                    Connections { target: window; function onSelectedSectionChanged() { if (window.selectedSection === 4 && (window.advanced || window.examineTool === 3)) causalTools.visited = true } }
                    Connections { target: window; function onExamineToolChanged() { if (window.examineTool === 3) causalTools.visited = true } }
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    visible: window.selectedSection === 4 && ((window.advanced && !dimensionTools.expanded && !survivalTools.expanded && !bayesTools.expanded && !statisticalModels.expanded && !resamplingTools.expanded && !experimentTools.expanded) || (!window.advanced && window.examineTool === 3))
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
                    Connections { target: window; function onSelectedSectionChanged() { if (window.selectedSection === 4 && (window.advanced || window.examineTool === 4)) bayesTools.visited = true } }
                    Connections { target: window; function onExamineToolChanged() { if (window.examineTool === 4) bayesTools.visited = true } }
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    visible: window.selectedSection === 4 && ((window.advanced && !dimensionTools.expanded && !survivalTools.expanded && !causalTools.expanded && !statisticalModels.expanded && !resamplingTools.expanded && !experimentTools.expanded) || (!window.advanced && window.examineTool === 4))
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
                    Connections { target: window; function onSelectedSectionChanged() { if (window.selectedSection === 4 && (window.advanced || window.examineTool === 5)) experimentTools.visited = true } }
                    Connections { target: window; function onExamineToolChanged() { if (window.examineTool === 5) experimentTools.visited = true } }
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    visible: window.selectedSection === 4 && ((window.advanced && !dimensionTools.expanded && !survivalTools.expanded && !causalTools.expanded && !statisticalModels.expanded && !resamplingTools.expanded && !bayesTools.expanded) || (!window.advanced && window.examineTool === 5))
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
                    Connections { target: window; function onSelectedSectionChanged() { if (window.selectedSection === 4 && (window.advanced || window.examineTool === 6)) resamplingTools.visited = true } }
                    Connections { target: window; function onExamineToolChanged() { if (window.examineTool === 6) resamplingTools.visited = true } }
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    visible: window.selectedSection === 4 && ((window.advanced && !dimensionTools.expanded && !survivalTools.expanded && !causalTools.expanded && !statisticalModels.expanded && !experimentTools.expanded && !bayesTools.expanded) || (!window.advanced && window.examineTool === 6))
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
                            if (window.selectedSection === 4 && (window.advanced || window.examineTool === 7)) statisticalModels.visited = true
                        }
                        function onExamineToolChanged() {
                            if (window.examineTool === 7) statisticalModels.visited = true
                        }
                    }
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    visible: window.selectedSection === 4 && ((window.advanced && !dimensionTools.expanded && !survivalTools.expanded && !causalTools.expanded && !resamplingTools.expanded && !experimentTools.expanded && !bayesTools.expanded) || (!window.advanced && window.examineTool === 7))
                    sourceComponent: StatisticalModelsPanel {
                        onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                    }
                }
                WorkspacePanel {
                    id: deferredStatisticsPanel
                    objectName: "deferredStatisticsPanel"
                    requested: window.selectedSection === 4 && ((!window.advanced && window.examineTool === 0) || (window.advanced && (!dimensionTools.expanded && !survivalTools.expanded && !causalTools.expanded && !statisticalModels.expanded && !resamplingTools.expanded && !experimentTools.expanded && !bayesTools.expanded)))
                    sourceComponent: StatisticsCatalogPanel {
                        onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                    }
                }
                ResultPanel {
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    expert: window.advanced
                    visible: window.advanced || (window.selectedSection === 4 && !!expertWorkspace.selected.id)
                    onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                }
                WorkspacePanel {
                    id: deferredModelCatalogPanel
                    objectName: "deferredModelCatalogPanel"
                    requested: window.modelOpen
                    sourceComponent: ModelCatalogPanel {
                        onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                    }
                }
                UiCombo {
                    id:modelPath
                    objectName:"modelPath"
                    visible: window.selectedSection === 5 && window.modelInstalled && !window.modelOpen
                    model:["Kayıt bazlı modelleme","Zaman serisi — geçmişten geleceğe","Yerel metin incelemesi"]
                    Layout.fillWidth:true;Layout.leftMargin:Theme.xl;Layout.rightMargin:Theme.xl
                    Accessible.name:"Modelleme yolu"
                }
                UiLabel {
                    objectName: "modelLeakageNotice"
                    visible: window.selectedSection === 5 && window.modelInstalled && !window.modelOpen && (operations.modelLeakage.text || "").length > 0
                    text: operations.modelLeakage.text || ""
                    color: operations.modelLeakage.warning ? Theme.warning : Theme.secondary
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    wrapMode: Text.Wrap
                }
                WorkspacePanel {
                    objectName: "deferredTextPanel"
                    requested: window.selectedSection === 5 && window.modelInstalled && !window.modelOpen && modelPath.currentIndex === 2
                    sourceComponent: TextPanel {
                        onHelpRequested:function(origin,context){window.openInformation(origin,"",context)}
                    }
                }
                WorkspacePanel {
                    objectName: "deferredTimeSeriesPanel"
                    requested: window.selectedSection === 5 && window.modelInstalled && !window.modelOpen && modelPath.currentIndex === 1
                    sourceComponent: TimeSeriesPanel {
                        onHelpRequested:function(origin,context){window.openInformation(origin,"",context)}
                    }
                }
                WorkspacePanel {
                    objectName: "deferredScenarioPanel"
                    requested: window.advanced && window.modelInstalled && window.selectedSection === 5 && !window.modelOpen && modelPath.currentIndex === 0
                    sourceComponent: ScenarioPanel {
                        onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                    }
                }
                WorkspacePanel {
                    objectName: "deferredMonitoringPanel"
                    requested: window.advanced && window.modelInstalled && window.selectedSection === 5 && !window.modelOpen && modelPath.currentIndex === 0
                    sourceComponent: MonitoringPanel {
                        onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                    }
                }
                WorkspacePanel {
                    objectName: "deferredPreparationPanel"
                    requested: window.selectedSection === 5 && window.modelInstalled && !window.modelOpen && modelPath.currentIndex === 0
                    sourceComponent: PreparationPanel {
                        onHelpRequested: function(origin, context) { window.openInformation(origin, "", context) }
                    }
                }
                StateNotice { objectName: "availabilityNotice"; visible: false; heading: "Henüz mevcut değil" }
                ProjectPanel {
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.xl
                    Layout.rightMargin: Theme.xl
                    visible: window.selectedSection === 0 || (window.selectedSection === 1 && !projects.opened)
                    onHelpRequested: function(origin) { window.openInformation(origin, "", "project") }
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
                if (!window.dataPane || window.dataPane === "import") window.openDataPane("rows")
            }
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
    Connections {
        target: projects
        function onChanged() {
            if (projects.opened && !window.sawProject) {
                window.sawProject = true
                if (window.selectedSection === 0) {
                    window.selectedSection = 1
                    window.openVeri(null)
                }
            }
            if (!projects.opened)
                window.sawProject = false
        }
    }
    Shortcut { sequence: "Ctrl+1"; enabled: !startupError; onActivated: window.navigate(0, null) }
    Shortcut { sequence: "Ctrl+2"; enabled: !startupError; onActivated: window.openVeri(null) }
    Shortcut { sequence: "Ctrl+3"; enabled: !startupError; onActivated: window.navigate(2, null) }
    Shortcut { sequence: "Ctrl+4"; enabled: !startupError; onActivated: window.navigate(3, null) }
    Shortcut { sequence: "Ctrl+5"; enabled: !startupError; onActivated: window.navigate(4, null) }
    Shortcut { sequence: "Ctrl+6"; enabled: !startupError; onActivated: window.openModel(null) }
    Shortcut { sequence: "Ctrl+7"; enabled: !startupError; onActivated: window.navigate(6, null) }
}
