# Faz51 — açıklama, hata dilimleri ve model senaryoları

<a id="e51"></a>
DEC51-01 açık kullanıcı talimatı; 2026-10-13 UTC / Europe/Istanbul.
ENV-51 kilitliCPython3.13.15/scikit-learn1.9.1 CPU/offscreen/software.
[Ortam](phase51/environment.json),[ADR052](../adr/052-explanation-phase51.md),
[10 C/V/G/H/P kaydı](phase51/acceptance.json),[gerçek kontroller](phase51/verification.json).
9bounded native kayıt doğrulandı; optional SHAP runtime doğrulanmadı. Resmî faz
sürüyor/deneysel/zorunlu; önceki kabul kapıları ayrıca açık.

Model kartı → “Faz51 model açıklaması, hata dilimleri ve senaryolar”: permutation
importance (tüm özgün kolon, onehot bloğu birlikte; accuracy/negativeMAE; shuffle
repeat/std ddof1), brute empirical PDP ve ICE; numeric quantile/explicit grid,
kategori observed-grid table; ICE ilk10 çizgi, tüm sample ortalama PDP. Background
ve model source/RowId/snapshot, original-feature/class response, missing/correlated
pairs, outside marginal range ve destek sınırları kayıtlı. Grid marjinal aralıkta
olsa da gerçek kombinasyon/causal destek kanıtı değildir; SHAP contribution neden-
sonuç değildir. Açıklama sample/seed/budget ile sınırlıdır, popülasyon iddiası yok.

Exact native local linear/Ridge regression: transformed background mean referansı,
coef*(x-reference) katkıları ve baseline+sum=prediction kontrolü; özgün ColumnId'ye
aggregation. Onehot/calendar/indicator/variance-selected index mapping fitted
operations'tan; Family çocuk preprocessing representation component/index ayrı.
Native hist/ensemble representation orijinal-source bağı; meta model latent OOF
inputs raw-column katkısı diye uydurulmaz. Joint imputation dependency links
saklı, bu local attribution ve SHAP yolunda kapalı. Native local-linear SHAP diye
sunulmaz; family/ensemble local-linear desteklenmiyorsa açık hata.

Optional SHAP ExactExplainer adapter: finite dense transformed independent
empirical background,8features/20rows, allowlisted0.51.0 API/version, response,
shape/additivity ve2^d cost preflight. Ortamda SHAP yok; **runtime compute NOT
validated**. UI unavailable ve controlled gate doğrulandı, SHAP hesabı test edildi
sayılmadı. Version/API allowlist bilimsel kabul değildir; yeni ortam gerçek
reference/GUI kanıtı ister. Exact subset enumeration finite background'a aittir;
popülasyon/background yaklaşımı, korelasyon ve nedensellik sınırları sürer.
F51-S001 tam optional kapsam nedeniyle doğrulanmadı; native P001–3/P005–10 ayrı
kayıtlarda verified; P004 runtime unvalidated.

Only same immutable model training snapshot: evaluation kayıtlı validation,
background model fit RowIds. User background dataset seçer; başka kaynak/background,
external package, final train+validation refitted model burada kapalı. Final holdout
burada açılmaz; validation zaten seçimde kullanıldı, sonuç keşifseldir. Faz50 frozen
modeli training/calibration ayrımını korur. Herhangi estimator/preprocessing fit yok.
5000source/500sample/100background/16originalfeature/300000 pipeline response row-
pass sınırı; shared RAM/wall/CPU/cancel. Pipeline counter native ensemble child/
secondary probability pass sayısı veya süre garantisi değildir; shared process
budget ek maliyeti sınırlar. Source/ColumnId/RowId/DatasetVersion/SourceSnapshotId/
fingerprint/lineage korunur; kullanıcı verisi değiştirilmez.

Group/time/class/numeric range dilimleri explicit ColumnId/edges; UTC time seconds,
missing/outside kategorileri; n/accuracy veya MAE, independent-record Wilson veya
seeded iid percentile MAE bootstrap. Group/time protokolünde iid CI kapalı;
uncertainty uydurulmaz. Metrikler unweighted, survey inference iddiası yok. Small
n<30 ve çoklu slice araması/tekrar validation keşfi görünür; simultaneous CI veya
multiple-search correction yapılmış denmez.

