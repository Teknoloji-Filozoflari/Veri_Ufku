import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Değerlendirme sonuçları, final test ve test kullanım defteri.
// Protokol (hedef/split/fold) ValidationProtocol.qml içindedir; buraya dışarıdan gelir.
ColumnLayout {
    id: panel
    objectName: "validationPanel"
    property string helpContext: "model.validation"
    property var protocol: ({})
    property bool protocolBlocked: false
    signal helpRequested(var origin, string context)
    spacing: Theme.md
    UiLabel { text:"Değerlendirme sonuçları ve final test";font.pixelSize:Theme.heading;font.bold:true;Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiLabel { text:"Test verisi en son açılır: aday seçimi geliştirme CV/validation üzerinde yapılır, final testte model ve eşik dondurulur. Her test kullanımı projede kayıtlıdır.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    ModelFamiliesPanel { Layout.fillWidth:true;protocol:panel.protocol;protocolBlocked:!!panel.protocolBlocked;onHelpRequested:function(origin,context){panel.helpRequested(origin,context)} }
    SearchPanel { Layout.fillWidth:true;protocol:panel.protocol;protocolBlocked:!!panel.protocolBlocked;onHelpRequested:function(origin,context){panel.helpRequested(origin,context)} }
    UncertaintyPanel { Layout.fillWidth:true;protocol:panel.protocol;protocolBlocked:!!panel.protocolBlocked;onHelpRequested:function(origin,context){panel.helpRequested(origin,context)} }
    Flow { Layout.fillWidth:true;spacing:Theme.sm
        UiButton { visible: false; text:qsTr("Bu ne işe yarar?");helpContext:"model.validation";onClicked:panel.helpRequested(this,helpContext) }
        UiButton { visible: false; text:"Test kullanımını öğren";helpContext:"model.test-use";onClicked:panel.helpRequested(this,helpContext) }
        UiButton { objectName:"validationCancel";text:qsTr("İptal");visible:validation.busy;enabled:validation.cancelable;onClicked:validation.cancel() }
    }
    StateNotice { Layout.fillWidth:true;kind:validation.errorText?"error":validation.busy?"loading":"info";heading:"Değerlendirme durumu";detail:validation.errorText||validation.message }
    Repeater { model:validation.invalidFolds;UiLabel { required property var modelData;text:modelData.scope+" · geçersiz: "+modelData.reason;color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap } }
    UiCheckBox { id:technical;objectName:"validationTechnical";text:"Split/protokol/koşu kimliklerini göster";Layout.fillWidth:true }
    UiLabel { objectName:"validationSummary";visible:!!validation.summaryReport.plan;text:(validation.current?"Güncel":"Kayıtlı/eski")+" · "+(validation.summaryReport.mode||"")+" · model: "+(validation.summaryReport.selected_model||validation.summaryReport.baseline||"")+"\n"+(validation.summaryReport.default_reason||"")+"\n"+(technical.checked&&validation.summaryReport.plan?validation.summaryReport.plan.split_id:"")+"\n"+(validation.summaryReport.estimated_cost?"Train="+validation.summaryReport.estimated_cost.train_n+" · validation="+validation.summaryReport.estimated_cost.validation_n+" · development="+validation.summaryReport.estimated_cost.development_n+" · test="+validation.summaryReport.estimated_cost.test_n+"\nFold train boyutları="+validation.summaryReport.estimated_cost.fold_train_n.join(", ")+" · fit kayıt geçişi tahmini="+validation.summaryReport.estimated_cost.estimated_fit_row_passes:"");Layout.fillWidth:true;wrapMode:Text.Wrap }
    Repeater { model:validation.summaryReport.evaluations||[];ColumnLayout { required property var modelData;Layout.fillWidth:true
        UiLabel { text:modelData.scope+" · train="+modelData.train_n+" · değerlendirilen="+modelData.evaluation_n;Layout.fillWidth:true;wrapMode:Text.Wrap;font.bold:true }
        Repeater { model:modelData.metrics;UiLabel { required property var modelData;objectName:"validationMetric_"+modelData.metric;text:modelData.metric+" = "+((typeof modelData.value!=="number"||!isFinite(modelData.value))?"tanımsız: "+modelData.status:modelData.value.toFixed(6))+" · "+(modelData.direction==="minimize"?"daha küçük iyi":"daha büyük iyi")+" · kapsam="+modelData.scope+" · n="+modelData.n;Layout.fillWidth:true;wrapMode:Text.Wrap } }
    } }
    Repeater { model:validation.summaryReport.cv_summary||[];UiLabel { required property var modelData;text:modelData.metric+" · geliştirme CV ortalaması="+modelData.mean.toFixed(6)+" · fold sapması="+modelData.standard_deviation.toFixed(6)+" · geçerli fold="+modelData.valid_folds;Layout.fillWidth:true;wrapMode:Text.Wrap } }
    UiCheckBox { id:finalConsent;objectName:"validationTestConsent";text:"Seçimlerim tamamlandı; final testi şimdi göreceğim. Tekrar kullanım ve sonraki seçimler keşifseldir, bağımsız değerlendirme gerekir.";Layout.fillWidth:true }
    UiButton { objectName:"validationTest";text:"Final testi değerlendir ve deftere kaydet";tone:"orange";multiline:true;Layout.fillWidth:true;enabled:validation.canTest&&finalConsent.checked;onClicked:{validation.evaluateTest();finalConsent.checked=false} }
    UiCombo { accessibleLabel: "Kayıtlı değerlendirme"; id:saved;objectName:"validationSaved";model:validation.savedRuns;textRole:"label";valueRole:"id";Layout.fillWidth:true }
    UiButton { objectName:"validationOpen";text:"Kayıtlı model/baseline koşusunu aç";enabled:!validation.busy&&!projects.busy&&saved.currentIndex>=0;onClicked:validation.openRun(saved.currentValue) }
    UiLabel { text:"Proje boyunca final test kullanım defteri";font.bold:true;Layout.fillWidth:true }
    UiLabel { text:"Yeni koşu, proje içi veri kopyası ve farklı kaydet geçmişi gizlemez. Bu defter yalnız bu projede gözlenen kullanımı bilir; proje dışında yapılan değerlendirmeler bilinmez. Pending kayıt sonucu belirsiz/kesilmiş kullanımdır; başarılı değildir.";color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap }
    Repeater { model:validation.testHistory;UiLabel { required property var modelData;text:modelData.status+" · "+(modelData.evaluated_at||modelData.requested_at)+(technical.checked?"\nVeri="+modelData.dataset_version+"\n"+modelData.split_id+"\n"+modelData.protocol_id+"\nKoşu="+modelData.run_id:"")+" · önceki kullanımlar="+modelData.prior_test_use_ids.length+" · sonraki seçimler="+modelData.subsequent_choices.join(", ");Layout.fillWidth:true;wrapMode:Text.Wrap } }
}
