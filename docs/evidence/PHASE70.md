# Faz70 — bilimsel rapor teknik kayıt

2026-10-16 · E70 · DEC70-01 · bounded teknik teslim; resmî kabul sürüyor.
Linux geliştirme ortamı, kilitli CPython3.13.15 .venv; Qt offscreen/software.
[Karar/kapsam](../adr/071-report-builder-phase70.md).
[Önceki durum/açıklar](phase70/prior-project_state.txt) korunur.

Çalıştırılmamış kontrol başarılı sayılmaz; aşağıdaki sonuçlar sınırlı teknik kapsama aittir.
DOCX ve local LLM uygulanmadı/doğrulanmadı. Fiziksel masaüstü, insan/AT,
minimum donanım, offline installer ve remote CI bu kayıtla kapanmaz.

<a id="e70-scope"></a>
## E70-SCOPE

Rapor → Bilimsel rapor oluşturucu;12blok türü,2preset ve kayıtlı tarif reuse.
Bölüm/not/varsayım manuel; yöntem/bulgu/model kartı/belirsizlik/diagnostic kayıtlı
run alanı ve referansı. Sözlük seçili ColumnId metadata; tablo ilk1..100satır,
maskeli kolon String ve CSV formula/null politikası; chart PNG+SVG/PDF byte bağları,
n/bin/filter/scope/normalization bağlamı; kaynakça HTTPS atıf metni, ağ açılmaz.
Deterministik anlatı ilk40 numeric native alanın birebir değerini referansla yazar;
veri yorumunu veya istatistiksel doğruluğu modelden türetmez. Eksik alan not_recorded.
Model seçim planı, exploratory/confirmatory kullanıcı beyanı ve mevcut final test
kullanım defteri korunur; test kullanılmadıysa başarı uydurulmaz.

Gerçek Markdown/HTML/PDF+ZIP. Gömülü DejaVuSans ve PNG, A4 Türkçe PDF yeniden
okunur; table CSV/Parquet, grafik SVG/PDF ve explicit numeric dictionary code_column
ile Faz63 reference-only script/SQL/notebook ZIP'i bağlanır. Script bütün raporu
hesaplıyor iddiası yok. Standalone MD/HTML/PDF yanında attachment yoksa bağlantı
çalışmaz; ZIP aynı dizine açıldığında bağlar taşınır. DOCX ve optional LLM yok.

Publish/export kaynak/run/artifact hash ve freshness/test-history token kontrolü;
rapor append-only mevcut ProjectStore/journal. Dataset sürümü/eski run STALE;
refresh/recompute açık eylem, açılışta ağ/hesap yok. Kayıtlı sonuçtan rapora lineage
edge ve dosya manifest hash'i gerçek. Redaction pattern/açık ColumnId/allow_graphics
sınırında; anonimlik garantisi yok, görsel içi yazı otomatik redakte edilmez.

Her id için ortam ENV-70, tarih2026-10-16; F70-S001..004 ve P001..006/P008..012
bu sınırlı teknik kapsamı ifade eder; P007/P013 mevcut değil/doğrulanmadı.
Resmî faz sürüyor/deneysel/isteğe bağlı; önceki kapılar açık.

<a id="e70-validation"></a>
## E70-VALIDATION

ENV-70 gerçek [donanım/kitaplıklar](phase70/environment.json); tüm komutlar kilitli
`.venv/bin/python` ile. Host Linux CPU; test ortamı offscreen/software, fiziksel
masaüstü değildir. Ağ/dependency/model indirmesi yapılmadı. Qt PDF/font kendi
worker runtime'ıdır; GUI Qt nesnesi worker'a gönderilmez.

İlk native kontrollerde PDF Türkçe metin/A4 reopen, email redaction, gerçek
CSV/Parquet row/type ve hash corruption; ardından gerçek histogram SVG/PDF ve
reference-only notebook attachment, trained baseline CV metrics/model card,
dataset/run stale ve lineage edge doğrulandı. Kontrollü iptal/kota/no-overwrite,
secret tarif reddi, HTML/Markdown injection ve credential/query URL reddi var.
Kaynak byte'ları değişmez; dosya hash'i önizleme ile eşleşmeden publish/export yok.

