import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id:root
    signal helpRequested(var origin,string context)
    spacing:Theme.md
    UiCheckBox { id:expanded;objectName:"privacyExpanded";text:"PII, redaction ve retention";Layout.fillWidth:true }
    ColumnLayout {
        visible:expanded.checked;Layout.fillWidth:true
        UiLabel { text:"Tarama yalnız aday üretir. Her kolon için insan kararı kaydedin. Hash ve pseudonym anonimlik garantisi değildir; nadir kombinasyonlar ve dış veri yeniden tanımlayabilir. Kaynak, geçmiş snapshot, model ve rapor değişmez.";wrapMode:Text.WordWrap;Layout.fillWidth:true }
        UiButton { visible: false; objectName:"privacyHelp";text:"PII, şifreleme ve privacy budget yardımı";helpContext:"privacy.scan";onClicked:helpRequested(this,"privacy.scan") }
        UiCombo { id:dataset;objectName:"privacyDataset";accessibleLabel:"Taranacak dataset sürümü";model:privacy.datasets;textRole:"label";valueRole:"id";Layout.fillWidth:true }
        UiButton { objectName:"privacyScan";text:"Yerel PII adaylarını tara";enabled:!privacy.busy && !!dataset.currentValue;onClicked:privacy.scan(dataset.currentValue) }
        UiLabel { text:"JSON kuralları: classification pii/not-pii/uncertain; strategy mask/drop/pseudonym/keep. Keep yalnız gerekçeli not-pii kararıyla. Eksik kolonlar dışa aktarılmaz; iç satır kimlikleri export edilmez. Reviewer yerel beyandır, doğrulanmış kimlik değildir.";wrapMode:Text.WordWrap;Layout.fillWidth:true }
        UiButton { text:"Son taramadan maskeli karar taslağı";onClicked:{policy.text=privacy.template();human.checked=false} }
        UiTextArea { id:policy;objectName:"privacyPolicy";Accessible.name:"ColumnId PII insan kararları JSON";property string helpContext:"privacy.review";textFormat:TextEdit.PlainText;wrapMode:Text.WrapAnywhere;Layout.fillWidth:true;Layout.preferredHeight:210 }
        UiCheckBox { id:human;objectName:"privacyHuman";text:"Kolon kararlarını ve gerekçeyi kendim inceledim" }
        UiButton { objectName:"privacySave";text:"Sürüme bağlı insan kararlarını kaydet";enabled:!privacy.busy && human.checked;onClicked:privacy.savePolicy(policy.text,human.checked) }
        UiCombo { id:review;objectName:"privacyReview";accessibleLabel:"Kayıtlı PII review";model:privacy.saved;textRole:"label";valueRole:"id";Layout.fillWidth:true }
        UiButton { objectName:"privacyPreview";text:"Kayıtlı kararla redaction önizlemesi";enabled:!privacy.busy && !!review.currentValue;onClicked:{approved.checked=false;privacy.preview(review.currentValue)} }
        ScrollView { id:pv;Layout.fillWidth:true;Layout.preferredHeight:220;contentWidth:availableWidth
            UiLabel { width:pv.availableWidth;text:privacy.previewText;textFormat:Text.PlainText;wrapMode:Text.WrapAnywhere }
        }
        UiCheckBox { id:approved;objectName:"privacyApproved";text:"Aynı çıktı kapsamını, kolon kararlarını ve linkage riskini onaylıyorum" }
        UiCombo { id:format;objectName:"privacyFormat";accessibleLabel:"Redacted paket formatı";model:["zip","sealed"];Layout.fillWidth:true }
        UiTextField { id:destination;objectName:"privacyDestination";Accessible.name:"Yeni proje dışı redacted export dosyası";placeholderText:"/tam/yol/yeni.zip veya yeni.vupseal";Layout.fillWidth:true }
        UiTextField { id:keyref;objectName:"privacyKeyRef";Accessible.name:"Secret Service key referansı; key değeri değil";placeholderText:"Key referansı (anahtar değeri girmeyin)";Layout.fillWidth:true }
        UiCombo { id:purpose;accessibleLabel:"Oluşturulacak key amacı";model:["hmac","fernet"];Layout.fillWidth:true }
        UiButton { objectName:"privacyGenerateKey";text:"Secret Service içinde yeni key oluştur (üzerine yazmaz)";enabled:!privacy.busy;onClicked:privacy.generateKey(purpose.currentText,keyref.text) }
        UiButton { objectName:"privacyExport";text:"İncelenen redacted paketi yeni dosyaya yaz";enabled:!privacy.busy && approved.checked;onClicked:privacy.exportData(review.currentValue,destination.text,format.currentText,keyref.text,approved.checked) }
        UiTextField { id:sealed;objectName:"privacySealed";Accessible.name:"Yerel şifreli export dosyası";placeholderText:"/tam/yol/paket.vupseal";Layout.fillWidth:true }
        UiButton { objectName:"privacyInspect";text:"Şifreli paketi doğrula ve manifesti incele (extract etmez)";enabled:!privacy.busy;onClicked:privacy.inspectSealed(sealed.text,keyref.text) }
        UiLabel { text:"Canlı proje şifrelemesi desteklenmiyor. Optional cryptography + Secret Service yalnız küçük export paketini korur. Oturum/RAM/swap ve kaynak kopyaları kapsam dışıdır. Key kaybında otomatik recovery/escrow yok; kayıp key ile paket açılamaz. Key yedeği/Secret Service recovery işletim sistemi sorumluluğudur. Decryption Python API ile aynı key gerektirir; bu ekran plaintext extract yapmaz.";wrapMode:Text.WordWrap;Layout.fillWidth:true }
        UiTextField { id:days;objectName:"privacyDays";Accessible.name:"Manuel retention gün sayısı1..3650";text:"30";Layout.fillWidth:true }
        UiButton { objectName:"privacyRetention";text:"Retention politikasını yerel kaydet (otomatik silmez)";enabled:!privacy.busy;onClicked:privacy.retention(Number(days.text)) }
        UiButton { objectName:"privacyCleanupPreview";text:"Sahiplik işaretli eski privacy cache silme kapsamını göster";enabled:!privacy.busy;onClicked:{clean.checked=false;privacy.cleanupPreview(Number(days.text))} }
        UiCheckBox { id:clean;objectName:"privacyCleanupConfirmed";text:"Son silme kapsamını inceledim; yalnız listeli sahipsiz privacy scratch silinsin" }
        UiButton { objectName:"privacyCleanup";text:"Onaylanan scratch dosyalarını sil";enabled:!privacy.busy && clean.checked;onClicked:privacy.cleanup(clean.checked) }
        UiButton { objectName:"privacyCancel";text:"Çalışan veri taraması/export iptal";enabled:privacy.busy;onClicked:privacy.cancel() }
        ScrollView { id:out;Layout.fillWidth:true;Layout.preferredHeight:320;contentWidth:availableWidth
            UiLabel { objectName:"privacyOutput";width:out.availableWidth;text:privacy.outputText+"\n\nKaynak PII ilişkileri\n"+privacy.dependenciesText;textFormat:Text.PlainText;wrapMode:Text.WrapAnywhere }
        }
        UiLabel { text:privacy.limitations;wrapMode:Text.WordWrap;Layout.fillWidth:true }
        UiLabel { text:"Güven sınırları: veri import safe parser/hash/budget ile; kod yalnız açık çalıştırma ve ayrı process (OS sandbox değil); plugin otomatik kod yükleme yok; ağ kullanıcı başlatır. Bu panel pentest veya üçüncü taraf kod güvenlik garantisi değildir. DP unavailable: sensitivity/accountant yok.";wrapMode:Text.WordWrap;Layout.fillWidth:true }
        UiLabel { objectName:"privacyError";text:privacy.errorText;color:Theme.warning;wrapMode:Text.WordWrap;Layout.fillWidth:true }
    }
}
