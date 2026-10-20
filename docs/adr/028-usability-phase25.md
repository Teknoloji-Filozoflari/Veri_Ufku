# ADR-028 — Faz25 kullanılabilirlik ve erişilebilirlik denetimi

Tarih: 2026-10-09 UTC / 2026-10-10 Europe/Istanbul. Python/PySide6/QML korunur.

Ortak UiCombo/UiTextField/UiTextArea/UiSpinBox erişilebilir amaç adı taşır.
Tab/ShiftTab metin alanından çıkar; dinamik import tür seçicisi yeniden
oluşturulduğunda aynı adla odak korunur. Salt okunur tablo başlıkları Tab
sırasında değildir; veri tablosunun ok tuşları satır seçer, Tab tablodan çıkar.
Boş tablo da odak tuzağı oluşturmamalıdır. F1 yardımın çıkışında odak geri gelir;
gelişmiş görünüm yardım makalesini ve açık paneli korur.

Arayüz tercihleri ayrı atomik `ui-preferences.json` şema4 kaydıdır. Varsayılan
koyu/Türkçe/%100; kullanıcı açık tema, %125–200 yazı ve temel İngilizce
arayüzü Görünüm ve dil / Ctrl+, ile seçebilir. Dosyanın ondalık/tarih parse
ayarları bu tercihlerden bağımsızdır. Eski tercihler açılışta yazılmaz.
Ayrıntılı yardım ve bazı analiz metinleri Türkçedir; tam İngilizce ürün iddiası yok.

Yardım denetimi yapısal alanlar ve bağları kontrol eder; jargon/kesinlik
adaylarını insan incelemesine sunar. Bu aday listesinin boş olması doğruluk
veya okunabilirlik kanıtı değildir. Ortak form kontrolü eklenirse aynı kapı
uygulanır. Temel çevirilerde unfinished kabul edilmez.

Matplotlib grup grafikleri renk yanında tarama/desen/işaret kullanır;
korelasyon sayısal alternatifle okunur. Renk görme bozukluğu olan bir
katılımcıyla test yapılmadı. Qt QAccessible ad/rol sorgusu, Linux AT-SPI
aktarımı veya Orca konuşması değildir.

Beş senaryo QTest klavye eylemleriyle gerçek worker/proje/export yollarını
çalıştırır. XDG, başlangıç klasörü ve sentetik dosya test fixture'ıdır.
Senaryo walkthrough'u sıfır bilgi kullanıcı testi değildir. İnsan testi ve
ekran okuyucu açıkları faz durumunu sürüyor tutar; sonraki faz başlatılmaz.
[Kanıt](../evidence/PHASE25.md), [insan testi planı](../USER_TEST_PLAN.md).

Qt uygulaması tekrar kullanıldığında eski shell’in engine/çeviricileri ve
aboutToQuit bağlantısı tutulmaz. Cleanup idempotenttir; eski engine’in
ertelemiş silmesi yeni shell’den önce tamamlanır. Görünüm/tema/yazı değişimi
retranslate çalıştırmaz; yalnız dil değişimi yapar. Kaynak bütçesi sabittir.