İlk core [83pass/1fail](phase70/source-core.xml): curriculum coverage beklentisi
eski403 idi; yeni report.builder ile404 olarak güncellendi. Sonra
[84source](phase70/source-final.xml) geçti. Son geniş odaklı koşu
[109source](phase70/source-complete.xml)/[109wheel](phase70/wheel-complete.xml) PASS:
report builder, code bridge, legacy exports, repro, experiment registry, learning,
learning lab ve workspace; tam depo testi değildir. Duplicate ZIP entry warning,
kasıtlı malicious-bundle negatif fixture'ından gelir, başarı uyarısı diye gizlenmez.

Ara test kusurları da korunur: [empty-import fixture](phase70/source-delivery-native.xml)
mevcut importer'ın sıfır satır reddine takıldı; raporun boş dataset'i desteklediği
iddia edilmedi. [quota fixture](phase70/source-delivery-native2.xml) reserve_disk=0
geçersizdi; pozitif varsayılan rezerv korunarak düzeltildi. Sonra
[29native+code](phase70/source-delivery-final.xml) PASS. Bu sayılar109ile toplanmaz.
İlk birlikte core+GUI denemesinde worker EOF görüldü; ayrı yeni GUI çalıştı.
[İlk kaydedilen GUI assertion failure](phase70/initial-gui-failure.txt) onay hatasının
ValueError ile genel mesaja dönmesiydi; kontrollü ProjectError olarak düzeltildi.
Font/PDF plugin prewarm mevcut export işçisiyle aynı bütçe sınırına alındı;
EOF için tek başına kök neden kesin bulundu iddiası yok, önceki longheap açık.

[İlk çalışan basic GUI](phase70/source-gui/gui.xml)1pass;
[iki kaynak GUI](phase70/source-final-gui/gui.xml)2pass;
[teslim source](phase70/source-delivery-gui/gui.xml)/[teslim wheel](phase70/wheel-delivery-gui/gui.xml)
ikişer PASS. GUI'de gerçek oluştur/kaydet, maskeli preview, onaysız export reddi,
açık ZIP export, cancel eski commit/sonucu koruma, close/reopen hash ve yardım var.
İkinci senaryo gerçek model+grafik kayıtlarını bağlar; model yeniden eğitilmez.
Basic varsayılan2GiB/model+grafik explicit4GiB; bu iki kapsam birbirine karıştırılmaz.
[Kaynak ölçüm](phase70/source-delivery-gui/measurement.json),
[wheel ölçüm](phase70/wheel-delivery-gui/measurement.json). Sampling100ms, kısa
zirveler kaçabilir; minHW/uzun heap ölçümü değildir. Model raporu ayrıntılı plan/
model kartı nedeniyle129sayfadır; özet sunum/kısa preset tercih edilebilir.

Türkçe font ve sayfa [basic PDF render](phase70/source-final-gui/basic/pdf-page-1.png)
ajan tarafından incelendi; [1000px GUI](phase70/source-gui/gui-1000.png) de incelendi.
PDF render transparan zemini beyaza kompoze eder; rapor PDF'i değiştirmez.
Görsel inceleme insan/AT veya bütün129model sayfasının okunabilirlik kabulü değildir.


Son helper/environment kaydı: PDF renderer, file publisher, code bridge ve font
hash'i backend import etmeden code closure'a dahil; PySide6/PyArrow sürümleri kayıtlı.
Legacy raporun artık yanlış olan “eğitim/tahmin mevcut değil” cümlesi, eski şablonun
model kartı taşımadığı ve yeni builder'da açık bağ kurulacağı açıklamasıyla düzeltildi.
Bundan sonra [34source](phase70/source-release.xml)/[34wheel](phase70/wheel-release.xml)
(report/native+legacy exports+registry) ve [2source GUI](phase70/source-release-gui/gui.xml)/
[2wheel GUI](phase70/wheel-release-gui/gui.xml) PASS. Sayılar109ile toplanmaz.
Son incelemede tek harfli hassas kolon x'in exploratory metnini substring olarak
maskeleyebilmesi bulundu; isim eşlemesi word-boundary oldu. [6source](phase70/source-mask-final.xml)/
[6wheel](phase70/wheel-mask-final.xml) maskeli numeric→String Parquet dahil son doğrulamadır;
önceki GUI sonucu yeniden çalıştırılmış gibi sayılmaz. [402byte-eşit paket](phase70/package-parity.json),
her iki kurulu wheel'ın editable olmayan import yolu measurement.json içinde.

