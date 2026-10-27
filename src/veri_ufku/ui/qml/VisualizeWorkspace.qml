import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ColumnLayout {
    id: root
    objectName: "visualizeWorkspace"
    property var chartControls: null
    property int currentTab: 0
    property bool pythonOpen: false
    property bool advancedOpen: false
    spacing: Theme.sm
    Layout.fillWidth: true
    Layout.fillHeight: true
    signal helpRequested(var origin, string context)

    readonly property var purposeCards: [
        { id: "distribution", title: qsTr("Dağılımı gör"), detail: qsTr("Ölçümün dağılımı, uçlar ve eksikler."), need: qsTr("1 ölçüm (X)"), kind: "histogram", purposeIndex: 0 },
        { id: "compare", title: qsTr("Grupları karşılaştır"), detail: qsTr("Kategoriye göre ölçüm farkları."), need: qsTr("kategori + ölçüm"), kind: "bar", purposeIndex: 1 },
        { id: "relationship", title: qsTr("İlişki ara"), detail: qsTr("İki ölçüm arasındaki ilişki ve güç."), need: qsTr("2 ölçüm (X, Y)"), kind: "scatter", purposeIndex: 2 },
        { id: "time", title: qsTr("Zaman içinde değişim"), detail: qsTr("Zaman/sıra boyunca trend."), need: qsTr("zaman + ölçüm"), kind: "line", purposeIndex: 3 },
        { id: "proportion", title: qsTr("Oranları göster"), detail: qsTr("Pay, yüzde ve bileşenler."), need: qsTr("kategori (+ ölçüm)"), kind: "percent-bar", purposeIndex: 1 },
        { id: "quality", title: qsTr("Eksikleri incele"), detail: qsTr("Eksik desenleri ve sütun oranları."), need: qsTr("bir veya daha çok sütun"), kind: "missing", purposeIndex: 4 }
    ]

    readonly property var advancedBlocks: [
        { title: qsTr("Dağılım ve oran"), kinds: "violin, kde, swarm", status: "ready" },
        { title: qsTr("İlişki ve zaman"), kinds: "bubble, facets, density-2d", status: "ready" },
        { title: qsTr("Hiyerarşi ve akış"), kinds: "treemap, sunburst, sankey, alluvial, funnel", status: "ready" },
        { title: qsTr("Ağ ve bağlantılar"), kinds: "GraphPanel", status: "panel", panel: "graph" },
        { title: qsTr("Dizi ve coğrafya"), kinds: "array-heatmap, map-*", status: "ready" },
        { title: qsTr("Metin ve ileri seçenekler"), kinds: "TextPanel", status: "panel", panel: "text" }
    ]

    readonly property string scopeBadge: {
        let r = charts.chartResult || ({})
        if (!r.dataset_version)
            return qsTr("grafik yok")
        let scope = ({ full: qsTr("tam veri"), view: qsTr("filtreli görünüm"), sample: qsTr("örneklem") })[r.scope] || r.scope
        if (r.scope === "sample")
            return qsTr("örneklem — ") + r.used_n + "/" + r.population_n
        return scope + " (n=" + r.used_n + ")"
    }

    function applyPurpose(card) {
        if (!root.chartControls)
            return
        root.chartControls.applyPurposeCard(card.purposeIndex, card.kind)
        root.currentTab = 0
    }

    function saveFinding() {
        if (!charts.explanation.ready || !charts.chartResult.dataset_version)
            return
        let note = [charts.explanation.see, charts.explanation.read, charts.explanation.caution, charts.explanation.next].filter(function(line) { return !!line }).join("\n")
        let summary = charts.methodSummary || ""
        if (summary)
            note += "\n" + summary
        dataView.saveChartNote(charts.chartResult.dataset_version + ":chart", note)
    }

    TabBar {
        id: tabs
        objectName: "visualizeTabBar"
        Layout.fillWidth: true
        currentIndex: root.currentTab
        onCurrentIndexChanged: root.currentTab = currentIndex
        TabButton { objectName: "visualizeTab_0"; text: qsTr("Grafik"); width: implicitWidth }
        TabButton { objectName: "visualizeTab_1"; text: qsTr("Çıktı"); width: implicitWidth }
        TabButton { objectName: "visualizeTab_2"; text: qsTr("Tablo"); width: implicitWidth }
    }

    StackLayout {
        Layout.fillWidth: true
        Layout.fillHeight: true
        currentIndex: root.currentTab

        // --- Grafik ---
        ScrollView {
            clip: true
            contentWidth: availableWidth
            ColumnLayout {
                width: parent.width
                spacing: Theme.sm

                Flow {
                    Layout.fillWidth: true
                    spacing: Theme.sm
                    Repeater {
                        model: root.purposeCards
                        Rectangle {
                            required property var modelData
                            required property int index
                            objectName: "visualizePurposeCard_" + (index + 1)
                            width: Math.max(160, Math.min(220, (parent.width - 2 * Theme.sm) / 3))
                            implicitHeight: cardCol.implicitHeight + 2 * Theme.sm
                            radius: Theme.radius
                            color: Theme.surface
                            border.width: (root.chartControls && root.chartControls.purposeIndex === modelData.purposeIndex && root.chartControls.kindName === modelData.kind) || (root.chartControls && root.chartControls.purposeIndex === modelData.purposeIndex && modelData.id !== "proportion" && modelData.id !== "compare") ? 2 : 1
                            border.color: border.width === 2 ? Theme.controlBorder : Theme.border
                            ColumnLayout {
                                id: cardCol
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.margins: Theme.sm
                                spacing: 2
                                UiLabel { text: modelData.title; font.bold: true; Layout.fillWidth: true; wrapMode: Text.Wrap }
                                UiLabel { text: modelData.detail; color: Theme.secondary; font.pixelSize: Theme.small; Layout.fillWidth: true; wrapMode: Text.Wrap }
                                UiLabel { text: modelData.need; color: Theme.dataTone; font.pixelSize: Theme.small; Layout.fillWidth: true; wrapMode: Text.Wrap }
                            }
                            MouseArea {
                                anchors.fill: parent
                                onClicked: root.applyPurpose(modelData)
                            }
                            Accessible.name: modelData.title
                            Accessible.role: Accessible.Button
                        }
                    }
                }

                Frame {
                    id: advancedSection
                    objectName: "visualizeAdvancedSection"
                    visible: window.advanced
                    Layout.fillWidth: true
                    padding: Theme.sm
                    ColumnLayout {
                        width: parent.width
                        spacing: Theme.sm
                        UiButton {
                            objectName: "visualizeAdvancedToggle"
                            text: root.advancedOpen ? qsTr("İleri grafikler −") : qsTr("İleri grafikler +")
                            quiet: true
                            Layout.fillWidth: true
                            onClicked: root.advancedOpen = !root.advancedOpen
                        }
                        UiLabel {
                            visible: root.advancedOpen
                            text: qsTr("Gelişmiş görünümde ek türler. Karşılığı yoksa uydurma çizim üretilmez.")
                            color: Theme.secondary
                            font.pixelSize: Theme.small
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                        }
                        Repeater {
                            model: root.advancedOpen ? root.advancedBlocks : []
                            Frame {
                                required property var modelData
                                Layout.fillWidth: true
                                padding: Theme.sm
                                ColumnLayout {
                                    width: parent.width
                                    UiLabel { text: modelData.title; font.bold: true; Layout.fillWidth: true }
                                    UiLabel {
                                        text: modelData.status === "panel"
                                              ? (qsTr("Ayrı panel: ") + modelData.kinds)
                                              : (qsTr("Türler: ") + modelData.kinds)
                                        color: Theme.secondary
                                        font.pixelSize: Theme.small
                                        Layout.fillWidth: true
                                        wrapMode: Text.Wrap
                                    }
                                    UiLabel {
                                        visible: modelData.status === "panel"
                                        text: modelData.panel === "graph"
                                              ? qsTr("Ağ: GraphPanel ayrı yüzeydir; bu sürümde grafik tuvalinde sahte ağ çizilmez.")
                                              : qsTr("Metin: TextPanel ayrı yüzeydir; kelime bulutu burada uydurulmaz.")
                                        color: Theme.warning
                                        font.pixelSize: Theme.small
                                        Layout.fillWidth: true
                                        wrapMode: Text.Wrap
                                    }
                                }
                            }
                        }
                    }
                }
                UiLabel {
                    visible: !window.advanced
                    text: qsTr("İleri grafikler gelişmiş görünümde açılır.")
                    color: Theme.secondary
                    font.pixelSize: Theme.small
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }

                RowLayout {
                    Layout.fillWidth: true
                    UiLabel {
                        objectName: "visualizeChartTitle"
                        text: (charts.chartResult.spec && charts.chartResult.spec.title) ? charts.chartResult.spec.title : qsTr("Grafik tuvali")
                        font.bold: true
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    UiLabel {
                        objectName: "visualizeScopeBadge"
                        text: root.scopeBadge
                        color: Theme.secondary
                        font.pixelSize: Theme.small
                    }
                    UiLabel {
                        text: charts.chartResult.dataset_version ? ("v" + String(charts.chartResult.dataset_version).slice(-4)) : ""
                        color: Theme.secondary
                        font.pixelSize: Theme.small
                        visible: text.length > 0
                    }
                    UiButton {
                        objectName: "chartPythonToggle"
                        text: qsTr("Python")
                        quiet: true
                        onClicked: root.pythonOpen = !root.pythonOpen
                    }
                }
                UiLabel {
                    objectName: "chartScope"
                    visible: !!charts.chartResult.dataset_version
                    text: (charts.current ? qsTr("Seçili veri/filtre ile uyumlu") : qsTr("Eski veri sürümü/filtre — yeniden oluşturun"))
                          + "\n" + qsTr("Sürüm: ") + (charts.chartResult.dataset_version || "")
                          + " · " + (charts.chartResult.scope || "")
                          + " · " + qsTr("kullanılan ") + charts.chartResult.used_n + " / " + qsTr("kapsam ") + charts.chartResult.population_n
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    font.pixelSize: Theme.small
                    color: charts.current ? Theme.secondary : Theme.warning
                }

                Popup {
                    id: pythonPopup
                    objectName: "chartPythonPanel"
                    visible: root.pythonOpen
                    modal: true
                    focus: true
                    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                    width: Math.min(520, root.width - 24)
                    height: Math.min(360, root.height - 24)
                    anchors.centerIn: Overlay.overlay
                    onClosed: root.pythonOpen = false
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.md
                        spacing: Theme.sm
                        UiLabel { text: qsTr("Python belirtimi (salt okunur, çalıştırılmaz)"); font.bold: true; Layout.fillWidth: true; wrapMode: Text.Wrap }
                        ScrollView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            TextArea {
                                id: pythonBody
                                objectName: "chartPython"
                                readOnly: true
                                text: charts.pythonSnippet
                                wrapMode: TextEdit.Wrap
                                selectByMouse: true
                                color: Theme.text
                                Accessible.name: qsTr("Python belirtimi")
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            UiButton {
                                objectName: "chartPythonCopy"
                                text: qsTr("Kopyala")
                                onClicked: pythonBody.selectAll()
                            }
                            UiButton { text: qsTr("Kapat"); quiet: true; onClicked: pythonPopup.close() }
                        }
                    }
                }

                UiCombo { accessibleLabel: qsTr("Grafikle etkileşim modu"); id: mode; objectName: "chartMode"; model: [qsTr("Sürükle / tıkla: RowId seçimi"), qsTr("Sürükle: yakınlaştır")]; Layout.fillWidth: true }
                Item {
                    id: canvas
                    objectName: "chartCanvas"
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.max(260, Math.min(720 * Theme.scale, width * (charts.plotMetadata.height || 600) / (charts.plotMetadata.width || 960)))
                    visible: charts.imageUrl.length > 0
                    Image {
                        id: plot
                        objectName: "chartImage"
                        anchors.fill: parent
                        source: charts.imageUrl
                        cache: false
                        fillMode: Image.PreserveAspectFit
                    }
                    Canvas {
                        id: selectionOverlay
                        anchors.fill: parent
                        onPaint: {
                            let ctx = getContext("2d"); ctx.clearRect(0, 0, width, height)
                            let selected = charts.selectionResult.point_ids || []
                            let meta = charts.plotMetadata
                            if (!meta.pixels) return
                            let marks = new Set(selected)
                            ctx.strokeStyle = "#991B1B"; ctx.lineWidth = 2
                            for (let p of meta.pixels) if (marks.has(p.point_id)) {
                                let px = (width - plot.paintedWidth) / 2 + p.x / meta.width * plot.paintedWidth
                                let py = (height - plot.paintedHeight) / 2 + p.y / meta.height * plot.paintedHeight
                                ctx.beginPath(); ctx.arc(px, py, 7, 0, Math.PI * 2); ctx.stroke()
                            }
                        }
                        Connections { target: charts; function onChanged() { selectionOverlay.requestPaint() } }
                        onWidthChanged: requestPaint()
                        onHeightChanged: requestPaint()
                    }
                    MouseArea {
                        id: mouse
                        objectName: "chartMouse"
                        anchors.fill: parent
                        property real sx: 0
                        property real sy: 0
                        property bool validOrigin: false
                        function insideImage(x, y) {
                            return plot.status === Image.Ready && plot.paintedWidth > 0 && plot.paintedHeight > 0
                                && x >= (width - plot.paintedWidth) / 2 && x <= (width + plot.paintedWidth) / 2
                                && y >= (height - plot.paintedHeight) / 2 && y <= (height + plot.paintedHeight) / 2
                        }
                        function nx(x) { return Math.max(0, Math.min(1, (x - (width - plot.paintedWidth) / 2) / plot.paintedWidth)) }
                        function ny(y) { return Math.max(0, Math.min(1, (y - (height - plot.paintedHeight) / 2) / plot.paintedHeight)) }
                        onPressed: function(event) { validOrigin = insideImage(event.x, event.y); if (!validOrigin) { event.accepted = false; return } sx = nx(event.x); sy = ny(event.y) }
                        onCanceled: validOrigin = false
                        onReleased: function(event) {
                            if (!validOrigin) return
                            validOrigin = false
                            if (mode.currentIndex === 0) charts.selectRectangle(sx, sy, nx(event.x), ny(event.y))
                            else charts.zoomRectangle(sx, sy, nx(event.x), ny(event.y))
                        }
                    }
                    Accessible.name: qsTr("Matplotlib grafik; seçim/yakınlaştırma modu ve metinli sonuç tablosu")
                }
                Flow {
                    Layout.fillWidth: true
                    spacing: Theme.sm
                    UiButton { objectName: "chartZoom"; text: qsTr("Yakınlaştır"); enabled: charts.current && !projects.busy; onClicked: charts.zoomRectangle(.25, .25, .75, .75) }
                    UiButton { objectName: "chartReset"; text: qsTr("Görünümü sıfırla"); enabled: charts.current && !projects.busy; onClicked: charts.reset() }
                }
                UiLabel {
                    objectName: "chartSelection"
                    text: qsTr("Seçim: ") + (charts.selectionResult.count || 0) + " RowId · " + (charts.selectionResult.scope || qsTr("seçim yok"))
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    font.pixelSize: Theme.small
                }
            }
        }

        // --- Çıktı ---
        ScrollView {
            clip: true
            contentWidth: availableWidth
            ColumnLayout {
                width: parent.width
                spacing: Theme.md
                UiLabel { objectName: "chartExplainSee"; text: (qsTr("Ne gösteriyorum?\n") + (charts.explanation.see || qsTr("Grafik henüz yok."))); Layout.fillWidth: true; wrapMode: Text.Wrap }
                UiLabel { objectName: "chartExplainRead"; text: (qsTr("Nasıl yorumlarım?\n") + (charts.explanation.read || "")); visible: (charts.explanation.read || "").length > 0; Layout.fillWidth: true; wrapMode: Text.Wrap }
                UiLabel { objectName: "chartExplainCaution"; text: (qsTr("Sınır\n") + (charts.explanation.caution || "")); visible: (charts.explanation.caution || "").length > 0; Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.warning }
                UiLabel { objectName: "chartExplainNext"; text: (qsTr("Sonraki adım\n") + (charts.explanation.next || "")); visible: (charts.explanation.next || "").length > 0; Layout.fillWidth: true; wrapMode: Text.Wrap }
                UiLabel {
                    objectName: "chartMethodDetails"
                    text: charts.methodSummary
                    visible: !!charts.chartResult.dataset_version
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
                UiLabel {
                    text: qsTr("Kutu / tür özeti")
                    font.bold: true
                    visible: (charts.chartResult.summary || []).length > 0
                    Layout.fillWidth: true
                }
                Repeater {
                    model: charts.chartResult.summary || []
                    UiLabel {
                        required property var modelData
                        text: modelData.column_name + " · " + JSON.stringify(modelData.numeric) + "\nNull/NaN/inf: " + JSON.stringify(modelData.counts)
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        font.pixelSize: Theme.small
                    }
                }
                UiButton {
                    objectName: "chartExplainSave"
                    text: qsTr("Bulguyu notuna ekle")
                    primary: true
                    enabled: !!charts.explanation.ready && !!charts.chartResult.dataset_version
                    Layout.fillWidth: true
                    onClicked: root.saveFinding()
                }
                UiButton {
                    objectName: "chartPythonToggleOutput"
                    text: qsTr("Python")
                    quiet: true
                    Layout.fillWidth: true
                    onClicked: root.pythonOpen = true
                }
            }
        }

        // --- Tablo ---
        Loader {
            active: root.currentTab === 2
            Layout.fillWidth: true
            Layout.fillHeight: true
            sourceComponent: DatasetPanel {
                objectName: "visualizeTablePanel"
                pane: "rows"
                autoLoad: true
                inspectMode: false
                onHelpRequested: function(origin, context) { root.helpRequested(origin, context) }
            }
        }
    }
}
