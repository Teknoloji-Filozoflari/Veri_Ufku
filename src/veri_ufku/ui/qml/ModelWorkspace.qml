import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    objectName: "modelWorkspace"
    property var catalogControls: null
    property int resultTab: 1
    spacing: Theme.sm
    Layout.fillWidth: true
    Layout.fillHeight: true
    signal helpRequested(var origin, string context)

    readonly property var result: statistics.analysisResult || ({})
    readonly property bool hasModel: !!(result.spec && result.spec.path === "models")
    readonly property var coefficients: result.coefficients || []
    readonly property var firstCoef: coefficients.length > 0 ? coefficients[0] : null
    readonly property var fit: result.fit || ({})
    readonly property var diagnostics: result.diagnostics || ({})
    readonly property bool stale: {
        if (!result.dataset_version)
            return false
        let ver = (dataView.dataContent && dataView.dataContent.version) || ""
        return ver && result.dataset_version !== ver && !statistics.current
    }

    function number(value) {
        return typeof value === "number" ? Number(value).toPrecision(6) : value === null || value === undefined ? qsTr("sunulmuyor") : String(value)
    }
    function badge(label, value) {
        return label + "\n" + value
    }
    function trainN() {
        if (root.catalogControls && root.catalogControls.trainN !== undefined && root.catalogControls.trainN !== null)
            return root.catalogControls.trainN
        if (result.n !== undefined && result.n !== null)
            return result.n
        return qsTr("atanmadı")
    }
    function testN() {
        if (root.catalogControls && root.catalogControls.testN !== undefined && root.catalogControls.testN !== null)
            return root.catalogControls.testN
        return qsTr("held-out bu ekranda yok")
    }
    function leakageText() {
        let text = (operations.modelLeakage && operations.modelLeakage.text) || ""
        if (text.length > 0)
            return text
        return qsTr("yok")
    }

    UiLabel {
        text: qsTr("Model sonucu")
        font.pixelSize: Theme.heading
        font.bold: true
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
    }

    Flow {
        objectName: "modelResultTabs"
        Layout.fillWidth: true
        spacing: Theme.sm
        UiButton {
            objectName: "modelResultTab_1"
            text: qsTr("Özet")
            primary: root.resultTab === 1
            onClicked: root.resultTab = 1
        }
        UiButton {
            objectName: "modelResultTab_2"
            text: qsTr("Katsayılar")
            primary: root.resultTab === 2
            onClicked: root.resultTab = 2
        }
        UiButton {
            objectName: "modelResultTab_3"
            text: qsTr("Artıklar")
            primary: root.resultTab === 3
            onClicked: root.resultTab = 3
        }
        UiButton {
            objectName: "modelResultTab_4"
            text: qsTr("Tanılama")
            primary: root.resultTab === 4
            onClicked: root.resultTab = 4
        }
    }

    Flow {
        objectName: "modelResultBadges"
        Layout.fillWidth: true
        spacing: Theme.sm
        visible: root.hasModel
        Rectangle {
            objectName: "modelBadgeEstimate"
            width: badgeEstimate.implicitWidth + Theme.md * 2
            height: badgeEstimate.implicitHeight + Theme.sm * 2
            radius: Theme.radius
            color: Theme.violetSurface
            border.color: Theme.border
            UiLabel {
                id: badgeEstimate
                anchors.centerIn: parent
                text: root.badge(qsTr("katsayı"), root.firstCoef ? root.number(root.firstCoef.estimate) : qsTr("sunulmuyor"))
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: Theme.small
            }
        }
        Rectangle {
            width: badgeSe.implicitWidth + Theme.md * 2
            height: badgeSe.implicitHeight + Theme.sm * 2
            radius: Theme.radius
            color: Theme.surface
            border.color: Theme.border
            UiLabel {
                id: badgeSe
                anchors.centerIn: parent
                text: root.badge("SE", root.firstCoef ? root.number(root.firstCoef.se) : qsTr("sunulmuyor"))
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: Theme.small
            }
        }
        Rectangle {
            width: badgeT.implicitWidth + Theme.md * 2
            height: badgeT.implicitHeight + Theme.sm * 2
            radius: Theme.radius
            color: Theme.surface
            border.color: Theme.border
            UiLabel {
                id: badgeT
                anchors.centerIn: parent
                text: root.badge("t/z", root.firstCoef && root.firstCoef.t !== undefined ? root.number(root.firstCoef.t) : (root.firstCoef && root.firstCoef.z !== undefined ? root.number(root.firstCoef.z) : qsTr("sunulmuyor")))
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: Theme.small
            }
        }
        Rectangle {
            width: badgeP.implicitWidth + Theme.md * 2
            height: badgeP.implicitHeight + Theme.sm * 2
            radius: Theme.radius
            color: Theme.surface
            border.color: Theme.border
            UiLabel {
                id: badgeP
                anchors.centerIn: parent
                text: root.badge("p", root.firstCoef ? root.number(root.firstCoef.p) : qsTr("sunulmuyor"))
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: Theme.small
                color: Theme.warning
            }
        }
        Rectangle {
            width: badgeVif.implicitWidth + Theme.md * 2
            height: badgeVif.implicitHeight + Theme.sm * 2
            radius: Theme.radius
            color: Theme.surface
            border.color: Theme.border
            UiLabel {
                id: badgeVif
                anchors.centerIn: parent
                text: {
                    let vif = (statistics.preflightResult && statistics.preflightResult.vif) || []
                    return root.badge("VIF", vif.length ? root.number(vif[0].value) : qsTr("sunulmuyor"))
                }
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: Theme.small
            }
        }
        Rectangle {
            width: badgeAic.implicitWidth + Theme.md * 2
            height: badgeAic.implicitHeight + Theme.sm * 2
            radius: Theme.radius
            color: Theme.surface
            border.color: Theme.border
            UiLabel {
                id: badgeAic
                anchors.centerIn: parent
                text: root.badge("AIC / BIC", (fit.aic !== undefined ? root.number(fit.aic) : qsTr("sunulmuyor")) + " / " + (fit.bic !== undefined ? root.number(fit.bic) : qsTr("sunulmuyor")))
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: Theme.small
            }
        }
    }
    UiLabel {
        visible: !root.hasModel
        text: qsTr("Sağdan model ve değişken seçin. Sonuç rozetleri yalnız gerçek fit alanlarından dolar; sayı uydurulmaz.")
        color: Theme.secondary
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
    }

    Rectangle {
        objectName: "modelLayerStrip"
        Layout.fillWidth: true
        implicitHeight: layerRow.implicitHeight + Theme.sm * 2
        radius: Theme.radius
        color: Theme.cyanSurface
        border.color: Theme.border
        RowLayout {
            id: layerRow
            anchors.fill: parent
            anchors.margins: Theme.sm
            spacing: Theme.md
            UiLabel {
                objectName: "modelTrainN"
                text: qsTr("Eğitim: n=") + root.trainN()
                Layout.fillWidth: true
                wrapMode: Text.Wrap
            }
            UiLabel {
                objectName: "modelTestN"
                text: qsTr("Test: n=") + root.testN()
                Layout.fillWidth: true
                wrapMode: Text.Wrap
            }
            UiLabel {
                objectName: "modelLeakageBadge"
                text: qsTr("Sızıntı: ") + root.leakageText()
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: (operations.modelLeakage && operations.modelLeakage.warning) ? Theme.warning : Theme.text
            }
        }
    }

    Frame {
        objectName: "modelCanvasFrame"
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 160
        padding: Theme.md
        background: Rectangle { color: Theme.raised; border.color: Theme.border; radius: Theme.radius }
        ColumnLayout {
            anchors.fill: parent
            spacing: Theme.sm
            UiLabel {
                objectName: "modelCanvasHint"
                visible: root.resultTab === 1 || !root.hasModel
                text: root.hasModel
                    ? ((result.method_label || result.spec.method || "") + qsTr(" · sürüm ") + (result.dataset_version || "").toString().slice(-8)
                       + "\n" + qsTr("Formül: ") + (result.formula || "")
                       + "\n" + qsTr("Uyum: ") + (fit.r_squared !== undefined ? ("R²=" + root.number(fit.r_squared)) : (fit.aic !== undefined ? ("AIC=" + root.number(fit.aic)) : qsTr("ayrıntı Katsayılar/Tanılama sekmelerinde"))))
                    : qsTr("Katsayı tablosu ve artık grafiği fit sonrası burada görünür. Eğitim katmanında fit; held-out skor bu ekranda üretilmez.")
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Theme.secondary
            }
            Flickable {
                visible: root.resultTab === 2 && root.hasModel
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentWidth: width
                contentHeight: coefCol.implicitHeight
                clip: true
                ColumnLayout {
                    id: coefCol
                    width: parent.width
                    Repeater {
                        model: root.coefficients
                        UiLabel {
                            required property var modelData
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                            text: modelData.term
                                  + " · β=" + root.number(modelData.estimate)
                                  + " · SE=" + root.number(modelData.se)
                                  + " · p=" + root.number(modelData.p)
                                  + " · CI [" + root.number(modelData.low) + ", " + root.number(modelData.high) + "]"
                        }
                    }
                }
            }
            UiLabel {
                visible: root.resultTab === 3 && root.hasModel
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: diagnostics.heteroskedasticity
                    ? (diagnostics.heteroskedasticity.p !== undefined
                       ? qsTr("Heteroskedastisite (Koenker BP) p=") + root.number(diagnostics.heteroskedasticity.p)
                       : qsTr("Heteroskedastisite: bu yöntemde sunulmuyor"))
                    : qsTr("Artık özeti fit sonrası tanılama alanından okunur; uydurma grafik yok.")
                color: Theme.secondary
            }
            Image {
                objectName: "modelDiagnosticImage"
                visible: (root.resultTab === 3 || root.resultTab === 4) && !!(statistics.modelDiagnostic)
                Layout.fillWidth: true
                Layout.fillHeight: true
                fillMode: Image.PreserveAspectFit
                source: statistics.modelDiagnostic || ""
                Accessible.name: qsTr("Model tanılama grafiği")
            }
            UiLabel {
                visible: root.resultTab === 4 && root.hasModel && !(statistics.modelDiagnostic)
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Theme.secondary
                text: qsTr("Tanılama görseli yok. VIF/önkontrol sağ panelden; Cook/QQ yöntem destekliyorsa fit sonrası gelir.")
            }
            UiLabel {
                objectName: "modelStaleWarning"
                visible: root.stale
                text: qsTr("Eski veri sürümü — yeniden eğitin")
                color: Theme.warning
                Layout.fillWidth: true
                wrapMode: Text.Wrap
            }
        }
    }

    StateNotice {
        Layout.fillWidth: true
        kind: statistics.errorText ? "error" : statistics.busy ? "loading" : "info"
        heading: qsTr("Model durumu")
        detail: statistics.errorText || statistics.message
    }

    UiLabel {
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.secondary
        font.pixelSize: Theme.small
        text: qsTr("Model yeni veri sürümü üretmez; kaynak dosya değişmez. Eğit ve kaydet sonucu analysis_store’a yazar.")
    }
}
