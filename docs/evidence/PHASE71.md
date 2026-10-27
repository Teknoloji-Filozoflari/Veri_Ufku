# Faz71 — yerel review/share teknik kayıt

2026-10-16 DEC71-01 / ENV-71. Açık Faz71 talimatı; bounded desktop kapsamı.
Bounded teknik teslim doğrulandı; resmî sürüyor/deneysel/isteğe bağlı.
[Önceki durum](phase71/prior-project_state.txt) korunur; Faz72 yetkisi yok.
[Karar ve güven sınırları](../adr/072-local-review-sharing-phase71.md).

<a id="e71-scope"></a>
## E71-SCOPE

Rapor → Yerel review/paylaşım. Üç mode, inclusion preview, pattern secret/PII tarama,
redacted numeric sample, hash doğrulamalı açma, schema/operation/params/run-metric/
learning-notes diff, immutable review checklist ve yalnız yeni fork restore.
Source RowId/SourceRecordId/ColumnId ve proje kökeni korunur; farklı köken eşit
kimliği collision, otomatik merge/last-write-wins yok. Tek yazıcı kilidi korunur;
SQLite network-share çok kullanıcılı DB sayılmaz. Server/SaaS uygulanmadı.
Sınırlar ADR072 içinde; opaque artifact full copy uygulanmıyor diye görünür.
Çalıştırılmamış kontrol başarılı sayılmaz. Fiziksel/human/AT/minHW/offlineinstaller/
remoteCI ve önceki longheap/process yaşam döngüsü açıkları korunur.

<a id="e71-validation"></a>
## E71-VALIDATION

ENV-71 [gerçek donanım/sürüm](phase71/environment.json); kilitli CPython3.13.15
`.venv`, Linux CPU Qt offscreen/software. Yeni bağımlılık, server veya ağ/model
indirmesi yok. [408byte-eşit noneditable package](phase71/package-parity.json).

[120source](phase71/source-core.xml)/[120wheel](phase71/wheel-core.xml) PASS;
share, ProjectStore/lock/crash, operation, repro, report-builder, learning ve
learning-lab odaklı regresyondur; tam depo testi değildir. ZIP duplicate config
warning kasıtlı malicious repro fixture'ından gelir. Sayılar [10native son test](phase71/source-native-final.xml)
ile toplanmaz; native koşusu son collision-detail limitinden önceydi,120koşusu
son code/wheel revision'ını içerir.

Gerçek testler üç mode/member eşleşmesi, manifest/path/hash/mask tamper ret,
secret state/hücre/Parquet schema metadata engeli ve opaque artifact full copy
ret; PII consent ayrı, explicit sensitive term pakette yok; numeric nonfinite
korunur, diğer metin masked. İki gerçek paket schema/operation/params/run/profile
metric/learning note farkını doğru gösterir. Cross-project eşit ColumnId ve
included RowId ayrı collision; metadata-only row collision not observable.
Kimlik detayları ilk1000, toplam sayılar tamdır. Kaynak kimlikler/full artifact
byte'ları fork'ta aynı; yeni proje id ve share-import origin event kaydedilir.

İkinci gerçek spawn process writer read-only, save reddi; eski kilit kaldırılmadı.
Mevcut hedefe restore ve file overwrite reddedilir. Review subject entity hash +
artifact fingerprints +origin/commit/context taşır; yeni artifact manifest hash'i
eski yorumu rebind etmez. Eski event journal'dan silinemez; yorumun gerçekliği veya
reviewer identity'si doğrulanmış sayılmaz. Secret/PII pattern note/author reddi;
review yeni ortak kayıt sistemi değildir.

[2source GUI](phase71/source-final-gui/gui.xml)/
[2wheel GUI](phase71/wheel-final-gui/gui.xml) PASS; her test çok sayıda gerçek
preview/export/open/diff/save-review/cancel/reopen eylemi çalıştırır. Full vaka
ayrıca yeni fork oluşturur; ana kullanıcı projesini değiştirmez. İptal önceki
commit/yorumları korur, paket açmak kod/model çalıştırmaz. Yardım/Escape gerçek
QML yoludur. [Source ölçüm](phase71/source-final-gui/measurement.json),
[wheel ölçüm](phase71/wheel-final-gui/measurement.json). Basic metadata/sample
varsayılan2GiB; full-copy explicit4GiB. Örneklenmiş peak source1,918,947,328/
1,856,733,184byte; wheel1,935,302,656/1,872,257,024byte.100ms örnekleme kısa
zirveyi kaçırabilir; shared pages iki kez sayılabilir, minHW benchmark değildir.
Basic peak2GiB sınırına yakındır; tüm projeler için performans garantisi yoktur.

İlk [GUI failure](phase71/gui-initial-failure.log) event tuple/list normalize
edilmediği için close/reopen equality assertion'ıydı; ortak JSON encode/decode ile
normalize edildi. [Default2GiB iptal](phase71/gui-budget-failure.log) ve
[tekrar](phase71/gui-budget-repeat.log) full-copy open aşamasında generic canceled
sonucu verdi. Tam kaynak nedeni bu erken loglarda saklanmadı; yalnız RAM kök nedeni
kesin bulundu iddiası yok. Son UI supervisor bütçe mesajını generic canceled ile
ezmez. Full4GiB kapsamı ayrıca doğrulandı, default2GiB full kabulü iddia edilmez.
[İlk core eksik import](phase71/native-intermediate-failure.log) geliştirme hatası
ayrıca korunur; sonra [8native](phase71/native-initial-pass.log) ve son10geçti.
Eski process-close/longheap resmî kapıları kapanmadı.

