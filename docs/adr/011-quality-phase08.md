# ADR-011 — Faz08 salt okunur kalite ve öneri sözleşmesi

2026-10-07. Python/PySide6/QML korunur; yeni bağımlılık veya proje şeması yok. Kapsam yalnız Faz08.

Tarama analytics/quality.py içinde Qt'sizdir. Mevcut analytics/worker spawn ve DatasetController binding/iptal/süreç bütçesi kullanılır. Worker ACTIVE veya kaynak yazmaz. Girdi snapshot hash/boyutu tarama öncesi ve sonrasında doğrulanır. Parquet4096 kayıt batch, SQLite8MiB cache/FILE temp; tekrar ve exact değer grupları disk üzerinde. Her bulguda ilk5 RowId/SourceRecordId örneği, metin256 ve örnek toplam1024 karakter; tam kayıt listesi UI'ye aktarılmaz. ComputeBudget süreç RAM/CPU/süre ve batch sınırında geçici disk bütçesi korunur; sampling sınırları önceki ADR ile aynıdır. Özel çalışma alanı iptal/hata/başarıda temizlenir.

Kapsam tüm dataset veya aktif AND filtreleridir. Sıralama/gizleme tarama kapsamını değiştirmez. Örnek ilkN özgün giriş kaydıdır (varsayılan10.000); filtre önce uygulanır. used_n/population_n/dataset_n ve full/filtered/sample ayrı kayıtlıdır. Örnek oranları örneğin içindedir; population tahmini değildir. Önceki tarama raporu kendisine ait parametreleri taşır; form değiştirmek otomatik tarama yapmaz. Proje kaydına ekleme açık eylemdir; sonuç snapshot/config/rol/yöntem/content7 bağlarıyla manifest4 içinde saklanır. Yeniden açılan aynı dataset sürümünün raporu gösterilir; yeni metadata sürümünde eski rapor güncel bağlanmaz.

Eksik null gözlemdir; boş metin/boşluk, NaN/sonsuz, benzer kategori ve IQR aykırı adaydır. Kesin ihlal yalnız kullanıcının açık gerekli/benzersiz/aralık/izinli değer/sonlu sayı/hedef türe dönüşüm/tarih kuralına göredir. Null gerekli kuralı dışında dönüşüm/aralık/tarih/izinli değer ihlali sayılmaz. Benzersizlik null'u dışlar; tekrar grupları null'u aynı anahtar sayar. Tam tekrar kullanıcı sütunlarını karşılaştırır, RowId/SourceRecordId karşılaştırmaya girmez. Grubun tüm üyeleri sayılır; silinecek fazlalık sayısı değildir. Meşru tekrarlı olaylar hata ilan edilmez. Sabit kolon non-null tek değer taşıyan kapsamı anlatır; tüm-null ayrı eksik bulgusudur.

Hedef tür int64/float64/boolean/date mevcut kayıpsız literal sözleşmesini kullanır; değer dönüştürülüp yazılmaz. Tarih ISO veya açık %Y-%m-%d/%d.%m.%Y/%d/%m/%Y; rastgele tarih tahmini yoktur. Karantinaya alınan source kayıtları aktif dataset dışında ayrı import_exclusions sayımıdır; tarama oranlarına katılmaz. Kaybedilmiş/karantinadaki özgün değerleri dataset içinden geri ürettiği iddia edilmez.

Kategori karşılaştırması yalnız önerilen/onaylı kategori/ordinal fiziksel metinde; NFC ve Türkçe I→ı, İ→i ile küçük harf/strip. İlk200 farklı etiket ve en fazla256 karakterlik etiket karşılaştırılır; limit aşımı uyarılıdır. Tam anahtar grupları kırpılmış UI metniyle kurulmaz. Aynı normalize etiket veya en az4 karakterde SequenceMatcher≥.85 yalnız adaydır. Otomatik birleştirme yoktur. Nested list/struct değer anahtarı fiziksel sıralı Python temsilidir; farklı sütun türleri birbirine eşitlenmez. Temponun/ns'nin cast metni hassasiyeti korur.

Aykırı aday yalnız measurement rolünde en az4 sonlu sayıda; Decimal80 aritmetik, linear h=(n−1)q ile Q1/Q3, 1.5×IQR sınırı. Bu bir hata testi değildir; kimlik/kategori değerlerinden aykırı ölçüm önerisi çıkarılmaz. [NIST Box Plot](https://www.itl.nist.gov/div898/handbook/eda/section3/boxplot.htm) sınır kuralını destekler; quantile/örnek minimumu bu uygulamanın açık yöntem seçimidir.

Öneri kimliği dataset sürümü/bulgu/parametrelerin SHA256'sından deterministik türetilir. Gerekçe, rol/fiziksel tür/amaç/miktar/kural bağlamı; önkoşul, etki, operation_id ve learning_id taşır. Kimlikte analiz birimi kontrolü, model amacında eğitim katında öğrenme/sızıntı, örnekte genellememe seçenekleri eklenir. Düzeltme işlemleri henüz yok: available=false, UI çalıştırma düğmesi üretmez. Faz09–11 başlatılmaz. Evrensel kalite puanı yok; örtüşen bulgu sayıları toplanmaz.

[Kanıt](../evidence/PHASE08.md).

Ortak domain/contracts.Provenance kullanılır; her gerçek koşuya UUID/tarih, dataset/source snapshot, config, parametre hash, ortam, filtre ve yardım sürümü bağlanır. Koşu kimliği/tarihi değişse de öneri kimliği ve bulgular deterministiktir.
