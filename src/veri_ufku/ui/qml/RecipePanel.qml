import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

ColumnLayout {
    id: panel
    objectName: "recipePanel"
    signal helpRequested(var origin, string context)
    spacing: Theme.md
    function format(v) { return v===null||v===undefined ? "tanımsız" : typeof v==="number" ? Number(v.toPrecision(6)).toString() : v }
    function distribution(v) {
        if(!v)return "Kolon eşlenmedi"
        let text=v.n+" kayıt · eksik "+v.missing+" (%"+format(v.missing_rate===null?null:100*v.missing_rate)+")"
        if(v.valid_n!==undefined)text+="\nSonlu "+v.valid_n+" · sonlu olmayan "+v.nonfinite+" · min/ortalama/max "+format(v.min)+" / "+format(v.mean)+" / "+format(v.max)+"\n%25 / medyan / %75: "+format(v.q25)+" / "+format(v.median)+" / "+format(v.q75)
        if(v.categories)text+="\n"+v.categories.map(c=>c.value+": "+c.count+" (%"+format(c.rate*100)+")").join(" · ")+"\nDiğer: "+v.other_count+" · farklı kategori: "+v.distinct
        return text+(v.distribution?"\n"+v.distribution:"")
    }
    FileDialog { id:open;title:"İşlem tarifi aç";nameFilters:["İşlem tarifi (*.json)"];onAccepted:recipes.openRecipe(selectedFile.toString()) }
    FileDialog { id:save;title:"Yeni tarif dosyası kaydet";fileMode:FileDialog.SaveFile;nameFilters:["İşlem tarifi (*.json)"];onAccepted:recipes.saveRecipe(selectedFile.toString()) }
    FileDialog { id:report;title:"Yeni etki/izleme raporu kaydet";fileMode:FileDialog.SaveFile;nameFilters:["Rapor (*.json)"];onAccepted:recipes.saveReport(selectedFile.toString()) }
    UiLabel { text:"Tekrar kullanılabilir işlem akışı";font.bold:true;font.pixelSize:Theme.heading;Layout.fillWidth:true }
    UiLabel { text:"Analiz tarifi işlemleri yeni veride yeniden hesaplar. Eğitimde öğrenilmiş pipeline ayrı Model ekranında korunur. Dry-run projeyi değiştirmez.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiCombo { accessibleLabel: "İşlem zinciri"; id:chain;objectName:"recipeChain";model:recipes.versions;textRole:"name";valueRole:"id";Layout.fillWidth:true }
    Flow { Layout.fillWidth:true;spacing:Theme.sm
        UiButton { objectName:"recipeSelect";text:"1. Bu sürümün zincirini seç";enabled:chain.currentIndex>=0&&!projects.busy;onClicked:recipes.selectRecipe(chain.currentValue) }
        UiButton { text:"Tarif aç";enabled:!projects.busy;onClicked:open.open() }
        UiButton { text:"Tarif aktar";enabled:recipes.recipeSources.length>0&&!projects.busy;onClicked:save.open() }
        UiButton { text:qsTr("İptal");visible:recipes.busy;onClicked:recipes.cancel() }
    }
    StateNotice { Layout.fillWidth:true;kind:recipes.errorText?"error":recipes.busy?"loading":"info";heading:"Tarif ve yeni veri";detail:recipes.errorText||recipes.message }
    Repeater { model:recipes.recipeSources;ColumnLayout { id:sourceRow;required property var modelData;Layout.fillWidth:true
        UiLabel { text:"2. Kaynak "+modelData.id.slice(-8)+" için yeni veri seçin";Layout.fillWidth:true }
        UiCombo { accessibleLabel: "Yeni veri kaynak eşlemesi"; id:sourceChoice;model:recipes.versions;textRole:"name";valueRole:"id";Layout.fillWidth:true
            currentIndex:{for(let i=0;i<count;i++)if(valueAt(i)===sourceRow.modelData.selected)return i;return -1}
            onActivated:recipes.mapSource(sourceRow.modelData.id,currentValue)
        }
        Repeater { model:sourceRow.modelData.columns;ColumnLayout { id:columnRow;required property var modelData;Layout.fillWidth:true
            UiLabel { text:modelData.name+" · "+modelData.type+" →";Layout.fillWidth:true }
            UiCombo { accessibleLabel: "Yeni veri sütun eşlemesi"; id:columnChoice;objectName:"recipeMap_"+columnRow.modelData.id;model:[{id:"",name:"Eşleme seçin"}].concat(sourceChoice.currentIndex>=0?recipes.versions[sourceChoice.currentIndex].columns:[]);textRole:"name";valueRole:"id";Layout.fillWidth:true
                function refreshSelection() { if(!sourceRow||!columnRow)return;let target=sourceRow.modelData.mapping[columnRow.modelData.id]||""; for(let i=0;i<count;i++)if(valueAt(i)===target){currentIndex=i;return};currentIndex=0 }
                Component.onCompleted:Qt.callLater(refreshSelection)
                onModelChanged:Qt.callLater(refreshSelection)
                Connections { target:recipes;function onRecipeChanged(){Qt.callLater(columnChoice.refreshSelection)} }
                onActivated:recipes.mapColumn(sourceRow.modelData.id,columnRow.modelData.id,currentValue)
            }
        } }
    } }
    UiLabel { text:"Tarif seed’i (mevcut dönüşümler deterministik)";Layout.fillWidth:true }
    UiTextField { Accessible.name: "Tarif seed’i (mevcut dönüşümler deterministik)"; objectName:"recipeSeed";text:recipes.recipeSeed.toString();validator:IntValidator {bottom:0;top:2147483647 } Layout.fillWidth:true;onEditingFinished:recipes.setSeed(parseInt(text)) }
    UiButton { objectName:"recipeDryRun";text:"3. Dry-run — tüm adımları dene";Layout.fillWidth:true;enabled:recipes.recipeSources.length>0&&!projects.busy;onClicked:recipes.dryRun() }
    Repeater { model:recipes.steps;UiLabel { required property var modelData;text:modelData.index+". "+modelData.kind+" · "+modelData.status+(modelData.error?"\n"+modelData.error:"")+(modelData.impact?"\nKayıt: "+modelData.impact.before_rows+" → "+modelData.impact.after_rows+" · değişen hücre: "+modelData.impact.changed_cells+" · yeni eksik: "+modelData.impact.new_nulls+" · çıkarılan kayıt: "+modelData.impact.removed_rows:"");Layout.fillWidth:true;wrapMode:Text.Wrap } }
    UiButton { objectName:"recipeApply";text:"İncelediğim akışı uygula ve projeyi kaydet";primary:true;tone:"violet";Layout.fillWidth:true;enabled:recipes.canApply;onClicked:recipes.applyRecipe() }
    UiCheckBox { id:monitor;objectName:"recipeMonitor";text:"Veri değişimini ve sonradan gelen hedefleri incele";Layout.fillWidth:true }
    ColumnLayout { visible:monitor.checked;Layout.fillWidth:true;spacing:Theme.md
        UiLabel { text:"Eski ve yeni sürümü seçin. Aynı isimli kolonlar eşlenir; tarifte bu iki kaynak eşlendiyse seçtiğiniz kolon haritası kullanılır.";Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiCombo { accessibleLabel: "Eski veri sürümü"; id:old;objectName:"recipeOld";model:recipes.versions;textRole:"name";valueRole:"id";Layout.fillWidth:true }
        UiCombo { accessibleLabel: "Yeni veri sürümü"; id:newData;objectName:"recipeNew";model:recipes.versions;textRole:"name";valueRole:"id";Layout.fillWidth:true }
        UiButton { objectName:"recipeCompare";text:"Dağılımları karşılaştır";enabled:old.currentIndex>=0&&newData.currentIndex>=0&&!projects.busy;onClicked:recipes.compareData(old.currentValue,newData.currentValue) }
        UiLabel { text:recipes.changeReport.note||"";color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap }
        Repeater { model:recipes.changeReport.columns||[];UiLabel { required property var modelData;text:modelData.name+(modelData.new_name?" → "+modelData.new_name:"")+" · "+({same:"şema aynı",renamed:"adı değişti",type_changed:"türü değişti","removed/unmapped":"eksik/eşlenmedi","added/unmapped":"yeni/eşlenmedi"}[modelData.schema_change]||modelData.schema_change)+"\nRol: "+((modelData.role_before||{}).role||"belirtilmedi")+" → "+((modelData.role_after||{}).role||"belirtilmedi")+"\nEski: "+panel.distribution(modelData.before)+"\nYeni: "+panel.distribution(modelData.after);Layout.fillWidth:true;wrapMode:Text.Wrap } }
        UiLabel { text:"Gerçek hedef sonradan geldiyse: Model ekranında ürettiğiniz son tahmin dosyasıyla yukarıdaki yeni veri sürümünü eşleyin. Anahtarlar benzersiz ve boş olmayan aynı türde olmalı. RowId yalnız aynı kayıt kimlikleri korunmuşsa kullanılır; ayrı içe aktarılmış hedef için ortak iş kimliği seçin.";Layout.fillWidth:true;wrapMode:Text.Wrap }
        UiTextField { Accessible.name: "Gerçek hedef sonradan geldiyse: Model ekranında ürettiğiniz son tahmin dosyasıyla yukarıdaki yeni veri sürümünü eşleyin. Anahtarlar benzersiz ve boş olmayan aynı türde olmalı. RowId yalnız aynı kayıt kimlikleri korunmuşsa kullanılır; ayrı içe aktarılmış hedef için ortak iş kimliği seçin."; id:pkey;objectName:"recipePredictionKey";placeholderText:"Tahmin dosyası kimlik kolonu";text:"__vu_row_id";Layout.fillWidth:true }
        UiTextField { Accessible.name: "Gerçek hedef sonradan geldiyse: Model ekranında ürettiğiniz son tahmin dosyasıyla yukarıdaki yeni veri sürümünü eşleyin. Anahtarlar benzersiz ve boş olmayan aynı türde olmalı. RowId yalnız aynı kayıt kimlikleri korunmuşsa kullanılır; ayrı içe aktarılmış hedef için ortak iş kimliği seçin."; id:tkey;objectName:"recipeTargetKey";placeholderText:"Hedef dosyası kimlik kolonu";text:"__vu_row_id";Layout.fillWidth:true }
        UiTextField { Accessible.name: "Gerçek hedef sonradan geldiyse: Model ekranında ürettiğiniz son tahmin dosyasıyla yukarıdaki yeni veri sürümünü eşleyin. Anahtarlar benzersiz ve boş olmayan aynı türde olmalı. RowId yalnız aynı kayıt kimlikleri korunmuşsa kullanılır; ayrı içe aktarılmış hedef için ortak iş kimliği seçin."; id:pcol;objectName:"recipePredictionColumn";placeholderText:"Tahmin kolonu adı";Layout.fillWidth:true }
        UiTextField { Accessible.name: "Gerçek hedef sonradan geldiyse: Model ekranında ürettiğiniz son tahmin dosyasıyla yukarıdaki yeni veri sürümünü eşleyin. Anahtarlar benzersiz ve boş olmayan aynı türde olmalı. RowId yalnız aynı kayıt kimlikleri korunmuşsa kullanılır; ayrı içe aktarılmış hedef için ortak iş kimliği seçin."; id:tcol;objectName:"recipeTargetColumn";placeholderText:"Gerçek hedef kolonu adı";Layout.fillWidth:true }
        UiButton { objectName:"recipeEvaluate";text:"Kimlikle eşle ve yeni performansı ölç";enabled:!projects.busy&&newData.currentIndex>=0;onClicked:recipes.evaluateTargets(newData.currentValue,pkey.text,tkey.text,pcol.text,tcol.text) }
        UiLabel { text:recipes.changeReport.schema==="DelayedPerformance/v1"?"Eşleşen: "+recipes.changeReport.matched+" · ölçülen: "+recipes.changeReport.scored+" · geçersiz: "+recipes.changeReport.invalid+" · hedefsiz tahmin: "+recipes.changeReport.unmatched_predictions+" · tahminsiz hedef: "+recipes.changeReport.unmatched_targets+"\n"+(recipes.changeReport.metrics?Object.keys(recipes.changeReport.metrics).map(k=>k+": "+panel.format(recipes.changeReport.metrics[k])).join(" · "):"Geçerli hedef yok; başarı metriği yok."):"";Layout.fillWidth:true;wrapMode:Text.Wrap }
    }
    UiButton { text:"Etki/izleme raporunu aktar";enabled:recipes.current&&!projects.busy;onClicked:report.open() }
    UiButton { text:qsTr("Bu ne işe yarar?");tone:"mint";helpContext:"workflow.recipe";onClicked:panel.helpRequested(this,helpContext) }
}