[1000px source GUI](phase71/source-final-gui/basic/gui-1000.png) ajan tarafından
incelendi; bu insan/AT/fiziksel kullanılabilirlik kabulü değildir. Full snapshot,
metadata-only ve redacted fixture paketleri screenshot dizinlerinde gerçek dosya
olarak bulunur; bunlar sentetik test verisidir, kullanıcı proje exportu değildir.

Kontrol komutları:

```sh
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m pytest tests/test_share.py tests/test_projects.py tests/test_operations.py tests/test_repro.py tests/test_report_builder.py tests/test_learning.py tests/test_learning_lab.py -q
PYTHONPATH=/tmp/veri-ufku-f71-final-installed QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m pytest tests/test_share.py tests/test_projects.py tests/test_operations.py tests/test_repro.py tests/test_report_builder.py tests/test_learning.py tests/test_learning_lab.py -q
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase71.py --output docs/evidence/phase71/source-final-gui
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python scripts/measure_phase71.py --output docs/evidence/phase71/wheel-final-gui --package-root /tmp/veri-ufku-f71-final-installed
```

Offline build/install: `env UV_CACHE_DIR=/tmp/veri-ufku-f71-uv uv build --wheel --no-build-isolation --offline --out-dir /tmp/veri-ufku-f71-final-wheel`;
`uv pip install --no-deps --python .venv/bin/python --target /tmp/veri-ufku-f71-final-installed /tmp/veri-ufku-f71-final-wheel/veri_ufku-0.1.0-py3-none-any.whl`.
[Build](phase71/build-final.log),[install](phase71/install-final.log).
Local wheel build/runtime internet gerektirmez; tam offline installer iddiası yok.

Kapılar [docs](phase71/docs-gate.log),[artifacts](phase71/artifacts-gate.log),
[learning](phase71/learning-gate.log),[usability](phase71/usability-gate.log),
[Ruff check](phase71/ruff-check.log),[format](phase71/ruff-format.log),
[14document unittest](phase71/document-tests.log),
[kurulu entrypoint smoke](phase71/wheel-smoke.log). Bunlar önceki resmî insan/AT/
minHW/fiziksel/offlineinstaller/remoteCI ve longheap/process kapılarını kapatmaz.
Server/deployment/identity/permissions backend mevcut değil, doğrulanmadı.

<a id="e71-delivery"></a>
## E71-DELIVERY

Son güvenlik incelemesi: source.path dışındaki serbest metadata notunda dış dosya
yolu kalabiliyordu. Full-copy scanner bunu da external-location blok olarak
raporlar; generated /unresolved-source/UUID dışında override yok. Metadata-only
bu değeri maskeler. Son [11source](phase71/source-location.xml)/
[11wheel](phase71/wheel-location.xml) PASS; bu yeni kontrol120koşusundan sonradır,
önceki regresyon yeniden çalıştırılmış sayılmaz. Son GUI source/wheel ayrı delivery
koşularıyla kayıtlıdır; yukarıdaki final-gui ilk başarılı revision'ı korur.
Son build/install `build-delivery.log`/`install-delivery.log`; package-parity bu
son scanner kodunu içeren noneditable build ile tekrar hesaplanır.

Yorum aktarımını ek olarak sınayan [source](phase71/source-review-transfer.xml)/
[wheel](phase71/wheel-review-transfer.xml) ilk koşuları başarısızdı: checklist'teki
`secret-pii-reviewed=True` anahtarı generic secret-key sanılıyordu. Yalnız bu exact
closed boolean için istisna eklendi; metin/sayı ve api_key için ret sürdü. Son
[13source](phase71/source-reviewed.xml)/[13wheel](phase71/wheel-reviewed.xml) PASS;
yorumlu full-copy yeni fork'a aktarılır, eski origin/subject/artifact fingerprints
birebir aynı ve external-origin kalır. Bunlar120önceki regresyonuyla toplanmaz.
Önceki source delivery GUI [1pass/1fail](phase71/source-delivery-gui/gui.xml) son
close/open assertion'ında başarısızdı; [wheel2pass](phase71/wheel-delivery-gui/gui.xml)
ayrı kanıttır, başarısız kaynak koşusunu silmez. Son reviewed GUI tekrarları aşağıda.


Son [2source GUI](phase71/source-reviewed-gui/gui.xml)/
[2wheel GUI](phase71/wheel-reviewed-gui/gui.xml) PASS. Önceki close/open assertion
kök nedeni değiştirilmiş/kapatılmış iddia edilmez; son tekrarlar gerçek başarıdır,
eski failure ayrıdır. [Source son ölçüm](phase71/source-reviewed-gui/measurement.json),
[wheel son ölçüm](phase71/wheel-reviewed-gui/measurement.json); basic2GiB/full4GiB.
Son408byte-eşit package review-wheel build'idir; `build-review.log` ve
`install-review.log`. Son kurulu giriş noktası [GUI_SMOKE](phase71/wheel-review-smoke.log)
PASS. Statik kapılar son kodla tekrar geçti;14document unittest belge son devirde
ayrıca yeniden çalıştırılır. Artefact source/test hash ve kapsamı bu dosyada kayıtlı;
çalıştırılmayan tam depo/human/AT/minHW/offlineinstaller/remoteCI kabulü yoktur.

Son reviewed GUI örneklenmiş peak source basic1,923,395,584/full2,301,595,648byte;
wheel basic1,932,390,400/full2,304,438,272byte. Full4GiB'nin default2GiB kapsamıyla
karıştırılmaması özellikle önemlidir; bu sayılar eski revision ölçümlerinin yerine
tarihsel olarak geçirilmez. Son14document unittest PASS (16.101s); son doc/static
kapılar PASS. Çalışma ağacı stage/commit/push yapılmadan bırakıldı.
