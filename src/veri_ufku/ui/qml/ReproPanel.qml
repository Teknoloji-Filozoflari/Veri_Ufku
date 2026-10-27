import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id:panel
    objectName:"reproPanel"
    signal helpRequested(var origin,string context)
    Layout.fillWidth:true
    UiCheckBox {id:expanded;objectName:"reproExpanded";text:"Lineage ve bilimsel yeniden üretim";Layout.fillWidth:true}
    ColumnLayout {visible:expanded.checked;Layout.fillWidth:true;spacing:Theme.sm
        UiLabel {text:"Kaynak → dataset → operation → analysis/model → report. Yalnız kaydedilmiş kimlikler bağlanır; eksik provenance tamamlanmış gibi sunulmaz. Önce projeyi kaydedin. Graph açmak hesap veya ağ başlatmaz.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiCombo {id:focus;objectName:"reproFocus";accessibleLabel:"Lineage rapor run veya dataset seçimi";model:reproducibility.targets;textRole:"label";valueRole:"id";Layout.fillWidth:true}
        UiCheckBox {id:includeData;objectName:"reproIncludeData";text:"Snapshot verisini bundle içine ayrıca ekle: ham/kişisel değer ve RowId içerebilir. İçeriği paylaşmadan önce incele.";Layout.fillWidth:true;enabled:!reproducibility.busy}
        UiButton {objectName:"reproInspect";text:"Lineage ve redaction önizlemesini oluştur";enabled:reproducibility.canAct&&focus.currentIndex>=0;onClicked:reproducibility.inspect(focus.currentValue,includeData.checked);Layout.fillWidth:true}
        UiLabel {objectName:"reproPreviewCaption";text:reproducibility.preview.schema?"Veri inclusion: "+reproducibility.preview.include_data+" · data bytes="+reproducibility.preview.estimated_data_bytes+" · re-run="+reproducibility.preview.rerun_supported+"\n"+reproducibility.preview.rerun_reason:"Önizleme henüz yok";wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiLabel {text:reproducibility.preview.storage?"Storage: "+reproducibility.preview.storage.artifact_usage_bytes+" / quota "+reproducibility.preview.storage.quota_bytes+" bytes. Snapshot immutable kopyadır; referans yalnız kimlik/URI/hash'tir. Retention: geçmiş artifact tutulur, otomatik silme yok. Archive disk boşaltmaz. Proje/bundle silmek kalıcı veri kaybı yaratabilir.":"";wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiLabel {text:"Dış secret/file path redaction önizlemesi (değerler gösterilmez):";font.bold:true;Layout.fillWidth:true}
        Repeater {model:(reproducibility.preview.redactions||[]).slice(0,100)
            UiLabel {required property var modelData;text:modelData.field+" · "+modelData.reason;wrapMode:Text.Wrap;Layout.fillWidth:true}
        }
        UiLabel {visible:(reproducibility.preview.redactions||[]).length>100;text:"İlk100 redaction gösteriliyor; tüm alan konumları bundle önizleme kaydında korunur.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiLabel {text:"Secret/path/free-text alanları temizlenir; config değişirse re-run destekli sayılmaz. Otomatik tarama evrensel secret dedektörü değildir; veri inclusion ayrı kullanıcı incelemesi ister. Aggregate sonuç ve params da hassas olabilir. Hash bütünlüğü kimlik doğrulama veya imza değildir.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiLabel {text:"Kayıtlı graph · oklar kaynak/girdi → sonuç; listeden düğüm seçerek hash/URI/schema/config/ortam ayrıntısını açın. Büyük graph yalnız seçili sonucun atalarını gösterir.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        Item {
            id:graphView
            Layout.fillWidth:true
            Layout.preferredHeight:Math.min(30,(reproducibility.graph.nodes||[]).length)*74
            Canvas {id:edges;anchors.fill:parent;onWidthChanged:requestPaint()
                Connections {target:reproducibility;function onChanged(){edges.requestPaint()}}
                onPaint:{
                    let ctx=getContext("2d");ctx.reset();ctx.lineWidth=2;ctx.strokeStyle=Theme.dataTone
                    let nodes=(reproducibility.graph.nodes||[]).slice(0,30)
                    for(let e of reproducibility.graph.edges||[]) {
                        let a=nodes.findIndex(n=>n.id===e.source),b=nodes.findIndex(n=>n.id===e.target);if(a<0||b<0)continue
                        let x=10+(a%6)*8,y1=a*74+28,y2=b*74+28
                        ctx.beginPath();ctx.moveTo(68,y1);ctx.lineTo(x,y1);ctx.lineTo(x,y2);ctx.lineTo(66,y2);ctx.stroke()
                        ctx.beginPath();ctx.moveTo(60,y2-4);ctx.lineTo(67,y2);ctx.lineTo(60,y2+4);ctx.stroke()
                    }
                }
            }
            Repeater {model:(reproducibility.graph.nodes||[]).slice(0,30)
                Rectangle {required property var modelData;required property int index;x:70;y:index*74;width:Math.max(100,graphView.width-78);height:60;color:Theme.surface;border.color:Theme.border;radius:Theme.radius
                    Column {anchors.fill:parent;anchors.margins:Theme.sm
                        UiLabel {text:modelData.kind+" · "+modelData.id.slice(-36);font.bold:true;elide:Text.ElideRight;width:parent.width}
                        UiLabel {text:modelData.metadata.status||(typeof modelData.metadata.version==="string"?modelData.metadata.version:"Kayıtlı bağ; detay için seçin");elide:Text.ElideRight;width:parent.width}
                    }
                }
            }
        }
        UiLabel {visible:(reproducibility.graph.nodes||[]).length>30;text:"Diagram30node görünüm bütçesi. Aşağıdaki listede tüm node/edge kimlikleri korunur; daha dar focus seçin.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiCombo {id:node;objectName:"reproNode";accessibleLabel:"Kayıtlı lineage düğümü";model:reproducibility.graph.nodes||[];textRole:"id";valueRole:"id";Layout.fillWidth:true}
        UiButton {objectName:"reproSelectNode";text:"Düğüm ayrıntısını göster";enabled:node.currentIndex>=0;onClicked:reproducibility.selectNode(node.currentValue);Layout.fillWidth:true}
        UiTextArea {objectName:"reproNodeDetails";Accessible.name:"Kayıtlı provenance ve eksik alanlar";visible:!!reproducibility.report.selected_node;readOnly:true;text:JSON.stringify(reproducibility.report.selected_node||{},null,2);textFormat:TextEdit.PlainText;wrapMode:TextEdit.Wrap;Layout.fillWidth:true;Layout.preferredHeight:240}
        UiLabel {visible:(reproducibility.graph.edges||[]).length>200;text:"İlk200 edge görünümü; tüm bağlantılar graph/bundle metadata içinde korunur. Daha dar focus seçin.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        Repeater {model:(reproducibility.graph.edges||[]).slice(0,200)
            UiLabel {required property var modelData;text:modelData.source+" → "+modelData.target+" · "+modelData.relation;wrapMode:Text.Wrap;Layout.fillWidth:true}
        }
        UiLabel {text:"RowId çok kaynak desteği: join/explode/aggregate ilişkisi yalnız kaydedilmiş lineage Parquet varsa vardır. Dataset-level bağ tek satır kökeni değildir. Genel row traversal/reconstruction mevcut değil; relation URI/hash gösterilir. Eski kayıtların hardware/code/decision alanları not_recorded kalır; bugünkü hardware geçmişe yazılmaz.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiTextField {id:destination;objectName:"reproDestination";Accessible.name:"Yeni repro bundle dosya yolu";placeholderText:"Yeni .vurepro dosya yolu";Layout.fillWidth:true}
        UiButton {objectName:"reproExport";text:"Önizlemedeki seçimle repro bundle oluştur";enabled:reproducibility.canAct&&!!reproducibility.preview.schema;onClicked:reproducibility.exportBundle(destination.text);Layout.fillWidth:true}
        UiLabel {text:"Bundle manifest/config/güvenli aggregate artifact/env lock/yöntem-yardım sürümü/erişim koşulu içerir. Varsayılan veri yok; referans kaynak bytes yedeği veya erişim izni değildir. Keyring/credential/env secret okunmaz. Arbitrary Python veya model object import edilmez.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiTextField {id:archive;objectName:"reproArchive";Accessible.name:"Açılacak yerel repro bundle";placeholderText:"Var olan .vurepro dosyası";Layout.fillWidth:true}
        UiButton {objectName:"reproOpen";text:"Bundle aç ve tüm hashleri doğrula (çalıştırmaz)";enabled:reproducibility.canAct;onClicked:reproducibility.openBundle(archive.text);Layout.fillWidth:true}
        UiLabel {objectName:"reproOpenCaption";text:reproducibility.openedBundle.status||"Bundle açılmadı";wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiCheckBox {id:projectAccess;objectName:"reproProjectAccess";text:"Re-run için açık projedeki snapshotlara salt okunur erişim ver (işaret yoksa included data gerekir)";Layout.fillWidth:true}
        UiCombo {id:mode;objectName:"reproMode";accessibleLabel:"Re-run exact veya tanımlı numeric tolerance";model:["exact","numeric"];Layout.fillWidth:true}
        UiLabel {text:"Verifier: Decimal80 profile ve counts/kimlik/null exact. Numeric yalnız bounded OLS Float64 coefficients/predictions rtol1e-9 + atol1e-12 (çıktı biriminde). Bu bilimsel eşdeğerlik garantisi değildir; conditioning/ölçek önemlidir. Backend/Python/code/platform lock değişirse migration varsayılmaz, safe failure. Seed tek başına yeniden üretim garantisi değildir. Diğer modeller/rapor layout'u için otomatik re-run mevcut değil.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiTextField {id:testDestination;objectName:"reproTestDestination";Accessible.name:"Yeni reference actual comparison test artifact dosyası";placeholderText:"Yeni .vureprotest dosyası";Layout.fillWidth:true}
        UiButton {objectName:"reproRerun";text:"Re-run ve reference/actual karşılaştırmasını açıkça başlat";enabled:reproducibility.canAct&&!!reproducibility.openedBundle.status;onClicked:reproducibility.rerun(projectAccess.checked,mode.currentText,testDestination.text);Layout.fillWidth:true}
        UiLabel {objectName:"reproResultCaption";text:reproducibility.report.comparison?reproducibility.report.comparison.status+" · fark="+reproducibility.report.comparison.difference_count:reproducibility.report.bundle_id||"Henüz karşılaştırma yok";wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiTextArea {objectName:"reproComparison";Accessible.name:"Karşılaştırma farkları ve tolerance policy";visible:!!reproducibility.report.comparison;readOnly:true;text:JSON.stringify(reproducibility.report.comparison||{},null,2);textFormat:TextEdit.PlainText;wrapMode:TextEdit.Wrap;Layout.fillWidth:true;Layout.preferredHeight:220}
        UiButton {objectName:"reproCancel";text:"Repro işlemini iptal et";visible:reproducibility.busy;onClicked:reproducibility.cancel();Layout.fillWidth:true}
        UiLabel {objectName:"reproStatusCaption";text:reproducibility.errorText||reproducibility.message;wrapMode:Text.Wrap;Layout.fillWidth:true}
        StateNotice {heading:"Lineage / repro durumu";detail:reproducibility.errorText||reproducibility.message;kind:reproducibility.errorText?"error":reproducibility.busy?"loading":"info";Layout.fillWidth:true}
        UiButton { visible: false;objectName:"reproHelp";text:"Lineage, snapshot, ortam ve tolerance öğren";helpContext:"repro.lineage";onClicked:panel.helpRequested(this,helpContext);Layout.fillWidth:true}
    }
}
