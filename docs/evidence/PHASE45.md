# Faz45 — sağkalım ve olay zamanı

<a id="e45"></a>
2026-10-12;DEC45-01 açık kullanıcı talimatı;ENV-45. [ADR046](../adr/046-survival-phase45.md)
backend/censoring/metrik ve prediction sınırlı sözleşmesi. KM/risk table,logrank,
CoxPH,Breslow/Efronties,lognormalAFT ve competingrightCIF. Entry desteği backend
bazında;interval/leftcensoring,time-dependentfit ve Brier/AUC kapalı. Graph/rapor/
modelpersistence mevcutregistry/atomicprojectpath. Çalıştırılmayan kapı geçmedi;
fizikselmasaüstü/insan/AT/minhardware/offlineinstall/remoteCI bu fazda açık.

## Son teknik kanıt

ENV-45 kilitli **CPython3.13.15 `.venv`**;statsmodels0.15.0/SciPy1.18.0/
NumPy2.5.3/Polars2.0.0/PySide6.11.2/Matplotlib3.11.2. Yeni bağımlılık yok.
[Ortam](phase45/environment.json),[18 C/V/G/H/P kayıt](phase45/acceptance.json).
F45-S001..004/P001..014 teknik kapsam doğrulandı. Resmî faz **sürüyor/deneysel/
zorunlu**; closed backend desteğinin doğrulanması o yöntemin fit implementation'ı
olduğu anlamına gelmez. P003interval/leftcensoring,P012IPCWtimeBrier/AUC,
P014time-dependentfit kapalı; P014ayrıcountingprocessvalidator uygulanmıştır.

Son kaynakta **154 ilgili vaka** geçti/0failure/0skip;123.02s:
[JUnit](phase45/targeted.xml),[çıktı](phase45/targeted.txt),
[tekil test ve süre özeti](phase45/test-summary.json). **34 Faz45 vakası**:
26core+8gerçekQML. Noneditable installed wheel aynı34/0skip geçti;86.62s:
[JUnit](phase45/wheel-targeted.xml),[çıktı](phase45/wheel-targeted.txt).
Diğer120vaka önceki istatistik/model/causal/registry/learning/usability yoludur;
**tüm depo regresyonu çalıştırılmadı**, eski tam regresyon tekrar koşulmuş sayılmaz.
14belge unittest ve docs/artifacts/learning/usability/Ruffcheck-format geçti.

Küçük KM0.8/0.6/0.3 ve risk10/8/4,group/right/entry risk eligibility;
independenthypergeometriclogrank;CIFcause0.4/0.3toplam0.7. CoxBreslow/Efronright/
entry independentpartiallikelihoodscalarMLE ve event-inclusivebaselinecumhazard;
stratabasalines/predictiongroup. AFTuncensoredlogOLSMLE/scale,analyticgradient
numericdifference ve censoredSciPylogpdf/logsf likelihood. Harrellcomparablepairs,
scoreties0.5,event/censor sametime,entry/strataclosure. Negativeduration/invalidentry/
null/causecode/units/extrapolation ret;eventscarcity/rank/separation/convergence/
AFTboundaryfail modelNone;PHdescriptive screen açık,formalPH p-test değildir.
Time-dependentstart/stop/sourceid overlap/gap/terminaleventschema ret ve fitclosure.
Censoring/units/source/RowId/SourceRecordId/hash mutation parentpublish ret.

GerçekQML:five methods + noeventKM + entryKM + few-eventCox; visibleunsupported
intervalselectorret,preflight/explicitapproval/spawn,cancel,PNG/riskpanel,
help-F1/Escape,export/save/fresh-result-reopen,safeJSONmodelreuse,extrapolation/
stalesave/predictret. Source/wheel8'er case×2width×4positions: **64+64PNG ve40+40safe
JSON/Parquet/PNG export**. [Source](phase45/source-gui/walkthrough.json),
[wheel](phase45/wheel-gui/walkthrough.json),[geliştirici görsel inceleme](phase45/visual-review.json).
270packagefile source/wheel/installbyteeşitliği [manifest](phase45/wheel.json);
275frozenapplication/test/script/lock file sonkontrollerde değişmedi
[head](phase45/head-verification.json). Fresh4XDGinstalledentry
[GUI_SMOKE PASS](phase45/wheel-smoke.txt). Katalog61/291;
152UIbinding/617namedfield/189finishedcoreEnglish. [Learning](phase45/learning.txt),
[usability](phase45/usability.txt),[belge unittest](phase45/doc-unit.txt).

## Olgunluk ve yöntem sınırları

Statik complete numeric 2–10000/nonmodel ve<=2000/modelrows;5baselinepredictor;
null/drop/imputation/weight/Decimal/Date/cluster yok. Censoring bağımsızlığı ve
truncation kullanıcı gerekçesi, gözlenen veriden ispat değil. KM başlangıç1,
özellikle delayedentryrisk desteği öncesinde normalization konvansiyonudur;
o bölgede population survival'ın gözlendiği iddiası değildir. Risk table'da
henüzgirmeyen ve sıfırrisk dönemleri açık. CIF ayrı causecoding, entryyok.
Log-normalAFT tüm dağılımlar için uygun değildir;time-ratioHRdeğil.
CoxPHscreening betimsel:rho>0.3flagheuristic,formal/calibratedtestyok;
EfronresidualmeansBreslowapproximation. NoflagPHkanıtı değil;güvenilirrozetiyok.
Delayedentryoriginprediction/strataC/entryC ve IPCWmetricbackend kapalı.
Safe model prediction trainingprofile/time desteğinde koşulluS(t), noCI/
bireyselprognosis veya heldoutvalidationclaim. HarrellCapparenttraining ve
censoringsensitive;IPCW C veya professionallyvalidatedprognosis sayılmaz.

İlk test planı defaultAnalysisSpeciterations1000 kullandı; boundedplan100 ile
fixture düzeltildi. Yeni modeleuse testi importPath/predict eksikliği çözüldü;
başarısız ilk koşular kabul değildir. İlk GUI 8passed, fakat son stale-label/
predictguard kontrolü ve curve çizimiyle son kaynak/wheel34 tekrar doğrulandı.
`initial-source-gui`/`pre-visual-final-*` eski ara kanıttır. Görsel incelemede
KMtail/noevents followup ve Coxsparsequerylinear interpolation sorunu bulundu:
KM observedfollowup boyunca uzatıldı;Coxgerçekbaselinesteps;AFTgerçeklognormalcurve,
explicit querypointmarkers;sonPNG kontrolü ve son34tests bu sürümdedir.
Pytestshutdown154/196uncollectableQtobjectResourceWarning mevcut;testfailure
veya insan/AT/lifetime/performance kabulü gibi sunulmaz.

Physical masaüstü/insan/Orca/AT/minhardware/cleanofflineinstall/remoteCI bu fazda
koşulmadı; önceki resmî açıklar korunur. Faz43monolithiclongsessionaggregateRAM
sınırı giderildi iddiası yok;budget gevşetilmedi. Connector sunucusu bu fazda
sınanmadı. Çalışma ağacı/untracked korundu;stage/commit/push yok. Faz46 başlamadı.
