# Lisans kararı ve dağıtım koşulları

Kullanıcı Faz27 sırasında açıkça GPL-3.0-or-later seçti. Veri_Ufku kaynak kodu ve proje varlıkları, ayrı bildirim taşıyan sentetik örnek/font/üçüncü taraf dosyalar hariç, bu lisansla dağıtılır. Tam metin LICENSE dosyasındadır. Bu bir yayıncı kararıdır; henüz kamuya release yayımlanmadı.

Python bağımlılıklarının dist-info lisansları ve native/font bildirimleri pakette korunur. Paket /app/share/veri-ufku/runtime-inventory.json içinde sürüm, dosya SHA256, upstream sdist/wheel URL ve hash'lerini içerir. Önceki fazların lisans metinleri docs/third_party altında korunur.

Qt/PySide6 6.11.2 dinamik kitaplık olarak dağıtılır. [Qt lisans koşulları](https://doc.qt.io/qt-6/licensing.html) modül bazlıdır; bundle içindeki GPL modülleri için uygulamanın GPL seçimi kaydedilir. QtPdf [LGPLv3 veya GPLv2](https://doc.qt.io/qt-6/qtpdf-licensing.html) seçeneklidir; PDFium bildirimleri ayrıca gereklidir. [LGPL yükümlülükleri](https://www.qt.io/development/open-source-lgpl-obligations) kapsamında değiştirilmiş kitaplığı kullanma/relink ve bu amaçla tersine mühendislik hakkı kısıtlanmaz.

Paket kaynak Python/QML dosyalarını içerir. Yeniden üretim: uv.lock ile kilitli dev ortamı hazırlayın, packaging/flatpak/bundle.json içindeki SDK/runtime commit'lerini kurun, scripts/build_flatpak.py çalıştırın. Qt değişimi için eşleşen PySide/Qt ABI kitaplıklarını dev ortamında değiştirip ayrı uygulama kimliği/yerel repo ile yeniden paketleyin; normal çalışma /app içindeki dinamik kitaplıkları yükler. Özgün Qt/PySide kaynakları https://download.qt.io/official_releases/qt/6.11/6.11.2/ ve https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.2-src/ adresindedir. Kamuya dağıtım öncesinde exact kaynak arşivleri, Qt third-party notices ve runtime kaynak erişimi somut artefact olarak doğrulanmalıdır; yalnız URL yazmak bu kapıyı kapatmaz.

org.veriufku.Veri_Ufku yerel uygulama kimliğidir; alan adı/Flathub sahipliği iddiası değildir. Kamuya yayın, marka/kimlik ve kaynak sunumu ayrıca açık kullanıcı talebine bağlıdır.