Binary fairness explicit protected/sensitiveColumnIds ve positiveclass; perattribute
selection-rate/TPR/FPR/PPV/base-rate, TP/FP/FN/TN, conditional Wilsoniid. Missing
attribute ayrı group; DP/EO/EOdds/PPV max-minus-min farkları, base-rate trade-off;
intersectional analysis burada yok. Protected nitelik otomatik seçilmez; tek
metrikle adil model rozeti/hukuki sonuç yok. Kaynak actual/RowId/sample order,
counts/rates/uncertainty parent'ta fit/deserialization olmadan yeniden doğrulanır.

What-if frozen model tahmini, causal counterfactual değil. Optional finite constrained
candidate araması tüm features'i explicit immutable veya values/direction/cost
olarak böler; immutable en az1, finite100domain, gözlenen numeric range/categories,
source-type ve immutable kontrolleri. Desiredpredictionclass/range ve range-scaled
unitless weighted cost; candidates yalnız seçili finite domain'de, en iyi genel
müdahale veya feasibility/actionability/nedensel etki garantisi yok. Kaynak tablosu
ve model değişmez; no-candidate yalnız verilen domain içinde.

Existing registry/Lifecycle CPU worker/ComputeBudget/commonProvenance/atomic
ProjectStore genişletildi. ExplanationRun/v1 mevcut result listesine16MiB safeJSON
artifact/hash/summary; append-only guards prior explanations/model/finaltestjournal
korur. Parent frozen modelcard/package/source/actual/memberships/diagnostics/
metric/uncertainty doğrular; worker Qt/ACTIVE yazmaz, writer model/usercode load
etmez. Safe JSON identity/hash/tamper ve project reopen/duplicate overwrite gates.
Archive masked export model dosyası gerektirmez; no model deserialize or network.

Maskeli safe JSON export rawrecords/modelcard/source/backgroundRowIds/ICE/local
record IDs, sensitive names/values/labels/contributions ve individual scenario
changes/constraints/predictions içermez; sensitive group counts/rates/disparities
paylaşılmaz, small-n slice cells suppressed. No anonymity guarantee. Project
archive sensitive analiz metadata'sını açık yerel inceleme için tutar; modelpaketi
export anonymization iddiası yok. Export analytics verisini değiştirmez; eski
çıktı/symlink üzerine yazılmaz.

[Source core](phase51/source-core.xml):320pass;[installed core](phase51/wheel-core.xml):320pass.
[Source GUI/regression](phase51/source-ui.xml):34pass. Yeni25core+9GUI.
[Source walkthrough](phase51/source-gui/walkthrough.json),[wheel walkthrough](phase51/wheel-gui/walkthrough.json):
9'ar gerçek akış (8native yöntem +cancel/optional-unavailable/no-overwrite),44'er
1366/1000 PNG ve16'şar full-safeJSON/masked-export kopyası. Native compute/Qtspawn/
atomic archive/export/reopen/F1/Escape/source preservation; cancel önceki açıklamayı
korudu. Independent local additive/coef reference, manual permutation/PDP/ICE,
fitted mapping3nativefamily/onehot/selection, smallgroup/timeCI rejection, handfair
counts/rates/missinglabel/Wilson, sensitive failclosed export, deterministic sample/
budget/cancel, constrainedimmutable/domain/direction, source-bound metrics tamper/
oldjournal guard; absent backend never counted as compute.

[Wheel](phase51/wheel.json):291 package files byteequal source/wheel/install;
[active freeze](phase51/frozen-head.json):27target files;[fresh4XDGsmoke](phase51/smoke.json):GUI_SMOKE PASS.
Docs/artifacts/learning/usability/Ruff check+format/14documentunit passed. Catalog
67/357;163bindings/722namedfields/189coreEnglish. Five new offline help articles,
no executable try_action. [Gerçek komutlar](../DEVELOPMENT.md). Stage/commit/push yok.

Physicaldesktop/human/AT/minHW/cleanofflineinstall/remoteCI ve fullrepoaggregate
notrun. Önceki F13/F24/F25/F27/F28/F30SAS/F31cache/F43RAM, optionalUMAP/XGB/LGB/
CatBoost/Optuna ve QtResourceWarning kapıları korunur. Formal acceptance ayrı;
önceki kanıtlar yeniden çalıştırılmış sayılmaz. Faz52 yetkisi yok.
