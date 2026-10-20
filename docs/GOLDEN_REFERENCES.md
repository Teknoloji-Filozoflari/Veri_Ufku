# Faz26 — altın referans ve bağımsızlık incelemesi

2026-10-09 UTC / 2026-10-10 Europe/Istanbul. Bütün girdiler paketli veya
test içinde üretilmiş sentetik verilerdir; gerçek kullanıcı verisi yoktur.
Üretim kütüphanesini aynı parametrelerle yeniden çağırmak altın referans değildir.

| Alan | Bağımsız beklenen değer / gerekçe | Gerçek kontrol |
|---|---|---|
| CSV kimlik/tür | `001` baştaki sıfırı korunur; eşit içerikli satırlar ayrı SourceRecordId/RowId alır; Decimal/tarih/null değerleri sabit fixture'dır | tests/test_delimited.py::test_utf8_expected_values_types_and_distinct_equal_record_ids |
| Profil | Paket satış örneği 12 kayıt/2 eksik; geçerli toplam480/ortalama48/medyan45. Tekrar eden kayıtlar ayrı kalır | tests/test_exports_gui.py; tests/test_dataset.py |
| İki grup | [1,2,3] ve [2,3,4]: iki ortalama farkı−1, t=−sqrt(1.5), df4 iki taraflı p kapalı form;95% aralık bağımsız t4 tablosu | tests/test_statistics.py::test_two_groups_closed_t_and_exact_rank_enumeration |
| Eşleştirme | Kişi anahtarıyla farklar1,2,3,4; ortalama2.5, t=sqrt(15). Satır sırası farklıdır; Wilcoxon p=2/2^4 | tests/test_statistics.py::test_key_pairing_order_invariance_and_independent_p |
| Kategorik/rank | Fisher olası tabloların kombinasyon toplamı; chi-kare uygun serbestlikte analitik kuyruk; Mann–Whitney/Kruskal/rank örnekleri bağımsız sıra hesapları | tests/test_statistics.py |
| Join | n:n eşleşmelerin satır/kaynak üyelikleri açık beklenen listeler; null-equality, ties ve outer unmatched kayıtlar ayrı | tests/test_relational.py::test_join_exact_growth_membership_undo_reopen |
| Dönüşüm | Aggregate/pivot/unpivot, dedup ve fill çıktıları elle belirlenmiş değer ve RowId/lineage üyeliğiyle karşılaştırılır; büyük Decimal/zone kaybı retleri ayrıca | tests/test_relational.py; tests/test_cleaning.py |
| Motorlar | Polars üretim sonucu, extension/autoload kapalı DuckDB SQL ile Decimal/date/null/join/sıra anlamında karşılaştırılır. Bu ayrı motor referansıdır; bütün olası veri tiplerinin kanıtı değildir | tests/test_relational_backends.py |
| Sınıf metrikleri | Matris[[2,1],[1,2]]; dört temel ikili metrik2/3, ROC8/9, PR65/72, AP11/12. Macro/micro/weighted ve tanımsız sınıf durumları ayrı | tests/test_classification.py::test_binary_hand_confusion_auc_and_undefined_classes; test_multiclass_hand_average |
| Sayısal metrikler | Baseline ve doğrusal sentetik hedef için beklenen merkez/hata ve negatif/sabit R² sınırları; eğitim üyeliği ve final test sınırı ayrıca | tests/test_validation.py; tests/test_regression.py |
| Sızıntı | Test özellikleri zehirlenir; eğitimde fit edilen merkez değişmemeli. Fit spy gerçek eğitim RowId üyeliğini denetler. Group/time/group_time ve hedef ufku kısıtları birlikte doğrulanır | tests/test_validation.py::test_test_feature_poison_never_changes_fit_and_hand_error; test_actual_baselines_group_time_and_json_roundtrip; tests/test_regression.py; tests/test_classification.py |
| Yeni veri | Güvenli paket roundtrip aynı eğitimli modelin tahminini korur; yeni veride fit çağrısı reddedilir/sayılır. Kaynak kolon/sıra/RowId ve invalid-row politikası ayrıca denetlenir | tests/test_lifecycle.py |

Roundtrip sonucu aynı modelle karşılaştırmak bilimsel bağımsız altın referans
değildir; serileştirme bütünlüğü kanıtıdır. Fit spy üyelik/sızıntı kontrolüdür;
saha başarısı değildir. DuckDB ayrı motor olsa da bağımsız elle değerlerle
birlikte değerlendirilir. Kapalı form hesaplarda kullanılan toleranslar
testlerde açık (genellikle1e−10–1e−12); exact Decimal/kimlik/sıra eşitliği
tolerans kullanmaz. Bootstrap/permutation gibi sunulmayan yöntemlere bu
kontrollerden kabul verilmez.

Gerçek koşu ve test kimlikleri [PHASE26](evidence/PHASE26.md) üzerinden
JUnit'e bağlanır; bu belge tek başına test başarısı değildir.
