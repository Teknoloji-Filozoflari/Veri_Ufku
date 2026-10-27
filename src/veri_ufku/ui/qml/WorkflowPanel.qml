import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: panel
    objectName: "workflowPanel"
    signal helpRequested(var origin, string context)
    function summary(n) {
        if(n.error)return n.error
        let r=(n.value||{}).report||{}
        if(n.kind==="source")return "Kaynak: "+(r.row_count===undefined?"planlandı":r.row_count+" satır")
        if(n.kind==="transform"&&r.impact)return "Satır: "+r.impact.before_rows+" → "+r.impact.after_rows+" · değişen kolon: "+r.impact.changed_columns
        if(n.kind==="quality"&&r.null_count!==undefined)return "Eksik değer: "+r.null_count+" · bulgu: "+(r.findings||[]).length
        if(n.kind==="analysis"&&r.numeric)return "n="+r.used_n+" · ortalama="+r.numeric.mean+" · std="+(r.numeric.std===null?"tanımsız":Number(r.numeric.std).toPrecision(5))+" · ddof="+r.numeric.ddof
        if(n.kind==="train"&&r.fit_row_ids)return "OLS fit n="+r.fit_row_ids.length+" · tüm upstream satırlar; held-out başarı skoru değil"
        if(n.kind==="predict"&&r.predicted_n!==undefined)return "Tahmin: "+r.predicted_n+" satır · satır kimlikleri korundu"
        if(n.kind==="export"&&r.rows!==undefined)return "Parquet: "+r.rows+" satır · doğrulanan="+r.verified_rows+" · mevcut dosya ezilmez"
        return "Bağımlılık ve kaynak doğrulaması çalıştırmada yapılır."
    }
    Layout.fillWidth: true
    UiCheckBox {id: expanded;objectName:"workflowExpanded";text:"Typed DAG · dallanan işlem akışı";Layout.fillWidth:true}
    ColumnLayout {
        visible: expanded.checked
        Layout.fillWidth: true
        spacing: Theme.sm
        UiLabel {text:"Source → transform / quality → analysis / train → predict → export. Veri portu dataset, model portu model taşır; cycle ve uyumsuz bağlantı reddedilir. Düğümler mevcut OperationSpec/RowId/provenance/ComputeBudget sözleşmesini kullanır. Kaynaklara yazma kapalıdır.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        Flow {Layout.fillWidth:true;spacing:Theme.sm
            UiButton {objectName:"workflowReset";text:"Seçili snapshot ile yeni DAG";enabled:workflowRunner.canAct;onClicked:workflowRunner.reset()}
            UiButton {objectName:"workflowChain";text:"Mevcut zinciri DAG'a al";enabled:workflowRunner.canAct;onClicked:workflowRunner.fromChain()}
        }
        UiLabel {text:"Typed bağlantılar · kartlar hesap sonucu değildir. Bağımsız dallar ayrı durum taşır.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        Item {
            id: diagram
            Layout.fillWidth: true
            Layout.preferredHeight: workflowRunner.nodes.length * 84
            Canvas {
                id: wires
                anchors.fill: parent
                onWidthChanged: requestPaint()
                Connections {target:workflowRunner;function onChanged(){wires.requestPaint()}}
                onPaint: {
                    let ctx=getContext("2d");ctx.reset();ctx.lineWidth=2
                    let nodes=workflowRunner.nodes
                    for(let i=0;i<nodes.length;i++) {
                        let edges=Object.values(nodes[i].inputs).map(e=>({id:e.node,control:false})).concat(nodes[i].after.map(p=>({id:p,control:true})))
                        for(let e of edges) {
                            let j=nodes.findIndex(n=>n.id===e.id);if(j<0)continue
                            let x=12+(i%5)*8,y1=j*84+34,y2=i*84+34
                            ctx.strokeStyle=e.control?Theme.muted:Theme.dataTone
                            ctx.setLineDash(e.control?[4,4]:[])
                            ctx.beginPath();ctx.moveTo(72,y1);ctx.lineTo(x,y1);ctx.lineTo(x,y2);ctx.lineTo(68,y2);ctx.stroke()
                            ctx.setLineDash([]);ctx.beginPath();ctx.moveTo(62,y2-4);ctx.lineTo(69,y2);ctx.lineTo(62,y2+4);ctx.stroke()
                        }
                    }
                }
            }
            Repeater {model:workflowRunner.nodes
                Rectangle {required property var modelData;required property int index;x:72;y:index*84;width:Math.max(80,diagram.width-80);height:68;color:Theme.surface;border.color:Theme.border;radius:Theme.radius
                    Column {anchors.fill:parent;anchors.margins:Theme.sm
                        UiLabel {text:modelData.id+" · "+modelData.kind;font.bold:true}
                        UiLabel {text:modelData.kind==="train"?"model →":modelData.kind==="analysis"?"report →":modelData.kind==="export"?"receipt →":"dataset →";color:Theme.dataTone}
                    }
                }
            }
        }
        UiLabel {text:"Oklar veri/model bağımlılığını; kesikli çizgi after kontrol bağımlılığını gösterir. Kart metni ve aşağıdaki port listesi aynı grafiği sunar.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        Repeater {model:workflowRunner.nodes
            Frame {id: card;required property var modelData;Layout.fillWidth:true
                ColumnLayout {width:parent.width
                    UiLabel {text:card.modelData.id+" · "+card.modelData.kind+" · v"+card.modelData.method_version;font.bold:true;Layout.fillWidth:true}
                    UiLabel {text:"Giriş portları: "+JSON.stringify(card.modelData.inputs)+" · after: "+JSON.stringify(card.modelData.after);wrapMode:Text.Wrap;Layout.fillWidth:true}
                    UiLabel {text:JSON.stringify(card.modelData.params);wrapMode:Text.Wrap;Layout.fillWidth:true}
                    UiButton {text:"Düğümü kaldır";enabled:!workflowRunner.busy;onClicked:workflowRunner.removeNode(card.modelData.id)}
                }
            }
        }
        UiCombo {id:kind;objectName:"workflowKind";accessibleLabel:"Yeni DAG düğüm türü";model:["analysis","transform","quality","train","predict","export","source"];Layout.fillWidth:true}
        UiTextField {id:ident;objectName:"workflowNodeId";Accessible.name:"Düğüm kimliği";placeholderText:"Düğüm kimliği: summary";text:"summary";Layout.fillWidth:true}
        UiTextField {id:upstream;objectName:"workflowUpstream";Accessible.name:"Dataset giriş düğümü";text:"source";placeholderText:"data portunun kaynak node kimliği";Layout.fillWidth:true}
        UiTextField {id:modelNode;objectName:"workflowModelNode";Accessible.name:"Model giriş düğümü";visible:kind.currentText==="predict";text:"fit";Layout.fillWidth:true}
        UiCombo {id:column;objectName:"workflowColumn";accessibleLabel:"DAG özellik veya analiz kolonu";model:dataView.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true}
        UiCombo {id:target;objectName:"workflowTarget";accessibleLabel:"OLS hedef kolonu";visible:kind.currentText==="train";model:dataView.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true}
        UiTextField {id:value;objectName:"workflowValue";Accessible.name:"Yeni kolon adı veya source DatasetVersion kimliği";visible:kind.currentText==="transform"||kind.currentText==="source";placeholderText:"Rename yeni adı / source dv:UUID";Layout.fillWidth:true}
        UiCheckBox {id:confirmed;objectName:"workflowConfirm";text:kind.currentText==="train"?"OLS ölçüm/bağımsız satır/varsayımlarını değerlendirdim. Tüm upstream satırlarda fit; held-out başarı skoru değildir.":"Null varsa quality dalını durdur (işaret yoksa raporla ve devam et)";visible:kind.currentText==="train"||kind.currentText==="quality";Layout.fillWidth:true}
        UiButton {objectName:"workflowAdd";text:"Typed düğümü ekle";enabled:workflowRunner.canAct&&workflowRunner.nodes.length>0;onClicked:workflowRunner.addNode(kind.currentText,ident.text,upstream.text,modelNode.text,column.currentValue||"",target.currentValue||"",value.text,confirmed.checked);Layout.fillWidth:true}
        UiTextField {id:edgeTarget;objectName:"workflowEdgeTarget";Accessible.name:"Bağlantı hedef düğüm kimliği";placeholderText:"Hedef düğüm kimliği";Layout.fillWidth:true}
        UiCombo {id:inPort;objectName:"workflowInputPort";accessibleLabel:"Hedef giriş portu";model:["data","model"];Layout.fillWidth:true}
        UiTextField {id:edgeSource;objectName:"workflowEdgeSource";Accessible.name:"Bağlantı kaynak düğüm kimliği";text:"source";Layout.fillWidth:true}
        UiCombo {id:outPort;objectName:"workflowOutputPort";accessibleLabel:"Kaynak çıkış portu";model:["data","model","report","receipt"];Layout.fillWidth:true}
        UiButton {objectName:"workflowConnect";text:"Portları bağla / mevcut girişi değiştir";enabled:workflowRunner.canAct;onClicked:workflowRunner.connectPorts(edgeTarget.text,inPort.currentText,edgeSource.text,outPort.currentText);Layout.fillWidth:true}
        UiTextField {id:after;objectName:"workflowAfter";Accessible.name:"Virgülle ayrılmış after düğümleri";placeholderText:"after: quality,summary (boş: bağımlılığı kaldır)";Layout.fillWidth:true}
        UiButton {objectName:"workflowSetAfter";text:"Hedefin after bağımlılığını doğrula";enabled:workflowRunner.canAct;onClicked:workflowRunner.setAfter(edgeTarget.text,after.text);Layout.fillWidth:true}
        UiCheckBox {id:advanced;objectName:"workflowAdvanced";text:"Bağlantı / dependency / batch / sweep tarifini düzenle";Layout.fillWidth:true}
        ColumnLayout {visible:advanced.checked;Layout.fillWidth:true
            UiLabel {text:"Data-only JSON: inputs ile portları, after ile kontrol bağımlılığını düzenleyin. Batch cases: {id,sources:{source:dv:UUID},columns:{source:{eskiColumnId:yeniColumnId}}}; farklı dataset için açık tür/metadata uyumlu eşleme. Sweep: {node,parameter:ddof,values:[0,1]}. En çok24 node,8 case×sweep,10000 satır/64 kolon/kaynak,500000 row×node. Rename/drop/filter transform desteklenir; diğer yöntemler hazır gösterilmez.";wrapMode:Text.Wrap;Layout.fillWidth:true}
            UiButton {text:"Güncel tarifi editöre getir";onClicked:editor.text=workflowRunner.graphText;Layout.fillWidth:true}
            UiTextArea {id:editor;objectName:"workflowEditor";Accessible.name:"Typed DAG declarative JSON64KiB";text:"{}";textFormat:TextEdit.PlainText;wrapMode:TextEdit.Wrap;Layout.fillWidth:true;Layout.preferredHeight:250;enabled:!workflowRunner.busy}
            UiButton {objectName:"workflowApply";text:"Tarifi doğrula ve kullan";enabled:workflowRunner.canAct;onClicked:workflowRunner.setGraph(editor.text);Layout.fillWidth:true}
        }
        UiTextField {id:savePath;objectName:"workflowSavePath";Accessible.name:"Yeni DAG JSON dosya yolu";placeholderText:"Yeni DAG dosya yolu";Layout.fillWidth:true}
        UiButton {objectName:"workflowSave";text:"DAG tarifini kaydet (veri içermez)";enabled:workflowRunner.canAct;onClicked:workflowRunner.saveGraph(savePath.text);Layout.fillWidth:true}
        UiCheckBox {id:exportConsent;objectName:"workflowExportConsent";text:"Export düğümlerinin aşağıdaki dizinde yeni Parquet dosyası oluşturmasını açıkça başlat";Layout.fillWidth:true}
        UiTextField {id:output;objectName:"workflowOutput";Accessible.name:"Var olan yerel export dizini";placeholderText:"Var olan export dizini (proje/cache dışında)";Layout.fillWidth:true}
        UiTextField {id:token;objectName:"workflowToken";Accessible.name:"Opsiyonel önceki export idempotency UUID kimliği";placeholderText:"Boş: yeni export UUID; tekrar için önceki token";Layout.fillWidth:true}
        Flow {Layout.fillWidth:true;spacing:Theme.sm
            UiButton {objectName:"workflowDryRun";text:"Dry-run / maliyet önkontrol";enabled:workflowRunner.canAct&&workflowRunner.nodes.length>0;onClicked:workflowRunner.start(true,false,"","")}
            UiButton {objectName:"workflowRun";text:"DAG'ı açıkça çalıştır";enabled:workflowRunner.canAct&&workflowRunner.nodes.length>0;onClicked:workflowRunner.start(false,exportConsent.checked,output.text,token.text)}
            UiButton {objectName:"workflowCancel";text:"DAG iptal";visible:workflowRunner.busy;onClicked:workflowRunner.cancel()}
        }
        UiLabel {objectName:"workflowCaption";text:(workflowRunner.report.status||"Çalıştırılmadı")+" · "+(workflowRunner.staleResult?"Geçmiş/düzenlenmiş; güncel sayılmaz":"Doğrulama zamanındaki sonuç")+" · iş tahmini="+(workflowRunner.report.estimated_work||0)+" · cache hit öncesi kaynak/config/code/env/yöntem yeniden doğrulanır.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiCheckBox {id:details;objectName:"workflowDetails";text:"Ayrıntılı hesap metadata ve provenance göster";Layout.fillWidth:true}
        Repeater {model:workflowRunner.report.nodes||[]
            UiLabel {required property var modelData;objectName:"workflowResult_"+modelData.node;text:modelData.case+" / "+modelData.node+": "+modelData.status+" · attempts="+modelData.attempts+" · verified="+(modelData.verified_at||"yok")+"\n"+panel.summary(modelData)+(details.checked?"\n"+JSON.stringify((modelData.value||{}).report||{}):"");wrapMode:Text.Wrap;Layout.fillWidth:true}
        }
        UiLabel {text:"Sonuçlar run artifact'ıdır; ana dataset zinciri otomatik değişmez. Kaynak değişirse eski cache güncel sayılmaz. Export yalnız yeni dosya yayınlar; başka run/kaynak üzerine yazmaz. İç RowId/SourceRecordId artifact'ta korunur; kullanıcı exportunda sistem kolonları çıkarılır. Retry yalnız saf hesaplamada geçici I/O için0–2; export otomatik retry edilmez. Geçmiş sonucu açmak veri veya ağ işlemi başlatmaz.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiCombo {id:saved;objectName:"workflowSaved";accessibleLabel:"Kayıtlı workflow run";model:workflowRunner.savedRuns;textRole:"label";valueRole:"id";Layout.fillWidth:true}
        UiButton {objectName:"workflowOpen";text:"Geçmiş run aç (çalıştırmaz)";enabled:!workflowRunner.busy&&saved.currentIndex>=0;onClicked:workflowRunner.openRecord(saved.currentValue);Layout.fillWidth:true}
        StateNotice {heading:"DAG durumu";detail:workflowRunner.errorText||workflowRunner.message;kind:workflowRunner.errorText?"error":workflowRunner.busy?"loading":"info";Layout.fillWidth:true}
        UiLabel {text:"Local schedule mevcut değil. Uygulama kapalıyken iş yok; CLI'yi kullanıcı başlatır. Sistem scheduler entegrasyonu kurulu/başarılı sayılmaz. GUI ve CLI aynı engine'i kullanır; aynı proje için tek writer gerekir.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiButton { visible: false;objectName:"workflowHelp";text:"DAG, dependency, cache ve batch öğren";helpContext:"workflow.source";onClicked:panel.helpRequested(this,helpContext);Layout.fillWidth:true}
    }
}
