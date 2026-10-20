import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

ColumnLayout {
    id:panel
    objectName:"lifecyclePanel"
    property string helpContext:"model.card"
    signal helpRequested(var origin,string context)
    signal retrainRequested()
    function purposeName(value) { return {regression:"Sayısal tahmin",classification:"Kategori tahmini",kmeans:"Benzer kayıtları gruplama",isolation_forest:"Anomali adayları",iqr:"IQR sınırları"}[value]||value||"" }
    function number(value) { return typeof value === "number" ? Number(value.toPrecision(6)).toString() : "tanımsız" }
    function metrics(values) { return (values||[]).map(m=>m.metric+" = "+number(m.value)).join(" · ") }
    function baselineSummary(card) {
        if(!card.baseline)return "Etiketsiz analizde baseline karşılaştırması yok."
        let first=(card.baseline.comparison||[]).filter(e=>e.scope==="validation")[0]
        return "Baseline — "+card.baseline.strategy+(first?"\nValidation: "+metrics(first.metrics):" · geliştirme koşusundaki karşılaştırmaya bakın.")
    }
    spacing:Theme.md
    FileDialog { id:openDialog;title:"Güvenli model paketi aç";nameFilters:["Veri_Ufku model (*.vumodel)"];onAccepted:lifecycle.openPackage(selectedFile.toString()) }
    FileDialog { id:saveDialog;title:"Yeni model paketi kaydet";fileMode:FileDialog.SaveFile;nameFilters:["Veri_Ufku model (*.vumodel)"];onAccepted:lifecycle.savePackage(selectedFile.toString()) }
    FileDialog { id:predictDialog;title:"Tahminleri yeni Parquet dosyasına aktar";fileMode:FileDialog.SaveFile;nameFilters:["Parquet (*.parquet)"];onAccepted:lifecycle.predictData(selectedFile.toString(),policy.currentIndex===0?"reject":"drop",parseInt(batch.text)) }
    UiLabel { text:"Model kartı ve yeni veriye uygulama";font.bold:true;font.pixelSize:Theme.heading;Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiLabel { text:"Yeni dosyayı önce Veri ekranında içe aktarın; aşağıdan tahmin veri sürümünü seçin. Eğitim pipeline’ı korunur, yeni veride tekrar fit yapılmaz. Tablo görünümündeki filtre/sıralama kapsamı değiştirmez; daha dar kapsam için ayrı işlem sürümü oluşturun.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiCombo { accessibleLabel: "Kayıtlı model"; id:models;objectName:"lifecycleModels";model:lifecycle.models;textRole:"label";valueRole:"id";Layout.fillWidth:true;Layout.minimumWidth:0 }
    Flow { Layout.fillWidth:true;spacing:Theme.sm
        UiButton { objectName:"lifecycleOpenSaved";text:"Koşunun modelini aç";enabled:models.currentIndex>=0&&!projects.busy;onClicked:lifecycle.selectModel(models.currentValue) }
        UiButton { objectName:"lifecycleOpenPackage";text:"Paket dosyası aç";enabled:!projects.busy;onClicked:openDialog.open() }
        UiButton { objectName:"lifecycleSave";text:"Yeni paket dosyası kaydet";enabled:!!lifecycle.card.schema&&!projects.busy;onClicked:saveDialog.open() }
        UiButton { text:qsTr("İptal");visible:lifecycle.busy;onClicked:lifecycle.cancel() }
    }
    StateNotice { Layout.fillWidth:true;kind:lifecycle.errorText?"error":lifecycle.busy?"loading":"info";heading:"Model yaşam döngüsü";detail:lifecycle.errorText||lifecycle.message }
    ColumnLayout {
        visible:!!lifecycle.card.schema;Layout.fillWidth:true;spacing:Theme.sm
        UiLabel { objectName:"lifecycleCard";text:panel.purposeName(lifecycle.card.purpose)+" · "+(lifecycle.card.estimator||"")+"\nKaynak veri sürümü: "+(lifecycle.card.dataset_version||"")+"\nEğitim: "+(lifecycle.card.fit_row_count||0)+" kayıt"+((lifecycle.card.fit_scope||"").indexOf("plus_validation")>=0?" · eğitim ve validation birlikte":" · eğitim bölümü")+"\nHedef: "+(lifecycle.card.target?lifecycle.card.target.name+(lifecycle.card.target.unit?" · "+lifecycle.card.target.unit:""):"Etiket yok")+" · seed: "+lifecycle.card.seed+"\nSeçilen aday: "+((lifecycle.card.candidate_selection||{}).selected||"")+"\n"+panel.baselineSummary(lifecycle.card);Layout.fillWidth:true;wrapMode:Text.Wrap }
        Repeater { model:lifecycle.card.features||[];UiLabel { required property var modelData;text:modelData.name+" · "+modelData.type+" · birim: "+(modelData.unit||"belirtilmedi")+" · "+modelData.id;Layout.fillWidth:true;wrapMode:Text.Wrap } }
        UiLabel { text:lifecycle.card.limitations||"";color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiLabel { text:"Özellik önemi — "+(lifecycle.card.importance&&lifecycle.card.importance.status==="available"?"validation üzerinde keşifsel karşılaştırma":"bu koşuda hesaplanmadı")+"\n"+(lifecycle.card.importance?(lifecycle.card.importance.limitation||lifecycle.card.importance.reason||""):"");Layout.fillWidth:true;wrapMode:Text.Wrap }
        Repeater { model:lifecycle.card.importance?lifecycle.card.importance.values||[]:[];UiLabel { required property var modelData;text:modelData.name+": "+panel.number(modelData.mean)+" ± "+panel.number(modelData.std);Layout.fillWidth:true;wrapMode:Text.Wrap } }
        UiCheckBox { id:details;text:"Split, preprocessing, metrikler, label sırası ve sürümleri göster";Layout.fillWidth:true }
        UiLabel { visible:details.checked;text:details.checked?JSON.stringify({candidate_selection:lifecycle.card.candidate_selection,split:lifecycle.card.split,preprocessing:lifecycle.card.preprocessing,fitted_preprocessing:lifecycle.card.fitted_preprocessing,metrics:lifecycle.card.metrics,label_order:lifecycle.card.label_order,versions:lifecycle.card.versions},null,2):"";Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiCombo { accessibleLabel: "Tahmin veri kümesi"; objectName:"lifecycleDataset";model:dataView.datasets;textRole:"label";valueRole:"id";Layout.fillWidth:true;Layout.minimumWidth:0
            currentIndex: { let values=dataView.datasets;for(let i=0;i<values.length;i++)if(values[i].id===dataView.selectedDataset)return i;return -1 }
            onActivated:{dataView.selectDataset(currentValue);lifecycle.invalidate()}
        }
        UiLabel { text:"Kolon eşlemesi: otomatik olarak kimlik, ardından tam isim kullanılır. Farklı isimlerde açık seçim yapın. Tür/birim uyuşmazlığı engellenir; fazla alanlar yalnız çıktıda korunur.";Layout.fillWidth:true;wrapMode:Text.Wrap }
        Repeater { model:lifecycle.card.features||[];ColumnLayout { required property var modelData;Layout.fillWidth:true
            UiLabel { text:modelData.name+" → yeni veri kolonu";Layout.fillWidth:true }
            UiCombo { accessibleLabel: "Tahmin özellik eşlemesi"; objectName:"lifecycleMap_"+modelData.id;model:[{id:"",name:"Otomatik kimlik/tam isim"}].concat(lifecycle.columns);textRole:"name";valueRole:"id";Layout.fillWidth:true;Layout.minimumWidth:0
                currentIndex: { let id=lifecycle.featureMapping[modelData.id]||"";for(let i=0;i<count;i++)if(valueAt(i)===id)return i;return 0 }
                onActivated:lifecycle.mapFeature(modelData.id,currentValue)
            }
        } }
        UiCombo { accessibleLabel: "Geçersiz kayıt politikası"; id:policy;objectName:"lifecyclePolicy";model:["Geçersiz kayıtta durdur","Geçersiz kaydı tahmin dışında bırak; çıktı satırını koru"];Layout.fillWidth:true;onActivated:lifecycle.invalidate() }
        UiLabel { text:"Parçalı tahmin boyutu (1–4096 kayıt)";Layout.fillWidth:true }
        UiTextField { id:batch;objectName:"lifecycleBatch";Accessible.name:"Parçalı tahmin boyutu";text:"512";validator:IntValidator { bottom:1;top:4096 } Layout.fillWidth:true;onTextEdited:lifecycle.invalidate() }
        UiButton { objectName:"lifecyclePreview";text:"Yeni veri kolon/kayıt önizlemesi";enabled:!projects.busy;Layout.fillWidth:true;onClicked:lifecycle.previewData(policy.currentIndex===0?"reject":"drop",parseInt(batch.text)) }
        UiLabel { objectName:"lifecyclePreviewReport";visible:!!lifecycle.previewReport.schema;text:"Önizleme: "+(lifecycle.previewReport.rows||0)+" kayıt · tahmin edilemeyen: "+(lifecycle.previewReport.invalid_rows||0)+"\nFazla alanlar çıktıda korunur: "+((lifecycle.previewReport.extra_columns||[]).join(", ")||"yok")+"\n"+(lifecycle.previewReport.blockers||[]).join("\n");Layout.fillWidth:true;wrapMode:Text.Wrap }
        Repeater { model:lifecycle.previewReport.features||[];UiLabel { required property var modelData;text:modelData.feature_name+" → "+modelData.column_name+" · "+modelData.actual_type+(modelData.actual_unit?" · "+modelData.actual_unit:"")+"\nEksik: "+modelData.missing+" · sonlu olmayan: "+modelData.nonfinite+" · bilinmeyen kategori: "+modelData.unknown_categories+(modelData.issues.length?"\n"+modelData.issues.join("\n"):"");Layout.fillWidth:true;wrapMode:Text.Wrap } }
        UiLabel { visible:!!lifecycle.previewReport.schema;text:"Eksikler eğitimde öğrenilen doldurma değerleriyle işlenir. Yeni kategoriler one-hot kodlamada sıfır blokla temsil edilir; sıralı kodlamada tahmin edilemez ve seçtiğiniz geçersiz kayıt politikası uygulanır.";Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiLabel { text:lifecycle.card.probability_supported?"Sınıf olasılığı desteklenir; label sırası karttadır. Olasılık kesinlik veya kalibrasyon garantisi değildir.":"Bu model sınıf olasılığı sağlamaz. Tahmin belirsizliği için otomatik güven aralığı üretilmez.";Layout.fillWidth:true;wrapMode:Text.Wrap;color:Theme.warning }
        UiLabel { text:"Yeni tahmin dosyası yolu (boşsa dosya seçicisi açılır)";Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiTextField { id:predictionPath;objectName:"lifecycleOutputPath";Accessible.name:"Yeni tahmin Parquet dosyası yolu";Layout.fillWidth:true }
        UiButton { objectName:"lifecyclePredict";text:"Modeli uygula ve yeni Parquet dosyasına aktar";primary:true;tone:"violet";multiline:true;Layout.fillWidth:true;enabled:!!lifecycle.previewReport.schema&&(lifecycle.previewReport.blockers||[]).length===0&&!projects.busy;onClicked: { if(predictionPath.text.trim()) lifecycle.predictData(predictionPath.text.trim(),policy.currentIndex===0?"reject":"drop",parseInt(batch.text)); else predictDialog.open() } }
        UiLabel { objectName:"lifecycleOutput";text:lifecycle.outputReport.output?"Yeni çıktı: "+lifecycle.outputReport.output+(lifecycle.outputReport.details.preview?"\nTahmin edilen: "+(lifecycle.outputReport.details.predicted_rows||0)+" · tahmin dışında bırakılan: "+((lifecycle.outputReport.details.dropped_row_ids||[]).length)+"\nKaynak satırları ve sırası korundu.":"\nDoğrulanmış model paketi kaydedildi."):"";Layout.fillWidth:true;wrapMode:Text.Wrap }
    }
    ExperimentRegistryPanel { Layout.fillWidth:true;onHelpRequested:function(origin,context){panel.helpRequested(origin,context)} }
    ExplanationPanel { Layout.fillWidth:true;onHelpRequested:function(origin,context){panel.helpRequested(origin,context)} }
    UiButton { objectName:"lifecycleRetrain";text:"Yeniden eğit — yeni veri için hazırlık ve değerlendirme ayarlarını aç";Layout.fillWidth:true;multiline:true;enabled:!projects.busy&&!lifecycle.busy;onClicked:panel.retrainRequested() }
    UiLabel { text:"Yeniden eğitim yeni bir plan/koşu oluşturur; mevcut model değişmez. Hedef, split ve seed seçilip eğitim ayrıca başlatılır.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    Flow { Layout.fillWidth:true;spacing:Theme.sm
        UiButton { text:"Model kartı";tone:"mint";helpContext:"model.card";onClicked:panel.helpRequested(this,helpContext) }
        UiButton { text:"Özellik önemi";tone:"mint";helpContext:"model.importance";onClicked:panel.helpRequested(this,helpContext) }
        UiButton { text:"Bilinmeyen kategori";tone:"mint";helpContext:"model.unknown-category";onClicked:panel.helpRequested(this,helpContext) }
        UiButton { text:"Yeni veri";tone:"mint";helpContext:"model.new-data";onClicked:panel.helpRequested(this,helpContext) }
        UiButton { text:"Tahmin belirsizliği";tone:"mint";helpContext:"model.uncertainty";onClicked:panel.helpRequested(this,helpContext) }
    }
}
