# Faz33 — ileri eksik veri, örnekleme ve ağırlıklar

2026-10-11; ENV-33; DEC-33-01. Teknik kapsam zorunlu/deneysel; resmî önceki
insan/AT/donanım/dağıtım kabulleri açık. Faz34 yetkisi yok.
[Karar ve bilimsel sınırlar](../adr/034-missing-sampling-phase33.md).

<a id="e33-final"></a>
## Gerçek kontrol kaydı

Gerçek full regresyon **853 geçti**,0 failure/error/skip; konsol540,64s:
[JUnit](phase33/pytest.xml), [konsol](phase33/pytest.txt).
Son **36 Faz33 testi** geçti (22 çekirdek/fold +14 GUI),60,19s:
[JUnit](phase33/final-targeted.xml), [konsol](phase33/final-targeted.txt).
Önce54 ilgili statistics/preparation/workspace testi105,15s;
[JUnit](phase33/targeted.xml). Son8 güçlendirilmiş weight/CV-worker kontrolü
8,43s: [konsol](phase33/strengthened-final.txt). Daha eski fixture/parametre
beklentisi hataları son başarıyla karıştırılmaz.

Kaynak ve ayrı noneditable kurulu wheel'de **14'er gerçek GUI case**,
6'şar render/12 ekran;5 F1/Escape/odak dönüşü, explicit approval, immutable
kimlik, export/save/reopen/cancel. KNN/iterative ayrıca gerçek validation/CV
worker'ında train ve kayıtlı koşu reopen kanıtıdır:
[kaynak walkthrough](phase33/source-gui/walkthrough.json),
[wheel walkthrough](phase33/wheel-gui/walkthrough.json).
**224 package file** source/wheel/installed byte eşit;
[hash kayıtları](phase33/wheel-integrity.json). Gerçek kurulu console girişinde
[GUI_SMOKE PASS](phase33/wheel-entry.txt). Son14 locked unittest,
docs/artifacts/learning/usability, Ruff check/format ve diff kapıları
[command/exit/date](phase33/checks.json)'a bağlıdır. Sistem Python unittest bu
fazda koşulmadı; lock/dependency dosyaları değiştirilmedi.

Final render normal görünümde teknik ColumnId yerine kaynak sütun adlarını,
6 anlamlı basamaklı görüntü sayılarını gösterir; saklanan Float64 değerler
aynıdır. Normal ekranda ilk20 desen/grup açık sınırla görünür, tam çıktı kayıttadır.
Full run son QML display polish, survey Qt scalar düzeltmesi ve strengthened test tanıklarından önce
başlatıldı; son36 testi ve source/wheel14'er walkthrough son dosyalarda
ayrıca çalıştı.853 tam suite'i yeniden çalıştırılmış gibi raporlanmaz.
İlk kamera başarısızlığı ayrı [kaynak log](phase33/source-gui-camera-failed.txt)
ve [wheel log](phase33/wheel-gui-camera-failed.txt); eski başarılı renderlar
`source-gui-before-label` / `wheel-gui-before-label` altında korunur.
Varsayılanların omit davranışını yanlış bekleyen ilk strengthened test
[başarısız konsol](phase33/strengthened.txt), son8 başarı ayrı kayıtlıdır.
Kaynak [379 hash](phase33/source.sha256), değişmeyen combined prompt
[hash](phase33/combined-prompt.sha256). Stage/commit/push yapılmadı.

Kilitli CPython3.13.15, Qt6.11.2, sklearn1.9.1, SciPy1.18.0, Polars2.0.0,
Linux x86_64, izole XDG/offscreen/software. Gerçek komut ve exit kayıtları
faz33 dizininde tutulur. Önceki faz testleri yeniden çalışmış gibi sunulmaz.
Fiziksel masaüstü/insan/AT/minimum donanım/temiz offline kurulum/remote CI ve
R survey binary testi bu fazda yapılmadı.

<a id="e33-core"></a>
## C/V — bağımsız sayısal ve kaynak kimliği kanıtı

