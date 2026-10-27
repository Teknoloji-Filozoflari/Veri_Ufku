# Faz08 — veri kalitesi merkezi kanıtı

2026-10-07 Europe/Istanbul (2026-10-06 UTC), ENV-08: yerel Linux geliştirici Btrfs/tmpfs, CPython3.13.15/PySide6Qt6.11.2/Polars2.0.0; offscreen/software. Kapsam yalnız Faz08, olgunluk deneysel. Gerçek masaüstü/minimum donanım doğrulanmadı; uzak CI başarısı aşağıda ayrı kayıtlıdır. Yerel kontroller ve kurulu wheel akışı doğrulandı. Matris tarih sütunu gerçek UTC günü2026-10-06; yerel takvim günü2026-10-07 ayrı belirtilir.

<a id="e08-center"></a>
## F08-S001 — gerçek merkez

Yollar src/veri_ufku/ui/qml/QualityPanel.qml, ui/dataset.py, analytics/worker.py. Veri→Veri kalitesi, dataset/miktar/kapsam/amaç, tekrar anahtarı ve formdan açık kurallar; gerçek QML düğmesi→spawn→rapor. tests/test_quality_gui.py iki test geçti: formdan range0..10 ile450 kayıt içinde439 ihlal; kaynak/draft değişmedi. İptal ve eski sütun binding sonucu yayınlanmadı. save→close→reopen raporu aynı veri sürümünde geri getirdi. Farklı metadata sürümünde eski rapor güncel bağlanmaz.

<a id="e08-findings"></a>
## F08-S002/S003/S006 — bağımsız kayıt referansları

Yollar analytics/quality.py ve tests/test_quality.py. Sekiz kayıtlık elle belirlenmiş fixture: category null index7; whitespace index5; sayı dönüşüm hatası index2; imkânsız tarih2024-02-30 index2; id benzersizlik ihlali index0/1; amount100 IQR adayı index7; kategori adayları index0..6 (İZMİR/izmir ve Ankara/ankra/boşluk); fixed tek değeri8 kayıt. Tam/tek id anahtarlı tekrar grubunun iki üyesi birlikte sayıldı. Her ilk5 örnek RowId immutable snapshot'taki beklenen kayda eşleşti; oranların paydası8. Candidate/violation ayrımı ve dataset/source SHA256 değişmezliği ayrıca kontrol edildi.

Sonlu int64/float64 dönüşümünde1.5/bad int hatası; 9007199254740993 float hassasiyet kaybı/bad hatası; izinli1/1.5 dışında iki ihlal. Boolean hedefinde true/false/evet geçerli, oops tek ihlal; date hedefinde geçerli2024-02-29 korunur, imkânsız2024-02-30/bad iki ihlal. Required null için ayrıca tek ihlal verir. Null bu dönüşüm kurallarında ihlal değil. required null'u ayrıca yakalar. NaN/+inf ayrı adaylar; nested değer ve boş filtre kapsamı güvenli taranır. Tüm-null sabit kolon gibi gösterilmez. İlk4/6 örnek scope sample, n4; açık filtreli1 kayıt scope filtered; tüm dataset taraması aktif görünüm filtresini uygulamaz. Kimlik rolünde IQR adaylığı bastırılır; açık range ihlali korunur. Türkçe I/ı, İ/i eşleşir; I/i eşleşmez. Geçersiz aralık/tarih biçimi işi başlatmaz. Kategori limitleri görünür uyarılıdır; eksiksiz fuzzy eşleme iddiası yoktur.

<a id="e08-recommendations"></a>
## F08-S004 — deterministik bilgi önerileri

