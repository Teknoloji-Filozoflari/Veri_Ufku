# SCHEMA_CONTRACT — Veri_Ufku şema sözleşmesi

**Sürüm:** 1.1 · 2026-11-13 · Faz A + B + C
**Kaynak şema:** `veri_ufku_sema.pdf` (7 aşama · 61 alt başlık · çekirdek/modül ayrımı)
**Yürütme çerçevesi:** `veri_ufku_sema_gelistirme_promtu.md` v1.0
**Kod eşlemesi:** [SCHEMA_MAP.md](SCHEMA_MAP.md)
**Kararlar:** [ADR076](adr/076-schema-single-source.md) · [ADR077](adr/077-finding-notebook-spine.md) · [ADR078](adr/078-mod1-mod2-contract.md)

Bu belge **kod değiştirmez**. Şemadaki her alt başlığın kod tabanındaki karşılığını tek satırda
tanımlar. Kod yolu şemaya uydurulur; şema değişmeden kod taşınmaz. Şemada olup kodda
bulunmayan alt başlık uydurulmaz — "yok" veya "eksik" olarak işaretlenir.

## Durum sözlüğü

| Durum | Anlamı |
|---|---|
| `var` | Alt başlığın tanımladığı davranış uçtan uca çalışır ve testle kanıtlanmıştır. Katalog satırı tek başına kanıt sayılmaz. |
| `eksik` | Davranışın bir parçası çalışır, şemanın istediği bütünlük sağlanmamıştır. Eksik parça bu satırda açıkça yazılır. |
| `yok` | Kod tabanında karşılığı yoktur. Uydurulmuş karşılık, boş buton veya sahte sonuç yazılmaz. |

**Çekirdek / Modül** sütunu şemanın kendi ayrımıdır ve kodla değiştirilmez. Bir alt başlık
şemada Modül ise kodda çekirdek olarak çalışabilir; bu durum **Çelişkiler** bölümünde yazılır.

## Özet

| Durum | Adet |
|---|---|
| `var` | 53 |
| `eksik` | 6 |
| `yok` | 1 |
| **Toplam** | **61** |

Aşama dağılımı:

| Aşama | Alt başlık | var | eksik | yok |
|---|---|---|---|---|
| Veri | 10 | 8 | 2 | 0 |
| İncele | 5 | 5 | 0 | 0 |
| Görselleştir | 12 | 11 | 1 | 0 |
| Hazırla | 9 | 6 | 2 | 1 |
| İstatistik | 8 | 7 | 1 | 0 |
| Model | 10 | 9 | 1 | 0 |
| Raporla | 7 | 6 | 0 | 1 |
| **Toplam** | **61** | **53** | **6** | **1** |

---

## Veri (10 alt başlık)

| # | Alt başlık | Çekirdek/Modül | Durum | Gerekçe |
|---|---|---|---|---|
| V-01 | Proje | Çekirdek | `var` | Proje oluştur/aç/kaydet gerçek komutlarla çalışır; proje klasörü veri, işlem ve raporu birlikte tutar (`ui/projects.py`, `storage/project_store.py`). |
| V-02 | Kaynak seçimi | Çekirdek | `var` | Yerel dosya seçme/bırakma, biçim algılama ve bağlantı kaynağı gerçek `capture` çağrısına gider (`ui/imports.py`, `importers/registry.py`). |
| V-03 | Okuma ayarları ve önizleme | Çekirdek | `var` | Ayraç, başlık satırı, kodlama, ondalık ve null işareti ayarları gerçek önizlemeye uygulanır (`importers/delimited.py`). |
| V-04 | Tür ve rol atama | Çekirdek | `var` | Sütun türü elle atanır, hedef/kimlik rolü sürümlü metadata olarak yazılır (`ui/dataset.py`, `operations/contracts.py`). |
| V-05 | Eksik değer eşleştirme | Çekirdek | `eksik` | Okuma zamanı null işareti ayarı var; ancak şemanın istediği **sütun bazında eşleştirme yüzeyi** Veri aşamasında kalıcı değil — kalıcı karşılaştırma Hazırla'da. "0 geçerli değerdir" kuralı doğru uygulanıyor, `999`/`-1` otomatik eksik sayılmıyor. |
| V-06 | İçe aktarma kontrolü | Çekirdek | `eksik` | Satır/sütun doğrulaması ve bozuk satır karantinasi var; ancak ayrı bir **tespit/kontrol yüzeyi** yok, kontrol `imports.ready` kapısına indirgenmiş. **Kişisel veri uyarısı (isim/e-posta/kimlik no) hiçbir yerde üretilmiyor.** |
| V-07 | Veri sürümü | Çekirdek | `var` | Kaynak → v1 → hazırlanmış sürüm zinciri, hash izleme ve geri alma kökeni projede saklanır (`storage/project_store.py`, `storage/lineage.py`). |
| V-08 | İlk bakış | Çekirdek | `var` | Onay kapısı sonrası satır/sütun sayısı, tür dağılımı ve ilk satırlar gerçek hesapla doldurulur (`analytics/inspection.py`). |
| V-09 | Kaynak adaptörleri | Modül | `var` | PostgreSQL/MySQL/MariaDB/DuckDB/HTTP/S3 bağlantıları ve tablo listeleme gerçek çalışır (`importers/connectors.py`); yüzey "Gelişmiş → Connector" altındadır (bkz. Ç-01). |
| V-10 | Özel kaynaklar | Modül | `var` | GeoJSON/NetCDF/Zarr/HDF5 gibi özel formatlar gerçek okunur, eklenti SDK'sı özel içe aktarıcı sözleşmesini çalıştırır (`plugins/sdk.py`, `importers/advanced.py`). |

