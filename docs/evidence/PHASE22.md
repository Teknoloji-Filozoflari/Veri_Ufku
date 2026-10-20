# Faz22 — yerel metin teknik kabul

2026-10-09 Europe/Istanbul, ENV-22. Linux x86_64/kilitli CPython3.13.15,
PySide6/Qt6.11.2 ve offscreen/software. Kullanıcı açık Faz22 seçmiştir;
önceki insan/bağımlılık kabulü açık, sürüyor/deneysel/zorunlu. Faz23 başlamadı.

<a id="e22-s001"></a>
## E22-S001 — gerçek yerel yol

`analytics/text.py`, `ui/text.py`, `TextPanel.qml`, `TextOptions.qml`,
`TextFrequencyPlot.qml`, `storage/text_store.py`. Immutable snapshot,
CPU spawn, ilerleme/iptal/eski bağ ve atomic safe summary kaydı/reopen.
[ADR-025](../adr/025-local-text-phase22.md).

<a id="e22-s002"></a>
## E22-S002 — Türkçe, boş kolon ve betimleme

Null/empty/whitespace/token-kalmayan, ham code-point uzunluk, gerçek kelime/
n-gram/doc-frequency, seçilebilir Türkçe/İngilizce/özel stopword, TF-IDF/IDF
incelemesi;100 terim tablo/15 grafik. I/İ/ı/i, decomposed Unicode, NFC/NFKC,
casefold/aksan/numerik seçimleri bağımsız örneklerle testlidir. Dil kullanıcı seçimi.

<a id="e22-s003"></a>
## E22-S003 — etiketli eğitim ve temel benzerlik

PreparationSpec.text, blueprint tfidf, TextPreparation sklearn Pipeline;
mevcut sınıflandırma/baseline/CV/eşik/final defteri. Her fold vocab/IDF yalnız
train; test/validation tokenları vocab'a eklenmez, fit RowId ayrık. Betimsel
inceleme vocab'ı taşınmaz. Kosinüs ayrı opt-in ve ≤1000 tam belge/30 pozitif çift;
anlam/duygu/konu sınıfı uydurulmaz. Güvenli metin model paketi henüz desteklenmez.

<a id="e22-s004"></a>
## E22-S004 — içerik ve maliyet

Ham preview opt-in, ilk5×200 karakter ve30 token; sonuç belleğinde, loglarda
ve project result kaydında yok. Yerleşik önce/sonra Türkçe örnek görünürdür.
100000 belge/10m karakter,50000 aday vocab/10000 tutulan vocab/5m n-gram ve
sparse nnz, kontrollü ret/ilerleme/iptal. Kaynak korunur.

<a id="e22-s005"></a>
## E22-S005 — çevrimdışı yardım

Katalog30/144 makale; text-tokens/language/tfidf/similarity. Token/n-gram,
stopword/dil/Unicode, TF-IDF training vocab ve benzerlik anlamı/sınırları.
Öğren Modelleme ağacı, capability ve QML bağları. Yeni try_action yok.

<a id="e22-s006"></a>
## E22-S006 — gerçek doğrulama

`tests/test_text.py`, `tests/test_text_gui.py`: Unicode/Türkçe/boş kolon,
elle hesaplanan frekans/IDF/L2, sınıflandırma fold fit spy, vocab ayrımı,
preview privacy/caplog/kaydet/reopen, limits/cancel ve gerçek QML/spawn/final defteri.
597 testin tümü son kodla geçti (214.46s); hedefli metin/GUI/öğren testleri
26 geçti (8.50s). Kaynak ve kurulu non-editable wheel, gerçek QML/CPU spawn,
baseline/logistic/forest karşılaştırması ve final test defteriyle çalıştırıldı.

## Kontrol kayıtları

Tüm kayıtlar 2026-10-09, [ENV-22](phase22/environment.json). Her satır kendi
gerçek komut çıktısına bağlıdır; sistem Python sonucu kilitli ortam sonucu değildir.

