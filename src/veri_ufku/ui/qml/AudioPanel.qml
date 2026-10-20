import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id:panel
    objectName:"audioPanel"
    property string helpContext:"model.audio"
    signal helpRequested(var origin,string context)
    readonly property var result:audioAnalysis.historyReport
    readonly property var tasks:["features","classification","transcribe"]
    function config(){return {task:tasks[task.currentIndex],target_rate:Number(rate.text),channel:Number(channel.text),n_fft:Number(fft.text),hop:Number(hop.text),n_mels:Number(mels.text),n_mfcc:Number(mfcc.text),f_min:0,f_max:Number(maxfreq.text),silence_dbfs:Number(silence.text),clip_level:Number(clip.text),gain_db:Number(gain.text),seed:Number(seed.text),stt_folder:folder.text,language:language.text,stt_consent:consent.checked}}
    function number(v){return typeof v==="number"?v.toFixed(4):"—"}
    function metrics(){var m=panel.result.metrics||{};return m.n!==undefined?"Validation n="+m.n+" · accuracy="+number(m.accuracy)+" · aynı split baseline="+number(m.baseline_accuracy)+"\nEtiket sırası: "+m.labels.join(", ")+" · confusion gerçek → tahmin: "+JSON.stringify(m.confusion):"Model/metric hesabı yok"}
    function quality(v){var a=v.source_quality||{},b=v.quality||{};return "Kaynak: clipping="+number(100*a.clipped_sample_fraction)+"% · RMS="+number(a.rms)+" · sessiz sample="+number(100*a.silence_sample_fraction)+"%\nİşlenmiş: clipping="+number(100*b.clipped_sample_fraction)+"% · sessiz window="+number(100*b.silence_window_fraction)+"% · dış full-scale="+number(100*b.outside_fullscale_fraction)+"%"}
    Connections {target:audioAnalysis;function onSelectAudio(value){expanded.checked=true;task.currentIndex=panel.tasks.indexOf(value)}}
    UiCheckBox {id:expanded;objectName:"audioExpanded";text:"Faz58 yerel ses çalışma alanını göster";Layout.fillWidth:true}
    ColumnLayout {visible:expanded.checked;Layout.fillWidth:true;spacing:Theme.sm
        UiLabel {text:"Yerel WAV/FLAC · segment/kanal · konuşmacı sızıntısı";font.bold:true;Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiLabel {text:"WAV/FLAC, klasör veya audio.json. AudioManifest/v1: classes/recordings; id/file/label/label_status/speaker/session/source_recording/segments. Segment id/start_frame/end_frame kaynak sample frame aralığıdır. Folder etiketleri proposed; training için human gerekir. Ses kopyası proje içinde, kaynak değişmez.";Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiTextField {id:source;objectName:"audioSource";Accessible.name:"Yerel ses kaynağı yolu";placeholderText:"Mutlak WAV/FLAC, klasör veya audio.json";Layout.fillWidth:true}
        UiButton {objectName:"audioChoose";text:"Ses kaynağını önizle";enabled:!audioAnalysis.busy&&!imports.busy&&!projects.busy;onClicked:imports.choose(source.text);Layout.fillWidth:true}
        UiButton {objectName:"audioImport";text:"Önizlenen ses snapshot'ını import et";enabled:imports.ready&&!projects.busy&&!audioAnalysis.busy;onClicked:imports.importData(true);Layout.fillWidth:true}
        StateNotice {heading:"Ses import durumu";detail:imports.errorText||imports.message;kind:imports.errorText?"error":"info";Layout.fillWidth:true}
        UiLabel {text:"64recording/256segment;16MiB dosya,60s/2Mframe,1–2kanal,8–96kHz. PCM16/24/32 veya WAV float.4M toplam işleme frame bütçesi. Bozuk/nonfinite/aşırı büyükte durur; sessiz trim/normalize yok. Canlı mikrofon kaydı, speaker diarization ve event detection ayrı, burada desteklenmiyor.";Layout.fillWidth:true;wrapMode:Text.Wrap}
        ColumnLayout {enabled:!audioAnalysis.busy;Layout.fillWidth:true
            UiCombo {id:task;objectName:"audioTask";accessibleLabel:"Ses alt yeteneği";model:["Waveform/spectrogram/MFCC/log-mel/kalite","Audio classification — grup holdout","Optional yerel Vosk speech-to-text"];Layout.fillWidth:true}
            UiLabel {text:"Target rate0=değişmez; kanal0/1 açık seçilir, downmix yok. Resample Kaiser5 anti-alias FIR; Nyquist üstü içerik kaldırılır. Seviye digital full-scale1, fiziksel SPL değil.";Layout.fillWidth:true;wrapMode:Text.Wrap}
            UiTextField {id:rate;objectName:"audioRate";Accessible.name:"Ses hedef sampling rate Hz";text:"16000";Layout.fillWidth:true}
            UiTextField {id:channel;objectName:"audioChannel";Accessible.name:"Ses kanal index";text:"0";Layout.fillWidth:true}
            UiTextField {id:fft;objectName:"audioFFT";Accessible.name:"Audio FFT window samples";text:"256";Layout.fillWidth:true}
            UiTextField {id:hop;objectName:"audioHop";Accessible.name:"Audio hop samples";text:"128";Layout.fillWidth:true}
            UiTextField {id:mels;objectName:"audioMels";Accessible.name:"Mel band sayısı";text:"24";Layout.fillWidth:true}
            UiTextField {id:mfcc;objectName:"audioMFCC";Accessible.name:"MFCC coefficient sayısı";text:"13";Layout.fillWidth:true}
            UiTextField {id:maxfreq;objectName:"audioMaxFrequency";Accessible.name:"Mel üst frekans Hz 0 Nyquist";text:"0";Layout.fillWidth:true}
            UiTextField {id:silence;objectName:"audioSilence";Accessible.name:"Silence eşiği dBFS";text:"-60";Layout.fillWidth:true}
            UiTextField {id:clip;objectName:"audioClipping";Accessible.name:"Clipping sample level eşiği";text:"0.999";Layout.fillWidth:true}
            UiTextField {id:gain;objectName:"audioGain";Accessible.name:"Train augmentation gain dB";text:"0";Layout.fillWidth:true}
            UiTextField {id:seed;objectName:"audioSeed";Accessible.name:"Audio group split seed";text:"58";Layout.fillWidth:true}
            UiLabel {text:"Gain augmentation yalnız train; >full-scale olursa reddedilir. Sampling rate/time anlamı değiştirilmez. MFCC/logmel summary scaler/model yalnız train fit; aynı kaydın overlap segmentleri ve bilinen speaker/session/source/decoded duplicate aynı split component. Bilinmeyen konuşmacı bağımsızlığı iddia edilmez. Final test metric burada kapalı.";Layout.fillWidth:true;wrapMode:Text.Wrap}
            UiTextField {id:folder;objectName:"audioSTTFolder";Accessible.name:"Yerel speech model klasörü";placeholderText:"Optional STT: audio-model.json ve Vosk ağırlıkları";Layout.fillWidth:true}
            UiTextField {id:language;objectName:"audioLanguage";Accessible.name:"Speech model dil beyanı";text:"tr";Layout.fillWidth:true}
            UiCheckBox {id:consent;objectName:"audioSTTConsent";text:"Yerel model lisans/dil/hash beyanını inceledim; optional STT'yi açıkça başlatıyorum";Layout.fillWidth:true}
            UiLabel {text:"STT yalnız yerel Vosk0.3.45/LocalVosk/v1 hash/lisans/dataset manifest. Küçük model yoksa unavailable; model otomatik indirilmez, internet zorunlu değil. Timestamp/confidence yalnız backend word alanları varsa; confidence kalibre doğruluk değildir. WER/CER yalnız tam seçili segmentin gerçek human referansı ile. Whole recording referansı alt segmentlere yeniden kullanılmaz.";color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap}
            UiButton {objectName:"audioRun";text:"Ses alt yeteneğini CPU'da çalıştır";primary:true;enabled:audioAnalysis.canAudioRun;onClicked:{try{audioAnalysis.startAudio(JSON.stringify(panel.config()))}catch(error){localError.text="Ses parametrelerini kontrol edin"}} Layout.fillWidth:true}
        }
        UiLabel {id:localError;text:"";color:Theme.warning;Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiButton {objectName:"audioCancel";text:"Ses işini iptal et";visible:audioAnalysis.busy;onClicked:audioAnalysis.cancel();Layout.fillWidth:true}
        StateNotice {heading:"Ses hesap durumu";detail:audioAnalysis.errorText||audioAnalysis.message;kind:audioAnalysis.errorText?"error":audioAnalysis.busy?"loading":"info";Layout.fillWidth:true}
        UiLabel {objectName:"audioSummary";text:panel.result.status?panel.result.status+" · "+((panel.result.audio_spec||{}).task||"")+" · segment="+(panel.result.segments||[]).length+"\n"+panel.metrics():"Henüz ses run yok";Layout.fillWidth:true;wrapMode:Text.Wrap}
        Repeater {model:panel.result.previews||[];ColumnLayout {required property var modelData;Layout.fillWidth:true
            UiLabel {text:modelData.segment_id+" · kaynak "+modelData.source_sample_rate+"Hz / "+modelData.source_channels+"kanal · seçili "+modelData.sample_rate+"Hz / "+modelData.duration_seconds.toFixed(3)+"s\nKaynak kalite: "+JSON.stringify(modelData.source_quality)+"\nProcessed kalite: "+JSON.stringify(modelData.quality)+"\nMFCC: "+JSON.stringify(modelData.mfcc_mean);Layout.fillWidth:true;wrapMode:Text.Wrap}
            UiLabel {text:"Waveform min/max zarfı · x=saniye, y=digital full-scale ±1";Layout.fillWidth:true;wrapMode:Text.Wrap}
            Canvas {objectName:"audioWaveform";Layout.preferredWidth:360;Layout.preferredHeight:120;property var values:modelData.waveform;onValuesChanged:requestPaint();onPaint:{var c=getContext("2d"),n=values.length;c.fillStyle="#202532";c.fillRect(0,0,width,height);c.strokeStyle="#ff8a35";c.beginPath();for(var i=0;i<n;i++){c.moveTo(i*width/n,height*(1-values[i].min)/2);c.lineTo(i*width/n,height*(1-values[i].max)/2)}c.stroke()}}
            UiLabel {text:"Spectrogram · x=saniye, y=0..Nyquist Hz · one-sided PSD dB/Hz; renk [-120,0]dB görsel aralık, istatistik kırpılmaz; time stride="+modelData.spectrogram_frame_stride;Layout.fillWidth:true;wrapMode:Text.Wrap}
            Canvas {objectName:"audioSpectrogram";Layout.preferredWidth:360;Layout.preferredHeight:180;property var values:modelData.spectrogram_db;onValuesChanged:requestPaint();onPaint:{var c=getContext("2d"),n=values.length;if(!n)return;var b=values[0].length;for(var t=0;t<n;t++)for(var f=0;f<b;f++){var v=Math.max(0,Math.min(1,(values[t][f]+120)/120));c.fillStyle=Qt.rgba(v,0.2+0.5*v,1-v,1);c.fillRect(t*width/n,(b-f-1)*height/b,width/n+1,height/b+1)}}}
        }}
        Repeater {model:(panel.result.audio_spec||{}).task==="transcribe"?panel.result.predictions||[]:[];UiLabel {required property var modelData;text:modelData.segment_id+" · model önerisi\n"+modelData.text+"\n"+JSON.stringify(modelData.metrics)+"\n"+JSON.stringify(modelData.words);Layout.fillWidth:true;wrapMode:Text.Wrap}}
        UiCombo {id:saved;objectName:"audioSaved";accessibleLabel:"Kalıcı audio kayıtları";model:audioAnalysis.savedRuns;textRole:"label";valueRole:"id";Layout.fillWidth:true}
        UiButton {objectName:"audioOpen";text:"Kalıcı ses snapshot/model aç";enabled:!audioAnalysis.busy&&saved.currentIndex>=0;onClicked:audioAnalysis.openRun(saved.currentValue);Layout.fillWidth:true}
        UiButton {objectName:"audioPredict";text:"Yeni ses snapshot'ında classification prediction";enabled:!audioAnalysis.busy&&!!panel.result.model_kind;onClicked:audioAnalysis.predictData();Layout.fillWidth:true}
        UiLabel {objectName:"audioPrediction";text:(audioAnalysis.predictionReport.predictions||[]).length?"Yeni segment prediction: "+audioAnalysis.predictionReport.predictions.length+" · fit yok · model önerisi (ilk8)\n"+(audioAnalysis.predictionReport.predictions||[]).slice(0,8).map(function(v){return v.segment_id+" → "+v.label}).join("\n"):"";Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiLabel {text:"Ses/transkript loglanmaz. Transcription çıktısı model önerisidir, human ground truth değil.";Layout.fillWidth:true;wrapMode:Text.Wrap}
        UiButton {objectName:"audioHelp";text:"MFCC, resampling, WER/CER ve speaker leakage öğren";helpContext:"model.audio";onClicked:panel.helpRequested(this,helpContext);Layout.fillWidth:true}
    }
}
