# Faz49 — bounded nested model araması

<a id="e49"></a>
DEC49-01; 2026-10-13 UTC / 2026-10-13 Europe/Istanbul; ENV-49 kilitli
CPython3.13.15 `.venv`, scikit-learn1.9.1; CPU/offscreen/software.
[Ortam](phase49/environment.json), [ADR050](../adr/050-hyperparameter-search-phase49.md),
[9 C/V/G/H/P](phase49/acceptance.json). Native kapsam teknik doğrulandı;8bounded
kayıt verified. Optional Bayesian runtime doğrulanmadı. Resmî faz sürüyor /
deneysel / zorunlu; önceki kabul kapıları kapanmadı.

Model → “Faz49 bütçeli hyperparameter aramasını göster”: grid ve unique seeded
random search, finite declarative conditional methods/parameters/when space,
MAE/RMSE veya accuracy/macroF1; max_rmse/min_accuracy secondary constraints.
Metric evaluation unweighted; sample_weight yalnız training loss. Space, seed,
parametreler, memberships, source fingerprint, ortam/engine hash/CPU threads,
trial history ve kaynak kimlik bağı kaydedilir. AutoML bir başlangıç önerisidir;
optimum veya genel üstünlük garantisi değildir.

Global ValidationPlan final holdout aynı kalır. Her outer train için inner plan
bir kez hazırlanır; tüm triallar aynı birleşik group/time/horizon kurallarını
korur. Outer evaluation yalnız inner winner için; outer skor trial seçmez.
Full-development inner tuning önerisi nested outer prosedür tahmininden ayrıdır.
Preprocessing/variance-only selection ve bagging/stacking resampling her train
katında öğrenilir; stacking child preprocessing iç OOF içinde de fit edilir.
Yeni arama ve resume eski final test kullanım kayıtlarını silmez. Öneriyi mevcut
BaselineRun/model kartı yolunda eğitmek ayrı eylem; final test yalnız mevcut
kalıcı defter ve ayrı onay yolundan. Tuning sonrası tekrar CV keşifseldir.

External early stopping yalnız gradient boosting: inner training içinde ayrıca
joint validation, scoring inner validation ve outer/final testten ayrı. 10-tree
adımları, patience ve seçili aşama saklanır. Pruning explicit partial inner-fold
loss threshold; tamamlanmış CV veya dış değerlendirme diye sunulmaz. Curves
öneriden sonra training%50/%100 ve diğer parametreler sabit tek parametre taraması;
RowId/n/metric saklı. Whole group/connected group-time units ve earlier time units;
yeni varlık veya sınıf eksikliği varsa curve point unavailable. Numeric eğri,
kategorik değerler tablo; artificial continuous category axis yok.

1000rows/32features/2–4outer+2–4inner folds;12unique trial per scope. Nested toplam
maliyet scope ile çarpılır; toplam attempt budget (default60,max200) canceled
retry dahil;600cumulative conservative native fit reservations. Stacking/curves/
stopping ek maliyeti görünür. CPUconcurrency1, shared RAM/wall/process limits;
cumulative elapsed/attempt/fit counters resume ile sıfırlanmaz. Completed/failed/
pruned/canceled attempts farklı; terminal attempts immutable, retry yeni ID.
Compatibility source/space/seeds/pipeline/joint plan/environment/engine hash.

Parent frozen plan, source-bound predictions/metrics/constraints/winner/scope/
curve doğrular; worker Qt/ProjectStore/ACTIVE almaz/yazmaz. Checkpoint32MiB safe
JSON artifact, SHA ve ordered kısa summary chain mevcut atomic ProjectStore
protokolündedir. Büyük history project JSON içine tekrar tekrar gömülmez.
Read-only search açılışı fit/network/user-code import yapmaz. Yeni safe JSON export
atomic/no-replace; mevcut source/output değişmez. Model-choice session IDs arama
kimliğine bağlı; eski search/model/test defteri transaction guard ile korunur.
DatasetVersion/ColumnId/RowId/SourceRecordId ve source snapshot/fingerprint korunur.

## Gerçek doğrulama

- [Kaynak](phase49/source-final.xml):297passed; [kurulu wheel](phase49/wheel-final.xml):272passed. [UI regression](phase49/source-ui-regression.xml):21passed; [son aktarım](phase49/source-handoff-final.xml):1passed. Gruplar örtüşür; yeni faz34core+8GUI. Independent sklearn small-grid metric, final target poison skor/öneri invariance, raw fit spy, actual joint nested/prune/cancel/resume, variance/child bootstrap/stacking scopes, external stopping split, secondary constraints/fail states, cumulative wall/attempt, tamper/rollback, source byte preservation, archive safe reopen/export.
- [Kaynak GUI](phase49/source-gui/walkthrough.json), [wheel GUI](phase49/wheel-gui/walkthrough.json):8şer gerçek QML/spawn yol;5grid/random × independent/group_time/regression/classification ana tur,2cancel-resume (independent/group_time),1external-stop/prune. Ana turlar50PNG/10safe evidence copies her ortam; gerçek JSON export assertion, model handoff/save ve final test sonrası yeni arama/journal/reopen. Bunlar fiziksel masaüstü kabulü değildir.
- [Wheel](phase49/wheel.json):284source/wheel/install byte eşit; [453frozen code/test/script/lock](phase49/frozen-head.json) hash kontrolü. [Fresh4XDGinstalled smoke](phase49/smoke.json):GUI_SMOKE PASS. [Kontrol özeti](phase49/verification.json).
- [Son kapılar](phase49/gates.json): Ruff check/format; docs/artifacts/learning/usability;14documentunittest geçti. Catalog65/348article,159UIbindings,686namedfields,189coreEnglish. Tam depo regresyonu koşulmadı; önceki fazların eski sonuçları yeniden koşulmuş sayılmaz.

İlk GUI açılışında inherited Qt notify signal SIGSEGV, debugger ile own
searchChanged signal ihtiyacı olarak teşhis edildi ve düzeltildi. Sandbox ptrace
engellediği için onaylı gdb kullanıldı; debuginfod indirme kapalı. İlk inline
checkpointler project size sınırına ulaştı; mevcut source artifact+summary atomik
protokolüne taşındı. İlk wheel turunda model handoff readiness reddi gözlendi;
ikili tekrar geçti, Apply kontrolü validation.canRun ile ayrıca korunup güncel
wheel GUI turu tamamlandı. Bunlar final başarı diye gizlenmiş eski kontroller değil;
son paket/affected UI doğrulaması yukarıdadır.

## Kapsam / açık kabul

Optional Optuna TPE adapter finite configuration index ve seeded history replay;
Optuna ortamda yok. Disabled UI/availability guard geçti; Bayesian optimization
compute test edilmiş sayılmaz. F49-P003/F49-S001 runtime bütünü doğrulanmadı.
Continuous distributions/user callbacks ve calibration araması kapalı. Advanced
supervised selection/indicator/MI search kapalı; native categorical variance
selection reddedilir. Stacking time/group_time için random fallback yok.

Physical desktop/human/Orca/AT/minHW/clean offline install/remoteCI bu fazda
koşulmadı. Önceki F13/F24/F25/F27/F28/F30largeSAS/F31cache/F43aggregateRAM ve
optional UMAP/model backend açıkları korunur. Temel uygulama offline; dependency
indirme/ağ eylemi yok. Qt teardown ResourceWarning200uncollectableobjects önceki
sınır olarak açık. Kullanıcı değişiklikleri/untracked korunur; stage/commit/push
yok. Faz50 yetkisi yok.
