# Faz19 — etiketsiz analiz teknik kabul kaydı

2026-10-09 Europe/Istanbul, ENV-19: Linux x86_64, kilitli CPython3.13.15,
PySide6/Qt6.11.2/scikit-learn1.9.1, offscreen/software, izole geçici XDG.
Yalnız açık Faz19 kapsamı; önceki insan/bağımlılık kabulü açık olduğu için faz
sürüyor, olgunluk deneysel. İnsan masaüstü, yeni uzak CI, minimum donanım,
ekran okuyucu ve bilgisiz kullanıcı kabulü bu oturumda yapılmadı.

<a id="e19-s001"></a>
## E19-S001 — iki ayrı yol

Model → amaç: Benzer kayıtları gruplamak / Sıra dışı kayıtları bulmak.
Başlangıç yol haritasının Kümeleme/Anomali eylemleri aynı gerçek formlara bağlı.
UnsupervisedPanel.qml, ui/unsupervised.py ve modeling/unsupervised.py;
[ADR-022](../adr/022-unsupervised-phase19.md). Gerçek dört QML/spawn yolu
[test kaydı](phase19/targeted-retry.txt); worker PID GUI'den farklı.

<a id="e19-s002"></a>
## E19-S002 — gerçek kümeleme ve kontrollü silhouette

KMeans/DBSCAN gerçek hesap, küme boyutu/profil ve RowId örnekleri. DBSCAN elle
iki üçlü grup+bir noise referansı; 0,1,2 /10,11,12 için silhouette bağımsız
elle a/b referansı (1−1.5/11,1−1/10,1−1.5/9 simetrisi). Tek küme, tüm noise,
singleton/iki kayıt, n küme ve 3000 üstü tam kapsam undefined; sayı uydurulmaz.
Seçili ölçümler/ölçek/eps/min_samples/k ve kategorik sınırlar görünür.
Boyut indirgeme görseli kullanılmadı; gerçek sınıf iddiası yok.

<a id="e19-s003"></a>
## E19-S003 — aday skorları ve veri koruma

IsolationForest ve tek sütun IQR ayrı. Skor > eşik, eşitlik işaretlenmez;
IF negatif score_samples, IQR kaynak biriminde sınır dışı uzaklık. Elle
[0,1,2,3,100] → Q1=1,Q3=3,IQR=2,sınırlar −2/6,100 skoru94. Sıfır IQR
[4,4,4,4,5] için yalnız5 aday. Etiket yok; precision/recall=null.
Dört yöntemin yeni dataset aktarımı aynı tüm satır/kolon/RowId ve kaynak byte
korumasını doğrular. Tek kaynak head'i korunur; iki aktif dataset vardır.

<a id="e19-s004"></a>
## E19-S004 — sürüm, kapsam ve yeni veri sınırı

Tam seçili veri sürümü fit; filtre yok, params/seed/scaler/backend/tarih/hash
kalıcı. Sonuç/üyelik kaydı ve reopen gerçek. DBSCAN doğal predict yok;
KMeans/IF/IQR native_support açıklanır, güvenli yeni dosya yolu bu fazda
sunulmaz. Eski ayar/veri sonucu güncel bağa yayımlanmaz; iptal eskisini korur.

<a id="e19-s005"></a>
## E19-S005 — yardım

Beş çevrimdışı konu: küme, uzaklık/ölçek, gürültü, anomali skoru ve etiketsiz
değerlendirme. Form düğmeleri ve capability bağları; gerçek LearningController
ile tüm beş context doğru makaleye açılır. Öğren ağacında iki ayrı alt grup.
Kritik gerçek sınıf/hata/precision-recall/silme sınırı her konuda görünür.

<a id="e19-s006"></a>
## E19-S006 — kabul kontrolleri

27 odaklı test [targeted-retry.txt](phase19/targeted-retry.txt) başarıyla geçti:
22 hesap/depo +5 gerçek GUI. Yalnız bu koşunun başarısı kabul kanıtıdır.
İlk çekirdek denemesi native import şemasına işaret kolonu eklenmesinde5 hata
buldu; derived_analysis kaynak+ek şema doğrulamasıyla düzeltildi. İlk GUI
denemesi inherited notify Signal bağında segfault; subclass'a özgü notify
sinyaliyle giderildi. Sonraki testin delegate araması QObject sahipliği yerine
Qt görsel ağacıyla yapıldı; önceki başarısız koşular başarı sayılmaz.

Nihai genel/paket kayıtları koşular tamamlandığında aşağıya eklenecektir.

## Tam kapsam ve kurulu paket kanıtı