`tests/test_missing_sampling.py`: frekans x=(10,20),w=(1,3): μ17,5,
V(mean)=6,25,df3; aynı değer analytic inverse-variance ise V18,75,df1.
Negatif/null/inf/fractional frequency/sıfır toplam ve desteklenmeyen tür reddi.
Survey x=(0,4,14,22), iki strata ve her birinde iki nested PSU:
μ10, WR Taylor V5,df2; t2 tablo quantile4,302652729696142 ile CI.
Tasarım etkisi yalnız unweighted observed SRS s²/n referansıyla oranlanır.
Lonely strata için açık ret; FPC/kalibrasyon/domain yöntemi iddiası yok.

Rubin fixture Q=(1,2,3),U=(4,4,4): Q̄2,Ū4,B1,T16/3;
Barnard–Rubin complete df20: old32, observed315/23, harmonic df.
Gerçek MI ortalama/OLS posterior realizasyonları, source kimlik, tüm gözlenen
hücrelerin aynı kalması, seed tekrar üretimi ve x-null delta duyarlılığı.
Parent sahte covariance/pooling'i ACTIVE değişmeden reddeder.
KNN/iterative fit spy: her fit yalnız gerçek train veya CV train üyeliğinde,
validation/test ile ayrıdır; tamamen eksik eğitim kolonu ret; frozen
training transform validation değerleri değişince değişmez; paket roundtrip.

<a id="e33-gui"></a>
## G/P — gerçek arayüz ve worker

`tests/test_missing_sampling_gui.py`:11 ileri yöntemde gerçek QML seçim,
önkontrol, insan varsayım onayı, ayrı spawn, kimlikli çıktı export, atomik kayıt,
reopen;5 çevrimdışı konu. Gerçek MI worker iptali ACTIVE/sonuç değiştirmez.
Kaynak hash ve source kayıt kimlikleri korunur. KNN/iterative/indicator mevcut
Model hazırlığında; eksiklik/sampling/weights Karşılaştır içinde aynı controller.
Kaynak ve kurulu wheel walkthrough kanıtı final kontrol kaydında ayrı tutulur.

<a id="e33-learning"></a>
## H — çevrimdışı öğrenme

Katalog49/172 konu: eksiklik varsayımları, temsil, örneklem yanlılığı, ağırlık
türleri ve ayrı MI. model-imputation rehberi fold-içi KNN/iterative ve tek/çoklu
ayrımıyla genişledi. MCAR rastgele cihaz arızası; MAR kayıtlı yaşa göre eksik
cevap; MNAR yüksek geliri bildirmeme. Mekanizma tespit edilmez.5 gerçek yardım
bağı; okuma hesap veya ağ başlatmaz. Kaynak URL'leri atıftır, runtime bağımlılığı
veya otomatik ağ eylemi değildir.

<a id="e33-limits"></a>
## Sınırlar ve kabul ayrımı

MI yalnız numeric Gaussian posterior ve normal mean/full-rank OLS;5000 satır,
20 alan,2..20 realizasyon,1..30 iterasyon. Predictive CV, categorical/bounded,
weighted/survey MI, p/R²/prediction pooling yok. Yakınsama/dağılım insan
incelemesi gerekir. KNN <=5000 training kayıt ve pair-distance RAM bütçesi;
üzerindeki scope reddedilir, sessiz sample yok. Diğer ileri yollar10000 satır;
1024 null desen;20 alan. Sample seçimi temsil garantisi değildir; stratified
adet her strata için aynıdır. Ağırlık türü açık; eksik/negatif reddedilir.
Survey WR ultimate-cluster Taylor, nested PSU,>=2 PSU/strata; sıfır varyans
ayrı işaretli; FPC/kalibrasyon/replicate/domain desteği yok.

Eski F13 kullanıcı, F25 insan/Orca/AT, F24 minimum donanım/fiziksel ölçüm,
F27 durdurulmuş dağıtım, Faz30 büyük SAS ve Faz31 clean offline cache açığı
korunur. Stage/commit/push yapılmaz; kullanıcı tracked/untracked dosyaları
korunur. Kaynak combined prompt değişmez; yalnız Faz33 uygulanır.


## Madde bazlı teknik tanıklar

[17 kabul kaydı](phase33/acceptance.json); C/V/G/H/P aynı yöntem ve gerçek ortamla bağlanır.

<a id="e33-s001"></a>

