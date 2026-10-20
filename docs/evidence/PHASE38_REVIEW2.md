# Faz38 devam incelemesi

2026-10-11, Europe/Istanbul; REV-38-02; kullanıcı isteğiyle yalnız Faz38.
[İlk inceleme](PHASE38_REVIEW.md) ve teslim kanıtları korunur.
Kilitli CPython3.13.15 `.venv`, offscreen/software Qt.

## Ek bulgular ve davranış

| Öncelik | Sorun | Son davranış |
|---|---|---|
| P1 | Integer koordinat `2**53+1` Point oluştururken `2**53` olarak yuvarlanıyordu. | Float64'e kayıpsız dönüşemeyen Integer/Decimal değer kontrollü reddedilir. Kullanıcı önce açık tür/ölçek dönüşümü yapmalıdır; kaynak bytes değişmez. |
| P2 | Moran Integer/Decimal ölçümleri `.astype(float)` ile sessizce yuvarlanıyordu; sayısal metin kolonu da kabul ediliyordu. | Ölçüm kolonunun fiziksel türü sayısal olmalı; Float64 dönüşümü hassasiyet kaybetmemeli. Binary-exact Decimal `0.125` ve temsil edilebilir büyük tamsayılar desteklenir. |
| P2 | Raster map X/Y yerine raster_col/raster_row veya value yerine raster_row seçildiğinde GeoTIFF metadata'sıyla yanlış veri çizilebiliyordu. | Captured `x/y/value` sütunları ColumnId üzerinden doğrulanır; farklı sütun/geometri seçiminde kontrollü ret. |
| P2 | Moran büyük ortak offset ile doğru temsil edilen küçük farkları merkezleme sırasında kaybediyordu. | Kuvvet-iki ölçeklemeden sonra ortak offset çıkarılır, ardından farklar merkezlenir. `[2**53,2**53+2,2**53+6]` için kapalı-form `I=-1/28`; önceki yanlış `I=0` sonucu önlenir. |

Sayısal sınırda Float64 overflow ham exception yerine kontrollü ProjectError
olur. `numeric_values` kaynak dönüşümü yapmaz; yalnız hesap sınırını doğrular.
Reprojection ve 2D geometri kapsamı ilk incelemedeki gibi korunur.
Yeni ret davranışında sessiz approximation veya kısmi yayın yok.

İlk altı regresyon vakası altı hata verdi;
[ilk JUnit](phase38/review2/before.xml).
Offset/overflow iki ek vakası da düzeltmeden önce başarısız oldu;
[sayısal ilk JUnit](phase38/review2/numeric-before.xml).
Test modülü artık toplam 16 vaka içerir; ilk incelemenin sekiz vakası korunur.

## Doğrulama

Son kaynakta **179 pytest**: geo/boundary, charts/composition/projects ve
20 gerçek offline GUI. Ayrıca **9 yerel TLS/online GUI**; toplam **188 pytest**,
sıfır failure/error/skip. Core/boundary 46 vaka; diğer uyumluluk 113 vaka.
14 belge unittest ayrıca geçti.

Yeni noneditable wheel ayrı `/tmp` hedefine kurulmuştur; kaynak ağacı ve
installed hesap dosyaları byte eşitliğiyle karşılaştırılır.
Kurulu paket hesap/GUI/ağ sonuçları ve gerçek komutlar
[özet](phase38/review2/summary.json) içindedir.
Kurulu wheel üzerinde **75 pytest**: 46 core/boundary, 20 offline GUI ve
9 yerel TLS/online GUI; sıfır failure/error/skip, 91.50 saniye.
Docs/artifacts/learning/usability, ilgili Ruff check/format kapıları geçmiştir.
Tam monolithic pytest yeniden çalıştırılmamıştır; önceki faz tesliminin
1075 tam regresyon sonucu güncel yeniden koşu olarak sunulmaz.

Faz39 kodu değiştirilmedi; yeni faz, stage, commit veya push yapılmadı.
Fiziksel masaüstü/insan/AT/minimum donanım/remote CI/temiz offline kurulum
bu incelemede doğrulanmadı. Resmî kabul ve önceki bağımlılık kapıları değişmez.
