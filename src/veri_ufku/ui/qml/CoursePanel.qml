import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    required property var library
    signal articleRequested(string articleId, var origin)
    spacing: Theme.md
    UiLabel { text: "Ders yolları ve uygulama laboratuvarı"; font.pixelSize: Theme.subheading; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    UiLabel { text: "Okumak, önkoşulu tamamlamak veya sınav zorunlu değil. Laboratuvar ayrı sentetik projede açılır; kendi projen ve taslağın değişmez. Arama yukarıdaki ortak Öğren aramasını kullanır."; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    UiCombo { id: path; objectName: "lessonPath"; accessibleLabel: "Ders öğrenme yolu"; model: root.library.lessonPaths; textRole: "title"; valueRole: "id"; Layout.fillWidth: true; currentIndex: root.library.lessonPaths.findIndex(function(p){return p.id===root.library.lessonPath}); onActivated: root.library.setLessonPath(currentValue) }
    UiCheckBox { objectName: "lessonFavorites"; text: "Yalnız favori dersler"; checked: root.library.favoriteLessonsOnly; onToggled: root.library.setFavoriteLessonsOnly(checked) }
    Repeater {
        model: root.library.lessons
        delegate: UiButton { required property var modelData; objectName: "lesson-"+modelData.id; text: modelData.title; helpContext: "learn.lab.mean-median"; Layout.fillWidth: true; onClicked: root.library.openLesson(modelData.id) }
    }
    UiLabel { text: "Seçili ders: "+root.library.lesson.title+" · sürüm "+root.library.lesson.version; Layout.fillWidth: true; font.bold: true; wrapMode: Text.WordWrap }
    UiLabel { text: root.library.lesson.purpose+"\nVeri: "+root.library.lesson.data+"\nVarsayım: "+root.library.lesson.assumptions; Layout.fillWidth: true; wrapMode: Text.WordWrap; textFormat: Text.PlainText }
    UiLabel { text: "Önkoşul kavram haritası — öneri, kilit değil"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    Repeater { model: root.library.lessonPrerequisites; delegate: UiButton { required property var modelData; text: modelData.title+" → "+root.library.lesson.title; Layout.fillWidth: true; onClicked: root.library.openLesson(modelData.id) } }
    UiCheckBox { id: graph; text: "Tüm önkoşul bağlantılarını göster" }
    Repeater { model: graph.checked ? root.library.conceptEdges : []; delegate: UiButton { required property var modelData; text: modelData.label; Layout.fillWidth: true; onClicked: root.library.openLesson(modelData.target) } }
    UiButton { objectName: "lessonStart"; text: "Dersi ayrı örnek workspace içinde aç"; helpContext: "learn.lab.mean-median"; enabled: !learningLab.busy && !learningLab.starting; onClicked: learningLab.startLesson(root.library.lesson.id) }
    UiCheckBox { objectName: "lessonMarksEnabled"; text: "Okuma, favori ve ders ilerlemesini yalnız bu cihazda kaydet (isteğe bağlı)"; checked: root.library.marksEnabled; onToggled: root.library.setMarksEnabled(checked); Layout.fillWidth: true }
    UiButton { objectName: "lessonBookmark"; text: root.library.isBookmarked ? "Makale/ders favorisini kaldır" : "Makale/dersi favoriye ekle"; enabled: root.library.marksEnabled; onClicked: root.library.toggleBookmark() }
    UiButton { objectName: "lessonComplete"; text: "Dersin bu sürümünü tamamlandı işaretle"; enabled: root.library.marksEnabled; onClicked: root.library.completeLesson() }
    UiLabel { text: root.library.lessonProgressText; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    UiCombo { id: related; objectName: "lessonModuleArticle"; accessibleLabel: "Bu yolun modül makaleleri"; model: root.library.moduleArticles; textRole: "title"; valueRole: "id"; Layout.fillWidth: true }
    UiButton { text: "Seçili modülün makalesini oku"; enabled: !!related.currentValue; onClicked: root.articleRequested(related.currentValue, this) }
    UiLabel { text: "Modül kapsamı: makale bağlantıları otomatik denetlenir. Her modülün ayrı interaktif laboratuvarı olduğu iddia edilmez. Teknik referans review bağımsız eğitimci/bilimsel inceleme değildir."; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    UiLabel { text: learningLab.errorText; color: Theme.warning; Layout.fillWidth: true; wrapMode: Text.WordWrap }
}
