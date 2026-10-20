# Veri_Ufku — 0.1.0 candidate kapsamı ve kabul kapısı

2026-10-16 DEC75-01 / ENV-75. **Deneysel yerel CPU desktop candidate**, genel veya
uzman onaylı production release değil. Bütün veri bilimi yöntemleri tamamlanmadı.
Dış yayınlama ayrı kullanıcı talebidir; bu faz yayınlama yapmaz.

Seçilen teknik değerlendirme kapsamı: küçük sentetik fixture'larla tablo
cleaning/chart/export, typed weights/survey/MI, fixed-horizon experiment ve optional
Bayes, regression/classification probability/conformal calibration, spatial-block ve
group/time plan, bounded causal/survival, yerel NLP/CPU vision/audio, recommendation/
graph ve typed workflow/repro bundle. Tam bütün backend/dataset/yöntem kombinasyonu,
ağ sunucuları ve gerçek klinik/endüstriyel kullanım doğrulaması değildir.

Kapsam değerlendirme başlamadan `scripts/benchmark75_plan.py` içinde açıkça seçildi.
Başarısızlıklar kapsamdan silinip sürüm onaylanmaz. Her grubun timeout/fail/skip
başarıdan ayrı saklanır. Yeni deneme önceki kanıtı ezmeyen ayrı klasöre gider.
Kaynak ile kurulu noneditable wheel testleri ayrı; GUI offscreen/software gerçek
kontroller/spawn/save/export yoludur, insan kullanılabilirlik testi değildir.

Nihai release için kapsamın bütün zorunlu gereksinimleri, güvenlik/veri bütünlüğü ve
uygulanabilir insan/uzman/erişilebilirlik/minimum donanım/uyumluluk kontrolleri kanıtlı
olmalıdır. Eksik, ertelenmiş, unsupported ve engelli işler bu koşulu sağlamaz.
Mevcut resmî kapılar açık olduğu için faz ve sürüm **doğrulandı olarak işaretlenmez**.
Kritik hata yok ifadesi yalnız gerçekten geçen testler için söylenebilir; test
edilmeyen yöntemler, gerçek veri veya düşmanca tüm girişler için garanti değildir.

[Ana matris](REQUIREMENTS_MATRIX.md), [capability sınıfları](PRO_CAPABILITY_MATRIX.md),
[E75 benchmark ve açık sorunlar](evidence/PHASE75.md). Kararlı sınıfı bağımsız kabul
kanıtı gerektirir; registry'nin supported alanı tek başına kararlı değildir.
Unknown/unsupported alt işlem eksik kapsamdır. Bir ailenin küçük örneğinin geçmesi
bütün alt yöntemlerinin tamamlandığı anlamına gelmez.

Dağıtım: Faz74 core ve seçili geospatial/arrays/CPU neural Flatpak local candidates;
exact hash/runtime ve gerçek paket smoke kayıtları korunur, Faz75'te ayrıca hash
uyumu denetlenir. Runtime önceden var olan fresh uygulama kurulumu temiz OS/offline
installer değildir. Pardus/Debian/ayrı Arch/GPU, insan file chooser ve uzaktaki yeni
CI çalışması yoktur. App rollback proje şema migration'ını geri almaz. Worker env
provisioning/generic local extra installer yoktur. [Kurulum sınırları](INSTALL_TR.md).

Uzman öğrenme review'u424content item için hash/version ve boş reviewer/karar
alanlarıyla hazırlanır; pending durumdadır. Teknik kaynak kontrolü veya AI üretimi
uzman onayı değildir. [İnsan/uzman test protokolü](RELEASE_REVIEW_PROTOCOL.md).
