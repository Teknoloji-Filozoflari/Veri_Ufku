import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    signal helpRequested(var origin,string context)
    spacing: Theme.md
    UiCheckBox { id: expanded;objectName:"sharingExpanded";text:"Yerel review / paylaşım paketi";Layout.fillWidth:true }
    ColumnLayout {
        visible:expanded.checked;Layout.fillWidth:true
        UiLabel { text:"Yerel dosya aktarımı; otomatik yayınlama veya ekip sunucusu yok. Tek yazıcı kilidi korunur; ağ klasöründeki SQLite ortak çok kullanıcı veritabanı değildir. Full copy yalnız taranabilir mevcut mantıksal proje; opaque binary/model artifact varsa kapalıdır. Tam kopyanın native proje doğrulaması daha fazla RAM ister; varsayılan bütçe yetmezse önceki sonuç korunur. Ayarlar üzerinden daha yüksek bütçeyi açıkça seçin.";wrapMode:Text.WordWrap;Layout.fillWidth:true }
        UiButton { objectName:"sharingHelp";text:"Review, diff ve redaction yardımı";helpContext:"share.bundle";onClicked:helpRequested(this,"share.bundle") }
        UiCombo { id:mode;objectName:"sharingMode";accessibleLabel:"Paylaşım inclusion modu";model:["metadata-only","redacted-sample","full-copy"];Layout.fillWidth:true }
        UiButton { text:"Seçili mod tarifini yükle";onClicked:recipe.text=sharing.template(mode.currentText) }
        UiLabel { text:"Redacted örnek: version DatasetVersion, ilk1..1000satır; keep_numeric açık ColumnId listesi. Bütün metin/kategori ve seçilmeyen sayısallar maskelenir. SourceRecordId/RowId ve ColumnId korunur. sensitive_terms yalnız geçici taramada kullanılır, pakete yazılmaz. Bu örnek özgün dataset diye yeniden etiketlenmez.";wrapMode:Text.WordWrap;Layout.fillWidth:true }
        UiTextArea { id:recipe;objectName:"sharingRecipe";Accessible.name:"ShareSpec inclusion ve hassas terim JSON tarifi";property string helpContext:"share.bundle";text:sharing.template("metadata-only");textFormat:TextEdit.PlainText;wrapMode:Text.WrapAnywhere;Layout.fillWidth:true;Layout.preferredHeight:190 }
        Flow { Layout.fillWidth:true;spacing:Theme.sm
            UiButton { objectName:"sharingPreview";text:"Secret/PII ve inclusion önizlemesi";helpContext:"share.bundle";enabled:!sharing.busy;onClicked:{reviewed.checked=false;sharing.inspect(recipe.text)} }
            UiButton { objectName:"sharingCancel";text:"İptal";enabled:sharing.busy;onClicked:sharing.cancel() }
        }
        ScrollView { id:preview;Layout.fillWidth:true;Layout.preferredHeight:280;contentWidth:availableWidth
            UiLabel { objectName:"sharingPreviewText";width:preview.availableWidth;text:sharing.previewText;textFormat:Text.PlainText;wrapMode:Text.WrapAnywhere }
        }
        UiCheckBox { id:reviewed;objectName:"sharingReviewed";text:"Inclusion, tarama bulguları ve maskeleri inceledim";Layout.fillWidth:true }
        UiCheckBox { id:pii;objectName:"sharingPii";text:"Tam kopyada bildirilen PII değerlerini paylaşmayı açıkça seçiyorum (secret engeli kaldırılamaz)";Layout.fillWidth:true }
        UiTextField { id:destination;objectName:"sharingDestination";Accessible.name:"Yeni yerel paylaşım paket dosyası";placeholderText:"Proje dışında yeni /tam/yol/review.vushare";Layout.fillWidth:true }
        UiButton { objectName:"sharingExport";text:"İncelenen paketi yerel dosyaya aktar";enabled:!sharing.busy && reviewed.checked;onClicked:sharing.exportBundle(destination.text,reviewed.checked,pii.checked) }
        UiTextField { id:archive;objectName:"sharingArchive";Accessible.name:"Açılacak yerel review bundle";placeholderText:"/tam/yol/review.vushare";Layout.fillWidth:true }
        UiButton { objectName:"sharingOpen";text:"Paketi hash kontrolüyle incele";helpContext:"share.diff";enabled:!sharing.busy;onClicked:{reviewed.checked=false;sharing.openBundle(archive.text)} }
        UiTextField { id:right;objectName:"sharingRight";Accessible.name:"Diff için ikinci yerel paket";placeholderText:"İkinci /tam/yol/review.vushare";Layout.fillWidth:true }
        UiButton { objectName:"sharingDiff";text:"İki paketi karşılaştır (review-only)";enabled:!sharing.busy;onClicked:sharing.compareBundles(archive.text,right.text) }
        UiLabel { text:"Diff: schema, operation, params, run/metric ve learning notes. Keep-local / incoming-as-separate-fork / defer yalnız kayıtlı insan kararıdır; veri merge uygulamaz. Kimlik çakışmasında sessiz birleşme veya last-write-wins yok.";wrapMode:Text.WordWrap;Layout.fillWidth:true }
        UiCombo { id:target;objectName:"sharingTarget";accessibleLabel:"Yorumun özgün proje/entity/artifact bağlamı";model:sharing.reviewTargets;textRole:"label";valueRole:"id";Layout.fillWidth:true }
        UiTextField { id:author;objectName:"sharingAuthor";Accessible.name:"Yerel reviewer kullanıcı beyanı";text:"Yerel inceleyen";Layout.fillWidth:true }
        UiTextArea { id:note;objectName:"sharingNote";Accessible.name:"Artifact sürümüne bağlı review veya learning notu";property string helpContext:"share.review";textFormat:TextEdit.PlainText;wrapMode:Text.WrapAnywhere;Layout.fillWidth:true;Layout.preferredHeight:100 }
        UiCheckBox { id:c1;text:"Inclusion incelendi" }
        UiCheckBox { id:c2;text:"Secret/PII incelendi" }
        UiCheckBox { id:c3;text:"Şema incelendi" }
        UiCheckBox { id:c4;text:"Yöntem/varsayım incelendi" }
        UiCheckBox { id:c5;text:"Metrik/test protokolü incelendi" }
        UiCheckBox { id:c6;text:"Kimlik çakışmaları incelendi" }
        UiCombo { id:decision;objectName:"sharingDecision";accessibleLabel:"İnsan review kararı; merge eylemi değildir";model:["comment","keep-local","incoming-as-separate-fork","defer","learning-note"];Layout.fillWidth:true }
        UiButton { objectName:"sharingSaveReview";text:"Özgün hash bağlamına yerel yorum/checklist kaydet";helpContext:"share.review";enabled:!sharing.busy && !!target.currentValue;onClicked:sharing.saveReview(target.currentValue,author.text,note.text,JSON.stringify({"inclusion-reviewed":c1.checked,"secret-pii-reviewed":c2.checked,"schema-reviewed":c3.checked,"methods-assumptions-reviewed":c4.checked,"metrics-protocol-reviewed":c5.checked,"identity-conflicts-reviewed":c6.checked}),decision.currentText) }
        UiLabel { text:"Hedef son açılan pakettir; paket yoksa son yerel önizlemedir. Diff hedefi otomatik değiştirmez. Eski yorum yeni artifact'a taşınmaz; eski subject, hash ve metadata bağlamı korunur. Reviewer yerel beyanıdır, sunucu kimliği/rol doğrulaması değildir.";wrapMode:Text.WordWrap;Layout.fillWidth:true }
        UiTextField { id:restore;objectName:"sharingRestorePath";Accessible.name:"Tam kopya için var olmayan yeni yerel proje klasörü";placeholderText:"Yeni /tam/yol/inceleme-fork";Layout.fillWidth:true }
        UiButton { objectName:"sharingRestore";text:"Açılan tam kopyayı yeni ayrı proje olarak oluştur";enabled:!sharing.busy && reviewed.checked;onClicked:sharing.restoreCopy(archive.text,restore.text,reviewed.checked) }
        ScrollView { id:output;Layout.fillWidth:true;Layout.preferredHeight:360;contentWidth:availableWidth
            UiLabel { objectName:"sharingOutput";width:output.availableWidth;text:sharing.outputText+"\n\nYerel yorumlar\n"+sharing.commentsText;textFormat:Text.PlainText;wrapMode:Text.WrapAnywhere }
        }
        UiLabel { text:sharing.limitations;wrapMode:Text.WordWrap;Layout.fillWidth:true }
        UiLabel { objectName:"sharingError";text:sharing.errorText;color:Theme.warning;wrapMode:Text.WordWrap;Layout.fillWidth:true }
    }
}
