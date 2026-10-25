# Veri_Ufku — kısa yol haritası

2026-10-13 Europe/Istanbul; ana kayıt REQUIREMENTS_MATRIX.md; hafıza PROJECT_STATE.md.
Bu belge yeni faz yetkisi vermez.

## UX V2 (arayüz/akış — teknik Faz’dan bağımsız)

Açık kullanıcı talimatı: Project store `veri-ufku-gelistirme-promptu.md`. Yerel dal `ux-v2`; push yok.

| UX | Teknik teslim | Resmî / kapsam |
|---|---|---|
|0 Denetim| **Teknik tamamlandı:** [UX_V2_AUDIT.md](UX_V2_AUDIT.md), [E UX_V2](evidence/UX_V2.md); H1–H4; taban kapılar + 26 UI pytest + smoke | sürüyor; resmî kabul ayrı; bilinen AGENTS açıkları korunur |
|1 Şartname| **Teknik tamamlandı:** [UX_WORKSPACE_V2.md](UX_WORKSPACE_V2.md); bölge/durum/eşleme; kod yok | sürüyor; kullanıcı gösterimi ayrı |
|2 Kabuk| **Teknik tamamlandı:** StageStrip + ContextSidePanel; mevcut ekranlar; smoke | sürüyor; resmî kabul ayrı |
|3 Tablo| **Teknik tamamlandı:** tablo merkez; başlık tür/rol; sayfa kapsamı; 23 GUI PASS | sürüyor; resmî kabul ayrı |
|4 Veri alanı| **Teknik tamamlandı:** örnek katalog + Verilerim (XDG indeks); proje şeması aynı | sürüyor; resmî kabul ayrı |
|5 Öğretim| **Teknik tamamlandı:** taslak aşama metinleri + tur; sözlük dosyası | sürüyor; metin onayı kullanıcıda |
|6 Özet/eksik| açık | — |
|7 Keşif| açık | — |
|8 Aykırı/hazırla| açık | — |
|9 Model| açık | — |
|10 Rapor/kabul| açık | — |

---


