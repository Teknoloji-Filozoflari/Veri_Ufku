# Veri_Ufku — çalışma alanı V2 şartnamesi (UX1)

2026-10-25. Kod değiştirilmedi. Bağlar: [UI_DESIGN_BRIEF.md](UI_DESIGN_BRIEF.md),
[DESIGN_SYSTEM.md](DESIGN_SYSTEM.md), [UX_V2_AUDIT.md](UX_V2_AUDIT.md),
[LEARNING_CONTENT.md](LEARNING_CONTENT.md). Token kaynağı `Theme.qml` korunur.

**Teknik teslim:** bu şartname. **Resmî kabul / kullanıcı gösterimi:** ayrı.

## 1. Amaç

Mevcut yetenekleri JASP (tablo + ayar + sonuç aynı bağlam) ve Orange (görünür
aşama yolculuğu) ilkeleriyle tek çalışma alanına dizmek. Yeni analiz ailesi yok.
Marka/ikon/metin kopyalanmaz.

## 2. Bölge yerleşimi

```
┌─ Üst çubuk ─────────────────────────────────────────────────────────┐
│ Proje · etkin veri kümesi/sürüm · kayıt durumu · geri/ileri · ara   │
├─ Sol aşama ─┬─ Merkez (Tablo | İnceleme | Sonuçlar) ─┬─ Sağ panel ─┤
│ 0…9 aşamalar│  aynı DatasetVersion + filtre bağlamı  │ Sütunlar    │
│ durum rozeti│                                         │ Analiz ayarı│
│             │                                         │ Bu adımı    │
│             │                                         │ öğren       │
├─────────────┴─────────────────────────────────────────┴─────────────┤
│ Not/karar (grafik veya sonuca bağlı; genel not defteri değil)         │
├─ Alt durum satırı ───────────────────────────────────────────────────┤
│ satır/sütun · görünen sayfa · filtre · örneklem · iş · kaynak        │
└──────────────────────────────────────────────────────────────────────┘
```

| Bölge | Sorumluluk | Dar pencere (<1000×Theme.scale veya 1366×768 altı) |
|---|---|---|
| Üst çubuk | Proje, sürüm, dirty/kayıt, geri/ileri (işlem undo bağlamı), arama (Ctrl+K) | Metin kısaltılır; ikon + tooltip |
| Sol aşama şeridi | 10 aşama; gezinme yardımcısı, zorunlu sihirbaz değil | 68px ikon rayı (mevcut compactNavigation) |
| Merkez | Tablo / İnceleme / Sonuçlar; aynı sürüm+filtre | Öncelikli; min kullanılabilir genişlik korunur |
| Sağ panel | Sütunlar, analiz ayarları, Bu adımı öğren | Varsayılan kapalı; açılır çekmece; kapatmak seçim/sonucu değiştirmez |
| Not/karar | Grafik veya sonuç kimliğine bağlı | Alt bölmede veya sonuç altında |
| Alt durum | Kapsam, sayfa, filtre, iş, kaynak | Tek satır; taşan bilgi erişilebilir ad |

**Tablo kuralı:** Proje veya veri kümesi etkinleşince merkez varsayılanı Tablo.
Sayfalama/sanal kaydırma; büyük veri belleğe tamamen yüklenmez. Görünüm filtresi
veri dönüşümü değildir. Başlıkta fiziksel tür, rol, kısa açıklama; eksik ≠ 0 ≠ "".

**Anlık sonuç:** Ucuz/küçük veride ayar→debounce→yenile. `ComputeBudget` aşımında
otomatik yenileme durur, maliyet gösterilir, **Çalıştır** çıkar. Yenileme veriyi
değiştirmez. Uzun iş iptal edilebilir; iptal son sağlam sonucu korur.

## 3. Aşama şeridi davranışı

| Durum rozeti | Anlamı |
|---|---|
| başlanmadı | Aşamaya girilmedi / çıktı yok |
| devam | Form veya önizleme var; kalıcı karar yok |
| not var | Kullanıcı karar/yorum notu kaydetti |
| uygulandı | (yalnız Hazırla) yeni DatasetVersion üretildi |

- İleri-geri serbest; geri dönmek seçim ve çalışmayı silmez.
- Aşama değiştirmek job’ı iptal etmez; busy ise durum satırında görünür.
- Hedef seçilmeden model aşaması zorlanmaz; keşif yoluna yönlendirilir.
- Her aşama kalıbı: Soru → Neden → Veri/sütunlar → Eylem → Sonuç/kapsam → Yorum → Karar/not → Sonraki.

