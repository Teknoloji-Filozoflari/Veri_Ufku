# Üçüncü taraf kayıtları — Faz 01

2026-10-06. Projenin kendi dağıtım lisansı henüz seçilmedi; dağıtım adayı kabulü yoktur. uv.lock sürüm/hash ana kaydıdır.

| Bileşen | Lisans kaynağı / yükümlülük |
|---|---|
| PySide6, shiboken6, Qt paketleri 6.11.2 | Kurulu dist-info LICENSES ve [Qt lisans belgeleri](https://doc.qt.io/qt-6/licensing.html); LGPLv3/GPL/commercial ve modül bazlı koşullar. Yeniden dağıtımda ilgili metin/bildirim, LGPL değiştirme/yeniden bağlama imkânı gerekir. |
| Ruff 0.16.10 yerel dev wheel | Wheel içindeki ruff-0.16.10.dist-info/licenses/LICENSE (MIT); yeniden paketlemede korundu. Manifest sha256 ve RECORD kontrolü uygulanır. Runtime'a paketlenmez. |
| pytest 9.1.1 | dist-info lisans (MIT), dev bağımlılığı. |
| Python / build ve transitif dev paketleri | Dağıtılan artefactın dist-info lisansları korunmalı; tam uygulama bundle lisans envanteri paketleme fazında doğrulanacak. |

Marka, ikon veya referans uygulama varlıkları alınmadı. QML native controls ve metin kullanır. Bu kayıt tüm gelecekteki analitik paketlerin lisans kabulü değildir.
