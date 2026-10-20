# ADR-033 — Faz32: sözleşmeler ve onaylı kimlik ilişkileri

2026-10-11; deneysel. Açık kullanıcı talimatı Faz32 kapsamını zorunlu kılar;
önceki insan/AT/donanım/dağıtım kabul açıklarını kapatmaz. Faz33 başlatılmaz.

Faz07 semantic_metadata/ColumnId alanları korunur; description anlamı,
unit birimi ve ordinal_order sırası yeniden tanımlanmaz. measurement_level
unknown/nominal/ordinal/interval/ratio additive alanıdır. Bilinmeyen ölçüm
birimi değerlerden çıkarılmaz. Ordinal görünüm açık onaylanan sırayı kullanır;
listede bulunmayan değerler/null sona gelir ve sözleşmede ayrıca yakalanır.

Kapalı JSON Contract/v1: schema_version=1, rules listesi; her kural id, kind,
column_id, severity (warning/error), parameters taşır. range/nullable/ordinal
satır, unique/type/unit kolon, row_count tablo, foreign_key tablolar arasıdır.
Bound scalar literal mevcut fiziksel tür doğrulayıcısından geçer; kod/SQL/eval
çalıştırılmaz. UNIQUE null politikası açık; FK referansı değişmez DatasetVersion
ve ColumnId taşır; nullable FK referansta null key aramaz. Kontrol başına bir
referans dataset desteklenir, çoklu referanslar ayrı kontrollerdir. Composite
key, genel ifade DSL ve kendiliğinden birim dönüşümü kapsam dışıdır.

schema_contract mevcut DatasetVersion ile definition_version bağlantısını
saklar. Değişen sürüm requires_validation; kaldırılan kolon inapplicable;
kontrol sonucu ve politika operasyon/provenance kaydına bağlıdır. Düzenlemek
ve kontrol etmek ayrı açık eylemlerdir. Tarifi JSON olarak dışa yazmak atomiktir;
başka dataset'te ColumnId ve FK sürümleri kullanıcı tarafından yeniden bağlanır.

Stop hata varsa yayını engeller; warning raporlanıp kalır. Continue hata/uyarıyı
saklayıp aynı değerleri yayınlar. Quarantine hata satırlarını tam kimlikleriyle
ayrı değişmez Parquet lineage artifact'ta saklar; warning satırları kalır.
Tablo/tür/birim/sıra tanımı hatası karantinayla çözülemez ve durur. Null,
nonfinite ve duplicate ihlalleri açık sayılır. Rapor tam veri sayımı ve en fazla
10 örnek/kural taşır; örnek görüntüsü256 karakter ile sınırlıdır, tam kayıtlar
kaynak/karantina snapshot'larında kalır. Kaynak dosyaya yazma yapılmaz.

SequenceMatcher(auto junk kapalı), NFKC/casefold/strip yalnız aday puanlamasında
kullanılır; kaynak metin değiştirilmez. Exact normalize edilmiş nonempty
blocking grubu dışında karşılaştırma yok; score olasılık/kimlik kanıtı değildir.
En fazla20.000 kayıt,20.000 karşılaştırma ve200 aday; sınır aşımı açık hata,
sessiz kırpma yok. Kategori adayları en fazla200 benzersiz String değer;
bu sınırlar UI ve kapalı ComputeBudget worker yaşam döngüsündedir.

Entity merge explicit approved=true, self-reported reviewer, reason ve timezone
aware at ister. Onaylı çift güncel blocking/skor listesinden yeniden doğrulanır.
Onay kimlik doğruluğunun veya inceleyenin kimliğinin sertifikası değildir.
Satır birleştirip silmek yerine canonical_id ataması yapılır; RowId,
SourceRecordId ve kullanıcı kolonları korunur. Yalnız önceki canonical alanı
veya yeni String ColumnId kullanılabilir; rastgele kullanıcı kolonuna yazılmaz.
Önceki gruplar bölünmez; birleşen grupların en küçük mevcut canonical kimliği
korunur. Tam input_version/row/source/previous_canonical/canonical ilişkisi
Parquet inverse artifact'tadır. Parent snapshot tamamıyla korunur.

Category map yalnız tek tek açık onaylanan kaynak→hedef String değerleri
değiştirir. Aday üretimi publication_allowed=false: Uygula engellidir. İnsan
onayı bir önizleme üretir; ayrıca Uygula ve kaydet eylemi gerekir. Eski analiz,
FK ve diğer sonuçlar eski DatasetVersion'a bağlı kalır; otomatik retarget yok.
İnsan karar günlüğü descendant/input-version ilişkileri üzerinden bağlı sürüm
ve sonuç kimliklerini gösterir. Undo/redo mevcut workflow head protokolüyle
tam önceki/sonraki snapshot'a geçer; journal ve eski sonuçlar silinmez.

Tek Capability registry, OperationSpec, worker ComputeBudget ve parent
ProjectStore ACTIVE protokolü kullanılır. Parent yayın öncesi closed recipe'yi
immutable girdilerden tekrar değerlendirip çıktı/diagnostics/inverse hash'lerini
kontrol eder; worker sonucu tek başına yetki değildir. Manifest7 additive
alanları yeni okuyucu gerektirir; eski okuyucunun ileri uyumluluğu iddia edilmez.

Kaynak incelemesi: kurulu CPython difflib.SequenceMatcher docstring/kaynak
ve mevcut immutable metadata/OperationSpec/ProjectStore sözleşmeleri.