F33-S001: C src/veri_ufku/modeling/baseline.py, src/veri_ufku/statistics/missing_sampling.py; V test_fold_joint_fit_validation_values_never_learned_and_all_missing_rejected; test_mi_separate_realizations_observed_cells_and_delta_sensitivity; G/P preparation_knn/preparation_iterative; mi_mean/mi_ols; H katalog49. ENV-33/2026-10-11; final-targeted ve source/wheel walkthrough. Resmî faz kabulü yerine yalnız bu teknik kapsam doğrulanır.

<a id="e33-s002"></a>

F33-S002: C src/veri_ufku/modeling/plan.py, src/veri_ufku/statistics/missing_sampling.py; V test_fold_joint_fit_validation_values_never_learned_and_all_missing_rejected; test_mi_separate_realizations_observed_cells_and_delta_sensitivity; G/P mi_mean/mi_ols; missing_patterns; H katalog49. ENV-33/2026-10-11; final-targeted ve source/wheel walkthrough. Resmî faz kabulü yerine yalnız bu teknik kapsam doğrulanır.

<a id="e33-s003"></a>

F33-S003: C src/veri_ufku/statistics/missing_sampling.py, src/veri_ufku/domain/capabilities.py; V test_seed_sampling_membership_and_cluster_integrity; test_survey_hand_two_strata_nested_psus_and_no_lonely_adjustment; G/P sample_random/sample_stratified/sample_cluster; weighted_mean/weighted_ols/weighted_fit/survey_mean; H katalog49. ENV-33/2026-10-11; final-targeted ve source/wheel walkthrough. Resmî faz kabulü yerine yalnız bu teknik kapsam doğrulanır.

<a id="e33-s004"></a>

F33-S004: C src/veri_ufku/statistics/missing_contracts.py, src/veri_ufku/learning/content/tr.json; V test_hand_weighted_mean_semantics_and_reopen_exportable_identity; test_rubin_hand_calculation_and_barnard_rubin_not_average_se; test_bad_weights_rejected_without_mutation; G/P all14; five actual F1 contexts; H katalog49. ENV-33/2026-10-11; final-targeted ve source/wheel walkthrough. Resmî faz kabulü yerine yalnız bu teknik kapsam doğrulanır.

<a id="e33-p001"></a>

F33-P001: C src/veri_ufku/statistics/missing_sampling.py; V test_patterns_indicators_null_not_mechanism; G/P missing_patterns; H katalog49. ENV-33/2026-10-11; final-targeted ve source/wheel walkthrough. Resmî faz kabulü yerine yalnız bu teknik kapsam doğrulanır.

<a id="e33-p002"></a>

F33-P002: C src/veri_ufku/modeling/baseline.py, src/veri_ufku/statistics/missing_sampling.py; V test_patterns_indicators_null_not_mechanism; test_fold_joint_fit_validation_values_never_learned_and_all_missing_rejected; G/P missing_indicators; preparation_knn/preparation_iterative; H katalog49. ENV-33/2026-10-11; final-targeted ve source/wheel walkthrough. Resmî faz kabulü yerine yalnız bu teknik kapsam doğrulanır.

<a id="e33-p003"></a>

F33-P003: C src/veri_ufku/modeling/baseline.py, src/veri_ufku/modeling/lifecycle.py; V test_fold_joint_fit_validation_values_never_learned_and_all_missing_rejected[knn]; G/P preparation_knn; H katalog49. ENV-33/2026-10-11; final-targeted ve source/wheel walkthrough. Resmî faz kabulü yerine yalnız bu teknik kapsam doğrulanır.

<a id="e33-p004"></a>

F33-P004: C src/veri_ufku/modeling/baseline.py, src/veri_ufku/modeling/lifecycle.py; V test_fold_joint_fit_validation_values_never_learned_and_all_missing_rejected[iterative]; G/P preparation_iterative; H katalog49. ENV-33/2026-10-11; final-targeted ve source/wheel walkthrough. Resmî faz kabulü yerine yalnız bu teknik kapsam doğrulanır.

<a id="e33-p005"></a>

F33-P005: C src/veri_ufku/statistics/missing_sampling.py; V test_rubin_hand_calculation_and_barnard_rubin_not_average_se; test_mi_separate_realizations_observed_cells_and_delta_sensitivity; test_parent_rejects_forged_mi_covariance_before_active; G/P mi_mean/mi_ols; H katalog49. ENV-33/2026-10-11; final-targeted ve source/wheel walkthrough. Resmî faz kabulü yerine yalnız bu teknik kapsam doğrulanır.

