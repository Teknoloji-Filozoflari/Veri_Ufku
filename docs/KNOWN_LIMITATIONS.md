# Bilinen sınırlamalar

Yalnız Linux x86_64 Flatpak yolu seçildi. Debian/Pardus, native Xorg ve farklı GPU/sürücü birleşimleri test edilmeden destek garantisi yoktur. Yerel CachyOS üzerinde temiz Flatpak uygulama/runtime kurulumu, temiz bir dağıtım VM'i yerine geçmez. Flatpak'ın ve masaüstü portal hizmetinin hostta bulunması gerekir.

Tek uygulama .flatpak dosyası KDE runtime içermez. İnternetsiz çalışma ile internetsiz kurulum ayrı doğrulanır. AppImage ertelendi; glibc tabanı belirlenmeden destek iddiası yoktur. İnsan kullanıcı ve gerçek yardımcı teknoloji kabulleri Faz25 kapsamında açıktır. Qt GC uyarısı önceki kanıtta kayıtlıdır.

Faz21 zaman serisi, Faz22 yerel metin, Faz23 tarif/izleme kullanıcının seçtiği deneysel kapsamdır; sessizce ertelenmedi. Harici dil modeli, çevrimiçi servis, GPU ML ve doğrulanmamış algoritmalar bu adayın kapsamında değildir. Tüm capability durumları REQUIREMENTS_MATRIX.md ana kaydındadır.

Faz59: bounded native offline recommendation; full catalog yalnız geçmişte gözlenen
ürünlerdir. Content sabit numeric/as-of metadata; ALS küçük CPU; query-group LTR ayrı
binary top-K değerlendirme. Sampled/full metrics karşılaştırılamaz; future-only/seen
relevant paydada kalır. Servis/otomatik kullanıcıya gönderme yok; score probability değil.
Salted export pseudonym anonimlik garantisi değildir. [Kanıt](evidence/PHASE59.md).

Faz60 native bounded:5000row/2000entity/64item/32activity, max5itemset/24period.
Conformance yalnız açık activity-adjacency dili; Petri concurrency/token replay/alignment
yok. Cohort observation bounds kullanıcı beyanı; incomplete period NA, missing trace
unknown. Çoklu rule keşfi FDR/significance veya causality kanıtı değil.
[Kanıt](evidence/PHASE60.md),[sözleşme](adr/061-patterns-phase60.md).

Faz61:256node/2000edge bounded graph, GraphML/GEXF static flat subset. Mixed/dynamic/
hierarchy/ports/hyperedge/viz reddi; attribute değerleri declared text. Community
undirected strength/unweighted; explicit parallel simple projection. Link prediction/
network embedding mevcut değil. View-only filter/sample; full IDs export hassas olabilir.
Repeated-import GUI2GiB toplam heap kapısı açık; [E61](evidence/PHASE61.md).

Faz62 bounded local stream/prequential/checkpoint ve özel development hedefleri: [kanıt](evidence/PHASE62.md).129şer seçilmiş source/wheel core,350byte-eşit paket; GUI explicit4GiB fixture ayrı,default2GiB kapısı açık. PU/broker/live tail ve özel hedef fitted-model prediction yok. Faz63 başlamadı.

Faz63 bounded numeric GUI profile Python/SQLite subset/notebook ve explicit fresh process: [kanıt](evidence/PHASE63.md).142şer seçilmiş core,355byte-eşit package; arbitrary code OS sandbox değildir. Managed Jupyter unavailable, yalnız harici notebook opsiyonel; önceki resmî/2GiB longheap açıkları korunur. Faz64 başlamadı.

Faz74: ayrı worker environment provisioning/routing, tam temiz makine offline
installer ve genel local extra/model-weight kurucusu mevcut değil. Metadata import
ortam kurmaz; hash update planner uygulamaz ve publisher authentication değildir.
App rollback şema göçünü geri almaz; ayrı kapalı proje yedeği gerekir.
[Gerçek Flatpak/Pardus/Debian/CachyOS/Arch/GPU matrisi](evidence/PHASE74.md#e74-platform).