## İncele (5 alt başlık)

| # | Alt başlık | Çekirdek/Modül | Durum | Gerekçe |
|---|---|---|---|---|
| I-01 | Tablo ve sütunlar | Çekirdek | `var` | Salt okunur tablo, arama, sıralama, görünüm filtresi ve sütun envanteri gerçek; seçim projeye yazılmaz (`ui/dataset.py`). |
| I-02 | Temel özet | Çekirdek | `var` | Ortalama/medyan/çeyrekler/std ve tür dağılımı gerçek hesaplanır (`analytics/inspection.py`). |
| I-03 | Eksik veri | Çekirdek | `var` | Eksik bulguları tarama sonucundan gelir; "silersem etki" önizlemesi satır sayısıyla hesaplanır, uygulama yapmaz (`analytics/quality.py`). |
| I-04 | Kalite kontrolleri | Çekirdek | `var` | Tekrar eden satır, geçersiz değer, sabit sütun vb. kontroller gerçek çalışır; bulgular projeye kaydedilebilir (`analytics/quality.py`). Aykırı adaylar IQR · dayanıklı z · klasik z olarak listelenir ve karar Hazırla'da verilir. |
| I-05 | Özel veri türleri | Modül | `var` | Görüntü/ses/metin/zaman serisi/mekânsal panelleri gerçek denetleyicilere bağlıdır (`modeling/vision.py`, `modeling/audio.py`, `analytics/text.py`). |

## Görselleştir (12 alt başlık)

| # | Alt başlık | Çekirdek/Modül | Durum | Gerekçe |
|---|---|---|---|---|
| G-01 | Soru odaklı öneri | Çekirdek | `var` | Amaç + kolon semantiğinden grafik önerisi gerçek hesaplanır, tıklanınca tür/eksen atanır (`charts/engine.py`). |
| G-02 | Grafik açıklama paneli | Çekirdek | `var` | "Ne görüyorum / nasıl yorumlarım / neye dikkat / sonraki adım" cümleleri hesaplanan sayılardan üretilir (`ui/chart_explain.py`). |
| G-03 | Dağılım ve eksikler | Çekirdek | `var` | Histogram, kutu, KDE, ECDF, QQ ve eksiklik deseni gerçek üretilir (`charts/distributions.py`). |
| G-04 | Karşılaştırma ve oran | Çekirdek | `var` | Sütun/çubuk karşılaştırma, yüzde/stacked bar ve payda politikası gerçek (`charts/composition.py`). |
| G-05 | Zaman ve olay sırası | Çekirdek | `eksik` | Zaman ekseni (line, alan, stacked area, takvim, zaman tablosu) gerçek; **olay sırası için ayrı görselleştirme yüzeyi yok** — olay sayımı `funnel` altında, desenler Model aşamasında. |
| G-06 | İlişki ve çok değişen | Çekirdek | `var` | Scatter, regresyon çizgisi, korelasyon ısı haritası, pair/hexbin/yoğunluk gerçek (`charts/multivariate.py`). |
| G-07 | Dağılım ve oran (ileri) | Modül | `var` | Violin, rug, strip, swarm, P–P, dalga-yaprak, nokta matrisi, Marimekko, Pareto, waterfall, funnel, hedef gerçek. |
| G-08 | İlişki ve zaman (ileri) | Modül | `var` | Joint plot, hexbin, 2B yoğunluk, bubble, paralel koordinatlar, Venn, akım, Gantt, mum/OHLC gerçek. |
| G-09 | Hiyerarşi ve akış | Modül | `var` | Treemap, sunburst, daire paketleme, Sankey, alluvial, paralel setler gerçek. |
| G-10 | Ağ ve bağlantılar | Modül | `var` | GraphML/GEXF içe aktarma, derece/PageRank/bileşen/kısa yol/komünite analizleri gerçek (`modeling/graphs.py`). |
| G-11 | Dizi ve coğrafya | Modül | `var` | NetCDF/Zarr/HDF5 dizi okuma + array heatmap/profil ve nokta/choropleth/yoğunluk/raster grafikleri gerçek (`importers/arrays.py`, `geo/charts.py`). |
| G-12 | Metin ve ileri seçenekler | Modül | `var` | Kelime bulutu, radar, nüfus piramidi, radyal, gül ve metin frekans yolları gerçek (`analytics/text.py`). |

