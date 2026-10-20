import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id:panel
    objectName:"preparationPanel"
    property string helpContext:"model.prepare"
    property var purposes:["regression","classification","clustering","anomaly"]
    property var families:["linear","distance","tree"]
    property var chosenFeatures:[]
    property string lastSource:""
    readonly property string purpose:purposes[purposeChoice.currentIndex]
    signal helpRequested(var origin,string context)
    spacing:Theme.md
    function key(picker){return picker.currentIndex>=0?picker.currentValue:""}
    function index(picker,value){for(let i=0;i<picker.model.length;i++)if(picker.model[i].id===value){picker.currentIndex=i;return}}
    function spec(){let value={purpose:purpose,features:chosenFeatures.filter(v=>v!==(purpose==="regression"||purpose==="classification"?key(target):"")&&v!==key(group)),target:purpose==="regression"||purpose==="classification"?key(target):"",family:families[family.currentIndex],history_action:["review","raw","relocate"][historyChoice.currentIndex],missing_indicator:missingFlag.checked,imputation_neighbors:neighbors.value,imputation_iterations:iterations.value,imputation_seed:imputationSeed.value,numeric_imputation:["median","mean","none","knn","iterative"][numericFill.currentIndex],categorical_imputation:categoryFill.currentIndex===0?"most_frequent":"none",encoding:encoding.currentIndex===0?"onehot":"ordinal",scaling:["auto","none","standard"][scaling.currentIndex],date_features:dates.checked,selection:selection.checked?"variance":"none",group:key(group),time:key(time),allow_identifiers:allowIds.checked,prediction_context:context.text,history_note:historyNote.text,invalid_numeric:nonfinite.checked?"as_missing":"reject",precision:approximate.checked?"approximate":"reject"};if(useText.checked&&panel.purpose==="classification"){value.features=[panel.key(textColumn)];value.text=textOptions.spec(panel.key(textColumn));value.selection="none"}return value}
    function restore(){let s=preparation.report.spec;if(!s)return;purposeChoice.currentIndex=purposes.indexOf(s.purpose);family.currentIndex=families.indexOf(s.family);index(source,s.source_version);index(target,s.target);index(group,s.group);index(time,s.time);chosenFeatures=s.features;historyChoice.currentIndex=["review","raw","relocate"].indexOf(s.history_action);numericFill.currentIndex=["median","mean","none","knn","iterative"].indexOf(s.numeric_imputation);missingFlag.checked=!!s.missing_indicator;neighbors.value=s.imputation_neighbors||5;iterations.value=s.imputation_iterations||10;imputationSeed.value=s.imputation_seed===undefined?42:s.imputation_seed;categoryFill.currentIndex=s.categorical_imputation==="most_frequent"?0:1;encoding.currentIndex=s.encoding==="onehot"?0:1;scaling.currentIndex=["auto","none","standard"].indexOf(s.scaling);dates.checked=s.date_features;selection.checked=s.selection==="variance";allowIds.checked=s.allow_identifiers;context.text=s.prediction_context;historyNote.text=s.history_note;nonfinite.checked=s.invalid_numeric==="as_missing";approximate.checked=s.precision==="approximate";useText.checked=!!s.text;if(s.text){index(textColumn,s.text.column);textOptions.restore(s.text)}settings.checked=false}
    Connections { target:preparation; function onChanged(){if(panel.lastSource!==preparation.sourceVersion){panel.lastSource=preparation.sourceVersion;panel.chosenFeatures=preparation.columns.filter(c=>!c.identifier_candidate&&c.role!=="ignored").map(c=>c.id)}} }
    Component.onCompleted:{lastSource=preparation.sourceVersion;chosenFeatures=preparation.columns.filter(c=>!c.identifier_candidate&&c.role!=="ignored").map(c=>c.id);if(preparation.current&&preparation.report.spec)restore()}
    UiLabel { text:"Modelleme için veri hazırlığı"; font.pixelSize:Theme.heading;font.bold:true;Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiLabel { text:"Bu ekran genel temizlikten ayrı bir hazırlama planı üretir. Tüm veri üzerinde fit, eğitim veya değerlendirme yapılmaz. Rapor sızıntısızlık garantisi vermez.";color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiCheckBox { id:settings;objectName:"preparationSettings";text:"Amaç, alanlar ve hazırlama seçeneklerini göster";checked:true;Layout.fillWidth:true }
    ColumnLayout {
        visible:settings.checked;Layout.fillWidth:true;spacing:Theme.md
        UiCombo { accessibleLabel: qsTr("Veri kümesi"); objectName:"preparationDataset";model:dataView.datasets;textRole:"label";valueRole:"id";Layout.fillWidth:true;Layout.minimumWidth:0;onActivated:{dataView.selectDataset(currentValue);preparation.invalidate()} }
        UiCombo { accessibleLabel: "Model amacı"; id:purposeChoice;objectName:"preparationPurpose";model:["Sayısal hedef tahmin etmek","Kategori hedef tahmin etmek","Benzer kayıtları gruplamak","Sıra dışı kayıtları bulmak"];Layout.fillWidth:true;onActivated:{if(panel.purpose==="clustering")family.currentIndex=1;else if(panel.purpose==="anomaly"&&family.currentIndex===0)family.currentIndex=2;preparation.invalidate()} }
        UiLabel { text:"Hazırlama planının model ailesi (henüz model eğitilmez)";Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiCombo { accessibleLabel: "Model ailesi"; id:family;objectName:"preparationFamily";model:["Düzenlileştirilmiş doğrusal","Uzaklığa dayalı","Ağaç tabanlı"];currentIndex:2;Layout.fillWidth:true;onActivated:preparation.invalidate() }
        UiLabel { text:"Hedef — tahmin etmek istediğin alan";visible:panel.purpose==="regression"||panel.purpose==="classification";Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiCombo { accessibleLabel: "Tahmin hedefi"; id:target;objectName:"preparationTarget";model:preparation.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true;Layout.minimumWidth:0;visible:panel.purpose==="regression"||panel.purpose==="classification";onActivated:preparation.invalidate() }
        UiLabel { text:"Geçmiş riskiyle ne yapmak istiyorsun?";Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiCombo { accessibleLabel: "Geçmiş riski kararı"; id:historyChoice;objectName:"preparationHistory";model:["Mevcut sürümü incele; riskler çözülmüş sayılmaz","Önceki temiz kaynaktan yeniden başlat","Önceki kaynağı kullan; desteklenen adımları eğitim katına taşı"];Layout.fillWidth:true;onActivated:preparation.invalidate() }
        UiCombo { accessibleLabel: "Hazırlama kaynak sürümü"; id:source;objectName:"preparationSource";model:preparation.sourceChoices;textRole:"label";valueRole:"id";Layout.fillWidth:true;Layout.minimumWidth:0;onActivated:{preparation.selectSource(currentValue);panel.chosenFeatures=preparation.columns.filter(c=>!c.identifier_candidate&&c.role!=="ignored").map(c=>c.id)} }
        UiLabel { text:"Önceki kaynak seçimi genel temizlik zincirini değiştirmez. Alanları bu kaynaktan yeniden seç; sonradan üretilmiş kolonlar burada bulunmayabilir. Geçmiş riskleri görünür kalır.";Layout.fillWidth:true;wrapMode:Text.Wrap;color:Theme.secondary }
        UiTextField { id:historyNote;objectName:"preparationHistoryNote";placeholderText:"Geçmiş veya proje dışında yapılan işlem/seçimler hakkında not";maximumLength:1000;Layout.fillWidth:true;onTextEdited:preparation.invalidate();Accessible.name:"Geçmiş inceleme notu" }
        UiTextField { id:context;objectName:"preparationContext";placeholderText:"Tahmin anında hangi bilgi biliniyor? (ör. satıştan önce)";maximumLength:1000;Layout.fillWidth:true;onTextEdited:preparation.invalidate();Accessible.name:"Tahmin bilgisi bağlamı" }
        UiLabel { text:"Özellikler — modele giriş olacak alanlar. Hedef/grup anahtarı özellik olmaz.";Layout.fillWidth:true;wrapMode:Text.Wrap }
        Repeater { id:featureChoices;model:preparation.columns;delegate:UiCheckBox { required property var modelData;objectName:"preparationFeature_"+modelData.name;text:modelData.name+" · "+modelData.physical_type+(modelData.identifier_candidate?" · kimlik adayı":"");checked:panel.chosenFeatures.indexOf(modelData.id)>=0&&enabled;enabled:(modelData.id!==panel.key(target)||!(panel.purpose==="regression"||panel.purpose==="classification"))&&modelData.id!==panel.key(group);Layout.fillWidth:true;onClicked:{let chosen=panel.chosenFeatures.slice();let at=chosen.indexOf(modelData.id);if(checked&&at<0)chosen.push(modelData.id);if(!checked&&at>=0)chosen.splice(at,1);panel.chosenFeatures=chosen;preparation.invalidate()} } }
        UiCheckBox { id:allowIds;objectName:"preparationAllowIds";text:"Kimlik adayını özellik olarak kullanmanın riskini açıkça kabul ediyorum";Layout.fillWidth:true;onClicked:preparation.invalidate() }
        UiLabel { text:"Grup/kişi anahtarı ve zaman alanı (varsa)";Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiCombo { accessibleLabel: "Grup veya kişi anahtarı"; id:group;objectName:"preparationGroup";model:[{id:"",name:"Grup alanı yok"}].concat(preparation.columns);textRole:"name";valueRole:"id";Layout.fillWidth:true;Layout.minimumWidth:0;onActivated:preparation.invalidate() }
        UiCombo { accessibleLabel: "Zaman alanı"; id:time;objectName:"preparationTime";model:[{id:"",name:"Zaman alanı yok"}].concat(preparation.columns);textRole:"name";valueRole:"id";Layout.fillWidth:true;Layout.minimumWidth:0;onActivated:preparation.invalidate() }
        UiCheckBox { id:useText;objectName:"preparationTextEnabled";visible:panel.purpose==="classification";text:"Serbest metni eğitim fold'unda öğrenilen TF-IDF ile sınıflandır";onClicked:preparation.invalidate() }
        ColumnLayout { visible:useText.checked&&panel.purpose==="classification";Layout.fillWidth:true
            UiCombo { accessibleLabel: "Serbest metin alanı"; id:textColumn;objectName:"preparationTextColumn";model:preparation.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true;onActivated:preparation.invalidate() }
            TextOptions { id:textOptions;Layout.fillWidth:true;onEdited:preparation.invalidate() }
            UiLabel { text:"Bu yol tek metin özelliği kullanır; hedef/grup/zaman giriş değildir. İnceleme vocab'ı alınmaz; vocab ve IDF her fit'te yalnız train'den öğrenilir. Boş metin sıfır vektör; tümü boş train reddedilir. Güvenli paket/yeni dosya tahmini henüz desteklenmez; mevcut sınıflandırma/defter/metrik akışı kullanılır.";Layout.fillWidth:true;wrapMode:Text.Wrap }
            UiButton { text:"TF-IDF ve eğitim fold'u yardımı";helpContext:"text.tfidf";onClicked:panel.helpRequested(this,helpContext) }
        }
        UiLabel { text:"Kategorik encoding — kategorileri modele uygun temsil etme";Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiCombo { accessibleLabel: "Kategori kodlama yöntemi"; id:encoding;objectName:"preparationEncoding";model:["One-hot — sözlük yalnız eğitim katında öğrenilecek","Ordinal — yalnız açık semantik sıraya sahip kategoriler"];Layout.fillWidth:true;onActivated:preparation.invalidate() }
        UiLabel { text:"Sayısal scaling — ölçüm ölçeğini düzenleme";Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiCombo { accessibleLabel: "Sayısal ölçekleme"; id:scaling;objectName:"preparationScaling";model:["Aileye göre: ağaçta yok; doğrusal/uzaklıkta standardizasyon","Scaling yok (açık seçim)","Standardizasyon (açık seçim; ağaçta genellikle gereksiz)"];Layout.fillWidth:true;onActivated:preparation.invalidate() }
        UiLabel { text:"İmputasyon — eksik özelliği eğitimde öğrenilen değerle doldurma";Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiCombo { accessibleLabel: "Sayısal eksik doldurma"; id:numericFill;objectName:"preparationNumericFill";model:["Sayısal: eğitim katı medyanı","Sayısal: eğitim katı ortalaması","Sayısal doldurma yok","KNN — yalnız eğitim katı, ham birim uzaklığı","Iterative — yalnız eğitim katı, tek doldurma"];Layout.fillWidth:true;onActivated:preparation.invalidate() }
        UiButton { text:"Eğitim katında imputasyon";helpContext:"model.imputation";onClicked:panel.helpRequested(this,helpContext) }
        UiCheckBox { id:missingFlag;objectName:"preparationMissingIndicator";text:"Özgün eksik hücre göstergesini özellik olarak ekle";Layout.fillWidth:true;onClicked:preparation.invalidate() }
        UiLabel { text:"KNN ham ölçüm birimi uzaklıklarını kullanır; birimleri inceleyin. Iterative tek doldurmadır; MI çıkarımı Karşılaştır alanında ayrıdır. Tam veri fit edilmez.";wrapMode:Text.Wrap;Layout.fillWidth:true }
        RowLayout {
            Layout.fillWidth:true
            UiSpinBox { id:neighbors;objectName:"preparationImputationNeighbors";from:1;to:20;value:5;Accessible.name:"KNN komşu sayısı";onValueModified:preparation.invalidate() }
            UiSpinBox { id:iterations;objectName:"preparationImputationIterations";from:1;to:30;value:10;Accessible.name:"Iterative iterasyon";onValueModified:preparation.invalidate() }
            UiSpinBox { id:imputationSeed;objectName:"preparationImputationSeed";from:0;to:2147483647;value:42;Accessible.name:"İmputasyon seed";onValueModified:preparation.invalidate() }
        }

        UiCombo { accessibleLabel: "Kategorik eksik doldurma"; id:categoryFill;objectName:"preparationCategoryFill";model:["Kategori: eğitim katında en sık değer","Kategori doldurma yok"];Layout.fillWidth:true;onActivated:preparation.invalidate() }
        UiCheckBox { id:dates;objectName:"preparationDates";text:"Tarih alanlarından yıl/ay/haftanın günü planla; hedef ufku/gelecek bilgi ekleme";checked:true;Layout.fillWidth:true;onClicked:preparation.invalidate() }
        UiCheckBox { id:selection;objectName:"preparationSelection";text:"İsteğe bağlı: sıfır varyanslı özellikleri eğitim katında seçerek ele";Layout.fillWidth:true;onClicked:preparation.invalidate() }
        UiCheckBox { id:nonfinite;objectName:"preparationNonfinite";text:"NaN/inf sayısal özelliklerini açıkça eksik kabul et (hedef doldurulmaz)";Layout.fillWidth:true;onClicked:preparation.invalidate() }
        UiCheckBox { id:approximate;objectName:"preparationApproximate";text:"Gelecekte Integer/Decimal → Float64 yaklaşık dönüşümüne açık izin ver";Layout.fillWidth:true;onClicked:preparation.invalidate() }
        UiButton { objectName:"preparationScan";text:"Uygunluk raporu ve plan oluştur";tone:"violet";primary:true;Layout.fillWidth:true;multiline:true;enabled:!projects.busy&&preparation.columns.length>0;onClicked:{preparation.create(JSON.stringify(panel.spec()));settings.checked=false} }
    }
    Flow { Layout.fillWidth:true;spacing:Theme.sm
        UiButton { text:qsTr("Bu ne işe yarar?");tone:"mint";helpContext:"model.prepare";onClicked:panel.helpRequested(this,helpContext) }
        UiButton { text:"Geçmiş ve eğitim katını öğren";tone:"mint";helpContext:"model.history";onClicked:panel.helpRequested(this,helpContext) }
        UiButton { text:qsTr("İptal");visible:preparation.busy;onClicked:preparation.cancel() }
    }
    StateNotice { Layout.fillWidth:true;kind:preparation.errorText?"error":preparation.busy?"loading":"info";heading:"Hazırlama durumu";detail:preparation.errorText||preparation.message }
    ColumnLayout {
        visible:!!preparation.report.plan;Layout.fillWidth:true;spacing:Theme.md
        UiLabel { objectName:"preparationSummary";text:(preparation.current?"Güncel plan":"Kayıtlı/eski plan; kaynak/ayar sürümünü kontrol edin")+"\nFit edilmedi · tam kaynak: "+(preparation.report.dataset_n||0)+" kayıt · geçerli hedef/gözlem: "+(preparation.report.eligible_n||0)+" · eksik/geçersiz hedef: "+(preparation.report.excluded_target_n||0)+"\nKaynak sürümü: "+(preparation.report.dataset_version||"")+"\n"+(preparation.report.status==="blocked"?"Çözülmesi gereken engeller var; plan eğitim onayı değildir.":"Plan inceleme gerektirir; eğitim/validation/test ayırma henüz yapılmadı.");Layout.fillWidth:true;wrapMode:Text.Wrap;font.bold:true }
        Repeater { model:preparation.report.risks||[];UiLabel { required property var modelData;text:(modelData.severity==="blocker"?"Engel: ":"İncele: ")+modelData.reason;color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap } }
        UiLabel { objectName:"modelResourceForecast";visible:!!preparation.report.resource_forecast;Layout.fillWidth:true;wrapMode:Text.Wrap;text: { const c=preparation.report.resource_forecast;return c?"Bellek öngörüsü: seçili giriş ~"+(c.projected_input_bytes/1048576).toFixed(1)+" MiB; olası dense matris ~"+(c.possible_dense_bytes/1048576).toFixed(1)+" MiB. Bütçe "+(c.ram_budget_bytes/1048576).toFixed(0)+" MiB. Eğitim bellekte çalışır.\n"+c.caveat+"\n"+c.action:"" } }
        UiLabel { text:"Geçmiş incelemesi";font.bold:true;Layout.fillWidth:true }
        Repeater { model:preparation.report.history?preparation.report.history.findings:[];UiLabel { required property var modelData;text:modelData.kind+(modelData.method?" / "+modelData.method:"")+" · "+(modelData.removed_from_source?"Seçilen model kaynağında bu işlem uygulanmadı":"Model kaynağında hâlâ etkili")+"\n"+modelData.reason+(modelData.resolution==="pending_fold_step"?"\nDesteklenen adım yalnız eğitim katında yeniden öğrenilmek üzere planlandı; fit henüz yapılmadı.":"");Layout.fillWidth:true;wrapMode:Text.Wrap;color:Theme.warning } }
        UiLabel { text:"Proje dışındaki işlemler ve kararlar kesin tespit edilemez. Yeni pipeline planı geçmiş riskini tek başına gidermez.";Layout.fillWidth:true;wrapMode:Text.Wrap;color:Theme.warning }
        Repeater { model:preparation.report.target?preparation.report.target.class_distribution||[]:[];UiLabel { required property var modelData;text:"Sınıf "+modelData.label+": "+modelData.count+" kayıt";Layout.fillWidth:true;wrapMode:Text.Wrap } }
        UiLabel { visible:!!preparation.report.target&&!!preparation.report.target.distribution_truncated;text:"Sınıf listesi ilk20 sınıfla sınırlıdır; sayımlar tam veri kapsamındadır.";Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiCheckBox { id:details;objectName:"preparationDetails";text:"Alan sayımları, kolon eşlemesi ve plan adımlarını göster";Layout.fillWidth:true }
        ColumnLayout { visible:details.checked;Layout.fillWidth:true
            Repeater { model:preparation.report.columns||[];UiLabel { required property var modelData;text:modelData.name+" · geçerli="+modelData.valid_count+" · eksik="+modelData.null_count+" · NaN/inf="+modelData.nonfinite_count+" · farklı="+modelData.unique_count;Layout.fillWidth:true;wrapMode:Text.Wrap } }
            Repeater { model:preparation.report.plan?preparation.report.plan.column_lineage:[];UiLabel { required property var modelData;text:modelData.source_name+" → "+modelData.output_names.join(", ")+(modelData.names_status==="template_training_bound"?"\nKategori adları/sözlüğü fit sonrası eğitim katından bağlanacak; şu an yalnız benzersiz ad şablonu.":"");Layout.fillWidth:true;wrapMode:Text.Wrap } }
            Repeater { model:preparation.report.plan?preparation.report.plan.steps:[];UiLabel { required property var modelData;text:modelData.reason+"\n"+(modelData.learned_scope==="training_fold"?"Yalnız eğitim katında öğrenilecek; henüz öğrenilmedi.":"Satırdan üretilecek/sabit açık seçim; henüz uygulanmadı.");Layout.fillWidth:true;wrapMode:Text.Wrap } }
        }
        UiButton { objectName:"preparationSave";text:"Fit edilmemiş planı projeye kaydet";enabled:preparation.current&&!projects.busy&&!projects.readOnly;Layout.fillWidth:true;multiline:true;onClicked:preparation.save() }
    }
    UnsupervisedPanel { Layout.fillWidth:true; purpose:panel.purpose; visible:panel.purpose==="clustering"||panel.purpose==="anomaly"; onPurposeRequested:function(purpose){purposeChoice.currentIndex=purpose==="clustering"?2:3}; onHelpRequested:function(origin,context){panel.helpRequested(origin,context)} }
    ValidationPanel { Layout.fillWidth:true; visible:panel.purpose==="regression"||panel.purpose==="classification"; onHelpRequested:function(origin,context){panel.helpRequested(origin,context)} }
    LifecyclePanel { Layout.fillWidth:true; onRetrainRequested: { preparation.beginRetraining(); settings.checked=true; settings.forceActiveFocus() } onHelpRequested:function(origin,context){panel.helpRequested(origin,context)} }
    UiCombo { accessibleLabel: "Kayıtlı hazırlama planı"; id:saved;objectName:"preparationSaved";model:preparation.savedPlans;textRole:"label";valueRole:"id";Layout.fillWidth:true;Layout.minimumWidth:0 }
    UiButton { objectName:"preparationOpen";text:"Kayıtlı hazırlama planını aç";enabled:saved.currentIndex>=0&&!projects.busy;onClicked:{preparation.openSaved(panel.key(saved));panel.restore()} }
}
