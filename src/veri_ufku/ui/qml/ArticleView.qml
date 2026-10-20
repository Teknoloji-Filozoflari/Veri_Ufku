import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: articleView
    required property var library
    property bool allowTry: true
    property bool readingMode: false
    property bool sourcesExpanded: false
    Connections { target: articleView.library; function onArticleOpened() { articleView.sourcesExpanded = false } }
    spacing: Theme.lg
    UiLabel {
        objectName: "articleTitle"
        text: articleView.library.article.title
        textFormat: Text.PlainText
        font.pixelSize: Theme.subheading
        font.bold: true
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
    }
    UiLabel {
        text: qsTr("İçerik sürümü ") + articleView.library.article.content_version + " · Türkçe · Çevrimdışı"
        textFormat: Text.PlainText
        color: Theme.secondary
        font.pixelSize: Theme.small
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
    }
    UiCombo { tone: "mint";
        objectName: "articleDepthPicker"
        visible: !articleView.readingMode
        Layout.fillWidth: true
        model: ["Tek cümle", "Bir dakikalık örnek", "Ayrıntılı rehber"]
        Accessible.name: "Açıklama derinliği"
        currentIndex: articleView.library.depth
        onActivated: articleView.library.setDepth(index)
    }
    UiLabel {
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
        UiLabel {
            width: parent.width
            text: qsTr("! Dikkat: ") + articleView.library.article.critical
            textFormat: Text.PlainText
            color: Theme.warning
            font.pixelSize: Theme.body
            wrapMode: Text.WordWrap
        }
    }
    Repeater {
        model: !articleView.readingMode && articleView.library.depth >= 1 ? [
            {heading: "Önce — küçük örnek", detail: articleView.library.article.example.before},
            {heading: "Sonra — nasıl okuyalım?", detail: articleView.library.article.example.after},
            {heading: "Sonucu nasıl yorumlarım?", detail: articleView.library.article.interpretation}
        ] : []
        ColumnLayout {
            required property var modelData
            Layout.fillWidth: true
            spacing: Theme.sm
            UiLabel { text: modelData.heading; textFormat: Text.PlainText; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            UiLabel { text: modelData.detail; textFormat: Text.PlainText; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        }
    }
    Repeater {
        model: articleView.readingMode ? articleView.library.article.guide.map(function(block) { return {heading: block.heading || "Ayrıntılar", detail: block.text} }) : articleView.library.depth === 2 ? [
            {heading: qsTr("Ne işe yarar?"), detail: articleView.library.article.purpose},
            {heading: qsTr("Ne zaman kullanılır?"), detail: articleView.library.article.when},
            {heading: "Ne zaman uygun değildir?", detail: articleView.library.article.when_not},
            {heading: "Sık hata", detail: articleView.library.article.common_mistake}
        ].concat(articleView.library.article.guide.map(function(block) { return {heading: block.heading || "Biraz daha ayrıntı", detail: block.text} })) : []
        ColumnLayout {
            required property var modelData
            Layout.fillWidth: true
            spacing: Theme.sm
            UiLabel { text: modelData.heading; textFormat: Text.PlainText; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            UiLabel { text: modelData.detail; textFormat: Text.PlainText; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        }
    }
    UiLabel {
        visible: articleView.readingMode || articleView.library.depth === 2
        text: qsTr("İlgili ekran/işlem: ") + articleView.library.articleContexts
        textFormat: Text.PlainText
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.secondary
    }
    UiLabel { text: qsTr("İlgili kavramlar"); font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    Repeater {
        model: articleView.library.relatedArticles
        UiButton { tone: "mint";
            required property var modelData
            Layout.fillWidth: true
            objectName: "related-" + modelData.id
            text: modelData.title
            glyph: "→"
            multiline: true
            onClicked: articleView.library.openArticle(modelData.id)
        }
    }
    UiButton { tone: "mint";
        objectName: "tryLearningButton"
        visible: articleView.allowTry && !articleView.library.sandbox && articleView.library.article.try_action === "learn.example"
        Layout.fillWidth: true
        text: qsTr("Uygulamada dene")
        helpContext: "learn.example"
        glyph: "↗"
        multiline: true
        onClicked: articleView.library.tryExample()
    }
    UiLabel {
        visible: articleView.allowTry && !articleView.library.sandbox && articleView.library.article.try_action === "learn.example"
        text: qsTr("Aramayı ayrı, geçici örnek öğrenme projesinde dene. Dosyan ve mevcut işin değişmez.")
        textFormat: Text.PlainText
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.secondary
    }
    UiLabel { visible: articleView.library.marksEnabled; text: "Okundu işareti not, sınav veya beceri değerlendirmesi değildir."; Layout.fillWidth: true; wrapMode: Text.Wrap }
    Flow {
        Layout.fillWidth: true
        visible: articleView.library.marksEnabled && !articleView.library.sandbox
        spacing: Theme.sm
        UiButton { tone: "mint"; text: articleView.library.isRead ? "✓ Okundu — geri al" : "Okundu işaretle"; width: Math.min(implicitWidth, parent.width); multiline: true; onClicked: articleView.library.toggleRead() }
        UiButton { tone: "mint"; text: articleView.library.isBookmarked ? "★ Yer imini kaldır" : "☆ Yer imi ekle"; width: Math.min(implicitWidth, parent.width); multiline: true; onClicked: articleView.library.toggleBookmark() }
    }
    UiButton {
        objectName: "articleSourcesToggle"
        tone: "mint"
        Layout.fillWidth: true
        visible: articleView.readingMode || articleView.library.depth === 2
        text: articleView.sourcesExpanded ? "İçerik kaynaklarını gizle" : qsTr("İçerik kaynakları")
        glyph: articleView.sourcesExpanded ? "⌄" : "›"
        Accessible.description: articleView.sourcesExpanded ? "Kaynaklar açık" : "Kaynaklar kapalı; açmak için tıkla"
        onClicked: articleView.sourcesExpanded = !articleView.sourcesExpanded
    }
    Repeater {
        model: articleView.sourcesExpanded && (articleView.readingMode || articleView.library.depth === 2) ? articleView.library.article.sources : []
        UiLabel {
            required property var modelData
            required property int index
            objectName: "articleSource-" + index
            text: modelData.title + "\n" + modelData.reference + "\nİnceleme: " + modelData.reviewed
            textFormat: Text.PlainText
            color: Theme.secondary
            Layout.fillWidth: true
            wrapMode: Text.WrapAnywhere
        }
    }
}
