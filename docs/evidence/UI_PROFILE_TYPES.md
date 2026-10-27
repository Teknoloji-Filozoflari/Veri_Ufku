# Profil düzeni ve tam sayı düzeltmesi

2026-10-10 Europe/Istanbul; ENV-UI-PROFILE-TYPES; UPT-01/02 matriste.
Açık kullanıcı UI düzeltmesi, yeni faz yok. Önceki iki sütunlu görünüm beş
sütuna döndü: Sütun, Veri türü, Dolu, Null, NaN. Üç üst özet ve otomatik
tam hesap korunur. Tarihsel UI_DATA_REFINEMENT kanıtı önceki görünümündür.

Son kullanılan projenin manifesti salt okunur incelendi: sayısal sütunlar
eski aktarımda text olarak kaydedilmiş. Kaynak veya kayıtlı snapshot
değiştirilmedi. Profil String sütunlarda tüm kapsamı4096 kayıtlık
streaming parçalarla tarar; content_type ve physical_type ayrıdır.
Int64 (kayıt: String) açık ayrımı fiziksel veri dönüşümü iddiası değildir.
Dolu/null/NaN kayıtlı değerleri sayar, boş metin null yapılmaz.
Describe ve analitik fiziksel tür/semantik role bağlı kalır.

Yeni CSV otomatik algılamada başlık id/code diye veya15 rakamı aştı diye
metin veto kaldırıldı. Tam Int64 min/max kesin saklanır; leading-zero ve
karma değerler metindir. Decimal hassasiyet ve kaynak byte koruması sürer.

Gerçek komut sonuçları [checks.json](ui-profile-types/checks.json) ve
çıktılardadır. Headless yazılım Qt testi fiziksel masaüstü/insan kabulü değildir.

İlk hedefli denemede collect_batches nesnesinde olmayan stop çağrısı
başarısız oldu (59 geçti/5 kaldı); çağrı kaldırıldı. Sonraki
[hedefli kontrol](ui-profile-types/targeted.txt):66 test başarılı,22.78s.
Daha sonra eklenen legacy gerçek GUI testi tam regresyona dahildir.
[Eski proje şeması](ui-profile-types/existing-schema.json):418 kaydın
tamamında PassengerId/Pclass/SibSp/Parch Int64 içerik, Age/Fare kesin
Decimal içerik; snapshot SHA256 önce/sonra eşit. Satır değerleri kanıta
kopyalanmadı. Profil için yeniden aktarım gerekmez; sayısal analitik hâlâ
kayıtlı fiziksel şemayı kullanır.

[Qt ekranları](ui-profile-types/screens/walkthrough.json) sentetik fixture;
geniş beş sütun görüntüsü gerçekten incelendi. Dolu/null/NaN ve fiziksel
türler görünür. Dar/%200 yatay kaydırma korunur. Kurulu giriş noktası
[smoke](ui-profile-types/smoke.json) GUI_SMOKE PASS, izole XDG.
Ruff/format/artifacts/learning/usability başarılı. check_docs ve
unittest8/9 önceden değiştirilmiş birleşik kaynak dosyanın tarihi hash
uyuşmazlığı yüzünden başarısız; kaynak/checksum değiştirilmedi.

Son format seçimi düzeltmesi: GUI CSV/TSV formatı elle seçildiğinde de
infer_types=true korunur; programatik ImportSettings varsayılanı değişmez.
Bu ekten sonra [17 GUI kontrolü](ui-profile-types/final-gui.txt) geçti
(18.19s). Legacy gerçek GUI testi ayrıca [başarılı](ui-profile-types/legacy-gui.txt)
(1.29s). Öğren içerik sürümü39;151 makale/90 binding.

Nihai [tam regresyon](ui-profile-types/pytest.txt):711 geçti/1 başarısız,
233.59s. Tek hata DocumentContracts kaynak/hash uyuşmazlığı; uygulama,
aktarım ve legacy GUI testleri geçti. [JUnit](ui-profile-types/pytest.xml).
Tam koşu format seçimi ekinden önce toplandı; ekten sonra17 ilgili GUI
testi ayrıca başarılıdır. Nihai belge sonrası kapılar checks.json içindedir;
belge dışında artifacts/learning/usability/Ruff/format başarılıdır.
Yeni faz, kayıtlı veri dönüşümü veya kullanıcı masaüstü kabulü yapılmadı.
