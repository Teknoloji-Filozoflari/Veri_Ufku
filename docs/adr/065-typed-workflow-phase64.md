# ADR065 — bounded typed DAG, Faz64

Tarih: 2026-10-15. Durum: uygulanmış teknik kapsam; resmî kabul ayrı.

Tek Capability registry port türlerini tanımlar. TypedDAG/v1 data-only JSON, mevcut OperationSpec/v1 düğüm işlemlerine derlenir. Source, transform, quality, analysis, train, predict ve export yürütülür. Transform ilk kapsamı mevcut rename/drop/filter; quality numeric required-null; analysis mevcut tam numeric profile/ddof; train doğrulanmış statsmodels OLS tek feature, predict güvenli katsayı şeması; export Parquet. Diğer yöntemler bu runner'da destekli sayılmaz. OLS kullanıcı varsayım onayı ister; tüm upstream veride fit, held-out score veya otomatik model seçimi yoktur. Önceki model/evaluation/test kullanım defteri korunur.

Girişler yerel immutable DatasetVersion snapshot'larıdır. Yeniden import veya yeni sürüm açık eylemdir. Orijinal dosyanın değişmesi geçmiş snapshot'ı yeni veri yapmaz; snapshot hash bozulması cache hit yerine hata verir. SourceAdapter yeni kayıt sistemi oluşturulmaz; ağ/import/schedule düğümü yoktur. Kaynak yazma kapalıdır.

DAG en çok24 node, kaynak başına10000 satır/64 kolon, batch×sweep8 case,500000 row×node önkontrolü ile mevcut ComputeBudget altında ayrı Qt'siz worker'da çalışır. Worker ACTIVE veya ProjectStore nesnesi almaz. GUI/CLI aynı worker/calculate ve parent ProjectStore atomik yayını kullanır. DatasetVersion/ColumnId/RowId/SourceRecordId native artifact içinde korunur; türetilmiş sürümler run kapsamındadır, ana dataset head otomatik değiştirilmez. Provenance kaynak snapshot'ları, OperationSpec, parent key, config/code/env ve doğrulama zamanını taşır. Kalıcı final test geçmişi mevcut registry ile bağlanır; bu akışta test değerlendirmesi yapılmaz.

Port/type/cycle ve after dependency kontrolü yürütmeden önce yapılır. Hatalı bir node yalnız bağımlılarını blocked yapar; bağımsız dal korunur. Çıktı eski başarılı run'ın yerine yazılmaz; her çalıştırma yeni run'dır. Edit veya geçmiş run açma stale gösterir. Başarılı durum yalnız kayıtlı doğrulama zamanına aittir; gelecekteki değişiklikler kendiliğinden izlenmez.

Cache key kaynak sürüm/hash/schema/semantics, node params/config/method version, parent key, uygulanan code hash, paket/Python ortamı ve ComputeBudget içerir. Hit öncesi ve sonrası kaynak tekrar hash edilir, artifact hash kontrol edilir. Bozuk entry yeniden hesaplanır; değişen kaynak güvenilir sayılmaz. Cache private OWNER marker/LOCK ile tek runner'a aittir; SIGKILL kalıntıları yalnız sahipli .tmp-dag-* dizinlerinde temizlenir. Cache doğrulaması aynı kullanıcıya karşı kriptografik sandbox veya imza iddiası değildir. Disk bütçesi uygulanır; cache otomatik süresiz büyütülmez. Dağıtık runner/cache paylaşımı yoktur.

Retry saf compute aşamasında geçici OSError için0–2 ile sınırlıdır; doğrulama/quality hatası tekrar edilmez. Export terminal side effect'tir; after bağımlılığı olamaz. Parent explicit allow_export ve gerçek yerel output diziniyle UUID-case-node.parquet adını üretir, exclusive link yayınlar. Var olan kaynak/başka run çıktısı ezilmez. Aynı token ve aynı case/node/cache key/hash için önceki proje receipt'i varsa tekrar already_published sayılır; yalnız dosyanın varlığı sahiplik kanıtı değildir. Proje commit öncesi crash dış dosya bırakabilir: orphan otomatik benimsenmez/ezilmez; yeni token veya kullanıcı incelemesi gerekir. Dosya sistemi ile proje arasında dağıtık atomik transaction iddiası yoktur. Canceled run'ın hazır exportları yayınlanmaz. Dış yayın parent aşamasında kısa bounded dosya I/O'dur; worker iptali tamamlanan dosyayı geri silmez. Kullanıcı exportu sistem kimlik kolonlarını çıkarır; iç native artifact kimlikleri korur.

Batch dataset seçimi kaynak düğümü→DatasetVersion, açık bijektif ColumnId eşlemesi ile yapılır; fiziksel tür/unit/role/ordinal uyumu doğrulanır. Sweep ilk kapsam analysis.ddof=[0,1]; rastgele kod veya keyfi model parametre araması değildir. Dry-run şema/dependency ve kaynak hash kontrolü/maliyet planıdır; compute/cache/export yapmaz, plan run kaydı projede saklanır.

Local schedule mevcut değil. Uygulama kapalıysa otomatik iş yoktur. Kullanıcı CLI'yi açıkça çağırabilir; GUI ve CLI aynı projede eşzamanlı writer olamaz. CLI SIGINT/SIGTERM, wall/RSS ve worker ComputeBudget iptal yollarını kullanır. Sisteme cron/service kurulmaz. Kaçırılan schedule başarılı sayılmaz; schedule yürütüldü kaydı üretilmez.

CLI örneği (aktif kilitli ortam veya kurulu wheel):

```sh
.venv/bin/python -m veri_ufku.operations.workflow_cli --project /yerel/proje --dag /yerel/akış.json --cache /yerel/cache --dry-run
.venv/bin/python -m veri_ufku.operations.workflow_cli --project /yerel/proje --dag /yerel/akış.json --cache /yerel/cache --allow-export --output-dir /yerel/çıktı
```

Tarif veri/credential/model nesnesi içermez; kullanıcı JSON'a secret yazmamalıdır. Credential okunmaz, ağ çağrısı yoktur. JSON'dan Python import/exec/pickle yapılmaz. GUI'de Hazırla → Typed DAG bölümünden source snapshot, tür/form ve portlar seçilir; ileri declarative editör branch/after/batch/sweep'i düzenler. Tarif açmak veya geçmiş run okumak yürütme başlatmaz. Yardım offline katalogdadır.