## Hazırla (9 alt başlık)

| # | Alt başlık | Çekirdek/Modül | Durum | Gerekçe |
|---|---|---|---|---|
| H-01 | Eksik veri | Çekirdek | `var` | Satır/sütun silme, eksik bayrağı sütunu ve doldurma (sabit/ortalama/medyan/mod) gerçek çalışır; etki sayımı ve geri al destekli (`operations/cleaning.py`). |
| H-02 | Aykırı değerler | Çekirdek | `var` | Tut / işaretle / kaldır / sınırla / dönüştür yolları gerçek; önce/sonra etki önizlemesi mevcut (`analytics/outliers.py`). |
| H-03 | Sütun temizliği | Çekirdek | `var` | Metin kırpma, tür/tarih dönüştürme, kategori eşleme gerçek (`operations/cleaning.py`). |
| H-04 | Kalite düzeltmeleri | Çekirdek | `var` | Tekrar eden satır kaldırma, geçersiz değer düzeltme, İncele bulgularını "Hazırla'ya taşı" taslak akışı gerçek. |
| H-05 | Yeni sütun üret | Çekirdek | `var` | Güvenli formülle hesaplanan sütun, metin bölme, tarih parçası, oran/fark, aralıklara bölme gerçek (`operations/formula.py`, `operations/relational.py`). |
| H-06 | Tablo birleştirme ve şekil | Çekirdek | `var` | Append/join/pivot/unpivot gerçek; anahtar benzersizliği, eşleşmeyen satır raporu ve çoktan çoğa uyarısı uygulanır. |
| H-07 | Özel veri türleri | Modül | `yok` | Hazırla'da özel tür dönüşüm paneli **bilinçli olarak boş bırakılmış**; yalnız "bu sürümde yok" notu var. Görüntü/ses/metin/zaman/mekânsal dönüşümleri ayrı modül yollarında değil, tür panellerinde dağınık durumda. |
| H-08 | Öğrenilen dönüşümler | Çekirdek | `eksik` | **Mod 1 gerçek**: öğrenilen doldurma/tür dönüşümleri tüm veriye uygulanır ve yeni sürüm üretir. **Mod 2 yalnız uyarı metni**: train-only fit yok, öğrenilen dönüşüm Model aşamasında tüketilmiyor (bkz. Ç-05). |
| H-09 | Uygula ve kayıt | Çekirdek | `var` | Önizleme → "Uygula ve kaydet" yeni veri sürümü ve işlem geçmişi üretir; geri alma önceki sürüme dönüş, sürüm zinciri silinmez (`ui/operations.py`). |

## İstatistik (8 alt başlık)