Kaynak ve kurulu wheel test komutları:

```sh
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m pytest tests/test_report_builder.py tests/test_code_bridge.py tests/test_exports.py tests/test_repro.py tests/test_experiment_registry.py tests/test_learning.py tests/test_learning_lab.py tests/test_workspace.py -q
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase70.py --output /tmp/f70-source
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase70.py --output /tmp/f70-wheel --package-root /tmp/veri-ufku-f70-release-installed
PYTHONPATH=/tmp/veri-ufku-f70-mask-installed QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m pytest tests/test_report_builder.py -q
```

Build: `env UV_CACHE_DIR=/tmp/veri-ufku-f70-uv uv build --wheel --no-build-isolation --offline --out-dir /tmp/veri-ufku-f70-mask-wheel`;
kurulum `uv pip install --no-deps --python .venv/bin/python --target /tmp/veri-ufku-f70-mask-installed /tmp/veri-ufku-f70-mask-wheel/veri_ufku-0.1.0-py3-none-any.whl`.
Testler kullanıcı kaynağı yerine geçici fixture/project kullanır. Paket offline
build ve runtime kanıtıdır; tam offline installer/wheelhouse kabulü değildir.
Faz71 için yetki yok; önceki resmî açıkların hiçbiri bu testlerle kapanmaz.

<a id="e70-final"></a>
## E70-FINAL

Son report envelope artık doğrudan ortak `Provenance` dataclass ve `ComputeBudget`
serileştirmesidir; yeni köken/bütçe kayıt sistemi yok. DatasetVersion ve gerçek
SourceSnapshotId eşleşmesi validation'da kontrol edilir; tablo için yeni RowId
uydurulmaz. Bu son değişiklikten sonra [6source](phase70/source-provenance.xml)/
[6wheel](phase70/wheel-provenance.xml) ve [2source GUI](phase70/source-provenance-gui/gui.xml)/
[2wheel GUI](phase70/wheel-provenance-gui/gui.xml) PASS. Basic2GiB/model4GiB ayrımı
[son source](phase70/source-provenance-gui/measurement.json) ve
[son wheel](phase70/wheel-provenance-gui/measurement.json) içinde; yeni font/env/code
closure ile oluştur/kaydet/aç/iptal/export gerçekten yeniden çalıştırıldı.
[Son402byte-eşit package](phase70/package-parity.json) bu build'e aittir;
`build-provenance.log`/`install-provenance.log` offline noneditable kurulum kaydıdır.

Kapılar: [docs](phase70/docs-gate.log),[artifacts](phase70/artifacts-gate.log),
[learning](phase70/learning-gate.log),[usability](phase70/usability-gate.log),
[Ruff check](phase70/ruff-check.log),[format](phase70/ruff-format.log),
[14document unittest](phase70/document-tests.log) PASS. Son dosya değişikliklerinden
sonra statik kapılar tekrar kontrol edilir; unittest sonucu önceki çalıştırmadır,
yeniden çalıştırılmış diye sunulmaz. [Kurulu giriş noktası smoke](phase70/wheel-smoke.log)
GUI_SMOKE PASS; son binary smoke ayrıca `wheel-provenance-smoke.log` içindedir.
Resmî phase sürüyor/deneysel/isteğe bağlı; insan/AT/minHW/fiziksel/offlineinstaller/
remoteCI ve önceki process/longheap açıkları korunur.
