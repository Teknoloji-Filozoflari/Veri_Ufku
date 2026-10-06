# Veri_Ufku — ortam ve resmî uyumluluk incelemesi

İnceleme tarihi 2026-10-06; ortam kimliği ENV-00. Kanıt [phase00 raporu](evidence/PHASE00.md). Gözlem ≠ paket desteği ≠ release kabulü.

| Alan | Gözlenen |
|---|---|
| OS/session | CachyOS rolling, Linux 7.2.9-1-cachyos, x86_64, Wayland; DISPLAY=:0 mevcut |
| CPU/RAM | Ryzen 7 8845HS, 8 core/16 thread, AVX2; 31,388 MiB RAM, 31,387 MiB swap |
| Disk | NVMe Btrfs, 667 GiB boş; /tmp 16 GiB tmpfs |
| Runtime | Python 3.14.7; glibc 2.44; SQLite 3.53.4 |
| Kurulu | PySide6/Qt 6.11.2, Matplotlib 3.11.2, NumPy 2.5.3, pytest 9.1.1, ruff 0.16.10; uv CLI 0.12.23 |
| Eksik | Polars, DuckDB, scikit-learn, SciPy, statsmodels; Python 3.13; Xvfb |
| Qt/font | Qt plugin path /usr/lib/qt6/plugins; Noto Sans system font |
| Depo | Sadece birleşik prompt vardı; AGENTS.md/kod yoktu. .git boş/salt okunur, git status başarısız; remote/commit yok. |

## Resmî kaynak kaydı

2026-10-06'da aşağıdaki sayfalar web aracıyla okundu. `stable` sayfaları değişebilir; sürüm etiketi paketin burada kurulduğunu veya uyumlu kilit çözüldüğünü göstermez. İncelenen doküman ile yerel runtime sürümü farklı olan yerler özellikle kayıtlıdır.

