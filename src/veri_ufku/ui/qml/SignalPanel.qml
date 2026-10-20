import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id:panel
    objectName:"signalPanel"
    signal helpRequested(var origin,string context)
    property bool enabledMode: expanded.checked
    property var report:timeSeries.report.advanced||{}
    function processingSummary(source){let out={};Object.keys(source).forEach(k=>{if(k!=="filter")out[k]=source[k]});if(source.filter){out.filter={};Object.keys(source.filter).forEach(k=>{if(["frequency_hz","gain","group_delay_seconds"].indexOf(k)<0)out.filter[k]=source.filter[k]})}return JSON.stringify(out)}
    function classificationSummary(source){if(!source)return "";let out={};Object.keys(source).forEach(k=>{if(["fit_window_ids","fit_row_ids","validation_window_ids","predictions","numeric_model"].indexOf(k)<0)out[k]=source[k]});out.prediction_preview=source.predictions.slice(0,12);return JSON.stringify(out,null,2)}
    function select(id){expanded.checked=true;for(let i=0;i<method.count;i++)if(method.model[i].id===id)method.currentIndex=i;targetRate.text=id==="resample"?"64":"0";detrend.currentIndex=id==="detrend"?2:0;filter.currentIndex=(id==="filter"||id==="zero-phase")?1:0;zero.checked=id==="zero-phase";task.currentIndex=id==="classification"?1:0}
    function config(primary){let cs=JSON.parse(channels.text);if(!cs.length)cs=[primary];let units=JSON.parse(channelUnits.text);cs.forEach(c=>{if(!units[c])units[c]=unit.text});return {family:"signal",operation:method.currentValue||"spectrogram",task:task.currentIndex===0?"analysis":"classification",sample_rate:Number(rate.text),time_unit:["s","ms","us","ns"][timeUnit.currentIndex],channels:cs,channel_units:units,bandlimit_hz:Number(band.text),acquisition_note:note.text,target_rate:Number(targetRate.text),allow_band_loss:loss.checked,mode:mode.currentIndex===0?"offline":"online",detrend:["none","constant","linear"][detrend.currentIndex],window:["hann","boxcar","hamming","blackman"][window.currentIndex],segment_length:Number(length.text),overlap:Number(overlap.text),scaling:scaling.currentIndex===0?"density":"spectrum",filter_type:["none","lowpass","highpass","bandpass","bandstop"][filter.currentIndex],cutoff:JSON.parse(cutoff.text),order:Number(order.text),zero_phase:zero.checked,prominence:Number(prominence.text),peak_distance:Number(distance.text),event:event.currentValue||"",block_columns:JSON.parse(blocks.text),train_recordings:JSON.parse(train.text),validation_recordings:JSON.parse(validation.text),label:label.currentValue||"",seed:Number(seed.text)}}
    function restore(s){if(!s){expanded.checked=false;return}expanded.checked=true;for(let i=0;i<method.count;i++)if(method.model[i].id===s.operation)method.currentIndex=i;task.currentIndex=s.task==="analysis"?0:1;rate.text=String(s.sample_rate);timeUnit.currentIndex=["s","ms","us","ns"].indexOf(s.time_unit);channels.text=JSON.stringify(s.channels);channelUnits.text=JSON.stringify(s.channel_units);band.text=String(s.bandlimit_hz);note.text=s.acquisition_note;targetRate.text=String(s.target_rate);loss.checked=s.allow_band_loss;mode.currentIndex=s.mode==="offline"?0:1;detrend.currentIndex=["none","constant","linear"].indexOf(s.detrend);window.currentIndex=["hann","boxcar","hamming","blackman"].indexOf(s.window);length.text=String(s.segment_length);overlap.text=String(s.overlap);scaling.currentIndex=s.scaling==="density"?0:1;filter.currentIndex=["none","lowpass","highpass","bandpass","bandstop"].indexOf(s.filter_type);cutoff.text=JSON.stringify(s.cutoff);order.text=String(s.order);zero.checked=s.zero_phase;prominence.text=String(s.prominence);distance.text=String(s.peak_distance);blocks.text=JSON.stringify(s.block_columns);train.text=JSON.stringify(s.train_recordings);validation.text=JSON.stringify(s.validation_recordings);seed.text=String(s.seed);for(let pair of [[event,s.event],[label,s.label]])for(let i=0;i<pair[0].count;i++)if(pair[0].valueAt(i)===pair[1])pair[0].currentIndex=i}
    Connections {target:timeSeries;function onSelectSignal(id){panel.select(id)}}
    UiCheckBox {id:expanded;objectName:"signalEnabled";text:"Faz54 · sinyal işleme";property string helpContext:"signal.sampling";onToggled:timeSeries.invalidate()}
    ColumnLayout {
        visible:panel.enabledMode
        Layout.fillWidth:true
        UiLabel {text:"Sayısal zaman s/ms/us/ns, düzenli fs; zaman ve ana kanal yukarıdan seçilir. Düzensiz/duplicate sıra FFT için reddedilir; otomatik interpolation/sort yok.32768 satır/16kayıt/8kanal/8192örnek/kayıt;131072 STFT hücresi/2000window. Çıktı kaynak veriyi değiştirmez.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiCombo {id:method;objectName:"signalMethod";model:timeSeries.signalMethods();textRole:"label";valueRole:"id";accessibleLabel:"Sinyal yeteneği";Layout.fillWidth:true;onActivated:panel.select(currentValue)}
        UiCombo {id:task;objectName:"signalTask";model:["Spektrum/işleme/feature extraction","Blok ayrımlı classification"];accessibleLabel:"Sinyal görevi";Layout.fillWidth:true;onActivated:timeSeries.invalidate()}
        UiTextField {id:rate;objectName:"signalRate";text:"128";Accessible.name:"Sampling rate Hz";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiCombo {id:timeUnit;objectName:"signalTimeUnit";model:["s","ms","us","ns"];accessibleLabel:"Kaynak zaman birimi";Layout.fillWidth:true;onActivated:timeSeries.invalidate()}
        UiTextField {id:unit;objectName:"signalUnit";text:"dimensionless";Accessible.name:"Kanal ölçüm birimi beyanı";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiTextField {id:channels;objectName:"signalChannels";text:"[]";Accessible.name:"Kanal ColumnId listesi JSON, boşsa ana kanal";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiTextField {id:channelUnits;objectName:"signalChannelUnits";text:"{}";Accessible.name:"Kanal ColumnId birim eşlemesi JSON";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiCombo {id:column;objectName:"signalRoleColumn";model:timeSeries.columns;textRole:"name";valueRole:"id";accessibleLabel:"Sinyal kanal veya blok kolonu";Layout.fillWidth:true}
        RowLayout {UiButton {text:"Kanal ekle";onClicked:{let a=JSON.parse(channels.text);if(column.currentValue&&a.indexOf(column.currentValue)<0)a.push(column.currentValue);channels.text=JSON.stringify(a);timeSeries.invalidate()}} UiButton {text:"Kişi/cihaz/oturum bloku ekle";onClicked:{let a=JSON.parse(blocks.text);if(column.currentValue&&a.indexOf(column.currentValue)<0)a.push(column.currentValue);blocks.text=JSON.stringify(a);timeSeries.invalidate()}}}
        UiTextField {id:band;objectName:"signalBand";text:"0";Accessible.name:"Kaynak bandlimit Hz,0 bilinmiyor";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiTextField {id:note;objectName:"signalAcquisition";text:"Analog anti-alias acquisition bilinmiyor";Accessible.name:"Sampling analog bant ve anti alias gerekçesi";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiLabel {text:"Nyquist fs/2. Örneklenmiş veriden geçmiş aliasing olmadığı kanıtlanamaz. Bandlimit beyanı fs/2 altında olmalı;0 bilinmiyor. Resample düşük geçiren anti-alias FIR uygular; yeni bant dışını kaybetmek ayrı onaydır.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiTextField {id:targetRate;objectName:"signalTargetRate";text:"0";Accessible.name:"Resample hedef Hz,0 değişiklik yok";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiCheckBox {id:loss;objectName:"signalBandLoss";text:"Yeni Nyquist nedeniyle yüksek frekans bant kaybını onaylıyorum";onToggled:timeSeries.invalidate()}
        UiCombo {id:mode;objectName:"signalMode";model:["Offline tüm kayıt","Online için causal dönüşüm kontrolü"];accessibleLabel:"Offline online sinyal modu";Layout.fillWidth:true;onActivated:timeSeries.invalidate()}
        UiCombo {id:detrend;objectName:"signalDetrend";model:["Detrend yok","Sabit mean çıkar","Linear detrend"];accessibleLabel:"Sinyal detrending";Layout.fillWidth:true;onActivated:timeSeries.invalidate()}
        UiCombo {id:window;objectName:"signalWindow";model:["hann","boxcar","hamming","blackman"];accessibleLabel:"DFT periodic window";Layout.fillWidth:true;onActivated:timeSeries.invalidate()}
        UiTextField {id:length;objectName:"signalLength";text:"128";Accessible.name:"STFT Welch feature window length örnek";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiTextField {id:overlap;objectName:"signalOverlap";text:"64";Accessible.name:"Overlap örnek, stride en az8";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiCombo {id:scaling;objectName:"signalScaling";model:["Welch density: unit²/Hz","Welch power spectrum: unit²"];accessibleLabel:"Welch power normalizasyonu";Layout.fillWidth:true;onActivated:timeSeries.invalidate()}
        UiLabel {text:"FFT one-sided peak amplitude: |FFT|/sum(window), iç bin×2; DC/Nyquist×1. PSD: |FFT|²/(fs sum(window²)), iç bin×2. Welch segmentleri ortalar. STFT padding/boundary yok; merkez zaman tanımlayıcıdır, kullanılabilirlik window sonundadır. Resolution fs/n; off-bin amplitude/window leakage sınırlıdır.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiCombo {id:filter;objectName:"signalFilter";model:["Filtre yok","Butterworth lowpass","Butterworth highpass","Butterworth bandpass","Butterworth bandstop"];accessibleLabel:"Butterworth SOS filtre";Layout.fillWidth:true;onActivated:timeSeries.invalidate()}
        UiTextField {id:cutoff;objectName:"signalCutoff";text:"[20]";Accessible.name:"Filter cutoff Hz listesi JSON";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiTextField {id:order;objectName:"signalOrder";text:"4";Accessible.name:"Butterworth order1..8";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiCheckBox {id:zero;objectName:"signalZeroPhase";text:"Zero-phase forward/backward · offline-only";onToggled:timeSeries.invalidate()}
        UiLabel {text:"Causal SOS zero/rest başlangıç, transient korunur; delay frekansa bağlıdır, zaman sessiz kaydırılmaz. Zero-phase odd padding geleceği kullanır ve etkin order/gain karesini değiştirir. Resample/polyphase ve tam kayıt detrend de offline-only. Online modu streaming deploy/model prediction değildir.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiTextField {id:prominence;objectName:"signalProminence";text:"0.1";Accessible.name:"Peak prominence measurement unit";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiTextField {id:distance;objectName:"signalPeakDistance";text:"1";Accessible.name:"Peak distance sample/bin";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiCombo {id:event;objectName:"signalEvent";model:[{id:"",name:"Event yok"}].concat(timeSeries.columns);textRole:"name";valueRole:"id";accessibleLabel:"Kaynak event kolonu contiguous segments";Layout.fillWidth:true;onActivated:timeSeries.invalidate()}
        UiCombo {id:label;objectName:"signalLabel";model:[{id:"",name:"Label yok"}].concat(timeSeries.columns);textRole:"name";valueRole:"id";accessibleLabel:"Classification recording label";Layout.fillWidth:true;onActivated:timeSeries.invalidate()}
        UiTextField {id:blocks;objectName:"signalBlocks";text:"[]";Accessible.name:"Kişi cihaz oturum blok ColumnId listesi JSON";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiTextField {id:train;objectName:"signalTrain";text:"[]";Accessible.name:"Train recording typed token list JSON";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiTextField {id:validation;objectName:"signalValidation";text:"[]";Accessible.name:"Validation recording typed token list JSON";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiTextField {id:seed;objectName:"signalSeed";text:"54";Accessible.name:"Sinyal classifier seed";Layout.fillWidth:true;onTextEdited:timeSeries.invalidate()}
        UiLabel {text:"Split tüm kayıtlar üzerinde window üretiminden önce: seçilen her kişi/cihaz/oturum kimliği iki tarafta ayrık. Aynı kaydın overlap pencereleri asla iki tarafa dağılmaz. Train-only scaler/LogisticRegression; window n bağımsız kişi n değildir. Validation final test diye sunulmaz; tuning ve yeni dosyada fitted prediction kapalı.";wrapMode:Text.Wrap;Layout.fillWidth:true}
        UiButton {objectName:"signalHelp";property string helpContext:"signal.sampling";text:"Sample rate, spektrum ve filtre yardımı";onClicked:panel.helpRequested(this,"signal.sampling")}
        UiButton {objectName:"signalRun";text:"Sinyali doğrula ve hesapla";primary:true;Layout.fillWidth:true;enabled:!timeSeries.busy&&!projects.busy&&!projects.readOnly;onClicked:{try{timeSeries.create(JSON.stringify(panel.parent.spec()))}catch(e){error.text="JSON ve sayısal alanları kontrol edin"}}}
        UiLabel {id:error;text:"";color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap}
    }
    ColumnLayout {
        visible:panel.report.schema==="SignalRun/v1"
        Layout.fillWidth:true
        UiLabel {objectName:"signalReport";text:"Sinyal · "+(panel.report.spec||{}).operation+" · "+(panel.report.spec||{}).mode+" · önkontrol "+JSON.stringify(panel.report.preflight);Layout.fillWidth:true;wrapMode:Text.Wrap}
        Repeater {model:panel.report.recordings||[];ColumnLayout {
            required property var modelData
            Layout.fillWidth:true
            UiLabel {text:"Kayıt "+modelData.recording_id+" · "+modelData.partition+" · source n="+modelData.source_n+" · fs="+modelData.sample_rate_hz+"Hz · başlangıç="+modelData.source_time_origin+modelData.source_time_unit;Layout.fillWidth:true;wrapMode:Text.Wrap}
            Repeater {model:modelData.channels;ColumnLayout {required property var modelData;Layout.fillWidth:true
                UiLabel {text:"Kanal "+modelData.column_id+" · "+modelData.unit+" · FFT peak: "+JSON.stringify(modelData.frequency_peaks);Layout.fillWidth:true;wrapMode:Text.Wrap}
                SignalSpectrogram {objectName:"signalSpectrogram";spectrumData:modelData.stft;unit:modelData.unit;Layout.fillWidth:true}
                TemporalDiagnosticPlot {title:"FFT peak amplitude ("+modelData.unit+") · Hz";points:modelData.fft.amplitude.map((y,i)=>({x:modelData.fft.frequency_hz[i],y:y}));xLabel:"Hz";Layout.preferredHeight:180;Layout.fillWidth:true}
                TemporalDiagnosticPlot {title:"Welch "+modelData.welch.scaling+" ("+modelData.unit+modelData.welch.unit_suffix+") · Hz";points:modelData.welch.values.map((y,i)=>({x:modelData.welch.frequency_hz[i],y:y}));xLabel:"Hz";Layout.preferredHeight:180;Layout.fillWidth:true}
                UiLabel {text:panel.processingSummary(modelData.processing);Layout.fillWidth:true;wrapMode:Text.Wrap}
            }}
            UiLabel {text:"Event segments: "+JSON.stringify(modelData.events);Layout.fillWidth:true;wrapMode:Text.Wrap}
        }}
        UiLabel {text:panel.classificationSummary(panel.report.classifier);Layout.fillWidth:true;wrapMode:Text.Wrap}
    }
}
