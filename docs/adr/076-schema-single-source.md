# ADR076 — şema tek doğruluk kaynağı

2026-11-13 · Faz A · şema geliştirme çerçevesi v1.0 · açık kullanıcı talimatı.

Veri_Ufku ürününün bilgi mimarisi ve kapsamı `veri_ufku_sema.pdf` ile tanımlanır: 7 aşama
(Veri · İncele · Görselleştir · Hazırla · İstatistik · Model · Raporla), 61 alt başlık,
"Çekirdek/Modül" ayrımı, Mod 1 / Mod 2 ayrımı ve Bulgu defteri omurgası. Bu PDF ürün
sözleşmesinin kaynağıdır.

Kod yolu bugün iki anlatı taşır: UX-V2 kabuk (10 aşamalı `UxStages.js`, 8 bölümlü `Main.qml`,
kaynak-aşamaya göre organize edilmiş Raporla paneli, "Gelişmiş"in arkasına gizlenmiş model
yolları) ve şema yolu (7 aşama, 61 alt başlık, işlevle organize edilmiş Raporla, Mod 1/Mod 2
ayrımı, kurulu olmayan modül için "Modül: indir"). Bu iki anlatı çelişir.

Karar: **şema tek doğruluk kaynağıdır.** Kod yolundaki sapmalar şemaya uydurulmaz. Şema
değişmeden kod başka yere taşınmaz; taşınacak kod, aktif fazın kapsamı dışındaysa faz
notunda belirtilir ve kullanıcıya sorulur. Şemadaki bir alt başlık kodda yoksa "yapılmamış"
görünür ve açıkça işaretlenir; uydurulmuş karşılık, boş buton veya sahte sonuç yazılmaz.

Belge yükümlülüğü: `docs/SCHEMA_CONTRACT.md` 61 alt başlığın her biri için tek satırlık
durum (var · eksik · yok) ve gerekçe taşır; çelişkiler ayrı bölümde listelenir.
`docs/SCHEMA_MAP.md` alt başlık ↔ modül ↔ QML ↔ test eşlemesini tutar ve bağlayıcıdır: bir
alt başlık için yeni kod yazıldığında karşılığı haritada gösterilmeden alt başlık "var"
sayılmaz.

Belirsizlikler yorumlanmaz. Kaynak çerçevenin §8 listesindeki on madde kullanıcının
kararına bırakılır; karar verilmemiş madde kod yazılmadan önce bağlanır ve
`SCHEMA_CONTRACT.md` belirsizlik bölümünde "bekliyor" olarak görünür kalır. B-02 ve B-03
2026-11-13'te karara bağlandı: bulgu defteri **alta çekmece**, Raporla **yedi iş birincil
sekme** (kaynak-aşamaya göre bölüm ikincil sekmede).

Sıra kısıtı: yalnız kullanıcının açıkça gönderdiği faz uygulanır. Çerçevenin tamamını okumak
bütün fazları başlatma yetkisi değildir. 2026-11-13'te Faz A, B ve C uygulanıyor; D–J
başlatılmaz.

Bu karar kod davranışını değiştirmez (Faz A kodu değiştirmez). Kodu şemaya bağlayan fazlar
sırayla uygulanır ve her biri kendi kabul kapılarıyla kanıtlanır.
