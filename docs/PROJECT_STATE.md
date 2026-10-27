# Veri_Ufku — aktif görev hafızası

## UX V2 (aktif — yerel `ux-v2`)

2026-10-25: Açık kullanıcı talimatı ile UX0–UX10 arayüz/akış görevi başladı.
Teknik Faz72+ başlatılmadı. Push yok; untracked `docs/PRODUCT_DIRECTION_JASP_ORANGE.md`
korunur ve commit’e karıştırılmaz.

**UX0 teknik teslim:** salt okunur denetim. [UX_V2_AUDIT.md](UX_V2_AUDIT.md),
[kanıt](evidence/UX_V2.md). H1/H3 doğrulandı; H2/H4 kısmen. Verilerim eksik;
eksik-etki ve üç yöntemli aykırı birleşik aşama kısmi. Taban: docs/artifacts/learning/
usability/Ruff/format PASS; `veri-ufku --smoke-test` GUI_SMOKE PASS; odaklı UI
26 pytest PASS. Tam suite/wheel/fiziksel/AT/minHW/offline/remoteCI/longheap
çalıştırılmadı veya bilinen açık. Resmî kabul ayrı.

**UX1 teknik teslim:** [UX_WORKSPACE_V2.md](UX_WORKSPACE_V2.md) bölge yerleşimi,
aşama şeridi, durum tabloları, mevcut ekran eşlemesi; DESIGN_SYSTEM/UI_DESIGN_BRIEF
bağı. Kod yok. Kullanıcıya bırakılan: gerçek yeni başlayanlarla gösterim.

**UX2 teknik teslim:** Sol `StageStrip` (10 aşama), açılır `ContextSidePanel`
(sütunlar / Bu adımı öğren), üst bağlam düğmesi, alt durum (aşama + veri kapsamı).
Mevcut 8 bölüm nav ve ekranlar korundu; proje/veri sözleşmesi değişmedi.
Test: `test_ux2_shell_gui` + odaklı UI; smoke/Ruff/docs/learning/usability PASS.

**UX3 teknik teslim:** Tablo merkeze (rows ilk accordion; aşama2→rows; otomatik sayfa);
başlıkta tür/rol/açıklama; sayfa≠tam veri uyarısı; sütun seçimi korunur; filtre
sürüm üretmez. 23 odaklı GUI PASS.

**UX4 teknik teslim:** Çevrimdışı `assets/examples/catalog.json`; Verilerim =
XDG `library-index.json` + dosya kopyası (ikinci ProjectStore yok). Import panelinde
Örnek/Verilerim; silme onayı; girdi silinince mevcut proje bozulmaz (test).
Karar: şema göçüsü yok.

**UX5 teknik teslim:** `ux_v2_stages.json` (taslak aşama+sözlük), `UxContentController`,
FirstRunTour (atlanabilir), bağlam paneli «Bu adımı öğren» metinleri. Kritik uyarı
sonuç yanında kalır sözleşmesi.

**UX6 teknik teslim:** `missing_drop_impact` + QualityPanel etki önizlemesi; karar
uygulanmaz; sürüm/kaynak korunur (test).

**UX7 teknik teslim:** Grafik yorum alanı; brushing→ortak RowId işaretleri; grafik
veri sürümü değiştirmez.

**UX8 teknik teslim:** IQR / dayanıklı z / klasik z aday listesi; birleşik RowId;
karar yok (Hazırla Önizle+Uygula).

**UX9 teknik teslim:** Gerekçeli yöntem adayları (`modeling/candidates.py`,
ValidationPanel çerçevesi); status=aday; auto_fit=false; ön işleme
`training_fold` sızıntı testi; mevcut preparation/validation yolları; final test
ayrı onay.

**UX10 teknik teslim:** Rapor UX bağlamı (`exports/ux_report_context.py`,
ReportBuilder append); Bölüm11 e2e parçaları otomatik; UX+prep/validation/report
81 pytest PASS; smoke GUI_SMOKE PASS; docs/learning/usability/artifacts/Ruff PASS.
Tam pytest `--all-extras` denemesi çok sayıda F ile yarıda (PASS iddia edilmez).
1366 ekran görüntüsü bu oturumda alınmadı (offscreen smoke + UX2 kabuk testleri).
Resmî kabul / insan gösterimi / AT / minHW / offline / remoteCI / longheap açık.
UX0–UX10 teknik zincir tamam; Faz72+ başlatılmadı.

