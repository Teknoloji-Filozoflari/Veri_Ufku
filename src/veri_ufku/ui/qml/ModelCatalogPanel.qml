import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    objectName: "modelCatalogPanel"
    signal helpRequested(var origin, string context)
    property int selectedBlock: 1
    property var touchedBlocks: ({})
    property var featureState: ({})
    property var interactions: []
    property var withinIds: []
    property var comparison: ({})
    property var trainN: null
    property var testN: null
    property bool leakageAck: false
    property bool pendingSave: false
    spacing: Theme.md
    Layout.fillWidth: true

    readonly property var chipDefs: [
        { index: 1, title: qsTr("Doğrusal regresyon"), method: "ols" },
        { index: 2, title: qsTr("Ağırlıklı EKK (WLS)"), method: "wls" },
        { index: 3, title: qsTr("GLM (binomial/Poisson)"), method: "glm_binomial" },
        { index: 4, title: qsTr("Kuantile regresyon"), method: "quantile" },
        { index: 5, title: qsTr("Karışık etkiler"), method: "mixed" },
        { index: 6, title: qsTr("Tekrarlanan ölçüm"), method: "repeated" },
        { index: 7, title: qsTr("Güvenli formül"), method: "" },
        { index: 8, title: qsTr("Model tanılama (VIF/artık)"), method: "" },
        { index: 9, title: qsTr("Robust / Küme SE"), method: "ols" },
        { index: 10, title: qsTr("Model karşılaştırma (AIC/BIC)"), method: "" }
    ]

    readonly property string method: {
        if (selectedBlock === 3)
            return glmFamily.currentValue || "glm_binomial"
        if (selectedBlock === 7 || selectedBlock === 8 || selectedBlock === 10)
            return ""
        let def = chipDefs[selectedBlock - 1]
        return def ? (def.method || "") : "ols"
    }
    readonly property bool countModel: method === "glm_poisson" || method === "glm_negative_binomial"
    readonly property bool fitBlock: selectedBlock >= 1 && selectedBlock <= 6 || selectedBlock === 9
    readonly property bool leakageBlocks: !!(operations.modelLeakage && operations.modelLeakage.warning)
    readonly property bool primaryEnabled: {
        if (!root.fitBlock || projects.readOnly || statistics.busy || projects.busy)
            return false
        if (root.leakageBlocks && !root.leakageAck)
            return false
        return statistics.preflightCurrent && assumptions.checked
    }
    readonly property string primaryReason: {
        if (!root.fitBlock)
            return qsTr("Bu blok fit üretmez — açıklamayı okuyun.")
        if (root.leakageBlocks && !root.leakageAck)
            return qsTr("Sızıntı uyarısını onaylayın.")
        if (!statistics.preflightCurrent)
            return qsTr("Önce önkontrol çalıştırın.")
        if (!assumptions.checked)
            return qsTr("Varsayımları onaylayın.")
        if (projects.readOnly)
            return qsTr("Proje salt okunur.")
        return ""
    }
    readonly property string healthText: {
        let warn = root.leakageBlocks ? 1 : 0
        let pending = assumptions.checked ? 0 : 1
        return warn + qsTr(" uyarı · ") + pending + qsTr(" karar bekliyor")
    }

    function statusColor(status) {
        return status === "done" ? Theme.learningTone : status === "pending" ? Theme.warning : Theme.muted
    }
    function statusLabel(status) {
        return status === "done" ? qsTr("Tamam") : status === "pending" ? qsTr("Karar bekliyor") : qsTr("Dokunulmamış")
    }
    function chipStatus(index) {
        if (index === 7)
            return "untouched"
        if (root.touchedBlocks[String(index)]) {
            if (index === 10)
                return root.comparison.delta_aic !== undefined ? "done" : "pending"
            if (statistics.current && statistics.analysisResult && statistics.analysisResult.spec && statistics.analysisResult.spec.path === "models")
                return "done"
            return "pending"
        }
        return "untouched"
    }
    function markTouched(index) {
        let next = Object.assign({}, root.touchedBlocks)
        next[String(index)] = true
        root.touchedBlocks = next
    }
    function selectBlock(index) {
        root.selectedBlock = index
        markTouched(index)
        changedConfig()
    }
    function number(v) {
        return typeof v === "number" ? Number(v).toPrecision(6) : v === null || v === undefined ? qsTr("sunulmuyor") : String(v)
    }
    function key(picker) {
        return picker.currentValue || ""
    }
    function changedConfig() {
        assumptions.checked = false
        root.comparison = ({})
        statistics.invalidate()
        root.trainN = null
        root.testN = null
    }
    function updateFeature(column, attribute, value) {
        let next = JSON.parse(JSON.stringify(featureState))
        if (!next[column])
            next[column] = { selected: false, categorical: false, reference: "", random: false }
        next[column][attribute] = value
        featureState = next
        changedConfig()
    }
    function spec() {
        let features = [], refs = {}, slopes = []
        for (let c of statistics.columns) {
            let f = featureState[c.id]
            if (f && f.selected) {
                features.push(c.id)
                if (f.categorical)
                    refs[c.id] = f.reference
                if (f.random)
                    slopes.push(c.id)
            }
        }
        let m = root.method || "ols"
        return {
            path: "models",
            method: m,
            x: key(response),
            features: m === "repeated" ? [] : features,
            references: m === "repeated" ? ({}) : refs,
            interactions: m === "repeated" ? [] : interactions,
            covariance: key(covariance),
            weight: m === "wls" ? key(weight) : "",
            offset: root.countModel ? key(offset) : "",
            exposure: root.countModel ? key(exposure) : "",
            cluster: key(covariance) === "cluster" ? key(cluster) : "",
            group: (m === "mixed" || m === "repeated") ? key(group) : "",
            random_slopes: m === "mixed" ? slopes : [],
            within: m === "repeated" ? withinIds : [],
            quantile: Number(quantile.text),
            nb_alpha: Number(alpha.text),
            reml: reml.checked,
            max_iterations: iterations.value,
            missing_policy: complete.checked ? "complete" : "reject",
            question: question.text,
            hypothesis: hypothesis.text,
            unit: unit.text,
            observation_unit: observation.text,
            independent: independent.checked,
            measurement_confirmed: measurement.checked,
            assumptions_confirmed: assumptions.checked,
            scope: full.checked ? "full" : "view",
            confidence: Number(confidence.currentValue)
        }
    }
    function runPreflight() {
        if (!root.fitBlock)
            return
        markTouched(root.selectedBlock)
        statistics.create(JSON.stringify(root.spec()), true)
    }
    function runTrainSave() {
        if (!root.primaryEnabled)
            return
        markTouched(root.selectedBlock)
        root.pendingSave = true
        statistics.create(JSON.stringify(root.spec()), false)
    }
    function runSave() {
        if (statistics.current)
            statistics.save()
    }
    function runReset() {
        root.leakageAck = false
        root.pendingSave = false
        assumptions.checked = false
        featureState = ({})
        interactions = []
        withinIds = []
        root.comparison = ({})
        statistics.invalidate()
        root.trainN = null
        root.testN = null
    }

    Connections {
        target: statistics
        function onBusyChanged() {
            if (statistics.busy)
                return
            if (statistics.preflightCurrent && statistics.preflightResult)
                root.trainN = statistics.preflightResult.used_rows
            if (!root.pendingSave)
                return
            if (statistics.current && statistics.analysisResult && statistics.analysisResult.spec && statistics.analysisResult.spec.path === "models") {
                root.trainN = statistics.analysisResult.n
                root.testN = qsTr("held-out bu ekranda yok")
                root.pendingSave = false
                if (!projects.readOnly)
                    statistics.save()
            } else if (statistics.errorText) {
                root.pendingSave = false
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.sm
        UiLabel {
            objectName: "modelCatalogTitle"
            text: qsTr("Model")
            font.pixelSize: Theme.heading
            font.bold: true
        }
        Item { Layout.fillWidth: true }
        UiLabel {
            objectName: "modelHealthSummary"
            text: root.healthText
            color: Theme.secondary
            font.pixelSize: Theme.small
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignRight
            Layout.maximumWidth: 280 * Theme.scale
        }
    }

    GridLayout {
        Layout.fillWidth: true
        columns: 2
        columnSpacing: Theme.sm
        rowSpacing: Theme.sm
        Repeater {
            model: root.chipDefs
            Rectangle {
                id: chip
                required property var modelData
                objectName: "modelBlockChip_" + modelData.index
                signal clicked()
                onClicked: root.selectBlock(modelData.index)
                Layout.fillWidth: true
                implicitHeight: 36 * Theme.scale
                radius: Theme.radius
                color: root.selectedBlock === modelData.index ? Theme.violetSurface : Theme.raised
                border.color: root.selectedBlock === modelData.index ? Theme.modelTone : Theme.border
                border.width: 1
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.sm
                    anchors.rightMargin: Theme.sm
                    spacing: Theme.sm
                    Rectangle {
                        width: 8
                        height: 8
                        radius: 4
                        color: root.statusColor(root.chipStatus(modelData.index))
                        Layout.alignment: Qt.AlignVCenter
                    }
                    UiLabel {
                        Layout.fillWidth: true
                        text: modelData.index + " · " + modelData.title
                        elide: Text.ElideRight
                        wrapMode: Text.NoWrap
                        maximumLineCount: 1
                        font.pixelSize: Theme.small
                        font.bold: root.selectedBlock === modelData.index
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: chip.clicked()
                }
                Accessible.name: modelData.index + " " + modelData.title + " · " + root.statusLabel(root.chipStatus(modelData.index))
                Accessible.role: Accessible.Button
                Accessible.onPressAction: chip.clicked()
            }
        }
    }

    UiLabel {
        objectName: "modelBlock7Note"
        visible: root.selectedBlock === 7
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.secondary
        text: qsTr("Güvenli formül: serbest kod/eval yok. Predictor’lar ColumnId seçiminden matrix olur. Bu sürümde serbest formül dizesi desteklenmiyor.")
    }
    UiLabel {
        objectName: "modelBlock8Note"
        visible: root.selectedBlock === 8
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.secondary
        text: qsTr("Tanılama VIF/artık/heteroskedastisite fit ve önkontrol sonuçlarından okunur. Merkez Tanılama sekmesine bakın; sayı uydurulmaz.")
    }
    UiLabel {
        objectName: "modelBlock10Note"
        visible: root.selectedBlock === 10
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.secondary
        text: qsTr("AIC/BIC yalnız aynı response/satır/likelihood bağlamında. Quantile, REML mixed ve repeated için sunulmaz.")
    }

    ColumnLayout {
        visible: root.fitBlock
        Layout.fillWidth: true
        spacing: Theme.sm
        UiCombo {
            id: glmFamily
            objectName: "modelGlmFamily"
            visible: root.selectedBlock === 3
            Layout.fillWidth: true
            model: [
                { id: "glm_binomial", label: qsTr("GLM binomial") },
                { id: "glm_poisson", label: qsTr("GLM Poisson") },
                { id: "glm_negative_binomial", label: qsTr("GLM negatif binom") }
            ]
            textRole: "label"
            valueRole: "id"
            accessibleLabel: qsTr("GLM ailesi")
            onActivated: root.changedConfig()
        }
        UiLabel { text: qsTr("Bağımlı (Y)"); Layout.fillWidth: true }
        UiCombo {
            id: response
            objectName: "modelResponse"
            Layout.fillWidth: true
            model: statistics.columns
            textRole: "name"
            valueRole: "id"
            accessibleLabel: qsTr("Bağımlı (Y)")
            onActivated: root.changedConfig()
        }
        UiLabel {
            visible: root.method !== "repeated"
            text: qsTr("Bağımsız (X)")
            Layout.fillWidth: true
        }
        Repeater {
            model: statistics.columns
            delegate: RowLayout {
                required property var modelData
                Layout.fillWidth: true
                visible: root.method !== "repeated"
                UiCheckBox {
                    objectName: "modelFeature_" + modelData.name
                    text: modelData.name
                    checked: !!(root.featureState[modelData.id] && root.featureState[modelData.id].selected)
                    onToggled: root.updateFeature(modelData.id, "selected", checked)
                }
                UiCheckBox {
                    objectName: "modelCategory_" + modelData.name
                    text: qsTr("Kategorik")
                    checked: !!(root.featureState[modelData.id] && root.featureState[modelData.id].categorical)
                    onToggled: root.updateFeature(modelData.id, "categorical", checked)
                }
            }
        }
        Repeater {
            model: statistics.columns
            delegate: UiCheckBox {
                required property var modelData
                objectName: "modelWithin_" + modelData.name
                visible: root.method === "repeated"
                Layout.fillWidth: true
                text: modelData.name + qsTr(" · within")
                checked: root.withinIds.indexOf(modelData.id) >= 0
                onToggled: {
                    let ids = root.withinIds.filter(c => c !== modelData.id)
                    if (checked)
                        ids.push(modelData.id)
                    root.withinIds = ids
                    root.changedConfig()
                }
            }
        }
        GridLayout {
            columns: 1
            Layout.fillWidth: true
            UiLabel { text: qsTr("SE / covariance"); visible: root.selectedBlock !== 6 || true }
            UiCombo {
                id: covariance
                objectName: "modelCovariance"
                Layout.fillWidth: true
                accessibleLabel: qsTr("SE / covariance")
                textRole: "label"
                valueRole: "id"
                model: (root.method === "quantile" ? ["robust", "iid"] : (root.method === "mixed" || root.method === "repeated") ? ["nonrobust"] : root.method.startsWith("glm_") ? ["nonrobust", "HC0", "cluster"] : ["nonrobust", "HC3", "cluster"]).map(v => ({ id: v, label: v }))
                onActivated: root.changedConfig()
            }
            UiCombo {
                id: weight
                objectName: "modelWeight"
                visible: root.method === "wls"
                Layout.fillWidth: true
                model: [{ id: "", name: qsTr("Seçin") }].concat(statistics.columns)
                textRole: "name"
                valueRole: "id"
                accessibleLabel: qsTr("WLS ağırlık")
                onActivated: root.changedConfig()
            }
            UiCombo {
                id: offset
                objectName: "modelOffset"
                visible: root.countModel
                Layout.fillWidth: true
                model: [{ id: "", name: qsTr("Yok") }].concat(statistics.columns)
                textRole: "name"
                valueRole: "id"
                accessibleLabel: qsTr("Offset")
                onActivated: root.changedConfig()
            }
            UiCombo {
                id: exposure
                objectName: "modelExposure"
                visible: root.countModel
                Layout.fillWidth: true
                model: [{ id: "", name: qsTr("Yok") }].concat(statistics.columns)
                textRole: "name"
                valueRole: "id"
                accessibleLabel: qsTr("Exposure")
                onActivated: root.changedConfig()
            }
            UiCombo {
                id: cluster
                objectName: "modelCluster"
                visible: covariance.currentValue === "cluster"
                Layout.fillWidth: true
                model: [{ id: "", name: qsTr("Seçin") }].concat(statistics.columns)
                textRole: "name"
                valueRole: "id"
                accessibleLabel: qsTr("Küme")
                onActivated: root.changedConfig()
            }
            UiCombo {
                id: group
                objectName: "modelGroup"
                visible: root.method === "mixed" || root.method === "repeated"
                Layout.fillWidth: true
                model: [{ id: "", name: qsTr("Seçin") }].concat(statistics.columns)
                textRole: "name"
                valueRole: "id"
                accessibleLabel: qsTr("Grup / kilit")
                onActivated: root.changedConfig()
            }
            UiTextField {
                id: quantile
                objectName: "modelQuantile"
                visible: root.method === "quantile"
                text: "0.5"
                placeholderText: qsTr("Quantile 0.05–0.95")
                Accessible.name: placeholderText
                onTextEdited: root.changedConfig()
            }
            UiTextField {
                id: alpha
                objectName: "modelAlpha"
                visible: root.method === "glm_negative_binomial"
                text: "1"
                placeholderText: qsTr("NB alpha")
                Accessible.name: placeholderText
                onTextEdited: root.changedConfig()
            }
            UiCheckBox {
                id: reml
                objectName: "modelReml"
                visible: root.method === "mixed"
                checked: true
                text: qsTr("REML · AIC/BIC sunulmaz")
                onToggled: root.changedConfig()
            }
        }
        UiLabel {
            visible: root.selectedBlock === 9
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.secondary
            text: qsTr("Robust/Küme SE: OLS/WLS HC3+cluster; GLM HC0+cluster; mixed/repeated yalnız nonrobust. CR2/wild bootstrap bu sürümde desteklenmiyor.")
        }
        RowLayout {
            Layout.fillWidth: true
            UiCombo {
                id: confidence
                objectName: "modelConfidence"
                model: [{ id: 0.95, label: "%95 CI" }, { id: 0.90, label: "%90 CI" }, { id: 0.99, label: "%99 CI" }]
                textRole: "label"
                valueRole: "id"
                accessibleLabel: qsTr("Güven düzeyi")
                onActivated: root.changedConfig()
            }
            UiSpinBox {
                id: iterations
                objectName: "modelIterations"
                from: 1
                to: 2000
                value: 1000
                Accessible.name: qsTr("Maksimum iterasyon")
                onValueModified: root.changedConfig()
            }
        }
        UiCheckBox {
            id: complete
            objectName: "modelComplete"
            text: qsTr("Complete-case dışlamasına izin ver")
            onToggled: root.changedConfig()
        }
        UiCheckBox {
            id: full
            objectName: "modelFull"
            text: qsTr("Tam dataset (tablo filtresi yerine)")
            onToggled: root.changedConfig()
        }
        UiTextField {
            id: question
            objectName: "modelQuestion"
            Layout.fillWidth: true
            placeholderText: qsTr("Araştırma sorusu")
            Accessible.name: placeholderText
            onTextEdited: root.changedConfig()
        }
        UiTextField {
            id: hypothesis
            objectName: "modelHypothesis"
            Layout.fillWidth: true
            placeholderText: qsTr("Hipotez / etki")
            Accessible.name: placeholderText
            onTextEdited: root.changedConfig()
        }
        UiTextField {
            id: unit
            objectName: "modelUnit"
            Layout.fillWidth: true
            placeholderText: qsTr("Response birimi")
            Accessible.name: placeholderText
            onTextEdited: root.changedConfig()
        }
        UiTextField {
            id: observation
            objectName: "modelObservation"
            Layout.fillWidth: true
            placeholderText: qsTr("Gözlem birimi")
            Accessible.name: placeholderText
            onTextEdited: root.changedConfig()
        }
        UiCheckBox {
            id: measurement
            objectName: "modelMeasurement"
            text: qsTr("Ölçüm ve response anlamını doğruladım")
            onToggled: root.changedConfig()
        }
        UiCheckBox {
            id: independent
            objectName: "modelIndependent"
            text: qsTr("Bağımsızlık tasarımını doğruladım")
            onToggled: root.changedConfig()
        }
        UiButton {
            objectName: "modelPreflight"
            text: qsTr("Önkontrol (design / VIF)")
            Layout.fillWidth: true
            enabled: !statistics.busy && root.fitBlock
            onClicked: root.runPreflight()
        }
        UiCheckBox {
            id: assumptions
            objectName: "modelAssumptions"
            text: qsTr("Önkontrolü ve yöntem varsayımlarını inceledim")
            enabled: statistics.preflightCurrent
        }
        UiLabel {
            objectName: "modelPreflightText"
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.secondary
            font.pixelSize: Theme.small
            text: statistics.preflightCurrent
                ? (qsTr("Formül: ") + statistics.preflightResult.formula + qsTr(" · dışlanan ") + statistics.preflightResult.excluded_rows)
                : qsTr("Güncel önkontrol gerekli.")
        }
    }

    ColumnLayout {
        visible: root.selectedBlock === 10
        Layout.fillWidth: true
        spacing: Theme.sm
        UiCombo {
            id: comparisonChoice
            objectName: "modelCompareChoice"
            Layout.fillWidth: true
            model: statistics.savedAnalyses.filter(r => r.path === "models")
            textRole: "label"
            valueRole: "id"
            accessibleLabel: qsTr("Karşılaştırılacak kayıt")
        }
        UiButton {
            objectName: "modelCompare"
            text: qsTr("AIC/BIC bağlamını kontrol et")
            Layout.fillWidth: true
            onClicked: root.comparison = statistics.compareModel(root.key(comparisonChoice))
        }
        UiLabel {
            objectName: "modelCompareText"
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: root.comparison.delta_aic !== undefined
                ? ("ΔAIC=" + root.number(root.comparison.delta_aic) + " · ΔBIC=" + root.number(root.comparison.delta_bic) + " · " + (root.comparison.warning || ""))
                : qsTr("Bağlamı doğrulanmış karşılaştırma yok.")
        }
    }

    UiLabel {
        objectName: "modelLeakageNotice"
        visible: (operations.modelLeakage.text || "").length > 0
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: operations.modelLeakage.warning ? Theme.warning : Theme.secondary
        text: operations.modelLeakage.text || ""
    }
    UiCheckBox {
        objectName: "modelLeakageAck"
        visible: root.leakageBlocks
        Layout.fillWidth: true
        text: qsTr("Sızıntı uyarısını okudum; eğitim katmanı fit / test yeniden öğretilmez")
        checked: root.leakageAck
        onToggled: root.leakageAck = checked
    }

    UiLabel {
        objectName: "modelPrimaryReason"
        visible: root.primaryReason.length > 0
        text: root.primaryReason
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        color: Theme.warning
        font.pixelSize: Theme.small
    }
    RowLayout {
        Layout.fillWidth: true
        UiButton {
            objectName: "modelPrimaryCancel"
            text: qsTr("Sıfırla")
            quiet: true
            enabled: !statistics.busy
            onClicked: root.runReset()
        }
        UiButton {
            objectName: "modelPrimaryAction"
            text: qsTr("Eğit ve kaydet")
            tone: "violet"
            primary: true
            Layout.fillWidth: true
            enabled: root.primaryEnabled
            Accessible.description: root.primaryReason
            onClicked: root.runTrainSave()
        }
    }
}
