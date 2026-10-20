# ADR-026 — Faz23 declarative yeniden uygulama ve izleme

2026-10-09. Kullanıcı açık Faz23 yetkisi; Python/PySide6/QML korunur.

AnalysisRecipe/v1 JSON en fazla2MiB,100 adım,100 kaynak; exact şema/yöntem
sürümü ve kapalı OperationSpec allowlist. Kaynak schema/ColumnId/rol/birim/
ordinal sıra ve fingerprint, orijinal input/output sürümleri ve seed taşınır.
Kod/modül/shell/model yükleme yok. computed mevcut bounded AST yorumlayıcısıyla
çalışır; yalnız col() referansları AST üzerinden eşlenir, literal metin değişmez.
Yeni alan kimlikleri ve sonraki adımlar eşlenir; join/append ikinci kaynak açık
seçilir. Fit edilmiş model ve analiz tarifi ayrı dosya/sözleşmedir.

Dry-run bütün adımları disposable CPU süreçte geçici Parquet üzerinde hesaplar;
her adım succeeded/failed/blocked ve tam etki/hata taşır. Giriş doğrulaması
eksik/tür/rol/birim/sıra/tekrar eşlemeyi reddeder. Tablo görünüm filtreleri
uygulanmaz. Yeniden hesaplanan mean/median/pivot genel dataset işlemidir;
training-only learned model preprocessing yerine kullanılamaz. Sonuç değerleri
aynı veri/seed/parametreyle aynıdır; yeni execution/operation/version kimlikleri
ve yeni satır köken UUID'leri ayrı çalıştırmada yenidir.

Bütün adımlar tek ACTIVE commit ile publish edilir. publish_operation internal
_defer yolunda aynı snapshot/kimlik/lineage/hash denetimlerini yapar, pending
ara çıktıları kullanır; yalnız tamamlanmış batch sonunda save. Adım/copy/save
hatası eski state/pending'i geri getirir; ACTIVE sonrası hata gerçek yayımlanmış
commit'e reconcile edilir. Preview bağında proje commit, aktif sürüm ve config
revision vardır. Readonly/eski/hatalı/iptal edilmiş sonuç publish edilemez.
RecipeReplay/v1 origin/step/hash/mapping/seed işlem kaydında kalır. Tarifi
uygulamak aktif kaynak sürümlerini ister; geçmiş snapshot'a dry-run mümkündür,
publish eski head'i sessiz değiştirmez.

DatasetChange/v1 tam immutable snapshot ≤100000 kayıt; null oranı, kategori
ilk30+diğer/farklı sayısı, sayısal finite/nonfinite/min/mean/q25/median/q75/max,
şema/isim/rol farkı. Betimsel yöntem, test/p/eşik yok. Örneklem büyüklüğü ve
toplama koşulu etkisi açık; dağılım değişimi model başarısızlığı değildir.
Nested/binary/tarih için null/şema görünür, dağılım özeti desteklenmedi etiketi.

Modeli uygula Faz20 fitted güvenli pipeline transform/predict; fit çağırmaz.
Yeniden eğit aktif veri için hazırlık/split formunu açar, yeni eğitim ayrı
kullanıcı eylemi; eski paket/fit üyeliği/veri sürümü korunur. Desteklenmeyen
metin/DBSCAN paketinde eski kapalı sınır korunur. DelayedPerformance/v1 son
üretilmiş hash kontrollü tahmin dosyası ve kullanıcı seçtiği hedef snapshot'ı,
aynı türde benzersiz/non-null iş anahtarı veya korunmuş RowId ile inner join.
Unmatched ve invalid ayrı; regression MAE/RMSE, classification accuracy;
hedefsiz/ölçülebilir eşsiz durumda metrics=null. Decimal veya büyük integer
hassasiyet kaybında ret. Bu yeni keşifsel performans final test değildir.
Training/model run/prediction/target versions+fingerprints+mappings korunur;
rapor yeni JSON dosyasına üzerine yazmadan aktarılır. İçe aktarma yeni RowId
üretir; ayrı hedef dosyası için ortak iş kimliği gerekir.

Hazırla ekranındaki RecipePanel üç aşamalı eşleme/dry-run/apply, isteğe bağlı
izleme/performance; Model ekranında ayrı apply/retrain eylemleri. Çevrimdışı
üç yardım ve mevcut capability registry, bütçe/iptal/proje yayın yolu kullanılır.
İnsan masaüstü ve minimum donanım kabulü başsız kontrolden çıkarılmaz.
