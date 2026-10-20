import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: labWindow
    objectName: "learningLabWindow"
    required property var library
    required property var lab
    signal articleRequested(string articleId, var origin)
    visible: false
    width: 1000; height: 800; minimumWidth: 640; minimumHeight: 480
    title: "Veri_Ufku · Ayrı sentetik öğrenme laboratuvarı"
    color: Theme.background
    font.pixelSize: Theme.body
    palette.windowText: Theme.text
    palette.text: Theme.text
    palette.buttonText: Theme.text
    palette.base: Theme.field
    palette.highlight: Theme.learningTone
    palette.highlightedText: Theme.accentText
    property string selectedLesson: ""
    onClosing: lab.closeView()
    Shortcut { sequence: "Escape"; onActivated: labWindow.close() }
    Connections { target: library; function onChanged() { if(labWindow.selectedLesson!==library.lesson.id){labWindow.selectedLesson=library.lesson.id;slider.value=library.lesson.control.default} } }
    ScrollView {
        id: scroll
        anchors.fill: parent; anchors.margins: Theme.xl
        contentWidth: availableWidth
        ColumnLayout {
            width: scroll.availableWidth; spacing: Theme.md
            UiLabel { objectName: "lessonTitle"; text: library.lesson.title; font.pixelSize: Theme.heading; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            UiLabel { text: "AYRI SENTETİK WORKSPACE · "+lab.workspaceId+"\nKullanıcı projesi/taslağı değişmez. Oturum sonu bu geçici workspace silinir; ilerleme kaydı ayrı isteğe bağlıdır."; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
            Repeater {
                model: [{name:"Amaç",text:library.lesson.purpose},{name:"Veri",text:library.lesson.data},{name:"Problem",text:library.lesson.problem},{name:"Varsayım",text:library.lesson.assumptions},{name:"Günlük örnek",text:library.lesson.daily_example}]
                delegate: UiLabel { required property var modelData; text: modelData.name+": "+modelData.text; Layout.fillWidth: true; wrapMode: Text.WordWrap; textFormat: Text.PlainText }
            }
            Repeater { model: library.lesson.steps; delegate: UiLabel { required property string modelData; required property int index; text: (index+1)+". "+modelData; Layout.fillWidth: true; wrapMode: Text.WordWrap } }
            UiLabel { text: library.lesson.control.label+": "+Math.round(slider.value); Layout.fillWidth: true; wrapMode: Text.WordWrap }
            Slider { id: slider; objectName: "lessonSlider"; Layout.fillWidth: true; from: library.lesson.control.minimum; to: library.lesson.control.maximum; stepSize: library.lesson.control.step; snapMode: Slider.SnapAlways; value: library.lesson.control.default; Accessible.name: "Kontrollü ders parametresi" }
            UiSpinBox { id: seed; objectName: "lessonSeed"; Accessible.name: "Sentetik veri seed"; from: 0; to: 1000000; value: 42 }
            UiButton { objectName: "lessonCalculate"; text: "Ayrı örnekte gerçek hesabı çalıştır"; helpContext: "learn.lab.ci"; enabled: !lab.busy && !lab.starting; onClicked: lab.calculateLesson(Math.round(slider.value),seed.value) }
            UiButton { objectName: "lessonCancel"; text: "Hesabı iptal et"; enabled: lab.busy; onClicked: lab.cancel() }
            UiLabel { objectName: "lessonLabError"; text: lab.errorText; color: Theme.warning; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            UiLabel { text: "Beklenen davranış: "+library.lesson.expected+"\nYanlış yorum: "+library.lesson.misinterpretation+"\nKendi verime nasıl uygularım: "+library.lesson.own_data; Layout.fillWidth: true; wrapMode: Text.WordWrap; textFormat: Text.PlainText }
            UiLabel { objectName: "lessonStale"; text: lab.report.spec && (lab.report.spec.lesson!==library.lesson.id || lab.report.spec.value!==Math.round(slider.value) || lab.report.spec.seed!==seed.value) ? "Ayar/ders değişti: aşağıdaki sonuç önceki ayara ait; yeniden Hesapla." : ""; Layout.fillWidth: true; color: Theme.warning; wrapMode: Text.WordWrap }
            UiLabel { objectName: "lessonMetrics"; text: lab.report.metrics ? "Gerçek sonuç · "+lab.report.spec.lesson+" · seed="+lab.report.spec.seed+" · ayar="+lab.report.spec.value+"\n"+JSON.stringify(lab.report.metrics,null,2) : "Henüz hesaplanmadı; görsel sayı uydurulmaz."; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere; textFormat: Text.PlainText }
            LabPlot { Layout.fillWidth: true; curves: lab.report.curves || [] }
            UiLabel { text: lab.report.details ? "Hesap/split ayrıntısı: "+JSON.stringify(lab.report.details)+"\n"+JSON.stringify(lab.report.split) : ""; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere; textFormat: Text.PlainText }
            UiCheckBox { id: advanced; text: "İleri açıklama, denklem ve review kaydı" }
            UiLabel { visible: advanced.checked; text: library.lesson.equation+"\nDers sürümü="+library.lesson.version+" · Makale="+library.lesson.article_id+"\n"+JSON.stringify(library.lesson.review)+"\nKaynaklar bağlı makalenin Kaynaklar bölümündedir."; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere; textFormat: Text.PlainText }
            UiButton { text: "Bağlı makaleyi Öğren içinde aç"; onClicked: labWindow.articleRequested(library.lesson.article_id, this) }
            UiCheckBox { id: selfCheck; objectName: "lessonSelfCheck"; text: "İsteğe bağlı self-check — sınav/sertifika değil" }
            UiLabel { visible: selfCheck.checked; text: library.lesson.check.question; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            Repeater { model: selfCheck.checked ? library.lesson.check.options : []; delegate: UiButton { required property string modelData; required property int index; objectName: "lessonAnswer-"+index; text: modelData; Layout.fillWidth: true; onClicked: library.answerLesson(index) } }
            UiLabel { objectName: "lessonFeedback"; text: library.lessonFeedback; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            UiButton { objectName: "lessonWindowComplete"; text: "Bu ders sürümünü tamamlandı işaretle (isteğe bağlı)"; enabled: library.marksEnabled; onClicked: library.completeLesson() }
            UiLabel { text: library.lessonProgressText; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            UiCombo { id: saved; objectName: "lessonSaved"; accessibleLabel: "Geçici workspace kayıtlı hesapları"; model: lab.saved; textRole: "label"; valueRole: "id"; Layout.fillWidth: true }
            UiButton { objectName: "lessonReopen"; text: "Kayıtlı hesabı hash kontrolüyle aç"; enabled: !lab.busy && !!saved.currentValue; onClicked: lab.openReport(saved.currentValue) }
            UiButton { objectName: "lessonClose"; text: "Okumayı kapat ve işime dön"; onClicked: labWindow.close() }
        }
    }
}