| Araç ve kaynak | Görülen destek bilgisi | Bu ortam kararı |
|---|---|---|
| [Qt for Python getting started](https://doc.qt.io/qtforpython-6/gettingstarted.html) | Python≥3.10, izole ortam önerisi; wheel Qt içerir | Yerel Qt 6.11.2 QML Controls offscreen load 1 root; sistem paketini lock sanma |
| [Qt Quick Controls](https://doc.qt.io/qt-6/qtquickcontrols-index.html) | Qt Quick kontrol seti; sayfa Qt 6.12 etiketiyle geldi | Exact 6.11.2 paket QML API/plugin testi Faz 01'de, resmî sayfa yeni sürüm olabilir |
| [Polars install](https://docs.pola.rs/user-guide/installation/) | CPU uyumluluğu/rtcompat, lazy/optional deps, varsayılan 2^32 row index sınırı | CPU AVX2 var; kurulu değil; exact Python wheel uyumu henüz doğrulanmadı |
| [DuckDB Python](https://duckdb.org/docs/current/clients/python/overview) | Python≥3.10, sayfa stable 1.5.6 bildiriyor | Kurulu değil; disk/SQL gerektiğinde; stable redirect ilk URL'de yalnız yönlendirme verdi, current okundu |
| [scikit-learn install](https://scikit-learn.org/stable/install.html) | İzole binary wheel önerisi, bağımlılık alt sınırları; doküman 1.9.1 | Kurulu değil; Python minimum tek başına 3.14 ABI uyumu kanıtlamaz |
| [SciPy toolchain](https://docs.scipy.org/doc/scipy/dev/toolchain.html) | Tablo 1.16 için Python≥3.11,<3.14, NumPy≥1.25.2,<2.6 | Yerel 3.14 ile bu satır uyumsuz; yeni 1.18 başlıklı sayfa tüm yeni sürüm destek tablosunu göstermedi. CPython3.13 başlangıç adayı; çözüm doğrulanmadı |
| [statsmodels install](https://www.statsmodels.org/stable/install.html) | Python≥3.9; NumPy/SciPy/Pandas/Patsy bağımlılıkları, doküman 0.15.0 | İhtiyaçta optional; kurulu değil; Pandas'ı genel tablo çekirdeği yapma gerekçesi yok |
| [Matplotlib backend](https://matplotlib.org/stable/users/explain/figure/backends.html), [Qt example](https://matplotlib.org/stable/gallery/user_interfaces/embedding_in_qt_sgskip.html) | Agg/render/export ve Qt bindings; QWidget örneği | Agg blank render çalıştı; QML bridge ADR-002; gerçek grafik/export etkileşimi yok |
| [QQuickImageProvider](https://doc.qt.io/qt-6/qquickimageprovider.html) | QImage async/thread/cache davranışı; doküman Qt6.12 | Sürümlü QImage aktarımı planı; exact API Faz 12 |

Lisans kaynakları/yükümlülükleri [ADR-004](adr/004-offline-licensing-packaging.md). Çekirdeğin tümüyle Python3.14 destekli olduğu iddia edilmez. Sürümler tahminle requirements'a yazılmadı. Faz 01 exact patch+ABI/wheel+transitif solver+import smoke+uv.lock ile karar kapanır. Faz 00 görevimiz bu çözümün planını hazırlamaktır; uygulama iskeleti veya kurulum yapılmadı.

## Gerçek denemeler ve sınırlar

`QT_QPA_PLATFORM=offscreen` altında geçici ApplicationWindow+Button QML 1 root üretti; yaklaşık 37 ms tek probe süresi uygulama açılış benchmark'ı değildir. Qt6.11.2 runtime; Agg 100×100 RGBA buffer=40,000 byte. Matplotlib sistem config path'i yazılamadı ve /tmp fallback uyarısı çıktı; yeniden üretilebilir probe `MPLCONFIGDIR` writable temp kullanır. Ürün XDG cache seçimini Faz 01'de uygular.

Masaüstü kullanıcı testi, X11, HiDPI, hedef 8GB donanım, analitik import veya paket smoke yapılmadı. Terminal ağ DNS erişimi başarısız; resmî belgeler web aracıyla erişilebilir. Gerçek registry çözümü yapılmadı. Ağ/izin belirsizliğini kurulmuş/locked saymayacağız.

## ENV-01 — 2026-10-06 Faz 01

CachyOS x86_64 Linux 7.2.9, Ryzen 7 8845HS, 32GB, Btrfs; /tmp tmpfs. CPython 3.13.15 uv-managed kurulum bu fazda bulundu; ENV-00 bulgusu tarihseldir. Sistem Python 3.14.7 değiştirilmedi. İzole .venv PySide6 6.11.2, pytest 9.1.1, Ruff 0.16.10, uv 0.12.23. Lock gerçek offline resolver ile üretildi. İkinci temiz venv ve noneditable wheel headless smoke çalıştı. Terminal registry DNS erişemedi; önceden mevcut cache kullanıldı.

Qt offscreen/software ekran ve worker testi geçti. Wayland wl_display Operation not permitted ile, X11 display :0 bağlantı hatası ile açılmadı (exit134); gerçek desktop doğrulanmadı. Ubuntu CI hedefi burada çalıştırılmadı; remote yok. [Faz 01 kanıtı](evidence/PHASE01.md), [ADR](adr/005-runtime-jobs-lock.md).

## ENV-USER-01 — 2026-10-06 kullanıcı masaüstü bildirimi

Kullanıcı yerel uygulamada CPU, I/O ve belirsiz ilerleme iptal/tamamlanma denemelerini bildirdi. Masaüstü backend, tam çalıştırma komutu, Python/Qt/binary hash ayrıca bildirilmedi; ENV-01 ile birebir ortam eşitliği varsayılmaz. Bu kanıt bildirilen eylemlerle sınırlı manuel kullanıcı kontrolüdür; performans veya bağımsız ajan masaüstü testi değildir. [Kanıt](evidence/PHASE01.md#e01-user-desktop).

ENV-USER-01 devam bildirimi: kullanıcı görev sırasında yapılandırma/eski sonuç, anlaşılır hata/takip kimliği ve aktif görevde kapanış için verilen üç kontrolün hepsinin çalıştığını bildirdi. Bu senaryolar manuel kabul kaydına eklendi; runtime/backend/hash belirsizliği korunur.
