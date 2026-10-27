# Faz38 yeniden inceleme

Sonraki kullanıcı talimatıyla yapılan [devam incelemesi REV-38-02](PHASE38_REVIEW2.md)
ayrı kayıttadır; bu belgedeki sayılar ilk incelemenin koşularına aittir.

2026-10-11, Europe/Istanbul; REV-38-01; kullanıcı isteğiyle mevcut Faz38
tesliminin kod ve regresyon incelemesi. Yeni faz başlatılmadı.
Kilitli `.venv` CPython3.13.15; offscreen/software Qt.

## Düzeltilen bulgular

| Öncelik | Önceki davranış | Düzeltme ve bağımsız kontrol |
|---|---|---|
| P1 | `POINT M (27 40 123)` kabul ediliyor; reprojection M değerini sessizce atıyordu. | İşlem ve doğrudan dönüşüm sınırında Z/M kontrollü ret; yalnız 2D xy. Kaynak import/metadata dönüşüm veya repair yapmaz. |
| P1 | Complex GeoTIFF `3+4j` Float64 tabloya `3` olarak aktarılıyordu. | Complex dtype decode öncesi kontrollü ret; metadata preview çalışır, kaynak bytes korunur. Complex64/128 gerçek GeoTIFF fixture. |
| P2 | EPSG4807 grad koordinatları derece sınırlarıyla karşılaştırılıyordu. | CRS axis angular unit faktörüyle yalnız doğrulama için derece ölçeğine geçilir; 99grad latitude kabul, 101grad ret, 190grad longitude kenarı geçerli. Koordinat değiştirilmez. |
| P2 | GeometryCollection içindeki bağımsız MultiPoint noktaları arasında hayali antimeridian kenarı oluşuyordu. | Koleksiyonlar recursive açılır; kontrol yalnız gerçek geometri/ring kenarlarında. Ayrı ±179° noktaları kabul, iç içe crossing LineString ret. |
| P2 | Moran I çok küçük sayılarda `NaN`, büyük sayılarda quadratic overflow üretiyordu. | Kuvvet-iki ölçekleme sonrası merkezleme; formül ve permutation sözleşmesi aynı. Üç düğümlü zincir, `[1,2,4]`, bağımsız `I=-1/28` referansı; `1e-200`, `1e200`, `1e307` ölçekleri. |

Yeni test modülü `tests/test_geo_boundaries.py` sekiz vaka içerir.
İlk yeni test koşusu altı hata gösterdi; iki büyük ölçek vakası daha sonra
sıfır olmayan kapalı-form referansa güçlendirildi. Başarısız ilk koşular
kabul sayılmaz; [ilk JUnit](phase38/review/boundaries-before.xml) korunur.

## Gerçek doğrulama

Kaynakta 38 core/boundary, 20 offline GUI, 9 yerel TLS/online GUI ve
127 chart/composition/project/document compatibility testi geçti.
Toplam **194 kaynak testi**, sıfır failure/error/skip.
Kurulu noneditable wheel üzerinde 38 core/boundary ve 20 GUI testi geçti;
toplam **58 wheel testi**, sıfır failure/error/skip.
GUI preview/apply/undo, dört offline map/export/help/save/reopen ve
beş gerçek reader testleri mevcut testlerden çalıştırıldı.
Komut, JUnit sonuçları ve düzeltme dosyası hashleri
[inceleme özeti](phase38/review/summary.json) içindedir.

Docs/artifacts/learning/usability ve ilgili Ruff check/format kontrolleri
geçti; 14 belge unittest ayrıca geçti. Tam monolithic pytest bu incelemede
yeniden çalıştırılmadı; önceki 1075 sonucunun yeniden üretildiği iddia edilmez.
Fiziksel masaüstü/insan/AT/remote CI/temiz offline kurulum iddiası yok.

## Eşzamanlı Faz39 çalışmasının etkisi

İlk kaynak GUI koşusu Faz39 `DashboardPanel.qml` içinde UiTextField'a
tanımsız `accessibleLabel` atanması yüzünden ana QML pencereyi yükleyemedi.
İlk TLS koşusu sandbox soket kısıtına takıldı; gerçek localhost TLS için
izinli çalıştırma yapıldı. İzinli ilk ağ koşusunda yedi hesap/ağ testi geçti,
iki GUI testi aynı QML hatasına takıldı.
Bu inceleme Faz39 dosyasını değiştirmedi. Aynı çalışma ağacındaki diğer
değişikliklerden sonra QML yükleme hatası kalktı ve kaynakta 20+9 vaka geçti.
[İlk kaynak koşusu](phase38/review/initial.xml),
[ilk izinli ağ koşusu](phase38/review/network-initial.xml) saklandı.
Aktif Faz39 dosyaları değiştiği için proje çapında değişmeyen HEAD iddiası
yapılmaz; yalnız bu düzeltmenin dosyaları kaynak/wheel byte eşitliğiyle
kontrol edilir. Stage/commit/push yapılmadı.