tests/test_quality.py aynı snapshot/parametreyle iki raporun bulgu/öneri ve parametrelerinin birebir eşitliğini doğrular. Her öneride id/reason/precondition/impact/operation_id/learning_id/available var. Gerekçe rol, tür, amaç, n ve açık kuralı taşır; kimlik/model/örnek bağlamında farklı inceleme seçenekleri vardır. available=false; QualityPanel yalnız tarama/kaydetme/yardım eylemi sunar. Doldurma, dedup, trim, eşleme, parse/dönüşüm için çalıştırma düğmesi yok. Evrensel kalite puanı yok.

<a id="e08-help"></a>
## F08-S005 — çevrimdışı yardım

src/veri_ufku/learning/content/tr.json içerik7: kalite, meşru tekrar, eksik veri mekanizması ve aykırı gözlem dört yeni makale; toplam35. domain/capabilities.py dataset.quality ve kavram bağları. Yardım normal makale okumadır; tarama/düzeltme veya yeni try_action üretmez. NIST resmi boxplot kaynağı2026-10-07 web üzerinden incelendi; yöntem seçimi ADR-011'de açık.

<a id="e08-measure"></a>
## Gerçek büyük tarama ve render

scripts/measure_phase08.py 100.000 kayıt Parquet→import→full kalite→save/reopen→10.000 firstN örnek→iptal. Beklenen null25.000, whitespace25.000, Türkçe kategori adayı50.000, invalid date1, outlier1, seçili tekrar100.000 doğrulandı. [Ham ölçüm](phase08-headless.json); screenshot geniş açık/dar koyu form ve bulgu. Geliştirici sıcak ortam N=1; hedef minimum donanım kabulü değildir. Kaynak hash değişmedi, çalışma alanı temizlendi. Son render [geniş form](phase08-wheel-1366-light-form.png), [geniş bulgular](phase08-wheel-1366-light-findings.png), [dar form](phase08-wheel-720-dark-form.png), [dar bulgular](phase08-wheel-720-dark-findings.png). Kurulu wheel son ölçümü3499.1ms full scan, parent+worker örneklenmiş peak513.71MiB ve max UI tick45.0ms; [ham paket ölçümü](phase08-wheel.json). RSS ortak sayfaları mükerrer sayabilir; cgroup garantisi değildir.

Beş Faz02 resmi cache görüntüsü bu oturumda gerçekten yeniden görüldü (Orange/KNIME/jamovi/JASP/LabPlot); kaynak kimlikleri phase02-references.json. Sütun bağlamı, açık parametreler ve ayrı görünür sonuç ilkeleri mevcut Theme tokenlarıyla uygulandı; uygulamalar çalıştırılmadı. Başsız render gerçek kullanıcı/assistive teknoloji kontrolü değildir.

<a id="e08-checks"></a>
## Regresyon kapıları

[Komut/çıktı/exit kaydı](phase08-checks.txt): 212 pytest,9 unittest; locked dev sync, sistem/locked check_docs, check_artifacts, check_learning35 makale/38 UI bağı, Ruff check/format72 dosya, izole XDG offscreen/software giriş noktası GUI_SMOKE PASS ve git diff --check geçti. İlk lint koşusu ölçüm betiği import sırası nedeniyle başarısız oldu, düzeltildi; [tarihsel başarısız koşu](phase08-initial-checks.txt) kabul sayılmadı. Ortak Provenance eklenmesindeki tuple/list roundtrip testi önce başarısız oldu; rapor provenance JSON ile normalize edildi, gerçek roundtrip tekrar geçti. Son capability şemaları ve boolean/date referansları ardından21 hedefli pytest, Ruff check/format, check_docs/check_learning ve kaynak/kurulu wheel ölçümü tekrar geçti. [Doğrulanan dosya hashleri](phase08-source.sha256); kaynak promptu hash kaydına dahil ve değiştirilmedi.

<a id="e08-package"></a>
## Kurulu Linux wheel

