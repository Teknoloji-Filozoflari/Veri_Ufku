# Faz14 — soru odaklı istatistiksel analiz

2026-10-08, ENV-14. Kullanıcının açık Faz14 talimatı uygulanır; sonraki faz başlatılmaz. Teknik kabul ve insan kullanıcı kabulü ayrıdır. Faz13 F13-S005 açık olduğu için Faz14 bağımlılık kapısı sürüyor/deneysel kalır; bu oturum önceki kullanıcı testine başarı yazmaz.

<a id="e14-s001"></a>
## Soru → önkontrol → sonuç

StatisticsPanel ve ui/statistics gerçek uygulama Karşılaştır ekranını etkinleştirir. Beş soru yolu, ölçüm/grup/anahtar, birim, bağımsız gözlem birimi ve hipotez bağlamı zorunludur. Önkontrol ayrı CPU süreçte tam seçili kapsamı kullanır; varsayım onayı gelmeden analiz başlatılmaz. Tarif/filtre/veri değişikliği güncel önkontrolü geçersiz kılar. Sonuç geldiğinde ayarlar katlanır; yeniden açılabilir. Gerçek QML düğmesi/preflight/run/save/help/reopen her yöntem için tests/test_statistics_gui.py içinde çalıştırıldı.

<a id="e14-s002"></a>
## Tasarım ve kişi eşleştirmesi

İki bağımsız grup, aynı kişilerin önce/sonrası, üç veya daha fazla grup, kategorik ve sayısal ilişki. Eşler uzun tablodaki kullanıcının kişi anahtarı ve seçtiği önce/sonra etiketleriyle kurulur. Satır sırası kullanılmaz: farklı sıralı fixture ve ters çevrilmiş kayıtlar aynı referans sonucu verir. Tekrarlanan kişi/etiket veya eksik anahtar belirsiz eşleştirmeyi durdurur. Eşleşmeyen kişilerde varsayılan hata; açık yalnız tam eşler seçiminde dışlama sayısı ve seçilim uyarısı kayıtlıdır. Eksik ölçüm çift olarak dışlanır. Kaynak byte hash'leri korunur.

<a id="e14-s003"></a>
## 11 yöntem, kurulu API ve bağımsız referanslar

