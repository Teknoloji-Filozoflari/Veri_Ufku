import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: example
    objectName: "learningExampleWindow"
    required property var library
    visible: false
    width: 900
    height: 700
    minimumWidth: 640
    minimumHeight: 480
    title: "Veri_Ufku · Örnek öğrenme projesi"
    color: Theme.background
    font.pixelSize: Theme.body
    palette.windowText: Theme.text
    palette.text: Theme.text
    palette.buttonText: Theme.text
    palette.base: Theme.field
    palette.highlight: Theme.learningTone
    palette.highlightedText: Theme.accentText
    Shortcut { sequence: "Escape"; onActivated: example.close() }
    ScrollView {
        anchors.fill: parent
        anchors.margins: Theme.xl
        contentWidth: availableWidth
        clip: true
        ColumnLayout {
            width: parent.width
            spacing: Theme.xl
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.md
                BrandMark { objectName: "exampleLogo"; Layout.preferredWidth: 36; Layout.preferredHeight: 36 }
                UiLabel { text: "Örnek öğrenme projesi · Geçici"; font.pixelSize: Theme.heading; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            }
            UiLabel { text: "Aşağıdaki arama yalnız bu geçici öğrenme örneğine aittir. Gerçek dosyan, oturumun ve işlerin değişmez. Dosyadan rapora kalıcı örnek proje için Başlangıç ekranındaki sentetik örnekleri kullanabilirsin."; textFormat: Text.PlainText; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            UiButton { objectName: "exampleCloseButton"; text: "Örneği kapat"; glyph: "×"; onClicked: example.close() }
            LearningCenter { Layout.fillWidth: true; library: example.library; onArticleRequested: function(articleId, origin) { example.library.openArticle(articleId) } }
            ArticleView { Layout.fillWidth: true; library: example.library; allowTry: false }
        }
    }
}
