# Faz62 — bounded local stream ve özel hedefler

2026-10-15 UTC; DEC62-01; ENV-62. Teknik teslim ile resmî kabul ayrıdır.
Faz durumu sürüyor, olgunluk deneysel, kapsam isteğe bağlı. Önceki resmî kapılar
ve özellikle GUI toplam2GiB bellek açığı korunur. Faz63 için yetki yok.

<a id="e62-native"></a>
## E62-NATIVE — kapsam ve kabul sınırı

Yerel değişmez snapshot üzerinde dosya append/event simülatörü; canlı dosya izleyicisi
ve ağ broker'ı yok. Açık Başlat eylemi olmadan replay çalışmaz. Tek registry,
ComputeBudget, Provenance, neural safe artifact ve ProjectStore parent-ACK/ACTIVE
protokolü genişletildi; yeni run/registry deposu kurulmadı. Kaynak dosya değişmez.

StreamEvent/v1: artan integer event ID; event/processing/feedback time aynı epoch'ta
saniye; finite numeric1–16feature; binary0/1target. Processing time monoton; clock
kaynak verisidir. Feedback zamanı processing time'dan erken olamaz. Missing label ve
feedback time birlikte null. Daha önce zamanı gelmiş feedback, sıradaki prediction'dan
önce; aynı zamanlı feedback kendi prediction'ından sonra işlenir. Due time/ID sırası
sabit. Önce test, sonra score/scaler/model partial_fit. İlk eğitimsiz prediction NA,
skor dışı. Son processing time'dan sonraki feedback pending; sahte flush/eğitim yok.

StandardScaler.partial_fit + SGDClassifier(log_loss, constant eta.01, shuffleFalse,
seed62, classes0/1). Scaler yalnız eğitim feedback'i geldiğinde güncellenir; model
katsayıları yeni ölçeğe taşınarak raw-input decision function korunur. Genel offline
modeller online sayılmaz. Drift: son32scored0/1loss'un iki16yarısı farkı>.25; alarm
istatistiksel kanıt değil. Alarm-only varsayılan; reset seçilirse scaler/model açıkça
sıfırlanır ve generation artar. Eksik feedback skorlanmaz, negatif sayılmaz.

Tumbling window event veya processing clock ile; watermark=max_event−lateness.
Late reject veya quarantine; karantina eğitim/pencere dışıdır, kaynak snapshot
korunur, son64late RowId/SourceRecordId önizlemesi saklanır. Pending ve active window
sınırı ayrı ayrı2–256; dolunca hata, sessiz drop yok. Son64prediction,32loss; okuma
1–128row chunk;100000row önkontrolü,16feature,2MiB safeJSON. Aktif son pencere
kısmi/open kalır; kapalı pencere sayısı ve açık count'lar checkpoint'te.

Checkpoint numeric scaler/model durumu, cursor, pending label/tahmin/ham feature,
window, loss/drift/generation, kaynak fingerprint/spec/sklearn hash ve kaynak kimliği
saklar. Object import/pickle yok. Parent atomik yayın ve ACK sonrası cursor durable.
İptalde tamamlanmamış chunk son durable checkpoint'e geri alınır. Resume açık ayrı
buton; running/canceled/budget_exhausted kayıt açılır. Aynı snapshot/spec/backend ve
test-use geçmişi gerekir; next cursor tekrar öğrenilmez. Duplicate/reordered integer
ID reject. Yeni run resume_from ile bağlı; immutable cursor/hash journal kontrolü.
Aynı olmayan sürüm/cihazda bit eşitliği ve dış broker exactly-once garantisi yok.
Append edilen yeni harici dosyaya devam bu yetenekte yok; kaynak yeniden snapshot
olmalıdır. Disk artefact birikimi mevcut proje kota politikasına tabidir.

Özel hedefler TargetRecipe/v1 ile ayrı: explicit development train/pool/eval role
kolonu, train-only scaler; otomatik split yok. Final test role reddedilir, önceki
Faz16 test-use defteri korunur. Group/time split üyeliği upstream hazırlanmalıdır;
burada onun doğrulanmış birleşik planı olduğu iddia edilmez.640row toplam, train256,
eval256,pool128,feature16. Prediction sonucu eval RowId/SourceRecordId sırasıyla
bağlıdır. Mevcut model paketini değiştirmez; yalnız güvenli sonuç saklama, yeni-data
model persistence/predict unavailable.

