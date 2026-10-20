import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ColumnLayout {
    id:options
    signal edited()
    function spec(column) { return {column:column,language:["tr","en","other"][language.currentIndex],normalization:unicodeChoice.currentIndex===0?"NFC":"NFKC",lowercase:lowercase.checked,numbers:numbers.checked,stopwords:["none","tr","en"][stops.currentIndex],custom_stopwords:custom.text,ngram_min:Number(ngramMin.text),ngram_max:Number(ngramMax.text),max_features:Number(vocab.text),preview:false,similarity:false} }
    function restore(s) { language.currentIndex=["tr","en","other"].indexOf(s.language);unicodeChoice.currentIndex=s.normalization==="NFKC"?1:0;lowercase.checked=s.lowercase;numbers.checked=s.numbers;stops.currentIndex=["none","tr","en"].indexOf(s.stopwords);custom.text=s.custom_stopwords;ngramMin.text=String(s.ngram_min);ngramMax.text=String(s.ngram_max);vocab.text=String(s.max_features) }
    UiLabel { text:"Dil varsayımı — kullanıcı seçimi, otomatik dil tespiti yok";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiCombo { accessibleLabel: "Metin dili"; id:language;objectName:"textLanguage";model:["Türkçe — I→ı, İ→i","İngilizce — Unicode casefold","Diğer/karışık — genel Unicode; dile özel kök bulma yok"];Layout.fillWidth:true;onActivated:options.edited() }
    UiCombo { accessibleLabel: "Unicode normalizasyonu"; id:unicodeChoice;objectName:"textUnicode";model:["NFC — eşdeğer Unicode bileşimleri","NFKC — uyumluluk karakterlerini de birleştir"];Layout.fillWidth:true;onActivated:options.edited() }
    UiCheckBox { id:lowercase;objectName:"textLowercase";text:"Dil seçimine göre küçük harfe dönüştür";checked:true;onClicked:options.edited() }
    UiCheckBox { id:numbers;objectName:"textNumbers";text:"Sayıları token içinde koru";checked:true;onClicked:options.edited() }
    UiLabel { text:"Token: Unicode harf/işaret (ve seçilirse sayı) dizisi. Noktalama ve semboller ayırır; aksan kaldırma/kök bulma yok. N-gram, durak sözcük çıkarıldıktan sonraki ardışık tokenlar; çıkarma yeni komşuluk oluşturabilir.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiCombo { accessibleLabel: "Durak sözcük politikası"; id:stops;objectName:"textStopwords";model:["Durak sözcük yok","Küçük Türkçe liste — 15 sözcük","Küçük İngilizce liste — 12 sözcük"];Layout.fillWidth:true;onActivated:options.edited() }
    UiTextField { id:custom;objectName:"textCustomStopwords";placeholderText:"Özel durak sözcükleri — boşlukla ayır, en fazla4000 karakter";maximumLength:4000;Layout.fillWidth:true;onTextEdited:options.edited();Accessible.name:"Özel durak sözcükleri" }
    UiLabel { text:"N-gram alt/üst sınırı (1–3); tutulacak vocab (1–10000). Büyük aday vocab 50000'de, üretilen n-gram 5 milyonda kontrollü durur. Frekansa göre sınırlandırma açık seçimdir; eşitlikte Unicode sözcük sırası.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiTextField { id:ngramMin;objectName:"textNgramMin";text:"1";maximumLength:1;Layout.fillWidth:true;onTextEdited:options.edited();Accessible.name:"N-gram alt sınırı" }
    UiTextField { id:ngramMax;objectName:"textNgramMax";text:"1";maximumLength:1;Layout.fillWidth:true;onTextEdited:options.edited();Accessible.name:"N-gram üst sınırı" }
    UiTextField { id:vocab;objectName:"textVocab";text:"2000";maximumLength:5;Layout.fillWidth:true;onTextEdited:options.edited();Accessible.name:"Vocab sınırı" }
}
