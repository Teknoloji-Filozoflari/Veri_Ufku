# Faz25 — kullanılabilirlik, erişilebilirlik ve öğrenme denetimi

Tarih: 2026-10-09 UTC / 2026-10-10 Europe/Istanbul. ENV-25 ve ENV-25-WHEEL.
Kullanıcının kalan işe devam talimatı ile mevcut Faz25 çalışması tamamlanır.
Faz sürüyor/deneysel/zorunlu; gerçek insan/AT ve önceki bağımlılık kabulü açık.
Faz26 başlatılmadı. [ADR-028](../adr/028-usability-phase25.md).

<a id="e25-s001"></a>
## E25-S001 — bulgular ve uygulanan düzeltmeler

Gerçek QML'de ortak form amaç adları, Tab görünürlüğü, textarea'dan çıkış,
dinamik import tür seçicisinde odak koruma ve boş tablo Tab tuzağı düzeltildi.
%200 yazıda uzun sol menü başlığı kesilmeden satıra kayar.
`tests/test_usability.py` bu davranışlar, bağımsız parse tercihleri, temel
İngilizce, yardım retleri ve iki tema kontrastı için regresyon kapısıdır.

İlk yüksek DPI denemesi boş `HorizontalHeaderView` üzerinde Tab'ın kaldığını
gösterdi. Önce animasyon beklemesi denendi; hatayı çözmedi. Asıl düzeltme
başlığı Tab sırasından çıkarıp tablo çıkışını korumaktır. İlk başarısız kayıt
[dpi-initial-failure.log](phase25/dpi-initial-failure.log) korunur.
Genel Ruff format kapısında iki dosya düzeltildi.
Tam koşunun ilk denemesinde 215 hata/421 başarı kaydedildi
([korunan log](phase25/pytest-initial-failure.log)); sonuç çıktıktan sonra Qt
kapanışında kalan süreç SIGTERM ile sonlandırıldı (exit143). Eski yardım metni
beklentisi güncellendi. Görünüm değişiminde gereksiz `engine.retranslate()`
kaldırıldı: yalnız gerçek dil değişimi çeviri yeniler. Kapanışta sinyal
bağlantısı, çeviriciler ve QML engine bırakılır; bir sonraki shell öncesinde
Qt ertelenmiş silmeleri tamamlar. Bu, eski modal odak ve biriken RAM’in sonraki
kontrolleri bozmasını hedefler; kaynak bütçesi artırılmadı.
İlk doğrudan engine silme denemesi tam koşuda exit139 ile çöktü
([korunan log](phase25/pytest-engine-disposal-failure.log)); engine silmesi
pencerenin destroyed sinyalinden sonra yapılacak şekilde sıralandı. Kaynak bırakma ve
pencerenin dil değişiminde açık kalması regresyonla denetlenir.

<a id="e25-s002"></a>
## E25-S002 — teknik erişilebilirlik ve kalan AT kabulü

Gerçek Qt QAccessible ad/rol sorguları sekiz alanı tarar. Otomatik statik
kapı 251 ortak form örneğinin amaç adını kontrol eder; bütün AT davranışını
doğrulamaz. Beş temel senaryo gerçek Tab/Space/ok/paste ve Ctrl+1–8 ile yürür.
Veri sekmeleri de gerçek Tab/Space ile seçilir; yalnız ilk odak, XDG ve
başlangıç klasörü fixture'dır. Modal yardım çıkışı ve gelişmiş görünümde
makale/panel korunması denetlenir.

720×560 mantıksal pencere, %200 yazı, koyu/açık tema render ve odak denemesi;
`QT_SCALE_FACTOR=2` ayrı başsız DPI denemesidir. Fiziksel ekran kabulü değildir.
[DPI JSON](phase25/dpi.json), [koyu](phase25/dpi-dark-200-small.png),
[açık](phase25/dpi-light-200-small.png). Ölçeklenmiş görüntü 1440×1120 pikseldir.
Kontrast testi ortak metin/alan/uyarı/hata/ana eylem ve renkli basılı eylem
çiftlerinde en az 4.5 oranını bağımsız luminance hesabıyla denetler;
bütün piksel durumlarının kontrastı denetlendi iddiası yoktur.

Grafik grupları renk yanında bar taraması, çizgi işareti/deseni ve scatter
işareti taşır; BrBG korelasyon haritasının küçük matrislerinde sayısal değer
vardır. Renk körlüğü katılımcısı/simülasyonu ve Orca/AT-SPI oturumu çalıştırılmadı.
F25-S002 bu açıklar nedeniyle doğrulanmadı kalır.

<a id="e25-s003"></a>
## E25-S003 — yardım kapsamı ve metin incelemesi

