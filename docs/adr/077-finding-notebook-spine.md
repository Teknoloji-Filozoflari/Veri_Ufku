# ADR077 — Bulgu defteri omurgası

2026-11-13 · Faz B · şema geliştirme çerçevesi v1.0 · açık kullanıcı talimatı.

Bulgu defteri ürünün omurgasıdır: her aşamada kullanıcı bulgu ekleyebilir, bulgular
rapora akar. Bugün kod tabanında kalıcı bir bulgu defteri **yoktur** (`storage/finding_store.py`
mevcut değildir). En yakın parçalar geçici kalite bulguları, sızıntı denetimi bulguları ve
kolon açıklamasının `semantic_metadata` içinde kalıcılaşmasıdır; hiçbiri şemanın
beş alanlı bulgu varlığını karşılamaz.

Bulgu varlığı: **soru · yöntem · sonuç · yorum · seçim gerekçesi.** Her bulgu ayrıca veri
sürümü, filtre/bağlam ve parametrelerle bağlıdır. Bağ olmadan bulgu yazılamaz; bağ kaydedilen
kayıttan türetilir.

Tek kayıt sistemi kuralı korunur: bulgular **mevcut `ProjectStore` durumuna** yazılır. İkinci
bir proje deposu, ikinci bir yetenek kaydı, ikinci bir provenance günlüğü veya ayrı bir bulgu
dosyası oluşturulmaz. Yazma mevcut atomik yayın protokolüne (`ProjectStore.save`, ACTIVE
commit) uyar.

Güncellik: veri sürümü, filtre/bağlam veya parametre değiştiğinde eski bulgu **"güncel
değil" olarak işaretlenir**; hiçbir bulgu sessizce güncellenmez veya örtük olarak yeniden
bağlanmaz. İşaret, bulgunun kendi kaydında tutulan bağ ile o anki aktif bağın karşılaştırılmasıyla
belirlenir; karşılaştırma hesaplanır, elle yazılmaz.

Yüzey kararı (B-02, kullanıcı kararı 2026-11-13): **alta çekmece.** Çekmece her aşamada
erişilebilir ve görünür kalır; aşamanın sağ panelini veya çalışma alanını işgal etmez. Bir
ekranın "tek belirgin ana eylemi" kuralı korunur: çekmece birincil eylem değil, yardımcı
kalıcı yüzeydir. "Bulgu defterine ekle" eylemi her aşamanın kendi yüzeyinde bulunur ve
bulgunun o aşamanın bağını (veri sürümü + kapsam + parametreler) doldurur; ekleme işlemi
kullanıcının o aşamadaki mevcut sonucunu değiştirmez, veri yazmaz.

Raporla akışı: Bulgu defteri birincil rapor işlevidir. Tanımlı bulguların tamamı raporun
"Bulgular" bölümüne **gerekçesiyle** taşınır; hiçbir bulgu sessizce düşmez. Rapor öncesi
kontrol, "güncel olmayan sonuç" uyarısını ve eksik açıklama (yöntem, birim, örneklem)
denetimini bu kayıtlara dayandırır.

Gizlilik: bulgu metni serbest kullanıcı metnidir ve proje kaydına yazılır. Secret yalnız
sistem keyring'inde tutulur; bulgu metnine yazılan gizli değerler kayıtta kalır ve bu
kapsam dışındadır — kullanıcıya "bulgu metnini gözden geçirin" uyarısı gösterilir.
Redaksiyon ve paylaşım, mevcut gizlilik/paylaşım yollarında ve bulgu metnine uygulanır.

Geri alınabilirlik: bir bulgunun silinmesi kullanıcının açık eylemidir ve onay ister; silme
işlem geçmişinde kayıt altındadır. Proje kaydı, bulgu kaydı ve rapor kaydı ayrı dosyalarda
tutulmaz.

Bu ADR kodu tanımlar; uygulama Faz B'de `storage/finding_store.py`, `ui/findings.py` ve
`FindingDrawer.qml` ile yapılır ve odaklı testlerle kanıtlanır.
