# ADR-015 — Faz12 grafik hesabı, QML adaptörü ve kayıt

2026-10-07; uygulanmış karar. Python/PySide6/QML korunur. Faz13 istatistiksel testler başlamaz. [ADR-002](002-matplotlib-qml.md) tasarımının gerçek adaptörü, [Faz12 kanıtı](../evidence/PHASE12.md).

## Hesap ve sunum sınırı

Qt'siz charts/contracts.py ChartSpec/v1; engine.py hesap ve RowId üyeliği; plot.py Matplotlib Agg FigureCanvasAgg render/koordinat/PNG/SVG adaptörüdür. worker.py spawn process hesabı, çizimi, üyelik sorgusunu ve export'u çalıştırır. UI charts.py yalnız tipli parametre/sürüm bağını ve QImage kopyasını aktarır; ChartPanel.qml gerçek MouseArea ve image provider içerir. QWidget/QtAgg toolbar QML item gibi gömülmez. Görseldeki yakınlaştırma hesabı/filtreyi değiştirmez; yeni çizim aynı referans tabloyu kullanır. Reset ilk çizim sınırlarını geri getirir. Bu fazda zoom/reset/seçim vardır; pan aracı eklenmedi.

ChartSpec başlık, eksen adları, birimler, legend, ColumnId, grup/agregasyon, bin/top-N/korelasyon/örnekleme yöntemleri, filtre/görünüm, null ve hassasiyet politikası ile açık kapsamı saklar. Sonuç veri sürümü, snapshot SHA256/boyut, kaynak snapshot, dataset/population/used sayıları, kesin profil, dışlama sayımları, referans noktalar ve render viewport/DPI/boyut taşır. Varsayılan başlık/eksen adları kayıtlı tür/kolon etiketiyle çözülür. PNG/SVG aynı figure'dan; sürüm/kapsam/filtre sayısı ve scatter örnekleme alt yazısı taşır. Tam filtre ifadesi ve null davranışı JSON/proje kaydında ve GUI'de görünür.

## Grafik anlamları

| Tür | Hesap ve seçim |
|---|---|
| Histogram | Kullanıcı1–200 eşit genişlikli bin seçer. Sol kapalı/sağ açık; son bin sağ kapalı. Sabit ölçüm ±0.5 açılır, temsil edilemeyen aralık ret. Bin seçimi bütün sonlu üyeleri kapsar. |
| Kutu | Linear h=(n−1)q yüzdelikleri; medyan/Q1/Q3;1.5IQR içindeki en uç gözlenen whisker. Her grupta ilk1000 aykırı işaret çizilir; tam sayı ve açık uyarı korunur. Grup seçimi bütün sonlu üyeleri kapsar. |
| Sütun | Kategori kaynak ilk görünümünde bağlanır; top-N tüm grup dallarının kayıt frekansına göre kararlı sıralanır. Kalanlar grup başına Diğer: kategori ve kayıt sayısı açık; sum/mean/median/min/max tüm kalan gerçek üyelerde yeniden hesaplanır. Literal Diğer veya null görsel adları kimlikleri birleştirmez. |
| Çizgi | Numeric/Date/Datetime X, grup sonra native X artan sıralı. Tekrar X açık count/sum/mean/median/min/max veya reject. X/null ve Y/nonfinite dışlanır. Native tarih/ns anahtarı ve timezone korunur; çizim gün koordinatı Float64 olduğundan çok yakın ns anları örtüşebilir. Naive tarih UTC yapılmaz. |
| Scatter | Açık systematic: sonlu giriş pozisyonları floor(jN/K), rastgele/temsili örnek iddiası yok; kullanılan/dışarıda kalan sayıları görünür. Full sınır aşımında ret. Grid: grup ve hücre başına ortalama koordinat; hücrenin bütün üyeleri seçilir. Hiçbir görünmez full→sample geçişi yok. |
| Korelasyon | Pearson normalize merkezlenmiş Float64 momentleri; Spearman çiftin ortak sonlu gözlemlerinde ortalama eşit sıralar. Her hücre ayrı n. n<2 veya sabit kolon coefficient=null + anlamlı hata; sıfır korelasyon diye sunulmaz. Çift üyeleri RowId ile saklanır. ≤10 alan hücre içinde r/n; tüm≤20 alanın≤400 çift sonucu metin tablosunda. |
| Eksik oranı | Yalnız null/used_n. NaN ve ±inf ayrı sayılır; boş metin null değildir. Seçim sütunun null kayıtlarıdır; null yoksa seçim0. |

Sonlu ölçümler yalnız sayısal fiziksel türdür; rol tür dönüşümü yapmaz. Kimlik/ignored/text rolü önerilmez; kimliği elle seçince uyarı vardır. Öneri tür+rol+amaç gerekçesidir, kullanıcı grafiği ve ikinci alanı seçer. Kesin özet ortak Faz07 profile motorunu kullanır (ddof1, linear yüzdelik); çizim Float64 projeksiyonudur. Int/Decimal dönüşüm ve agregasyon son değerinde kayıp default reject; açık approximate kayıp sayısını gösterir. Sum/mean/median Int/Decimal için Decimal precision80, float için yaklaşık math.fsum hesaplanır. Kaynak değişmez. Korelasyon büyük ortak Float64 offsetlerini Decimal fark/ölçek ile normalize eder; ±1e308 ve1e16 offset referans testleri taşma/iptal kaybını kontrol eder.

## Kapsam, kimlik ve bütçe

