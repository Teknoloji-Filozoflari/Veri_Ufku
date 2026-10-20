# Veri_Ufku API1 — bağımsız ortalama örneği

Bu klasör self-contained örnek pakettir: manifest.json, plugin.py ve request.json.
CC0-1.0, Veri_Ufku projesi tarafından örnek kod olarak yayımlanmıştır.
Bağımlılık indirme veya proje açılışında import yoktur. Kaynağı değiştirince
manifestte code_sha256 güncelleyin; hash yayıncı imzası veya güven kanıtı değildir.

Kilitli uygulama ortamında bağımsız contract testi:

```sh
.venv/bin/python -m veri_ufku.plugins.contract_test --manifest examples/plugins/mean/manifest.json --request examples/plugins/mean/request.json --trust-code
```

Beklenen mean=2, n=3, null dışlanır. Contract yalnız protokolü denetler; sayısal
referans ayrıca tests/test_plugins.py içinde bağımsız assertion ile doğrulanır.
CLI GUI/ProjectStore açmadan ayrı process'te çalışır; güvenli OS sandbox değildir.

GUI: Rapor → Uzman eklentileri / SDK → bu manifestin mutlak yolunu seç → incele →
seçili numeric dataset/ColumnId tarifini yükle → kod/izinlere güven onayı → çalıştır.
Sonuç ve `example-mean-help` yardım snapshot'ı projeye kaydolur. Paket silinse de
kayıtlı sonucu açabilirsiniz; recompute için aynı paket ve explicit trust gerekir.

SDK altı türün sürümlü data sözleşmesini sunar; host importer/transform çıktılarını
tablo preview artifact'ı olarak arşivler, aktif dataset yapmaz. Model state yalnız
safe JSON arşividir; model prediction/reload, executable object checkpoint ve
kullanıcı kodu otomatik import yoktur. Lesson düz metin snapshot'ıdır; otomatik
çekirdek katalog kurulumu yoktur. Chart x/y numeric descriptor arşividir; bu örnek
istatistik analizidir, tam native chart editor/renderer eklentisi değildir.
