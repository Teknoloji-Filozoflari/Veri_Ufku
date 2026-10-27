import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ColumnLayout {
    id: panel
    objectName: "chartPanel"
    property string helpContext: "chart.histogram"
    property var selected: []
    property var recommendationRows: []
    property var galleryRows: []
    property bool liveEnabled: true
    property bool liveArmed: false
    property int purposeIndex: purpose.currentIndex
    readonly property string kindName: panel.kindValues[kind.currentIndex] || ""
    property var kindValues: ["histogram","box","bar","line","scatter","correlation","missing","array-heatmap","array-profile","violin","kde","ecdf","rug","strip","swarm","qq","pp","error-bar","ci-band","missing-pattern","pair","hexbin","density-2d","bubble","grouped-heatmap","clustered-heatmap","parallel","facets","conditional","stacked-bar","percent-bar","stacked-area","percent-area","dot","lollipop","waterfall","pareto","treemap","sunburst","sankey","alluvial","funnel","calendar","pie","donut","radar","map-point","map-choropleth","map-density","map-raster"]
    signal helpRequested(var origin, string context)
    spacing: Theme.md
    onLiveEnabledChanged: if (!liveEnabled) liveTimer.stop()
    // Arm only after first explicit user gesture so load-time ComboBox model fills
    // cannot spawn a worker under max_processes=1.
    Component.onCompleted: panel.liveArmed = false

    function key(picker) { return picker.currentIndex >= 0 ? picker.currentValue : "" }
    function armLive() {
        if (!panel.liveArmed)
            panel.liveArmed = true
    }

    readonly property bool needsX: {
        let name = kindName
        let multiple = ["correlation","missing","array-heatmap","missing-pattern","pair","grouped-heatmap","clustered-heatmap","parallel","radar"].indexOf(name) >= 0
        return !multiple && kind.currentIndex !== 19
    }
    readonly property bool needsY: {
        let name = kindName
        return ["line","scatter","array-profile","error-bar","ci-band","hexbin","density-2d","bubble","facets","conditional"].indexOf(name) >= 0
            || (kind.currentIndex >= 29 && name !== "funnel" && name !== "radar" && name !== "pie" && name !== "donut" && name !== "percent-bar" && name !== "stacked-bar")
            || (name === "bar" && aggregate.currentIndex !== 0)
    }
    readonly property bool wantsGroup: {
        let name = kindName
        return kind.currentIndex <= 4 || (kind.currentIndex >= 9 && kind.currentIndex !== 19 && name.indexOf("array-") !== 0 && name.indexOf("map-") !== 0)
    }
    readonly property bool wantsFacet: kindName === "facets" || kindName === "conditional"
    readonly property string slotWarning: {
        if (!needsX)
            return ""
        if (x.currentIndex < 0 || !charts.columns.length)
            return qsTr("X ölçümü atanmadı.")
        let col = charts.columns[x.currentIndex] || ({})
        if (kindName === "line" && col.type && String(col.type).indexOf("Date") < 0 && String(col.type).indexOf("Datetime") < 0 && (col.role || "") !== "Zaman")
            return qsTr("Çizgi grafiği X’te zaman/tarih bekler; seçilen sütun uyumsuz olabilir.")
        if (kindName === "histogram" && needsY)
            return ""
        return ""
    }

    function scheduleCreate() {
        if (!panel.liveEnabled || !panel.liveArmed || projects.busy || dataView.datasets.length === 0)
            return
        liveTimer.restart()
    }
    function applyPurposeCard(pIndex, defaultKind) {
        panel.armLive()
        purpose.currentIndex = Math.max(0, Math.min(4, pIndex))
        let ki = panel.kindValues.indexOf(defaultKind)
        if (ki >= 0)
            kind.currentIndex = ki
        panel.recommendationRows = charts.recommendations(["distribution","compare","relationship","time","quality"][purpose.currentIndex])
        panel.scheduleCreate()
    }
    function restore() {
        let s = charts.chartResult.spec
        if (!s) return
        panel.liveEnabled = false
        kind.currentIndex = kindValues.indexOf(s.kind)
        for (let i = 0; i < charts.columns.length; i++) {
            if (charts.columns[i].id === s.x) x.currentIndex = i
            if (charts.columns[i].id === s.y) y.currentIndex = i
        }
        group.currentIndex = 0
        for (let i = 0; i < group.model.length; i++) if (group.model[i].id === s.group) group.currentIndex = i
        facet.currentIndex = 0
        for (let i = 0; i < facet.model.length; i++) if (facet.model[i].id === s.facet) facet.currentIndex = i
        panel.selected = s.columns; title.text = s.title; xlabel.text = s.xlabel; ylabel.text = s.ylabel; xunit.text = s.xunit; yunit.text = s.yunit
        legend.checked = s.legend; bins.value = s.bins; topn.value = s.top_n
        aggregate.currentIndex = ["count","sum","mean","median","min","max","reject"].indexOf(s.aggregation)
        correlation.currentIndex = s.correlation === "pearson" ? 0 : 1
        scatter.currentIndex = ["systematic","grid","full"].indexOf(s.scatter_mode)
        limit.value = s.point_limit; grid.value = s.grid_bins; scope.currentIndex = ["view","full","sample"].indexOf(s.scope)
        sample.value = s.sample_rows; approx.checked = s.precision === "approximate"
        purpose.currentIndex = ["distribution","compare","relationship","time","quality"].indexOf(s.purpose)
        panel.helpContext = "chart." + s.kind.replace("_", "-")
        distribution.restore(s)
        multivariate.restore(s)
        composition.restore(s)
        geo.restore(s)
        settings.checked = true
        panel.liveEnabled = true
    }
    function create() {
        liveTimer.stop()
        let name = kindValues[kind.currentIndex]
        let multiple = ["correlation","missing","array-heatmap","missing-pattern","pair","grouped-heatmap","clustered-heatmap","parallel","radar"].indexOf(name) >= 0
        let needsYLocal = ["line","scatter","array-profile","error-bar","ci-band","hexbin","density-2d","bubble","facets","conditional"].indexOf(name) >= 0 || kind.currentIndex >= 29 && name !== "funnel" && name !== "radar" || name === "bar" && aggregate.currentIndex !== 0
        let spec = {
            kind: name,
            x: multiple ? "" : key(x),
            y: needsYLocal ? key(y) : "",
            group: (!multiple || kind.currentIndex >= 20) && name.indexOf("array-") !== 0 && group.currentIndex > 0 ? group.currentValue : "",
            facet: "",
            columns: multiple ? selected : [],
            title: title.text, xlabel: xlabel.text, ylabel: ylabel.text, xunit: xunit.text, yunit: yunit.text,
            legend: legend.checked, bins: bins.value, top_n: topn.value,
            aggregation: ["count","sum","mean","median","min","max","reject"][aggregate.currentIndex],
            correlation: correlation.currentIndex === 0 ? "pearson" : "spearman",
            scatter_mode: ["systematic","grid","full"][scatter.currentIndex],
            point_limit: limit.value, grid_bins: grid.value,
            scope: ["view","full","sample"][scope.currentIndex],
            sample_rows: sample.value,
            precision: approx.checked ? "approximate" : "reject",
            purpose: ["distribution","compare","relationship","time","quality"][purpose.currentIndex]
        }
        if (name === "error-bar" || name === "ci-band") spec.aggregation = "mean"
        Object.assign(spec, distribution.values())
        if (kind.currentIndex >= 20 && kind.currentIndex < 29) Object.assign(spec, multivariate.values())
        if (kind.currentIndex >= 29 && kind.currentIndex < 46) {
            Object.assign(spec, composition.values())
            spec.weight = ""; spec.weight_type = "none"; spec.size = ""; spec.xscale = "linear"; spec.yscale = "linear"
            spec.category_order = composition.order()
        }
        if (kind.currentIndex >= 46) {
            Object.assign(spec, geo.values())
            spec.group = ""; spec.facet = ""; spec.weight = ""; spec.weight_type = "none"; spec.size = ""
            spec.xscale = "linear"; spec.yscale = "linear"
            if (spec.geometry) { spec.x = ""; spec.y = "" }
        }
        if (panel.wantsFacet && facet.currentIndex > 0)
            spec.facet = facet.currentValue
        else if (!panel.wantsFacet && kind.currentIndex >= 29)
            spec.facet = ""
        charts.create(JSON.stringify(spec))
    }

    Timer {
        id: liveTimer
        interval: 400
        repeat: false
        onTriggered: {
            if (!panel.liveEnabled || !panel.liveArmed)
                return
            if (!charts.busy && !projects.busy && dataView.datasets.length > 0)
                panel.create()
        }
    }

    RowLayout {
        Layout.fillWidth: true
        UiLabel {
            objectName: "chartWorkspaceTitle"
            text: qsTr("Grafik")
            font.pixelSize: Theme.heading
            font.bold: true
        }
        Item { Layout.fillWidth: true }
        UiLabel {
            objectName: "chartHealthSummary"
            text: charts.busy ? qsTr("Hesaplanıyor…") : (charts.chartResult.dataset_version ? (qsTr("n=") + charts.chartResult.used_n) : qsTr("Hazır"))
            color: Theme.secondary
            font.pixelSize: Theme.small
        }
    }
    UiLabel {
        text: qsTr("Atama ve ayar değişince grafik yeniden hesaplanır. Veri sürümü değişmez.")
        color: Theme.secondary
        font.pixelSize: Theme.small
        Layout.fillWidth: true
        wrapMode: Text.Wrap
    }

    Frame {
        objectName: "chartVariablesBox"
        Layout.fillWidth: true
        padding: Theme.md
        background: Rectangle { color: Theme.surface; border.color: panel.slotWarning ? Theme.warning : Theme.border; radius: Theme.radius }
        ColumnLayout {
            width: parent.width
            spacing: Theme.sm
            UiLabel { text: qsTr("Değişkenler"); font.bold: true; Layout.fillWidth: true }
            UiLabel {
                objectName: "chartSlotWarning"
                visible: panel.slotWarning.length > 0
                text: panel.slotWarning
                color: Theme.warning
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                font.pixelSize: Theme.small
            }
            GridLayout {
                columns: 2
                Layout.fillWidth: true
                columnSpacing: Theme.sm
                rowSpacing: Theme.sm
                UiLabel { text: qsTr("Ölçüm (X)"); Layout.fillWidth: true }
                UiCombo {
                    accessibleLabel: qsTr("X ölçümü")
                    id: x
                    objectName: "chartX"
                    model: charts.columns
                    textRole: "name"
                    valueRole: "id"
                    Layout.fillWidth: true
                    enabled: panel.needsX
                    opacity: panel.needsX ? 1 : 0.55
                    displayText: !panel.needsX ? qsTr("bu grafik istemiyor") : (currentIndex < 0 ? qsTr("atanmadı") : currentText)
                    onActivated: {
                        panel.armLive()
                        if (kind.currentIndex === 1) yunit.text = model[currentIndex].unit
                        else xunit.text = model[currentIndex].unit
                        charts.invalidate(); panel.scheduleCreate()
                    }
                }
                UiLabel { text: qsTr("Ölçüm (Y)"); Layout.fillWidth: true }
                UiCombo {
                    accessibleLabel: qsTr("Y ölçümü")
                    id: y
                    objectName: "chartY"
                    model: charts.columns
                    textRole: "name"
                    valueRole: "id"
                    Layout.fillWidth: true
                    enabled: panel.needsY
                    opacity: panel.needsY ? 1 : 0.55
                    displayText: !panel.needsY ? qsTr("bu grafik istemiyor") : (currentIndex < 0 ? qsTr("atanmadı") : currentText)
                    onActivated: { panel.armLive(); yunit.text = model[currentIndex].unit; charts.invalidate(); panel.scheduleCreate() }
                }
                UiLabel { text: qsTr("Grup"); Layout.fillWidth: true }
                UiCombo {
                    accessibleLabel: qsTr("Grafik grubu")
                    id: group
                    objectName: "chartGroup"
                    model: [{id: "", name: qsTr("Grup yok")}].concat(charts.columns)
                    textRole: "name"
                    valueRole: "id"
                    Layout.fillWidth: true
                    enabled: panel.wantsGroup
                    opacity: panel.wantsGroup ? 1 : 0.55
                    displayText: !panel.wantsGroup ? qsTr("bu grafik istemiyor") : (currentIndex <= 0 ? qsTr("atanmadı") : currentText)
                    onActivated: { panel.armLive(); charts.invalidate(); panel.scheduleCreate() }
                }
                UiLabel { text: qsTr("Facet"); Layout.fillWidth: true }
                UiCombo {
                    accessibleLabel: qsTr("Facet")
                    id: facet
                    objectName: "chartFacetSlot"
                    model: [{id: "", name: qsTr("Facet yok")}].concat(charts.columns)
                    textRole: "name"
                    valueRole: "id"
                    Layout.fillWidth: true
                    enabled: panel.wantsFacet
                    opacity: panel.wantsFacet ? 1 : 0.55
                    displayText: !panel.wantsFacet ? qsTr("bu grafik istemiyor") : (currentIndex <= 0 ? qsTr("atanmadı") : currentText)
                    onActivated: { panel.armLive(); charts.invalidate(); panel.scheduleCreate() }
                }
            }
        }
    }

    UiCheckBox { id: settings; objectName: "chartSettings"; text: qsTr("Ayarlar ve tür"); checked: true; Layout.fillWidth: true }
    ColumnLayout {
        visible: settings.checked
        Layout.fillWidth: true
        spacing: Theme.md
        UiCombo {
            accessibleLabel: qsTr("Veri kümesi")
            model: dataView.datasets
            textRole: "label"
            valueRole: "id"
            Layout.fillWidth: true
            onActivated: { dataView.selectDataset(currentValue); panel.selected = []; charts.invalidate(); panel.scheduleCreate() }
        }
        UiLabel { text: dataView.viewSummary; color: Theme.secondary; Layout.fillWidth: true; wrapMode: Text.Wrap }
        UiTextField {
            id: galleryQuery
            Accessible.name: qsTr("Grafik sorusu veya tür araması")
            objectName: "chartGalleryQuery"
            placeholderText: qsTr("Soru veya tür ara: pay, nereden nereye, hangi gün…")
            Layout.fillWidth: true
            onTextChanged: panel.galleryRows = charts.gallery(text, composition.advanced || window.advanced)
        }
        UiButton {
            objectName: "chartGallerySearch"
            text: qsTr("Soruya göre grafik galerisi")
            Layout.fillWidth: true
            onClicked: panel.galleryRows = charts.gallery(galleryQuery.text, composition.advanced || window.advanced)
        }
        Repeater {
            model: panel.galleryRows
            UiButton {
                required property var modelData
                text: modelData.kind + " · " + modelData.question + "\n" + modelData.status
                multiline: true
                Layout.fillWidth: true
                enabled: modelData.ready
                onClicked: {
                    let ki = panel.kindValues.indexOf(modelData.kind)
                    if (ki >= 0) { kind.currentIndex = ki; panel.scheduleCreate() }
                }
            }
        }
        UiCombo {
            accessibleLabel: qsTr("Grafik amacı")
            id: purpose
            objectName: "chartPurpose"
            model: [qsTr("Dağılımı incele"), qsTr("Grupları karşılaştır"), qsTr("İlişki ara"), qsTr("Zamanı incele"), qsTr("Eksikleri incele")]
            Layout.fillWidth: true
            onActivated: {
                panel.armLive()
                panel.recommendationRows = charts.recommendations(["distribution","compare","relationship","time","quality"][currentIndex])
                charts.invalidate()
                panel.scheduleCreate()
            }
        }
        Repeater {
            model: panel.recommendationRows
            UiButton {
                required property var modelData
                text: modelData.reason + " → " + modelData.kind
                Layout.fillWidth: true
                multiline: true
                onClicked: {
                    panel.armLive()
                    kind.currentIndex = panel.kindValues.indexOf(modelData.kind)
                    for (let i = 0; i < charts.columns.length; i++)
                        if (charts.columns[i].id === modelData.column_id) x.currentIndex = i
                    charts.invalidate()
                    panel.scheduleCreate()
                }
            }
        }
        UiLabel { text: qsTr("Grafik türü"); Layout.fillWidth: true }
        UiCombo {
            accessibleLabel: qsTr("Grafik türü")
            id: kind
            objectName: "chartKind"
            model: ["Histogram — dağılım","Kutu — medyan ve yayılım","Sütun — kategori karşılaştırması","Çizgi — sıralı zaman/ölçüm","Dağılım — iki ölçüm","Korelasyon ısı haritası","Eksik oranı","Array 2D ısı haritası · iki eksen + ölçüm","Array profil çizgisi","Violin — yoğunluk","KDE — yoğunluk","ECDF — birikimli olasılık","Rug — tekil değerler","Strip — kategoride gözlemler","Swarm — limitli çakışma yerleşimi","QQ — normal referans","PP — normal referans","Hata çubuğu — SD / SE / CI","Noktasal CI bandı","Eksiklik desenleri","Pair / scatter matrix","Hexbin — CPU sayım","2D yoğunluk — hücre histogramı","Bubble — boyut kodlama","Gruplu heatmap","Kümelenmiş heatmap","Parallel coordinates — sayısal","Facet / small multiples","Koşullu ilişki / pooled","Stacked bar","100% stacked bar","Stacked area","100% stacked area","Dot — kategori karşılaştırması","Lollipop","Waterfall — başlangıç/değişim/bitiş","Pareto","Treemap — yaprak toplamı","Sunburst — hiyerarşi","Sankey — dengeli akış","Alluvial — aşamalı akış","Funnel — kişi/olay","Takvim heatmap","Pie — en fazla6 kategori","Donut — en fazla6 kategori","Radar — gelişmiş/normalize","Nokta haritası · offline","Choropleth · sayım/oran","Yoğunluk haritası · grid","GeoTIFF raster kesit"]
            Layout.fillWidth: true
            onCurrentIndexChanged: panel.helpContext = "chart." + panel.kindValues[currentIndex].replace("_", "-")
            onActivated: { panel.armLive(); charts.invalidate(); panel.scheduleCreate() }
        }
        UiLabel {
            text: kind.currentIndex === 7 ? qsTr("Sırayla iki boyut koordinatı/indeksi, sonra value ölçümünü seçin.") : qsTr("Korelasyon/eksik oranı sütunları (en fazla20)")
            visible: kind.currentIndex >= 5 && kind.currentIndex <= 7 || kind.currentIndex === 19 || [20, 24, 25, 26, 45].indexOf(kind.currentIndex) >= 0
            Layout.fillWidth: true
            wrapMode: Text.Wrap
        }
        Repeater {
            model: kind.currentIndex >= 5 && kind.currentIndex <= 7 || kind.currentIndex === 19 || [20, 24, 25, 26, 45].indexOf(kind.currentIndex) >= 0 ? charts.columns : []
            UiCheckBox {
                required property var modelData
                text: modelData.name + " · " + modelData.type
                Layout.fillWidth: true
                checked: panel.selected.indexOf(modelData.id) >= 0
                onClicked: {
                    panel.selected = checked ? panel.selected.concat([modelData.id]) : panel.selected.filter(v => v !== modelData.id)
                    charts.invalidate()
                    panel.scheduleCreate()
                }
            }
        }
        GridLayout {
            columns: 1
            Layout.fillWidth: true
            UiCombo {
                accessibleLabel: qsTr("Özetleme yöntemi")
                id: aggregate
                objectName: "chartAggregation"
                model: [qsTr("Kayıt sayısı (count)"), qsTr("Toplam (sum)"), qsTr("Ortalama (mean)"), qsTr("Medyan (median)"), qsTr("En küçük"), qsTr("En büyük"), qsTr("Tekrarda dur (reject)")]
                currentIndex: 6
                visible: kind.currentIndex === 2 || kind.currentIndex === 3 || kind.currentIndex === 7 || kind.currentIndex === 8 || kind.currentIndex === 24 || kind.currentIndex === 25 || kind.currentIndex >= 29
                Layout.fillWidth: true
                onActivated: { charts.invalidate(); panel.scheduleCreate() }
            }
            UiLabel { text: qsTr("Kutu sayısı"); visible: kind.currentIndex === 0; Layout.fillWidth: true }
            UiSpinBox {
                id: bins
                objectName: "chartBins"
                from: 1; to: 200; value: 20; editable: true
                visible: kind.currentIndex === 0
                onValueModified: { charts.invalidate(); /* pahalı: elle yeniden hesap */ }
                Accessible.name: qsTr("Histogram bin sayısı")
            }
            UiSpinBox {
                Accessible.name: qsTr("Top-N kategori")
                id: topn
                objectName: "chartTopN"
                from: 1; to: 100; value: 20; editable: true
                onValueModified: { charts.invalidate() }
            }
            UiCombo {
                accessibleLabel: qsTr("Korelasyon yöntemi")
                id: correlation
                objectName: "chartCorrelation"
                model: [qsTr("Pearson — doğrusal ilişki"), qsTr("Spearman — sıra ilişkisi")]
                visible: kind.currentIndex === 5
                Layout.fillWidth: true
                onActivated: { charts.invalidate(); panel.scheduleCreate() }
            }
            UiCombo {
                accessibleLabel: qsTr("Nokta örnekleme yöntemi")
                id: scatter
                objectName: "chartScatter"
                model: [qsTr("Sistematik örnekleme"), qsTr("Izgara ortalaması"), qsTr("Tam noktalar")]
                visible: kind.currentIndex === 4
                Layout.fillWidth: true
                onActivated: { charts.invalidate(); panel.scheduleCreate() }
            }
            UiSpinBox {
                Accessible.name: qsTr("Azami nokta sayısı")
                id: limit
                objectName: "chartPointLimit"
                from: 1; to: 10000; value: 10000; editable: true
                visible: kind.currentIndex === 4
                onValueModified: charts.invalidate()
            }
            UiSpinBox {
                Accessible.name: qsTr("Izgara eksen başına hücre")
                id: grid
                from: 2; to: 80; value: 40
                visible: kind.currentIndex === 4 && scatter.currentIndex === 1
                onValueModified: charts.invalidate()
            }
            UiCombo {
                accessibleLabel: qsTr("Grafik kapsamı")
                id: scope
                objectName: "chartScopeChoice"
                model: [qsTr("Mevcut tablo filtreleri / tam alt küme"), qsTr("Tam dataset (filtreleri kullanma)"), qsTr("Filtreli ilk-N açık örneklem")]
                Layout.fillWidth: true
                onActivated: { charts.invalidate(); panel.scheduleCreate() }
            }
            UiSpinBox {
                Accessible.name: qsTr("İlk-N kayıt")
                id: sample
                objectName: "chartSample"
                from: 1; to: 100000; value: 10000; editable: true
                visible: scope.currentIndex === 2
                onValueModified: charts.invalidate()
            }
        }
        UiCheckBox {
            id: approx
            objectName: "chartApproximate"
            text: qsTr("Integer/Decimal Float64 çizim kaybına açık izin ver")
            Layout.fillWidth: true
            onClicked: { charts.invalidate(); panel.scheduleCreate() }
        }
        UiCheckBox { id: styleDetails; text: qsTr("Başlık, eksen adı, birim ve legend"); Layout.fillWidth: true }
        ColumnLayout {
            visible: styleDetails.checked
            Layout.fillWidth: true
            UiTextField { id: title; objectName: "chartTitle"; placeholderText: qsTr("Grafik başlığı"); maximumLength: 200; Layout.fillWidth: true; onTextEdited: charts.invalidate(); Accessible.name: qsTr("Grafik başlığı") }
            UiTextField { id: xlabel; placeholderText: qsTr("X ekseni adı"); maximumLength: 200; Layout.fillWidth: true; onTextEdited: charts.invalidate(); Accessible.name: qsTr("X ekseni adı") }
            UiTextField { id: ylabel; placeholderText: qsTr("Y ekseni adı"); maximumLength: 200; Layout.fillWidth: true; onTextEdited: charts.invalidate(); Accessible.name: qsTr("Y ekseni adı") }
            UiTextField { id: xunit; placeholderText: qsTr("X birimi"); maximumLength: 200; Layout.fillWidth: true; onTextEdited: charts.invalidate(); Accessible.name: qsTr("X birimi") }
            UiTextField { id: yunit; placeholderText: qsTr("Y birimi"); maximumLength: 200; Layout.fillWidth: true; onTextEdited: charts.invalidate(); Accessible.name: qsTr("Y birimi") }
            UiCheckBox { id: legend; checked: true; text: qsTr("Legend göster"); onClicked: charts.invalidate() }
        }
        GeoChartOptions {
            id: geo
            visible: kind.currentIndex >= 46
            columns: charts.columns
            chartKind: panel.kindValues[kind.currentIndex]
            Layout.fillWidth: true
            onEdited: { charts.invalidate(); panel.scheduleCreate() }
        }
        CompositionOptions {
            id: composition
            visible: kind.currentIndex >= 29 && kind.currentIndex < 46
            columns: charts.columns
            chartKind: panel.kindValues[kind.currentIndex]
            onEdited: { charts.invalidate(); panel.scheduleCreate() }
        }
        MultivariateOptions {
            id: multivariate
            visible: kind.currentIndex >= 20 && kind.currentIndex < 29
            columns: charts.columns
            selectedCount: panel.selected.length
            chartKind: panel.kindValues[kind.currentIndex]
            onEdited: { charts.invalidate(); panel.scheduleCreate() }
        }
        DistributionOptions {
            id: distribution
            visible: kind.currentIndex < 29
            columns: charts.columns
            chartKind: panel.kindValues[kind.currentIndex]
            onEdited: { charts.invalidate(); panel.scheduleCreate() }
        }
        UiButton {
            objectName: "chartRecalc"
            text: qsTr("Yeniden hesapla")
            Layout.fillWidth: true
            enabled: !projects.busy && dataView.datasets.length > 0 && !charts.busy
            onClicked: { panel.armLive(); panel.create() }
        }
    }

    Flow {
        Layout.fillWidth: true
        spacing: Theme.sm
        UiButton {
            objectName: "chartCancel"
            text: qsTr("İptal")
            enabled: charts.busy
            onClicked: charts.cancel()
        }
        UiButton {
            objectName: "chartSave"
            text: qsTr("Projeye kaydet")
            primary: true
            enabled: charts.current && !projects.busy && !projects.readOnly
            onClicked: charts.save()
        }
    }
    StateNotice {
        Layout.fillWidth: true
        kind: charts.errorText ? "error" : charts.busy ? "loading" : "info"
        heading: qsTr("Grafik sonucu")
        detail: charts.errorText || charts.message
    }
    UiLabel {
        objectName: "chartCausalNotice"
        visible: ["scatter", "correlation", "line"].indexOf(panel.kindName) >= 0
        text: qsTr("Bu bir ilişki özetidir. Nedensel etki değildir.")
        color: Theme.warning
        Layout.fillWidth: true
        wrapMode: Text.Wrap
    }
    UiLabel {
        text: (charts.explanation.see || "")
        visible: text.length > 0
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        font.pixelSize: Theme.small
        color: Theme.secondary
    }
    Flow {
        Layout.fillWidth: true
        spacing: Theme.sm
        UiButton {
            objectName: "chartExportPNG"
            text: qsTr("PNG")
            enabled: charts.current && !projects.busy
            onClicked: { exportDialog.nameFilters = ["PNG (*.png)"]; exportDialog.defaultSuffix = "png"; exportDialog.open() }
        }
        UiButton {
            objectName: "chartExportSVG"
            text: qsTr("SVG")
            enabled: charts.current && !projects.busy
            onClicked: { exportDialog.nameFilters = ["SVG (*.svg)"]; exportDialog.defaultSuffix = "svg"; exportDialog.open() }
        }
        UiButton {
            objectName: "chartExportPDF"
            text: qsTr("PDF")
            enabled: charts.current && !projects.busy
            onClicked: { exportDialog.nameFilters = ["PDF (*.pdf)"]; exportDialog.defaultSuffix = "pdf"; exportDialog.open() }
        }
    }
    FileDialog {
        id: exportDialog
        title: qsTr("Yeni çıktı dosyası seçin (mevcut dosya korunur)")
        fileMode: FileDialog.SaveFile
        onAccepted: charts.export(selectedFile.toString(), defaultSuffix)
    }
    UiButton {
        objectName: "chartSelectionDataset"
        text: qsTr("Seçili satırlardan yeni dataset önizle")
        enabled: charts.current && !projects.busy && !projects.readOnly && (charts.selectionResult.count || 0) > 0
        Layout.fillWidth: true
        multiline: true
        onClicked: operations.previewChartSelection(JSON.stringify(charts.selectionResult))
    }
    UiButton {
        objectName: "chartSelectionExportContext"
        text: qsTr("Seçimi statik çıktıya işle (yalnız görünüm)")
        enabled: charts.current && !charts.busy
        Layout.fillWidth: true
        multiline: true
        onClicked: charts.freezeSelection()
    }
    UiTextArea {
        id: chartNote
        objectName: "chartInterpretationNote"
        placeholderText: qsTr("Grafik yorumu / bulgu notu (taslak)")
        Layout.fillWidth: true
        Layout.preferredHeight: 72 * Theme.scale
        Accessible.name: qsTr("Grafik yorumu")
    }
    UiButton {
        objectName: "chartSaveNote"
        text: qsTr("Yorumu kaydet (veri değişmez)")
        enabled: !!charts.chartResult.dataset_version
        Layout.fillWidth: true
        multiline: true
        onClicked: dataView.saveChartNote(charts.chartResult.dataset_version + ":" + (panel.kindName || "chart"), chartNote.text)
    }
    UiCombo {
        accessibleLabel: qsTr("Kayıtlı grafik")
        id: saved
        objectName: "chartSaved"
        model: charts.savedCharts
        textRole: "label"
        valueRole: "id"
        Layout.fillWidth: true
    }
    UiButton {
        text: qsTr("Kayıtlı grafiği aç")
        enabled: saved.currentIndex >= 0 && !projects.busy
        onClicked: { charts.openSaved(saved.currentValue); panel.restore() }
        Layout.fillWidth: true
    }
}