Full dataset veya mevcut filtreli tam alt küme; sample açık filtreli ilk-N (1–100000). Filtre/population lazy hesaplanır; yalnız seçili alanlar worker'da toplanır. Bu bir tüm-boyutlarda streaming grafik iddiası değildir: seçili alanlar için used×(160+40×alan) ve korelasyon için used×alan²×64 RAM önkontrolü; Linux CPU/AS, wall600s, iptal grace2s ve geçici disk ComputeBudget uygulanır. Önkontrol metin boyutunun tam peak garantisi değildir; sınır aşımı başarılı sonuç oluşturmaz. Grafik noktaları≤10000, grup≤top-N≤100, grid eksen2–80, correlation/missing≤20 alan. Aşan grup/çizgi/grid sessizce kesilmez; açık filtre/örneklem/limit düzeltmesi gerekir. Nested/Binary/Duration/Time grafiği desteklenmez; kaynakta korunur.

PointId grafik içinde yerel; kalıcı tablo eşleşmesi RowId'dir. Her nokta→gerçek RowId Parquet üyelik tablosunda, aggregate nokta tek kayıt diye gösterilmez. Nokta/tıklanabilir bar/kutu/hücre seçimi tam üyelik; dikdörtgen seçim görünür merkez koordinatlarını seçer. Noktada olmayan downsample kaydı tablo seçimiyle seçili kalır, sahte nokta üretilmez. Tablo→grafik bir kaydın temsil noktalarını vurgular, grubun diğer üyelerini seçmez. Gösterilen kimlik listesi ilk200; seçili sayısı tam, mevcut200 satırlık sayfa eşleşmesi ayrıca sorgulanır. Piksel haritası letterbox ölçeği ve Matplotlib axes dönüşümüyle eşleşir. Görsel tıklama/fare sürükleme ve programatik zoom/reset gerçek QML paket yolunda denendi.

## Kayıt ve koruma

Manifest7'nin mevcut results alanı chart nesnesiyle genişler; yeni manifest sürümü/migrasyon gerekmez. Beş artifact (data/members Parquet, PNG, SVG, tam JSON) hash ve schema/count denetimiyle staged; referans tablo=noktalar, n=üyelik sayısı, üyeler gerçek dataset RowId, nokta kimliği/üyeliği tekrarsız olmalı. ChartSpec ve bağlı dataset sürümü manifest açılışında doğrulanır. Aktif dataset/hash yayından önce tekrar kontrol; mevcut ProjectStore ACTIVE atomik transaction, read-only kilit, recovery/fsync ve eski commit koruması kullanılır. Save sırasında proje taslağı da kaydedilir. Eski veri/filtre/config sonucu güncel sonuç alanına taşınmaz; eski kayıt görüntülenebilir, güncel olmayan grafik save/export edilmez. Kayıtlı grafik açarken beş hash yeniden kontrol edilir.

PNG/SVG export ayrı süreçte hash doğrular, yeni/proje dışı hedef ve suffix ister. Mevcut dosya, kaynak, symlink veya proje artifact üstüne yazmaz. Anchored dir_fd, exclusive temp, fsync ve exclusive hardlink ile tek yayın; hata/iptal önceki dosyayı korur. Yayın tamamlanmışsa UI iptali çıktıyı yok saymaz. İki gerçek SIGKILL (kopya/pointer sonrası), iki yazıcı ve fault/tamper testleri mevcut sağlam ACTIVE veya tam yeni kaydı doğrular. Native SaveFile diyalog kullanıcı kabulü ayrı açıktır.

## Runtime ve erken Linux paketi

Exact Matplotlib3.11.2 uv.lock runtime'a eklendi; NumPy2.5.3, contourpy1.4.0, cycler0.12.1, fonttools4.66.1, kiwisolver1.5.1, Pillow12.3.0, pyparsing3.3.3, python-dateutil2.9.0.post0, six1.17.0 transitifleri gerçek CPython3.13 wheel'leriyle çözülür. Matplotlib DejaVu/STIX fontları yerel wheel içindedir; ağ font indirmesi yok. Worker MPLCONFIGDIR özel geçici alandır; kullanıcı config'i değiştirilmez. Kilitli runtime lisans metinleri/copyright ve bundled native/font bildirimleri [envanterde](../third_party/phase12/inventory.json); bu tam dağıtım uygunluk kabulü değildir.

scripts/measure_phase12.py source ve /tmp cwd'de kurulu noneditable Linux wheel'de aynı100k akışı denetler. Paket kökü assertion'ı kaynak modül fallback'ini reddeder; yedi hesap, QImage, gerçek Qt input→RowId, spawn PID, kaydet/aç, zoom/reset, her tür PNG/SVG, filtre/iptal ve100 input/render ölçümü birlikte koşar. Ubuntu CI'a gerçek wheel adımı eklendi; uzaktaki yeni koşu henüz yok. Faz27 AppImage/Flatpak temiz makine/offline kurulum kabulü yerine geçmez. Faz12'de yakalanan exact Qt requestImage dönüş biçimi ve empty-members lazy join Polars optimizer problemi düzeltilmiş ve kanıtta kayıtlıdır.

Resmî kaynaklar2026-10-07 incelemesi: [Matplotlib backend](https://matplotlib.org/stable/users/explain/figure/backends.html), [Matplotlib bxp](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.bxp.html), [Qt for Python QQuickImageProvider](https://doc.qt.io/qtforpython-6/PySide6/QtQuick/QQuickImageProvider.html), [Matplotlib paket metadata](https://pypi.org/pypi/matplotlib/json). Yerel exact sürüm davranışı ayrıca gerçek testle doğrulandı.