<a id="e33-p006"></a>

F33-P006: C src/veri_ufku/statistics/missing_sampling.py; V test_mi_separate_realizations_observed_cells_and_delta_sensitivity[mi_mean]; G/P mi_mean/mi_ols; H katalog49. ENV-33/2026-10-11; final-targeted ve source/wheel walkthrough. Resmî faz kabulü yerine yalnız bu teknik kapsam doğrulanır.

<a id="e33-p007"></a>

F33-P007: C src/veri_ufku/statistics/missing_sampling.py; V test_seed_sampling_membership_and_cluster_integrity[sample_random]; G/P sample_random; H katalog49. ENV-33/2026-10-11; final-targeted ve source/wheel walkthrough. Resmî faz kabulü yerine yalnız bu teknik kapsam doğrulanır.

<a id="e33-p008"></a>

F33-P008: C src/veri_ufku/statistics/missing_sampling.py; V test_seed_sampling_membership_and_cluster_integrity[sample_stratified]; G/P sample_stratified; H katalog49. ENV-33/2026-10-11; final-targeted ve source/wheel walkthrough. Resmî faz kabulü yerine yalnız bu teknik kapsam doğrulanır.

<a id="e33-p009"></a>

F33-P009: C src/veri_ufku/statistics/missing_sampling.py; V test_seed_sampling_membership_and_cluster_integrity[sample_cluster]; G/P sample_cluster; H katalog49. ENV-33/2026-10-11; final-targeted ve source/wheel walkthrough. Resmî faz kabulü yerine yalnız bu teknik kapsam doğrulanır.

<a id="e33-p010"></a>

F33-P010: C src/veri_ufku/statistics/missing_sampling.py, src/veri_ufku/domain/capabilities.py; V test_hand_weighted_mean_semantics_and_reopen_exportable_identity[frequency]; test_bad_weights_rejected_without_mutation; G/P weighted_mean; H katalog49. ENV-33/2026-10-11; final-targeted ve source/wheel walkthrough. Resmî faz kabulü yerine yalnız bu teknik kapsam doğrulanır.

<a id="e33-p011"></a>

F33-P011: C src/veri_ufku/statistics/missing_sampling.py, src/veri_ufku/domain/capabilities.py; V test_hand_weighted_mean_semantics_and_reopen_exportable_identity[analytic]; G/P weighted_mean; weighted_ols; H katalog49. ENV-33/2026-10-11; final-targeted ve source/wheel walkthrough. Resmî faz kabulü yerine yalnız bu teknik kapsam doğrulanır.

<a id="e33-p012"></a>

F33-P012: C src/veri_ufku/statistics/missing_sampling.py, src/veri_ufku/domain/capabilities.py; V test_survey_hand_two_strata_nested_psus_and_no_lonely_adjustment; test_bad_weights_rejected_without_mutation; G/P survey_mean; H katalog49. ENV-33/2026-10-11; final-targeted ve source/wheel walkthrough. Resmî faz kabulü yerine yalnız bu teknik kapsam doğrulanır.

<a id="e33-p013"></a>

F33-P013: C src/veri_ufku/statistics/missing_sampling.py, src/veri_ufku/domain/capabilities.py; V test_sample_weight_linear_loss_without_survey_inference; test_unsupported_weight_old_and_new_methods_rejected; G/P weighted_fit; H katalog49. ENV-33/2026-10-11; final-targeted ve source/wheel walkthrough. Resmî faz kabulü yerine yalnız bu teknik kapsam doğrulanır.


Son dar survey renderinde hesaplanan NumPy Float64 tasarım etkisi Qt tarafından sayı olarak sunulmadı. Python float sınırı açıkça uygulanarak düzeltildi; hesaplanan değer değişmedi. Son36 test/60,19s ve source/wheel14'er walkthrough bu düzeltmeyle tekrar geçti. GUI şimdi tasarım etkisini numeric gösterir ve testi “sunulmuyor” mesajını reddeder; eski başarılı ekranlar `source-gui-before-scalar` / `wheel-gui-before-scalar` altında ayrı tutulur.