Multi-label:2–8binary indicator, bağımsız LogisticRegression; subset accuracy ve
Hamming loss. Multi-output:2–8numeric target, Ridge(alpha1), hedef başına RMSE;
farklı birimlerin ortalama skoru yok. Ordinal: açık unique string order; nominal
logistic probability + absolute rank-loss için median karar. Numeric regression veya
proportional-odds model diye sunulmaz. PU unavailable: class-prior/selection varsayımı
ve doğrulanmış backend yok; unlabeled negatif değil. Semi-supervised: LabelPropagation
RBF gamma1/maxiter200;0/1/−1; training pool null/−1. Inductive yolda eval graph dışı.
Açık transductive seçim eval FEATURES'i graph'a ekler, eval truth asla fit etmez;
bağımsız inductive test skoru değildir. Convergence flag raporlanır.

Registry model.stream.replay/scaler/partial-fit ve model.special.multilabel/
multioutput/ordinal/semisupervised. model.special.pu ve model.stream.broker açık
unavailable. QML StreamPanel tüm destekli yollar, iptal/devam/kayıt açma ve çevrimdışı
yardım sağlar; GUI tek feature, multioutput/multilabel iki hedef; adapter üst sınırları
daha geniş. Öğrenme stream/window, prequential/drift, özel hedef varsayımları3makale.

<a id="e62-validation"></a>
## E62-VALIDATION — gerçek kontroller

Kaynak ve kurulu wheel kanıtları bu klasörde ayrı JUnit ve walkthrough dosyalarıdır.
[Kaynak çekirdek](phase62/source-core-current.xml),
[GUI son kaynak](phase62/source-final-gui/walkthrough.json),
[bellek](phase62/memory.json), [ortam](phase62/environment.json),
[wheel](phase62/wheel.json), [kapılar](phase62/gates.json),
[dondurma](phase62/frozen-head.json), [doğrulama](phase62/verification.json).
Çalıştırılmayan fiziksel masaüstü/insan/AT/minimum donanım/offlineinstaller/remote CI
başarılı sayılmaz. Tam depo regresyonu iddiası yok; seçilmiş komşu testler çalışır.

Başarısız koşular korunur: ilk source GUI1fail toplam2GiB kapısı
[source-gui-first.xml](phase62/source-gui-first.xml). Geçici explicit4GiB fixture ile
önce5pass [source-gui-4g](phase62/source-gui-4g.xml); default değişmedi. İlk native
checkpoint restore NumPy scalar tür hatası düzeltildi; sonraki özel-target roundtrip
4tuple/list assertion failure [source-native-final](phase62/source-native-final.xml)
normalize recipe list ile düzeltildi; ayrı21pass [source-native-current](phase62/source-native-current.xml).
İlk core126pass/1taxonomy expectation fail [source-core](phase62/source-core.xml);
yeni konular workflow yerine model eğitim dalına taşındı; sonraki127pass
[source-core-final](phase62/source-core-final.xml). Bunlar tek aggregate başarılı
koşu gibi toplanmaz. Ölçüm betiğinin ilk psutil eksikliği /proc RSS ile giderildi;
çalışma bağımlılığı eklenmedi. Son kaynak/wheel sayıları verification.json içindedir.

Bellek CPU fresh subprocess512/4096: peak675065856/679862272byte; serialized state
12667/12791byte; pending peak1, closed511/4095. Bu bounded state/RSS ölçek örneğidir;
sonsuz stream,100000row performansı veya GUI2GiB kabulü değildir.

## Resmî açıklar

PU, broker, live tail, multiclass online, yeni snapshot'a append-resume ve özel hedef
fitted-model/new-data prediction mevcut değil. GUI toplam2GiB ilk denemede engelli;
4GiB işlevsel kanıt minimum donanımı kapatmaz. Önceki tüm resmî açıklar
[önceki hafıza](phase62/prior-project_state.txt) ile korunur. Stage/commit/push yok.

## Resmî backend kaynakları

