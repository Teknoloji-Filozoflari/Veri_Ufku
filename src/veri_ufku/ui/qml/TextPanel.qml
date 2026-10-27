import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ColumnLayout {
    id:panel
    objectName:"textPanel"
    signal helpRequested(var origin,string context)
    spacing:Theme.md
    function spec(){let s=options.spec(column.currentValue||"");s.preview=preview.checked;s.similarity=similarity.checked;if(nlp.enabledMode)s.advanced=nlp.config();return s}
    Connections { target:textAnalysis;function onRestoreRequested(value){nlp.restore(JSON.parse(value).advanced);let s=JSON.parse(value);options.restore(s);preview.checked=false;similarity.checked=s.similarity;for(let i=0;i<column.count;i++)if(column.valueAt(i)===s.column)column.currentIndex=i} }
    UiLabel { text:"Yerel metin incelemesi";font.pixelSize:Theme.heading;Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiLabel { text:nlp.enabledMode?"İleri NLP: training pool, model dili/lisansı, review ve offset sınırlarını aşağıdan seç. Kaynak değiştirilmez.":"Serbest metni açık token/dil seçimiyle incele. Sonuçlar seçili veri sürümünün tamamını betimler; bu inceleme vocab'ı sınıflandırma eğitimine taşınmaz. Kaynak değiştirilmez. Embedding, dış API, otomatik duygu/konu etiketi yok.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiCombo { accessibleLabel: "Metin sütunu"; id:column;objectName:"textColumn";model:textAnalysis.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true;onActivated:textAnalysis.invalidate() }
    TextOptions { id:options;Layout.fillWidth:true;onEdited:textAnalysis.invalidate() }
    UiCheckBox { id:preview;objectName:"textPreviewConsent";text:"Hassas içerik içerebilir: ilk5 ham metni (200 karakter) ekranda önce/sonra göster. Log veya sonuç kaydına alınmaz.";Layout.fillWidth:true;onClicked:textAnalysis.invalidate() }
    UiCheckBox { id:similarity;objectName:"textSimilarity";text:"Ayrı seçenek: TF-IDF kosinüs benzerliği (en fazla1000 belge, en yüksek30 pozitif çift)";Layout.fillWidth:true;onClicked:textAnalysis.invalidate() }
    UiLabel { text:"Uzunluk normalizasyon öncesi Unicode kod noktasıdır; bayt veya görünen harf sayısı değildir. En fazla100000 belge, belge başına10000 karakter/3000 token, toplam10 milyon karakter. TF-IDF: (1+log((1+N)/(1+df))) × token sayısı; belge vektörü L2 normalize edilir.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiButton { objectName:"textRun";text:"Metni yerel incele";primary:true;enabled:!textAnalysis.busy&&!projects.busy&&!projects.readOnly;onClicked:textAnalysis.create(JSON.stringify(panel.spec())) }
    UiButton { objectName:"textCancel";text:qsTr("İptal");visible:textAnalysis.busy;onClicked:textAnalysis.cancel() }
    StateNotice { kind:textAnalysis.errorText?"error":textAnalysis.busy?"loading":"info";heading:"Metin inceleme durumu";detail:textAnalysis.errorText||textAnalysis.message;Layout.fillWidth:true }
    UiLabel { visible:!!textAnalysis.report.schema&&!textAnalysis.report.advanced;text:(textAnalysis.current?"Güncel":"Eski veri/ayar sonucu")+" · "+textAnalysis.report.rows+" belge · null="+textAnalysis.report.null_text+" · boş="+textAnalysis.report.empty_text+" · yalnız boşluk="+textAnalysis.report.whitespace_text+" · token kalmayan="+textAnalysis.report.empty_after+" · aday vocab="+textAnalysis.report.candidate_vocab+" · tutulan="+textAnalysis.report.retained_vocab;Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiLabel { visible:!!textAnalysis.report.length;text:textAnalysis.report.length?"Ham uzunluk min/max/ortalama: "+textAnalysis.report.length.minimum+" / "+textAnalysis.report.length.maximum+" / "+(textAnalysis.report.length.mean===null?"Tanımsız":Number(textAnalysis.report.length.mean).toPrecision(5)):"";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiLabel { text:textAnalysis.report.warning||"";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiLabel { text:"Frekans tablosu — en yüksek100 terim; sayı tüm kolon üzerindedir";font.bold:true;Layout.fillWidth:true;wrapMode:Text.Wrap }
    Repeater { model:textAnalysis.report.frequencies||[];delegate:RowLayout { required property var modelData;Layout.fillWidth:true;UiLabel { text:modelData.term;Layout.fillWidth:true;wrapMode:Text.Wrap } UiLabel { text:modelData.count+" kez · "+modelData.document_count+" belge" } } }
    TextFrequencyPlot { objectName:"textFrequencyGraph";points:(textAnalysis.report.frequencies||[]).slice(0,15);Layout.fillWidth:true;Layout.preferredHeight:250 }
    UiLabel { text:"TF-IDF incelemesi — en yüksek100 ortalama ağırlık. Sık sözcük her zaman ayırt edici değildir.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    Repeater { model:textAnalysis.report.tfidf||[];delegate:UiLabel { required property var modelData;text:modelData.term+": IDF="+Number(modelData.idf).toPrecision(5)+" · ortalama L2 ağırlık="+Number(modelData.mean_weight).toPrecision(5);Layout.fillWidth:true;wrapMode:Text.Wrap } }
    Repeater { model:preview.checked?(textAnalysis.report.previews||[]):[];delegate:UiLabel { required property var modelData;text:"Önce: "+modelData.before+"\nNormalize: "+modelData.normalized+"\nSonra token: "+modelData.tokens.join(" | ");Layout.fillWidth:true;wrapMode:Text.Wrap } }
    UiLabel { text:"Yerleşik önce/sonra örneği: ‘IŞIK ve İSTANBUL’ → Türkçe küçük harf+Türkçe stopword: ‘ışık | istanbul’. ‘ç’ ve ‘c’ ayrıdır; NFC ‘c + ◌̧’ ile ‘ç’yi eşler. NFKC ‘Ａ’ ile ‘A’yı eşler. Dil değişikliği anlam/kök/duygu çıkarmaz.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    Repeater { model:textAnalysis.report.similarities||[];delegate:UiLabel { required property var modelData;text:modelData.left+" ↔ "+modelData.right+" · kosinüs="+Number(modelData.cosine).toPrecision(5);Layout.fillWidth:true;wrapMode:Text.Wrap } }
    UiLabel { text:"Etiketli metin: Model → Kayıt bazlı modelleme → Kategori hedefi → Metin TF-IDF seçimini aç. Aynı dil/token ayarlarını seç; önce uygunluk planı, sonra mevcut sınıflandırma ve final test akışını kullan. Vocab/IDF her eğitim fold'unda öğrenilir; ham boş belgeler sıfır vektördür, tümü boş eğitim kontrollü reddedilir.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    NLPPanel { id:nlp; Layout.fillWidth:true; onHelpRequested:function(origin,context){panel.helpRequested(origin,context)} }
    Flow { Layout.fillWidth:true;spacing:Theme.sm
        UiButton { visible: false; text:"Token ve n-gram";helpContext:"text.tokens";onClicked:panel.helpRequested(this,helpContext) }
        UiButton { visible: false; text:"Durak sözcük ve dil";helpContext:"text.language";onClicked:panel.helpRequested(this,helpContext) }
        UiButton { visible: false; text:"TF-IDF";helpContext:"text.tfidf";onClicked:panel.helpRequested(this,helpContext) }
        UiButton { visible: false; text:"Benzerlik";helpContext:"text.similarity";onClicked:panel.helpRequested(this,helpContext) }
    }
    UiCombo { accessibleLabel: "Kayıtlı metin analizi"; id:saved;model:textAnalysis.savedRuns;textRole:"label";valueRole:"id";Layout.fillWidth:true }
    UiButton { text:"Kayıtlı metin özetini aç";enabled:saved.currentIndex>=0&&!textAnalysis.busy&&!projects.busy;onClicked:textAnalysis.openSaved(saved.currentValue) }
}