| Kimlik | Gerçek kontrol | Sonuç / kanıt |
|---|---|---|
| E22-LOCK | `uv sync --locked --group dev` | Geçti; [sync](phase22/sync.txt), lock değişmedi/yeni bağımlılık yok |
| E22-DOCS | Sistem `python3 scripts/check_docs.py` ve kilitli belge kontrolü | [sistem](phase22/system-docs.txt), [kilitli](phase22/docs.txt) |
| E22-ARTIFACT | `uv run --frozen python scripts/check_artifacts.py` | Geçti; [artifact](phase22/artifacts.txt) |
| E22-HELP | `uv run --frozen python scripts/check_learning.py` | Geçti; 144 makale/90 UI bağı; [learning](phase22/learning.txt) |
| E22-RUFF | Ruff check ve format --check | Geçti; [check](phase22/ruff-check.txt), [format](phase22/ruff-format.txt) |
| E22-TARGET | `.venv/bin/pytest tests/test_text.py tests/test_text_gui.py tests/test_learning.py -q` | 26 geçti; [targeted](phase22/targeted.txt) |
| E22-FULL | Kilitli pytest tam regresyon | 597 geçti; [pytest](phase22/pytest.txt) |
| E22-UNIT | Kilitli `python -m unittest discover -s tests -v` | 9 belge testi geçti; [unittest](phase22/unittest.txt) |
| E22-SYSTEM-UNIT | Sistem `python3 -m unittest discover -s tests -v` | Başarısız: sistem Python3.14.7 PySide6/Polars içermez; 59 kontrol/50 import hatası; [system-unittest](phase22/system-unittest.txt). Bu sonuç başarılı sayılmadı. |
| E22-SOURCE | Offscreen/software `uv run --frozen python scripts/measure_phase22.py --output docs/evidence/phase22/source.json` | Geçti; [source](phase22/source.json), [log](phase22/source.log) |
| E22-WHEEL | `uv build --wheel` ve non-editable hedefe `uv pip install --no-deps --reinstall --target …` ardından aynı ölçüm | Geçti; [build](phase22/build.txt), [install](phase22/install.txt), [wheel](phase22/wheel.json), [log](phase22/wheel.log) |
| E22-ENTRY | Kurulu `bin/veri-ufku --smoke-test`, offscreen/software | GUI_SMOKE PASS; [entry](phase22/entry.txt) |
| E22-INTEGRITY | Kaynak/kurulu paket SHA256 eşitliği | Son analitik/QML/storage/model dosyaları eşit; [integrity](phase22/integrity.json); kaynak prompt korunmuştur |

Kaynak 120 belge 1.036s, 100000 belge 3.256s; wheel 120 belge 1.015s,
100000 belge 3.378s. Bu sentetik corpus yalnız beş terimlidir; büyük vocab için
aynı performans iddiası değildir. Qt tick en büyük gözlenen aralık kaynakta
1163ms, wheel'de1151ms: başlatma/GUI hazırlığı da ölçüme dahildir; 60fps iddiası yok.
Kaynak hash önce/sonra aynı; preview açık/kapalı ve kaydet/reopen testlerinde ham
önizleme kalıcı sonuçta yok. Hassas sentetik marker, yakalanan loglarda ve izole
ölçümün uygulama loglarında bulunmadı. Toplu frekans terimleri sonuçlarda saklanır;
bu modül metinleri anonimleştirmez.

Python TCP connect ana süreçte ve yeniden içe aktarılan spawn süreçte engellendi;
yardım, inceleme, benzerlik, üç sınıflandırma adayı ve reopen geçti. Bu gerçek
çevrimdışı çalışma kanıtıdır; işletim sistemi ağ arayüzleri kapatılmadı, temiz
internetsiz kurulum kanıtlanmadı. No API/embedding/dış istek bağımlılığı yok.

1366×900 ve720×560 gerçek pencere görüntüleri:
[geniş ayar](phase22/source-settings-1366.png),
[dar ayar](phase22/source-settings-720.png),
[geniş frekans](phase22/source-frequencies-1366.png),
[dar frekans](phase22/source-frequencies-720.png).
Dar ayar ve geniş frekans görüntüsü görsel olarak incelendi; gerçek kullanıcı
masaüstü kabulü veya Wayland kabulü bu başsız kontrolden çıkarılmadı.

Metin pipeline'ı için güvenli model paketleme/yeni dosya tahmini açıkça kapalıdır;
değerlendirme özeti proje içinde saklanır. Önceki insan/bağımlılık kabulü açık
olduğu için faz sürüyor, yetenek deneysel, kapsam zorunlu; teknik kabul doğrulandı.
Faz23 başlatılmadı.
