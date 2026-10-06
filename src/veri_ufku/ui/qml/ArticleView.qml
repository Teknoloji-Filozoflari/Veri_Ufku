import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: articleView
    required property var library
    property bool allowTry: true
    spacing: Theme.lg
    Label {
        objectName: "articleTitle"
        text: articleView.library.article.title
        textFormat: Text.PlainText
        font.pixelSize: Theme.subheading
        font.bold: true
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
    }
    Label {
        text: "İçerik sürümü " + articleView.library.article.content_version + " · Türkçe · Çevrimdışı"
        textFormat: Text.PlainText
        color: Theme.secondary
        font.pixelSize: Theme.small
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
    }
    UiCombo {
        objectName: "articleDepthPicker"
        Layout.fillWidth: true
        model: ["Tek cümle", "Bir dakikalık örnek", "Ayrıntılı rehber"]
        Accessible.name: "Açıklama derinliği"
        currentIndex: articleView.library.depth
        onActivated: articleView.library.setDepth(index)
    }
    Label {
        objectName: "articleSummary"
        text: articleView.library.article.summary
        textFormat: Text.PlainText
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
    }
    Frame {
        objectName: "criticalWarning"
        Layout.fillWidth: true
        padding: Theme.md
        background: Rectangle { color: Theme.warningSurface; border.color: Theme.warning; radius: Theme.radius }
        Label {
            width: parent.width
            text: "! Dikkat: " + articleView.library.article.critical
            textFormat: Text.PlainText
            color: Theme.warning
            font.pixelSize: Theme.body
            wrapMode: Text.WordWrap
        }
    }
    Repeater {
        model: articleView.library.depth >= 1 ? [
            {heading: "Önce — küçük örnek", detail: articleView.library.article.example.before},
            {heading: "Sonra — nasıl okuyalım?", detail: articleView.library.article.example.after},
            {heading: "Sonucu nasıl yorumlarım?", detail: articleView.library.article.interpretation}
        ] : []
        ColumnLayout {
            required property var modelData
            Layout.fillWidth: true
            spacing: Theme.sm
            Label { text: modelData.heading; textFormat: Text.PlainText; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            Label { text: modelData.detail; textFormat: Text.PlainText; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        }
    }
    Repeater {
        model: articleView.library.depth === 2 ? [
            {heading: "Ne işe yarar?", detail: articleView.library.article.purpose},
            {heading: "Ne zaman kullanılır?", detail: articleView.library.article.when},
            {heading: "Ne zaman uygun değildir?", detail: articleView.library.article.when_not},
            {heading: "Sık hata", detail: articleView.library.article.common_mistake}
        ].concat(articleView.library.article.guide.map(function(block) { return {heading: "Biraz daha ayrıntı", detail: block.text} })) : []
        ColumnLayout {
            required property var modelData
            Layout.fillWidth: true
            spacing: Theme.sm
            Label { text: modelData.heading; textFormat: Text.PlainText; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            Label { text: modelData.detail; textFormat: Text.PlainText; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        }
    }
    Label {
        visible: articleView.library.depth === 2
        text: "İlgili ekran/işlem: " + articleView.library.articleContexts
        textFormat: Text.PlainText
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.secondary
    }
    Label { text: "İlgili kavramlar"; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    Repeater {
        model: articleView.library.relatedArticles
        UiButton {
            required property var modelData
            Layout.fillWidth: true
            objectName: "related-" + modelData.id
            text: modelData.title
            glyph: "→"
            multiline: true
            onClicked: articleView.library.openArticle(modelData.id)
        }
    }
    UiButton {
        objectName: "tryLearningButton"
        visible: articleView.allowTry && !articleView.library.sandbox && articleView.library.article.try_action === "learn.example"
        Layout.fillWidth: true
        text: "Uygulamada dene"
        helpContext: "learn.example"
        glyph: "↗"
        multiline: true
        onClicked: articleView.library.tryExample()
    }
    Label {
        visible: articleView.allowTry && !articleView.library.sandbox && articleView.library.article.try_action === "learn.example"
        text: "Aramayı ayrı, geçici örnek öğrenme projesinde dene. Dosyan ve mevcut işin değişmez."
        textFormat: Text.PlainText
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.secondary
    }
    Flow {
        Layout.fillWidth: true
        visible: articleView.library.marksEnabled && !articleView.library.sandbox
        spacing: Theme.sm
        UiButton { text: articleView.library.isRead ? "✓ Okundu — geri al" : "Okundu işaretle"; width: Math.min(implicitWidth, parent.width); multiline: true; onClicked: articleView.library.toggleRead() }
        UiButton { text: articleView.library.isBookmarked ? "★ Yer imini kaldır" : "☆ Yer imi ekle"; width: Math.min(implicitWidth, parent.width); multiline: true; onClicked: articleView.library.toggleBookmark() }
    }
    Label { text: "İçerik kaynakları"; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap; visible: articleView.library.depth === 2 }
    Repeater {
        model: articleView.library.depth === 2 ? articleView.library.article.sources : []
        Label {
            required property var modelData
            text: modelData.title + "\n" + modelData.reference + "\nİnceleme: " + modelData.reviewed
            textFormat: Text.PlainText
            color: Theme.secondary
            Layout.fillWidth: true
            wrapMode: Text.WrapAnywhere
        }
    }
}