| # | Alt başlık | Çekirdek/Modül | Durum | Gerekçe |
|---|---|---|---|---|
| İ-01 | Dağılım ve normallik | Çekirdek | `eksik` | Dağılım özeti, çarpıklık/basıklık ve QQ/PP grafikleri var; **hiçbir normallik testi yok** (Shapiro-Wilk/Anderson bulunmuyor). QML bunu dürüstçe "desteklenmiyor" diye ilan ediyor. |
| İ-02 | İlişki ölçüleri | Çekirdek | `var` | Pearson/Spearman + ki-kare/Fisher ilişki ölçüleri p ve güven aralığıyla uçtan uca çalışır. |
| İ-03 | Hipotez testi | Çekirdek | `var` | Welch t, eşleştirilmiş t, Mann-Whitney, Wilcoxon, ANOVA, Welch ANOVA, Kruskal-Wallis, ki-kare, Fisher + post-hoc düzeltme açık hipotezle çalışır. |
| İ-04 | Etki büyüklüğü ve belirsizlik | Çekirdek | `var` | Cohen d ve eşdeğerleri, eta-kare, Cramér V ve güven aralıkları üretilir; CI üretilemediğinde `ci_limitation` ile gerekçelenir. |
| İ-05 | Test öneri kartı | Çekirdek | `var` | Önkontrol sonrası gerekçeli öneri kartı; yöntem p değerine göre seçilmez (`ui/statistics_advice.py`). |
| İ-06 | Regresyon (çıkarım) | Çekirdek | `var` | OLS/WLS/GLM/quantile/mixed/repeated + kovaryans; katsayı, SE, p, CI ve tanılama üretir (`statistics/models.py`). |
| İ-07 | Sağlamlık ve deneme kaydı | Çekirdek | `var` | Bootstrap/BCa, permutation, robust özet, duyarlılık + kalıcı deneme kaydı mevcut (`statistics/resampling.py`, `statistics/experiments.py`). Erişim yolu katalog notundan farklı olsa da yol gerçektir (bkz. Ç-06). |
| İ-08 | İleri istatistik | Modül | `var` | Bayes, nedensel, sağkalım, eksik/örnekleme ve çok değişkenli yollar gerçek çalışır ve testlidir; **katalog metni bayat** (bkz. Ç-02). |

## Model (10 alt başlık)

| # | Alt başlık | Çekirdek/Modül | Durum | Gerekçe |
|---|---|---|---|---|
| M-01 | Hedef ve plan | Modül | `var` | Amaç, hedef sütun, özellik seçimi ve sızıntı kontrolü içeren blueprint planı projeye kaydedilir; bilinçli olarak fit edilmez (`modeling/plan.py`). |
| M-02 | Hazırla'dan devralınanlar | Modül | `eksik` | Taşıma **plan seviyesinde** üretiliyor; ancak aile adaptörü yalnız 8 adım türünü kabul ediyor, taşınmış `outlier_iqr_mark` / `impute_joint` / `missing_indicator` adımları "sessiz atlama yok" hatası veriyor. Sızıntı sertifikası `leakage_certified=False` kalıyor. |
| M-03 | Regresyon (tahmin) | Modül | `var` | CV protokolü ve aile adaptörleriyle bounded eğitim/ölçüm/leaderboard çalışır (`modeling/regression.py`). |
| M-04 | Sınıflandırma | Modül | `var` | Sınıf metrikleri, olasılık, eşik seçimi ve karışıklık matrisi üretilir. |
| M-05 | Kümeleme | Modül | `var` | kmeans/dbscan/agglomerative/gmm/optics/hdbscan + anomali tespiti; silhouette ve karşılaştırma çalışır. |
| M-06 | Boyut azaltma | Modül | `var` | PCA/IncrementalPCA/SVD/NMF/ICA/t-SNE/UMAP + özellik seçimi var; **kod İstatistik modülünde, arayüz Model'de değil** (bkz. Ç-03). |
| M-07 | Doğrulama ve karşılaştırma | Modül | `var` | independent/group/time/group_time protokolü, nested CV, arama/leaderboard, AIC/BIC karşılaştırması çalışır. |
| M-08 | Yorumlama | Modül | `var` | Kayıtlı model paketi üzerinde özellik önemi, SHAP, dilim, adalet ve what-if raporu üretilir. |
| M-09 | Özel veri türü yolları | Modül | `var` | Zaman serisi/sinyal/ağ/ses/görüntü/metin yolları ayrı panellerde gerçek çalışır. |
| M-10 | İleri yollar | Modül | `var` | Sinir ağı, monitoring, senaryo, pattern ve model yaşam döngüsü yolları ileri modda açılır. |

## Raporla (7 alt başlık)

