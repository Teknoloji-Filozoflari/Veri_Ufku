# Veri_Ufku — temel ilerleme

Kullanıcı logo seçimi — 2026-10-08: UI-BRANDING ortak görsel kapsam doğrulandı/deneysel/zorunlu.
Veri Bağları v2/02 ana/örnek pencere, Qt simgesi, Linux kullanıcı menüsü/hicolor,
HTML/PDF rapor ve README'ye yerleştirildi. 347 test ve kurulu wheel smoke geçti.
[Ana kabul kaydı](REQUIREMENTS_MATRIX.md), [gerçek kanıt ve masaüstü sınırları](evidence/UI_BRANDING.md).
Bu görsel düzeltme yeni faz başlatmaz; faz durumları değişmedi.

Ana kayıt [REQUIREMENTS_MATRIX](REQUIREMENTS_MATRIX.md). Güncel tarama 2026-10-08 Europe/Istanbul: [Faz00–13 denetimi](evidence/AUDIT_00_13.md). Bu özet aynı durum/olgunluk/kapsam alanlarını yansıtır; checker çelişkiyi hata yapar. Gerçek kullanıcı testleri kullanıcının talimatıyla taramadan sonraya bırakıldı; F13-S005 doğrulanmadı. Aşağıdaki faz teslim paragrafları teslim tarihindeki durumu kaydeder; güncel durum tablodadır.

2026-10-11 DEC-39-01: Faz39 teknik teslimi tamamlandı: masaüstü dashboard canvas,
sürüm/filtre bağlı dört widget, global/local filtre, açık kaynak eşleme, brushing,
drill-down/save/reopen; vektör/raster composer ve ağsız yerel HTML. 12 teknik
kayıt; gerçek kaynak ve kurulu wheel QML/export kanıtı. Resmî durum sürüyor /
deneysel / zorunlu; önceki insan/AT/donanım/dağıtım kabulleri ve DEP-28-GATE açık.
[Hafıza](PROJECT_STATE.md), [kanıt](evidence/PHASE39.md).

| Faz | Durum | Olgunluk | Kapsam | Kayıt |
|---|---|---|---|---|
| 00 | doğrulandı | kararlı | zorunlu | REQUIREMENTS_MATRIX.md:F00 |
| 01 | doğrulandı | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F01 |
| 02 | doğrulandı | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F02 |
| 03 | doğrulandı | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F03 |
| 04 | doğrulandı | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F04 |
| 05 | doğrulandı | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F05 |
| 06 | doğrulandı | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F06 |
| 07 | doğrulandı | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F07 |
| 08 | doğrulandı | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F08 |
| 09 | doğrulandı | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F09 |
| 10 | doğrulandı | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F10 |
| 11 | doğrulandı | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F11 |
| 12 | doğrulandı | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F12 |
| 13 | sürüyor | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F13 |
| 14 | sürüyor | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F14 |
| 15 | sürüyor | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F15 |
| 16 | sürüyor | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F16 |
| 17 | sürüyor | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F17 |
| 18 | sürüyor | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F18 |
| 19 | sürüyor | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F19 |
| 20 | sürüyor | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F20 |
| 21 | sürüyor | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F21; PHASE21 teknik kapılar geçti; önceki insan/bağımlılık kabulü açık |
| 22 | sürüyor | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F22; teknik kapılar geçti PHASE22.md; önceki insan/bağımlılık kabulü açık |
| 23 | sürüyor | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F23 |
| 24 | sürüyor | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F24; ENV-24 teknik ölçüm; minimum donanım/cold OS açık |
| 25 | sürüyor | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F25; PHASE25 teknik denetim; insan/AT kabulü açık |
| 26 | sürüyor | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F26; PHASE26 güvenilirlik incelemesi |
| 27 | sürüyor | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F27 |

Faz00 belge ve plan kabulü doğrulandı; F00-001..017 ve F00-S001..S007 kanıtı docs/evidence/PHASE00.md. Faz01 çalışan QML uygulaması, kilitli paket, CPU/I/O manager, güvenli log, çeviri ve yerel CI kontrolleri uygulandı; 32 test geçti. [Faz01 kanıtları](evidence/PHASE01.md). Kullanıcı normal masaüstünde CPU/I/O ve belirsiz ilerleme iptal/tamamlanmasını denedi (F01-USER-OPEN/JOBS). Kullanıcı kalan yapılandırma/eski sonuç, hata ve aktif görevde kapanış kontrollerini de başarılı bildirdi (F01-USER-STALE/ERROR/CLOSE); F01-DESKTOP ve F01-S005 doğrulandı. GitHub CI koşusu 37500721689, commit 603d54a7aae24da275b8a777b93a8d86066b1599 için linux job112396721151 üzerinde 28 saniyede başarıyla tamamlandı; sistem kitaplıkları, kilitli kurulum, belge/artefact, lint, çekirdek/başsız test ve kurulu giriş noktası smoke geçti. F01-CI-REMOTE ve F01-S006 doğrulandı; Faz01 kabulü tamamlandı, olgunluk deneysel. Analitik/import/proje kaydı henüz mevcut değil. Minimum donanım ve offline dağıtım kabulü açık kalır.

Faz02 gerçek QML kabuğu ve ortak tokenlar uygulandı: sekiz alanın kullanılabilirlik açıklaması, başlangıç amaçları, tema/görünüm/yazı boyutu kalıcılığı, sağ bilgi paneli ve klavye gezinmesi. [Faz02 kanıtları](evidence/PHASE02.md): başsız ve gerçek Wayland GUI, küçük/büyük pencere ve %100–200 yazı ölçeği, 37 test. UI-REF-VIS beş resmî görselin gerçekten incelenmesiyle doğrulandı. Faz02 doğrulandı/deneysel/zorunlu; Faz03 ve sonrası başlamadı. Veri açma/örnek veri eylemleri henüz mevcut değil; UI bunu açık gösterir.