[Kaynak](phase19/source-final.json)/[çıktı](phase19/source-final.txt),
[noneditable wheel](phase19/wheel.json)/[çıktı](phase19/wheel.txt): dört yöntem
240 kayıt; KMeans/IsolationForest/IQR100.000 ve DBSCAN3.000 olmak üzere sekiz
gerçek QML/spawn fit. Her koşuda işaretli yeni dataset, kaynak kolon/RowId
byte-değer eşitliği, kaynak dosya SHA256 eşitliği ve kaydet/yeniden açma.
DBSCAN tek izole gürültü; her iki tam kapsamdaki gerçek silhouette kaydı.
Silhouette3000 üzeri için gerekçeli unavailable; anomali aday sayıları gerçek.

Son odaklı kontrol [targeted-complete-final.txt](phase19/targeted-complete-final.txt):
**44 test /10.44s** (24 hesap/depo+5 gerçek GUI+15 yardım regresyonu).
Gerçek tek küme/tüm noise ve tam IQR sınır eşitliği; CSV leading-zero alanı,
işaretli kolonlar, var olan rename motoru ve yeniden açma da doğrulandı.
Önceki genel koşuda528 geçti/1 yardım sözlüğü sayısı başarısız oldu; beş yeni
konunun eklenmesi sonrası beklenti81→86 ve makale kimlikleri doğrulandı.
Başarısız genel koşu başarı değildir; nihai koşu aşağıda ayrı verilir.
Ölçüm betiğinin ilk çoklu-dataset koşusu seçili eski dataset'i ölçtüğünü
assert ile yakaladı; sonraki deneme açık dataset seçimi ve tablo işi bitişiyle
çalıştı. Büyük DBSCAN denemesindeki birçok komşu uzak kayıt gerçek üçüncü
küme oluşturdu; tek noise varsayımı yerine izole tek-kayıt fixture kullanıldı.
Bu başarısız ölçüm denemeleri son başarılı JSON yerine kabul sayılmaz.

Kaynak süreleri sırasıyla0.864/0.871/0.989/0.845/1.408/1.024/1.617/1.181s;
wheel0.829/0.852/0.944/0.828/1.336/1.003/1.499/1.180s. Kaynak tepe
parent+worker RSS932290560 byte/max tick145.302ms; wheel934359040/147.066ms.
Sıcak runtime/geliştirici makinesi ve eşzamanlı test yükü; minimum donanım,
soğuk açılış veya bütün performans hedeflerini karşılama kabulü değildir.

[Build](phase19/build.txt), [install](phase19/install.txt),
[wheel hash](phase19/wheel.sha256), [kaynak byte eşleşmesi](phase19/package-integrity.json),
[kurulu wheel giriş noktası](phase19/wheel-entry.txt). Wheel yolu /tmp altında,
`__file__` noneditable package-root assert'i var; temiz makine/offline kurulum
kabulü değildir. Yeni bağımlılık veya model pickle/joblib dosyası eklenmedi.

Görsel inceleme: [DBSCAN720](phase19/source-final-dbscan-720.png),
[IF1366](phase19/wheel-isolation_forest-1366.png) gerçekten görüntülendi.
Kritik sınıf/hata sınırı, ayrı skor/eşik, gerçek profil/örnek, kaydırılabilir
720px form ve kayıpsız aktarım görünür. Fiziksel masaüstü/insan kabulü değildir.

## Nihai kilitli doğrulama

[Nihai komut/exit/süre kaydı](phase19/checks-final.json): sistem+locked
check_docs, check_artifacts, check_learning, Ruff check/format ve kurulu giriş
noktası smoke exit0. **531 pytest /167.51s**
[çıktı](phase19/final-pytest.txt); **9 locked unittest /0.946s**
[çıktı](phase19/final-unittest.txt). **131 çevrimdışı makale/75 UI bağı**, beş
Faz19 konusu ve capability linkleri geçerli. Kilitli dev sync gerçekten çalıştı;
[ön kontrol kaydı](phase19/sync.txt).

Sistem Python3.14 keşfi **53 test /44 import errors /exit1**;
[sistem kaydı](phase19/final-system-unittest.txt). NumPy/Polars/PySide6/sklearn/dev
paketleri sistem Python'una kurulu değil; bu kontrol başarısızdır, kilitli
CPython3.13.15 test başarısıyla karıştırılmaz. Sistem Python'una paket yazılmadı.
Yeni insan masaüstü/uzak CI/minimum donanım kabulü yok; önceki F13/bağımlılık
kabulü açık. Faz19 teknik satırlar doğrulandı, faz sürüyor/deneysel/zorunlu.
Faz20+ başlatılmadı.
