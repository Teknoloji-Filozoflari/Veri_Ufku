# ADR060 — Faz59 bounded offline öneri ve ayrı query ranking

DEC59-01, 2026-10-15: açık Faz59 talimatı. Linux Python/PySide6/QML korunur;
Faz60 yetkisi yok. Mevcut native Parquet SourceAdapter, Capability registry,
ComputeBudget, Provenance, neural artifact/experiment projection ve ProjectStore
parent-ACK atomik yayını genişletilir. İkinci run/model kayıt sistemi yok.

Dört CPU şablonu: unique positive-user popularity, numeric cosine content,
explicit/implicit ALS ve ayrı query-group pairwise logistic ranking. User/item
kimliği string/integer tipiyle kodlanır; isim benzerliği birleştirme değildir.
ColumnId, DatasetVersion, RowId, SourceRecordId ve snapshot hash saklanır.
Time sayısal Unix seconds; dönüşüm kullanıcı işlemidir. Null/nonfinite/bozuk
ve rol çakışması reddedilir.2000row/32user/128item/16feature/64query,16factor,
50epoch/10000LTRpair sınırları ve global süre/RAM/cancel bütçesi vardır.

Explicit ALS observed squared error + ridge; missing pair normal equation'a
katılmaz, tekrar pair son tarihsel rating. Aynı zamandaki çelişki reddedilir.
Implicit ALS preference(event>0), confidence1+alpha·strength; unseen p0/c1
bir model varsayımıdır. [Hu/Koren/Volinsky](https://yifanhu.net/PUB/cf.pdf)
confidence formülünün kaynağıdır. Content ölçek/birim dönüşümü yapmaz;
item content snapshot içinde değişiyorsa as-of enrichment yapılmış sayılmaz,
reddedilir. Profil pozitif tarihsel item unit vektörlerinin normalize ortalaması.
Zero profile fallback popularity. Skor olasılık değildir.

Temporal: cutoff öncesi fit, snapshot sonuna kadar holdout. Leave-last-out:
kullanıcı son timestamp'taki bütün bağlar holdout; her query için strict global
historical prefix. **Bütün** holdout RowId'ler **bütün** fitlerden çıkarılır;
başka kullanıcının heldout'u da training'e giremez. Daha erken query gelecekteki
hiçbir event'i görmez. Kullanılmayan kayıtlar excluded olarak saklanır. Final
test bu panelde kapalı; önceki test-use defteri run seçimiyle sıfırlanmaz.
Kaydedilen model en son query prefix modelidir; tüm snapshot'a refit değildir.

Recommendation catalog yalnız prefix'te gözlenmiş item'lardır; tam katalog
ifadesi **bu tarihsel gözlenen katalog** anlamında sınırlıdır, ticari gerçek katalog
iddiası değildir. Tam ve sampled aday listeleri/hash/seed kayıtlıdır. Uniform
sampling replacement olmadan, kullanıcının geçmişte görmediği eligible item'lar;
held relevant adayda mevcutsa her zaman dahil. Seen filter açık seçilir. Cold
ve seen relevant recall/AP/NDCG paydasında kalır; unreachable ayrı raporludur.
Sampled/full metric karşılaştırma anahtarı ayrıdır;
[Krichene/Rendle](https://research.google/pubs/on-sampled-metrics-for-item-recommendation/)
bu ayrımın gerekçesidir. Precision paydası K, AP min(K,total relevant), binary
NDCG; boş relevance recall/AP/NDCG ortalamasından çıkarılır, n görünür.
Coverage unique recommended/catalog union; diversity1−cosine yalnız nonzero
content ile. Temporal horizon ve n query raporlanır; gerçek kullanıcı faydası
kanıtlanmaz. Tüm sorguların macro ortalaması ve aynı aday popularity baseline.

LTR input ayrı query/user/item/relevance/time + numeric feature şemasıdır.
Query tek kullanıcı/tek timestamp/unique item. Train query'ler cutoff öncesi;
validation query'lerin feature'ları query anında mevcut olmalı. Pairwise logistic
karşılaştırmalar query içinde, scaler yalnız train pair'lerden. Graded relevance
öğrenilir, raporlanan top-K metrikler binary relevance>0 olarak açıktır. Yeni
query aday feature'ları açık payload ile istenir; classifier etiketi veya implicit
negatif sanılmaz. Optional XGBoost/LightGBM ranking runtime doğrulaması iddiası yok.

New-list inference saved numeric JSON, fit yok. Unknown user popularity;
unknown item zero popularity ve açık reason. LTR nonpersonal query score yeni
kullanıcıda da çalışır; candidate feature yoksa reddeder. Kaynak ürünlerin
RowId/SourceRecordId ilişkisi listede. İstekle eklenen unknown item için kaynak
satırı uydurulmaz. Yeni dosya export O_EXCL/O_NOFOLLOW/0600, varsayılan per-export
salted pseudonym; raw IDs ayrı açık onay. JSON'da formül/HTML çalıştırılmaz;
pseudonym anonimlik garantisi değildir. Ağ, kullanıcıya gönderme veya deploy yok.

[Gerçek kontroller ve açıklar](../evidence/PHASE59.md) resmî kabulden ayrıdır.
