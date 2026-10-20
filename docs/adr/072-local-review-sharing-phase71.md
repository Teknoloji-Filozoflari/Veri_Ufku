# ADR072 — yerel review ve share paketi

2026-10-16 · DEC71-01 · açık Faz71 talimatı; yalnız Linux/Python/PySide6/QML.

ReviewShare/v1; metadata-only, redacted-sample veya full-copy açık seçilir.
ShareSpec/v1 mode/version/rows/keep_numeric/sensitive_terms kapalıdır. En çok64MiB
expanded toplam,128member,32MiB artifact, Parquet taraması10000row/80column;
örnek ilk1..1000row/64column. Limit aşımı hata, silent truncation yoktur. Preview
hash proje/commit/member hashes, inclusion, scanner findings ve redaction bağlar;
export aynı seçimi yeniden tarar. Kullanıcı dışa aktarır, yayınlama/ağ yoktur.

Metadata projection schema/operation/params/run-metric/learning-notes; redaction
secret key/value, email/telefon/path ve geçici explicit terimler kapsamındadır.
Raw hash değişimi maskelenen alanlar değiştiğinde de görünür. Bunlar tam PII tespiti
veya anonimlik değildir. Hassas sayısal kolon açıkça saklanabilir; kullanıcı seçimi
ve önizleme sorumluluğu görünür. Hassas terimler pakete/yeni bir kayıt sistemine
kaydedilmez. Redacted sample bütün metin/kategori ve seçilmeyen numerikleri maskeler;
nonfinite numeric değiştirilmez, JSON preview nan/inf metniyle gösterir. Maskeli
alan String'dir; fiziksel alias→özgün ColumnId bağı korunur. RowId/SourceRecordId
aynen kalır, gizli desenli kaynak kimliği paylaşımı bloke eder.

Full copy mevcut committed mantıksal state ve manifest artifact setidir. Dış source
path /unresolved-source/UUID olur; keyring, credential, SQLite DB/lock, eski ACTIVE,
recovery/staging ve geçmiş commit arşivi paylaşılmaz. Parquet hücre/schema metadata,
UTF8 JSON/text taranır; binary/image/model/archive taranamıyorsa full kapalıdır.
Secret bulgusu override edilemez, PII bulgusu explicit ayrıca consent gerektirir.
Metadata-only raw veri satırı taşımaz; redacted örnek özgün full dataset sayılmaz.
Gönderici hash'i auth değildir. Open closed paths/size/hash/schema ve sample identity/
mask doğrular; full native state mevcut validator ile doğrulanır ve artifact yeniden
taranır. Açılış kod/model import/deserialization veya kaynak erişimi başlatmaz;
uygulamanın kendi doğrulayıcı modülleri trusted build'den yüklenir.

Diff review-only; keep-local/incoming-as-separate-fork/defer kayıtlı karar, merge
uygulaması değildir. Farklı proje kökenlerinde eşit kimlikler collision olarak
bildirilir; ColumnId ve included RowId kesişimi ayrıca sayılır (detay ilk1000). Metadata-only row collision gözlenemez; kimlikler sessiz birleştirilmez. Full-copy restore yalnız mevcut olmayan
yerel hedefe ayrı yeni ProjectStore/proje id; özgün dataset/source/row/column/run id
ve artifact byte'ları korunur, share-import event origin proje/commit/hash saklar.
renameat2 NOREPLACE ve mevcut tek yazıcı flock korunur. Mevcut proje overwrite/
shared concurrent edit ve ekip sunucusu yoktur. Ağ FS mevcut require_local ile
reddedilir; SQLite ağ paylaşımı çok kullanıcı DB sayılmaz.

ReviewEvent/v1 mevcut append-only results journal'a eklenir. Author yerel beyandır,
authenticated identity değil. Note/checklist/decision subject origin+entity hash+
artifact hashes+metadata context'e bağlıdır. Eski yorum yeni artifact'a rebind olmaz;
yeni yorum/yanıt yeni event'tir. Worker immutable envelope, pinned source paths,
ComputeBudget/supervisor ve Qt'siz process; ACTIVE yazmaz. Yeni fork yayınlaması GUI
executor thread'inde mevcut ProjectStore atomik protokolüyle, yalnız açık eylemdir.

Metadata/sample GUI2GiB ile sınanır; full native validation daha ağırdır ve explicit
4GiB koşusu ayrıca raporlanır. Bütçeler otomatik yükseltilmez. Optional server ayrı
deployment/identity/permissions tasarımı gerektirir; bu fazda yoktur.
[Teknik kanıt/resmî sınırlar](../evidence/PHASE71.md).

Son güvenlik sınırı: tam kopyadaki serbest metadata/artifact metninde kalan dış
konum deseni de override edilemeyen engeldir. Yalnız üretilen /unresolved-source/UUID
placeholder geçer; metadata-only/redacted projection konumu maskeler. Böylece raw
not içindeki /home yolu, yalnız source.path disarm edildi diye gözden kaçmaz.

Review checklist'teki tam `secret-pii-reviewed` anahtarı yalnız boolean ise credential
anahtarı değildir; True/False korunur. Aynı anahtarda metin/sayı veya gerçek api_key
credential istisna kapsamına girmez. Yorumlu full-copy başka fork'a taşınırken eski
subject/artifact context aynen tutulur; dış köken görünür kalır.
