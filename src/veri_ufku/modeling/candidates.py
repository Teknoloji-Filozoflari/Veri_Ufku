"""Gerekçeli model aday listesi — fit yok; seçim kullanıcıya aittir."""

from __future__ import annotations


def suggest_candidates(purpose: str, *, has_group: bool = False, has_time: bool = False):
    """Hedef/soru türüne göre aday yöntemler (status=aday; otomatik fit yok)."""
    purpose = (purpose or "").strip().lower()
    structure = (
        "group_time"
        if has_group and has_time
        else "group"
        if has_group
        else "time"
        if has_time
        else "independent"
    )
    structure_note = {
        "independent": "Bağımsız kayıt varsayımı; stratified sınıf oranını koruyabilir.",
        "group": "Aynı kişi/cihaz bütün ayrılır; grup içi sızıntı engellenir.",
        "time": "Geçmiş→gelecek ayrımı; ufuk eğitim sonunda arındırılır.",
        "group_time": "Grup ve zaman birlikte; çakışan aralıklar aynı tarafta kalır.",
    }[structure]

    if purpose == "regression":
        methods = [
            _candidate(
                "baseline",
                "Başlangıç referansı (ortalama/medyan)",
                "Ucuz merkez; her aday bunun üstüne ek değer göstermeli.",
                "Hedef ölçeği veya dağılımı değişkense tek başına yetersiz kalır.",
                "Sayısal hedef; özellik gerekmez.",
                ["mae", "rmse", "r2"],
            ),
            _candidate(
                "linear",
                "Doğrusal (OLS)",
                "Özelliklerin doğrusal katkısı yorumlanabilir; az parametre.",
                "Güçlü doğrusal olmayan ilişkide zayıf kalır; çok ortak özellikte kararsız.",
                "Ölçekleme önerilir; eksik doldurma yalnız eğitim fold'unda.",
                ["mae", "rmse", "r2"],
            ),
            _candidate(
                "ridge",
                "Ridge (düzenlileştirilmiş doğrusal)",
                "Çok özellikte katsayıları küçültür; gürültüye daha dayanıklı.",
                "Seyrek özellik seçimi gerekirse Lasso/ElasticNet ayrı yolda.",
                "Standard scaling eğitim fold'unda; alpha kullanıcı seçer.",
                ["mae", "rmse", "r2"],
            ),
            _candidate(
                "forest",
                "RandomForest",
                "Doğrusal olmayan ve etkileşimli ilişkiler için sınırlı ağaçlar.",
                "Çok pahalı; küçük n veya yorum zorunluluğunda uygun olmayabilir.",
                "Ağaçta scaling genelde gerekmez; eksik doldurma yine train-fold.",
                ["mae", "rmse", "r2"],
            ),
        ]
        starter = "baseline"
        plan = "train / validation / CV fold'ları / tek final test"
    elif purpose == "classification":
        methods = [
            _candidate(
                "baseline",
                "Başlangıç referansı (öncül / en sık sınıf)",
                "Sınıf dengesizliğinde accuracy tuzağını gösterir.",
                "Azınlık sınıfını bulmak asıl hedefse tek başına yetersiz.",
                "Hedef kategorik; özellik gerekmez.",
                ["f1", "precision", "recall", "roc_auc"],
            ),
            _candidate(
                "logistic",
                "LogisticRegression",
                "Doğrusal karar sınırı; olasılık çıktısı; düzenlileştirme ile kararlı.",
                "Doğrusal ayrılamayan desenlerde zayıf; scaling önerilir.",
                "One-hot/imputasyon yalnız eğitim fold'unda öğrenilir.",
                ["f1", "precision", "recall", "roc_auc"],
            ),
            _candidate(
                "forest",
                "RandomForest",
                "Doğrusal olmayan kararlar ve etkileşimler için.",
                "Olasılık kalibrasyonu bu yolda garanti değil; pahalı olabilir.",
                "Ağaç native kategorik yolları ayrı ailelerde; burada train-fold hazırlık.",
                ["f1", "precision", "recall", "roc_auc"],
            ),
        ]
        starter = "baseline"
        plan = "train / validation / stratified veya yapısal CV / tek final test"
    elif purpose in ("clustering", "anomaly"):
        methods = [
            _candidate(
                purpose,
                "Keşif / etiketsiz yol",
                "Hedef yok; benzerlik veya sıra dışı kayıt aranır.",
                "Supervised metrik ve final test bu yolda uygulanmaz.",
                "Hazırlık planı sonrası ilgili etiketsiz panele geçin.",
                ["silhouette"] if purpose == "clustering" else ["decision_score"],
            )
        ]
        starter = purpose
        plan = "etiketsiz inceleme; train/test ayrımı zorunlu değil"
    else:
        methods = []
        starter = ""
        plan = "Önce amaç (sayısal/kategori/küme/aykırı) seçin."

    return {
        "purpose": purpose or "",
        "status": "aday",
        "applied": False,
        "auto_fit": False,
        "selected_method": None,
        "starter_model": starter,
        "split_plan": plan,
        "structure": structure,
        "structure_note": structure_note,
        "structure_preserved": True,
        "test_policy": "Final test yalnız açık kullanıcı onayıyla bir kez; ayar seçiminde kullanılmaz.",
        "leakage_policy": "İmputasyon, scaling, encoding ve seçim yalnız eğitim fold'unda öğrenilir.",
        "candidates": methods,
        "disclaimer": (
            "Bunlar adaydır; kesin en iyi yöntem değildir. "
            "Kullanıcı seçmeden model fit edilmez."
        ),
    }


def _candidate(method_id, label, why, when_not, prep, metrics):
    return {
        "id": method_id,
        "label": label,
        "status": "aday",
        "why_suitable": why,
        "when_not_suitable": when_not,
        "preparation_needed": prep,
        "metrics": list(metrics),
        "selected": False,
        "fitted": False,
    }
