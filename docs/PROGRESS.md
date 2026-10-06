# Veri_Ufku — temel ilerleme

Ana kayıt [REQUIREMENTS_MATRIX](REQUIREMENTS_MATRIX.md). Tarih 2026-10-06. Bu özet aynı durum/olgunluk/kapsam alanlarını yansıtır; checker çelişkiyi hata yapar.

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
| 09 | başlanmadı | mevcut değil | zorunlu | REQUIREMENTS_MATRIX.md:F09 |
| 10 | başlanmadı | mevcut değil | zorunlu | REQUIREMENTS_MATRIX.md:F10 |
| 11 | başlanmadı | mevcut değil | zorunlu | REQUIREMENTS_MATRIX.md:F11 |
| 12 | başlanmadı | mevcut değil | zorunlu | REQUIREMENTS_MATRIX.md:F12 |
| 13 | başlanmadı | mevcut değil | zorunlu | REQUIREMENTS_MATRIX.md:F13 |
| 14 | başlanmadı | mevcut değil | zorunlu | REQUIREMENTS_MATRIX.md:F14 |
| 15 | başlanmadı | mevcut değil | zorunlu | REQUIREMENTS_MATRIX.md:F15 |
| 16 | başlanmadı | mevcut değil | zorunlu | REQUIREMENTS_MATRIX.md:F16 |
| 17 | başlanmadı | mevcut değil | zorunlu | REQUIREMENTS_MATRIX.md:F17 |
| 18 | başlanmadı | mevcut değil | zorunlu | REQUIREMENTS_MATRIX.md:F18 |
| 19 | başlanmadı | mevcut değil | zorunlu | REQUIREMENTS_MATRIX.md:F19 |
| 20 | başlanmadı | mevcut değil | zorunlu | REQUIREMENTS_MATRIX.md:F20 |
| 21 | başlanmadı | mevcut değil | isteğe bağlı | REQUIREMENTS_MATRIX.md:F21 |
| 22 | başlanmadı | mevcut değil | isteğe bağlı | REQUIREMENTS_MATRIX.md:F22 |
| 23 | başlanmadı | mevcut değil | isteğe bağlı | REQUIREMENTS_MATRIX.md:F23 |
| 24 | başlanmadı | mevcut değil | zorunlu | REQUIREMENTS_MATRIX.md:F24 |
| 25 | başlanmadı | mevcut değil | zorunlu | REQUIREMENTS_MATRIX.md:F25 |
| 26 | başlanmadı | mevcut değil | zorunlu | REQUIREMENTS_MATRIX.md:F26 |
| 27 | başlanmadı | mevcut değil | zorunlu | REQUIREMENTS_MATRIX.md:F27 |

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
