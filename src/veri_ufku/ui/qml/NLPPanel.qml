import QtQuick
import QtQuick.Layouts
ColumnLayout {
    id:panel
    objectName:"nlpPanel"
    signal helpRequested(var origin,string context)
    property bool enabledMode: expanded.checked
    property var report:textAnalysis.report.advanced||{}
    function select(id){expanded.checked=true;for(let i=0;i<method.count;i++)if(method.model[i].id===id)method.currentIndex=i}
    function config(){return {operation:method.currentValue||"nmf",topics:Number(topics.text),seed:Number(seed.text),model_folder:folder.text,query:query.text,top_k:Number(topk.text),partitions:JSON.parse(partitions.text),document_labels:JSON.parse(documentLabels.text),entity_labels:JSON.parse(entityLabels.text),annotations:JSON.parse(annotations.text),relevance:JSON.parse(relevance.text)}}
    function restore(s){if(!s){expanded.checked=false;return}panel.select(s.operation);topics.text=String(s.topics);seed.text=String(s.seed);folder.text=s.model_folder;query.text=s.query;topk.text=String(s.top_k);partitions.text=JSON.stringify(s.partitions);documentLabels.text=JSON.stringify(s.document_labels);entityLabels.text=JSON.stringify(s.entity_labels);annotations.text=JSON.stringify(s.annotations);relevance.text=JSON.stringify(s.relevance)}
    function summary(a){let out={document_count:(a.source_documents||[]).length};for(let k of ["status","operation","model_meta","test_withheld","notes","metrics","active_learning","revision_id","revisions"])out[k]=a[k];out.fit=a.fit?{fit_row_ids:a.fit.fit_row_ids,vocabulary:a.fit.vocabulary,fit_scope:a.fit.fit_scope,backend:a.fit.backend}:null;return JSON.stringify(out,null,2)}
    Connections {target:textAnalysis;function onSelectNLP(id){panel.select(id)}function onModelSelected(path){folder.text=path;textAnalysis.invalidate()}}
    UiCheckBox {id:expanded;objectName:"nlpEnabled";text:"Faz55 · ileri yerel metin";property string helpContext:"nlp.models";onToggled:textAnalysis.invalidate()}
    ColumnLayout {visible:panel.enabledMode;Layout.fillWidth:true
        UiCombo {id:method;objectName:"nlpMethod";model:textAnalysis.nlpMethods();textRole:"label";valueRole:"id";accessibleLabel:"NLP adapter";Layout.fillWidth:true;onActivated:textAnalysis.invalidate()}
        UiLabel {text:"NMF TF-IDF, LDA raw count: yalnız train corpus vocabulary/model fit. Topic gerçek sınıf değildir; adları insan düzenler. Yerel modeller: static mean word vectors, literal gazetteer NER, linear sentiment scores; transformer/spaCy/ONNX yok. Türkçe model dili beyanı kalite garantisi değildir.500rows/500000chars,8topics,16MiB model.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiTextField {id:topics;objectName:"nlpTopics";text:"2";Accessible.name:"NLP topic count2..8";Layout.fillWidth:true;onTextEdited:textAnalysis.invalidate()}
        UiTextField {id:seed;objectName:"nlpSeed";text:"55";Accessible.name:"NLP seed";Layout.fillWidth:true;onTextEdited:textAnalysis.invalidate()}
        UiTextField {id:folder;objectName:"nlpFolder";text:"";Accessible.name:"Yerel model klasörü, model.json";Layout.fillWidth:true;onTextEdited:textAnalysis.invalidate()}
        UiButton {objectName:"nlpInspectModel";text:"Yerel model/cache boyut, hash ve lisansını incele";enabled:!textAnalysis.busy;onClicked:textAnalysis.inspectModel(folder.text)}
        UiLabel {text:JSON.stringify(textAnalysis.modelInfo,null,2);wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiTextField {id:url;objectName:"nlpDownloadURL";text:"";Accessible.name:"Public HTTPS model URL, auth/query yok";Layout.fillWidth:true}
        UiTextField {id:hash;objectName:"nlpDownloadHash";text:"";Accessible.name:"Beklenen model SHA256";Layout.fillWidth:true}
        UiTextField {id:bytes;objectName:"nlpDownloadSize";text:"0";Accessible.name:"İndirme boyutu exact bytes max16MiB";Layout.fillWidth:true}
        UiLabel {text:"İndirme açık kullanıcı eylemi: public HTTPS only, TLS verified, exact size+SHA256, aynı origin en fazla3 redirect. Auth/private hub/token desteklenmez. Yayıncının model/dataset lisansını ve kullanım koşullarını inceleyin; bundle içindeki training/license beyanı doğrulanmış kalite değildir. Kaydedilmiş sonuç açılışı ağ veya dış model klasörü okumaz.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiButton {objectName:"nlpDownload";text:"Belirtilen boyut/hash ile modeli indir";enabled:!textAnalysis.busy;onClicked:textAnalysis.downloadModel(url.text,hash.text,Number(bytes.text))}
        UiTextField {id:query;objectName:"nlpQuery";text:"";Accessible.name:"Semantic search query";Layout.fillWidth:true;onTextEdited:textAnalysis.invalidate()}
        UiTextField {id:topk;objectName:"nlpTopK";text:"10";Accessible.name:"Search/active top k";Layout.fillWidth:true;onTextEdited:textAnalysis.invalidate()}
        UiTextArea {id:partitions;objectName:"nlpPartitions";text:"{}";Accessible.name:"RowId train validation test JSON, boş exploratory train";Layout.fillWidth:true;Layout.preferredHeight:70;onTextChanged:textAnalysis.invalidate()}
        UiTextField {id:documentLabels;objectName:"nlpDocumentLabels";text:'["negative","positive"]';Accessible.name:"Document label schema JSON";Layout.fillWidth:true;onTextEdited:textAnalysis.invalidate()}
        UiTextField {id:entityLabels;objectName:"nlpEntityLabels";text:'["PER","LOC","ORG"]';Accessible.name:"Entity label schema JSON";Layout.fillWidth:true;onTextEdited:textAnalysis.invalidate()}
        UiTextArea {id:annotations;objectName:"nlpAnnotations";text:"[]";Accessible.name:"Human approved/rejected annotations row_id label spans reviewer decision JSON";Layout.fillWidth:true;Layout.preferredHeight:90;onTextChanged:textAnalysis.invalidate()}
        UiTextArea {id:relevance;objectName:"nlpRelevance";text:"{}";Accessible.name:"Gerçek query relevance judgments RowId0..3 JSON";Layout.fillWidth:true;Layout.preferredHeight:70;onTextChanged:textAnalysis.invalidate()}
        UiLabel {text:"NER offset original Unicode codepoint [start,end), ayrıca Qt UTF16 offset; normalizasyon offset'e uygulanmaz. Raw preview ayrı açık checkbox ister. Cosine kalibre probability değildir; static pooling sıra/negation/context kaybeder. Pretrained output öneridir, ground truth olamaz. Active-learning yalnız train unlabeled pool; test labels seçim/fit dışında. Relevance yoksa retrieval başarı metriği yok. Aynı metin farklı splitlerde reddedilir.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiButton { visible: false;objectName:"nlpHelp";property string helpContext:"nlp.models";text:"Topic, embedding, model dili ve annotation yardımı";onClicked:panel.helpRequested(this,"nlp.models")}
        UiButton {objectName:"nlpRun";text:"NLP adapteri doğrula ve hesapla";primary:true;Layout.fillWidth:true;enabled:!textAnalysis.busy&&!projects.busy&&!projects.readOnly;onClicked:{try{textAnalysis.create(JSON.stringify(panel.parent.spec()))}catch(e){error.text="JSON/sayısal alanları kontrol edin"}}}
        UiLabel {id:error;text:"";Layout.fillWidth:true;wrapMode:Text.Wrap;color:Theme.warning}
    }
    ColumnLayout {visible:panel.report.schema==="NLPRun/v1";Layout.fillWidth:true
        UiLabel {objectName:"nlpReport";text:panel.summary(panel.report);wrapMode:Text.Wrap;Layout.fillWidth:true}
        Repeater {model:panel.report.topics||[];UiLabel {required property var modelData;text:"Topic "+modelData.topic+" · ad="+(modelData.name||"insan adı bekleniyor")+" · "+modelData.terms.join(" | ");wrapMode:Text.Wrap;Layout.fillWidth:true}}
        UiLabel {text:"NER (model suggestion, ground truth=false): "+JSON.stringify(panel.report.entities||[]);wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiLabel {text:"Search cosine: "+JSON.stringify(panel.report.search_results||[]);wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiLabel {text:"Classification/sentiment: "+JSON.stringify(panel.report.predictions||[]);wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiTextField {id:reviewer;objectName:"nlpReviewer";text:"";Accessible.name:"Human reviewer kimliği";Layout.fillWidth:true}
        UiTextArea {id:patch;objectName:"nlpReviewPatch";text:"{}";Accessible.name:"Versioned topic_names veya annotations review patch JSON";Layout.fillWidth:true;Layout.preferredHeight:90}
        UiButton {objectName:"nlpReview";text:"İnsan kararını yeni revision olarak kaydet";enabled:textAnalysis.current&&!textAnalysis.busy&&!projects.readOnly;onClicked:textAnalysis.reviewNLP(patch.text,reviewer.text,panel.report.revision_id)}
        UiTextField {id:exportPath;objectName:"nlpExportPath";text:"";Accessible.name:"Annotation JSON yeni dosya yolu";Layout.fillWidth:true}
        UiCheckBox {id:exportRaw;objectName:"nlpExportRaw";text:"Exporta ham metni açıkça dahil et"}
        UiButton {objectName:"nlpExport";text:"Label schema/split/offset/revision export et";enabled:textAnalysis.current&&!textAnalysis.busy;onClicked:textAnalysis.exportNLP(exportPath.text,exportRaw.checked)}
    }
}
