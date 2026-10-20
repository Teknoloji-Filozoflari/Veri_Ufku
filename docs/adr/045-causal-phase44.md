# ADR045 — Faz44 sınırlı nedensel şablonlar

2026-10-12; DEC44-01 açık kullanıcı Faz44 talimatı. Faz45 yetkisi yok.
Python/PySide6/QML, mevcut Capability/AnalysisSpec/ValidationPlan/ComputeBudget/
Provenance/ProjectStore protokolü genişletilir; ikinci registry veya Qt worker yok.

## Şablon ve tanımlama

44.1 önce bağımsız Bernoulli randomize ATE; sonra lineer g-formula adjustment,
Horvitz–Thompson IPW, cross-fitted AIPW.44.2 propensity caliper matching;
44.3 dengeli2pre/1post DiD;44.4 ikiliZ/ikiliT WaldLATE ayrı alt aşamalar.
Outcome sayısal, treatment0/1, covariate<=5 ön-tedavi sayısal, birim kimliği,
sayısal zaman/dönem ve ölçüm/bağımsızlık onayı gerekir. Date/Datetime dönemi
otomatik çevrilmez: kullanıcı açık sayısal dönem hazırlamalı. Tam veri sürümü;
2000iid veya3000DiD kayıt; eksik/drop/imputation/weight/Decimal desteklenmez.

DAG2–12node/30edge: node role, kullanıcının gerekçesi, ölçülen/latentColumnId;
edge yön/gerekçe; cycle ve yinelenen kimlik ret. Node konumu güvenli declarative.
Confounder/collider/mediator etiketi kullanıcı hipotezidir, veriden otomatik keşif
veya kanıt değil. Backdoor için outgoingT silme, ancestral moralization ve
conditioning node çıkarılmasıyla d-separation; açık yol, total effect için
mediator/descendant/collider adjustment veya gerekli varsayım gerekçesi eksikse
kalıcı “Bu veri/varsayımla belirlenemiyor” raporu, effect/CI boş. IV incomingZ
cause veya T dışı Z→Y yolu konservatif ret; Z→T hipotezi zorunlu. Bu basit IV
şablonu conditioning instrument independence desteklemez. DiD/IV ordinary
backdoor adjustment kriteriyle yanlış etiketlenmez. DAG varsayımları kanıtlamaz.

Consistency, positivity, no interference, time order; gözlemsel exchangeability/
unmeasured confounding; DiD parallel trends/no anticipation; IV exclusion/
independence/monotonicity gerekçeleri ve alternatif açıklamalar JSON/Parquet
kaynak kökeniyle saklanır. Randomize gerçek evidence ve Bernoulli allocation
kullanıcı beyanı; exact binomial SRMp<.001 etkiyi engeller. Zaman sırası
kullanıcı gerekçesidir; tek sayısal tarih causality sağlamaz.

## Hesap ve çıkarım sınırı

Randomize fark ve DiD birim değişimi farkı WelchCI. DiD tam3unique ortak dönem,
her unit×period bir kayıt, sabit ever-treated group; staggered/TWFE yok.
Pre2−pre1 placebo CI sıfırı dışlarsa etki engelli; non-rejection parallel trend
kanıtı değil, iki pre dönem zayıf kontroldür.

Mevcut ValidationSpec/ValidationPlan stratifieddevelopment folds + reserved
block: development her katında train dışında; reserved block alldevelopment
ile. Her satır tam bir kez out-of-fold; train/evalRowId, protocol/splitID ve seed
saklanır. Reserved block modelbenchmark/finaltest reuse değildir. StandardScaler
fit yalnız train; unpenalizedLogit + arm-specificOLS; rank/separation/nonconvergence
engelli. e epsilon dışı/maxweight aşımı/kol aralıkları örtüşmüyorsa clip/trim
olmadan belirlenemiyor. Arm propensity histogram/range, herRowIdpropensity,
ESS ve before/IPW SMD saklanır. SMD paydası orijinal pooled within-arm SD;
sabit ama farklı ortalama “undefined” görünür. Tanılar exchangeability kanıtı değil.

Adjustment m1−m0;IPW T·Y/e−(1−T)·Y/(1−e);AIPW residual augmentedscore.
Adjustment/IPW nokta sonucu: nuisance uncertainty CI uygulanmadı, sahteCI yok.
AIPW n>=100 iid/overlap/nuisance product-rate koşulları altında asimptotik
influence-function normalCI; küçük n nokta. Lineer/logistic nuisance sınırlı;
double robustness her iki model yanlışken veya latentconfounding varken korumaz.

Matching rawpropensity caliper, withoutreplacement, RowIdsorted treated ve
nearestcontrol/RowId tie; çift kaynakRowId kaydolur. Yalnız eşleşen treatedATT;
unmatched sayıları/balance açık; fullATE/fullATT değil. Non-smooth matching
inference uygulanmadı; sıradan bootstrapCI sunulmaz.
IV Wald reduced/firststage LATE;firststageCI0 içeriyorsa veya Fheuristic<10
engelli. Exclusion/independence/monotonicity test edilmiş sayılmaz. n>=100 güçlü
IV jointoutcome/treatment covariance deltaCI; weakIVrobust yok; küçük n nokta.

Additivebias sensitivity outcome biriminde hipotetik effect−bias, tahmini
confounding düzeltmesi değil. Ön-tedavi placebo alanı ve etkilenemezlik gerekçesi;
kol ilişkisinin null olması causality kanıtı değil. Featureimportance neden
sıralaması yapılmaz. Kaynak veri/SourceRecordId/DatasetVersion değişmez.

## Yayın, GUI ve yardım

Disposable worker kontrollü cancel/wall/RAM/disk; parent tek ACTIVE yazarı.
Immutable source hash ve tümRowId/ColumnId/detay kontrolü; parent deterministic
hesap/split/pairs tekrar doğrular. JSON+members/detailsParquet atomik save;
export yeni klasör; stale kaynak/sürüm/config engelli; reopen hash doğrular,
model/code import yok. DAG drag/add/update/delete ve gerekçeler gerçek QML;
form, önkontrol, açık onay, sonuç/tanılar, save/export/reopen, F1/Escape.
Katalog60/282; dokuz offline nedensel makale; yeni try_action yok.

## Kaynaklar

[Hernán/Robins What If](https://www.hsph.harvard.edu/miguel-hernan/wp-content/uploads/sites/1268/2024/04/hernanrobins_WhatIf_26apr24.pdf),
[statsmodels TreatmentEffect](https://www.statsmodels.org/stable/generated/statsmodels.treatment.treatment_effects.TreatmentEffect.html),
[IV2SLS](https://www.statsmodels.org/dev/generated/statsmodels.sandbox.regression.gmm.IV2SLS.html).
Yerel referans fixture ve gerçek koşu sonuçları [Faz44](../evidence/PHASE44.md).
Physical insan/AT/minHW/cleanofflineinstall/remoteCI ayrı açık kanıtlardır.