| # | Alt başlık | Çekirdek/Modül | Durum | Gerekçe |
|---|---|---|---|---|
| R-01 | Bulgu defteri | Çekirdek | `var` | Faz B'de kuruldu: beş alanlı bulgu varlığı (`storage/finding_store.py`), her aşamada erişilebilir **alta çekmece** (`FindingDrawer.qml`), "Bulgu defterine ekle" eylemi, veri sürümü değişince **"güncel değil"** işareti ve rapora %100 taşınma. Bulgu tek kayıt sisteminde, mevcut `ProjectStore` durumunda saklanır. |
| R-02 | Rapor yapısı | Çekirdek | `var` | Bölüm blokları (section/note/assumption/table/dictionary/chart/bibliography) kaynak + grafik + tablo bağlarıyla kurulur (`exports/report_builder.py`). |
| R-03 | Rapor öncesi kontrol | Çekirdek | `var` | Hash/freshness/redaction ön-kontrolü ve insan "inceledim" onayı olmadan dışa aktarma kilitli (`storage/report_builder_store.py`). |
| R-04 | Dışa aktar | Çekirdek | `var` | PDF/HTML/Markdown + PNG/SVG/PDF grafik + CSV/Excel/Parquet veri var; Faz C'de **Word (DOCX)** eklendi: bağımlılıksız, yerel OOXML üreticisi (`exports/docx.py`), paket bütünlüğü ve `word/document.xml` varlığı testli. |
| R-05 | Yeniden üretim | Çekirdek | `var` | Profil/işlem/workflow reçetesi + ortam + hash korumalı paket; yeniden açma ve bozulma doğrulaması testli (`exports/repro.py`). |
| R-06 | Gizlilik ve paylaşım | Çekirdek | `var` | PII taraması → insan kararı → redaksiyon → keyring'li paket + retention temizliği ve paylaşım paketi çalışır (`exports/privacy.py`, `exports/share_bundle.py`). |
| R-07 | İleri çıktılar | Modül | `eksik` | Salt okunur inceleme paketi var; **etkileşimli HTML, sunum/slayt ve zamanlanmış rapor için hiçbir kod/kayıt yok**. |

---

## Çelişkiler

Bunlar **kod yolundan şemaya doğru düzeltilecek** sapmalardır. Sıra, güvenlik sırasıdır.

| # | Çelişki | Şema | Kod | Karar |
|---|---|---|---|---|
| Ç-01 | Kaynak adaptörleri ve özel kaynaklar yüzeyi | Veri aşaması kutularında görünür, kurulu değilse "Modül: indir" | Gerçek bağlayıcı yüzey "Gelişmiş → Connector" altında; Veri bloğu yalnız "bu ekranda indirme/kurulum yok" notu basıyor | Faz F'te "Modül: indir" kutusu + manifest sözleşmesi ile hizalanacak |
| Ç-02 | İleri istatistik bayat metni | İleri istatistik Modül altında gerçek bir yol | Bayes/nedensel/sağkalım gerçek çalışır, katalog "bu sürümde desteklenmiyor (Faz40+)" diyor | Faz A sonrası metin düzeltmesi; Faz I'de kapsam genişletmesi |
| Ç-03 | Boyut azartma konumu | Model modülü altında | `statistics/dimensions.py`, Main.qml'de İstatistik bölümüne bağlı | Faz D'de Model alt başlığına taşınacak; önce envanter notu güncellenecek |
| Ç-04 | Regresyon adı çakışması | İstatistik "Regresyon (çıkarım)" · Model "Regresyon (tahmin)" | Katalog notu çıkarımı "Model aracı"na yönlendiriyor, oysa çıkarım kodu `statistics/models.py`'de | Faz D açıklamayı "açıklayıcı/tahmin" ayrımıyla netleştirecek |
| Ç-05 | Mod 2 karşılığı | Mod 2 "model için planla" gerçek bir plan | Hazırla'da yalnız uyarı metni; train-only fit ve tarif yok | Faz E kapsamında gerçek plan/pipeline |
| Ç-06 | Sağlamlık erişim yolu | İstatistik alt başlığı içinde | Yeniden örnekleme ayrı araç altında (`examineTool=6`) | Faz I'de katalog metni erişim yoluna göre düzeltilecek |
| Ç-07 | Hazırla'da özel türler | Modül altında ayrı kutu | Kutu bilinçli olarak boş; davranış dağınık | Faz G/F kapsamında modül sözleşmesiyle açılacak |
| Ç-08 | Hazırla katalog bloğu sayısı | 9 alt başlık | `PrepareCatalogPanel` 10 blok ("Diğer" ve "Uygunluk" şemada yok) | Faz G'de 9 şema kutusuna birebir döndürülecek; ek bloklar gerekçeyle kaydedilecek |
| Ç-09 | Raporla düzeni | 7 işlev birincil | Kaynak-aşamaya göre 8 bölüm birincil | **Faz C'de kapandı:** yedi işlev birincil listedir; kaynak-aşama bölümleri "Rapor yapısı" işlevinin içinde ikincil kaldı |
| Ç-10 | Bulgu defteri yüzeyi | Her aşamada görünür kalıcı yüzey | Yok | **Faz B'de kapandı:** alta çekmece (`FindingDrawer.qml`), çalışma alanı satırı olarak yerleşir ve hiçbir denetimi örtmez |

