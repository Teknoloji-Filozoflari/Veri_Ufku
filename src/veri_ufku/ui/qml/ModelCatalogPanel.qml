import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    objectName: "modelCatalogPanel"
    signal helpRequested(var origin, string context)
    signal sectionRequested(int section)
    property int selectedBlock: 1
    property var touchedBlocks: ({})
    spacing: Theme.md
    Layout.fillWidth: true

    // Şemanın Model aşamasındaki on alt başlığı birebir (ADR079).
    // tier: core = çekirdek kurulum (temel + keşif); optional = isteğe bağlı modül (B-06).
    readonly property var schemaEntries: [
        {
            index: 1,
            title: qsTr("Hedef ve plan"),
            module: qsTr("Modül · Model"),
            tier: "core",
            summary: qsTr("Hedef sütun · sızıntı kontrolü · özellikler · grup ve zaman yapısına göre bölme.")
        },
        {
            index: 2,
            title: qsTr("Hazırla'dan devralınanlar"),
            module: qsTr("Modül · Model"),
            tier: "core",
            summary: qsTr("Mod 2 ile planlanan adımlar burada uygulanır: doldurma · standardizasyon · kodlama. Yalnız eğitim verisiyle öğrenilir.")
        },
        {
            index: 3,
            title: qsTr("Regresyon"),
            module: qsTr("Modül · Model"),
            tier: "core",
            summary: qsTr("Hedef sürekli sayı. Doğrusal · Ridge · Lasso · karar ağacı · Random Forest · SVR.")
        },
        {
            index: 4,
            title: qsTr("Sınıflandırma"),
            module: qsTr("Modül · Model"),
            tier: "core",
            summary: qsTr("Hedef kategori. Lojistik regresyon · Naive Bayes · K-NN · karar ağacı · Random Forest · SVM.")
        },
        {
            index: 5,
            title: qsTr("Kümeleme"),
            module: qsTr("Modül · Model"),
            tier: "core",
            summary: qsTr("Hedef yok, gruplar aranır. K-Means · hiyerarşik · DBSCAN · Mean Shift · Gaussian karışım · anomali tespiti.")
        },
        {
            index: 6,
            title: qsTr("Boyut azaltma"),
            module: qsTr("Modül · Model"),
            tier: "core",
            summary: qsTr("Hedef yok, yapı keşfedilir. PCA · t-SNE (yalnız keşif görselleştirmesi).")
        },
        {
            index: 7,
            title: qsTr("Doğrulama ve karşılaştırma"),
            module: qsTr("Modül · Model"),
            tier: "core",
            summary: qsTr("Çapraz doğrulama · hiperparametre ayarı · R² · RMSE · F1 · AUC · ROC eğrisi · kalibrasyon · deney kaydı.")
        },
        {
            index: 8,
            title: qsTr("Yorumlama"),
            module: qsTr("Modül · Model"),
            tier: "optional",
            summary: qsTr("Özellik önemi · permütasyon önemi · kısmi bağımlılık · SHAP · hata ve artık analizi.")
        },
        {
            index: 9,
            title: qsTr("Özel veri türü yolları"),
            module: qsTr("Modül · Tür modülleri"),
            tier: "optional",
            summary: qsTr("Zaman serisi · sinyal · mekânsal veri · görüntü · ses · metin.")
        },
        {
            index: 10,
            title: qsTr("İleri yollar"),
            module: qsTr("Modül · Model"),
            tier: "optional",
            summary: qsTr("Öneri sistemi · birliktelik (sepet) analizi · yarı denetimli öğrenme · sinir ağı.")
        }
    ]

    function statusColor(status) {
        return status === "done" ? Theme.learningTone : status === "pending" ? Theme.warning : Theme.muted
    }
    function statusLabel(status) {
        return status === "done" ? qsTr("Kayıt var") : status === "pending" ? qsTr("Karar bekliyor") : qsTr("Dokunulmamış")
    }
    function statusFor(index) {
        let map = modelPaths.statusMap || ({})
        return map[String(index)] || "untouched"
    }
    function optionalFor(index) {
        return (modelPaths.optionalModules || []).filter(m => (m.entries || []).indexOf(index) >= 0)
    }
    function selectBlock(index) {
        root.selectedBlock = index
        let next = Object.assign({}, root.touchedBlocks)
        next[String(index)] = true
        root.touchedBlocks = next
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
            objectName: "modelCatalogTier"
            text: qsTr("Çekirdek: temel + keşif · İsteğe bağlı modül: yorum ve ileri yollar")
            color: Theme.secondary
            font.pixelSize: Theme.small
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignRight
            Layout.maximumWidth: 240 * Theme.scale
        }
    }

    UiLabel {
        objectName: "modelCatalogScope"
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.secondary
        text: qsTr("Model aşaması tahmin yoludur: önce değerlendirme planı, test verisi en son açılır. Açıklayıcı regresyon (OLS/WLS/GLM/kuantil/karışık etki) İstatistik aşamasındaki «İstatistiksel modeller ve tanılama» yüzeyindedir.")
    }

    ColumnLayout {
        objectName: "modelCatalogChips"
        Layout.fillWidth: true
        spacing: Theme.xs
        Repeater {
            model: root.schemaEntries
            delegate: Rectangle {
                id: chip
                required property var modelData
                objectName: "modelBlockChip_" + modelData.index
                signal clicked()
                onClicked: root.selectBlock(modelData.index)
                Layout.fillWidth: true
                implicitHeight: chipRow.implicitHeight + Theme.sm * 2
                radius: Theme.radius
                color: root.selectedBlock === modelData.index ? Theme.violetSurface : Theme.raised
                border.color: root.selectedBlock === modelData.index ? Theme.modelTone : Theme.border
                border.width: 1
                ColumnLayout {
                    id: chipRow
                    anchors.fill: parent
                    anchors.leftMargin: Theme.sm
                    anchors.rightMargin: Theme.sm
                    anchors.topMargin: Theme.xs
                    anchors.bottomMargin: Theme.xs
                    spacing: 2
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.sm
                        Rectangle {
                            width: 8
                            height: 8
                            radius: 4
                            color: root.statusColor(root.statusFor(modelData.index))
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
                        UiLabel {
                            text: modelData.module
                            color: Theme.secondary
                            font.pixelSize: Theme.small
                            elide: Text.ElideRight
                        }
                    }
                    UiLabel {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        color: Theme.secondary
                        font.pixelSize: Theme.small
                        text: modelData.summary
                    }
                    UiLabel {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        font.pixelSize: Theme.small
                        color: modelData.tier === "core" ? Theme.secondary : Theme.warning
                        text: modelData.tier === "core"
                            ? qsTr("Çekirdek kurulum")
                            : qsTr("İsteğe bağlı modül · kurulumda yoksa yol kapalı")
                    }
                    Repeater {
                        model: root.optionalFor(modelData.index)
                        delegate: UiLabel {
                            required property var modelData
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            font.pixelSize: Theme.small
                            color: modelData.available ? Theme.secondary : Theme.warning
                            text: modelData.label + " · " + (modelData.available
                                ? qsTr("kurulu")
                                : qsTr("kurulu değil: ") + modelData.reason)
                        }
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: chip.clicked()
                }
                Accessible.name: modelData.index + " " + modelData.title + " · " + modelData.module + " · " + root.statusLabel(root.statusFor(modelData.index))
                Accessible.role: Accessible.Button
                Accessible.onPressAction: chip.clicked()
            }
        }
    }

    UiLabel {
        objectName: "modelCatalogInferenceNote"
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.secondary
        text: qsTr("Çıkarım (katsayı, p-değeri, VIF, AIC/BIC) Model aşamasında değil, İstatistik aşamasında üretilir. Buradaki sonuçlar tahmin başarısıdır; ilişki nedensellik kanıtı değildir.")
    }
    UiButton {
        objectName: "modelCatalogOpenStatistics"
        text: qsTr("İstatistik aşamasını aç (açıklayıcı regresyon)")
        Layout.fillWidth: true
        onClicked: root.sectionRequested(4)
    }

    UiLabel {
        objectName: "modelLeakageNotice"
        visible: (modelPaths.leakageText || "").length > 0
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.warning
        text: modelPaths.leakageText || ""
    }
}
