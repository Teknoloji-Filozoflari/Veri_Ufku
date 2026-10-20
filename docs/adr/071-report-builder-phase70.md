# ADR071 — bounded bilimsel rapor oluşturucu

2026-10-16 · DEC70-01 · açık Faz70 talimatı. Linux/Python/PySide6/QML korunur.

ReportSpec/v1 kapalı sıralı bölüm tarifi; section/note/assumption manuel metin,
method/result/model-card/uncertainty/diagnostic kayıtlı alan projeksiyonu,
dictionary seçili metadata, table ilk1..100satır/1..16kolon, chart immutable
PNG/SVG/PDF, bibliography query/auth içermeyen HTTPS atıf metni. En çok32blok,
64MiB snapshot,16MiB native artifact,128KiB blok,32MiB toplam dosya bütçesi.
Metadata/sayısal bulgu eksikse not_recorded; analiz/model recompute yok.

İki built-in preset ve kayıtlı rapor tarifini yeniden kullanma; serbest rich-text,
DOCX, LLM ve dış servis bu sürümde desteklenmez. Deterministik anlatı etiketli
kaynak alanlarıdır; kullanıcı metnindeki sayılar doğrulanmış metrik sayılmaz.
Keşifsel/doğrulayıcı beyan, seçim planı ve mevcut test defteri görünür.

Mevcut registry/ComputeBudget/supervised worker/ProjectStore transaction kullanılır;
worker immutable envelope alır, ACTIVE yazmaz. Kaynak/sonuç hash'leri publish ve
export öncesi doğrulanır. Report result ve dosyalar immutable manifest'e eklenir;
source→dataset→result→report gerçek edges. Eski sürüm/yeni aynı capability run
STALE; dış kaynağın canlı tazeliği doğrulanmış sayılmaz. Yeni rapor açık eylemdir,
analiz recompute kendi aracından ayrıca başlatılır. Açılış hesap/ağ başlatmaz.

MD/HTML/PDF gerçek üretilir; A4/bundled DejaVuSans, HTML gömülü font/PNG, PDF
whitelist image resolver; user HTML escape. SVG/PDF/CSV/Parquet ve isteğe bağlı
Faz63 numeric profile reference-only Python/SQL/notebook ZIP'i ana ZIP'te bağlıdır.
Bu kod paketi bütün raporu yeniden üretmez. Standalone export attachment'ları
kopyalamaz; taşınabilir paylaşım ZIP'tir. Manifest her dosyayı hash'ler; paket
kendisini kendi manifest'inde hash'lemez, dış ProjectStore manifest'i ZIP'i hash'ler.

Redaction açık ColumnId ve secret/path/email desenleri; preview nedenleri eski
gizli değeri saklamaz. Maskeli kolon kullanan grafik reddedilir, grafik içi yazı
otomatik anonimleştirilmez; allow_graphics açık inceleme beyanı gerekir.
Bilinen pattern dışındaki serbest metin için anonimlik garantisi yoktur. CSV null
boş hücre ve formül escape politikası açık; Parquet null/type korur, maskeli kolon
String olur. Kayıtlı dosyaların hash'i açarken doğrulanır; exclusive export
proje içini/symlink/varolan dosyayı reddeder. GUI review onayı paylaşmadan önce
zorunlu; ayrı process güvenli sandbox olarak sunulmaz.

Teknik doğrulama ve resmî kabul ayrıdır; gerçek komut/ortam/sonuçlar
[PHASE70](../evidence/PHASE70.md). Önceki formal açıklar korunur.
