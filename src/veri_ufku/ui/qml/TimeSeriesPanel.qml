import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: panel
    objectName: "timeSeriesPanel"
    signal helpRequested(var origin, string context)
    spacing: Theme.md
    function spec() {
        let result={date:dateChoice.currentValue||"",measurement:measureChoice.currentValue||"",group:groupChoice.currentValue||"",frequency:["D","h","W-MON","MS"][frequency.currentIndex],timezone:zone.text,resample:resample.checked,aggregation:resample.checked?(aggregation.currentIndex===0?"sum":"mean"):"none",horizon:Number(horizon.text),test_periods:Number(testPeriods.text),folds:Number(folds.text),seasonal_period:Number(season.text),window:Number(windowSize.text),model:["level","trend","seasonal","none"][modelChoice.currentIndex]};if(temporal.enabledMode)result.advanced=temporal.config();if(signalOptions.enabledMode){result.resample=false;result.aggregation="none";result.advanced=signalOptions.config(result.measurement)}return result
    }
    Connections { target:timeSeries
        function onRestoreRequested(value) {
            let s=JSON.parse(value);temporal.restore(s.advanced&&s.advanced.family!=="signal"?s.advanced:null);signalOptions.restore(s.advanced&&s.advanced.family==="signal"?s.advanced:null)
            for(let pair of [[dateChoice,s.date],[measureChoice,s.measurement],[groupChoice,s.group]]) {
                for(let i=0;i<pair[0].count;i++)if(pair[0].valueAt(i)===pair[1])pair[0].currentIndex=i
            }
            frequency.currentIndex=["D","h","W-MON","MS"].indexOf(s.frequency);zone.text=s.timezone
            resample.checked=s.resample;aggregation.currentIndex=s.aggregation==="mean"?1:0
            horizon.text=String(s.horizon);testPeriods.text=String(s.test_periods);folds.text=String(s.folds)
            season.text=String(s.seasonal_period);windowSize.text=String(s.window);modelChoice.currentIndex=["level","trend","seasonal","none"].indexOf(s.model)
        }
    }
    UiLabel { text:"Zaman serisi — geçmişten geleceğe tahmin";font.pixelSize:Theme.heading;Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiLabel { text:"Bu yol tarih sırasını korur. Her grup ayrı seri ve ayrı kesim tarihine sahiptir; rastgele regresyon bölmesi kullanılmaz. Kaynak kayıtlar değişmez. En fazla 20 grup / 100.000 kayıt.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiButton { objectName:"timeSeriesHelp";property string helpContext:"model.time-series";text:"Sıklık ve doğrulama yardımı";onClicked:panel.helpRequested(this,"model.time-series") }
    UiLabel { text:signalOptions.enabledMode?"Sinyal: sayısal zaman ve ana kanal; kayıt/grup isteğe bağlı":"Tarih (Date/Datetime) ve sayısal ölçüm" }
    UiCombo { id:dateChoice;objectName:"timeSeriesDate";model:timeSeries.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true;Accessible.name:"Zaman serisi tarih sütunu";onActivated:timeSeries.invalidate() }
    UiCombo { id:measureChoice;objectName:"timeSeriesMeasurement";model:timeSeries.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true;Accessible.name:"Zaman serisi ölçüm";onActivated:timeSeries.invalidate() }
    UiLabel { text:temporal.enabledMode?"Series/panel kimliği — local ayrı, global ortak geçmiş":"İsteğe bağlı grup — seriler birbirinin geçmişini kullanmaz";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiCombo { accessibleLabel: "Zaman serisi grubu"; id:groupChoice;objectName:"timeSeriesGroup";model:[{id:"",name:"Grup yok"}].concat(timeSeries.columns);textRole:"name";valueRole:"id";Layout.fillWidth:true;onActivated:timeSeries.invalidate() }
    ColumnLayout { visible:!signalOptions.enabledMode;Layout.fillWidth:true
    UiLabel { text:"Sıklık: saatlik UTC geçen saat; günlük/haftalık/aylık yerel takvim başlangıcı. Haftalık pazartesi, aylık ayın ilk günü. Date için saat dilimi yoktur. Datetime saat dilimsizse IANA dilimi seçin; DST belirsiz saatleri reddedilir.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiCombo { accessibleLabel: "Dönem sıklığı"; id:frequency;objectName:"timeSeriesFrequency";model:["Günlük","Saatlik","Haftalık — pazartesi","Aylık — ay başı"];Layout.fillWidth:true;onActivated:timeSeries.invalidate() }
    UiTextField { id:zone;objectName:"timeSeriesTimezone";placeholderText:"IANA saat dilimi; ör. Europe/Istanbul";maximumLength:64;Layout.fillWidth:true;Accessible.name:qsTr("Saat dilimi");onTextChanged:timeSeries.invalidate() }
    UiCheckBox { id:resample;objectName:"timeSeriesResample";text:"Açık seçim: yeniden örnekle ve aynı dönemleri birleştir";onCheckedChanged:timeSeries.invalidate() }
    UiCombo { accessibleLabel: "Dönem özetleme yöntemi"; id:aggregation;objectName:"timeSeriesAggregation";visible:resample.checked;model:["Toplam — dönem içindeki miktar (satış/adet)","Ortalama — dönem içindeki ölçüm düzeyi (sıcaklık)"];Layout.fillWidth:true;onActivated:timeSeries.invalidate() }
    UiLabel { text:"Toplam miktarları toplar; sıcaklık gibi düzeylerde çoğu kez anlamlı değildir. Ortalama her kayda eşit ağırlık verir; zaman ağırlıklı ortalama değildir. Binler [başlangıç, sonraki başlangıç) aralığıdır. Eksik dönemler sıfır sayılmaz; tahmin durur ve açık veri hazırlığı gerekir. Duplicate tarihte seçim olmadan hesap yapılmaz.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiLabel { text:"Tahmin ufku (1–60 dönem); final test aralığı (ufuk kadar veya daha uzun, en çok 120)";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiTextField { id:horizon;objectName:"timeSeriesHorizon";text:"3";maximumLength:3;Layout.fillWidth:true;Accessible.name:"Tahmin ufku";onTextChanged:timeSeries.invalidate() }
    UiTextField { id:testPeriods;objectName:"timeSeriesTestPeriods";text:"6";maximumLength:3;Layout.fillWidth:true;Accessible.name:"Final test dönem sayısı";onTextChanged:timeSeries.invalidate() }
    UiLabel { text:"Rolling-origin fold sayısı (2–5): eğitim büyür, doğrulama hep sonraki ufuktur. Final test hiçbir fold'a girmez.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiTextField { id:folds;objectName:"timeSeriesFolds";text:"3";maximumLength:1;Layout.fillWidth:true;Accessible.name:"Rolling-origin fold sayısı";onTextChanged:timeSeries.invalidate() }
    UiLabel { text:"Mevsim dönemi: 0 kapalı; 2–366 gözlemde bir tekrar. Günlükte haftalık tekrar için 7; aylıkta yıllık tekrar için 12. Otomatik mevsim varsayımı yok.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiTextField { id:season;objectName:"timeSeriesSeason";text:"0";maximumLength:3;Layout.fillWidth:true;Accessible.name:"Mevsim dönemi";onTextChanged:timeSeries.invalidate() }
    UiButton { objectName:"timeSeriesSeasonHelp";property string helpContext:"timeseries.seasonality";text:"Mevsimsellik yardımı";onClicked:panel.helpRequested(this,"timeseries.seasonality") }
    UiLabel { text:"Geçmiş hareketli ortalama penceresi (2–60): önce lag 1, sonra geçmiş pencere. Merkezli pencere/gelecekle doldurma yok. Grafik mevcut hedefi özelliğe katmaz.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiTextField { id:windowSize;objectName:"timeSeriesWindow";text:"3";maximumLength:2;Layout.fillWidth:true;Accessible.name:"Geçmiş hareketli ortalama penceresi";onTextChanged:timeSeries.invalidate() }
    UiButton { objectName:"timeSeriesLagHelp";property string helpContext:"timeseries.lag";text:"Lag ve pencere yardımı";onClicked:panel.helpRequested(this,"timeseries.lag") }
    UiCombo { accessibleLabel: "Zaman serisi modeli"; id:modelChoice;objectName:"timeSeriesModel";model:["ExponentialSmoothing — düzey","ExponentialSmoothing — toplamsal trend","ExponentialSmoothing — toplamsal trend ve mevsim","Yalnız baseline"];Layout.fillWidth:true;onActivated:timeSeries.invalidate() }
    UiLabel { text:"İlk fold eğitimi en az max(12, 3 × mevsim dönemi, pencere + 1) dönem. Toplam geçmiş ayrıca fold × ufuk ve final aralığını kapsamalı. Naive son değeri, seasonal-naive son mevsimi tekrarlar. Model yalnız rolling-origin MAE ile seçilir; eşitlikte baseline önce gelir. Gelişmiş model her zaman daha iyi değildir.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    }
    TemporalPanel { visible:!signalOptions.enabledMode;id:temporal; onEnabledModeChanged:{if(enabledMode)signalOptions.restore(null)} Layout.fillWidth:true;onHelpRequested:function(origin,context){panel.helpRequested(origin,context)} }
    SignalPanel { id:signalOptions; onEnabledModeChanged:{if(enabledMode)temporal.restore(null)} Layout.fillWidth:true; onHelpRequested:function(origin,context){panel.helpRequested(origin,context)} }
    UiButton { objectName:"timeSeriesRun";text:signalOptions.enabledMode?"Sinyali doğrula ve hesapla":"Geliştirme ve baseline karşılaştırmasını hesapla";multiline:true;Layout.fillWidth:true;primary:true;enabled:!timeSeries.busy&&!projects.busy&&!projects.readOnly;onClicked:timeSeries.create(JSON.stringify(panel.spec())) }
    UiButton { objectName:"timeSeriesCancel";text:qsTr("İptal");visible:timeSeries.busy;onClicked:timeSeries.cancel() }
    UiLabel { text:timeSeries.message;Layout.fillWidth:true;wrapMode:Text.Wrap }
    StateNotice { visible:!!timeSeries.errorText;heading:"Zaman serisi tamamlanamadı";detail:timeSeries.errorText;Layout.fillWidth:true }
    UiLabel { visible:!!timeSeries.report.schema&&!timeSeries.current;text:"Sonuç eski veri/ayara bağlı; güncel başarı olarak kullanmayın.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiLabel { visible:!!timeSeries.report.schema;text:(timeSeries.report.warning||"")+" "+(timeSeries.report.interpretation||"");Layout.fillWidth:true;wrapMode:Text.Wrap }
    Repeater {
        model:timeSeries.report.groups||[]
        delegate: ColumnLayout {
            required property var modelData
            Layout.fillWidth:true
            UiLabel { text:modelData.group+" · "+modelData.timezone+" · "+modelData.periods+" dönem · "+modelData.duplicate_dates+" duplicate · "+modelData.missing_periods+" eksik dönem";Layout.fillWidth:true;wrapMode:Text.Wrap }
            UiLabel { text:"Eğitim sonu: "+modelData.train_end+"; saklı final: "+modelData.test_start+" — "+modelData.test_end+". Seçim: "+modelData.chosen;Layout.fillWidth:true;wrapMode:Text.Wrap }
            UiLabel { text:"Geliştirme trendi: "+Number(modelData.trend_per_period).toPrecision(5)+" ölçüm birimi/dönem. MAE ve RMSE ölçüm birimindedir.";Layout.fillWidth:true;wrapMode:Text.Wrap }
            Repeater { model:modelData.comparisons;delegate:UiLabel { required property var modelData;text:"Rolling-origin · "+modelData.method+": MAE "+Number(modelData.mae).toPrecision(6)+" · RMSE "+Number(modelData.rmse).toPrecision(6)+" · n="+modelData.n;Layout.fillWidth:true;wrapMode:Text.Wrap } }
            Repeater { model:modelData.invalid_models;delegate:UiLabel { required property var modelData;text:"Geçersiz model · "+modelData.method+": "+modelData.reason;Layout.fillWidth:true;wrapMode:Text.Wrap } }
            TimeSeriesPlot { points:modelData.history;Layout.fillWidth:true;Layout.preferredHeight:220 }
            UiLabel { text:"Mevsim profili — yalnız geliştirme, faz ortalamaları: "+(modelData.seasonal_profile.length?modelData.seasonal_profile.map(p=>p.phase+": "+Number(p.mean).toPrecision(4)).join("; "):"Dönem seçilmedi");Layout.fillWidth:true;wrapMode:Text.Wrap }
            Repeater { model:modelData.forecast;delegate:UiLabel { required property var modelData;text:modelData.date+" → tahmin "+Number(modelData.predicted).toPrecision(6)+(modelData.actual===null?" · gerçek saklı":" · gerçek "+Number(modelData.actual).toPrecision(6));Layout.fillWidth:true;wrapMode:Text.Wrap } }
            UiLabel { visible:!timeSeries.report.advanced;text:"Kaynak tarihinin ötesi — model yalnız eğitim sonuna kadar gördü; aradaki final dönemler de tahmin mesafesine dahildir. Aralık desteklenmiyor.";Layout.fillWidth:true;wrapMode:Text.Wrap }
            Repeater { model:modelData.future_forecast||[];delegate:UiLabel { required property var modelData;text:modelData.date+" → gelecek tahmini "+Number(modelData.predicted).toPrecision(6);Layout.fillWidth:true;wrapMode:Text.Wrap } }
            Repeater { model:modelData.final_metrics;delegate:UiLabel { required property var modelData;text:"Final · "+modelData.method+": MAE "+Number(modelData.mae).toPrecision(6)+" · RMSE "+Number(modelData.rmse).toPrecision(6);Layout.fillWidth:true;wrapMode:Text.Wrap } }
        }
    }
    UiLabel { visible:!signalOptions.enabledMode;text:timeSeries.report.advanced?"Advanced final tüm saklı test dönemlerini frozen origin/model ile değerlendirir. Out-of-source future covariate dosyası/model persistence bu dilimde kapalı. Test defteri kalıcıdır; sonradan seçim keşifseldir.":"Final test gerçek değerleri açar ve kullanım kalıcı kaydedilir. Testten sonra ayar/model değiştirmek keşifseldir; yeni koşu önceki kullanımı silmez. Gelecek tahminleri son kaynak tarihinin ötesine uzanır; model yalnız geliştirme geçmişine fit olur, final gerçeklerini kullanmaz.";Layout.fillWidth:true;wrapMode:Text.Wrap }
    UiButton { objectName:"timeSeriesFinal";visible:!signalOptions.enabledMode;text:"Kullanımı kaydet ve saklı final testi aç";multiline:true;Layout.fillWidth:true;enabled:timeSeries.current&&timeSeries.report.mode==="development"&&(!timeSeries.report.advanced||timeSeries.report.advanced.spec.task==="forecast")&&!timeSeries.busy&&!projects.busy&&!projects.readOnly;onClicked:timeSeries.finalTest() }
    UiButton { objectName:"timeSeriesValidationHelp";property string helpContext:"timeseries.validation";text:"Ufuk ve geçmişten geleceğe doğrulama";onClicked:panel.helpRequested(this,"timeseries.validation") }
    UiCombo { accessibleLabel: "Kayıtlı zaman analizi"; id:saved;objectName:"timeSeriesSaved";model:timeSeries.savedRuns;textRole:"label";valueRole:"id";Layout.fillWidth:true }
    UiButton { objectName:"timeSeriesOpen";text:"Kayıtlı zaman serisi sonucunu aç";enabled:saved.currentIndex>=0&&!timeSeries.busy&&!projects.busy;onClicked:timeSeries.openSaved(saved.currentValue) }
}