Aşama kimlikleri (sabit): `goal`, `load`, `columns`, `summary`, `missing`,
`explore`, `outliers`, `prepare`, `model`, `report`.

## 4. Ekran akışı (özet)

1. **goal** — Amaç kartları + kaynak: dosya / Verilerim / örnek katalog.
2. **load** — Önizleme, ayraç/tür, kaynak vs çalışma kopyası; onay.
3. **columns** — Tam tablo + rol/açıklama; öneri onaysız kesinleşmez.
4. **summary** — Özet + korelasyon/ısı haritası; nedensellik uyarısı sonuç yanında.
5. **missing** — Eksik sayılar + silme etki önizlemesi; otomatik silme yok.
6. **explore** — Rehberli grafik / katalog; yorum; olağandışı nokta → aynı RowId aday kümesi.
7. **outliers** — IQR / dayanıklı z / klasik z aday listesi; karar yok.
8. **prepare** — 3–6 kararları; önizle + **Uygula**; yeni sürüm + geçmiş; kaynak korunur.
9. **model** — Gerekçeli adaylar; kullanıcı seçmeden fit yok; test bir kez.
10. **report** — Not+grafik+kapsam+sınır; HTML/PDF ayrı hedefe.

## 5. Durum tabloları

| Durum | Üst / merkez / sağ / alt | Kullanıcı eylemi |
|---|---|---|
| Boş veri (Veri) | Üst yalnız Geri·Kaydet; seyrek kahraman (kısa CTA); proje·klasör·kaynak; dock kapalı; ipucu/çift Gözat/kart-footer zorunlu değil | Dosya / Verilerim / Örnek → kaynak seçilince önizleme·İçe aktar |
| Yüklü veri (Veri) | Tablo (ad + tür·rol); sağ «Veri»+sağlık, 2×5 kısa çip; alt sakin `N satır · M sütun · sürüm` (sayfa aralığı zorunlu değil) | Çip → blok; sonraki satır; Geri + İçe aktar |
| İncele (yüklü) | Merkez şerit+tablo; sağ 5 çip; alt tarama kapsamı (used_n/population_n); dock Kapat gizli | Tarama → bulgu → Hazırla’ya taşı (taslak, sürüm yok) |
| Görselleştir | Merkez Grafik\|Çıktı\|Tablo + 6 amaç kartı; sağ Değişkenler; canlı create; Python kapalı | Amaç → atama → tuval/çıktı; sürüm değişmez |
| Hazırla (yüklü, işlemler) | Merkez rozet+zincir+önce/sonra; sağ 10 çip+parametre; alt İptal·Önizle·Uygula; dock Kapat gizli | Önizle (sürüm yok) → Uygula (yeni sürüm); İncele taslağı onaylı; Mod 1/2 dürüst |
| İstatistik (yüklü, examineTool=0) | Merkez öneri+özet+grafik; sağ 8 çip+değişken/parametre; alt Sıfırla·Önizle·Kaydet; dock Kapat gizli | Canlı önkontrol; varsayım→tam analiz; kaydet=analysis_store; sürüm yazılmaz |
| Model (yüklü, modelInstalled) | Merkez özet+sekme/tuval; sağ 10 çip+Y/X/param; alt Sıfırla·Eğit ve kaydet; dock Kapat gizli | Önkontrol→varsayım→fit+kaydet (analysis_store); sürüm yazılmaz; held-out skor yok |
| Raporla (proje açık, reportTool=0) | Merkez Önizleme\|HTML\|PDF; sağ 8 çip+ayarlar; HTML/PDF dışa aktar; dock Kapat gizli | Bölüm seç→compose→oluştur; birleştirme-only; STALE+LIMITATIONS |
| Yükleniyor | Busy; iptal görünür; seçim korunur | İptal veya bekle |
| Hata | StateNotice hata; son sağlam sonuç korunur | Yeniden dene / ayarı düzelt |
| Çok büyük veri | Otomatik canlı yenileme kapalı; maliyet + Çalıştır; sayfalı tablo | Çalıştır veya örneklem açık seçimi |
| Dar pencere | Sol ikon; sağ kapalı; merkez öncelikli; 720 minWidth korunur | Panel aç/kapa |
| Eksik opsiyonel paket | Capability unavailable metni; core paneller çalışır; kayıtlı sonuç görüntülenir | Kurulum (açık kullanıcı eylemi); ağ otomatik değil |

