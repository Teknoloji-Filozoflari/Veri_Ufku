import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: panel
    objectName: "modelPathsPanel"
    signal helpRequested(var origin, string context)
    signal sectionRequested(int section)
    spacing: Theme.md
    Layout.fillWidth: true

    UiLabel {
        text: qsTr("Hazırla'dan devralınanlar")
        font.pixelSize: Theme.heading
        font.bold: true
        Layout.fillWidth: true
        wrapMode: Text.Wrap
    }
    UiLabel {
        objectName: "modelPathsScope"
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.secondary
        text: qsTr("Mod 2 ile planlanan adımlar burada uygulanır. Doldurma · standardizasyon · kodlama yalnız eğitim katında öğrenilir; test verisine bilgi sıkmaz. Mod 2 hiçbir zaman yeni veri sürümü üretmez.")
    }
    UiLabel {
        objectName: "modelPathsLeakage"
        visible: (modelPaths.leakageText || "").length > 0
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.warning
        text: modelPaths.leakageText || ""
    }

    UiLabel {
        objectName: "modelPathsRecipeTitle"
        text: qsTr("Saklanan tarifler") + " (" + (modelPaths.planCount || 0) + ")"
        font.bold: true
        Layout.fillWidth: true
    }
    UiLabel {
        objectName: "modelPathsRecipeEmpty"
        visible: (modelPaths.planCount || 0) === 0
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.secondary
        text: qsTr("Kayıtlı tarif yok. Hazırla aşamasında «Öğrenilen dönüşümler» için Mod 2 seçip «Model için planla» deyin; ya da Model aşamasındaki «Hedef ve plan» bloğundan pipeline planını oluşturun.")
    }
    Repeater {
        model: modelPaths.recipeList || []
        delegate: ColumnLayout {
            required property var modelData
            Layout.fillWidth: true
            spacing: Theme.xs
            UiLabel {
                objectName: "modelPathsRecipe_" + modelData.id
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: modelData.label
                      + " · durum: " + modelData.status
                      + " · öğrenme kapsamı: " + modelData.learn_scope
                      + " · veri sürümü: " + (modelData.dataset_version || "").slice(-8)
                      + "\n" + modelData.reason
            }
            Repeater {
                model: modelData.operations || []
                delegate: UiLabel {
                    required property var modelData
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    color: Theme.secondary
                    font.pixelSize: Theme.small
                    text: "· " + modelData.kind + (modelData.method ? " / " + modelData.method : "")
                          + (modelData.reason ? " — " + modelData.reason : "")
                          + (modelData.learned_scope ? " [" + modelData.learned_scope + "]" : "")
                }
            }
            UiButton {
                objectName: "modelPathsOpenRecipe_" + modelData.id
                text: qsTr("Tarifi «Hedef ve plan» formunda aç")
                Layout.fillWidth: true
                visible: modelData.kind === "preparation"
                enabled: !projects.busy
                onClicked: modelPaths.openRecipe(modelData.id)
            }
        }
    }

    UiLabel {
        objectName: "modelPathsPlanTitle"
        text: qsTr("Geçerli hazırlık planının öğrenilen adımları")
        font.bold: true
        Layout.fillWidth: true
        visible: !!(preparation.report.plan)
    }
    UiLabel {
        objectName: "modelPathsPlanEmpty"
        visible: !preparation.report.plan
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.secondary
        text: qsTr("Hazırlık planı yok. «Hedef ve plan» bloğunda hedefi ve özellikleri seçip uygunluk raporu ve plan üretin.")
    }
    Repeater {
        model: preparation.report.plan ? (preparation.report.plan.steps || []) : []
        delegate: UiLabel {
            required property var modelData
            objectName: "modelPathsStep_" + modelData.kind
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: "· " + modelData.kind
                  + (modelData.learned_scope === "training_fold"
                     ? qsTr(" — yalnız eğitim katında öğrenilir")
                     : qsTr(" — satırdan üretilir"))
                  + "\n" + (modelData.reason || "")
        }
    }
    UiButton {
        objectName: "modelPathsOpenPrepare"
        text: qsTr("Hazırla aşamasında öğrenilen dönüşümleri düzenle")
        Layout.fillWidth: true
        onClicked: panel.sectionRequested(2)
    }
    UiLabel {
        objectName: "modelPathsError"
        visible: (modelPaths.errorText || "").length > 0
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.warning
        text: modelPaths.errorText || ""
    }
}
