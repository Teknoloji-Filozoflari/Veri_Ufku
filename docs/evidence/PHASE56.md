# Faz56 — bounded CPU tensor training

<a id="e56"></a>
DEC56-01 açık kullanıcı talimatı; Faz57 yetkisi yok.
ENV-56 locked CPython3.13.15 / torch2.13.0+cpu / Qt offscreen software.
[Ortam](phase56/environment.json), [ADR057](../adr/057-neural-phase56.md).
10 bounded CPU teknik kayıt doğrulandı; resmî sürüyor/deneysel/isteğe bağlı.
GPU/VRAM/mixed precision uygulanmadı ve ortamı olmayan connector gibi doğrulanmış sayılmaz.
Fiziksel/human/AT/minHW/clean-offline-install/remoteCI/fullrepo aggregate yapılmadı.
Önceki kabuller [korunan hafızada](phase56/prior-project_state.txt).

CPU MLP regresyon/kategori ve gerçek Conv2d CNN, train-only scaler/class weights/flip,
aynı holdout sklearn Dummy, shared group/time/horizon plan, no final-test fit.
Safe JSON16MiB kapalı model/optimizer/scheduler/RNG/early-stop state; arbitrary object
checkpoint import yok. Pause epoch boundary; cancel partial epoch discard. Resume source/
split/settings/framework/thread/test history compatibility. Fresh prediction target-free,
RowId preservation, immutable source. DatasetVersion/ColumnId/SourceSnapshotId/Provenance
ve tek ProjectStore/Capability/experiment registry genişletilir.

İlk GUI notifier çökmesi düzeltildi; geçici source edit sırasında çalışan CNN fixture başarısız
oldu ve başarılı sayılmadı. OneDNN workspace default toplam2GiB kontrolünü tetikledi; küçük
CPU şablonda oneDNN kapatıldı ve isolated CNN2GiB ile yeniden doğrulandı.
Repeated GUI retained heap yine2GiB kontrolünü tetikledi; actualflow için açık geçici4GiB
ComputeBudget kullanıldı. Çekirdek default2GiB değiştirilmedi; minimum donanım iddiası yok. Son teslim kanıtı aşağıda ayrı
kayıtlarla belirtilecektir; eski/başarısız denemeler kabul yerine kullanılmaz.

Son gerçek kontroller: [241 source core](phase56/source-core.xml),
[241 installed core](phase56/wheel-core.xml),
[18 current source focused](phase56/source-neural-current.xml),[18 current wheel focused](phase56/wheel-neural-current.xml),
[17 source GUI/regression](phase56/source-ui.xml).
[4source actualflow](phase56/source-gui-final/walkthrough.json),
[4installed actualflow](phase56/wheel-gui-final/walkthrough.json):16PNG/16safeJSON run+prediction.
Son yalnız gradient caption açıklaması (clip öncesi norm) sonrası ortak panel yeniden
[1source](phase56/source-caption/walkthrough.json)/[1release wheel](phase56/wheel-caption/walkthrough.json)
MLP gerçek train/reopen/new-predict ile doğrulandı;4PNG/4JSON ek kanıt. Sayısal backend değişmedi.
[312byte-eşit release package](phase56/wheel.json),[fresh4XDG release smoke](phase56/smoke.json),
[10C/V/G/H/P ve1unvalidated GPU](phase56/acceptance.json),[gate commands](phase56/gates.json),
[frozen source/evidence hashes](phase56/frozen-head.json),[verification](phase56/verification.json).

Hand SGD reference residuals−2,−3:loss6.5,dw−8,db−5,w1.8,b0.5. CPU optimizer/scheduler/
RNG exact resume for MLP/CNN including flip/balanced weights. Training-only poison/fit IDs,
group/time/combined source memberships; zero final-test fit. Early stopping plateau and
bounded cumulative time; hash corruption/wrong tensor/object schema rejected. Original
source bytes unchanged; target-free new5rows prediction IDs exact. Real canceled marker
and paused/canceled model choices not successful. Existing registry artifact verification
and legacy protocols preserved. No model quality, production deployment or final inference
claim. Optional absent backend explicit error, no runtime download.