| Faz | Teknik teslim | Resmî durum / kapsam |
|---|---|---|
|30| Yerel formatlar; büyük SAS açık | sürüyor / deneysel / zorunlu |
|31| DB/HTTP/S3; önceki sunucu kanıtları yerinde | sürüyor / deneysel / zorunlu |
|32| Sözlük/sözleşme/insan onaylı canonical kimlik, önceki kanıt korunur | sürüyor / deneysel / zorunlu |
|33| **Teknik tamamlandı:** fold-içi indicator/KNN/iterative; mean/OLS MI/delta; sampling; typed weights; WR Taylor survey;853 full regression (son display/Qt scalar düzeltmesi öncesi başlatıldı),36 final faz testi; source/wheel14 case,12 render,224 file | **sürüyor / deneysel / zorunlu**;17 teknik madde doğrulandı, önceki resmî kapılar açık |
|34| **Teknik tamamlandı:** NetCDF/Zarr/HDF5 array;lazy kesit/maliyet/CFmetadata/Pint;heatmap/profil;872regresyon,19faztesti,36render,226file | **sürüyor / deneysel / zorunlu**;12 teknik madde doğrulandı; önceki resmî kapılar açık |
|35| **Teknik tamamlandı:** 11 yeni dağılım/belirsizlik grafiği; histogram/box grup/facet/ağırlık;917 regresyon,45faz vakası,15son GUI,52render,78export,229file | **sürüyor / deneysel / zorunlu**;19 teknik madde doğrulandı; önceki kabuller açık |
|36| **Teknik tamamlandı:** dokuz çok değişkenli tür; RowId brushing/filter copy; 950regresyon,33faz vakası,36render,54export,232file | **sürüyor / deneysel / zorunlu**;15teknik madde;3D/surfaceoptional uygulanmadı; önceki kabuller açık |
|37| **Teknik tamamlandı:** 17kompozisyon/hiyerarşi/akış türü; doğrulama/payda/soru galerisi; 1016regresyon,66faz vakası,68render,102export,235file | **sürüyor / deneysel / zorunlu**;21teknik madde; önceki kabuller açık |
|38| Teknik tamamlandı:5geo reader,4offline map,11operation;explicit tile/geocoding;1075 tam regresyon,59 faz/39 wheel vaka,80render/24export,244file | sürüyor / deneysel / zorunlu;24teknik kayıt,önceki kabuller açık |
|39| **Teknik tamamlandı:** masaüstü grafik/tablo/KPI/not grid; sürüm/filtre eşleme/brushing/drill-down/save-reopen; SVG/PDF/PNG ve ağsız HTML composer | **sürüyor / deneysel / zorunlu**;12 teknik kayıt; önceki resmî kabuller açık |
|40| **Teknik tamamlandı:** OLS/WLS, GLM binomial/Poisson/NB2, quantile, Gaussian mixed, balanced repeated; güvenli matrix/tanılama/GUI-yardım/save | sürüyor / deneysel / zorunlu;17 teknik kayıt;1168 passed/19 skip; önceki kapılar açık |
|41| **Teknik tamamlandı:** Resampling/percentile-BCa/whole cluster/time blocks; exchangeable permutation/paired sign; robust/aile/duyarlılık;1229 passed/19skip,61faztesti | sürüyor / deneysel / zorunlu;15 teknik kayıt; önceki kabuller açık |
|42| **İlk kapsam teknik tamamlandı:** bağımsız iki-grup yolu: ölçüm planı/power/MDE, yerel assignment, SRM/attrition/ITT-PP;1276 passed/19skip,47faztesti | sürüyor / deneysel / zorunlu; paired/cluster/factorial/sequential ayrı kapalı alt işler; önceki kabuller açık |
|43| Optional CPU PyMC;4 güvenli şablon, prior/PPC/sensitivity;R-hat/ESS/divergence/trace;bounded safe chain artifact | sürüyor / deneysel / zorunlu; 14 teknik kayıt doğrulandı;1305passed/19skip |
|44| Teknik tamamlandı: yedi sınırlı nedensel şablon, DAG/identification/cross-fit/overlap/matchingRowId/DiD/IV;25faz/158ilgili vaka,112render/56export | sürüyor / deneysel / zorunlu;15teknik kayıt; önceki resmî kabuller açık |
|45| Teknik tamamlandı: KM/risk/logrank/CoxPH/lognormalAFT/CIF;safe model reuse;34faz/154ilgili vaka,128render/80export | sürüyor / deneysel / zorunlu;18teknik kayıt;unsupported censoring/metrics/time-dependentfit kapalı; önceki resmî kapılar açık |
|46| Numeric PCA/IPCA/SVD/NMF/ICA,t-SNE ve nestedselection;41fazpass/1skip,189ilgili/1skip,192render/120export | sürüyor / deneysel / zorunlu;16teknik verified;optionalUMAPbackendyok/notvalidated;önceki kabuller açık |
|47| BoundednumericAgglomerative/GMM/OPTICS/HDBSCAN+sharedDBSCAN/KMeans;LOF/SVM/covariance;123source/61wheel,192render/48artifactcopy | sürüyor / deneysel / zorunlu;16teknikverified;new-filemodelreusekapalı;önceki kabuller açık |
|48| 26native purpose/model;285source/235wheel,26şar GUI;closed safe persistence;OOF stacking | sürüyor / deneysel / zorunlu;16bounded teknikverified;optional3/rankingruntime unvalidated;multioutput/GPU kapalı;önceki kabul açık |
|49| Bounded grid/random nested tuning, trial history/cumulative budget/joint folds;297source/272wheel,8şer GUI | sürüyor / deneysel / zorunlu;8bounded records;optional Optuna runtime unvalidated;önceki kabul açık |
|50| 10bounded native calibration/threshold/quantile/conformal records;295source/295wheel;10şar GUI | sürüyor / deneysel / zorunlu; önceki resmî kabul kapıları açık |
|51| 9native inspection/mapping/slices/fairness/scenario records;320source/320wheel;9şar GUI | sürüyor / deneysel / zorunlu;optionalSHAPruntimeunvalidated;previousformalopen |



[Faz33 kanıt](evidence/PHASE33.md), [karar](adr/034-missing-sampling-phase33.md),
[17 C/V/G/H/P kaydı](evidence/phase33/acceptance.json).
Önceki F13/F24/F25/F27 insan/AT/hardware/distribution; Faz30 büyük SAS ve
Faz31 clean offline cache açığı PROJECT_STATE içinde ayrı tutulur.

