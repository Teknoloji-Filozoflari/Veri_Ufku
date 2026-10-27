# Faz21 — zaman serisi teknik kabul

2026-10-09 Europe/Istanbul, ENV-21. Kilitli CPython3.13.15/Linux x86_64,
PySide6/Qt6.11.2, offscreen/software ve izole geçici XDG. Bu kayıt teknik
kontroller içindir; yeni insan masaüstü/uzak CI kabulü yapılmadı.
Önceki insan/bağımlılık kabulü açık: sürüyor/deneysel/zorunlu. Faz22 başlamadı.

<a id="e21-s001"></a>
## E21-S001 — ayrı yol

`ui/qml/TimeSeriesPanel.qml`, `ui/time_series.py`, `modeling/time_series.py`:
Model → Zaman serisi ve yol haritası; ayrı spawn, iptal/bütçe ve eski bağ denetimi.
Güvenli JSON artifact ve kalıcı proje yeniden açılışı. [ADR-024](../adr/024-time-series-phase21.md).

<a id="e21-s002"></a>
## E21-S002 — zaman kontrolleri

Tarih/ölçüm/grup, IANA/DST, hizalama ve duplicate/eksik dönem kontrolleri;
varsayılan ret ve açık resample/sum/mean. Kaynak değişmez; boş bin sıfır olmaz.
Günlük/haftalık/aylık yerel takvim, saatlik UTC geçen saat; ns precision kaybı ret.

<a id="e21-s003"></a>
## E21-S003 — gerçek inceleme ve tahmin

Yalnız geliştirmede trend, mevsim faz ortalamaları, geçmiş hareketli ortalama.
Gerçek naive/seasonal-naive; sınırlı toplamsal ExponentialSmoothing; rolling-origin
MAE seçimi, gerçek baseline karşılaştırması, açık minimum geçmiş ve dönem.
Kaynak tarihinin ötesinde de aynı geliştirme fit'inden nokta tahmini; origin ve
saklı aralık mesafesi görünür. Aralık desteklenmiyor, uydurulmadı.

<a id="e21-s004"></a>
## E21-S004 — sızıntı ve final

Final son dönemdir; hiçbir eğitim/özellik/aday seçimine girmez. Gelecek ölçümleri
zehirleme testi aynı seçim/özellik/tahmini verir. Lag1 ve trailing pencere yalnız
önceki hedefler; grup RowId'leri ayrık. MAE/RMSE gerçek, MAPE yok ve nedeni açık.
Final öncesi pending kayıt, final frozen seçim, completed/iptal/hata/eski durumları;
yeni koşu ve yeniden açılış önceki kullanımları korur. Normal model defteri de
zaman serisi final kullanımlarını görür.

<a id="e21-s005"></a>
## E21-S005 — yardım

Katalog29/140 makale: timeseries-frequency/seasonality/lag/validation.
Sıklık/agregasyon/saat dilimi, dönem/geçmiş, lag/pencere, ufuk/rolling-origin ve
final disiplini; Modelleme Öğren ağacı ve capability/QML yardım bağları.

<a id="e21-s006"></a>
## E21-S006 — gerçek doğrulama

`tests/test_time_series.py`, `tests/test_time_series_gui.py`: bağımsız baseline
ve metrik değerleri, future poison, lag referansı, gruplar, düzensiz/duplicate/gap,
sum/mean, timezone/DST, çok kısa seri, değişmiş fingerprint/protokol, gerçek
QML/spawn/iptal/final defteri/reopen ve yardım. Çalıştırma sonuçları aşağıda kayıtlıdır.

## Çalıştırılmış kapılar ve gerçek artefactlar

ENV-21/date kayıtları [environment.json](phase21/environment.json), lock SHA256
`5b8b1e04184a9e2b0413f416c0c3e4be64f1d2fb5acf20ec4e1aab3c18b7f419`.

