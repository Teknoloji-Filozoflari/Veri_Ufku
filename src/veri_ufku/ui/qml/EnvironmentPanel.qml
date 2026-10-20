import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id:root
    signal helpRequested(var origin,string context)
    spacing:Theme.md
    UiCheckBox { id:expanded;objectName:"environmentExpanded";text:"Paket / bağımlılık / worker ortamı durumu";Layout.fillWidth:true }
    ColumnLayout {
        visible:expanded.checked;Layout.fillWidth:true
        UiLabel { text:"Core CPU kurulumu ve optional extras ayrı profillerdir. Sürüm eşleşmesi native backend/GPU çalışma kanıtı değildir. Uyumsuz stack'ler ayrı worker ortamı gerektirir; bu sürüm otomatik environment kurmaz veya tüm modelleri tek Python'a sığmış saymaz.";wrapMode:Text.WordWrap;Layout.fillWidth:true }
        UiButton { objectName:"environmentHelp";text:"Paket, environment ve rollback yardımı";helpContext:"environment.inspect";onClicked:helpRequested(this,"environment.inspect") }
        UiButton { objectName:"environmentRefresh";text:"Yerel core/extras, artifact backend, QML/plugin, driver ve cache durumunu oku";enabled:!environment.busy;onClicked:environment.refresh() }
        ScrollView { id:report;Layout.fillWidth:true;Layout.preferredHeight:320;contentWidth:availableWidth
            UiLabel { objectName:"environmentReport";width:report.availableWidth;text:environment.reportText;textFormat:Text.PlainText;wrapMode:Text.WrapAnywhere }
        }
        UiTextField { id:path;objectName:"environmentProfilePath";Accessible.name:"Environment export/import JSON yolu";placeholderText:"/tam/yol/environment.json";Layout.fillWidth:true }
        UiCheckBox { id:approved;objectName:"environmentApproved";text:"Görünen metadata kapsamını inceledim; seçili dosyada export/import karşılaştırmasını onaylıyorum";Layout.fillWidth:true }
        UiButton { objectName:"environmentExport";text:"Raporu yeni yerel dosyaya export et";enabled:!environment.busy && approved.checked;onClicked:environment.exportProfile(path.text,approved.checked) }
        UiButton { objectName:"environmentImport";text:"Seçili environment raporunu güvenli şemayla karşılaştır";enabled:!environment.busy && approved.checked;onClicked:environment.importProfile(path.text,approved.checked) }
        UiLabel { text:"Environment import yalnız metadata karşılaştırmasıdır; requirements/komut çalıştırmaz, Python değişmez. Ayrı worker env provisioning ve yerel wheelhouse/extra kurucusu bu GUI'de mevcut değildir. Model ağırlıkları yalnız ilgili modelin açık yerel dosya/klasör yoluyla ve kendi doğrulamasıyla kullanılır.";wrapMode:Text.WordWrap;Layout.fillWidth:true }
        UiTextField { id:cache;objectName:"environmentCachePath";Accessible.name:"İncelenecek kullanıcı seçimi düz model-cache klasörü";placeholderText:"Seçili yerel model klasörü (flat64dosya/64MiB)";Layout.fillWidth:true }
        UiButton { objectName:"environmentCache";text:"Seçili cache dosyalarını hash ile incele; yükleme/deserialize yok";enabled:!environment.busy && approved.checked;onClicked:environment.inspectCache(cache.text,approved.checked) }
        UiTextField { id:bundle;objectName:"environmentUpdatePath";Accessible.name:"Kullanıcının seçtiği yeni yerel Flatpak artifact";placeholderText:"/tam/yol/candidate.flatpak";Layout.fillWidth:true }
        UiTextField { id:expected;objectName:"environmentUpdateHash";Accessible.name:"Bağımsız güvenilen kaynaktan beklenen artifact SHA256";placeholderText:"Beklenen SHA256 (publisher signature yerine geçmez)";Layout.fillWidth:true }
        UiTextField { id:commit;objectName:"environmentCurrentCommit";Accessible.name:"Rollback için mevcut Flatpak commit";placeholderText:"Mevcut Flatpak commit64hex; host flatpak info --show-commit";Layout.fillWidth:true }
        UiButton { objectName:"environmentUpdatePlan";text:"Yerel artifact hash kontrolü ve rollback planı";enabled:!environment.busy && approved.checked;onClicked:environment.prepareUpdate(bundle.text,expected.text,commit.text,approved.checked) }
        UiLabel { text:"Bu panel güncellemeyi uygulamaz: host Flatpak işlemi kullanıcı seçimiyle yapılır. App commit rollback proje şema göçünü geri almaz. Önce kapalı projenin ayrı tam yedeğini saklayın; eski uygulama yeni şemayı açamayabilir. Tek .flatpak runtime/driver içermez; temiz makinede offline installer desteği ayrı ve doğrulanmamıştır.";wrapMode:Text.WordWrap;Layout.fillWidth:true }
        UiButton { objectName:"environmentCancel";text:"İptal";enabled:environment.busy;onClicked:environment.cancel() }
        ScrollView { id:out;Layout.fillWidth:true;Layout.preferredHeight:300;contentWidth:availableWidth
            UiLabel { objectName:"environmentOutput";width:out.availableWidth;text:environment.outputText;textFormat:Text.PlainText;wrapMode:Text.WrapAnywhere }
        }
        UiLabel { objectName:"environmentError";text:environment.errorText;color:Theme.warning;wrapMode:Text.WordWrap;Layout.fillWidth:true }
    }
}