[Faz34 kanıt](evidence/PHASE34.md),[ADR035](adr/035-multidimensional-phase34.md),[12kabul](evidence/phase34/acceptance.json).

[Faz35 kanıt](evidence/PHASE35.md), [ADR036](adr/036-distribution-charts-phase35.md), [19 teknik kayıt](evidence/phase35/acceptance.json).

[Faz36 kanıt](evidence/PHASE36.md), [ADR037](adr/037-multivariate-charts-phase36.md), [15 teknik kayıt](evidence/phase36/acceptance.json). Faz38 teknik tamamlandı; resmî kabuller ayrı açık.

[Faz37 kanıt](evidence/PHASE37.md), [ADR038](adr/038-composition-charts-phase37.md), [21 teknik kayıt](evidence/phase37/acceptance.json). Faz39 ayrı açık kullanıcı talimatıyla uygulandı.


[Faz38](evidence/PHASE38.md),[ADR039](adr/039-geospatial-phase38.md).

[Faz39 teknik teslimi](evidence/PHASE39.md), [ADR040](adr/040-dashboard-figure-phase39.md), [12 C/V/G/H/P kaydı](evidence/phase39/acceptance.json). Faz40 açık kullanıcı talimatıyla teknik uygulandı; [kanıt ve sınırlar](evidence/PHASE40.md), [ADR041](adr/041-statistical-models-phase40.md). Faz41 açık kullanıcı talimatıyla uygulandı; [kanıt ve sınırlar](evidence/PHASE41.md), [ADR042](adr/042-resampling-phase41.md). Faz42 kullanıcı talimatıyla ilk bağımsız iki-grup yolunu uygular; varyantlar ve sequential ayrı kapalı alt işlerdir.

Faz42 açık kullanıcı talimatıyla ilk bağımsız iki-grup yolu: [kanıt](evidence/PHASE42.md), [ADR043](adr/043-experiments-phase42.md). Faz43 açık kullanıcı talimatıyla Bayes şablonları uygulandı; 14 teknik kayıt doğrulandı;1305passed/19skip. Faz44 açık kullanıcı talimatıyla nedensel şablonlar teknik tamamlandı; Faz45 açık kullanıcı talimatıyla sınırlı sağkalım teknik tamamlandı; Faz46 açık talimatla numeric teknik tamamlandı; Faz47 açık talimatla teknik tamamlandı; Faz48 açık talimatla sınırlı native model aileleri teknik doğrulandı;optional3/ranking runtime doğrulanmadı;Faz49 açık talimatla bounded nested native search teknik doğrulandı;optional Bayesian compute doğrulanmadı;Faz50 DEC50-01 bounded native teknik doğrulandı; Faz51 DEC51-01 boundednative teknik doğrulandı; optionalSHAPruntimeunvalidated; Faz52 DEC52-01 açık talimatla aktif; Faz53 DEC53-01 açık talimatla aktif; Faz54 yetkisi yok.


[Faz43](evidence/PHASE43.md),[ADR044](adr/044-bayes-phase43.md).


[Faz47](evidence/PHASE47.md),[ADR048](adr/048-exploration-phase47.md).

[Faz48](evidence/PHASE48.md),[ADR049](adr/049-model-families-phase48.md).

[Faz49](evidence/PHASE49.md),[ADR050](adr/050-hyperparameter-search-phase49.md).

[Faz50](evidence/PHASE50.md),[ADR051](adr/051-uncertainty-phase50.md).

[Faz51](evidence/PHASE51.md),[ADR052](adr/052-explanation-phase51.md).

Faz52 DEC52-01:7native bounded registry teknik doğrulandı;332source/332wheel core,13GUI;1şer actualsource/wheel workflow. Optional tracking uygulanmadı/notvalidated; generic other-schema fullcapture açık; resmî kabul ayrı. [Kanıt](evidence/PHASE52.md).

Faz53 DEC53-01:19 bounded native temporal capabilities teknik doğrulandı;373source/373wheel,29GUI,19şar actualflow; resmî kabul ayrı.

Faz54 DEC54-01 açık kullanıcı talimatıyla aktif; Faz55 yetkisi yok. [Kanıt](evidence/PHASE54.md).

Faz54 DEC54-01:13 bounded native signal teknik doğrulandı;408source/408wheel,42GUI/regression,13şer actualflow,303packagefiles;resmî sürüyor/deneysel/zorunlu. [Kanıt](evidence/PHASE54.md). Faz55 yetkisi yok.

