# Verinin Temizlenmesi - Ön İşleme

Elimizdeki veri setini anlamaya ve keşfetmeye yönelik bir takım işlemler yapmadan önce, veri setindeki verilerin çoğunlukla düzenlenmesi, bir takım ön işlemlerin yapılması gerekir. Bu işlemler şemada gösterildiği gibi:
- Temizleme
- Birleştirme
- Dönüştürme
- İndirgeme
başlıkları altında incelenebilir.

![[veri_temizleme.png]]

## Verilerin temizlenmesi
Eksik verilerin tamamlanması, “göze batan”, hatalı, “anlamsız” verilerin düzgünleştirilmesi, tutarsızlıkların giderilmesi gibi işlemleri kapsar.

1. Eksik veri: Eksik veriler, veri içinde eksik olan değerlerdir. Eksik veriler, silinir veya doldurulur.
2. Hatalı veri: Hatalı veriler, veri içinde yanlış olan değerlerdir. Hatalı veriler, düzeltilir veya silinir.
3. Üst sınır veya alt sınır değerleri: Üst sınır veya alt sınır değerleri, veri içinde anormal değerlerdir. Üst sınır veya alt sınır değerleri, silinir veya düzeltilir.
4. Outlier: Outlier, veri içinde anormal değerlerdir. Outlier, silinir veya düzeltilir.

![[outlier.png]]

5. Duplicate: Duplicate, veri içinde yinelenen değerlerdir. Duplicate, silinir.
6. Sütun veya satır silme: Sütun veya satır silme, veri içinde gereksiz olan sütun veya satırların silinmesini içerir.
7. Veri türü dönüştürme: Veri türü dönüştürme, veri içinde yanlış olan veri türlerinin düzeltilmesini içerir.
8. Kategorik veri dönüştürme: Kategorik veri dönüştürme, veri içinde kategorik değerlerin düzeltilmesini içerir.

## Verilerin Birleştirilmesi
Farklı kaynaklardan gelen ilişkili verilerin birleştirilmesi işlemini ifade eder. Birleştirilmiş veriler daha zengin yeni bir kaynağı oluşturur. Bu yöntem için çeşitli teknikler uygulanır. Bu veri setlerindeki bazı alanlar ortak, ancak bir veri setinde olan alanlar diğerinde yok. Bu iki veri setini birleştirip, yeni bir veri seti oluşturma işlemi veri birleştirmedir. Veri tabaları üzerinde JOIN işlemleri buna bir örnektir.

## Veri Dönüşümü
- Veri Düzeltme
  - Bölmeleme
  - Kümeleme
  - Eğri Uydurma
- Biriktirme
- Genelleme
- Normalizasyon
  - min-max normalizasyon
  - z-score normalizasyon
  - ondalık normalizasyon
- Nitelik Oluşturma

Min-max normalleştirmesi ile orijinal veriler yeni veri aralığına doğrusal dönüşüm ile dönüştürülürler. Bu veri aralığı genellikle 0-1 aralığıdır.

Z Skor normalleştirmede (veya0 ortalama normalleştirme) değişkenin herhangi bir değeri, değişkenin ortalaması ve standart sapmasına bağlı olarak bilinen Z dönüşümü ile normalleştirilir.

Ondalık ölçekleme ile normalleştirmede ele alınan değişkenin değerlerinin ondalık kısmı hareket ettirilerek normalleştirme gerçekleştirilir. Hareket edecek ondalık nokta sayısı değişkenin maksimum mutlak değerine bağlıdır. Örneğin900 maksimum değer ise, n=3 olacağından900 sayısı0,9 olarak normalleştirilir.

![[normalizasyon.PNG]]