**UX-Veri teknik teslim (2026-10-27, `ux-v2`):** Veri mockup fidelity
(yerleşim A). Üst şerit yalnız bağlam + Geri·Kaydet. Boş: seyrek kahraman,
CTA `Verilerim`/`Örnek`; hint/footer/browseSource gizli (objectName kalır);
önizleme/gate yalnız kaynak doluyken; drop yok; `createDefaultForImport`
klasör sormaz. Yüklü: salt okunur tablo + tür·rol menü; seçim şeridi sakin;
alt `N satır · M sütun · sürüm` (sayfa aralığı Veri’de yok); sağ «Veri»+sağlık,
2×5 kısa çip (`cyanSurface`), Geri + geniş İçe aktar. Dock kabuk Kapat gizli.
İkinci registry yok. `test_data_workspace_gui` + offscreen smoke. Tam
suite/wheel/fiziksel/AT/minHW/offline/remoteCI iddia edilmez. Faz72 yok;
commit/push yok.

**UX-İncele tarama teknik teslim (2026-10-27, `ux-v2`):** İncele merkez
şerit+tablo; `InspectWorkspacePanel` 5 çip; describe/values/profile Veri’den
İncele’ye; `operations.inspectDraft` bellek taslağı (sürüm yok) → Hazırla
önseçim+origin; tablo başlığı eksik rozeti; scope etiketi; puan yok. İkinci
kuyruk/API yok. `test_inspect_workspace_gui` + odaklı quality/ux3/dataset/veri;
Ruff; offscreen smoke. Tam suite/wheel/fiziksel/AT/minHW/offline/remoteCI/
Faz72 iddia edilmez; commit/push yok.

**UX-Görselleştir keşif teknik teslim (2026-10-27, `ux-v2`):** Merkez
`VisualizeWorkspace` (Grafik|Çıktı|Tablo, 6 amaç kartı, tuval, Python kapalı);
sağ `ChartPanel` Değişkenler+debounce create; chartCreate kaldırıldı; 12 blok
eşlemesi (Graph/Text dürüst ayrı panel). Yeni grafik motoru yok.
`test_visualize_workspace_gui` + charts_gui; Ruff; offscreen smoke. Tam
suite/wheel/fiziksel/AT/minHW/offline/remoteCI/Faz72 iddia edilmez; commit/push
yok.

**UX-Hazırla önizleme A teknik teslim (2026-10-27, `ux-v2`):** Merkez
`PrepareWorkspace` (etki rozetleri, salt okunur sürüm zinciri, önce/sonra,
İptal·Önizle·Uygula); sağ `PrepareCatalogPanel` 10 blok + Gelen taslaklar
(`inspectDraft`); Mod 1/2 UI (LEARNED uyarı; train-only motor yok;
`prepare_scope_mode` apply notu). Cleaning API genişletilmez. `test_prepare_workspace_gui`
+ cleaning_gui; Ruff; offscreen smoke. Tam suite/wheel/fiziksel/AT/minHW/
offline/remoteCI/Faz72 iddia edilmez; commit/push yok.

**UX-İstatistik soru odaklı A teknik teslim (2026-10-27, `ux-v2`):** Merkez
`StatisticsWorkspace` (öneri, n/p/etki/CI, grafik alanı, varsayım,
Sıfırla·Önizle·Kaydet); sağ `StatisticsCatalogPanel` 8 blok + `StatisticsPanel`
catalogMode debounce önkontrol; assumptions→tam create; kaydet=`analysis_store`.
Blok 1/8 desteklenmiyor; 6/7 examineTool köprüsü. Yeni motor/Bootstrap yok.
`test_statistics_workspace_gui` + statistics_gui; Ruff; offscreen smoke. Tam
suite/wheel/fiziksel/AT/minHW/offline/remoteCI/Faz72 iddia edilmez; commit/push
yok.

**UX-Model yerleşim A teknik teslim (2026-10-27, `ux-v2`):** Merkez
`ModelWorkspace` (Özet|Katsayılar|Artıklar|Tanılama, rozetler, eğitim/test
şeridi — held-out skor yok); sağ `ModelCatalogPanel` 10 çip (OLS…AIC/BIC) +
Y/X/param + Sıfırla·Eğit ve kaydet → Faz40 `statistics` models +
`analysis_store`; DatasetVersion yazılmaz. ML `modelPath` Layout A’da gizli;
İstatistik StatisticalModelsPanel korunur. `test_model_workspace_gui` +
offscreen smoke. Tam suite/wheel/fiziksel/AT/minHW/offline/remoteCI/Faz72
iddia edilmez; commit/push yok.

**UX-Raporla yerleşim A teknik teslim (2026-10-27, `ux-v2`):** Merkez
`ReportWorkspace` (Önizleme|HTML|PDF, freshness/STALE, LIMITATIONS);
sağ `ReportCatalogPanel` 8 çip + ayarlar + HTML/PDF dışa aktar;
`composeLayout` → `reportBuilder.run`/`exportReport`; birleştirme-only,
DatasetVersion yazılmaz. Legacy builder Loader gizli kalır.
`test_report_workspace_gui` + smoke. Tam suite/wheel/fiziksel/AT/minHW/
offline/remoteCI/Faz72 iddia edilmez; commit/push yok.

---

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
