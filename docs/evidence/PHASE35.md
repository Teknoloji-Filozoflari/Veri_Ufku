# Faz35 — gerçek teknik kabul kaydı

<a id="e35"></a>
2026-10-11; DEC-35-01; [ENV-35](phase35/environment.json): kilitli
CPython3.13.15, Linux x86_64, Qt6.11.2 offscreen/software. Ana kayıt
REQUIREMENTS_MATRIX. Resmî faz sürüyor / deneysel / zorunlu; önceki kabul
kapıları korunur. Bu kayıt teknik doğrulamadır.

Tek registry ve mevcut ChartSpec/worker/ProjectStore yolu üzerinden
violin, KDE, ECDF, rug, strip/swarm, QQ/PP, error-bar/CI band,
missing-pattern; histogram/box grup/facet/ağırlık desteği eklendi.
Bandwidth/bin, normalizasyon, agregasyon, dışlanan n ve örnek kapsamı
sonuçta görünür. SD/SE/CI seçimi belirsizlik grafiklerinde ana formda;
Yalnız mean agregasyonu geçerlidir; başka seçim kontrollü reddedilir.
mean/SD/SE/df/critical/confidence ve varsayım metadata ile kaydedilir.
Başlık/eksen/palet/font/annotation/DPI görünümü değiştirir; kaynak değişmez.
Ham sütun özeti ağırlıksızdır; ağırlıklı grafik referansı ayrı gösterilir.

Tam regresyon **917 passed / 727.39s /
0 failure-error-skip**: [JUnit](phase35/pytest.xml),
[çıktı](phase35/pytest.txt), [45 Faz35 vaka kimliği](phase35/test-cases.json).
32 çekirdek ve 13 gerçek GUI vakası. Son tam koşu başladıktan sonra uygulama/test dosyaları değişmedi;
[350 dosyalık başlangıç kaydı](phase35/full-start-head.json) son hashlerle eşleşir.
Son arayüzde **15 gerçek GUI testi** (13 yeni +
2 mevcut), [JUnit](phase35/final-gui.xml), [çıktı](phase35/final-gui.txt).
Son kaynak ve wheel denemeleri bu arayüzü kullanır.

Bağımsız SciPy gaussian_kde referansı: ağırlıksız, analitik ve frekans
(tekrarlanmış örnek) yoğunlukları/bandwidth eşleşir. Elle histogram
count/probability/density/percent, frekans box quantile, ECDF ties,
QQ normal quantile/PP CDF, null bit desenleri doğrulanır. SD/SE/95% CI
2,4 örneği: mean3, SD=sqrt(2), SE1, df1, t critical12.7062047364.
Swarm501 reddi, açık20 örnek seçimi; küçük/sabit KDE/QQ/PP ret;
Boş/nonfinite/negatif/eksik ağırlık, kesirli frekans ve tümü sıfır
ağırlıklar reddedilir; tekil sıfır ağırlık açıkça sayılıp dışlanır.
Symlog koordinatları Matplotlib transform ile eşleşir. Log sıfır/negatif
ve interval endpoint reddi; görünüm değişince plot noktaları aynı kalır.
Kategorik etiketlerin ölçek ayarında korunması SVG ile doğrulanır.

Kaynak ve noneditable kurulu wheel **13'er gerçek QML/spawn/F1-Escape**
vakası; 26'şar geniş/dar render = **52 ekran görüntüsü**;
39'ar gerçek PNG/SVG/PDF export = **78 çıktı**. Her PDF sistem Poppler ile
metin ve raster kontrolünden geçti. Font ligatürü tam UUID çıkarımını
bölebildiği için PDF metninde n/DPI, SVG/JSON'da tam sürüm kimliği ve
kaydedilen snapshot bağı denetlenir. Export ve üyelik source/wheel'de
kayıt/açılışla doğrulanır; kaynak hash'i değişmez.
[Kaynak walkthrough](phase35/source-gui/walkthrough.json),
[kurulu walkthrough](phase35/wheel-gui/walkthrough.json).
Violin/CI PDF ve dar box GUI araçla görsel incelendi; fiziksel masaüstü
veya insan kullanılabilirlik kabulü değildir.

**229 paket dosyası kaynak/wheel/kurulu byte eşitliği**:
[manifest](phase35/wheel.json). Kurulu giriş **GUI_SMOKE PASS**:
[çıktı](phase35/wheel-smoke.txt). Wheel mevcut `.venv` bağımlılıklarını
kullanır; temiz çevrimdışı kurulum değildir. pyproject/uv.lock değişmedi.
14 belge unittest ve son docs/artifacts/learning/usability/Ruff check+
format gerçek komutları [checks](phase35/checks.json) içinde.
[19 C/V/G/H/P kaydı](phase35/acceptance.json),
[son source/test/script/lock hashleri](phase35/source.sha256),
[korunan kaynak prompt hash'i](phase35/source-prompt.sha256).

İlk tanılarda test yardımcı API'si, QML yardım alanı bildirimi, filtre
alanları, profiler sonuç karşılaştırması ve PDF font ligatürü kontrolü
düzeltildi. Son koşuların yerine ilk başarısız koşular sayılmaz. İlk smoke ortamı tüm XDG dizinleri izole edilmeden exit2 verdi; dört XDG
dizini izole edilerek gerçek kurulu giriş geçti. İlk tam regresyonda registry
operasyonlarının eksik listesi nedeniyle 916pass/1fail vardı; tüm altı
operasyon açık destek durumuyla kaydedildi ve son tam koşu yeniden çalıştı.
Mean sözleşmesi netleştirilirken ikinci koşu 144 testten sonra kesildi;
[bu kısmi koşu](phase35/interrupted-pytest.txt) kabul kanıtı değildir.
[İlk başarısız tam koşu](phase35/initial-pytest.txt) korunur.

Sınırlar [ADR036](../adr/036-distribution-charts-phase35.md): en fazla4
facet,5000 KDE örneği/128grid,500 swarm/10000point; swarm piksel çakışmasızlığı
garantilemez. Density Gaussian kernel, görüntü aralığı observed±3bandwidth;
kesilen kuyruk yeniden normalize edilmez. Violin genişliği her grup/facet
peak yoğunluğunu 0.35 yarı genişliğe ölçekler; sayım genişliği değildir. Analitik ağırlık burada açık
betimsel kütledir; survey/sample_weight desteklenmez. CI band noktasal,
iid varsayımlı; survey/eşzamanlı bant değildir. Facet zoom yerine açık
filtre istenir. Missing-pattern yalnız null; mekanizma çıkarmaz.

Önceki F13/F24/F25/F27, Faz30 büyük SAS ve Faz31 temiz offline cache
kabulleri açık. Fiziksel masaüstü, insan/AT, minimum donanım, temiz offline
kurulum ve remote CI çalıştırılmadı. Stage/commit/push yapılmadı;
Faz36 başlamadı. Önceki hafıza [arşiv](phase35/prior-project-state.txt).
