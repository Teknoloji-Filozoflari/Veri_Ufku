import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id:panel
    objectName:"recommendationPanel"
    property string helpContext:"model.recommendation"
    signal helpRequested(var origin,string context)
    readonly property var result:recommendationAnalysis.historyReport
    readonly property var tasks:["popularity","content","factorization","ranker"]
    function cid(combo){return combo.currentValue||""}
    function config(){return {task:tasks[task.currentIndex],feedback:feedback.currentIndex===0?"implicit":"explicit",user:cid(user),item:cid(item),value:cid(value),time:cid(time),query:cid(query),features:features.text.split(",").map(function(x){return x.trim()}).filter(function(x){return !!x}),split:split.currentIndex===0?"temporal":"leave_last_out",cutoff:Number(cutoff.text),k:Number(k.text),candidates:candidates.currentIndex===0?"full":"sampled",negatives:Number(negatives.text),seen_filter:task.currentIndex===3?false:seen.checked,rating_min:Number(ratingMin.text),rating_max:Number(ratingMax.text),relevant_rating:Number(relevance.text),factors:Number(factors.text),epochs:Number(epochs.text),regularization:Number(reg.text),alpha:Number(alpha.text),seed:Number(seed.text)}}
    function label(value){try{var v=JSON.parse(value);return String(v[1])+" ("+v[0]+")"}catch(e){return String(value)}}
    function fmt(value){return typeof value==="number"?value.toFixed(4):"hesaplanamaz"}
    function metricLine(m){return "Precision@K="+fmt(m.precision)+" · Recall@K="+fmt(m.recall)+" · NDCG@K="+fmt(m.ndcg)+" · MAP/AP@K="+fmt(m.ap)}
    function summary(){var r=panel.result,m=r.metrics||{};return r.status?r.status+" · "+((r.recommendation_spec||{}).task||"")+" · K="+(m.k||"—")+" · "+(m.candidate_protocol||"—")+"\n"+metricLine(m)+"\nQuery n="+(m.n_queries||0)+" · relevant query n="+(m.n_relevant_queries||0)+" · coverage="+fmt(m.catalog_coverage)+" · diversity="+fmt(m.diversity)+"\nCold user query="+(m.cold_user_queries||0)+" · cold item relevant="+(m.cold_item_relevant||0)+" · seen relevant="+(m.seen_relevant||0)+"\nÖnceki final test kullanımları: "+(r.prior_test_use_ids||[]).length:"Henüz öneri run yok"}
    function predictionText(){var p=recommendationAnalysis.predictionReport;if(!p.schema)return "";return p.schema+" · as-of="+p.as_of+" · fit yok\nKullanıcı: "+label(p.user)+" · "+p.candidate_protocol+" · seen filter="+p.seen_filter+"\n"+p.recommendations.map(function(r,i){return (i+1)+". "+label(r.item)+" · puan="+fmt(r.score)+" · "+r.reason+" · kaynak kayıt n="+r.source_records.length}).join("\n")}
    Connections {target:recommendationAnalysis;function onSelectRecommendation(value){expanded.checked=true;task.currentIndex=panel.tasks.indexOf(value)}}
    UiCheckBox {id:expanded;objectName:"recommendationExpanded";text:"Faz59 yerel öneri ve query ranking alanını göster";Layout.fillWidth:true}
    ColumnLayout {visible:expanded.checked;Layout.fillWidth:true;spacing:Theme.sm
        UiLabel {text:"Öneri listesi · geçmiş katalog · zaman sınırı";font.bold:true;Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiLabel {text:"Önce user/item/value/time kolonlu tabloyu veri ekranından içe aktarın. Time sayısal Unix seconds olmalı; birim dönüşümü otomatik yapılmaz. En çok2000kayıt/32user/128item/16feature/64query. Kimlik tipi korunur: string001 ile integer1 farklıdır. Kaynakta değişiklik yapılmaz.";Layout.fillWidth:true;wrapMode:Text.Wrap}
        ColumnLayout {enabled:!recommendationAnalysis.busy;Layout.fillWidth:true
            UiCombo {id:task;objectName:"recommendationTask";accessibleLabel:"Öneri yöntemi";model:["Popularity baseline","Content cosine similarity","Matrix factorization — ALS","Learning-to-rank — ayrı query/group pairwise"];Layout.fillWidth:true}
            UiCombo {id:feedback;objectName:"recommendationFeedback";accessibleLabel:"Implicit event veya explicit rating";model:["Implicit pozitif event strength","Explicit gözlenmiş rating"];Layout.fillWidth:true}
            UiLabel {text:"Roller: kullanıcı, ürün, değer ve zaman. LTR'de değer graded relevance0..100; query tek kullanıcı/tek timestamp ve unique candidate item grubu. LTR sıradan classification değildir; yalnız temporal + tam beyan edilmiş query candidate kümesi.";Layout.fillWidth:true;wrapMode:Text.Wrap}
            UiCombo {id:user;objectName:"recommendationUser";accessibleLabel:"User kimlik kolonu";model:recommendationAnalysis.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true}
            UiCombo {id:item;objectName:"recommendationItem";accessibleLabel:"Item kimlik kolonu";model:recommendationAnalysis.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true}
            UiCombo {id:value;objectName:"recommendationValue";accessibleLabel:"Event strength rating veya relevance kolonu";model:recommendationAnalysis.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true}
            UiCombo {id:time;objectName:"recommendationTime";accessibleLabel:"Unix seconds zaman kolonu";model:recommendationAnalysis.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true}
            UiCombo {id:query;objectName:"recommendationQuery";accessibleLabel:"LTR query group kolonu";model:recommendationAnalysis.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true}
            UiLabel {text:"Content/LTR features: aşağıdaki ColumnId listesinden virgülle seçin; as-of mevcut, uyumlu birimlerde numeric özellikler. Content item vektörü snapshot boyunca sabit olmalı. LTR candidate özellikleri ilgili query anında mevcut olmalı; hedef/gelecek bilgi koymayın. Encoding/scaling otomatik yapılmaz.";Layout.fillWidth:true;wrapMode:Text.Wrap}
            UiLabel {text:recommendationAnalysis.columns.map(function(c){return c.name+" = "+c.id}).join("\n");Layout.fillWidth:true;wrapMode:Text.Wrap}
            UiTextField {id:features;objectName:"recommendationFeatures";Accessible.name:"Content veya LTR feature ColumnId listesi";placeholderText:"column:… , column:…";Layout.fillWidth:true}
            UiCombo {id:split;objectName:"recommendationSplit";accessibleLabel:"Öneri zaman değerlendirme planı";model:["Global temporal cutoff","Leave-last-out — son timestamp bağları birlikte"];Layout.fillWidth:true}
            UiTextField {id:cutoff;objectName:"recommendationCutoff";Accessible.name:"Temporal cutoff Unix seconds";text:"0";Layout.fillWidth:true}
            UiLabel {text:"Training her query için strict time<cutoff; bütün heldout kayıtlar bütün fitlerden çıkarılır. Leave-last-out'ta kişi son timestamp bağları birlikte. Gelecek-only ürünler katalogda yok; kaçırılan relevant olarak paydada kalır. Temporal ufuk snapshot sonuna kadar; bu geliştirme holdout'udur, final test raporu değildir.";Layout.fillWidth:true;wrapMode:Text.Wrap}
            UiCombo {id:candidates;objectName:"recommendationCandidates";accessibleLabel:"Evaluation aday evreni";model:["Tam tarihsel gözlenen katalog","Örneklenmiş aday — relevant + uniform unobserved negatives"];Layout.fillWidth:true}
            UiTextField {id:negatives;objectName:"recommendationNegatives";Accessible.name:"Sampled candidate negative sayısı";text:"20";Layout.fillWidth:true}
            UiTextField {id:k;objectName:"recommendationK";Accessible.name:"Top K liste uzunluğu";text:"5";Layout.fillWidth:true}
            UiCheckBox {id:seen;objectName:"recommendationSeen";text:task.currentIndex===3?"LTR query adaylarında seen-item filtresi uygulanmaz":"Tüm tarihsel görülen ürünleri filtrele; tekrar relevant paydada kalır";enabled:task.currentIndex!==3;checked:true;Layout.fillWidth:true}
            UiTextField {id:ratingMin;objectName:"recommendationRatingMin";Accessible.name:"Explicit rating minimum";text:"1";Layout.fillWidth:true}
            UiTextField {id:ratingMax;objectName:"recommendationRatingMax";Accessible.name:"Explicit rating maximum";text:"5";Layout.fillWidth:true}
            UiTextField {id:relevance;objectName:"recommendationRelevance";Accessible.name:"Explicit relevant rating eşiği";text:"4";Layout.fillWidth:true}
            UiTextField {id:factors;objectName:"recommendationFactors";Accessible.name:"ALS latent faktör sayısı";text:"4";Layout.fillWidth:true}
            UiTextField {id:epochs;objectName:"recommendationEpochs";Accessible.name:"ALS veya LTR epoch sayısı";text:"10";Layout.fillWidth:true}
            UiTextField {id:reg;objectName:"recommendationRegularization";Accessible.name:"ALS veya LTR regularization";text:"0.1";Layout.fillWidth:true}
            UiTextField {id:alpha;objectName:"recommendationAlpha";Accessible.name:"Implicit confidence alpha";text:"10";Layout.fillWidth:true}
            UiTextField {id:seed;objectName:"recommendationSeed";Accessible.name:"Öneri model ve sampling seed";text:"59";Layout.fillWidth:true}
            UiLabel {text:"Explicit ALS: yalnız gözlenen pair, tekrar rating için son tarihsel değer. Implicit ALS: pozitif preference ve1+alpha·strength güven; gözlenmeyen p0/c1 bir varsayımdır, gerçek dislike değildir. Popularity: pozitif/relevant unique user sayısı; content: pozitif geçmiş item vektörlerinin normalize ortalaması. Eşit skor typed ID sırasıyla çözülür.";Layout.fillWidth:true;wrapMode:Text.Wrap}
            UiButton {objectName:"recommendationRun";text:"CPU öneri değerlendirmesini başlat";primary:true;enabled:recommendationAnalysis.canRecommendationRun;onClicked:recommendationAnalysis.startRecommendation(JSON.stringify(panel.config()));Layout.fillWidth:true}
        }
        UiButton {objectName:"recommendationCancel";text:"Öneri işini iptal et";visible:recommendationAnalysis.busy;onClicked:recommendationAnalysis.cancel();Layout.fillWidth:true}
        StateNotice {heading:"Öneri hesap durumu";detail:recommendationAnalysis.errorText||recommendationAnalysis.message;kind:recommendationAnalysis.errorText?"error":recommendationAnalysis.busy?"loading":"info";Layout.fillWidth:true}
        UiLabel {objectName:"recommendationSummary";text:panel.summary();Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiCheckBox {id:technical;objectName:"recommendationTechnical";text:"Teknik kimlikleri, protokol hash ve kaynak kayıt kökenini göster";Layout.fillWidth:true}
        UiLabel {visible:technical.checked;text:JSON.stringify(panel.result.metrics||{});Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiLabel {text:"Precision paydası K (eksik slot dahil); Recall tüm relevant; AP paydası min(K,relevant); binary NDCG ideal tüm relevant. Boş relevance query recall/AP/NDCG ortalamasına girmez, n raporludur. Coverage önerilen unique / query katalog birleşimi; diversity1−cosine yalnız mevcut nonzero content ile, aksi halde unavailable. Cold user/item sayıları ayrıca raporlanır. Full/sample karşılaştırması geçersizdir.";Layout.fillWidth:true;wrapMode:Text.Wrap}
        Repeater {model:panel.result.queries||[];ColumnLayout {required property var modelData;Layout.fillWidth:true
            UiLabel {text:"Query "+panel.label(modelData.query)+" · as-of="+modelData.time+" · train="+modelData.fit_row_ids.length+" · katalog="+modelData.universe_ids.length+" · aday="+modelData.candidate_ids.length+" · "+modelData.candidate_protocol+"\n"+panel.metricLine(modelData.metrics)+"\nAynı aday popularity baseline: "+panel.metricLine(modelData.baseline)+"\nCold item="+modelData.unseen_relevant_ids.length+" · seen relevant="+modelData.seen_relevant_ids.length;Layout.fillWidth:true;wrapMode:Text.Wrap}
            Repeater {model:modelData.recommendations;UiLabel {required property var modelData;required property int index;text:(index+1)+". "+panel.label(modelData.item)+" · puan="+panel.fmt(modelData.score)+" · "+modelData.reason+" · kaynak kayıt n="+modelData.source_records.length;Layout.fillWidth:true;wrapMode:Text.Wrap}}
            UiLabel {visible:technical.checked;text:JSON.stringify(modelData.recommendations)+"\nAday hash="+modelData.candidate_hash+"\n"+modelData.negative_sampling;Layout.fillWidth:true;wrapMode:Text.Wrap}
        }}
        UiCombo {id:saved;objectName:"recommendationSaved";accessibleLabel:"Kalıcı recommendation kayıtları";model:recommendationAnalysis.savedRuns;textRole:"label";valueRole:"id";Layout.fillWidth:true}
        UiButton {objectName:"recommendationOpen";text:"Kalıcı öneri model/snapshot aç";enabled:!recommendationAnalysis.busy&&saved.currentIndex>=0;onClicked:recommendationAnalysis.openRun(saved.currentValue);Layout.fillWidth:true}
        UiLabel {text:"Yeni yerel liste: JSON {\"user\":\"u1\",\"items\":[\"i1\",\"yeni\"]}. Items boş bırakılırsa kayıtlı tarihsel katalog. Unknown user popularity; unknown item zero popularity, nedeni listede. LTR features:[{item:…,values:[…]}] zorunlu; query candidate özellikleri açık istekte. Model en son değerlendirme query zamanında fit edilen tarihsel modeldir; yeniden fit yok.";Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiTextField {id:request;objectName:"recommendationRequest";Accessible.name:"Yeni yerel öneri listesi JSON isteği";text:'{"user":"new-user"}';Layout.fillWidth:true}
        UiButton {objectName:"recommendationPredict";text:"Yerel öneri listesi üret — gönderme yok";enabled:!recommendationAnalysis.busy&&panel.result.status==="completed";onClicked:recommendationAnalysis.requestList(request.text);Layout.fillWidth:true}
        UiLabel {objectName:"recommendationPrediction";text:panel.predictionText();Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiTextField {id:destination;objectName:"recommendationDestination";Accessible.name:"Yeni öneri JSON export yolu";placeholderText:"Yeni mutlak dosya.json";Layout.fillWidth:true}
        UiCheckBox {id:ids;objectName:"recommendationExportIDs";text:"Kaynak user/item/record kimliklerini açıkça export et; hassas kimlik içerebilir";Layout.fillWidth:true}
        UiButton {objectName:"recommendationExport";text:"Öneri listesini yeni yerel JSON'a yaz";enabled:!recommendationAnalysis.busy&&!!recommendationAnalysis.predictionReport.schema;onClicked:recommendationAnalysis.exportList(destination.text,ids.checked);Layout.fillWidth:true}
        UiLabel {text:"Varsayılan export kimlikleri her dosyada farklı salted pseudonym ile maskeler; anonimlik garantisi değildir. Skor click probability değildir. Offline ranking gerçek kullanıcı faydasını kanıtlamaz. Gerçek kullanıcıya otomatik gönderim veya ağ bağlantısı yok.";color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiButton { visible: false;objectName:"recommendationHelp";text:"Implicit feedback, top-K, negative sample ve cold start öğren";helpContext:"model.recommendation";onClicked:panel.helpRequested(this,helpContext);Layout.fillWidth:true}
    }
}