Faz55 DEC55-01 açık talimatla aktif; Faz56 yetkisi yok. [Kanıt](evidence/PHASE55.md).

Faz55 DEC55-01:12 bounded native teknik doğrulandı;437source/437wheel,23GUI,1sourceTLS,12şer actualflow,307files;resmî sürüyor/deneysel/zorunlu. Neural unsupported;Faz56 yetkisi yok. [Kanıt](evidence/PHASE55.md).

Faz56 DEC56-01:10 bounded CPU tensor kayıt teknik doğrulandı;241source/241wheel core,18şer focused,17GUI/regression,4şer actualflow ve1şer finalcaption,312byte-eşit package; GPU unvalidated/kapalı, resmî sürüyor/deneysel/isteğe bağlı. [Kanıt](evidence/PHASE56.md). Faz57 yetkisi yok.

Faz57 açık talimatla bounded teknik teslim: yerel görüntü adapter, CPU CNN/safe transfer ve ayrı bounded
pixel detection/segmentation;12 kayıt,311şer core/14şer focused,6şar actual+1şer review,319package. Önceki resmî kapılar korunur.
[Faz57](evidence/PHASE57.md). Faz58 başlatılmaz.

Faz58 explicit DEC58-01: bounded WAV/FLAC, waveform/spectrogram/MFCC/logmel, speaker split ve CPU classification; optional local Vosk küçük model yok/unvalidated. Diarization/event/microphone kapalı. [Kanıt](evidence/PHASE58.md). Faz59 başlatılmaz.

Faz59 DEC59-01 bounded native CPU recommendation ve ayrı query-group ranking;
[gerçek kapsam/kanıt](evidence/PHASE59.md),[ADR060](adr/060-recommendation-phase59.md).
Tek registry/journal; resmî kabul ayrı; Faz60 başlatılmaz.

Faz59 son teknik teslim:12 bounded native kayıt;177source/177wheel core,
source5actualGUI+1finalranker/finalwheel5actualGUI,332byte-eşit package.
Resmî sürüyor/deneysel/isteğe bağlı; önceki açıklar PROJECT_STATE içinde korunur.

Faz60 DEC60-01 native bounded sepet/event/süreç keşfi; [kapsam/kanıt](evidence/PHASE60.md),[ADR061](adr/061-patterns-phase60.md). Resmî kabul ayrı, Faz61 başlatılmaz.

Faz60 son teknik:11bounded native kayıt,155şer core/27native,finalwheel8GUI,338byte-eşit package.
Resmî kabul ayrı; kaynak GUI koşuları ve önceki açıklar E60/PROJECT_STATE içinde.

Faz61 DEC61-01 bounded native GraphML/GEXF ve NetworkX3.7: [kanıt](evidence/PHASE61.md),[ADR062](adr/062-graphs-phase61.md). Optional link prediction/embedding unavailable; resmî kabul ayrı, Faz62 başlatılmaz.

Faz61 teknik:10bounded native;192şer core/finalwheel41focused;344byte-eşit package.
Wheel8actualGUI önceki koşuda pass; sonraki7pass/1memoryfail ve ayrı final kontroller E61
içinde korunur. Optional link prediction/embedding yok; resmî kapılar ayrı açık.

Faz62 DEC62-01 açık talimatla bounded local replay, incremental scaler/SGD, prequential/checkpoint ve ayrı özel hedefler; [kapsam/kanıt](evidence/PHASE62.md), [ADR063](adr/063-streams-phase62.md). PU/broker unavailable; default2GiB GUI kapısı açık,4GiB işlevsel test ayrı. Resmî kabul sürüyor/deneysel/isteğe bağlı; Faz63 başlatılmaz.

Faz63 DEC63-01: sınırlı numeric GUI profile Python/SQLite/notebook reference-only export ve explicit fresh Python process; [kanıt](evidence/PHASE63.md),[ADR064](adr/064-code-bridge-phase63.md). OS sandbox/managed Jupyter yok; resmî sürüyor/deneysel/isteğe bağlı, önceki kapılar korunur. Faz64 başlatılmaz.

