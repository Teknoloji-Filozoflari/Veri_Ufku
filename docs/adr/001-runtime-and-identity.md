# ADR-001 — Yerel masaüstü yığını ve kimlik

Tarih 2026-10-06; karar: kabul edilmiş tasarım, uygulama/bağımlılık çözümü doğrulanmadı.

Görünen ad **Veri_Ufku**. Python dağıtım adı `veri-ufku`, import paketi `veri_ufku`, CLI `veri-ufku`. Masaüstü uygulama kimliği geçici `org.veriufku.Veri_Ufku`; alan adı sahipliği doğrulanmadı, release öncesi yayıncı kararı gerekir. XDG veri/config/cache/log alt dizinleri teknik `veri_ufku`; proje yolu uygulama kimliğine bağlı değildir. Kimlik değişikliği veri taşıma/alias ADR'si ister.

Python/PySide6 + Qt Quick Controls korunur. Polars, ihtiyaçta DuckDB, SciPy/scikit-learn, optional statsmodels; Matplotlib adaptörü. Web, Docker, zorunlu servis yok. Kurulu Python 3.14.7 altında Qt 6.11.2 başsız probe geçti. Eksik analitik paketler nedeniyle bütün yığın uyumu doğrulanmadı.

Başlangıç kilit çözümü için CPython 3.13 ailesi tercih edilir: [SciPy resmî toolchain tablosu](https://docs.scipy.org/doc/scipy/dev/toolchain.html) 1.16 için <3.14 bildiriyor. Bu kaynak yeni SciPy sürümlerinin uyumunu tek başına kanıtlamaz. Python 3.13 burada kurulu değil; Faz 01'de gerçek sabit patch + wheel/Requires-Python + transitif çözüm denenmeden runtime seçimi tamamlanmış sayılmaz. 3.14 uyumlu tüm seçilmiş wheel'ler doğrulanırsa ek ADR ile tercih güncellenebilir. Mevcut sistemi downgrade etme veya sistem Python'una pip kurma yok.

Faz 01 izole uv ortamı, sabit Python patch, uv.lock ve hash'li paketler; dev grupta pytest/ruff. Ağ/registry erişimi yoksa sürüm tahmin edilmez, Faz 01 kilit kabulü doğrulanmadı kalır. Qt QML/plugin yolu paketle birlikte; sistem `/usr/lib/qt6` yolları son kullanıcıda varsayılmaz. [ENVIRONMENT](../ENVIRONMENT.md), [DEVELOPMENT](../DEVELOPMENT.md).
