# Veri_Ufku — aktif görev hafızası

2026-10-21 kullanıcı README yenileme ve GitHub gönderimini açıkça istedi.
README ürün amacı/hedef kullanıcı/başlangıç-Öğren-gelişmiş akışı, gerçek ekranlar,
kurulum, yöntem kapsamı ve deneysel sınırlarla yenilendi. Önceki uzun README
yerel /tmp/veri-ufku-readme-before-publication-20261021.md içinde saklandı.
Bu talimat mevcut hazırlanan kaynakların stage/commit/push yetkisini içerir.
Remote origin Teknoloji-Filozoflari/Veri_Ufku; sonuç Git geçmişi ve GitHub CI
üzerinden doğrulanmalı, eski no-push kayıtları önceki görevlerin durumudur.

2026-10-21 GitHub hazırlığı: kullanıcı gereksiz üretilmiş dosya temizliği istedi.
Üç eski builddir ve Windows runtime, Python/test/lint cache silindi; kaynak,
.venv, historical evidence ve arşiv/source cache korundu. .gitignore yerel sır
ve cache alanlarıyla genişletildi. Publish betiği --check salt okunur gate;
LICENSE/packaging/examples/branding açık staging listesi düzeltildi.
[Hazırlık ve gerçek kanıt](GITHUB_PREPARATION.md). Stage/commit/push yapılmadı.

2026-10-17 UI-JOURNEY-01: son açık kullanıcı talimatıyla başlangıç sayfası yeniden
harita→proje sırasına geçti; önceki UI_RENEWAL project-first tercihi artık tarihsel.
Başlangıç eylem başlıkları +6 çalışma rehberi, Öğren aynı10aşama haritası ve
sonunda ek lab; gelişmişte teknik paneller/form-state koruma ve doğrudan erişim.
İlk giriş beginner, son tercih kalıcı; işlem/bütçe/güvenlik yetkileri değişmez.
Senaryo/monitoring harita bağlantıları mevcut ileri formlara gider, otomatikrun yok.
Yeni JourneyGuide.qml; home11/katalog92. [Güncel kanıt](evidence/UI_JOURNEY.md).
Kaggle sayfa hücreleri okunamadı; birebir içerik incelemesi/kopyalama iddiası yok.
Önceki resmî kabul/longheap/GC/human/AT/offlineinstaller açıkları korunur.

## Önceki UI yenileme teslimi (tarihsel)

2026-10-17: Kullanıcının açık kapsamlı UI/UX yenileme talimatı uygulandı.
Yeni faz başlatılmadı. [UI yenileme teknik teslimi](evidence/UI_RENEWAL.md) güncel
runtime değişikliklerini ve ayrı test kanıtlarını taşır; aşağıdaki Faz75 kaydı
kendi teslim tarihindeki kaynak/kanıt durumudur, yeni UI için yeniden kabul değildir.

Ortak açık/koyu tema, daraltılabilir navigasyon, üst arama/ayar/yardım, durum satırı,
18 panelde ilk ziyarette yükleme ve form koruma; modül listesinin görünür delegate
üretimi; gizli aramada optional backend probe engeli. Dataset200 kayıtlık mevcut
model/view: gerçek null rolü, sütun genişliği, klavye ve yalnız görünen seçimin
RowId'li JSON kopyası. Rapor başlık/bölüm editörü; grafik responsive canvas/boşlukta
seçim koruması. Validation/Preparation ilk yüklemede mevcut planı okur. skops.io
safe serializer yalnız save/load çağrısında yüklenir. Algoritma/iş yönetimi yeniden
yazılmadı; bütçe gevşetilmedi, dependency değişmedi. Learning katalog91; home10 ve
dataset-profile4 güncellendi,414article; uzman review yenilenmiş/onaylı değildir.

Son source regresyon34PASS, kurulu noneditable wheel17PASS; ek güncel görsel7source/7wheel PASS, kilitli giriş smoke source/wheel PASS ve432paket byte-eşit; scientific-integrity
110PASS, model/calibration/validation8PASS, accessibility/persistence44PASS,
workflow19PASS ayrı koşular (tekrarlar toplanmaz). Görsel/source/wheel ekleri EUI'da.
Tekil offscreen başlangıç gözlemi3.49→1.74s ve865→556MiB; minHW/median garantisi değil.
Son ek grafik koşusunda süreç/native thread bütçe iptali, sonra aynı test PASS:
UI-R01 aralıklı kaynak denetimi açık. Kapanışta307uncollectable warning UI-R02 açık.
Eski longheap/minHW/physical/human/AT/offlineinstaller/remoteCI kapıları kapanmadı.
Tüm400+ modül için gerçekGUI/insan kabulü iddiası yok. Faz74Flatpak adayları yeni UI
kodunu içermiyor; güncel wheel yerel geliştirici paketidir, dış release yapılmadı.
Çalışma ağacı mevcut dirty/untracked içerikle korundu; stage/commit/push yok.

## Önceki Faz75 teslim kaydı (tarihsel)

2026-10-17 final;2026-10-16 başlangıç DEC75-01 açık Faz75: son bounded benchmark/capability audit teknik teslim.
Resmî **sürüyor / deneysel / isteğe bağlı**. Bütün zorunlu release gates kanıtlanmadı;
production veya bütün yöntemler tamamlandı denmez. [E75](evidence/PHASE75.md),
[kapsam](RELEASE_SCOPE_0_1.md), [önceki tam durum](evidence/phase75/prior-project_state.txt).
Yeni faz veya dış release yetkisi yok. Stage/commit/push yok.

