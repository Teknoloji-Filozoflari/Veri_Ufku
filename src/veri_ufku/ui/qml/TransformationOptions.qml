import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    objectName: "transformationOptions"
    signal helpRequested(var origin, string context)
    property var kinds: ["computed", "text_split", "text_combine", "date_parts", "aggregate", "pivot", "unpivot", "append", "join"]
    property string kind: kinds[method.currentIndex]
    property int joinStep: 0
    property var selected: []
    property var groups: []
    property var metrics: []
    property var keyPairs: []
    property var mapping: []
    property var other: (operations.secondaryDatasets[secondary.currentIndex] || {})
    property var rightColumns: other.columns || []
    property string equality: "v1:null_equal;nan_reject;zero_equal;decimal_numeric;timezone_instant;text_exact"
    property var advice: ({computed: "İzinli ifadeler: + − * /, karşılaştırma, and/or/not; abs, coalesce, ifelse, lower, upper, length, round. col kalıcı ColumnId taşır. Null yayılır; coalesce açık istisnadır. Float64 kesin değerleri temsil edemeyebilir; Decimal ölçeğine sığmayan sonuç reddedilir. round yalnız açık seçimle half-even yuvarlar.", text_split: "Literal ayraçla iki yeni metin alanı üretir; son alan kalan metni korur. Eksik parça null olur. Asıl alan korunur.", text_combine: "Seçtiğiniz alanları seçim sırasıyla birleştirir. Null yayılımı veya null atlama açık seçilir; tümü null ve atlama seçiminde boş metin üretilir.", date_parts: "Native tarih parçaları eklenir. Saat dilimsiz tarihe timezone atanmaz; mevcut timezone korunur veya aware veride dönüştürülür. Hafta/haftanın günü ISO kuralıdır.", aggregate: "Her grup yeni kayıt olur; tüm üye kaynak kayıtlarına ilişkisi saklanır. Görüntü sırası kullanılmaz; gruplar ilk kaynak görünümü sırasındadır. Null anahtarlar birlikte gruplanır; NaN/inf anahtar reddedilir. Tam sayı/Decimal taşması ve ölçek kaybı durdurur; Float64 yaklaşık hesap açık seçilir.", pivot: "Uzun veriyi genişletir. Aynı grup/başlıkta birden çok kayıt varsa açık agregasyon gereklidir; varsayılan çakışmada durur. Null başlık reddedilir. Başlıklar önizlemede kalıcı kimlikle sabitlenir.", unpivot: "Geniş alanları uzun veri yapar; seçili değer alanlarının türleri tam aynı olmalı. Her kaynak × alan için yeni kayıt ve kaynak alan ilişkisi saklanır.", append: "Sol kayıtlar ardından sağ kayıtlar eklenir. Her alanın eşlemesini gözden geçirip onaylayın. Eksik taraf açık null olur; farklı türleri önce açıkça dönüştürün. Otomatik tür veya kolon kaybı yoktur.", join: "1. İkinci sürüm ve anahtar çiftleri; 2. join türü, null ve ad çakışmaları; 3. tam veri önizlemesi. n:n eşleşmede satırlar çoğalır. Önizleme ilişkiyi, tam satır tahminini ve eşleşmeyenleri gösterir. Uygulama yalnız incelenmiş önizlemeyi yayımlar."})
    spacing: Theme.md
    function readableFormula(value) { operations.transformColumns.forEach(c=>{value=value.split('col("'+c.id+'")').join('['+c.name+']')}); return value }
    function invalidate() { operations.discardPreview() }
    function toggle(values, id, checked) { let result = values.filter(v => v !== id); if (checked) result.push(id); return result }
    function output(name, type) { return {id: operations.newColumnId(), name: name, original_name: name, type: type} }
    function descriptor(type) {
        if (type === "decimal") return {kind:"Decimal",precision:38,scale:6}
        if (type === "datetime") return {kind:"Datetime",unit:"us",zone:null}
        if (type === "Decimal") return {kind: "Decimal", precision: 38, scale: scale.value}
        if (type.indexOf("Decimal(") === 0) { let m = /precision=(\d+), scale=(\d+)/.exec(type); return {kind:"Decimal", precision:Number(m[1]), scale:Number(m[2])} }
        if (type.indexOf("Datetime(") === 0) { let m = /time_unit='([^']+)', time_zone=(None|'([^']+)')/.exec(type); return {kind:"Datetime",unit:m[1],zone:m[3] || null} }
        return {kind: ({text:"String",int64:"Int64",float64:"Float64",decimal:"Decimal",date:"Date",datetime:"Datetime",boolean:"Boolean"})[type] || type}
    }
    function typeText(d) { if (d.kind === "Decimal") return "Decimal(precision="+d.precision+", scale="+d.scale+")"; if (d.kind === "Datetime") return "Datetime(time_unit='"+d.unit+"', time_zone="+(d.zone ? "'"+d.zone+"'" : "None")+")"; return d.kind }
    function target() { return descriptor(["Decimal", "Int64", "Float64", "String", "Boolean"][targetType.currentIndex]) }
    function col(id) { return operations.transformColumns.find(c => c.id === id) || {} }
    function prepareMapping() {
        let used = []
        let items = operations.transformColumns.map(c => { let other = rightColumns.find(r => r.name === c.name); if (other) used.push(other.id); return {left_column:c.id,right_column:other ? other.id : null,output:output(c.name,typeText(descriptor(c.type)))} })
        rightColumns.filter(c => used.indexOf(c.id)<0).forEach(c => { let name = c.name; if (items.some(m=>m.output.name===name)) name += "_sağ"; items.push({left_column:null,right_column:c.id,output:output(name,typeText(descriptor(c.type)))}) })
        mapping = items; approved.checked = false; invalidate()
    }
    function preview() {
        let p = {}, ids = [], t = target(), limit = maxRows.value
        if (kind === "computed") {
            ids = operations.transformColumns.filter(c => expression.text.indexOf(c.id)>=0).map(c=>c.id)
            p = {expression:expression.text,target:t,output:output(outputName.text,typeText(t)),zero_policy:zeroPolicy.currentIndex === 0 ? "reject" : "null"}
        } else if (kind === "text_split") { ids=[column.currentValue]; p={delimiter:separator.text,outputs:[output(outputName.text, "String"),output(secondName.text,"String")]} }
        else if (kind === "text_combine") { ids=selected; p={separator:separator.text,null_policy:nullPolicy.currentIndex===0 ? "propagate" : "skip",output:output(outputName.text,"String")} }
        else if (kind === "date_parts") { ids=[column.currentValue]; p={timezone:timezone.text || "preserve",parts:[{part:["year","month","day","weekday","week","quarter","hour","minute"][datePart.currentIndex],output:output(outputName.text,"Int64") }]} }
        else if (kind === "aggregate") { ids=groups.concat(metrics.map(m=>m.column_id).filter(i=>i!==null && groups.indexOf(i)<0)); ids=Array.from(new Set(ids)); p={group_columns:groups,metrics:metrics,equality:equality,max_output_rows:limit} }
        else if (kind === "pivot") { ids=Array.from(new Set(groups.concat([header.currentValue,column.currentValue]))); let agg=["reject","count","sum","mean","min","max"][aggregation.currentIndex]; let dt=agg==="count" ? {kind:"Int64"} : ["reject","min","max"].indexOf(agg)>=0 ? descriptor(col(column.currentValue).type) : t; p={group_columns:groups,header_column:header.currentValue,value_column:column.currentValue,aggregation:agg,target:dt,equality:equality,max_output_rows:limit} }
        else if (kind === "unpivot") { ids=Array.from(new Set(groups.concat(selected))); p={index_columns:groups,value_columns:selected,variable_output:output(outputName.text,"String"),value_output:output(secondName.text,typeText(descriptor(col(selected[0]).type))),max_output_rows:limit} }
        else if (kind === "join") { ids=keyPairs.map(k=>k.left); p={secondary_version_id:other.version_id,left_keys:ids,right_keys:keyPairs.map(k=>k.right),how:["inner","left","right","full"][joinType.currentIndex],nulls_equal:nullJoin.checked,right_outputs:rightColumns.map(c=>({column_id:c.id,output:output(c.name+suffix.text,typeText(descriptor(c.type)))})),max_output_rows:limit,equality:equality} }
        else if (kind === "append") { if (!approved.checked) return; ids=operations.transformColumns.map(c=>c.id); p={secondary_version_id:other.version_id,mapping:mapping,max_output_rows:limit} }
        operations.previewTransform(kind,JSON.stringify(ids),JSON.stringify(p),destination.currentIndex===0 ? "chain" : "copy")
    }
    UiCombo { id: method; objectName: "transformMethod"; Layout.fillWidth: true; model: ["Hesaplanmış kolon", "Metin böl", "Metin birleştir", "Tarih parçası", "Grupla / toplulaştır", "Pivot — geniş veri", "Unpivot — uzun veri", "Alt alta ekle — append", "Anahtarla birleştir — join"]; onActivated: { selected=[]; groups=[]; metrics=[]; keyPairs=[]; mapping=[]; root.invalidate() } }
    Label { text: root.advice[root.kind]; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.secondary }
    UiCombo { id: destination; objectName: "transformDestination"; Layout.fillWidth: true; model: ["Mevcut işlem zincirinde yeni sürüm", "Ayrı kopya dataset'te yeni zincir"]; onActivated: root.invalidate() }
    Label { visible: ["computed","text_split","date_parts","aggregate","pivot"].indexOf(root.kind)>=0; text: "Giriş sütunu / ölçüm alanı" }
    UiCombo { id: column; objectName: "transformColumn"; Layout.fillWidth: true; model: operations.transformColumns; textRole:"name"; valueRole:"id"; visible: ["computed","text_split","date_parts","aggregate","pivot"].indexOf(root.kind)>=0; onActivated: root.invalidate() }
    ColumnLayout {
        visible: root.kind === "computed"; Layout.fillWidth: true
        UiButton { objectName:"formulaInsertColumn"; text:"Seçili sütunu formüle ekle"; onClicked: { expression.insert(expression.cursorPosition,'col("'+column.currentValue+'")'); root.invalidate() } }
        TextArea { id: expression; objectName:"formulaExpression"; Layout.fillWidth:true; wrapMode:TextEdit.Wrap; placeholderText:"Örn. col(\"kalıcı kimlik\") * 2"; Accessible.name:"Güvenli formül"; onTextChanged: root.invalidate() }
        Label { text:"Okunabilir formül: " + root.readableFormula(expression.text); Layout.fillWidth:true; wrapMode:Text.WordWrap }
        Label { text:"Formül sütunları: "+operations.transformColumns.filter(c=>expression.text.indexOf(c.id)>=0).map(c=>c.name+" = "+c.id).join("; "); Layout.fillWidth:true; wrapMode:Text.WrapAnywhere }
        UiCombo { id: zeroPolicy; objectName:"formulaZeroPolicy"; Layout.fillWidth:true; model:["Sıfıra bölmede bütün işlemi durdur", "Sıfıra bölmeyi yeni null yap ve say"]; onActivated:root.invalidate() }
    }
    Label { visible:["computed","text_split","text_combine","date_parts","unpivot"].indexOf(root.kind)>=0; text:root.kind==="unpivot" ? "Değişken alanının adı" : "Yeni alan adı" }
    TextField { id:outputName; objectName:"transformOutputName"; text:"Yeni_alan"; maximumLength:200; Layout.fillWidth:true; visible:["computed","text_split","text_combine","date_parts","unpivot"].indexOf(root.kind)>=0; onTextEdited:root.invalidate() }
    TextField { id:secondName; objectName:"transformSecondName"; text:"Yeni_değer"; placeholderText:"İkinci alan adı"; maximumLength:200; Layout.fillWidth:true; visible:root.kind==="text_split" || root.kind==="unpivot"; onTextEdited:root.invalidate() }
    TextField { id:separator; objectName:"transformSeparator"; text:"-"; placeholderText:"Literal ayraç / birleştirme metni"; Accessible.name:"Ayraç"; Layout.fillWidth:true; visible:root.kind==="text_split" || root.kind==="text_combine"; onTextEdited:root.invalidate() }
    UiCombo { id:nullPolicy; Layout.fillWidth:true; visible:root.kind==="text_combine"; model:["Null varsa sonuç null", "Null alanları atla"]; onActivated:root.invalidate() }
    UiCombo { id:datePart; objectName:"transformDatePart"; Layout.fillWidth:true; visible:root.kind==="date_parts"; model:["Yıl","Ay","Gün","Haftanın günü — ISO 1–7","Hafta — ISO","Çeyrek","Saat","Dakika"]; onActivated:root.invalidate() }
    TextField { id:timezone; visible:root.kind==="date_parts"; Layout.fillWidth:true; placeholderText:"preserve veya aware veride IANA timezone"; text:"preserve"; maximumLength:100; onTextEdited:root.invalidate() }
    ColumnLayout {
        visible:root.kind==="text_combine" || root.kind==="unpivot"; Layout.fillWidth:true
        Label { text:"Değer alanları (seçim sırası korunur)" }
        Repeater { model:root.kind==="text_combine" || root.kind==="unpivot" ? operations.transformColumns : []; delegate:CheckBox { required property var modelData; text:modelData.name; checked:root.selected.indexOf(modelData.id)>=0; onToggled:{root.selected=root.toggle(root.selected,modelData.id,checked);root.invalidate()} } }
    }
    ColumnLayout {
        visible:["aggregate","pivot","unpivot"].indexOf(root.kind)>=0; Layout.fillWidth:true
        Label { text:root.kind==="unpivot" ? "Korunacak kimlik alanları" : "Grup alanları (toplulaştırmada boş: tüm veri)" }
        Repeater { model:["aggregate","pivot","unpivot"].indexOf(root.kind)>=0 ? operations.transformColumns : []; delegate:CheckBox { required property var modelData; text:modelData.name; checked:root.groups.indexOf(modelData.id)>=0; onToggled:{root.groups=root.toggle(root.groups,modelData.id,checked);root.invalidate()} } }
    }
    ColumnLayout {
        visible:root.kind==="computed" || root.kind==="aggregate" || root.kind==="pivot"; Layout.fillWidth:true
        Label { text:"Sonuç türü (sum/mean için de açık seçim)" }
        UiCombo { id:targetType; objectName:"transformTarget"; model:["Kesin Decimal", "Tam sayı Int64", "Yaklaşık Float64", "Metin", "Boolean"]; Layout.fillWidth:true; onActivated:root.invalidate() }
        SpinBox { id:scale; from:0; to:38; value:6; visible:targetType.currentIndex===0; onValueModified:root.invalidate() }
    }
    ColumnLayout {
        visible:root.kind==="aggregate"; Layout.fillWidth:true
        UiCombo { id:metricMethod; objectName:"transformMetric"; model:["Kayıt sayısı","Geçerli değer sayısı","Toplam","Ortalama","En küçük","En büyük"]; Layout.fillWidth:true; onActivated:root.invalidate() }
        TextField { id:metricName; text:"Ölçüm"; maximumLength:200; Layout.fillWidth:true }
        UiButton { objectName:"transformAddMetric"; text:"Ölçümü ekle"; onClicked:{ let m=["count","count_valid","sum","mean","min","max"][metricMethod.currentIndex]; let dt=["count","count_valid"].indexOf(m)>=0 ? {kind:"Int64"} : ["min","max"].indexOf(m)>=0 ? root.descriptor(root.col(column.currentValue).type) : root.target(); root.metrics=root.metrics.concat([{column_id:m==="count" ? null : column.currentValue,method:m,target:dt,output:root.output(metricName.text,root.typeText(dt))}]); root.invalidate() } }
        Repeater { model:root.metrics; delegate:Label { required property var modelData; text:modelData.output.name+" · "+modelData.method+" · "+(root.col(modelData.column_id).name || "tüm kayıtlar"); Layout.fillWidth:true; wrapMode:Text.WordWrap } }
        UiButton { text:"Ölçüm listesini temizle"; onClicked:{root.metrics=[];root.invalidate()} }
    }
    UiCombo { id:header; objectName:"pivotHeader"; visible:root.kind==="pivot"; model:operations.transformColumns; textRole:"name"; valueRole:"id"; Layout.fillWidth:true; onActivated:root.invalidate() }
    UiCombo { id:aggregation; objectName:"pivotAggregation"; visible:root.kind==="pivot"; Layout.fillWidth:true; model:["Çakışmada durdur — agregasyon seçilmedi","Kayıt sayısı","Toplam","Ortalama","En küçük","En büyük"]; onActivated:root.invalidate() }
    ColumnLayout {
        visible:root.kind==="join" || root.kind==="append"; Layout.fillWidth:true
        Label { text:"İkinci dataset'in değişmez sürümü" }
        UiCombo { id:secondary; objectName:"transformSecondary"; model:operations.secondaryDatasets; textRole:"label"; valueRole:"version_id"; Layout.fillWidth:true; onActivated:{root.keyPairs=[];root.mapping=[];root.invalidate()} }
        ColumnLayout {
            visible:root.kind==="join"; Layout.fillWidth:true
            Label { text:"Join sihirbazı · " + (root.joinStep + 1) + "/3: " + ["Anahtar çiftleri", "Eşleşme ve kolon adları", "Tam etkiyi incele"][root.joinStep]; Layout.fillWidth:true; wrapMode:Text.WordWrap }
            RowLayout {
                UiButton { objectName:"joinPreviousStep"; text:"Önceki adım"; enabled:root.joinStep>0; onClicked:root.joinStep-- }
                UiButton { objectName:"joinNextStep"; text:"Sonraki adım"; enabled:root.joinStep<2; onClicked:root.joinStep++ }
            }
            ColumnLayout { visible:root.joinStep===0; Layout.fillWidth:true
            Label { text:"Anahtar çifti: sol → sağ (türleri tam aynı olmalı)" }
            UiCombo { id:leftKey; objectName:"joinLeftKey"; model:operations.transformColumns; textRole:"name"; valueRole:"id"; Layout.fillWidth:true }
            UiCombo { id:rightKey; objectName:"joinRightKey"; model:root.rightColumns; textRole:"name"; valueRole:"id"; Layout.fillWidth:true }
            UiButton { objectName:"joinAddKey"; text:"Anahtar çiftini ekle"; onClicked:{root.keyPairs=root.keyPairs.concat([{left:leftKey.currentValue,right:rightKey.currentValue}]);root.invalidate()} }
            Repeater { model:root.keyPairs; delegate:Label { required property var modelData; text:root.col(modelData.left).name+" → "+(root.rightColumns.find(c=>c.id===modelData.right) || {}).name; Layout.fillWidth:true; wrapMode:Text.WordWrap } }
            UiButton { text:"Anahtarları temizle"; onClicked:{root.keyPairs=[];root.invalidate()} }
            }
            ColumnLayout { visible:root.joinStep===1; Layout.fillWidth:true
            UiCombo { id:joinType; objectName:"joinType"; model:["Inner — yalnız eşleşen","Left — tüm sol kayıtlar","Right — tüm sağ kayıtlar","Full — iki taraftaki tüm kayıtlar"]; Layout.fillWidth:true; onActivated:root.invalidate() }
            CheckBox { id:nullJoin; objectName:"joinNullEqual"; text:"Null anahtarlar birbirleriyle eşleşsin"; onToggled:root.invalidate() }
            TextField { id:suffix; objectName:"joinRightSuffix"; text:"_sağ"; placeholderText:"Sağ alan adlarının eki (çakışma çözümü)"; Accessible.name:"Sağ kolon adı eki"; Layout.fillWidth:true; onTextEdited:root.invalidate() }
            Label { text:"Sağ çıktı alanları: "+root.rightColumns.map(c=>c.name+suffix.text).join(", ")+". Eşleşmeyen tarafın değerleri null olur. Null eşleştirme açık seçilirse null tekrarlar da satırları çoğaltabilir."; Layout.fillWidth:true; wrapMode:Text.WordWrap }
            }
            Label { visible:root.joinStep===2; text:"Anahtarlar: " + root.keyPairs.map(k=>root.col(k.left).name+" → "+(root.rightColumns.find(c=>c.id===k.right) || {}).name).join(", ")+". " + joinType.currentText + "; null eşitliği " + (nullJoin.checked ? "açık" : "kapalı") + "; sağ ad eki: " + suffix.text + ". Önizle ile tam ilişki/satır sayısı ve eşleşmeyenleri inceleyin; Uygula ile bu önizlemeyi yayımlayın."; Layout.fillWidth:true; wrapMode:Text.WordWrap }
        }
        ColumnLayout {
            visible:root.kind==="append"; Layout.fillWidth:true
            UiButton { objectName:"appendPrepareMapping"; text:"Alan eşleme önerisini hazırla"; onClicked:root.prepareMapping() }
            Repeater { model:root.mapping; delegate:ColumnLayout { required property var modelData; required property int index; Layout.fillWidth:true
                Label { text:(root.col(modelData.left_column).name || "açık null")+" → "+modelData.output.name+" ← "+((root.rightColumns.find(c=>c.id===modelData.right_column) || {}).name || "açık null"); Layout.fillWidth:true; wrapMode:Text.WordWrap }
                UiCombo { model:[{id:"",name:"Sağ taraf açık null"}].concat(root.rightColumns); textRole:"name"; valueRole:"id"; currentIndex:model.findIndex(c=>c.id===(modelData.right_column || "")); Layout.fillWidth:true; onActivated:{let items=root.mapping.slice();let item=Object.assign({},items[index]);item.right_column=currentValue || null;items[index]=item;root.mapping=items;approved.checked=false;root.invalidate()} }
            } }
            CheckBox { id:approved; objectName:"appendApproveMapping"; text:"Eşleme ve eksik tarafların null olmasını onaylıyorum"; onToggled:root.invalidate() }
        }
    }
    Label { text:"En fazla üretilecek kayıt (bütçe; aşılırsa eski veri korunur)"; visible:["aggregate","pivot","unpivot","append","join"].indexOf(root.kind)>=0; Layout.fillWidth:true; wrapMode:Text.WordWrap }
    SpinBox { id:maxRows; objectName:"transformMaxRows"; from:1; to:10000000; value:1000000; editable:true; visible:["aggregate","pivot","unpivot","append","join"].indexOf(root.kind)>=0; onValueModified:root.invalidate() }
    UiButton { text:"Yöntem ve küçük örnek"; property string helpContext:"transform.methods"; onClicked:root.helpRequested(this, "transform."+root.kind.replace(/_/g,"-")) }
}
