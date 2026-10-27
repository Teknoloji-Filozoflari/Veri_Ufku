import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: panel
    objectName: "unsupervisedPanel"
    property string purpose: "clustering"
    property var chosenFeatures: []
    readonly property bool clustering: purpose === "clustering"
    readonly property var clusterMethods: ["kmeans", "dbscan", "agglomerative", "gmm", "optics", "hdbscan"]
    readonly property var anomalyMethods: ["isolation_forest", "iqr", "lof", "one_class_svm", "robust_covariance"]
    readonly property string method: (clustering ? clusterMethods : anomalyMethods)[Math.max(0, methodChoice.currentIndex)] || "kmeans"
    signal helpRequested(var origin, string context)
    signal purposeRequested(string purpose)
    spacing: Theme.md
    onPurposeChanged: { methodChoice.currentIndex=0; unsupervised.invalidate() }
    function spec() {
        let value={method:method,features:chosenFeatures,scaling:method==="iqr"?"none":scaleChoice.currentIndex===0?"standard":"none",seed:Number(seed.text)}
        if(["kmeans","agglomerative","gmm"].indexOf(method)>=0)value.clusters=Number(k.text)
        if(method==="dbscan"){value.eps=Number(eps.text);value.min_samples=Number(neighbors.text)}
        if(method==="isolation_forest"){
            value.threshold_mode=thresholdMode.currentIndex===0?"fraction":"score"
            if(thresholdMode.currentIndex===0)value.contamination=Number(fraction.text)
            else value.score_threshold=Number(threshold.text)
        }
        if(method==="iqr")value.iqr_multiplier=Number(multiplier.text)
        value.metric=(!clustering&&method!=="lof")||metricChoice.currentIndex===0?"euclidean":"manhattan"
        value.linkage=["ward","complete","average","single"][linkageChoice.currentIndex]
        value.covariance_type=["full","tied","diag","spherical"][covarianceChoice.currentIndex]
        value.min_samples=Number(neighbors.text)
        value.min_cluster_size=Number(minCluster.text)
        value.xi=Number(xi.text)
        value.stability_runs=Number(stability.text)
        value.compare_methods=compareAll.checked?clusterMethods:[]
        if(!clustering&&method!=="iqr"&&method!=="isolation_forest") {
            value.anomaly_mode=noveltyChoice.currentIndex===0?"outlier":"novelty"
            value.training_fraction=Number(trainFraction.text)
            value.contamination=Number(fraction.text)
            value.nu=Number(nu.text)
            value.label_column=labelChoice.currentValue||""
            value.false_positive_cost=Number(fpCost.text); value.false_negative_cost=Number(fnCost.text)
        }
        return value
    }
    Connections { target:unsupervised
        function onRestoreRequested(value) {
            let spec=JSON.parse(value)
            panel.purposeRequested(panel.clusterMethods.indexOf(spec.method)>=0?"clustering":"anomaly")
            methodChoice.currentIndex=(panel.clustering?panel.clusterMethods:panel.anomalyMethods).indexOf(spec.method)
            panel.chosenFeatures=spec.features
            scaleChoice.currentIndex=spec.scaling==="standard"?0:1
            seed.text=String(spec.seed); k.text=String(spec.clusters); eps.text=String(spec.eps); neighbors.text=String(spec.min_samples)
            fraction.text=String(spec.contamination); multiplier.text=String(spec.iqr_multiplier)
            metricChoice.currentIndex=spec.metric==="manhattan"?1:0
            linkageChoice.currentIndex=["ward","complete","average","single"].indexOf(spec.linkage||"ward")
            covarianceChoice.currentIndex=["full","tied","diag","spherical"].indexOf(spec.covariance_type||"full")
            minCluster.text=String(spec.min_cluster_size||5); xi.text=String(spec.xi||0.05)
            stability.text=String(spec.stability_runs||0); compareAll.checked=(spec.compare_methods||[]).length>0
            noveltyChoice.currentIndex=spec.anomaly_mode==="novelty"?1:0; trainFraction.text=String(spec.training_fraction||0.7)
            nu.text=String(spec.nu||0.05); labelChoice.currentIndex=labelChoice.model.findIndex(c=>c.id===(spec.label_column||""))
            fpCost.text=String(spec.false_positive_cost||1); fnCost.text=String(spec.false_negative_cost||1)
            thresholdMode.currentIndex=spec.threshold_mode==="fraction"?0:1; threshold.text=String(spec.score_threshold)
        }
    }
    UiLabel { text:panel.clustering?"Kümeleme — benzer kayıtları keşfet":"Anomali — sıra dışı kayıt adayları";font.bold:true;Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiLabel { text:"Etiket gerekmez. Fit kapsamı outlier/kümeleme için tam sürüm, novelty için seed ile ayrılmış eğitim kayıtlarıdır; Veri ekranının görünüm filtreleri uygulanmaz. Kümeler gerçek sınıf, anomali adayları kesin hata değildir. Kaynak veri değişmez; otomatik silme yok.";Layout.fillWidth:true;wrapMode:Text.Wrap;color:Theme.warning }
    UiCombo { accessibleLabel: qsTr("Veri kümesi"); objectName:"unsupervisedDataset";model:dataView.datasets;textRole:"label";valueRole:"id";currentIndex:dataView.datasets.findIndex(d=>d.id===dataView.selectedDataset);Layout.fillWidth:true;Layout.minimumWidth:0;onActivated:{dataView.selectDataset(currentValue);panel.chosenFeatures=[];unsupervised.invalidate()} }
    UiCombo { accessibleLabel: "Etiketsiz analiz yöntemi"; id:methodChoice;objectName:"unsupervisedMethod";model:panel.clustering?["KMeans — merkez","DBSCAN — yoğunluk/gürültü","Agglomerative — dendrogram","Gaussian mixture — soft membership","OPTICS — yoğunluk sırası","HDBSCAN — optional sklearn backend"]:["IsolationForest — anomali skoru","Tek sütun IQR","LOF — yerel yoğunluk","OneClassSVM — sınır","Robust covariance — elliptical Gaussian"];Layout.fillWidth:true;onCurrentIndexChanged:unsupervised.invalidate() }
    UiCombo { id:metricChoice;objectName:"explorationMetric";visible:panel.clustering||panel.method==="lof";accessibleLabel:"Distance metric";model:["Euclidean","Manhattan"];Layout.fillWidth:true;onCurrentIndexChanged:unsupervised.invalidate() }
    UiCombo { id:linkageChoice;objectName:"explorationLinkage";accessibleLabel:"Linkage";visible:panel.method==="agglomerative";model:["Ward (Euclidean)","Complete","Average","Single"];Layout.fillWidth:true;onCurrentIndexChanged:unsupervised.invalidate() }
    UiCombo { id:covarianceChoice;objectName:"explorationCovariance";accessibleLabel:"GMM covariance";visible:panel.method==="gmm";model:["Full","Tied","Diag","Spherical"];Layout.fillWidth:true;onCurrentIndexChanged:unsupervised.invalidate() }
    UiTextField { id:minCluster;objectName:"explorationMinCluster";Accessible.name:"Minimum küme boyutu";visible:panel.method==="hdbscan";text:"5";Layout.fillWidth:true;onTextChanged:unsupervised.invalidate() }
    UiTextField { id:xi;objectName:"explorationXi";Accessible.name:"OPTICS xi";visible:panel.method==="optics";text:"0.05";Layout.fillWidth:true;onTextChanged:unsupervised.invalidate() }
    UiTextField { id:stability;objectName:"explorationStability";Accessible.name:"Stabilite yeniden örnekleme sayısı 0–10";visible:panel.clustering;text:"0";Layout.fillWidth:true;onTextChanged:unsupervised.invalidate() }
    UiCheckBox { id:compareAll;objectName:"explorationCompare";text:"Altı yöntemi aynı kapsam/ölçekte karşılaştır (en fazla 3000 kayıt)";visible:panel.clustering;Layout.fillWidth:true;onClicked:unsupervised.invalidate() }
    UiCombo { id:noveltyChoice;objectName:"explorationMode";accessibleLabel:"Outlier veya novelty";visible:["lof","one_class_svm","robust_covariance"].indexOf(panel.method)>=0;model:["Outlier — fit kayıtlarındaki adaylar","Novelty — eğitimden ayrılmış kayıtlar"];Layout.fillWidth:true;onCurrentIndexChanged:unsupervised.invalidate() }
    UiTextField { id:trainFraction;objectName:"explorationTrainFraction";Accessible.name:"Novelty eğitim oranı";visible:noveltyChoice.visible&&noveltyChoice.currentIndex===1;text:"0.7";Layout.fillWidth:true;onTextChanged:unsupervised.invalidate() }
    UiTextField { id:nu;objectName:"explorationNu";Accessible.name:"OneClassSVM nu";visible:panel.method==="one_class_svm";text:"0.05";Layout.fillWidth:true;onTextChanged:unsupervised.invalidate() }
    UiCombo { id:labelChoice;objectName:"explorationLabel";accessibleLabel:"Gerçek anomali etiketi 0 normal 1 anomaly";visible:noveltyChoice.visible;model:[{id:"",name:"Etiket yok — başarı ölçülmez"}].concat(unsupervised.columns);textRole:"name";valueRole:"id";Layout.fillWidth:true;onActivated:unsupervised.invalidate() }
    UiTextField { id:fpCost;objectName:"explorationFPCost";Accessible.name:"False positive maliyeti";visible:noveltyChoice.visible;text:"1";Layout.fillWidth:true;onTextChanged:unsupervised.invalidate() }
    UiTextField { id:fnCost;objectName:"explorationFNCost";Accessible.name:"False negative maliyeti";visible:noveltyChoice.visible;text:"1";Layout.fillWidth:true;onTextChanged:unsupervised.invalidate() }
    UiLabel { text:"LOF outlier negative_outlier_factor_ kullanır; novelty score_samples yalnız eğitimde olmayan kayıtlara uygulanır. Skorlar yöntemler arasında aynı ölçekte değildir; büyük değer daha sıra dışıdır. Novelty eğitim kayıtları skorlanmaz. Contamination eşik varsayımıdır; SVM nu gerçek anomali oranı değildir. Robust covariance tam rank ve elliptical dağılım gerektirir.";visible:noveltyChoice.visible;Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiButton { visible: false; objectName:"explorationHelp";text:"Yoğunluk, soft membership, novelty ve stabiliteyi öğren";helpContext:"exploration";onClicked:panel.helpRequested(this,"exploration") }
    UiButton { objectName:"explorationPreflight";text:"Hesap maliyetini önkontrol et";enabled:!unsupervised.busy;onClicked:unsupervised.preflight(JSON.stringify(panel.spec())) }
    UiLabel { objectName:"explorationCost";text:JSON.stringify(unsupervised.costPreview);Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiLabel { text:"Ölçümleri açıkça seçin (en fazla 20). Bu başlangıç yolu sayısal ölçümler içindir; kimlik, nominal/ordinal kategori, tarih ve metin desteklenmez. Kategoriyi 1/2/3 diye kodlamak geçerli uzaklık oluşturmaz. One-hot da ağırlık/boyut etkisini değiştirir; karma kategori uzaklığı bu fazda sunulmaz. Eksik/NaN/inf seçili ölçümler reddedilir; sessiz doldurma veya kayıt dışlama yapılmaz.";Layout.fillWidth:true;wrapMode:Text.Wrap;color:Theme.secondary }
    Repeater { model:unsupervised.columns
        UiCheckBox { required property var modelData;objectName:"unsupervisedFeature_"+modelData.name;text:modelData.name+" · "+modelData.physical_type+(modelData.identifier_candidate?" · kimlik adayı":"");Layout.fillWidth:true;checked:panel.chosenFeatures.indexOf(modelData.id)>=0
            onClicked:{let values=panel.chosenFeatures.slice();let at=values.indexOf(modelData.id);if(checked&&at<0)values.push(modelData.id);if(!checked&&at>=0)values.splice(at,1);panel.chosenFeatures=values;unsupervised.invalidate()}
        }
    }
    UiLabel { text:"Standardizasyon: her ölçümün ortalamasını çıkarıp standart sapmasına böler. Büyük birimler uzaklığı tek başına yönetmesin. Ölçekleme kapalıysa kaynak birimleri baskın olabilir. Ölçek seçimi keşfedilen grupları değiştirebilir. IQR kendi sütununun kaynak biriminde çalışır.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiCombo { accessibleLabel: "Ölçekleme yöntemi"; id:scaleChoice;objectName:"unsupervisedScaling";model:["Standardizasyon — tam fit kapsamında öğrenilir","Ölçekleme yok — kaynak birimleri"];enabled:panel.method!=="iqr";Layout.fillWidth:true;onCurrentIndexChanged:unsupervised.invalidate() }
    UiLabel { text:"Seed — KMeans/GMM/IsolationForest/robust covariance başlangıcı, novelty ayrımı ve stabilite örnekleri.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiTextField { id:seed;objectName:"unsupervisedSeed";text:"42";maximumLength:10;Layout.fillWidth:true;onTextChanged:unsupervised.invalidate();Accessible.name:qsTr("Seed") }
    UiLabel { visible:["kmeans","agglomerative","gmm"].indexOf(panel.method)>=0;text:"Küme sayısı (1–20): kaç merkeze ayıracağınızı seçersiniz; doğal/gerçek sınıf sayısı garantisi değildir. Tek kümede silhouette hesaplanmaz. KMeans tek fit: 100.000; diğer yöntem/karşılaştırma/stabilite: 3.000 kayıt.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiTextField { id:k;objectName:"unsupervisedClusters";visible:["kmeans","agglomerative","gmm"].indexOf(panel.method)>=0;text:"3";maximumLength:2;Layout.fillWidth:true;onTextChanged:unsupervised.invalidate();Accessible.name:"Küme sayısı" }
    UiLabel { visible:panel.method==="dbscan";text:"eps: seçilen ölçekli uzayda Öklid komşuluk yarıçapı. min_samples: noktanın kendisi dahil yoğun çekirdek için gereken komşu sayısı. eps küçüldükçe daha fazla gürültü olabilir. Küme sayısı önceden verilmez. En fazla 3.000 kayıt; yoğun komşuluk belleği sınırlıdır.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiTextField { id:eps;objectName:"unsupervisedEps";visible:panel.method==="dbscan";text:"0.5";maximumLength:16;Layout.fillWidth:true;onTextChanged:unsupervised.invalidate();Accessible.name:"DBSCAN mesafe eps" }
    UiTextField { id:neighbors;objectName:"unsupervisedNeighbors";visible:["dbscan","optics","hdbscan","lof"].indexOf(panel.method)>=0;text:"5";maximumLength:3;Layout.fillWidth:true;onTextChanged:unsupervised.invalidate();Accessible.name:"DBSCAN minimum komşu" }
    UiLabel { visible:panel.method==="isolation_forest";text:"IsolationForest skoru = negatif score_samples; büyük skor daha sıra dışı demektir, hata olasılığı değildir. Aday oranı eşik seçme varsayımıdır; gerçek anomali oranı değildir. Eşiğe eşit kayıt işaretlenmez. En fazla 100.000 kayıt.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiCombo { accessibleLabel: "Anomali eşiği"; id:thresholdMode;objectName:"unsupervisedThresholdMode";visible:panel.method==="isolation_forest";model:["Aday oranından eşik","Açık skor eşiği"];Layout.fillWidth:true;onCurrentIndexChanged:unsupervised.invalidate() }
    UiTextField { id:fraction;objectName:"unsupervisedFraction";visible:(!panel.clustering&&panel.method!=="iqr")&&thresholdMode.currentIndex===0;text:"0.05";maximumLength:16;Layout.fillWidth:true;onTextChanged:unsupervised.invalidate();Accessible.name:"Anomali aday oranı (0, 0.5]" }
    UiTextField { id:threshold;objectName:"unsupervisedThreshold";visible:panel.method==="isolation_forest"&&thresholdMode.currentIndex===1;text:"0.6";maximumLength:16;Layout.fillWidth:true;onTextChanged:unsupervised.invalidate();Accessible.name:"Anomali skor eşiği (0, 1]" }
    UiLabel { visible:panel.method==="iqr";text:"Tek ölçüm seçin. Alt sınır Q1 − çarpan × IQR; üst sınır Q3 + çarpan × IQR. Varsayılan çarpan 1.5; büyük çarpan daha geniş sınır demektir. Skor, sınır dışındaki kaynak birimi uzaklığıdır; >0 aday. IQR sıfırsa eşit sınırların dışı adaydır. Sınır üstündeki kayıt aday değildir.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiTextField { id:multiplier;objectName:"unsupervisedMultiplier";visible:panel.method==="iqr";text:"1.5";maximumLength:16;Layout.fillWidth:true;onTextChanged:unsupervised.invalidate();Accessible.name:"IQR çarpanı" }
    UiButton { objectName:"unsupervisedRun";text:panel.clustering?"Kümeleri hesapla":"Anomali adaylarını hesapla";primary:true;tone:"violet";Layout.fillWidth:true;multiline:true;enabled:!projects.busy&&!projects.readOnly&&panel.chosenFeatures.length>0;onClicked:unsupervised.create(JSON.stringify(panel.spec())) }
    Flow { Layout.fillWidth:true;spacing:Theme.sm
        UiButton { visible: false; text:"Küme nedir?";helpContext:"unsupervised.cluster";tone:"mint";onClicked:panel.helpRequested(this,helpContext) }
        UiButton { visible: false; text:"Uzaklık ve ölçek";helpContext:"unsupervised.distance";tone:"mint";onClicked:panel.helpRequested(this,helpContext) }
        UiButton { visible: false; text:"Gürültü noktası";helpContext:"unsupervised.noise";tone:"mint";onClicked:panel.helpRequested(this,helpContext) }
        UiButton { visible: false; text:"Anomali skoru";helpContext:"unsupervised.score";tone:"mint";onClicked:panel.helpRequested(this,helpContext) }
        UiButton { visible: false; text:"Etiketsiz değerlendirme";helpContext:"unsupervised.evaluation";tone:"mint";onClicked:panel.helpRequested(this,helpContext) }
        UiButton { text:qsTr("İptal");visible:unsupervised.busy;onClicked:unsupervised.cancel() }
    }
    StateNotice { Layout.fillWidth:true;kind:unsupervised.errorText?"error":unsupervised.busy?"loading":"info";heading:"Etiketsiz analiz durumu";detail:unsupervised.errorText||unsupervised.message }
    ColumnLayout { visible:!!unsupervised.report.schema;Layout.fillWidth:true;spacing:Theme.md
        UiLabel { objectName:"unsupervisedSummary";text:(unsupervised.current?"Güncel hesap":"Kayıtlı/eski hesap: kaynak/ayar sürümünü inceleyin")+"\nYöntem: "+(unsupervised.report.spec?unsupervised.report.spec.method:"")+" · tam fit: "+(unsupervised.report.rows||0)+" kayıt\nVeri sürümü: "+(unsupervised.report.dataset_version||"")+"\nSeed: "+(unsupervised.report.spec?unsupervised.report.spec.seed:"")+"\n"+(unsupervised.report.warning||"");Layout.fillWidth:true;wrapMode:Text.Wrap;font.bold:true }
        UiLabel { objectName:"unsupervisedPrediction";text:unsupervised.report.new_data?unsupervised.report.new_data.reason:"";Layout.fillWidth:true;wrapMode:Text.Wrap;color:Theme.warning }
        UiLabel { objectName:"unsupervisedSilhouette";visible:!!unsupervised.report.silhouette;text:unsupervised.report.silhouette?(unsupervised.report.silhouette.status==="valid"?"Silhouette: "+Number(unsupervised.report.silhouette.value).toFixed(4):"Silhouette hesaplanmadı")+" · "+unsupervised.report.silhouette.reason+"\nGürültü dışlanan: "+unsupervised.report.silhouette.noise_excluded+" · kapsam: "+unsupervised.report.silhouette.used_rows:"";Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiLabel { objectName:"unsupervisedScore";visible:!!unsupervised.report.score_direction;text:"Aday: "+(unsupervised.report.flagged_count||0)+" · eşik: "+unsupervised.report.threshold+" · skor > eşik\n"+(unsupervised.report.score_units||"")+"\nBüyük skor daha sıra dışı; aday işareti kesin veri hatası değildir. Değerlendirme kapsamı aşağıdaki rapordadır.";Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiLabel { objectName:"explorationEvaluation";text:JSON.stringify(unsupervised.report.evaluation||{});Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiLabel { text:"Karşılaştırma: aynı kayıtlar ve ölçek; iç metrikler gerçek küme sayısını kanıtlamaz. Stabilite: %80 kayıt, her örnekte scaler yeniden fit; ARI ortak gürültü olmayan kayıtlar içindir. Soft membership model olasılığıdır, gerçek sınıf kanıtı değildir.";visible:panel.clustering;Layout.fillWidth:true;wrapMode:Text.Wrap }
        Repeater { model:(unsupervised.report.method_state||{}).comparison||[]
            UiLabel { required property var modelData;text:modelData.method+" · "+JSON.stringify(modelData.metrics)+" · AIC: "+modelData.aic+" · BIC: "+modelData.bic+" · stability: "+JSON.stringify(modelData.stability.map(s=>({status:s.status,adjusted_rand:s.adjusted_rand,noise_agreement:s.noise_agreement,non_noise_overlap:s.non_noise_overlap,reason:s.reason})));Layout.fillWidth:true;wrapMode:Text.Wrap }
        }
        UiLabel { objectName:"explorationState";text:JSON.stringify({mode:(unsupervised.report.method_state||{}).mode,score_origin:(unsupervised.report.method_state||{}).score_origin,score_geometry:(unsupervised.report.method_state||{}).score_geometry,metric:(unsupervised.report.method_state||{}).metric,linkage:(unsupervised.report.method_state||{}).linkage,covariance_type:(unsupervised.report.method_state||{}).covariance_type,soft_membership_examples:((unsupervised.report.method_state||{}).soft_membership||[]).slice(0,5),membership_strength_examples:((unsupervised.report.method_state||{}).membership_strength||[]).slice(0,5),training_rows:((unsupervised.report.method_state||{}).training_indices||[]).length,scored_rows:((unsupervised.report.method_state||{}).scored_indices||[]).length});Layout.fillWidth:true;wrapMode:Text.Wrap }
        Image { objectName:"explorationDendrogram";readonly property bool imageReady:status===Image.Ready;visible:unsupervised.treeImage!=="";source:unsupervised.treeImage;sourceSize.width:900;sourceSize.height:350;Layout.fillWidth:true;Layout.preferredHeight:350;fillMode:Image.PreserveAspectFit }
        Repeater { model:unsupervised.report.profiles||[]
            ColumnLayout { required property var modelData;Layout.fillWidth:true
                UiLabel { text:modelData.name+" · "+modelData.count+" kayıt";font.bold:true;Layout.fillWidth:true;wrapMode:Text.Wrap }
                Repeater { model:modelData.measurements;UiLabel { required property var modelData;text:modelData.name+" · kaynak biriminde ortalama: "+modelData.mean+" · min: "+modelData.min+" · max: "+modelData.max;Layout.fillWidth:true;wrapMode:Text.Wrap } }
                Repeater { model:modelData.examples;UiLabel { required property var modelData;text:"Örnek RowId: "+modelData.row_id+" · "+JSON.stringify(modelData.values)+(typeof modelData.score==="number"?" · skor: "+modelData.score:"");color:Theme.secondary;Layout.fillWidth:true;wrapMode:Text.Wrap } }
            }
        }
        UiLabel { text:"Profiller tüm kayıtlardan; her grupta ilk 5 gerçek kayıt örnektir. Boyut indirgeme/projeksiyon kullanılmadı. Sonuç ve parametreler otomatik projeye kaydedildi.";Layout.fillWidth:true;wrapMode:Text.Wrap;color:Theme.secondary }
        UiButton { objectName:"unsupervisedTransfer";text:"Tüm kayıtları koruyarak işaretli yeni dataset oluştur";tone:"cyan";multiline:true;Layout.fillWidth:true;enabled:unsupervised.current&&!projects.busy&&!projects.readOnly;onClicked:unsupervised.transfer() }
    }
    UiCombo { accessibleLabel: "Kayıtlı etiketsiz analiz"; id:saved;objectName:"unsupervisedSaved";model:unsupervised.savedRuns;textRole:"label";valueRole:"id";Layout.fillWidth:true;Layout.minimumWidth:0 }
    UiButton { objectName:"unsupervisedOpen";text:"Kayıtlı etiketsiz sonucu aç";enabled:saved.currentIndex>=0&&!projects.busy;onClicked:unsupervised.openSaved(saved.currentValue) }
}