## Belirsizlik listesi — karar durumu

Kaynak belgenin §8 listesindeki on madde. **Sessizce yorumlanmaz.** Kullanıcı kararı verilmemiş
olanlar "bekliyor" durumunda, kod yazılmadan önce karara bağlanır.

| # | Konu | Karar |
|---|---|---|
| B-01 | "İleri seçenek" rengi | **Bekliyor.** Göstergede var, hiçbir kutuda kullanılmıyor. Önerilen varsayılan: şema rozetleriyle uyumlu kalsın diye kullanılmaya devam eder, ayrı renk tanımlanmaz. |
| B-02 | Bulgu defteri yüzeyi | **Karar verildi (2026-11-13): alta çekmece.** Her aşamada erişilebilir kalıcı yüzey; panel/çekmece ayrımı ADR077'de bağlandı. |
| B-03 | Raporla düzeni | **Karar verildi (2026-11-13): yedi iş birincil sekme.** Kaynak-aşamaya göre bölüm ikincil sekmede kalır. |
| B-04 | Mod 2 çıktısı | **Bekliyor.** Önerilen varsayılan: saklanan bir "tarif" (pipeline) olarak durur, Model aşamasında bir form olarak açılır. Faz E başlamadan karara bağlanmalı. |
| B-05 | "Dizi ve coğrafya" | **Bekliyor.** Önerilen varsayılan: "Tür modülleri: mekânsal" içinde kalır, ayrı modül değil. G-11 kodu zaten bu ayrımı uyguluyor. |
| B-06 | Model alt paketleri | **Bekliyor.** Önerilen varsayılan: temel + keşif çekirdek kurulumda; yorum ve ileri yollar isteğe bağlı. Faz D başlamadan karara bağlanmalı. |
| B-07 | "çizelge" / "kagi" | **Bekliyor.** Önerilen varsayılan: "çizelge" = basamaklı grafik, "kagi" = "kama" (Kagi çizimi). İkisi de çizim motorunda yok; Faz H kapsamında eklenmeli. |
| B-08 | Zamanlanmış rapor | **Bekliyor.** Önerilen varsayılan: gerçek zamanlayıcı yok, "bir sonraki açılışta yenile" yaklaşımı. R-07 kapsamında. |
| B-09 | Korelasyonun yeri | **Bekliyor.** Önerilen varsayılan: İncele'de tarama özeti kalır, ayrıntılı keşif Görselleştir'de (kod zaten böyle). |
| B-10 | Word dışa aktarma | **Bekliyor.** Önerilen varsayılan: DOCX (RTF değil). Faz C kapsamında; bağımlılık eklemeden üretim kararı ADR076 kapsamında kayda geçirilmeli. |

## Aktif faz kapsamı

| Faz | Kapsam | Durum |
|---|---|---|
| A — Yol haritası ve çekirdek sözleşme | Bu belge, [SCHEMA_MAP.md](SCHEMA_MAP.md), ADR076/077/078 | **Teknik tamamlandı** (kod değiştirmez) |
| B — Bulgu defteri omurgası | `storage/finding_store.py`, alta çekmece, "Bulgu defterine ekle" eylemi, "güncel değil" işareti, Raporla'ya akış | **Teknik tamamlandı** |
| C — Raporla hizalama | `ReportCatalogPanel.qml` yedi işlev, kaynak-aşama ikincil bölüm, DOCX dışa aktarma | **Teknik tamamlandı** |

D–J fazları **başlatılmaz**. Bu belgenin tamamını okumak onları başlatma yetkisi değildir.
Teknik teslim kanıtı: [evidence/SCHEMA_ABC.md](evidence/SCHEMA_ABC.md).

## Kanıt ve sınırlar

- Durum tespiti kaynak kod ve mevcut test dosyalarının birebir okunmasıyla yapıldı; katalog
  satırı tek başına kanıt sayılmadı.
- Bu belge kod değiştirmez; `scripts/check_docs.py` kapısı gereksinimleriyle çelişmez.
- Fiziksel masaüstü, gerçek ekran okuyucu, insan kullanıcı kabulü, minimum donanım, temiz-OS
  offline kurulum ve uzak CI koşuları bu fazda **kapanmış sayılmaz**.
