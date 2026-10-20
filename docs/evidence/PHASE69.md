# Faz69 — Öğren dersleri ve ayrı laboratuvar

2026-10-16 DEC69-01 / ENV-69. Açık talimat; sınırlı yerel CPU kapsamı.
Resmî sürüyor/deneysel/isteğe bağlı. Faz70 başlamaz; önceki kabuller korunur.

<a id="e69-scope"></a>
## E69-SCOPE

Öğren → ders yolu → ayrı sentetik workspace.10gerçek kernel/8yol; advisory prerequisite
DAG, ortak arama/sözlük/makale favorileri ve optional versioned local progress.
Her ders amaç/veri/problem/varsayım/adım/beklenen/yanlış yorum/kendi verin/günlük örnek/
denklem/kaynak-review taşır. Optional açıklamalı self-check; zorunlu sınav/sertifika yok.
403Capability otomatik learning coverage:10interactive, diğer393article-linked,
tüm modüllerde lab var iddiası yok.409makale/content85, lesson catalog1.
[Gerçek matematik/split/bütçe/yaşam döngüsü](../adr/070-learning-laboratory-phase69.md).

Ayrı ProjectController aynı ProjectStore/registry/Provenance/ComputeBudget'u kullanır;
ana kullanıcı proje referansı yok. Safe synthetic fixture/kimlik ve gerçek metrik/
grafik/split native artifact'ta; DatasetVersion/user RowId uydurulmaz. Worker Qt/ACTIVE
ve kaynak yazmaz. Pencere nonmodal, açılışta hesap yok; slider değişikliği compute
tetiklemez. Sonuç önceki ayarsa stale görünür. Cancel eski sonucu korur. Normal
shutdown geçici workspace'i temizler; kalıcı lesson ilerlemesi yalnız açık opt-in.

<a id="e69-validation"></a>
## E69-VALIDATION

[İlk native32pass/1fail](phase69/source-initial.xml): önceki compute-resources ve
model-monitoring makalelerinin taxonomy üyeliği eksikti. Yeni gruplar eklendi;
eski workflow grubunun test edilen anlamı korundu. İlk seed widget property hatası
[source GUI failure](phase69/source-gui-initial.xml). Ardından QML startup notify
metadata SIGSEGV (exit139; tamamlanmış JUnit yok) ayrı başarısızlıktır. GDB ptrace
sandbox'ta engellendi, izinli izole geçici ayarlı teşhis notifySignalIndex çökmesini
gösterdi. Yeni özelliklerin own notify signal ve bridge düzeltmesi sonrası QML
startup gerçekten açıldı. Palette/recipe route substring ve yeni örnek adı yüzünden
boş taslağın dirty sayılması da geliştirirken düzeltildi. Ara failure'lar başarılı
kontrol diye sayılmaz.

[İlk ilgili core65pass/1fail](phase69/source-core.xml): Spearman GUI worker close
sırasında process-is-still-running hata/timeout. İlgili istatistik kodu bu fazda
sessizce değiştirilmedi. [Ayrı workspace4pass tekrar](phase69/workspace-recheck.xml)
aynı yolun yeniden çalıştığı ayrı kanıttır; önceki failure silinmez veya düzeltilmiş
kök neden iddiası kurulmaz. Genel uzun oturum/process kapanış kabulü açık tutulur.

[İlk çalışan gerçek walkthrough1pass](phase69/source-walkthrough-working/gui.xml):
on dersin hepsi aynı kullanıcı projesi/taslak/commit/dosya hashleri korunarak çalıştı;
fail-fast network guard, gerçek spawn/atomic save/hash reopen, iptal, optional
progress/opt-out, lab kapatılınca kendi CSV önizlemesi ve shutdown cleanup. Bu ilk
render düşük kontrastlıydı; son palette düzeltmesi ayrı doğrulanır. Son native,
kurulu wheel ve final GUI sonuçları tamamlandıkça aşağıya eklenir; bekleyen iş başarılı
sayılmaz. Fiziksel/human/AT/minHW/longheap/offlineinstaller/remoteCI ve önceki resmî
kapılar açık; bilimsel/eğitimci insan review not_recorded.


Son ilgili regresyon [67source](phase69/source-final.xml)/[67wheel](phase69/wheel-final.xml)
PASS; tam depo testi değildir. Bu koşulardan sonra gözlenen ortalamalar fixture sabiti
yerine aynı input listesinden açık NumPy mean ile hesaplandı (sonuç eşdeğer), Öğren
sözlük/kavram checkbox'ı eklendi. Son final native [15source](phase69/source-delivery-native.xml)/
[15wheel](phase69/wheel-delivery-native.xml) PASS; sayılar67ile toplanmaz.

Son teslim GUI: [source1pass](phase69/source-delivery-gui/gui.xml)/
[wheel1pass](phase69/wheel-delivery-gui/gui.xml); bir test her on dersin gerçek GUI
hesabını ve20render'ı sınar. Default2GiB; [source ölçüm](phase69/source-delivery-gui/measurement.json),
[wheel ölçüm](phase69/wheel-delivery-gui/measurement.json).1000/1366px screenshot'lar;
son palette [CI1000](phase69/source-final-gui/ci-1000.png) ajan tarafından incelendi.
Offscreen gerçek uygulamadır; insan/AT/fiziksel kabul değildir.

Eski Öğren/okuma/focus/examples regresyonu [3pass](phase69/legacy-learning-held-job.xml).
İlk kısa ömürlü8s/20s demo okumada tamamlanıp cancel-origin'i gizlediği için eski
assertionlar başarısızdı. Fixture gerçek işi600×0.1s boyunca canlı tutacak şekilde
uzatıldı; sonunda gerçek job başarılı tamamlanır, production hesap/pacing değiştirilmez.
[Önceki failure'lar](phase69/early-failures.json) silinmedi; statistics close race için
kök neden çözümü iddiası yok. Son3pass önceki2pass/1fail ile toplanmaz.

[Doğrulama](phase69/verification.json), [sekiz teknik kabul](phase69/acceptance.json),
[ortam](phase69/environment.json), [396byte-eşit source/kurulu wheel](phase69/wheel.json).
Yeni dependency/model indirmesi yok. Genel kullanıcı datasını ders motorunda işleme,
OS ağ arayüzü izolasyonu, zorunlu sınav/sertifika, bağımsız bilimsel review veya her
modüle özel interactive lab iddiası yok. Kullanıcı projesi değişmez; çalışma ders
workspace'inde kalır, normal shutdown temizler.

[Son kapılar](phase69/gates.json): docs/artifacts/learning/usability, Ruff check/format ve14belge testi PASS. [Teslim dosya hashleri](phase69/delivery.json). Stage/commit/push yapılmadı; kullanıcı dirty/untracked teslimi korunur.
