# Profil teknik tür etiketleri

2026-10-10 Europe/Istanbul; ENV-UI-PROFILE-TYPE-LABELS; UPT-03.
Açık kullanıcı gösterim düzeltmesi; yeni faz yok. Profil tür tablosu ve üst
özet gerçek teknik adları kullanır. Hücre Int64/String/Decimal gibi yalnız
algılanan türü gösterir. Eski fiziksel String kaydı hücrenin tooltip'inde
ayrı açıklanır; kaynak ve snapshot değişmez. Önceki UPT-02 hücre içindeki
kayıt açıklaması bu taleple tooltip'e taşındı. Analitik fiziksel türü kullanır.

Gerçek kontroller [checks.json](ui-profile-type-labels/checks.json) içindedir.
Headless Qt geliştirici doğrulaması fiziksel masaüstü kabulü değildir.
