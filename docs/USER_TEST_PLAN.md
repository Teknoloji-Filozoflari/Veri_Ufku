# Faz25 — gerçek kullanıcı testi planı

Plan tarihi: 2026-10-09 Europe/Istanbul. **Henüz katılımcı testi yapılmadı.**
QTest, ajan/geliştirici walkthrough'u ve Qt erişilebilirlik arayüzü sorgusu bu
planın uygulanması değildir. Ürün doğrulama açığı F25-S007'de açık tutulur.

En az beş yeni başlayan (veri bilimi/kod deneyimi olmayan) ve beş uzman için
ayrı oturum planlanır. Bu küçük örnek keşif amaçlıdır; nüfus başarı oranı veya
istatistiksel genelleme üretmez. Klavye ve ekran okuyucu kullanan katılımcılar
ayrı erişilebilirlik oturumuna davet edilir; yalnız simüle edilmiş renk görme
bozukluğu gerçek katılımcı deneyimi yerine geçmez. Katılım ve kayıt izni açıkça
alınır; gerçek kişisel veri yerine paketli/sentetik dosyalar kullanılır.

| Görev | Yeni başlayan için yönlendirmesiz amaç | Uzman için ek amaç | Başarı kanıtı |
|---|---|---|---|
| U25-01 | Proje oluştur; satış dosyasını aç, bir sütunun eksik oranını bul | Başlık/ondalık/null ayarını doğrula, tam/örnek profil farkını anlat | Doğru kaynak ve veri sürümü; beklenen sayım; kapsamın doğru açıklanması |
| U25-02 | Eksik ölçümleri seçtiğin sabitle doldur, sonra geri al | Önizleme etkisini ve eğitim sızıntısı riskini açıkla | Değişen hücre sayısı; geri alınmış değer/RowId; kaynak aynı |
| U25-03 | Dağılım grafiği oluştur ve raporu yeni dosyaya kaydet | Filtre/örneklem ve eski bulgu sürümlerini ayırt et | Açılabilir grafik/rapor; kapsam doğru; eski dosya ezilmemiş |
| U25-04 | İki şubenin ortalama ölçümlerini karşılaştır | Birim/bağımsızlık/hipotez ve Welch varsayımlarını açıkla | Geçerli önkontrol; p/etki/belirsizliği ayrı yorumlama; nedensellik iddiası yok |
| U25-05 | Mevcut modelle yeni dosyaya tahmin al | Alan eşlemesini ve uygulama/yeniden eğitim farkını göster | Satır kimlikleri korunmuş çıktı; yeniden fit yok; hedef yokken başarı metriği yok |

Her katılımcı için görev başlangıç/bitiş zamanı, kullandığı sürüm, donanım,
masaüstü/ölçek/font/dil, tamamlandı/kısmen/başarısız sonucu, bağımsız tamamlandı
veya yardım aldı ayrımı kaydedilir. Yardım paneli açma sayısı, aranan konu,
hangi metnin işe yaradığı, moderatör müdahalesi ve müdahale zamanı tutulur.
Yardım okumak başarısızlık değildir. Katılımcıya “doğru düğme” söylenmeden önce
sorun ve kendi beklentisi sorulur. Süre keşifsel kaydedilir; bu çalışmada keyfî
süre eşiği geçme/kalma ölçütü değildir. Görev sırası ve öğrenme etkisi kayıtlıdır.

Kritik hata kaydı: kayıt kimliği/görev/sürüm, beklenen ve gerçek davranış,
tekrar adımları, veri/çıktı etkisi, kurtarma ve yardım alma. Kaynak ezilmesi,
yanlış sürümün güncel görünmesi, sessiz yeniden eğitim, hedef olmadan başarı
metriği ve varsayımı geçersiz bilimsel kesinlik kritik sayılır. Bu durumda
ilgili görev durdurulur, güvenli kopya korunur; ilgili sürüme dağıtım adayı
kabulü verilmez. Okundu işareti katılımcı notu, sınav veya beceri puanı değildir.

Oturum kayıt şablonu: `participant_alias`, `cohort`, `consent`, `environment`,
`task_id`, `started_at`, `ended_at`, `outcome`, `independent_completion`,
`help_openings`, `moderator_assistance`, `critical_errors`, `interpretation`,
`artifact_refs`, `followup_findings`. Katılımcı kimlikleri projeye veya ürün
telemetrisine yazılmaz. Gerçek test sonuçları ayrı tarihli kanıt dosyasında
raporlanır; bu plan dosyasına uydurma katılımcı veya başarı sayısı eklenmez.

Ekran okuyucu oturumu: Linux AT-SPI/Orca sürümü, masaüstü, Qt platform eklentisi,
Tab/ShiftTab, duyurulan ad/rol/durum/değer, tablo satır/sütun gezinmesi, modal
odak sınırı, hata ve ilerleme duyurusu, yardımın açılıp kapanması ölçülür.
Qt QAccessible adlarının varlığı AT-SPI aktarımını veya Orca konuşmasını
kanıtlamaz. Bu oturum henüz çalıştırılmadı.