| Kimlik | Gerçek komut/iş | Sonuç ve kanıt |
|---|---|---|
| E21-LOCK | `uv sync --locked --group dev` | exit0; [sync](phase21/sync.txt) |
| E21-DOCS | sistem `python3 scripts/check_docs.py`, locked karşılığı | [sistem](phase21/system-docs.txt), [locked](phase21/docs.txt) |
| E21-ARTIFACT | `uv run --frozen python scripts/check_artifacts.py` | exit0; [artifact](phase21/artifacts.txt) |
| E21-HELP | `uv run --frozen python scripts/check_learning.py` | exit0,140 makale/85 UI bağ; [yardım](phase21/learning.txt) |
| E21-RUFF | `uv run --frozen ruff check src tests scripts`, `ruff format --check` | exit0; [check](phase21/ruff-check.txt), [format](phase21/ruff-format.txt) |
| E21-TARGETED | offscreen/software `.venv/bin/pytest tests/test_time_series.py tests/test_time_series_gui.py tests/test_learning.py -q` | 35 test/5.26s, exit0; [hedefli](phase21/targeted.txt) |
| E21-FULL | `uv run --frozen pytest -q` | 583 test/210.89s, exit0; [tam regresyon](phase21/pytest.txt). Koleksiyondan sonra eklenen üç ETS aday testi ayrıca35 hedefli koşuda geçti; bu log586 tam test gibi sunulmaz. |
| E21-UNIT | `uv run --frozen python -m unittest discover -s tests -v` | 9 test, exit0; [locked unittest](phase21/unittest.txt) |
| E21-SYSTEM-UNIT | sistem `python3 -m unittest discover -s tests -v` | exit1,57 test/48 import error; sistem Python3.14.7 PySide6/Polars vb. kilitli bağımlılıkları içermiyor. [Başarısız gerçek log](phase21/system-unittest.txt); başarılı sayılmadı. |
| E21-SOURCE | `uv run --frozen python scripts/measure_phase21.py` | 120 mevsimsel/100000 baseline; gerçek QML/spawn/final/reopen/source hash, exit0; [JSON](phase21/source.json), [log](phase21/source.log) |
| E21-WHEEL | `uv build --wheel --out-dir /tmp/veri-ufku-phase21-dist`; `uv pip install --no-deps --reinstall --target /tmp/veri-ufku-phase21-installed ...whl` | exit0; [build](phase21/build.txt), [install](phase21/install.txt). Bağımlılıklar locked runtime'dan gelir; temiz makine offline kurulum iddiası yok. |
| E21-INSTALLED | /tmp cwd, `PYTHONPATH=/tmp/veri-ufku-phase21-installed .venv/bin/python scripts/measure_phase21.py --package-root /tmp/veri-ufku-phase21-installed --output .../wheel.json` | import yolu noneditable hedefte doğrulanır; 120/100000 aynı gerçek yol exit0; [wheel JSON](phase21/wheel.json), [log](phase21/wheel.log) |
| E21-ENTRY | /tmp cwd, aynı PYTHONPATH/izole XDG/offscreen/software ile gerçek `/tmp/veri-ufku-phase21-installed/bin/veri-ufku --smoke-test` | exit0 GUI_SMOKE PASS; [kurulu giriş](phase21/entry.txt) |
| E21-GUI-FINAL | Canvas düzeltmesi sonrası gerçek QML/spawn pytest | 1 test, exit0; [son GUI](phase21/gui-final.txt) |

Kaynak120/100000 hesap: geliştirme0.983/2.349s, final0.980/1.886s.
Kurulu wheel120/100000: geliştirme1.022/2.298s, final1.013/1.733s.
Bunlar yalnız bu ortamın tekil ölçümleridir; genel performans/minimum donanım garantisi yok.

[720 ayarlar](phase21/source-settings-720.png), [1366 ayarlar](phase21/source-settings-1366.png),
[720 sonuç](phase21/source-result-720.png), [1366 sonuç](phase21/source-result-1366.png)
ve wheel karşılıkları gerçek grabWindow çıktılarıdır. Ajan720 ayar ve1366 sonuçları
fiilen görsel inceledi. İlk görsel kontrolde Canvas null/undefined NaN ekseni bulundu,
düzeltildi; yeniden render ve GUI denemesi geçti. Metin dar genişlikte sarılır,
geçmiş çizgisi gerçek ve lagged hareketli ortalamayı gösterir. Bunlar insan kullanıcı
ve gerçek Wayland masaüstü kabulü değildir.

İlk100000 reopen denemesinde tam ayrıntı JSON'u4MiB metadata decoder'a takıldı;
64MiB ayrı güvenli ayrıntı decoder'ı (duplicate/nonfinite JSON reddi) uygulanıp
aynı gerçek kaynak/wheel denemesi yeniden geçti. Başarısız ön denemeler nihai
başarı gibi değerlendirilmedi. Final veri fit'e katılmaz; aralık null kalır.

