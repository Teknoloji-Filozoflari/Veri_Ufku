# Veri_Ufku · Bilimsel rapor

Protokol: exploratory
Keşifsel inceleme; analiz birimi, seçim ve test kullanımını kayıtlı sonuçlarla değerlendirin.

Güncellik: Seçilen dataset/run için daha yeni kayıt bulunmadı; dış kaynağın canlı tazeliği doğrulanmadı.

Test kullanım defteri: []
Model seçim protokolü: kayıtlı method/model-card alanlarına bakın; alan yoksa not_recorded.

## Araştırma sorusu

**text**

```text
Soruyu ve analiz birimini kullanıcı olarak açıklayın.
```
**evidence**

```text
Kullanıcı metni; doğrulanmış hesap değildir.
```

## Yorum ve sınırlamalar

**text**

```text
Bulguyu yorumdan ayırın; nedensel çıkarım varsayımlarını açıkça yazın.
```
**evidence**

```text
Kullanıcı metni; doğrulanmış hesap değildir.
```

## Kaynakça

[Qt PDF](https://doc.qt.io/qt-6/qpdfwriter.html)

## Sözlük

**dataset_version**

```text
dv:80e262fd-4af3-4582-9e6f-ccdf6aef45d4
```
**data**

```text
{
  "columns": [
    {
      "id": "col:f2a434f1-432b-498c-8282-2b82eb6efbf3",
      "name": "değer",
      "original_name": "değer",
      "type": "Float64"
    }
  ],
  "semantic_metadata": {}
}
```

## Tablo

| isim | değer |
| --- | --- |
| Çağrı İıŞşÇçĞğÖöÜü | 1.0 |
| [redacted] | 2.0 |
**dataset_version**

```text
dv:80e262fd-4af3-4582-9e6f-ccdf6aef45d4
```
**caption**

```text
İlk iki satır.
```
**n**

```text
2
```
**total_n**

```text
3
```
**selection**

```text
İlk N immutable satır; rastgele veya tam veri değildir.
```
**csv_policy**

```text
Null boş hücre; spreadsheet formül öneklerine apostrof eklenir. Parquet null/type korur; maskeli kolon string olur.
```
[table-4.csv](table-4.csv)
[table-4.parquet](table-4.parquet)

## Sınırlamalar
Bulgular seçilen immutable kayıtların değerleridir; bu rapor analiz/modeli yeniden hesaplamaz.
Keşifsel/doğrulayıcı sınıfı kullanıcı beyanıdır; confirmatory seçmek tasarımın geçerliliğini kanıtlamaz.
Kullanıcı notu/yorum/varsayım manuel metindir; doğrulanmış sayısal bulgu veya nedensel etki diye etiketlenmez.
Eksik metrik, belirsizlik veya tanılama üretilmez; not_recorded olarak görünür.
Redaction desen ve açık ColumnId seçimine dayanır; anonimlik veya bütün serbest metindeki sırları bulma garantisi değildir.
Statik grafikte örnekleme/filtre/caption bağlamı korunur; kaynak değişimi eski raporu güncel kanıt yapmaz.
Markdown/HTML/PDF bağımsız dosyada attachment bağlantıları yalnız paketle aynı dizine açıldığında çalışır; ZIP taşınabilir tam teslimdir.
PDF yerel A4 Türkçe font kullanır; HTML/Markdown/PDF düzenleri birebir aynı değildir. DOCX/local LLM/remote service desteklenmiyor.