Faz64 DEC64-01: bounded typed DAG source/transform/quality/analysis/train/predict/export, aynı GUI/CLI worker ve batch/sweep/dry-run. [Kanıt](evidence/PHASE64.md), [sözleşme/CLI kullanımı](adr/065-typed-workflow-phase64.md). Schedule mevcut değil; resmî kabul ayrı, önceki kapılar korunur. Faz65 başlatılmaz.

Faz65 DEC65-01 açık talimat: kayıtlı source/dataset/operation/analysis/model/report lineage, reference-only veya explicit data-inclusion safe bundle ve sınırlı exact/numeric verifier. [Kapsam/kanıt](evidence/PHASE65.md), [sözleşme](adr/066-reproducibility-phase65.md). Geçmiş provenance uydurulmaz; genel row traversal/model rerun yok; önceki resmî kapılar ayrı, Faz66 başlatılmaz.

Faz66 DEC66-01: ortak process/native thread bütçesi, ölçüm paneli, bounded yerel optional Dask; remote executor/GPU runtime unavailable. [Kapsam ve gerçek kanıt](evidence/PHASE66.md). Faz67 başlatılmaz.

Faz67 DEC67-01: bounded yerel drift/kalite/delayed-label monitoring, shadow/gerçek rollback, CLI scoring ve ayrı opt-in loopback API. [Kapsam ve kanıt](evidence/PHASE67.md). Resmî kabul ayrı; Faz68 başlatılmaz.


Faz68 DEC68-01: bounded Monte Carlo/sensitivity, LP/MILP ve bounded local nonlinear; frozen regression what-if/model-domain. [Kapsam ve kanıt](evidence/PHASE68.md). Resmî kabul ayrı; Faz69 başlamaz.


Faz69 DEC69-01:8öğrenme yolu/10gerçek sentetik lab, advisory prerequisite ve optional progress/self-check; tüm modüller article coverage. [Kapsam ve kanıt](evidence/PHASE69.md). Faz70 başlatılmaz.


Faz70 DEC70-01 açık talimat: bounded bilimsel report builder; pinned dataset/run, preset, deterministic field narrative, MD/HTML/PDF/ZIP ve artifact bağları. [Kapsam/kanıt](evidence/PHASE70.md),[ADR071](adr/071-report-builder-phase70.md). DOCX/LLM uygulanmadı; resmî önceki kapılar korunur. Faz71 başlatılmaz.


Faz71 DEC71-01 açık talimat: yerel metadata/redacted/full-copy review bundle, inclusion/secret tarama, semantic diff ve immutable subject review; full restore yeni ayrı fork. [Kapsam/kanıt](evidence/PHASE71.md),[ADR072](adr/072-local-review-sharing-phase71.md). Ortak yazma/server yok; önceki kapılar korunur, Faz72 başlamaz.

|72|Bounded PII/review/redaction, optional HMAC/Fernet export, retention/owned cache cleanup ve hedefli security audit;222source/222wheel,1şer GUI|sürüyor/deneysel/isteğe bağlı; live keyring unvalidated, DP/project encryption yok; [E72](evidence/PHASE72.md)|

Faz73 DEC73-01: API1 altı tür data contract, explicit trusted manifest/worker ve stat UI/result/help/save örneği; bounded host native importer/transform/model/chart/lesson adapter değildir. [E73](evidence/PHASE73.md). Sürüyor/deneysel/isteğe bağlı; önceki kabuller korunur. Faz74 başlatılmaz.

Faz74 DEC74-01: core28 / lock123 ve seçili extras, environment status/export/import/
cache/integrity update-plan; gerçek Flatpak CPU/native/portal worker yolu.
Ayrı worker provisioning/offline installer/local extra kurucusu mevcut değil.
[E74](evidence/PHASE74.md). Sürüyor/deneysel/isteğe bağlı; önceki kabuller ayrı,
Pardus/Debian/Arch/GPU/cleanOS/remoteCI test edilmedi; Faz75 başlatılmaz.

Faz75 DEC75-01:76faz/416static capability ve alt support/operation audit,
explicit sentetik benchmark/GUI/guardrails, hash-bound bağımsız expert review hazır
worksheet. [E75](evidence/PHASE75.md), [seçilmiş kapsam](RELEASE_SCOPE_0_1.md).
Resmî sürüyor/deneysel/isteğe bağlı; açık/engelli/ertelenmiş işler tamamlanma değil.
Bütün zorunlu release kapıları kanıtlanmadı, bütün veri bilimi yöntemleri tamamlanmadı.
