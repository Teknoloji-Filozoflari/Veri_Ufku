import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "FocusScroll.js" as FocusScroll

ColumnLayout {
    id: center
    required property var library
    signal articleRequested(string articleId, var origin)
    spacing: Theme.lg
    Label { text: "Merak ettiğin konuyu bul"; font.pixelSize: Theme.subheading; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    Label { text: "İnternet gerekmez. Sözlükte temel kavramları, kategorilerde ilgili konuları bulabilirsin."; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.secondary }
    TextField {
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
        background: Rectangle { color: Theme.surface; radius: Theme.radius; border.color: parent.activeFocus ? Theme.accent : Theme.border; border.width: parent.activeFocus ? 2 : 1 }
    }
    UiCombo {
        objectName: "learningCategory"
        Layout.fillWidth: true
        model: center.library.categories
        currentIndex: center.library.categories.indexOf(center.library.category)
        Accessible.name: "Yardım kategorisi"
        onActivated: center.library.setCategory(center.library.categories[index])
    }
    Flow {
        Layout.fillWidth: true
        spacing: Theme.sm
        UiButton { objectName: "glossaryButton"; width: Math.min(implicitWidth, parent.width); multiline: true; text: center.library.glossary ? "✓ Sözlük — temel kavramlar" : "Sözlük — temel kavramlar"; checked: center.library.glossary; onClicked: center.library.setGlossary(!center.library.glossary) }
        UiButton { width: Math.min(implicitWidth, parent.width); multiline: true; text: "Aramayı temizle"; onClicked: { center.library.setQuery(""); center.library.setCategory("Tümü"); center.library.setGlossary(false) } }
    }
    UiButton {
        objectName: "readingMarksButton"
        visible: !center.library.sandbox
        Layout.fillWidth: true
        multiline: true
        checked: center.library.marksEnabled
        text: center.library.marksEnabled ? "✓ Yerel okundu / yer imi kaydı açık — kapat ve temizle" : "İsteğe bağlı yerel okundu / yer imi kaydını aç"
        onClicked: center.library.setMarksEnabled(!center.library.marksEnabled)
    }
    StateNotice { visible: center.library.errorText.length > 0; Layout.fillWidth: true; kind: "error"; heading: "Okuma tercihleri"; detail: center.library.errorText }
    Label { text: center.library.results.length + " konu bulundu"; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.secondary }
    StateNotice { visible: center.library.results.length === 0; Layout.fillWidth: true; kind: "empty"; heading: "Konu bulunamadı"; detail: "Daha kısa bir sözcük dene veya kategori seçimini temizle." }
    Repeater {
        model: center.library.results
        Frame {
            required property var modelData
            Layout.fillWidth: true
            padding: Theme.md
            background: Rectangle { color: Theme.surface; border.color: Theme.border; radius: Theme.radius }
            ColumnLayout {
                width: parent.width
                spacing: Theme.sm
                UiButton { objectName: "learningArticle-" + modelData.id; Layout.fillWidth: true; text: modelData.title; glyph: "→"; multiline: true; onClicked: center.articleRequested(modelData.id, this) }
                Label { text: modelData.summary; textFormat: Text.PlainText; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                Label { text: modelData.category + (center.library.marksEnabled && modelData.read ? " · ✓ Okundu" : "") + (center.library.marksEnabled && modelData.bookmarked ? " · ★ Yer imi" : ""); textFormat: Text.PlainText; color: Theme.secondary; font.pixelSize: Theme.small; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            }
        }
    }
}