SGD partial_fit/classes ve constant-learning-rate sözleşmesi:
[SGDClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.SGDClassifier.html).
Incremental scaler:
[StandardScaler](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html).
LabelPropagation inductive predict ve transductive etiketsiz düğümler:
[resmî API](https://scikit-learn.org/stable/modules/generated/sklearn.semi_supervised.LabelPropagation.html).
Geliştirme sırasında2026-10-15 incelendi; uygulama bu adreslere ağ isteği yapmaz.

## Son teslim ve alt koşular

129source/129wheel seçilmiş core: [source](phase62/source-core-delivery.xml),
[wheel](phase62/wheel-core-final.xml);26native dahil, tam depo regresyonu değil.
350byte-eşit package,4freshXDG. Son GUI source/wheel mixed6pass/1fail;7pass diye
sunulmaz. Failure kısa stream checkpoint'ini predicate ile gözlerken işin bitmesi:
[source](phase62/source-final-gui/gui.xml),[wheel](phase62/wheel-final-gui/gui.xml).
Önceki source isolated-cancel1fail aynı gözlem yarışı; bounded engine failure değil.
Parent publication gerçek ProjectStore'da kontrollü thread gate ile tutulup worker
ACK beklerken GUI cancel yapılır; chunk16durable'dan açık resume toplam40learn/
39score verir. Bu kontrollü I/O boundary kanıtıdır, doğal uzun hesap iptali değildir.
Native mid-update cancellation/rollback ayrıca testli.

Son ayrı [source cancel](phase62/source-gated-cancel-final/walkthrough.json),
[wheel cancel](phase62/wheel-gated-cancel-final/walkthrough.json),
[source transductive caption](phase62/source-readable-caption-final/walkthrough.json),
[wheel caption](phase62/wheel-readable-caption-final/walkthrough.json).
İlk caption'lar yanlış kaydırma bölgesini gösterdi; son script layout sonrası
1000/1366genişlikte görünen caption scene koordinatı assert eder ve ekran görüntüsü
alır. İlk yeni capture helper mapToScene(0,0) overload TypeError; QPointF ile
onarılmıştır. [Source readable ilk failure](phase62/source-readable-caption/gui.xml),
[source gated ilk failure](phase62/source-gated-cancel/gui.xml),
[wheel gated ilk failure](phase62/wheel-gated-cancel/gui.xml) korunur. Bu caption
hatası sonucun başarılı hesaplandığını GUI testi başarılı saymaya gerekçe değildir.
Son ayrı kontrollerin başarılı statüsü verification.json ile doğrulanır.

Geliştirici tekrar komutları: `.venv/bin/python scripts/measure_phase62_memory.py`;
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase62.py --output ABS_PATH`.
`--package-root TARGET` noneditable wheel kullanır; `--only live_cancel` veya
`--only transductive` dar son kontrolü seçer. Tüm GUI fixture'larında explicit geçici
4GiB config vardır, ürün varsayılanını değiştirmez. CPython3.13.15 `.venv` şarttır.

Son kaynak iyileştirmesi: lazy scan yalnız seçili olay/feature ve native kimlik
kolonlarına projection uygular; kullanılmayan büyük kolonlar materialize edilmez.
Integer/float fiziksel tip önkontrolü collection öncesi; label/feedback Null olabilir.
Bu sürüm yeniden129source/129wheel core ve fresh CPU RSS ölçümünden geçirilmiştir.
Son kurulu paket `/tmp/veri-ufku-f62-installed-bounded`; [iki dar GUI yolu](phase62/wheel-bounded-gui/walkthrough.json)
transductive/cancel-resume. Önceki `installed-final`/`installed-delivery` alt koşuları
kendi paket yoluyla korunur; final frozen/wheel hash yeni bounded paketine aittir.

Son belge önkontrolünde GUI koşusu henüz tamamlanmadan yeni walkthrough bağlantısı
eklenmişti: docs ve14unit içinde1document-contract failure;
[gates-before-gui-artifact](phase62/gates-before-gui-artifact.json) korunur. GUI
artifact gerçek tamamlandıktan sonra7kapı yeniden çalıştırılır. Bu başarısız belge
önkontrolü başarılı sayılmamıştır.