SciPy1.18.0/NumPy2.5.3 locked API; [resmî SciPy stats belgeleri](https://docs.scipy.org/doc/scipy/reference/stats.html) ve kurulu signature/result probe'u birlikte doğrulandı. f_oneway(equal_var=False) Welch ANOVA'yı destekliyor. Native t/Pearson CI ve contingency.odds_ratio koşullu exact CI çağrıları çalıştırıldı. API signature, gerçek sonuç/pid/n/CI ve süre [source ölçümünde](phase14/headless.json) ve [kurulu wheel ölçümünde](phase14/wheel.json).

| Yöntem | Bağımsız çekirdek doğrulama | Etki / CI |
|---|---|---|
| Welch t | df4 kapalı t kuyruğu ve bağımsız t4 tablo quantile | Birimli ortalama farkı / t CI |
| Eşleştirilmiş t | Anahtarla farklar, df3 kapalı t kuyruğu | Ortalama sonra−önce / t CI |
| Mann–Whitney | U ve tüm kombinasyonlardan exact p | Sıra biserial / CI sunulmaz |
| Wilcoxon | Fark işaretlerinin exact2^n örnek uzayı; ties/zeros politikası | Eşleştirilmiş sıra biserial / CI sunulmaz |
| ANOVA | Elle SSbetween/SSwithin, F27 ve F(2,6) kuyruk | Betimsel eta-kare / CI sunulmaz |
| Welch ANOVA | Elle ağırlık/df formülü, F162/7 ve kapalı kuyruk | Betimsel eta-kare; Welch sınırlaması / CI sunulmaz |
| Kruskal–Wallis | Elle grup rankları H12.5 ve chi²2 kuyruk | Epsilon-kare / CI sunulmaz |
| Ki-kare | Elle hücre toplamları chi²20, erfc kuyruğu | Cramér V0.5 / CI sunulmaz |
| Fisher2×2 | Hipergeometrik kombinasyonlardan iki yönlü exact p; sonsuz OR sınırı | Koşullu OR / koşullu exact CI |
| Pearson | Elle kovaryans/r, df3 t kuyruğu; NormalDist Fisher-z sınırı | r / n>3 Fisher-z CI |
| Spearman | Elle sıralanmış örnekte rho/t kuyruğu | rho / CI sunulmaz |

Normalite testi otomatik seçim kuralı değildir; yöntem kullanıcı sorusu/hipotezi/tasarımla seçilir. Grup dağılımı/uç değerler ve bağımsızlık kullanıcı tarafından incelenir. MW/Kruskal genel medyan farkı testi değildir; Wilcoxon kişi içi farkların simetrisine dayanır. Örneklem/beklenen hücre/sıfır varyans koşulları [ADR-017](../adr/017-statistics-phase14.md) içinde açık.

<a id="e14-s004"></a>
## Sonuç, çoklu test ve atomik kayıt

Her sonuç n, kullanılan/dışlanan kayıtlar, null/nonfinite ve eşleşme sayımları, istatistik/p, uygun etki ve mevcut CI veya açık CI yokluk gerekçesi taşır. Sonsuz sınır metin olarak kayıtlı; NaN başarı değildir. Bootstrap yapılmaz, provenance seed/bootstrap null ve bağımsızlık varsayımı kayıtlıdır.

Post-hoc bütün seçili grup çiftleri: ANOVA/Welch için Welch t, Kruskal için MW (Tukey/Dunn değildir). Holm/Bonferroni/BH/none seçimi, aile boyutu/kapsamı, raw/düzeltilmiş p kayıtlıdır. BH bağımsız/pozitif bağımlı aile koşulu açıklanır. Birincil test/ayrı çalıştırmalar otomatik aynı aileye girmez; tekil CI'lar düzeltilmiş aile CI'ı değildir. Düzeltmeler bağımsız elle sayılarla test edildi.

JSON sonuç+RowId üyeliği hash/çekirdek JSON/üyelik/kaynak sürümü kontrolünden sonra mevcut atomik ACTIVE protokolüyle projeye kaydedilir. Copy fault injection önceki ACTIVE'yi korur; sonuç JSON tamper reddedilir. Kaydet/kapat/aç ve kaydedilmiş analizi tekrar kaydet yolu gerçek GUI'de çalıştırılır. Saved sonuçlar rapor exportunda açıklamalarıyla görünür; yeni şema migration gerekmez. İstatistik yayınının pointer_written ve pointer_replaced noktalarında iki gerçek SIGKILL deneyi önceki veya yeni tam commit'i korudu; kilit kurtarma sonrası JSON/RowId artifact'ları yeniden açıldı. Gerçek ikinci süreç salt okunur kaldı ve istatistik yayınını reddetti.

<a id="e14-s005"></a>
## Yardım ve bağlam

İçerik15/toplam89 makale: altı istenen kavram, soru yolu ve11 yöntem. p-değeri H0'ın doğruluğunun olasılığı değildir; etki/CI, kişi anahtarı, aile düzeltmesi ve gözlemsel ilişki açıklanır. Her yöntemin gerçek yardım bağı GUI'de açılır; F1 Karşılaştır bağlamını açar. check_learning gerçek içerik/QML bağı kontrolüyle çalıştırılır. Yardım kaynak veya analiz verisini değiştirmez.

<a id="e14-s006"></a>
## Kabul, paket ve sınırlar

Bağımsız sayısal referanslar tests/test_statistics.py; gerçek11 yöntem UI/process/save/reopen ve stale/cancel tests/test_statistics_gui.py. Yetersiz veri, sabit varyans/fark, sparse kategori, duplicate/missing/unmatched kişi, Float64 kaybı, null/nonfinite ve açık filtre kapsamı test edilir. p eşiklerini kesin sonuç olarak sunan anlatı yok. 100000 kayıt tam kapsam ölçümü, iptal ve önceki sonuç koruması source ve noneditable Linux wheel içinde yapılır.

[Gerçek komut/exit/log kayıtları](phase14/checks.json), [source](phase14/headless.json), [wheel](phase14/wheel.json), [ortam](phase14/environment.json), [source/hash](phase14/source.sha256). Yerel source/wheel QML offscreen/software geliştirici kontrolüdür; insan kullanılabilirliği, gerçek masaüstü/native picker, yeni uzak CI, temiz offline kurulum ve minimum donanım kanıtı değildir. Python TCP parent/spawn reddi OS arayüzlerini kapatmaz. Eski sağlam proje/kaynak korunur; model/bootstrap/permutation/ağırlık/küme/zaman bağımlı testler bu sürümde yoktur.

Nihai yerel kontroller: **389 pytest,9 locked unittest geçti**. Son arayüz düzenlemesinden sonra42 istatistik çekirdek/GUI testi yeniden geçti. Locked offline dev sync, system/locked check_docs, check_artifacts/check_learning, Ruff check/format, source ve kurulu wheel giriş noktası smoke başarılı.89 çevrimdışı makale/53 QML yardım bağı;11 yöntem source/noneditable wheel içinde gerçek önkontrol/run/save/reopen/resave, varsayım ve hesap düğmesine Qt Space, F1 bağlamı ve immutable kaynak hash kontrolünden geçti. Bütün son wheel package dosyalarının final source ile byte eşitliği ayrıca kontrol edildi; wheel/source/hash ortam kaydındadır.

İlk tam regresyonda eski “Karşılaştır mevcut değil” beklentisi ve eski sözlük26 sayısı takıldı; ekranın etkinliği ve44 sözlük makalesi beklentisi güncellendi. Son tam389 test geçti; ilk başarısız komut/log tarihçesi silinmedi.

Sistem `python3 -m unittest discover -s tests -v` Python3.14.7 içinde runtime paketleri yokluğu ile exit1; başarı diye kaydedilmedi. Proje >=3.13,<3.14 sözleşmesine uygun locked Python3.13.15 içinde aynı unittest9/9 ve tam pytest389/389 başarılı. [Ayrı sistem başarısızlık kaydı](phase14/system-unittest.txt).

Kavram içeriklerinin p-değeri/etki yorum sınırı [ASA açıklaması](https://www.amstat.org/asa/files/pdfs/p-valuestatement.pdf), güven aralığının tekrar örnekleme yorumu [NIST açıklaması](https://itl.nist.gov/div898/handbook/prc/section1/prc14.htm) ile kontrol edildi. Bu kaynaklar yöntemin varsayımlarını inceleme gereğini ortadan kaldırmaz.


## Gerçek performans ölçümü — sıcak geliştirici ortamı, N=1

| Yol |100k önkontrol ms|100k Welch hesap ms|İptal ms|Max Qt event aralığı ms|Parent+worker örneklenmiş RSS byte|
|---|---|---|---|---|---|
|Source|1038.38|1101.84|760.41|156.11|835444736|
|Noneditable Linux wheel|970.23|1016.54|707.28|153.57|835723264|

100000 kayıt sessiz örneklemesiz n=[50000,50000]. RSS ortak sayfaları iki kez sayabilir; Qt tick fiziksel input→frame değildir.100k/20 grup ve RAM/Float64 sınırı uygulama kapsamıdır;16/50ms hedefleri ve minimum donanım kabulü bu sıcakN=1 ölçümden doğrulanmaz. Dar/geniş render, klavye varsayım onayı ve sonuç ekranları [source ölçümü](phase14/headless.json) ve [wheel ölçümü](phase14/wheel.json) içinde listelenmiştir.