Uygulama runtime kodu Faz74 ile aynı431dosya: Python3.13.15/PySide6/QML,
tek Capability/SourceAdapter registry, ProjectStore/ComputeBudget/Provenance ve
RowId/ColumnId/SourceRecordId korunur. Çalışma ağacı önceki fazlardan çok dirty ve
untracked; bunlar teslimin parçasıdır, silme/reset/stage yapma. Faz75 yeni runtime
metodu eklemedi; audit/benchmark/review docs ve test readiness düzeltmesi ekledi.

scripts/benchmark75_plan.py dokuz alan +guardrails/numeric açık seçim.
benchmark75.py ayrı bounded process source/noneditable-wheel veya gerçek GUI,
timeout process-group temizliği; yeni output dizini, eski sonuç ezilmez.
benchmark75_evidence.py post-call synthetic fixture/artifact/test SHA256 ve referans
assertion/numeric actual-reference-atol-rtol-inputhash-assumptions; GUI shutdown
öncesi screenshot ve örneklenmiş kaynak raporu. Kullanıcı projesinde çalıştırılmaz.
Numeric fourteen witness: histogram, typedweight/Rubin, beta-binomial, label-order
Brier/logloss, ATE, KM/risk, IoU/Dice, audio sinePSD, topK/PageRank, experiment mean,
CRS, toyTurkish cosine, typedDAG profile. Bunlar bütün backend/yöntem sertifikası değil.

Nihai seçilmiş compute323source/323wheel PASS; ayrıca9audit gate contract PASS.
Eski319run üstüne14numeric duplicate sayılmaz. Train/test/group/time poisoning,
MI/fold isolation, calibration and persistence, cancel/crash, single writer/ACTIVE/
source integrity, optional absence and ledger kontrolleri guardrails176 dahil.
Tam depo suite'i değildir; tüm alt yöntemler bu koşuda tek tek yeniden bilimsel
verified değildir. Source/wheel431byte parity +Faz74core/pro candidate SHA256match.
2GiB isolated installed entry GUI_SMOKE PASS; ilk inherited-user-settings entryexit2
startup ret saklı, o koşu kontrollü default test sayılmaz. User settings okunup/ezilmedi.
Gerçek pinned KDEPlatform core no-network optional-absent smoke yeniden PASS;
cleanOS offlineinstaller veya insan portal testi değildir.

GUI: baseline2GiB ile weighted, experiment/Bayes, calibration, spatial/time,
causal/survival ve recommendation/graph yollarının ayrı başarılı koşuları var.
Bazı uzun default2GiB/explicit4GiB zincirleri kaynak/timeout nedeniyle fail;
her biri E75'te ayrı, tek başarılı tekrar kök nedeni tamamen kapatmaz.
Temizlikte disabled button'a direct signal emit öncesi project/data idle/button
wait test düzeltildi, product limitleri kaldırılmadı. Küçük4GiB source/wheel
clean→histogram→PNG/SVG/export/save/reopen PASS; source sampled peak2.167GB,
minHW/perf garantisi değil. Uzun temizlik240s timeout ve bir saved calibrated run
canTest false ara failure açık. NLP/vision/audio uzun combined run timeout oldu; ek tek-case audio classification GUI de90s worker timeout/failed;
partial call witnesses ve ek tek-case denemeleri final-results/acceptance içinde.
Gerçek insan novice/expert/physical/AT testleri yapılmadı.

scripts/audit_phase75.py: bütün76phase/sourceS/planP ve416static capabilities;
source path/help/test/GUItest presence/current JUnit ile ayrı sınıflandırma.
Kararlı0, deneysel412, eksik4 static capability; unknown/unsupported operation/support
ayrıca eksik. Test module PASS birebir method acceptance değildir. Capcode.jupyter,
model.special.pu,model.stream.broker,workflow.schedule eksik; diğer geniş native/
backend/OS/worker environment açıkları method/requirements sınıflarında saklı.
Makine JSON ve generated ana bölüm docs/PRO_CAPABILITY_MATRIX.md içinde.
Final audit kaynak/JUnit hash'leri ve eski test revision flag'i taşır.

414article/content90+10lesson değişmedi;424hash/version-bound expert review pending,
reviewer/date/decision boş. review worksheet human alanı doluysa generator ezmez;
yeni output klasörü gerekir. Hiçbir AI/teknik review bağımsız bilimsel uzman onayı
sayılmaz. docs/RELEASE_REVIEW_PROTOCOL.md gerçek futurehuman/expert/AT protokolüdür,
gerçekleşmiş study değil. Issues severity ve current source/wheel/GUI/candidate
kanıtları E75/acceptance.json/final-results.json içinde; zorunlu gate açık.

Önceki live keyring/privacy/DP/nativeSDK/worker env provisioning/offlineinstaller/
Pardus/Debian/ayrıArch/GPU/minHW/physical/human/AT/newremoteCI ve longheap açıkları
korunur. Flatpak unsigned local candidate hash/authenticity farklı; app rollback
schema migration'ını geri almaz. Şimdi yeni iş için E75'in final loglarını esas al;
eski açıkları kapatılmış veya koşulmayan kontrolleri PASS gibi sunma.

Son14document unittest PASS ve static docs/learning/usability/artifacts/Ruff/format kapıları E75 loglarında. Nihai source323/wheel323+9each audit contracts; GUI runları tekrarlandığı için birbirine toplanmaz. Kaynakta14completed GUI PASS olan run içinde ayrıca media timeout var; bütün run PASS değil. Wheel3GUI PASS; default2GiB entry ve gerçek core Flatpak optional-absent offline smoke PASS.
