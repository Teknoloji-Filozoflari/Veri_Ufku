# Faz68 — Monte Carlo, sensitivity ve optimizasyon

2026-10-16 DEC68-01 / ENV-68. Açık kullanıcı talimatıyla sınırlı yerel CPU kapsamı.
Resmî sürüyor/deneysel/isteğe bağlı. Önceki tüm kabul açıkları korunur; Faz69 başlamaz.

<a id="e68-scope"></a>
## E68-SCOPE

Model ekranı → Simülasyon, senaryo ve optimizasyon. Komut paleti scenario.* gerçek
formu açar; yalnız kullanıcı run düğmesi hesap başlatır. Normal/uniform/triangular;
explicit independent veya joint-normal correlated; seed/draw/uncertainty type,
output quantiles/mean/SD/Monte Carlo error ve sensitivity. LP/MILP HiGHS, bounded
quadratic/model SLSQP, objective/constraints/units/feasibility/status/gap/tolerance/
timeout. Kaynak/model değişmez; safe frozen regression what-if ve model-optimize
fit-domain kontrolü. Limits ve matematiksel/gerçek uygulanabilirlik ayrımı görünür.
[Sözleşme/varsayımlar ve resmi kaynaklar](../adr/069-simulation-optimization-phase68.md).
Tek registry/ComputeBudget/Provenance/ProjectStore ve append-only test/run journal.

<a id="e68-validation"></a>
## E68-VALIDATION

İlk kaynak faz testleri [23passed/2failed](phase68/source-initial.xml): LP'de SciPy'nin
mip_gap=0 alanı LP gap gibi taşınmıştı, adapter düzeltildi; lineage test helper adı
build yerine gerçek graph API'siyle düzeltildi. Sonraki
[48passed focused](phase68/source-focused.xml):25faz,19monitoring ve workspace dahil.
Koşular ayrı kapsamdır, toplama veya tam-depo regresyon iddiası yok.

Önceki fiziksel masaüstü,
insan/AT/minimum donanım/long retained heap/clean offline installer/remote CI,
Faz65/66 default2GiB büyük model/tuning ve GPU/remote, Faz67 Secret Service provisioning
kapıları bu fazın sayısal testleriyle kapanmaz.


Son analitik kapsam: [90source](phase68/source-core.xml)/[90wheel](phase68/wheel-core.xml)
PASS;25faz vakası,19monitoring ve registry/workspace/repro/workflow ilgili regresyon.
Kasıtlı duplicate ZIP config.json tamper uyarısı. Bunlar48focused veya önceki faz
sayılarıyla toplanmaz. [İzlenebilir doğrulama](phase68/verification.json),
[sekiz teknik kabul kaydı](phase68/acceptance.json), [ortam](phase68/environment.json).

Gerçek GUI: [source6pass](phase68/source-walkthrough/gui.xml)/
[wheel6pass](phase68/wheel-walkthrough/gui.xml), her birinde9capture: Monte Carlo,
LP, MILP, bounded quadratic, frozen model what-if/optimize ve infeasible/unbounded/
timeout. Basic/status default2GiB; model açık4GiB. Actual command palette/form/button,
spawn, cancel, native atomic save ve hash ile reopen; model template düğmesi gerçek.
[Kaynak ölçüm](phase68/source-walkthrough/measurement.json),
[paket ölçüm](phase68/wheel-walkthrough/measurement.json);1000/1366px PNG'ler.
Donanım Ryzen7 8845HS/16visibleCPU; bazı bağımsız test runnerları aynı donanımı
paylaştı. Sayılar minimum donanım/idle/performance iddiası değildir.

İlk görselde uygulanmayan gap/bound alanlarının undefined görünümü düzeltildi;
son QML sunulmuyor/uygulanmaz yazar. [Source son model1pass/5deselected](phase68/source-final-model/gui.xml),
[wheel son model1pass/5deselected](phase68/wheel-final-model/gui.xml), explicit4GiB,
iki model capture. Analitik Python90şar koşuyla byte-eşit, fark yalnız QML sunumu.
[Son1000px model görünümü](phase68/source-final-model/model-optimize-1000.png)
ajan tarafından incelendi; Monte Carlo1000px de incelendi. İnsan/AT kabulü değildir.
Ortak job yaşam döngüsü refactor sonrası eski monitoring ekranı
[source1pass/1deselected](phase68/source-monitor-regression/gui.xml)/
[wheel1pass/1deselected](phase68/wheel-monitor-regression/gui.xml), default2GiB.

[387byte-eşit kaynak/kurulu paket dosyası](phase68/wheel.json); yeni dependency,
model indirmesi veya network eylemi yok. Monte Carlo ve safe-model senaryo harici
model aileleri/categorical/integer-feature optimization/general nonlinear code,
genel copula, GPU/remote solver ve nested epistemic variance decomposition yok.
Bu sınırlar GUI/yardım/registry ve ADR'de açık. No convergence global infeasibility
kanıtı değil; feasible gerçek dünyada uygulanabilirlik değil.

[Son kapılar](phase68/gates.json): docs/artifacts/learning/usability, Ruff check/format ve14 belge testi geçti.408offline makale/199UI binding/971namedfield. [Teslim dosya hashleri](phase68/delivery.json). Stage/commit/push yapılmadı; mevcut kullanıcı dirty/untracked değişiklikleri korunur.
