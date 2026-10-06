# Veri_Ufku — temel ilerleme

Ana kayıt [REQUIREMENTS_MATRIX](REQUIREMENTS_MATRIX.md). Tarih 2026-10-06. Bu özet aynı durum/olgunluk/kapsam alanlarını yansıtır; checker çelişkiyi hata yapar.

| Faz | Durum | Olgunluk | Kapsam | Kayıt |
|---|---|---|---|---|
| 00 | doğrulandı | kararlı | zorunlu | REQUIREMENTS_MATRIX.md:F00 |
| 01 | doğrulandı | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F01 |
| 02 | doğrulandı | deneysel | zorunlu | REQUIREMENTS_MATRIX.md:F02 |
| 03 | başlanmadı | mevcut değil | zorunlu | REQUIREMENTS_MATRIX.md:F03 |
| 04 | başlanmadı | mevcut değil | zorunlu | REQUIREMENTS_MATRIX.md:F04 |
| 05 | başlanmadı | mevcut değil | zorunlu | REQUIREMENTS_MATRIX.md:F05 |
| 06 | başlanmadı | mevcut değil | zorunlu | REQUIREMENTS_MATRIX.md:F06 |
| 07 | başlanmadı | mevcut değil | zorunlu | REQUIREMENTS_MATRIX.md:F07 |
| 08 | başlanmadı | mevcut değil | zorunlu | REQUIREMENTS_MATRIX.md:F08 |
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

Kullanıcı tema, Tab gezinmesi ve F1 yardım kontrolünü başarılı bildirdi (F02-USER-SHELL, ENV-USER-02, 2026-10-06). Faz02 uzak CI sonucu bekleniyor.