[Yapısal denetim](phase25/help-audit.json): 147 makale; sade özet, örnek,
uygun/uygunsuz durum, yorum ve bağ kayıtları. `check_learning` bağları ve
negatif broken-id testi ayrıca gerçek kapılardır. Katalog34, kalıcı kimlikler
korunmuş; değişen makalelerin sürümleri artırılmıştır. Önceki 68 jargon/
kesinlik adayı özet/kritik/yorum üzerinden okundu. “Kesin değildir” ve
“garanti vermez” bilimsel sınırlama açıklamalarıdır; bunlar yanlış kesinlik
diye otomatik silinmez. İçerik fingerprint, ddof/scope, exact tablo hesabı,
fold/fit/vocab kritik açıklamaları sadeleştirildi. İleri formüller ve teknik
ayrıntılar korunur; tüm makalelerin insan okunabilirlik kabulü yapılmadı.
Gerçek beş yol, örnek, varsayım, kapsam ve belirsizlikle birlikte incelendi.

<a id="e25-s004"></a>
## E25-S004 — dil, görünüm ve isteğe bağlı rehber

186 tamamlanmış temel İngilizce mesaj; Türkçe varsayılan. Sayı/tarih dosya
okuma ayarları arayüz dili/tema/yazı değişiminde aynı kalır; gerçek QML testi
Ctrl+, ve klavye seçimini çalıştırır. Kayıt atomik ve ayrı şema4 dosyasındadır.
Tam İngilizce yardım/analiz çevirisi yok; sınır diyalogda açıkça yazılıdır.
Rehber yeniden açılır, adımlar atlanabilir ve kapanır. Okundu beceri/not değildir.
Dar/büyük-font teknik render geçti; bütün ekran/font/dil kombinasyonlarının
manuel görsel kabulü ve gerçek başlangıç kullanıcısı açık kalır.

<a id="e25-s005"></a>
## E25-S005 — beş gerçek klavye walkthrough'u

[Kaynak JSON](phase25/walkthrough.json), [kurulu wheel](phase25/wheel.json).
W25-01 proje/CSV önizleme/import/tam profil; W25-02 eksik sabit doldurma/
önizleme/uygula/geri al ve önceki sürüm; W25-03 histogram/HTML rapor;
W25-04 açık soru/birim/gözlem/varsayımla Welch t;
W25-05 hazırlık/baseline development/dondurulmuş model/yeni CSV/no-fit tahmin.
Sentetik kaynak SHA256 korunur; yeni veride `fit_calls=0`, hedef olmadan başarı
metriği üretilmez. Başarılı source yürüyüşü 62 gerçek kayıtlı klavye eylemidir.
Nav/fokus Tab taramaları ve ilk odak ayrıca betikte görünür; 62 bütün Tab
basışlarının toplamı değildir. Gerçek kullanıcı testi yapılmadı.

<a id="e25-s006"></a>
## E25-S006 — kapılar ve sınırlar

[Gerçek komut/exit/date kayıtları](phase25/checks.json),
[paket komutları](phase25/package-checks.json),
[kaynak/wheel hash eşitliği](phase25/wheel-hashes.json).
CI'a kalıcı yardım/çeviri/erişilebilirlik kapısı ve kurulu wheel klavye
walkthrough'u eklendi; yeni uzak CI koşusu çalıştırılmadı.
Yardım linklerinin teknik kapsamı ve beş klavye yolu doğrulanır;
AT, insan kullanılabilirliği, tüm font/dil kombinasyonları kabulü açık olduğu
için F25-S001/S002/S004/S006/S007 tamamlandı diye işaretlenmez.

<a id="e25-s007"></a>
## E25-S007 — insan testi planı / açık ürün doğrulaması

[USER_TEST_PLAN](../USER_TEST_PLAN.md): yeni başlayan ve uzman görevleri,
bağımsız/yardımlı başarı, yardım açılması/moderatör müdahalesi, kritik hata,
ortam/sürüm/artifact ve AT-SPI/Orca ad/rol/durum/değer oturumu kayıt şablonu.
Henüz katılımcı oturumu yoktur; plan sonuç kabulü değildir.

## Nihai gerçek sonuçlar

637 pytest /226.37s ([log](phase25/pytest-final.log)),9 kilitli unittest
([log](phase25/unittest-final.log)); locked sync/check_docs/check_artifacts/
check_learning/check_usability/Ruff check-format/entry smoke exit0.
Kaynak ve noneditable wheel beş senaryo/62 kayıtlı klavye eylemi,
195 gerçek Qt amaç adı sorgusu; DPI/layout-only197 ad ve %200 yazı/iki tema
render geçti. [Paket giriş noktası](phase25/wheel-entry.log) GUI_SMOKE PASS;
sekiz önemli paket kaynağı kaynak ağacıyla hash eşitliği verdi.

Sistem Python3.14.7 unittest bağımlılık eksikliğiyle exit1
([gerçek log](phase25/system-unittest-final.log)); kilitli runtime başarısı
ile karıştırılmaz. Sistem Python belge kapısı exit0. Gerçek insan/Orca/
AT-SPI/renk körlüğü katılımcısı/fiziksel DPI/temiz offline kurulum veya yeni
uzak CI kabulü yoktur. Sonuçlar yalnız gerçekleştirilen teknik kapsamındadır.
