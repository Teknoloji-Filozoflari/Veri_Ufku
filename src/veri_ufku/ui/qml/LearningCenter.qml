import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "FocusScroll.js" as FocusScroll

ColumnLayout {
    id: center
    required property var library
    signal articleRequested(string articleId, var origin)
    spacing: Theme.lg
    UiLabel { text: "Verinin yolculuğunu öğren"; color: Theme.learningTone; font.pixelSize: Theme.subheading; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    UiLabel { text: "Veri Bilimi Yol Haritası aşamasını ve alt başlığını aç; konuyu seçerek oku. Arama sonuçları da ilgili başlığın altında görünür. İnternet gerekmez."; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.secondary }
    UiTextField {
        id: searchField
        objectName: "learningSearch"
        onActiveFocusChanged: if (activeFocus) Qt.callLater(function() { FocusScroll.reveal(searchField) })
        Layout.fillWidth: true
        font.pixelSize: Theme.body
        implicitHeight: Theme.controlHeight
        placeholderText: "Konu ara — örneğin medyan veya sızıntı"
        Accessible.name: "Çevrimdışı yardım araması"
        text: center.library.query
        maximumLength: 200
        onTextEdited: center.library.setQuery(text)
        background: Rectangle { color: Theme.surface; radius: Theme.radius; border.color: parent.activeFocus ? Theme.learningTone : Theme.border; border.width: parent.activeFocus ? 2 : 1 }
    }
    UiCombo { tone: "mint";
        objectName: "learningCategory"
        Layout.fillWidth: true
        model: center.library.categories
        currentIndex: center.library.categories.indexOf(center.library.category)
        Accessible.name: "Yardım kategorisi"
        onActivated: center.library.setCategory(center.library.categories[index])
    }
    UiCheckBox { objectName: "learningGlossary"; text: "Sözlük / kavramlar — uygulama rehberleri hariç"; checked: center.library.glossary; onToggled: center.library.setGlossary(checked); Layout.fillWidth: true }
    StateNotice { visible: center.library.errorText.length > 0; Layout.fillWidth: true; kind: "error"; heading: "Okuma tercihleri"; detail: center.library.errorText }
    UiLabel { text: center.library.results.length + " konu bulundu"; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.secondary }
    StateNotice { visible: center.library.results.length === 0; Layout.fillWidth: true; kind: "empty"; heading: "Konu bulunamadı"; detail: "Daha kısa bir sözcük dene veya kategori seçimini temizle." }
    LearningTrail {
        Layout.fillWidth: true
        library: center.library
        onArticleRequested: function(articleId, origin) { center.articleRequested(articleId, origin) }
    }
    Loader {
        Layout.fillWidth: true
        active: !center.library.sandbox
        sourceComponent: Component { CoursePanel { library: center.library; onArticleRequested: function(articleId, origin) { center.articleRequested(articleId, origin) } } }
    }
}
