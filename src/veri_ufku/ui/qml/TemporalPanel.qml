import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id:panel
    objectName:"temporalPanel"
    signal helpRequested(var origin,string context)
    property bool enabledMode: expanded.checked
    property var report: timeSeries.report
    function diagnosticSummary(source){let out={};Object.keys(source||{}).forEach(k=>{let d={};Object.keys(source[k]).forEach(name=>{if(["trend","seasonal","residual","values","lags"].indexOf(name)<0)d[name]=source[k][name]});out[k]=d});return JSON.stringify(out,null,2)}
    function select(id){expanded.checked=true;let diag=["decomposition","stl","acf","pacf","stationarity","change-point"];if(diag.indexOf(id)>=0){task.currentIndex=1;diagnostics.text=JSON.stringify([id])}else if(id==="classification"||id==="clustering"){task.currentIndex=id==="classification"?2:3;diagnostics.text="[]"}else{task.currentIndex=0;let i=["arima","sarima","sarimax","var","global-ridge","croston","naive","seasonal-naive"].indexOf(id);method.currentIndex=i>=0?i:0}}
    function config(){return {task:["forecast","diagnostics","classification","clustering"][task.currentIndex],method:["arima","sarima","sarimax","var","global-ridge","croston","naive","seasonal-naive"][method.currentIndex],diagnostics:JSON.parse(diagnostics.text),order:JSON.parse(order.text),seasonal_order:JSON.parse(seasonalOrder.text),gap:Number(gap.text),embargo:Number(embargo.text),lags:Number(lags.text),difference:Number(difference.text),known_future:JSON.parse(known.text),past_covariates:JSON.parse(past.text),availability:JSON.parse(availability.text),var_columns:JSON.parse(varColumns.text),var_assumption:varReason.text,hierarchy:JSON.parse(hierarchy.text),training_series:JSON.parse(trainSeries.text),validation_series:JSON.parse(valSeries.text),label:label.currentValue||"",clusters:Number(clusters.text),seed:Number(seed.text),alpha:Number(alpha.text),croston_alpha:.1,change_penalty:3}}
    function restore(s){if(!s){expanded.checked=false;return}expanded.checked=true;task.currentIndex=["forecast","diagnostics","classification","clustering"].indexOf(s.task);method.currentIndex=["arima","sarima","sarimax","var","global-ridge","croston","naive","seasonal-naive"].indexOf(s.method);diagnostics.text=JSON.stringify(s.diagnostics);order.text=JSON.stringify(s.order);seasonalOrder.text=JSON.stringify(s.seasonal_order);gap.text=String(s.gap);embargo.text=String(s.embargo);lags.text=String(s.lags);difference.text=String(s.difference);known.text=JSON.stringify(s.known_future);past.text=JSON.stringify(s.past_covariates);availability.text=JSON.stringify(s.availability);varColumns.text=JSON.stringify(s.var_columns);varReason.text=s.var_assumption;hierarchy.text=JSON.stringify(s.hierarchy);trainSeries.text=JSON.stringify(s.training_series);valSeries.text=JSON.stringify(s.validation_series);clusters.text=String(s.clusters);seed.text=String(s.seed);alpha.text=String(s.alpha);for(let i=0;i<label.count;i++)if(label.valueAt(i)===s.label)label.currentIndex=i}
    Connections {target:timeSeries;function onSelectTemporal(id){panel.select(id)} }
    UiCheckBox {id:expanded;objectName:"temporalExpanded";text:"Faz53 gelişmiş temporal modüller";onToggled:timeSeries.invalidate()}
    ColumnLayout {visible:expanded.checked;Layout.fillWidth:true
        UiLabel {text:"Regular panel; max4000rows/8series/1000periods/200fits. Global, hierarchy ve whole-series clustering aynı calendar ister. Resample ayrı açık hazırlık işlemidir. Random tabular split yok; source ve RowId korunur.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiButton {objectName:"temporalHelp";text:"Differencing, exogenous ve ufuk yardımı";helpContext:"temporal.advanced";onClicked:panel.helpRequested(this,helpContext)}
        UiCombo {id:task;objectName:"temporalTask";accessibleLabel:"Temporal amaç";model:["Forecast/backtest","Development diagnostics","Whole-series classification","Whole-series clustering"];Layout.fillWidth:true;onActivated:timeSeries.invalidate()}
        UiCombo {id:method;objectName:"temporalMethod";accessibleLabel:"Temporal forecast yöntemi";model:["ARIMA","SARIMA","SARIMAX","VAR","Global lag Ridge","Croston demand","Naive","Seasonal naive"];Layout.fillWidth:true;onActivated:timeSeries.invalidate()}
        UiLabel {text:"p,d,q ve seasonal P,D,Q: p/q/P/Q≤2,d/D≤1; seasonal period yukarıda2–24. Difference0/1 yalnız VAR için; stationarity varsayımı kullanıcı gerekçesidir. ADF/KPSS tek başına durağanlık kanıtı değildir.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiTextField {id:order;objectName:"temporalOrder";Accessible.name:"ARIMA p d q JSON";text:"[1,0,0]";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiTextField {id:seasonalOrder;objectName:"temporalSeasonalOrder";Accessible.name:"Seasonal P D Q JSON";text:"[1,0,0]";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiTextField {id:diagnostics;objectName:"temporalDiagnostics";Accessible.name:"Diagnostics JSON yöntem listesi";text:'["acf","stationarity"]';Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiTextField {id:gap;objectName:"temporalGap";Accessible.name:"Origin ile değerlendirme arasında gap dönem";text:"0";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiTextField {id:embargo;objectName:"temporalEmbargo";Accessible.name:"Ek embargo dönem";text:"0";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiTextField {id:lags;objectName:"temporalLags";Accessible.name:"Lag ve ACF PACF gecikme sayısı";text:"4";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiTextField {id:difference;objectName:"temporalDifference";Accessible.name:"VAR differencing 0 veya1";text:"0";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiLabel {text:"SARIMAX: known_future ancak origin anında bilinen program/fiyat/takvim senaryosudur; realized weather gelecek diye kullanılamaz. Past covariate lagı max(horizon,test_periods)+gap+embargo kadar olmalı. İlk lag dönemlerinin targetları fit dışıdır; fill/bfill yok. Rol beyanı gerçek erişimin kanıtı değildir.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiCombo {id:covChoice;objectName:"temporalCovChoice";accessibleLabel:"Covariate VAR kolonu seçimi";model:timeSeries.columns;textRole:"name";valueRole:"id";Layout.fillWidth:true}
        UiTextField {id:covReason;Accessible.name:"Covariate origin erişim gerekçesi";placeholderText:"Origin anında nasıl biliniyor?";Layout.fillWidth:true}
        Flow {Layout.fillWidth:true;spacing:Theme.sm
            Repeater {model:["known","past","var"];UiButton {required property string modelData;text:modelData+" listesine ekle";onClicked:{let field=modelData==="known"?known:modelData==="past"?past:varColumns;let ids=JSON.parse(field.text);if(ids.indexOf(covChoice.currentValue)<0)ids.push(covChoice.currentValue);field.text=JSON.stringify(ids);if(modelData!=="var"){let notes=JSON.parse(availability.text);notes[covChoice.currentValue]=covReason.text;availability.text=JSON.stringify(notes)}timeSeries.invalidate()}}}
        }
        UiTextField {id:known;objectName:"temporalKnown";Accessible.name:"Known future ColumnIds JSON";text:"[]";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiTextField {id:past;objectName:"temporalPast";Accessible.name:"Past observed ColumnIds JSON";text:"[]";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiTextArea {id:availability;objectName:"temporalAvailability";Accessible.name:"Covariate access justification JSON";text:"{}";Layout.fillWidth:true;Layout.preferredHeight:65;onTextChanged:timeSeries.invalidate()}
        UiTextField {id:varColumns;objectName:"temporalVar";Accessible.name:"VAR other numeric ColumnIds JSON";text:"[]";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiTextField {id:varReason;objectName:"temporalVarReason";Accessible.name:"VAR stationarity gerekçesi";text:"";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiLabel {text:"Hierarchy ayrı bottom-up yetenek: [[parent,typedSeriesToken],...]. Seri tokenları raporda [group_type,group] JSON'dur. Parent gözlenen aggregate seri olamaz; tüm yapraklar tam bir kez kapsanır. Cycle/multiple-parent reddedilir. Aggregate interval covariance modeli olmadan üretilmez; MinT değil.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiTextArea {id:hierarchy;objectName:"temporalHierarchy";Accessible.name:"Bottom up hierarchy edges JSON";text:"[]";Layout.fillWidth:true;Layout.preferredHeight:65;onTextChanged:timeSeries.invalidate()}
        UiLabel {text:"Whole-series classification: her entity bir örnek, train/validation tokenları açık; label her kullanılan seride sabit categorical olmalı. Mean/std/slope/last özellikleri yalnız geçmiş prefix; scaling yalnız train entities. Clustering aynı calendar ve tüm prefix dizilerinin Euclidean standardize şeklidir, başarı/gerçek sınıf iddiası yok.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiCombo {id:label;objectName:"temporalLabel";accessibleLabel:"Whole series label kolonu";model:[{id:"",name:"Label yok"}].concat(timeSeries.columns);textRole:"name";valueRole:"id";Layout.fillWidth:true;onActivated:timeSeries.invalidate()}
        UiTextField {id:trainSeries;objectName:"temporalTrainSeries";Accessible.name:"Whole training series tokens JSON";text:"[]";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiTextField {id:valSeries;objectName:"temporalValSeries";Accessible.name:"Whole validation series tokens JSON";text:"[]";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiTextField {id:clusters;objectName:"temporalClusters";Accessible.name:"Whole series kmeans clusters";text:"2";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiTextField {id:seed;objectName:"temporalSeed";Accessible.name:"Temporal seed";text:"53";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiTextField {id:alpha;objectName:"temporalAlpha";Accessible.name:"Predictive alpha";text:"0.2";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiButton {objectName:"temporalRun";text:"Ayarları doğrula ve temporal işi başlat";primary:true;Layout.fillWidth:true;enabled:!timeSeries.busy&&!projects.busy&&!projects.readOnly;onClicked:{try{let s=panel.parent.spec();s.advanced=panel.config();timeSeries.create(JSON.stringify(s))}catch(e){localError.text="JSON/sayısal alanı kontrol edin"}}}
        UiLabel {id:localError;text:"";color:Theme.warning;wrapMode:Text.Wrap;Layout.fillWidth:true}
    }
    ColumnLayout {visible:(panel.report.advanced||{}).schema==="TemporalRun/v1";Layout.fillWidth:true
        UiLabel {objectName:"temporalReport";text:"Temporal task: "+((panel.report.advanced||{}).spec||{}).task+" · "+((panel.report.advanced||{}).spec||{}).method+"\nMASE denominator yalnız origin train; constant train scale tanımsız. Interval predictive, mean CI değil; Gaussian conditional on exog, global subgroup coverage garantisi yok. Gerçek holdout yalnız final eyleminde açılır. Out-of-source future exog dosyası/model persistence bu dilimde kapalı.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        Repeater {model:panel.report.groups||[];ColumnLayout {required property var modelData;Layout.fillWidth:true
            UiLabel {text:"Panel ID: "+modelData.series_id;wrapMode:Text.Wrap;Layout.fillWidth:true}
            Repeater {model:(panel.report.mode==="final"?modelData.final_metrics:modelData.comparisons)||[];ColumnLayout {required property var modelData;Layout.fillWidth:true
                UiLabel {text:modelData.method+" · gerçek ufuk raporu";font.bold:true}
                Repeater {model:modelData.per_horizon||[];UiLabel {required property var modelData;text:"h="+modelData.horizon+" · lead="+modelData.lead+" · n="+modelData.n+" · MAE="+modelData.mae+" · RMSE="+modelData.rmse+" · MASE="+(modelData.mase==null?"tanımsız":modelData.mase)+"\n"+(modelData.probabilistic ? JSON.stringify(modelData.probabilistic) : "Olasılıksal skor bu yöntemde desteklenmiyor.");wrapMode:Text.Wrap;Layout.fillWidth:true}}
                SearchCurve {points:(modelData.per_horizon||[]).map(p=>({x:p.horizon,y:p.mae}));title:"Ufuk bazlı MAE";xLabel:"Forecast horizon";yLabel:"mae";Layout.fillWidth:true;Layout.preferredHeight:180}
            }}
            Repeater {model:Object.keys(modelData.diagnostics||{}).map(k=>({kind:k,data:modelData.diagnostics[k]}));ColumnLayout {required property var modelData;Layout.fillWidth:true
                Repeater {model:modelData.data.values?[{name:modelData.kind,values:modelData.data.values}]:modelData.data.trend?[{name:modelData.kind+" trend",values:modelData.data.trend},{name:modelData.kind+" seasonal",values:modelData.data.seasonal},{name:modelData.kind+" residual",values:modelData.data.residual}]:[];TemporalDiagnosticPlot {required property var modelData;points:modelData.values.map((v,i)=>({x:i,y:v}));title:modelData.name+" · development only";Layout.fillWidth:true;Layout.preferredHeight:180}}
            }}
            UiLabel {text:panel.diagnosticSummary(modelData.diagnostics);wrapMode:Text.Wrap;Layout.fillWidth:true}
        }}
        UiLabel {text:JSON.stringify((panel.report.advanced||{}).series_task||{},null,2);wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiLabel {text:JSON.stringify((panel.report.advanced||{}).reconciliation||[],null,2);wrapMode:Text.Wrap;Layout.fillWidth:true}
    }
}
