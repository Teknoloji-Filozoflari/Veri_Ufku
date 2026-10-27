# Faz52 — yerel experiment ve model kayıtları

<a id="e52"></a>
DEC52-01 açık kullanıcı Faz52 talimatı. ENV-52 CPython3.13.15, CPU,
Qt offscreen/software. [Ortam](phase52/environment.json),
[ADR053](../adr/053-experiment-registry-phase52.md).
7 bounded yerel native kayıt teknik doğrulandı; resmî faz sürüyor/deneysel/zorunlu.
Optional tracking adapter uygulanmadı/runtime doğrulanmadı. F52-S001/S003 tam genel
run capture/backend kapsamı ayrıca açık; native slice acceptance aşağıda.

Mevcut run/model/search/analysis/chart/text kimlikleri üzerine yerel projection;
Faz16 final test defteri ve source lineage korunur. Yeni supervised runlarda code/
config/environment hash (validation/model options + immutable PipelineId preprocessing
reference), first read boundary ve elapsed; eski bilinmeyenler unknown.
Model version/run kartı, candidate/selected/archived append-only revisions; metric
revision ayrı, threshold/calibration değişimi yeni training run. Yerel durum deploy
başlatmaz. Legacy hashes sonradan uydurulmaz.

32run compare, actual fold distributions/final-validation metrics, Pareto only same
protocol. Dataset/fingerprint/split/protocol/target/decision/uncertainty mismatch warns;
prior test use/time/scope/cost context visible. Selected legacy evaluation duration vs
new full job wall time cost scope farklı; aynı birim aynı maliyet hesabı değildir.
Artifact streaming SHA256, safe JSON/model references, shared Control timeout/cancel;
quota default4GiB all historical artifact bytes, no auto-delete. Physical deletion
closed with loss disclosure; archive doesn't free disk. Optional tracking unconfigured,
not runtime validated; offline native core independent. Export excludes raw configs,
model cards/free tags/labels/envstrings and rawdata; IDs/hashes not anonymity guarantee.

[12 yeni core +regresyon,332 başarılı kaynak](phase52/source-core.xml),
[332 başarılı noneditable wheel](phase52/wheel-core.xml),[13 gerçek GUI/regresyon](phase52/source-ui.xml).
[Kaynak GUI](phase52/source-gui-release/walkthrough.json),
[kurulu GUI](phase52/wheel-gui-release/walkthrough.json),
[7native +1unvalidated C/V/G/H/P](phase52/acceptance.json),
[gerçek komutlar](phase52/verification.json),[wheel295 eşit dosya](phase52/wheel.json),
[frozen-head](phase52/frozen-head.json),[fresh4XDG kurulu smoke](phase52/smoke.json).
Core kapsamında aynı dataset/farklı split, macro vs weighted F1, legacy unknown,
model corruption, cancellation/timeout, pending/canceled final reservation, secret
sentinel olmayan export, immutable revision/stale draft, quota aşımında ACTIVE
koruması; GUI training→compare→revision→status→maskexport→finaltest→subsequent
training→journal unchanged→reopen/help/project-close scope kontrolü. Gerçek fold ve
cost-score görselleri1000/1366PNG; synthetic fixture only. Historical preliminary
GUI folders retained as earlier iteration evidence; release paths are delivery.
Sources: tests/test_experiment_registry.py; tests/test_experiment_registry_gui.py;
scripts/measure_phase52.py. Formal physical/human/AT/minHW/offlineinstall/remoteCI and
prior acceptance gates remain open. No stage/commit/push.

Son QML legend değişimi yalnız P Pareto işareti; hesap Python dosyaları değişmedi.
Final release source/wheel gerçek Qt akışı ve screenshot yeniden çalıştı.

[Docs/artifacts/learning/usability/Ruff ve14 gerçek belge unit kapısı](phase52/gates.json).
