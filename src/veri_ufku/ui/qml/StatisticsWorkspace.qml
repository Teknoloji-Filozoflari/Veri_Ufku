import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    objectName: "statisticsWorkspace"
    property var catalogControls: null
    spacing: Theme.sm
    Layout.fillWidth: true
    Layout.fillHeight: true
    signal helpRequested(var origin, string context)

    readonly property var result: statistics.analysisResult || ({})
    readonly property var preflight: statistics.preflightResult || ({})
    readonly property bool hasResult: !!(result.primary)
    readonly property bool hasPreflight: statistics.preflightCurrent
    readonly property bool stale: {
        if (!result.dataset_version)
            return false
        let ver = (dataView.dataContent && dataView.dataContent.version) || ""
        return ver && result.dataset_version !== ver && !statistics.current
    }

    function number(value) {
        return typeof value === "number" ? Number(value).toPrecision(6) : value === null ? qsTr("sunulmuyor") : String(value)
    }
    function pvalue(value) {
        return value === 0 ? "0 (Float64 alt sınırı; kesinlik değildir)" : number(value)
    }
    function statistic(method) {
        return ({ welch_t: "t", paired_t: "t", mann_whitney: "U", wilcoxon: "W", anova: "F", welch_anova: "F", kruskal: "H", chi2: "Ki-kare", fisher: "Örneklem odds oranı", pearson: "r", spearman: "rho" })[method] || qsTr("İstatistik")
    }
    function interval(effect) {
        if (!effect)
            return ""
        let c = effect.confidence_interval
        return c
            ? "%" + Math.round(c.level * 100) + qsTr(" güven aralığı: [") + number(c.low) + ", " + number(c.high) + "] · " + c.method + " · " + c.target
            : qsTr("Güven aralığı: ") + (effect.ci_limitation || qsTr("CI yok — bu yöntemde sunulmuyor"))
    }
    function exclusions(e) {
        e = e || ({})
        return qsTr("Eksik alanlı kayıt: ") + (e.null_rows || 0)
              + qsTr(" · sonlu olmayan değer: ") + (e.nonfinite_rows || 0)
              + qsTr(" · eksik/geçersiz kişi anahtarı: ") + (e.missing_key_rows || 0)
              + qsTr(" · eşleşmeyen kişi: ") + (e.unmatched_people || 0)
              + qsTr(" · eksik ölçümlü çift: ") + (e.incomplete_pairs || 0)
    }
    function runPreflight() {
        if (root.catalogControls && root.catalogControls.runPreflight)
            root.catalogControls.runPreflight()
    }
    function runFull() {
        if (root.catalogControls && root.catalogControls.runFull)
            root.catalogControls.runFull()
    }
    function runSave() {
        if (root.catalogControls && root.catalogControls.runSave)
            root.catalogControls.runSave()
        else
            statistics.save()
    }
    function runReset() {
        if (root.catalogControls && root.catalogControls.runReset)
            root.catalogControls.runReset()
        else
            statistics.invalidate()
    }
    function syncAssumptions(checked) {
        if (root.catalogControls && root.catalogControls.setAssumptions)
            root.catalogControls.setAssumptions(checked)
    }

    // --- Soru / öneri ---
    UiLabel {
        text: qsTr("Soru odaklı istatistik")
        font.pixelSize: Theme.heading
        font.bold: true
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
    }
    ColumnLayout {
        objectName: "statisticsAdvice"
        visible: (statistics.advice.question || "").length > 0
        Layout.fillWidth: true
        spacing: Theme.sm
        UiLabel { objectName: "statisticsAdviceQuestion"; text: statistics.advice.question || ""; Layout.fillWidth: true; wrapMode: Text.Wrap; font.bold: true }
        UiLabel { objectName: "statisticsAdviceStructure"; text: statistics.advice.structure || ""; visible: text.length > 0; Layout.fillWidth: true; wrapMode: Text.Wrap }
        UiLabel { objectName: "statisticsAdviceSuggestion"; text: statistics.advice.suggestion || ""; visible: text.length > 0; Layout.fillWidth: true; wrapMode: Text.Wrap }
        UiLabel { objectName: "statisticsAdviceAssumption"; text: statistics.advice.assumption || ""; visible: text.length > 0; Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.warning }
        UiLabel { objectName: "statisticsAdviceSelection"; text: statistics.advice.selection || ""; visible: text.length > 0; Layout.fillWidth: true; wrapMode: Text.Wrap }
    }
    UiLabel {
        visible: !((statistics.advice.question || "").length > 0)
        text: qsTr("Sağdan soru / yol / değişken seçin. Canlı önkontrol öneri kartını doldurur; yöntem otomatik seçilmez.")
        color: Theme.secondary
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
    }

    // --- Sonuç özeti ---
    Frame {
        Layout.fillWidth: true
        padding: Theme.md
        background: Rectangle { color: Theme.surface; border.color: Theme.border; radius: Theme.radius }
        ColumnLayout {
            width: parent.width
            spacing: Theme.sm
            UiLabel {
                objectName: "statisticsResultScope"
                text: root.hasResult
                    ? ((statistics.current ? qsTr("Güncel veri/filtre sonucu") : qsTr("Kayıtlı veya eski veri/yapılandırma sonucu — sürümü kontrol edin"))
                       + "\n" + qsTr("Soru: ") + ((result.spec && result.spec.question) || "")
                       + "\n" + qsTr("Sürüm: ") + (result.dataset_version || ""))
                    : root.hasPreflight
                        ? (qsTr("Önkontrol · kullanılan ") + (preflight.used_rows || 0) + qsTr(" / nüfus ") + (preflight.population_n || 0)
                           + qsTr(" · dışlanan ") + (preflight.excluded_rows || 0))
                        : qsTr("Sonuç yok — önizleme veya varsayım onayı sonrası tam analiz")
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                font.bold: true
            }
            UiLabel {
                objectName: "statisticsPrimary"
                visible: root.hasResult && !!(result.primary && result.primary.effect)
                text: root.hasResult && result.primary && result.primary.effect
                    ? (result.method_label || "")
                      + "\nn=" + JSON.stringify(result.n) + qsTr(" · dışlanan kayıt=") + result.excluded_rows
                      + "\n" + root.statistic(result.method) + "=" + root.number(result.primary.statistic) + " · p=" + root.pvalue(result.primary.p_value)
                      + "\n" + result.primary.effect.name + "=" + root.number(result.primary.effect.value)
                      + "\n" + root.interval(result.primary.effect)
                    : ""
                Layout.fillWidth: true
                wrapMode: Text.Wrap
            }
            UiLabel {
                visible: root.hasPreflight && !root.hasResult
                text: root.exclusions(preflight.exclusions)
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Theme.secondary
            }
            UiLabel {
                objectName: "statisticsStaleWarning"
                visible: root.stale
                text: qsTr("Eski veri sürümü — yeniden hesaplayın")
                color: Theme.warning
                Layout.fillWidth: true
                wrapMode: Text.Wrap
            }
        }
    }

    // --- Grafik alanı (mevcut charts; yeni motor yok) ---
    Frame {
        objectName: "statisticsChartFrame"
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 160
        padding: Theme.md
        background: Rectangle { color: Theme.raised; border.color: Theme.border; radius: Theme.radius }
        ColumnLayout {
            anchors.fill: parent
            spacing: Theme.sm
            UiLabel {
                text: charts.chartResult && charts.chartResult.dataset_version
                    ? qsTr("İlgili grafik (Görselleştir motoru) · n=") + (charts.chartResult.used_n || 0)
                    : qsTr("Tablo / grafik: değişken atanınca Görselleştir motoru ile üretilebilir; uydurma çizim yok.")
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Theme.secondary
            }
            Image {
                objectName: "statisticsChartImage"
                visible: !!(charts.chartResult && charts.chartResult.dataset_version)
                Layout.fillWidth: true
                Layout.fillHeight: true
                fillMode: Image.PreserveAspectFit
                source: charts.chartResult && charts.chartResult.image_id ? ("image://charts/" + charts.chartResult.image_id) : ""
            }
        }
    }

    UiCheckBox {
        id: assumptionsBox
        objectName: "statisticsAssumptions"
        text: qsTr("Önkontrolü, dağılım/uç değerleri, bağımsızlığı ve seçili yöntemin hipotezini inceledim")
        Layout.fillWidth: true
        onCheckedChanged: root.syncAssumptions(checked)
        onClicked: {
            if (checked)
                root.runFull()
        }
    }
    Connections {
        target: root.catalogControls
        function onAssumptionsCheckedChanged() {
            if (root.catalogControls && assumptionsBox.checked !== root.catalogControls.assumptionsChecked)
                assumptionsBox.checked = root.catalogControls.assumptionsChecked
        }
    }
    UiLabel {
        visible: root.hasPreflight && !assumptionsBox.checked
        text: qsTr("Varsayımları onaylayın — tam analiz (p/etki) onaysız üretilmez.")
        color: Theme.warning
        Layout.fillWidth: true
        wrapMode: Text.Wrap
    }

    StateNotice {
        Layout.fillWidth: true
        kind: statistics.errorText ? "error" : statistics.busy ? "loading" : "info"
        heading: qsTr("Analiz durumu")
        detail: statistics.errorText || statistics.message
    }

    Flow {
        Layout.fillWidth: true
        spacing: Theme.sm
        UiButton {
            objectName: "statisticsReset"
            text: qsTr("Sıfırla")
            quiet: true
            enabled: !statistics.busy
            onClicked: root.runReset()
        }
        UiButton {
            objectName: "statisticsPreflight"
            text: qsTr("Önizle")
            tone: "violet"
            enabled: !projects.busy && dataView.datasets.length > 0 && !statistics.busy
            primary: !statistics.current
            onClicked: root.runPreflight()
        }
        UiButton {
            objectName: "statisticsRun"
            visible: false
            text: qsTr("Analizi çalıştır")
            enabled: statistics.preflightCurrent && assumptionsBox.checked && !projects.busy
            onClicked: {
                root.syncAssumptions(true)
                assumptionsBox.checked = true
                root.runFull()
            }
        }
        UiButton {
            objectName: "statisticsSave"
            text: qsTr("Uygula ve kaydet")
            tone: "violet"
            primary: true
            enabled: statistics.current && !projects.busy && !projects.readOnly
            onClicked: root.runSave()
        }
    }
}