Offline/no-build-isolation wheel/sdist /tmp/veri-ufku-phase08-verified-dist; offline/no-deps target /tmp/veri-ufku-phase08-verified-installed. Ayrı /tmp cwd ve PYTHONPATH target ile module __file__ target doğrulanır. Gerçek kurulu QML/spawn100.000 kayıt kalite→save/reopen→sample→cancel akışı geçti; kaynak hash değişmedi. [Paket kanıtı](phase08-wheel.json). Locked runtime ve mevcut sistem Qt kullanılır; bağımsız temiz Linux kurulum kabulü değildir.

<a id="e08-ci-remote"></a>

## F08-CI-REMOTE — başarılı uzak Linux CI

Kayıt 2026-10-06 UTC / 2026-10-07 Europe/Istanbul, ENV-CI-08. Kullanıcının paylaştığı gerçek GitHub Actions sonuç özeti: [koşu37532581621](https://github.com/Teknoloji-Filozoflari/Veri_Ufku/actions/runs/37532581621), [Linux işi112505393392](https://github.com/Teknoloji-Filozoflari/Veri_Ufku/actions/runs/37532581621/job/112505393392), **success**,1 dakika12 saniye. [Ham kullanıcı çıktısı](phase08-ci-37532581621.txt).

Qt native runtime kitaplıkları, izole yollar, sabit uv/Python ve kilitli bağımlılıklar, belge/artefact, lint, çekirdek/başsız QML ve kurulu giriş noktası Qt/process smoke adımları başarılı bildirildi. Yol .github/workflows/docs.yml; mevcut workflow belge adımında check_learning.py yardım bağ kapısını içerir. İlk kullanıcı özetinde commit SHA/test sayısı/ayrıntılı runtime metadata yoktu. Sonraki gh API kontrolü aşağıda commit eşlemesini doğruladı; test sayısı ve fiilî runner/runtime metadata ayrıca verilmedi. Kayıt tarihi koşunun başlangıç tarihi olarak sunulmaz.

Node.js20 kullanımdan kaldırma ve actions/checkout@v4'ün Node.js24 üzerinde çalıştırılması annotation'ı uyarıdır; bütün adımlar success. Workflow değiştirilmedi. Gerçek masaüstü/minimum donanım bu CI sonucu ile doğrulanmış sayılmaz.

Bu koşu önce yanlışlıkla Faz03'e bağlanmıştı. Kullanıcının düzeltmesiyle Faz08'e kaydedildi; Faz03'ün önceki37511231471 kanıtı korundu. Faz08 doğrulandı/deneysel/zorunlu; Faz09 başlamadı.

### Commit eşlemesinin bağımsız doğrulanması

`gh run view 37532581621 --repo Teknoloji-Filozoflari/Veri_Ufku --json headSha,conclusion,status,url,createdAt` gerçek GitHub API sonucu: [ham JSON](phase08-ci-37532581621.json), completed/success, headSha `e9fd13f41afb83daaca1c3790e8dc1e14a58d3cb`, createdAt2026-10-06T21:15:31Z. Sandbox ilk API bağlantısı başarısızdı; izinli tekrar başarılı oldu. Web sayfası fetch denemesi erişim sağlamadı; doğrulama gh API çıktısına dayanır.

Yerel Git aynı committe analytics/quality.py, ui/qml/QualityPanel.qml, tests/test_quality.py, tests/test_quality_gui.py ve docs/evidence/PHASE08.md dosyalarını içeriyor. `git show HEAD:docs/PROGRESS.md` Faz08 doğrulandı kaydını içerir. Committeki ve çalışma ağacındaki kalite motorunun SHA256'sı aynı: `26614e90d24781175ee63e890ea820abdc3ba71a338c0a8eac68973ab4f91002`. Böylece bu başarılı CI koşusunun Faz08 kodunu içerdiği commit düzeyinde doğrulandı.

Commit mesajı `feat: add phase 03 offline learning center` olarak kalmış; mesaj faz içeriğini doğru özetlemiyor. Geçmiş değiştirilmedi. Faz08 atfı commit başlığına değil doğrulanan commit ağacına dayanır.