Ağ: açılış, proje açma, arama, panel görüntüleme ağ isteği başlatmaz.

## 6. Mevcut ekran eşlemesi

| V2 bölge / aşama | Mevcut bileşen | UX2+ notu |
|---|---|---|
| Üst çubuk | `Main.qml` header (proje, arama, seviye) | Sürüm/dirty vurgusu güçlendir |
| Sol 8 sekme | `sections` 0–7 + JourneyGuide | 10 aşamalı şeride genişlet; gelişmiş paneller erişimi korunur |
| Tablo | `DatasetPanel` rows | Yüklü Veri’de merkez; İncele’de de merkez (inspectMode + eksik rozeti); boşta `DataEmptyCard` |
| Veri sağ panel | `DataWorkspacePanel` (10 çip, 2 sütun) | Yüklüyken «Veri»+sağlık; İlk bakış çipi 8; describe/values Veri’de yok |
| İncele tarama | `InspectScanStrip` + `InspectWorkspacePanel` | 5 çip; blok1 ValueInspection; blok2 DatasetOverview; 3–4 kalite; 5 özel tür Loader |
| Profil/değer/özet | `DatasetOverview`, `ValueInspection` | İncele blok 1–2 (Veri accordion’dan taşındı) |
| Kalite/eksik | `QualityPanel` (blok 4) + eksik bulgu kartları | Aşama missing etki önizlemesi; Hazırla köprüsü `inspectDraft` |
| Grafik | `VisualizeWorkspace` + `ChartPanel` (Değişkenler) | Amaç kartları; canlı create; Çıktı=explain; Tablo=DatasetPanel |
| Aykırı | quality IQR + CleaningOptions + unsupervised | Aşama 6 birleşik yüzey |
| Hazırla | `PrepareWorkspace` + `PrepareCatalogPanel` → `OperationsPanel`/`CleaningOptions` | Yerleşim A; 10 blok; Mod 1/2 UI; train-only motor yok |
| İstatistik | `StatisticsWorkspace` + `StatisticsCatalogPanel` → `StatisticsPanel` | Yerleşim A; 8 blok; canlı önkontrol+varsayım; Bootstrap yok |
| Model | `ModelWorkspace` + `ModelCatalogPanel` (Faz40 models); ML `modelPath` Layout A dışı | 10 çip; Eğit ve kaydet → analysis_store |
| Rapor | `ReportWorkspace` + `ReportCatalogPanel`; legacy builder gizli | 8 çip; HTML/PDF dışa aktar |
| Öğren | `LearningCenter`, InfoPanel/F1 | Sağ “Bu adımı öğren” |
| Verilerim | — | UX4b yeni; ProjectStore genişletmesi |
| Örnek katalog | `learning.exampleLibrary` sandbox | UX4a ürün katalog kartları |

Gelişmiş görünüm: workflow/dashboard/ileri paneller mevcut `advanced` yollarından
erişilebilir kalır; form state korunur (UI-JOURNEY sözleşmesi).

## 7. Erişilebilirlik ve performans

- 1366×768 ve dar pencerede merkez kullanılabilir; klavye ile ana akış.
- Odak sırası / kontrast: DESIGN_SYSTEM + Theme.
- Tablo sayfalama `PERFORMANCE.md` sınırlarına uyar; ölçüm UX3/UX10’da.
- Worker Qt almaz, ACTIVE yazmaz; UI thread’de ağır hesap yok.

## 8. Kullanıcıya bırakılan işler

- **Gerçek yeni başlayan kullanıcılarla gösterim** (2–3 kişi) ve gözlem toplama.
- Türkçe aşama/grafik/model metinlerinin son onayı (UX5 taslakları sonrası).
- Resmî ürün kabulü; fiziksel masaüstü / AT / minHW / offline installer / remote CI.

## 9. Kapı (UX1)

| Koşul | Kanıt |
|---|---|
| Her bölge ve durum için net davranış | §2, §5 |
| Mevcut ekranlarla eşleme | §6 |
| Kullanıcıya bırakılan işlerde gösterim | §8 |
| Kod değişmedi; yalnız belge kapıları | `check_docs` (UX1 commit öncesi) |
