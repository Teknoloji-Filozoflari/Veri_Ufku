import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id:panel
    objectName:"codePanel"
    property string helpContext:"code.bridge"
    signal helpRequested(var origin,string context)
    Connections {target:codeBridge;function onSelectCode(){expanded.checked=true}}
    UiCheckBox {id:expanded;objectName:"codeExpanded";text:"Faz63 Python / SQL / notebook ve isteğe bağlı kod alanı";Layout.fillWidth:true}
    ColumnLayout {visible:expanded.checked;Layout.fillWidth:true;spacing:Theme.sm
        UiLabel {text:"GUI → kod: yalnız seçili dataset'in numeric measurement sütun profili. Önce Veri → sütun profili hesaplayın. Görünüm filtreleri/diğer analizler çevrilmez. Python aynı Decimal profil motorunu çağırır; SQLite SQL yalnız sonlu sayısal count/min/max/mean alt kümesidir (|value|≤2^53, mean toleranslı).";Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiCombo {id:format;objectName:"codeFormat";accessibleLabel:"Kod paketi formatı";model:["Python script ZIP","SQLite SQL + runner ZIP","Notebook + runner ZIP"];Layout.fillWidth:true}
        UiTextField {id:destination;objectName:"codeDestination";Accessible.name:"Proje dışı yeni kod ZIP dosyası mutlak yolu";placeholderText:"/yerel/yeni-kod.zip";Layout.fillWidth:true}
        UiButton {objectName:"codeExport";text:"Destekli GUI tarifini kod paketi olarak dışa aktar";enabled:codeBridge.canAct;onClicked:codeBridge.exportCode(["python","sql","notebook"][format.currentIndex],destination.text);Layout.fillWidth:true}
        UiLabel {text:"Paket ham veri, örnek satırlar, notebook çıktısı veya secret içermez. DatasetVersion/ColumnId/snapshot hash referansı ve exact environment lock taşır; yeniden çalıştırırken aynı yerel projeyi açıkça verin. Çıktı istatistikleri hassas olabilir. Notebook açmak çalıştırmak değildir; restart/run-all ve aynı ortam gerekir. Harici Jupyter opsiyonel; masaüstü buna bağımlı değil, managed Jupyter kernel bağlantısı mevcut değil.";Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiCheckBox {id:preview;objectName:"codePreviewToggle";text:"Üretilen okunabilir Python / SQL şablonunu göster";Layout.fillWidth:true}
        UiTextArea {objectName:"codeGeneratedPreview";Accessible.name:"Üretilen kod şablonu";visible:preview.checked;readOnly:true;text:format.currentIndex===1?codeBridge.sqlPreview:codeBridge.pythonPreview;textFormat:TextEdit.PlainText;wrapMode:TextEdit.Wrap;Layout.fillWidth:true;Layout.preferredHeight:220}
        UiCheckBox {id:enable;objectName:"codeEnable";text:"Serbest kod alanını etkinleştir: ayrı process güvenlik sınırı değildir; doğrulanmış OS sandbox yok. Kod aynı kullanıcı haklarıyla dosya/ağa erişebilir.";Layout.fillWidth:true}
        ColumnLayout {visible:enable.checked;Layout.fillWidth:true
            UiLabel {text:"Kod yalnız aşağıdaki Çalıştır eyleminde başlar. Her seferinde yeni süreç; kalıcı kernel/global state yok. Proje/kayıt açmak kod çalıştırmaz. Serbest Python'u kayıpsız GUI tarifine çevirmeyiz. Kod düzenlemesi hash/config revision'ı değiştirir; hash kaydı/çalıştırma geçmişi projeye eklenir. Hücre metni stdin pipe ile gider; geçici code dosyası yazılmaz. Hücre metni ve stdout/stderr yalnız oturumda; otomatik export/log/proje kaydı yok. Secret yazmayın; çıktı maskelemesi örüntü bazlıdır, tam secret dedektörü değildir.";Layout.fillWidth:true;wrapMode:Text.Wrap}
            UiTextArea {id:editor;objectName:"codeEditor";Accessible.name:"Kullanıcı Python hücresi16KiB";text:'print("Veri_Ufku: explicit local code action")\n';enabled:!codeBridge.busy;textFormat:TextEdit.PlainText;wrapMode:TextEdit.Wrap;onTextChanged:codeBridge.setCode(text);Layout.fillWidth:true;Layout.preferredHeight:180}
            UiTextField {id:timeout;objectName:"codeTimeout";Accessible.name:"Kod wall timeout saniye0–600 ve ComputeBudget sınırı";text:"10";Layout.fillWidth:true}
            UiLabel {objectName:"codeHashCaption";text:"Cell SHA256="+codeBridge.codeHash+" · revision="+codeBridge.codeRevision;Layout.fillWidth:true;wrapMode:Text.Wrap}
            UiLabel {objectName:"codeEnvironment";text:"Kernel environment: "+JSON.stringify(codeBridge.environmentInfo);Layout.fillWidth:true;wrapMode:Text.Wrap}
            UiLabel {text:"Resource bütçesi: ComputeBudget RAM/CPU/thread, wall timeout,64KiB toplam çıktı,16KiB cell, tek süreç. Geçici her dosya≤min(16MiB,disk bütçesi); parent disk/RSS denetimi best-effort. Kaçan descendant veya kullanıcı yetkisiyle başka yollar güvenli biçimde sınırlandırılmış sayılmaz. OS sandbox/cgroup garantisi yok.";Layout.fillWidth:true;wrapMode:Text.Wrap}
            UiButton {objectName:"codeSaveHash";text:"Yalnız hücre hash/revision kaydını sakla (çalıştırmaz)";enabled:codeBridge.canAct;onClicked:codeBridge.saveHash();Layout.fillWidth:true}
            UiButton {objectName:"codeRun";text:"Bu Python hücresini açıkça çalıştır";enabled:codeBridge.canAct&&enable.checked;onClicked:codeBridge.execute(enable.checked,Number(timeout.text));Layout.fillWidth:true}
            UiButton {objectName:"codeCancel";text:"Kod sürecini iptal et";visible:codeBridge.canCancel;onClicked:codeBridge.cancel();Layout.fillWidth:true}
            UiLabel {objectName:"codeRunCaption";text:codeBridge.report.status?codeBridge.report.status+" · output bytes="+codeBridge.report.output_bytes+" · exit="+codeBridge.report.exit_code:"Henüz code run yok";Layout.fillWidth:true;wrapMode:Text.Wrap}
            UiTextArea {objectName:"codeOutput";Accessible.name:"Geçici maskelenmiş stdout stderr64KiB";text:codeBridge.outputText;readOnly:true;textFormat:TextEdit.PlainText;wrapMode:TextEdit.Wrap;Layout.fillWidth:true;Layout.preferredHeight:160}
        }
        UiCombo {id:saved;objectName:"codeSaved";accessibleLabel:"Kalıcı hash-only code run";model:codeBridge.savedRuns;textRole:"label";valueRole:"id";Layout.fillWidth:true}
        UiButton {objectName:"codeOpenRecord";text:"Seçili hash kaydını aç (çalıştırmaz)";enabled:!codeBridge.busy&&saved.currentIndex>=0;onClicked:codeBridge.openRecord(saved.currentValue);Layout.fillWidth:true}
        StateNotice {heading:"Kod köprüsü durumu";detail:codeBridge.errorText||codeBridge.message;kind:codeBridge.errorText?"error":codeBridge.busy?"loading":"info";Layout.fillWidth:true}
        UiButton { visible: false;objectName:"codeHelp";text:"Bu ne işe yarar?";helpContext:"code.bridge";onClicked:panel.helpRequested(this,helpContext);Layout.fillWidth:true}
    }
}