Kullanıcı tema, Tab gezinmesi ve F1 yardım kontrolünü başarılı bildirdi (F02-USER-SHELL, ENV-USER-02, 2026-10-06). Faz02 uzak CI koşusu [37504698665](https://github.com/Teknoloji-Filozoflari/Veri_Ufku/actions/runs/37504698665), linux işi112410240655 üzerinde 36 saniyede başarıyla tamamlandı (F02-CI-REMOTE, ENV-CI-02). Faz02 kabul kaydı tamamlandı; olgunluk deneysel.

Faz03 çevrimdışı öğrenme uygulandı/doğrulandı/deneysel: 13 sürümlü Türkçe makale, üç açıklama derinliği, bağlama bağlı F1 paneli, arama/kategori/dokuz kavram sözlüğü ve isteğe bağlı atomik yerel okundu/yer imi. Uygulamada dene yalnız gerçek yardım aramasını ayrı geçici örnek öğrenme projesinde açar. [Kanıt](evidence/PHASE03.md): 54 test, başsız ve gerçek Wayland GUI, her modda11 ekran; CI yardım bağı doğrulayıcısı eklendi. Faz03 uzak CI [37511231471](https://github.com/Teknoloji-Filozoflari/Veri_Ufku/actions/runs/37511231471) linux işi112432592915 üzerinde38 saniyede başarılı (F03-CI-REMOTE, ENV-CI-03). Kullanıcı ayrı örnek öğrenme penceresinin açıldığını ve küçük örneği gördüğünü doğruladı (F03-USER-EXAMPLE, ENV-USER-03, 2026-10-06); diğer manuel yardım kontrolleri henüz bildirilmedi. Bu Faz03 kabul kaydı sırasında Faz04 başlamamıştı.

Faz04 proje deposu ve gerçek QML akışları uygulandı: SQLite + şema1 manifest + gerektiğinde gerçek Parquet; kaynak referansı/kopyası, yeniden bağlama ve sonuç veri sürümleri; ACTIVE yayın noktası, ayrı AUTOSAVE, dirty kapanış, salt okunur ikinci örnek ve kontrollü eski kilit kurtarma. [Kanıt](evidence/PHASE04.md): yerel Btrfs/başsız Qt, 30 gerçek SIGKILL senaryosu, iki süreç ve iki Qt pencere, şema0 fixture migrasyonu. Ağ/sync klasöründe dayanıklılık, gerçek yeni masaüstü/native dosya seçici ve yeni remote CI doğrulanmadı. Faz04 doğrulandı/deneysel/zorunlu; Faz05 başlamadı.

Faz04 kullanıcı bildirimi: kendi kullanıcı klasöründe oluştur/aç/isim değişikliği kaydet/kapat geçti (F04-USER-PROJECTS, ENV-USER-04); native seçici ve diğer manuel akışlar ayrı açık. Yanlış proje yolundaki genel hata açıklayıcı mesajlara ayrıldı; Klasör seç ve diyalog içinde hata/düzeltme akışı eklendi (F04-FIX-PATH). [Kayıt](evidence/PHASE04.md#e04-path-fix).

Faz05 CSV/TSV sihirbazı, değişmez kopyadan ortak preview/full parser, türler/karantina, UUID kimlikler ve şema2 atomik yayın uygulandı. Yerel parser/proje/Qt ve kurulu wheel kontrolleri geçti; gerçek native/remote/minimum donanım ayrı açık. [Kanıt](evidence/PHASE05.md). Faz06+ başlamadı.

Faz05 kullanıcı temel CSV/kaydet/yeniden aç akışını başarılı bildirdi (F05-USER-ROUNDTRIP, ENV-USER-05, 2026-10-06). Native seçim/bırakma yöntemi, tür/karantina/iptal kontrolleri ayrıca kullanıcı tarafından bildirilmedi. [Kayıt](evidence/PHASE05.md#e05-user-roundtrip).

Faz06 JSON/JSONL/NDJSON/XLSX/Parquet adaptörleri uygulandı/doğrulandı/deneysel. Ortak worker/snapshot/yayın; ayrı JSON flatten/list açma; bounded makrosuz OOXML ve native Parquet tür koruma; manifest3/migration. 188 pytest ve9 unittest, check_docs/artifacts/learning, Ruff, entry smoke, kurulu Linux wheel dört format/yeniden açma geçti. [Kanıt](evidence/PHASE06.md). Native masaüstü/minimum donanım/remote CI ayrı doğrulanmadı. Faz07 başlamadı.

Faz07 tablo/profil/rol uygulandı/doğrulandı/deneysel: 206 pytest,9 unittest, kilitli belge/artefact/yardım/Ruff/entry smoke, kurulu Linux wheel import/sayfa/profil/metadata roundtrip. 100.000 kayıt16 sayfa ve kaynak hash kontrolü; [kanıt](evidence/PHASE07.md). Bu Faz07 kaydı sırasında Faz08 başlamamıştı.

Faz07 kullanıcı tablo açma/yenileme işlemini başarılı bildirdi (F07-USER-TABLE, ENV-USER-07, 2026-10-06). Diğer manuel akışlar ayrıca bildirilmedi. [Kayıt](evidence/PHASE07.md#e07-user-table).

Faz08 kalite merkezi uygulandı/doğrulandı/deneysel: 212 pytest,9 unittest, belge/artefact/yardım/Ruff/entry smoke ve kurulu Linux wheel100.000 kayıt kalite/örneklem/iptal/rapor roundtrip geçti. Tarama kaynak/dataset değiştirmez; bilgi önerileri çalıştırma eylemi üretmez. Yeni masaüstü/minimum donanım ayrı doğrulanmadı; uzak CI37532581621 başarısı kullanıcı bildirimiyle kayıtlı. Faz09 başlamadı. [Kanıt](evidence/PHASE08.md).


Faz08 uzak CI (2026-10-06 UTC / 2026-10-07 Europe/Istanbul): [37532581621](https://github.com/Teknoloji-Filozoflari/Veri_Ufku/actions/runs/37532581621), Linux işi112505393392,1m12s, tüm adımlar success. F08-CI-REMOTE / ENV-CI-08; [kanıt](evidence/PHASE08.md#e08-ci-remote).

Faz08 CI commit eşlemesi gh API ile doğrulandı:37532581621 → e9fd13f41afb83daaca1c3790e8dc1e14a58d3cb. Commit mesajında Faz03 yazsa da commit ağacı Faz08 kalite motoru/ekranı/testlerini içeriyor. [Kanıt](evidence/PHASE08.md#e08-ci-remote).

Faz09 uygulandı/doğrulandı/deneysel: tipli OperationSpec1, immutable rename/drop/filter, full preview çıktısının aynı hash kontrollü yayını, şema5 kalıcı heads/redo ve eski sonuç güncelliği. 228 pytest/9 unittest, kilitli kapılar ve kurulu Linux wheel100.000 kayıt işlem/filtre/iptal/undo/redo/reopen geçti. Beş gerçek SIGKILL ve beş yayın fault injection eski veya tam yeni sürümü korudu. Elle düzenleme D-01 seçilmedi; future sort/join/explode/aggregate/dedup yalnız köken sözleşmesi. Yeni kullanıcı masaüstü/remote CI/minimum donanım ayrı doğrulanmadı. [Kanıt](evidence/PHASE09.md). Faz10 başlamadı.

Faz10 uygulandı/doğrulandı/deneysel: dokuz tipli temizlik işlemi, açık yöntem/kayıp/politika, tam veri etki sayımları, güvenli Decimal/tarih/DST ve null/NaN ayrımı. Şema6 kopya dataset, dedup survivor/köken Parquet ve veri bağımlı sızıntı geçmişi; kaynak immutable. 261 pytest/9 locked unittest, gerçek QML/spawn ve kurulu wheel100.000 kayıt preview/apply/undo/redo/reopen geçti. Kullanıcının isteğiyle manuel denemeler ileride toplu yapılacak; yeni masaüstü/remote CI doğrulanmadı. [Kanıt](evidence/PHASE10.md). Bu Faz10 kaydı sırasında Faz11 başlamamıştı.

Faz11 uygulandı/doğrulandı/deneysel: dokuz tipli dönüşüm, izinli AST, üç adımlı join, açık append eşleme ve pivot agregasyonu. Şema7 çoklu immutable giriş ve gerçek kaynak üyelikleri; ODS, salt okunur SQLite, Feather V2/Arrow IPC file/stream. 297 pytest/9 locked unittest, Polars–DuckDB sözleşme fixture'ları, gerçek QML/spawn ve kurulu wheel100.000 kayıt preview/apply/undo/redo/reopen geçti; n:n join200.000 satır/400.000 üyelik. Kaynak değişmedi; hata/iptal ve iki SIGKILL sonrası atomiklik doğrulandı. Manuel kullanıcı denemeleri daha sonra toplu; yeni masaüstü açık, uzak CI kullanıcı kanıtıyla doğrulandı. [Kanıt](evidence/PHASE11.md). Bu Faz11 kaydı sırasında Faz12 başlamamıştı.

Faz11 uzak CI: kullanıcı2026-10-07 tarihinde [koşu37668560670](https://github.com/Teknoloji-Filozoflari/Veri_Ufku/actions/runs/37668560670), Linux işi112954058877,2m29s ve tüm adımların success sonucunu bildirdi. F11-CI-REMOTE/ENV-CI-11 [kanıtı](evidence/PHASE11.md#e11-ci-remote); uzak commit bağımsız doğrulanmadı, manuel masaüstü kabulü açık.


Faz12 uygulandı/doğrulandı/deneysel: yedi grafik ve kesin istatistik özeti, tür/rol/amaç önerileri, açık örnekleme/Diğer/null/çift n; kalıcı ChartSpec ve tam RowId üyelikleri.320 pytest/9 locked unittest, gerçek QML/Matplotlib pointer/drag zoom/reset ve kurulu Linux wheel100k her tür PNG/SVG/save/reopen geçti. İki grafik SIGKILL ve ikinci süreç readonly yayın reddi sağlam ACTIVE'yi korudu. Yeni kullanıcı masaüstü/native picker/uzak CI/minimum donanım ayrı açık; manuel denemeler daha sonra toplu. [Kanıt](evidence/PHASE12.md). Faz13 başlamadı.

Faz13 mevcut özellikler GUI'de bağlandı; CSV/JSON/JSONL/Parquet/XLSX, yerel HTML/PDF, isteğe bağlı rehber, iki sentetik CC0 örnek ve paket DejaVu font. Source ve Linux wheel/fresh-XDG offline çalışma teknik denemeleri geçti; kayıt/tür/yeniden açma ve temizlik geçmişi korundu. [Kanıt](evidence/PHASE13.md), [release](RELEASE_NOTES_0_1_0.md). Faz13 sürüyor/deneysel/zorunlu: F13-S005 gerçek bilgisiz kullanıcı görev tamamlama/yardım/kritik hata ölçümü yok; geliştirici walkthrough'u kullanıcı testi değildir. Faz14 başlanmadı.

Kullanıcı görsel düzeltmesi: sağ üstte yalnız tema ve başlangıç/gelişmiş simgeleri; yazı boyutu sabit. Eski ölçek kanıtları tarihsel kayıt olarak korunur; güncel doğrulama [UI_HEADER](evidence/UI_HEADER.md).

Sol menü görsel düzeltmesi: sekiz özgün ortak çizgi simgesi,184px menü,44px sola hizalı düğmeler; planlanan alan açıklaması kaldırıldı. [Gerçek Qt kanıtı](evidence/UI_NAVIGATION.md).

Koyu tema revizyonu: katmanlı antrasit yüzeyler, sıcak turuncu ana eylem/seçim ve sakin alan simge renkleri. [Teknik/görsel kayıt](evidence/UI_DARK_THEME.md).

Son kullanıcı talimatıyla yalnız turuncu vurgulu koyu tema; tema düğmesi kaldırıldı. Eski açık/sistem kayıtları uygulanmaz; sağ üst yalnız seviye simgeleri. [Güncel doğrulama](evidence/UI_DARK_ONLY.md).

Güncel tema: mor işlemler, mint öğren/yardım, turkuaz veri/grafik, turuncu ana dosya/kayıt; yalnız koyu tema. Logo sonraya bırakıldı. [Doğrulama](evidence/UI_MULTICOLOR.md).


Faz14, 2026-10-08: açık kullanıcı talimatıyla beş soru yolu/11 SciPy yöntemi uygulandı; anahtarla kişi eşleştirme, varsayım onayı, eksik dışlama, etki/CI sınırları, kayıtlı düzeltme ailesi ve çevrimdışı yardım. Teknik F14-S001..006 ve yöntem kabul kayıtları ayrı doğrulandı. Faz13 F13-S005 gerçek kullanıcı görevi açık olduğundan bağımlılık kabulü tamamlanmadı; Faz14 durum sürüyor, olgunluk deneysel. Kullanıcı talimatı bu fazın uygulanmasına izin verir, önceki kullanıcı testine sahte başarı vermez. Bu Faz14 kaydı sırasında Faz15 başlatılmamıştı. [Kanıt](evidence/PHASE14.md).

Faz14 nihai yerel doğrulama:389 pytest/9 locked unittest; son arayüzden sonra42 istatistik testi; source/noneditable wheel11 yöntem+100k tam kapsam+iptal+save/reopen/resave+F1.89 çevrimdışı makale/53 bağ. SistemPython3.14.7 unittest başarısız ayrı kaydedildi. Faz13 gerçek kullanıcı bağımlılığı açık; yeni uzak CI veya fiziksel masaüstü başarı iddiası yok. [Gerçek kayıt](evidence/PHASE14.md).

Faz15 açık talimatla uygulandı: ayrı Model hazırlığı ekranı, dört amaç için tam kaynak uygunluk/geçmiş raporu, eğitim katına bağlı fit edilmemiş plan, gerçek temiz kaynak seçimi, kolon eşlemesi, kaydet/aç ve içerik16 yardım. Teknik kanıt [PHASE15](evidence/PHASE15.md); Faz13 F13-S005 insan kabulü açık olduğundan faz sürüyor/deneysel. Faz16 başlatılmadı.

Faz15 nihai yerel kontrol:419 pytest/9 locked unittest; docs/artifacts/learning/Ruff format/check ve giriş noktası smoke geçti.96 makale/56 UI bağ; source ve noneditable Linux wheel dört amaç, geçmiş kaynak/relocate,100k, kayıt/aç/F1/iptal/eski plan doğrulandı. Fit yok; insan kabulü/uzak CI ve minimum donanım ayrı açık. [Kanıt](evidence/PHASE15.md).

2026-10-08 kullanıcı görsel düzeltmesi: Başlangıç sadeleştirildi, Proje başlığı, metin yolu olmadan klasör seçimi, ortak koyu FolderPicker, yalnız isim gösteren recents ve kompakt UiButton. Yeni faz başlamadı; faz durumları aynı. [Kanıt](evidence/UI_HOME_COMPACT.md).

Faz16 teknik split/fold/baseline uygulandı: random/stratified/group/time/group_time, training-only Pipeline ve ayrı final test/proje geneli defter. Paket/kaynak, iptal/eski/failed, gerçek SIGKILL/readonly, copy/reopen/farklı kaydet ve100k kanıtı [PHASE16](evidence/PHASE16.md). Faz13 insan/Faz15 bağımlılık kabulü açık olduğu için sürüyor/deneysel/zorunlu; teknik satırlar matriste ayrı. Faz17 başlatılmadı.

Faz17 açık kullanıcı kapsamıyla uygulandı: gerçek baseline/doğrusal/Ridge/RandomForest, geliştirme CV MAE seçimi, birimli MAE/RMSE ve negatif/sabit R², validation/final tahmin-artık grafikleri, dondurulmuş final aday ve Faz16 test defteri/keşifsel retune. Kaynak korunur, train-only fit, dar ayar/maliyet/iptal/hata sınırları. Teknik kabul [PHASE17](evidence/PHASE17.md); önceki insan/bağımlılık kabulü açık: sürüyor/deneysel. Bu Faz17 kaydı sırasında Faz18 başlatılmamıştı.

Faz17 nihai yerel doğrulama:469 pytest,9 locked unittest;49 regresyon/Faz16 odaklı test; kaynak/noneditable Linux wheel240 bağımsız+combined,20k Forest ve100k doğrusal aday, iki final test ve reopen;99 çevrimdışı makale/63 UI bağı. Sistem Python3.14 eksik paket discovery başarısızlığı ayrı kayıtlı. Yeni insan/uzak CI kabulü iddia edilmez. [Kanıt](evidence/PHASE17.md).

2026-10-08 kullanıcı arayüz düzenlemesi: Başlangıç yardım ve ara rehber/dosya/örnek satırları kaldırıldı; Veri bilimi yol haritası başlığı; üst gelişmiş yanında uygulama kapatma simgesi; son projeler yatay sarılan düğmeler. Bütün tik kutuları ortak oval UiCheckBox; tek FolderPicker geri/üst simgeleri ve üzerine yazmayan yeni klasör oluşturma. Örnek projeler Öğren ekranında aynı seçiciye bağlı. Faz/olgunluk/kapsam değişmedi. [Gerçek kontrol](evidence/UI_HOME_REFINEMENT.md).

2026-10-08 kullanıcı yol haritası düzenlemesi: Veri Bilimi Yol Haritası on numaralı kıvrılan aşama, açılabilir alt başlıklar ve yalnız etkileşim/ilk görünüş animasyonlarıyla sunulur. Genişte iki yana, darda tek sütuna yerleşir; alt yollar mevcut ekranlara bağlı, planlanan araçlar pasiftir. İçerik20/home.roadmap çevrimdışı yardım mevcut home makalesinde. Yeni faz veya analitik capability başlamadı. [Gerçek kayıt](evidence/UI_SCIENCE_ROADMAP.md).

2026-10-09 — Kullanıcının Öğren düzenlemesi: yol haritasına uygun aşama/alt başlık ağacı, aramada konum korunması, ortalanmış okuma penceresi ve sağlanan Veri.md metninin çevrimdışı anlatımı. Yeni analitik faz başlatılmadı; Faz17 durumu/olgunluğu değiştirilmedi. Kanıt: `docs/evidence/UI_LEARNING_TREE.md`; insan masaüstü kabulü ayrıca beklenir.

2026-10-09 — Öğren ikinci düzenlemesi: üst örnek/rehber satırları ve istenmeyen düğmeler kaldırıldı; numaralı merdiven kartları; Veri yalnız kullanıcı Markdown başlıklarıyla düzenlendi; Proje alanı başlangıç yol haritasının sonuna taşındı.107 çevrimdışı makale,85 öğrenme ağacı konusu/22 bağlamsal konu. Faz17 durumu ve olgunluğu değişmedi; insan kabulü ayrıca beklenir. Kanıt: `docs/evidence/UI_LEARNING_REFINEMENT.md`.

2026-10-09 — Kaynak açıklamaları varsayılan kapalı/tıklamayla açık; kullanıcı metninden genel analiz ve beş yaklaşım başlığı/anlatımı.113 çevrimdışı makale/91 Öğren konusu; mevcut analiz araçları kapsamı/faz/olgunluk değişmedi. Kuralcı başlığın okunabilmesi yeni optimizasyon yeteneği değildir. Kanıt: `docs/evidence/UI_LEARNING_ANALYSIS.md`.

2026-10-09 — Ortak Başlangıç/Öğren yol haritası; Başlangıç başlığı işlem ekranını açar, ayrı ok alt işlemleri açar. Temizlik/JOIN/dönüşüm ve model alt bölümlerine yönlendirme; Öğren açıklama akışı. Temizleme metni kodlar hariç sekiz anlatım olarak eklendi;121 makale/99 konu. Yeni analitik faz/algoritma yok; Faz17 durum/olgunluk değişmedi. Kanıt: `docs/evidence/UI_SHARED_ROADMAP.md`.


2026-10-09 kullanıcı Veri sayfası düzenlemesi: üst içe aktarma kartı, dört ortak yol haritası eylemi, Veri içeriği/sütun açıklamaları ve Veriyi oku ve incele bölümleri. Faz durumu/olgunluğu değişmedi; UID-01..03 kayıtları [matriste](REQUIREMENTS_MATRIX.md), geliştirici kanıtı [UI_DATA_CONTENT](evidence/UI_DATA_CONTENT.md). İnsan masaüstü kabulü ayrıca açık.

Faz18 açık kapsamıyla uygulandı: Baseline/LogisticRegression/RandomForest, ikili/çok sınıflı hedef, pozitif sınıf/dağılım, matris/per-class/averaging/ROC-PR, validation eşiği ve dondurulmuş final karar. Sınıf/eşik/model ayar geçmişi, final tekrarları ve proje dışı bilinmezlik görünür. Kaynak değişmez; resampling yok. Teknik kayıt [PHASE18](evidence/PHASE18.md); sürüyor/deneysel/zorunlu, insan/önceki bağımlılık kabulü açık. Faz19+ başlatılmadı.

Faz18 nihai yerel doğrulama:502 pytest/9 locked unittest,75 odaklı test; source/noneditable Linux wheel ikili/çok sınıflı ve combined240,20k Forest/100k Baseline-Logistic, iki final kullanım/retune/reopen.126 çevrimdışı makale/70 UI bağı; docs/artifacts/learning/Ruff/entry smoke geçti. Sistem Python51 keşif/42 eksik bağımlılık import hatası ayrı başarısız. Yeni insan/uzak CI/minimum donanım kabulü yok. [Kanıt](evidence/PHASE18.md).

Faz19 açık kullanıcı kapsamıyla uygulandı: iki ayrı etiketsiz yol, gerçek KMeans/DBSCAN ve IsolationForest/tek sütun IQR; ölçüm/ölçek/sınır/seed/tam fit sürümü, kontrollü silhouette ve kayıpsız işaretli yeni dataset. DBSCAN predict yok; güvenli yeni dosya uygulaması Faz20 kapsamında henüz mevcut değil. Teknik kanıt [PHASE19](evidence/PHASE19.md); önceki insan/bağımlılık kabulü açık: sürüyor/deneysel/zorunlu. Faz20+ başlamadı.

Faz19 nihai yerel doğrulama:531 pytest/9 locked unittest;44 odaklı hesap/depo/GUI/yardım testi. Kaynak/noneditable Linux wheel dört yöntem240, KMeans/IsolationForest/IQR100k ve DBSCAN3k; tüm satırlı yeni dataset/RowId/kaynak hash/kayıt/aç ve143 paket kaynak byte eşleşmesi.131 makale/75 UI bağı; docs/artifacts/learning/Ruff/entry smoke geçti. Sistem Python53 keşif/44 eksik bağımlılık import hatası ayrı başarısız. İnsan/uzak CI/minimum donanım kabulü yok. [Kanıt](evidence/PHASE19.md).

Faz20 yarım kalan model yaşam döngüsü uygulaması tamamlandı: fitted model kartı, dar güvenli paket ve yeni veri önizleme/tahmin yolu. Teknik kabul [PHASE20](evidence/PHASE20.md); önceki insan/bağımlılık kabulü açık olduğundan sürüyor/deneysel/zorunlu. Faz21 daha sonraki açık kullanıcı seçimiyle başlatıldı.

Faz20 son odaklı35 test; kaynak/noneditable Linux wheel regresyon+sınıflandırma6/100k yeni dosya, batch127/RowId/orijinal kolon ve kaynak koruması, paket kaydet/aç ve kalıcı proje reopen geçti.136 makale/81 UI bağı ve172 paket dosyası kaynak byte eşleşmesi. Standart kapılar ve sistem Python eksik bağımlılık başarısızlığı [PHASE20](evidence/PHASE20.md) kaydında ayrı; insan/uzak CI/minimum donanım kabulü verilmedi.

Faz20 nihai genel kontrol:566 pytest/200.22s ve9 kilitli unittest geçti; locked sync/check_docs/check_artifacts/check_learning/Ruff check-format/kaynak ve kurulu wheel entry smoke exit0. Sistem Python55 keşif/46 eksik bağımlılık import hatası ayrı başarısız kayıt. [Nihai kanıt](evidence/PHASE20.md).


Faz21 açık kullanıcı seçimiyle ayrı zaman serisi yolu olarak uygulandı: düzen/DST/agregasyon
kontrolleri, geçmiş trend/mevsim/pencere, gerçek naive/seasonal-naive ve sınırlı
ExponentialSmoothing, rolling-origin ve saklı final defteri. [Gerçek teknik kabul](evidence/PHASE21.md):
583 tam regresyon, üç son ETS kontrolü dahil35 hedefli test,9 locked unittest,
100000 kayıt kaynak/kurulu wheel ve installed entry smoke geçti. Sistem Python
bağımlılık eksikliği ayrı başarısız kayıttır. Önceki insan/bağımlılık kabulü açık: sürüyor/deneysel/zorunlu.
Faz22 başlatılmadı.

Faz22 sonraki açık kullanıcı seçimiyle uygulandı: yerel metin incelemesi, Türkçe/Unicode,
eğitim fold TF-IDF sınıflandırması ve ayrı kosinüs benzerliği. Teknik kabul
[PHASE22](evidence/PHASE22.md): 597 pytest, 26 hedefli test; kaynak ve kurulu wheel
120/100000 satır, TCP engelli iş akışı ve kurulu giriş noktası geçti. Önceki insan/
bağımlılık kabulü açık olduğundan sürüyor/deneysel/zorunlu. Faz23 başlamadı.

Faz23 açık kullanıcı seçimiyle uygulandı: declarative tarif, açık kaynak/kolon
eşleme, tüm adımlar dry-run ve tek atomik yayın; betimsel drift, ayrı model
uygulama/yeniden eğitim ve kimlikle sonradan hedef performansı. Teknik kabul
[PHASE23](evidence/PHASE23.md); insan/bağımlılık kabulü açık: sürüyor/deneysel/zorunlu.
Faz24 başlatılmadı.

Faz23 nihai teknik doğrulama: 618 pytest,56 hedefli ve9 kilitli unittest;
kaynak/kurulu wheel120–100000 kayıt, atomik batch/SIGKILL, no-fit model ve120
kimlikli sonradan hedef performansı; entry smoke/hash eşitliği geçti. Sistem
Python bağımlılık eksikliği başarısızlığı ayrı kayıttır. [PHASE23](evidence/PHASE23.md).

## Faz24 — mevcut yolların ölçümü

Üç sınıf/yedi aşama zaman-RSS benchmark, bounded page cache/kolon projection,
model maliyet öngörüsü, native thread/toplam kaynak bütçesi ve iptal/staging
temizliği uygulandı. F24-S006 minimum donanım/cold OS/physical latency açık;
önceki insan/bağımlılık kabulü korunur. [Kanıt](evidence/PHASE24.md). Faz25 başlamadı.

## Faz25 — kalan teknik kullanılabilirlik denetimi

2026-10-09 UTC / 2026-10-10 Europe/Istanbul: mevcut Faz25 işi devam talimatıyla
sürdürüldü. Ortak erişilebilir adlar, boş tabloda Tab çıkışı, dinamik seçicide
odak koruma, büyük yazıda menü satır kaydırma, temel İngilizce ve bağımsız
parse tercihleri; katalog34 yardım/jargon incelemesi ve beş gerçek klavye
senaryosu. [Gerçek kanıt](evidence/PHASE25.md). İnsan/Orca/AT-SPI kabulü ve
önceki bağımlılık açık: sürüyor/deneysel/zorunlu. Faz26 başlatılmadı.

Faz25 nihai teknik kontrol:637 pytest/9 locked unittest; kaynak ve kurulu
wheel beş klavye senaryosu, yüksek DPI/font render, yardım/çeviri/erişilebilir
adlar ve installed entry smoke geçti. Sistem Python bağımlılık eksikliği
unittest başarısızlığı ayrı kayıttır. [PHASE25](evidence/PHASE25.md).

## Faz26 — veri bütünlüğü ve güvenilirlik incelemesi

Açık kullanıcı Faz26 talimatıyla sentetik güvenlik/kurtarma/migration/atomiklik
ve bilimsel referans denetimi teknik olarak tamamlandı. Log ve SQLite link koruması,
ODS kodlanmış XML/bütçe denetimi, şema4–6 açılışı ve commit bağlı kurtarma
önizlemesi eklendi. [Gerçek kayıt](evidence/PHASE26.md); önceki insan/AT
ve bağımlılık kabulü açık olduğundan sürüyor/deneysel. Faz27 başlatılmadı.

Faz26 nihai teknik doğrulama:695 pytest/9 locked unittest,262 hedefli kontrol;
15 inceleme alanı ve20 gerçek kesilme noktası JUnit'e bağlı. Şema/log/ODS/
SQLite/kurtarma/timer altı bulgu kapatıldı; kaynak/noneditable wheel OS ağsız
beş yol+kurtarma/büyük-font/iptal ve199 paket byte eşleşmesi geçti.
Sistem Python65/56 import hata başarısızlığı ayrı kayıttır. [PHASE26](evidence/PHASE26.md).
Faz27 başlatılmadı; önceki insan/AT/bağımlılık kabulü açık.


Faz27 kullanıcı talebiyle durduruldu. Önceki Flatpak seçimi son talimatla iptal edildi; .deb/AppImage/rpm/Snap/Nix ve Windows11 x64 ZIP kapsamı henüz kabul edilmiş paket değildir. Üretim/temiz hedef/kurulum kabulü açık kalır; UI çalışması bu fazı yeniden başlatmaz.

Kullanıcı veri ekranı düzenlemesi: ayrı ilk kullanım rehberi girişi kaldırıldı; Başlangıç yol haritası araçlara, Öğren aynı aşamalardaki açıklamalara gider. Veri sayfası kapalı başlıklarla açılır: import, tüm sütunların profili, değerler, describe, notlar, kayıt tablosu ve kalite. [Gerçek kayıt](evidence/UI_DATA_INSPECTION.md); faz kabulü/olgunluğu artırılmaz.

2026-10-10 veri ekranı devam çalışması: UDI-07 görünür klavye seçimi,
Enter/Space ile sütun değerleri, Tab çıkışı ve boş tablo koruması eklendi.
Önceki belge/katalog/klavye kontrol hataları düzeltildi. Nihai704 pytest,
9 kilitli unittest, beş klavye senaryosu, kaynak/noneditable wheel sekizer
ekran ve kurulu giriş noktası geçti;203 paket dosyası kaynakla eşleşti.
Sistem Python unittest59 import hatası ayrı başarısız kayıttır; insan/AT
kabulü açık kalır. [Kanıt](evidence/UI_DATA_INSPECTION.md#udi-continuation).
Faz durumları değişmedi; Faz27 durdurulmuş olarak kalır.


2026-10-10 kullanıcı UI düzenlemesi: sayfa sağ üstündeki genel yardım kaldırıldı; Veri bölümleri açıklamalı numaralı kartlara çevrildi; import temel/Gelişmiş ayrımı ve projeye koşullu Başlangıç yönlendirmesi uygulandı. UIS-01..03 ana kayıtları ve [kanıt/sınırlar](evidence/UI_IMPORT_SIMPLE.md). Faz durumları ve yetenek olgunluğu değişmedi.

2026-10-10 UIS-03 kullanıcı düzeltmesi: proje yokken dosya alanını gizleme hatası giderildi. Dosya seç/bırak ve önizleme proje açmadan çalışır; aktarım düğmesi görünür ve yazılabilir proje/önizleme hazır olduğunda etkinleşir. Proje oluştur / aç yalnız açık proje yokken gösterilir. [Kanıt](evidence/UI_IMPORT_SIMPLE.md#project-visibility-fix).


2026-10-10 UDR-01..04: görev yardım düğmesi kaldırıldı; import önizlemesi20 kayıt; yeni CSV/TSV aktarımlarında tüm dosya üzerinden güvenli otomatik tür algılama; Veri profili tam veri üstünde otomatik sütun başlığı/tür tablosu ve üç üst bilgi; değer listesinde başlık/alternatif satır/tekrar rozetleri. [Kanıt ve sınırlar](evidence/UI_DATA_REFINEMENT.md). Faz/olgunluk/kapsam değişmedi; eski kayıtlı veriler otomatik dönüştürülmedi.

2026-10-10: Açık kullanıcı profil düzeltmesi UPT-01/02: eski beş sütun düzeni ve tam sayı algılama; eski metin snapshot içerik türü ayrı gösterilir. Faz ilerletilmedi; doğrulama UI_PROFILE_TYPES kaydında. [Kanıt](evidence/UI_PROFILE_TYPES.md).

UPT-01/02 doğrulaması: tam regresyon711 başarılı/1 kaynak-hash belge hatası; son ekten sonra17 GUI testi başarılı. [Gerçek kayıt](evidence/UI_PROFILE_TYPES.md).

2026-10-10 son kullanıcı gösterim isteği: profil tablosu ve üst tür özetinde teknik tür adları (Int64/String/Decimal…) kullanılır. İçerik türü hücrede tek başına; farklı fiziksel kayıt türü tooltip içinde açıklanır. Veri dönüşümü yapılmaz. [Güncel kanıt](evidence/UI_PROFILE_TYPE_LABELS.md).

2026-10-10 son saklama talebi önceki içerik türü gösterimini geçersiz kıldı: profil yalnız gerçek physical_type gösterir; aktarımda Int64/Decimal fiziksel olarak saklanır. Titanic mevcut aktif sürümü kullanıcı izniyle mevcut convert operasyonu üzerinden dönüştürüldü; kaynak, satır kimlikleri ve geri alma geçmişi korunur. [Gerçek kayıt](evidence/UI_ACTUAL_STORAGE.md).

2026-10-10 profil tür özeti her fiziksel türü ayrı satırda sayı ve ilgili sütun adlarıyla gösterir: Int64:4 — sütunlar. Uzun adlar sarılır, plain text korunur. Kullanıcının data_info.png referansı gerçekten incelendi. [Kanıt](evidence/UI_PROFILE_TYPE_COLUMNS.md).

2026-10-10 kullanıcı kısa not isteği: Anlam ve notlar ayrı Veri başlığı olmaktan çıktı, profil tablosunun altına sütun seçimi/kısa açıklama/Notu kaydet alanı taşındı. Her sütunun taslağı seçimler arasında korunur; açık kayıt projeyi kalıcı kaydeder. applyDescription mevcut rol/birim/sıra/analiz birimi ve confirmed durumunu korur; yeni not role önerisini onaylamaz. Analitik profil onaylanmamış rolün yerine mevcut öneri politikasını kullanır. Kaynak/snapshot/RowId değişmez. [Kanıt](evidence/UI_PROFILE_NOTES.md).

UPT-06:41 ilk ilgili test başarılı; tam712/2 koşusundaki rol uyumluluğu hatası düzeltildi ve26 son ilgili test geçti. Kaynak/hash belge hatası sürer; tam koşu yeniden başarı diye etiketlenmez. Geniş/dar not ekranları incelendi. [Kayıt](evidence/UI_PROFILE_NOTES.md).

2026-10-10 sade veri akışı: import Gelişmiş alanı tüm seviye tercihlerinde ve yeniden girişte kapalıdır; kullanıcı tıklayarak açar. Profil not girişinin üstünde yalnız açıklaması olan sütunlar ad/açıklama biçiminde kompakt, plain-text ve220px bounded listede görünür. Verini tanı altında inventory/describe/unique/sütun profili GUI çağrıları sample=false; ilk10.000 seçicileri kaldırıldı, tam veri hesabı ve200 değer görüntü sayfası ayrı tutulur. [Kanıt](evidence/UI_COMPACT_NOTES_FULL_DATA.md).


Faz28 açık kullanıcı talimatıyla denetlendi: mevcut teknik yollar ve eski proje uyumu gerçek regresyon/GUI üzerinden yeniden kontrol edildi. Temel faz kabulleri değiştirilmedi; F13/F24/F25/F27 giriş açıkları nedeniyle profesyonel Faz28 engelli. [Denetim](evidence/PHASE28.md), [profesyonel özet](PRO_PROGRESS.md).

Faz29 kullanıcı “faz 29 bitir önce” DEC-29-01 teknik geçiş istisnasıyla uygulandı; önceki kabul kapıları açık kalır. [Profesyonel ilerleme](PRO_PROGRESS.md), [gerçek kanıt](evidence/PHASE29.md). Faz30 başlamadı.

2026-10-10 Faz29 devamı: dar pencere modül keşfi taşması düzeltildi;
724 pytest,14 kilitli unittest, kaynak/kurulu wheel gerçek GUI ve import,
izole giriş smoke ve208 paket dosyası eşitliği doğrulandı.
[Son kanıt ve başarısız denemeler](evidence/PHASE29.md#e29-continuation).
Önceki insan/AT/donanım/dağıtım kabulü açık; faz durumu değişmedi.

Faz30 açık kullanıcı talimatıyla başlatıldı (DEC-30-01). Mevcut adaptör/worker/atomik yayın yolunda format başına küçük native ve metadata fixture, gerçek QML/spawn/reopen çalışmaları yürütülüyor. Önceki faz kabulleri değişmedi; [profesyonel kayıt](PRO_PROGRESS.md), [kanıt](evidence/PHASE30.md). Faz31 başlamadı.

2026-10-11 Faz30 devamı: kesilen final regresyon ve belge kapanışı yeniden
yürütüldü; güncel noneditable wheel on format/QML/spawn/kaydet/reopen,
dokuz10005 kayıt bounded preview/iptal, eski CSV ve kurulu entry kontrollerini
geçti;211 paket dosyası kaynakla eşleşti. F30-S001..004 ve
F30-P001..013 teknik tanıkları matrise işlendi.
Büyük SAS dosyası ölçümü açık;
önceki insan/AT/donanım/dağıtım kapıları açık. Faz30 sürüyor/deneysel/zorunlu;
Faz31 başlamadı. [Güncel sonuçlar ve sınırlar](evidence/PHASE30.md#e30-continuation).


2026-10-11 Faz30 yarım kalan teknik teslim tamamlandı: 761 pytest,
14 kilitli unittest; on format kaynak/noneditable wheel native metadata ve
reopen; her adaptörde F1/Escape ve beş çevrimdışı konu; dokuz10005 kayıt
preview/iptal; 211 paket dosyası byte eşitliği ve izole kurulu giriş
smoke geçti. F30-S001..004/F30-P001..013 ana matrise gerçek C/V/G/H/P
witness'larıyla bağlandı. Sistem Python62 import hatası ayrı başarısız;
SAS büyük fixture ölçümü ve önceki insan/AT/donanım/dağıtım kabulü açık.
Faz30 sürüyor/deneysel/zorunlu; Faz31 başlamadı.
[Nihai teknik kanıt](evidence/PHASE30.md#e30-continuation).


2026-10-11 DEC-31-01: kullanıcı yalnız Faz31 bağlantı kaynaklarını açıkça seçti.
PostgreSQL/HTTP ilk dilim; MySQL/MariaDB/DuckDB/S3 ayrı adaptör ve gerçek
sentetik sunucu yolları. Aynı registry/worker/ProjectStore kullanılır;
source key/tutarlılık ve Secret Service referansı kalıcı, secret kaydı yok.
İlk32 gerçek connector testi ardından nihai regression ve wheel kontrolleri
[PHASE31](evidence/PHASE31.md#e31-final) altında tamamlandı.
Faz31 sürüyor/deneysel/zorunlu; önceki kabul açıkları korunur; Faz32 başlamadı.


2026-10-11 Faz31 nihai teknik teslim: 795 pytest,34 odaklı connector ve
14 kilitli unittest; PostgreSQL18.6/MySQL8.4.11/MariaDB13.0.2/DuckDB1.5.6,
HTTPS ve SeaweedFS4.48 gerçek kaynak/QML/spawn/keyring/native/reopen yolları
geçti. 218 wheel dosyası kaynakla eşit; optional client paketleri olmadan
OS ağsız core smoke geçti. F31-S001..005/P001..008 matriste ayrı C/V/G/H/P
witness'larına bağlandı. Sistem Python65 import hatası ve temiz offline cache
eksikliği ayrı başarısız kayıttır. Önceki insan/AT/donanım/dağıtım kapıları
açık; Faz31 sürüyor/deneysel/zorunlu, Faz32 başlamadı.
[Nihai kanıt](evidence/PHASE31.md#e31-final).


2026-10-11 DEC-32-01: Faz32 teknik teslimi tamamlandı; F32-S001..005/
P001..008 C/V/G/H/P kanıtları doğrulandı. Tam816 pytest, son22 faz testi,
64 ilgili regresyon,14 kilitli unittest; kaynak/kurulu wheel altı gerçek akış,
12 render ve221 byte-eşit paket dosyası. Faz32 sürüyor/deneysel/zorunlu;
önceki insan/AT/donanım/dağıtım kabul açıkları korunur. Faz33 başlamadı.
[Gerçek kayıt ve sınırlar](evidence/PHASE32.md).


2026-10-11 DEC-33-01: Faz33 teknik tamamlandı;17 madde teknik doğrulandı, resmî faz sürüyor/deneysel/zorunlu. Son36 Faz33 testi ve source/wheel14 gerçek GUI case/12 render/224 dosya doğrulandı. Full regresyon ve son kapı sayıları [Faz33](evidence/PHASE33.md) içinde gerçek çıktılara bağlıdır. Önceki resmî kabul açıkları korunur; Faz34 başlatılmadı.

2026-10-11 DEC40-01: İstatistiksel model/tanılama teknik teslimi;17 kayıt.
Resmî Faz40 sürüyor/deneysel/zorunlu; önceki resmî kapılar açık.
[Kaynak/wheel/backend kanıtı](evidence/PHASE40.md). Faz41 başlatılmadı.

2026-10-11 DEC41-01: teknik tamamlandı; resampling/robust/aile/duyarlılık;15 teknik kayıt,
1229 passed/19skip tam regresyon,61faztesti,source/wheel80 ilgili test.
Resmî Faz41 sürüyor/deneysel/zorunlu; önceki kabuller açık.
[Gerçek kanıt](evidence/PHASE41.md). Faz42 başlatılmadı.

2026-10-11 DEC42-01: ilk kapsam teknik tamamlandı: bağımsız iki randomize kol ve ölçüm/örneklem planı;
8 teknik kayıt,1276 passed/19skip full,47faztesti. Resmî Faz42 sürüyor/deneysel/zorunlu; varyant/sequential alt işleri kapalı, önceki kabuller açık. [Gerçek kanıt](evidence/PHASE42.md). Faz43 başlamadı.

2026-10-14 DEC56-01:10 bounded CPU teknik kayıt;241source/241wheel core,18şer focused,17GUI/regression,4şer actualflow ve1şer finalcaption,312byte-eşit package. GPU unvalidated/kapalı; resmî kabul ayrı. [Kanıt](evidence/PHASE56.md). Faz57 başlatılmaz.

Faz57 açık talimatla bounded yerel görüntü/CPU teknik teslim; ana kayıt PRO_PROGRESS ve REQUIREMENTS_MATRIX. [Kanıt](evidence/PHASE57.md); resmî kapılar korunur.

Faz58 bounded native ses; STT gerçek yerel model olmadan doğrulanmış değildir. [Kanıt](evidence/PHASE58.md), ana kayıt REQUIREMENTS_MATRIX ve PRO_PROGRESS.

Faz64 DEC64-01: bounded typed DAG source/transform/quality/analysis/train/predict/export, aynı GUI/CLI worker ve batch/sweep/dry-run. [Kanıt](evidence/PHASE64.md), [sözleşme/CLI kullanımı](adr/065-typed-workflow-phase64.md). Schedule mevcut değil; resmî kabul ayrı, önceki kapılar korunur. Faz65 başlatılmaz.

Faz65 DEC65-01 açık talimat: kayıtlı source/dataset/operation/analysis/model/report lineage, reference-only veya explicit data-inclusion safe bundle ve sınırlı exact/numeric verifier. [Kapsam/kanıt](evidence/PHASE65.md), [sözleşme](adr/066-reproducibility-phase65.md). Geçmiş provenance uydurulmaz; genel row traversal/model rerun yok; önceki resmî kapılar ayrı, Faz66 başlatılmaz.

Faz66 DEC66-01: ortak process/native thread bütçesi, ölçüm paneli, bounded yerel optional Dask; remote executor/GPU runtime unavailable. [Kapsam ve gerçek kanıt](evidence/PHASE66.md). Faz67 başlatılmaz.

Faz67 DEC67-01: bounded yerel drift/kalite/delayed-label monitoring, shadow/gerçek rollback, CLI scoring ve ayrı opt-in loopback API. [Kapsam ve kanıt](evidence/PHASE67.md). Resmî kabul ayrı; Faz68 başlatılmaz.


Faz68 açık talimatıyla sınırlı CPU simulation/optimization teknik çalışması; [gerçek kapsam ve kanıt](evidence/PHASE68.md). Önceki resmî açıklar korunur; Faz69 başlamaz.


Faz69 açık talimatıyla ayrı workspace içinde10bounded CPU ders/8yol ve otomatik learning coverage; [gerçek kapsam/kanıt](evidence/PHASE69.md). Resmî önceki açıklar korunur.


Faz70 açık talimat: kayıtlı sonuçlardan bounded bilimsel rapor/preset/MD/HTML/PDF/ZIP; explicit review/export, stale uyarısı ve offline yardım. [Gerçek kapsam/kanıt](evidence/PHASE70.md). Önceki resmî açıklar korunur.


Faz71 açık talimatıyla bounded yerel review/share/diff/yeni fork; üç inclusion modu, source kimliği ve version-bound checklist. [Gerçek kapsam/kanıt](evidence/PHASE71.md). Önceki resmî açıklar korunur.

Faz72 açık talimatıyla bounded PII adayları/insan kararı, redaction, standard HMAC/Fernet, retention/scratch cleanup ve kaynak PII lineage ilişkileri uygulandı. [E72](evidence/PHASE72.md): live keyring doğrulanmadı, DP/canlı proje encryption yok; önceki resmî kabuller korunur.

Faz73 açık talimatıyla versioned plugin SDK, manifest-only inspect, explicit trust/env/hash run ve safe archived result. Gerçek stat GUI örneği; tüm native tür entegrasyonları tamamlandı sayılmaz. [E73](evidence/PHASE73.md).
