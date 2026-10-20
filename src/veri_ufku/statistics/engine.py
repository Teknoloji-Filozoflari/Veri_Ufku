"""Bounded complete-case analyses with explicit assumptions and method-specific effects."""

import hashlib
import itertools
import json
import math
import warnings
from decimal import Decimal
from pathlib import Path

import numpy as np
import polars as pl
import scipy
from scipy import stats
from scipy.stats.contingency import odds_ratio

from veri_ufku.analytics.contracts import ViewSpec
from veri_ufku.analytics.dataset import checked, filtered
from veri_ufku.importers.delimited import Control, hash_artifact
from veri_ufku.statistics.contracts import LABELS, AnalysisSpec
from veri_ufku.storage.project_model import ProjectError, uid

MAX_ROWS = 100000
MAX_GROUPS = 20
CAUTION = "p-değeri hipotezin doğru olma olasılığı değildir; küçük p kesinlik veya pratik önem göstermez. Gözlemsel ilişki nedensellik değildir."
ASSUMPTIONS = {
    "welch_t": "H0: iki popülasyon ortalaması eşittir. Bağımsız gözlemler; ortalamalar hedeflenir. Küçük örneklemde grup dağılımı ve uç değerler incelenmeli; eşit varyans gerekmez.",
    "paired_t": "H0: sonra−önce farkının popülasyon ortalaması sıfırdır. Kişiler birbirinden bağımsızdır; kişi içi sonra−önce farklarının dağılımı ve uç değerleri incelenir. Hedef ortalama değişimdir.",
    "mann_whitney": "H0: iki popülasyon dağılımı eşittir. Bağımsız gözlemler; eşit dağılımlar sıfır hipotezi ve sıra üstünlüğü hedeflenir. Dağılım şekilleri eşit değilse medyan farkı testi diye yorumlanmaz.",
    "wilcoxon": "H0: kişi içi farkların dağılımı sıfır çevresinde simetriktir. Kişi içi farkların sıfır etrafında simetrik dağılımı gerekir. Genel medyan farkı testi değildir; sıfır farklar wilcox politikasıyla sıralardan çıkarılır.",
    "anova": "H0: bütün grup popülasyon ortalamaları eşittir. Bağımsız gruplar, grup içi yaklaşık normal hatalar, eşit popülasyon varyansları. Dağılım, uç değerler ve araştırma tasarımı birlikte değerlendirilir.",
    "welch_anova": "H0: bütün grup popülasyon ortalamaları eşittir. Bağımsız gruplar ve yaklaşık normal grup içi hatalar; eşit varyans gerekmez. Her grupta pozitif varyans gerekir.",
    "kruskal": "H0: grup popülasyon dağılımları eşittir. Bağımsız gözlemler; grup dağılımlarının sıraları karşılaştırılır. Şekiller farklıysa genel medyan farkı iddiası kurulmaz; her grupta en az5 geçerli gözlem bu uygulamanın asimptotik kabul koşuludur.",
    "chi2": "H0: iki kategorik değişken bağımsızdır. Bağımsız gözlemler ve frekans tablosu gerekir. Her beklenen hücre en az5 olmalı (bu uygulamanın muhafazakâr önkoşulu).",
    "fisher": "H0: popülasyon odds oranı1’dir. Bağımsız gözlemler, 2×2 frekans tablosu ve pozitif satır/sütun toplamları gerekir. Küçük hücrelerde exact çıkarım; eşleştirilmiş kategoriler için uygun değildir.",
    "pearson": "H0: popülasyon doğrusal korelasyonu sıfırdır. Bağımsız gözlem çiftleri, doğrusal ilişki; analitik p ve Fisher-z CI için iki değişkenli normal popülasyon varsayımı. Uç değerleri inceleyin.",
    "spearman": "H0: popülasyon sıra korelasyonu sıfırdır. Bağımsız gözlem çiftleri, monoton ilişki; eşit değerlerin sırası ortalamadır. Asimptotik p küçük örneklemde güvenilir olmayabilir; bu sınırlama açıkça kaydedilir.",
}


def scalar(value):
    value = float(value)
    return (
        value
        if math.isfinite(value)
        else "∞"
        if value == math.inf
        else "−∞"
        if value == -math.inf
        else None
    )


def adjusted(ps, correction):
    values = np.asarray(ps, dtype=float)
    if correction == "none":
        return values.tolist()
    if correction == "bonferroni":
        return np.minimum(1, len(values) * values).tolist()
    if correction == "bh":
        return stats.false_discovery_control(values, method="bh").tolist()
    order = np.argsort(values, kind="stable")
    result = np.empty(len(values))
    result[order] = np.minimum(
        1, np.maximum.accumulate(values[order] * np.arange(len(values), 0, -1))
    )
    return result.tolist()


def prepare(request, spec, control):
    spec.validate(request["columns"])
    checked(request, control)
    view = ViewSpec.from_dict(spec.view) if spec.scope == "view" else ViewSpec()
    query, schema, names = filtered(request, view)
    count = query.select(pl.len()).collect(engine="streaming").item()
    chosen = [spec.x]
    if spec.path in ("numeric", "categorical"):
        chosen += [spec.y]
    if spec.path in ("independent", "groups", "paired"):
        chosen += [spec.group]
    if spec.path == "paired":
        chosen += [spec.key]
    if (
        not count
        or count > MAX_ROWS
        or count * (160 + 64 * len(chosen)) > control.budget.ram_bytes // 2
    ):
        raise ProjectError(
            "Seçili kapsam boş veya istatistik bütçesini aşıyor (en fazla100000 kayıt). Açık tablo filtresi kullanın; sessiz örnekleme yapılmaz."
        )
    for ident in chosen:
        dtype = schema[names[ident]]
        if dtype.is_nested() or dtype.is_temporal() or dtype == pl.Binary:
            raise ProjectError(
                "İstatistik alanları skaler sayı/kategori/kişi anahtarı olmalı; tarih/nested/binary desteklenmiyor."
            )
    numeric = (
        [spec.x, spec.y]
        if spec.path == "numeric"
        else [spec.x]
        if spec.path != "categorical"
        else []
    )
    for ident in numeric:
        if not schema[names[ident]].is_numeric():
            raise ProjectError(
                "Ölçüm fiziksel sayısal tür olmalı; sayısal kimliği ölçüm diye seçmeyin."
            )
        role = request.get("semantic_metadata", {}).get(ident, {}).get("role")
        if role in ("identifier", "category", "time", "ignored"):
            raise ProjectError(
                "Seçilen sütun ölçüm rolünde değil; Veri ekranında rolü düzeltin."
            )
    frame = query.select("__vu_row_id", *[names[c] for c in chosen]).collect(
        engine="streaming"
    )
    control.check()
    rows = frame.to_dicts()
    excluded = dict(
        null_rows=0,
        nonfinite_rows=0,
        missing_key_rows=0,
        unmatched_people=0,
        incomplete_pairs=0,
        unselected_phase_rows=0,
    )
    losses = 0

    def valid(row, fields):
        nonlocal losses
        values = [row[names[c]] for c in fields]
        if any(v is None for v in values):
            excluded["null_rows"] += 1
            return False
        if any(
            isinstance(v, (float, Decimal)) and not math.isfinite(v) for v in values
        ):
            excluded["nonfinite_rows"] += 1
            return False
        return True

    def number(value):
        nonlocal losses
        out = float(value)
        if not math.isfinite(out) or abs(out) > 1e100:
            raise ProjectError(
                "Ölçüm Float64 güvenli hesap aralığını aşıyor; birimi/ölçeği açık dönüşümle düzenleyin."
            )
        if isinstance(value, (int, Decimal)) and Decimal.from_float(out) != Decimal(
            value
        ):
            if spec.precision == "reject":
                raise ProjectError(
                    "Integer/Decimal → Float64 hassasiyet kaybı var; yaklaşık hesap iznini açıkça seçin."
                )
            losses += 1
        return out

    groups, labels, members, arrays = [], [], [], []
    if spec.path == "paired":
        pairs = {}
        for row in rows:
            control.check()
            phase = row[names[spec.group]]
            if phase is None:
                excluded["null_rows"] += 1
                continue
            if str(phase) not in (spec.before, spec.after):
                excluded["unselected_phase_rows"] += 1
                continue
            key = row[names[spec.key]]
            if key is None or isinstance(key, float) and not math.isfinite(key):
                excluded["missing_key_rows"] += 1
                continue
            person = pairs.setdefault(key, {})
            tag = str(phase)
            if tag in person:
                raise ProjectError(
                    "Aynı kişi anahtarı/ölçüm etiketi birden çok kez var. Eşleştirme belirsiz; önce tekrarları inceleyin."
                )
            person[tag] = row
        if excluded["missing_key_rows"]:
            raise ProjectError(
                f"{excluded['missing_key_rows']} kayıtta kişi anahtarı eksik/geçersiz; satır sırasıyla eşleştirme yapılmaz."
            )
        before, after = [], []
        for person in pairs.values():
            if set(person) != {spec.before, spec.after}:
                excluded["unmatched_people"] += 1
                continue
            a, b = person[spec.before], person[spec.after]
            va, vb = valid(a, [spec.x]), valid(b, [spec.x])
            if not (va and vb):
                excluded["incomplete_pairs"] += 1
                continue
            before.append(number(a[names[spec.x]]))
            after.append(number(b[names[spec.x]]))
            members.extend([a["__vu_row_id"], b["__vu_row_id"]])
        if excluded["unmatched_people"] and spec.pair_policy == "reject":
            raise ProjectError(
                f"{excluded['unmatched_people']} kişi yalnız bir ölçümde var. Anahtarı/etiketi düzeltin veya 'yalnız tam eşler' seçimini açıkça yapın."
            )
        arrays = [np.asarray(after), np.asarray(before)]
        groups, labels = arrays, [spec.after, spec.before]
    elif spec.path in ("independent", "groups"):
        buckets = {}
        # Keep observed groups even if every measurement is missing, so no group silently disappears.
        for row in rows:
            control.check()
            group = row[names[spec.group]]
            if group is not None and not (
                isinstance(group, float) and not math.isfinite(group)
            ):
                buckets.setdefault(group, [])
            if not valid(row, [spec.x, spec.group]):
                continue
            buckets[group].append(number(row[names[spec.x]]))
            members.append(row["__vu_row_id"])
            if len(buckets) > MAX_GROUPS:
                raise ProjectError(
                    "En fazla20 grup desteklenir; açık kapsam filtresi seçin."
                )
        labels = [
            str(k) for k in sorted(buckets, key=lambda k: (type(k).__name__, str(k)))
        ]
        groups = [
            np.asarray(buckets[k])
            for k in sorted(buckets, key=lambda k: (type(k).__name__, str(k)))
        ]
        if (
            spec.path == "independent"
            and len(groups) != 2
            or spec.path == "groups"
            and not 3 <= len(groups) <= MAX_GROUPS
        ):
            raise ProjectError(
                "Bu soruda tam iki veya en az üç geçerli grup gerekir; grup sütununu/kapsamı kontrol edin."
            )
    elif spec.path == "numeric":
        a, b = [], []
        for row in rows:
            control.check()
            if valid(row, [spec.x, spec.y]):
                a.append(number(row[names[spec.x]]))
                b.append(number(row[names[spec.y]]))
                members.append(row["__vu_row_id"])
        arrays = [np.asarray(a), np.asarray(b)]
        groups, labels = arrays, [names[spec.x], names[spec.y]]
    else:
        complete = []
        for row in rows:
            control.check()
            if valid(row, [spec.x, spec.y]):
                complete.append((row[names[spec.x]], row[names[spec.y]]))
                members.append(row["__vu_row_id"])
        cats = [
            sorted({v[i] for v in complete}, key=lambda v: (type(v).__name__, str(v)))
            for i in (0, 1)
        ]
        if any(not 2 <= len(c) <= MAX_GROUPS for c in cats):
            raise ProjectError(
                "Kategorik ilişki için her alanda2–20 gözlenen kategori gerekir."
            )
        table = np.zeros((len(cats[0]), len(cats[1])), dtype=int)
        lookup = [{v: i for i, v in enumerate(c)} for c in cats]
        for a, b in complete:
            table[lookup[0][a], lookup[1][b]] += 1
        arrays = [table]
        groups, labels = [table.sum(axis=1)], [str(c) for c in cats[0]]

    notes = [
        ASSUMPTIONS[spec.method],
        "Normalite testi yöntemi otomatik seçmez. Dağılım grafikleri, örneklem büyüklüğü, uç değerler ve tasarım birlikte incelenmelidir.",
        CAUTION,
    ]
    if spec.path != "categorical":
        minimum = 5 if spec.method == "kruskal" else 3 if spec.path == "numeric" else 2
        if any(len(g) < minimum for g in groups):
            raise ProjectError(
                f"Yetersiz veri: her grupta/eş çiftinde en az{minimum} geçerli gözlem gerekir."
            )
        if spec.method in (
            "welch_t",
            "anova",
            "welch_anova",
            "paired_t",
            "pearson",
            "spearman",
        ):
            check_groups = [arrays[0] - arrays[1]] if spec.path == "paired" else groups
            if any(np.ptp(g) == 0 or np.var(g, ddof=1) <= 0 for g in check_groups):
                raise ProjectError(
                    "Sıfır varyans/sabit ölçüm veya sabit kişi içi fark; bu sürümde seçili yöntemin pozitif varyans önkoşulu sağlanmıyor."
                )
        if spec.method == "wilcoxon" and np.all(arrays[0] == arrays[1]):
            raise ProjectError(
                "Bütün kişi içi farklar sıfır; Wilcoxon sıraları tanımlanamıyor."
            )
        if spec.method == "wilcoxon":
            active_n = int(np.sum(arrays[0] != arrays[1]))
            if active_n < 2:
                raise ProjectError(
                    "Wilcoxon için sıfır farklar çıkarıldıktan sonra en az2 eş gerekir."
                )
            notes.append(
                f"Wilcoxon: {len(arrays[0]) - active_n} sıfır fark sıralardan çıkarılır; {active_n} eş sıralanır. Bağlı/sıfır fark varsa p asimptotiktir; küçük örneklem sınırlıdır."
            )
        if spec.method == "kruskal" and np.ptp(np.concatenate(groups)) == 0:
            raise ProjectError(
                "Bütün gruplarda ölçüm sabit; Kruskal–Wallis tanımlanamıyor."
            )
        if any(len(g) < 30 for g in groups):
            notes.append(
                "Küçük örneklem: dağılım/uç değer varsayımlarını özellikle inceleyin; önkontrol geçmesi yeterli güç garantisi değildir."
            )
        if spec.method == "spearman" and len(arrays[0]) <= 500:
            notes.append(
                "Spearman p asimptotiktir; n≤500 için hassasiyet sınırlıdır. Bu sürüm permutation p sunmaz."
            )
        if spec.method in ("mann_whitney", "wilcoxon", "kruskal"):
            notes.append(
                "Bağlı sıralar ortalama sıra ile işlenir; sıralama yöntemleri genel olarak yalnız medyan farkını sınamaz."
            )
    else:
        table = arrays[0]
        expected = stats.contingency.expected_freq(table)
        if spec.method == "fisher" and table.shape != (2, 2):
            raise ProjectError(
                "Fisher exact bu sürümde yalnız2×2 tabloda kullanılabilir."
            )
        if spec.method == "chi2" and np.any(expected < 5):
            raise ProjectError(
                "Beklenen hücre frekansı5'ten küçük; ki-kare önkoşulu sağlanmıyor.2×2 ise Fisher seçin; diğer tablolar için daha fazla veri gerekir."
            )
        notes.append(
            "Kategori sırası kayıtlıdır; Fisher odds oranı satır/sütun sırasına bağlıdır."
        )
    if losses:
        notes.append(
            f"{losses} ölçümde Float64 yaklaşımı kullanıcı izniyle kullanıldı; kesin Decimal çıkarımı değildir."
        )
    if excluded["unmatched_people"] or excluded["incomplete_pairs"]:
        notes.append(
            "Yalnız tam eşler analiz edildi; eşleşmeyen/eksik kişilerin dışlanması seçilim yanlılığı oluşturabilir."
        )
    info = dict(
        method=spec.method,
        method_label=LABELS[spec.method],
        n=[len(g) for g in groups]
        if spec.path != "categorical"
        else int(arrays[0].sum()),
        group_labels=labels,
        population_n=count,
        dataset_n=request["row_count"],
        used_rows=len(members),
        excluded_rows=count - len(members),
        exclusions=excluded,
        precision_loss_values=losses,
        warnings=notes,
        summaries=[
            dict(
                label=label,
                n=len(g),
                mean=scalar(np.mean(g)),
                std=scalar(np.std(g, ddof=1)),
                median=scalar(np.median(g)),
                minimum=scalar(np.min(g)),
                maximum=scalar(np.max(g)),
                q25=scalar(np.quantile(g, 0.25)),
                q75=scalar(np.quantile(g, 0.75)),
            )
            for label, g in zip(labels, groups)
        ]
        if spec.path != "categorical"
        else [],
    )
    if spec.path == "categorical":
        info.update(
            table=arrays[0].tolist(),
            row_labels=[str(c) for c in cats[0]],
            column_labels=[str(c) for c in cats[1]],
            expected=expected.tolist(),
        )
    if spec.path == "paired":
        difference = arrays[0] - arrays[1]
        info["difference_summary"] = dict(
            n=len(difference),
            mean=scalar(np.mean(difference)),
            std=scalar(np.std(difference, ddof=1)),
            minimum=scalar(np.min(difference)),
            maximum=scalar(np.max(difference)),
            zero_differences=int(np.sum(difference == 0)),
        )
    checked(request, control)
    return info, groups, arrays, members


def effect(
    name,
    value,
    ci=None,
    reason="Bu yöntem/etki için doğrulanmış güven aralığı bu sürümde sunulmuyor; bootstrap yapılmadı.",
):
    return dict(
        name=name,
        value=scalar(value),
        confidence_interval=ci,
        ci_limitation="" if ci else reason,
    )


def test(method, groups, arrays, alternative, confidence):
    if method in ("welch_t", "paired_t"):
        a, b = arrays if method == "paired_t" else groups
        result = (
            stats.ttest_rel(a, b, alternative=alternative)
            if method == "paired_t"
            else stats.ttest_ind(a, b, equal_var=False, alternative=alternative)
        )
        interval = result.confidence_interval(confidence_level=confidence)
        out = effect(
            "Ortalama farkı (sonra−önce)"
            if method == "paired_t"
            else "Ortalama farkı (ilk grup−ikinci grup)",
            np.mean(a) - np.mean(b),
            dict(
                low=scalar(interval.low),
                high=scalar(interval.high),
                level=confidence,
                method="t dağılımı",
                target="ortalama farkı",
            ),
        )
        extras = dict(df=scalar(result.df))
    elif method == "mann_whitney":
        a, b = groups
        ties = len(np.unique(np.concatenate(groups))) < len(a) + len(b)
        algorithm = "exact" if min(len(a), len(b)) <= 8 and not ties else "asymptotic"
        result = stats.mannwhitneyu(
            a, b, alternative=alternative, method=algorithm, use_continuity=True
        )
        out = effect(
            "Sıra biserial korelasyonu (ilk grubun üstünlüğü)",
            2 * result.statistic / (len(a) * len(b)) - 1,
        )
        extras = dict(
            p_algorithm=algorithm,
            ties=ties,
            continuity_correction=algorithm == "asymptotic",
        )
    elif method == "wilcoxon":
        diff = arrays[0] - arrays[1]
        active = diff[diff != 0]
        ties = len(np.unique(np.abs(active))) != len(active)
        algorithm = (
            "exact"
            if not ties and len(active) == len(diff) and len(active) <= 50
            else "asymptotic"
        )
        result = stats.wilcoxon(
            diff,
            zero_method="wilcox",
            correction=False,
            alternative=alternative,
            method=algorithm,
        )
        ranks = stats.rankdata(np.abs(active), method="average")
        out = effect(
            "Eşleştirilmiş sıra biserial korelasyonu (sonra−önce)",
            np.sum(ranks * np.sign(active)) / np.sum(ranks),
        )
        extras = dict(
            p_algorithm=algorithm,
            zero_differences=int(np.sum(diff == 0)),
            ranked_pairs=len(active),
            zero_method="wilcox",
            ties=ties,
            difference_precision="Float64 sonra−önce; yaklaşık eşitlik/yuvarlama otomatik uygulanmaz",
        )
    elif method in ("anova", "welch_anova"):
        result = stats.f_oneway(*groups, equal_var=method == "anova")
        mean = np.mean(np.concatenate(groups))
        between = sum(len(g) * (np.mean(g) - mean) ** 2 for g in groups)
        total = sum(np.sum((g - mean) ** 2) for g in groups)
        out = effect("Eta-kare (betimsel grup varyansı payı)", between / total)
        extras = dict(
            equal_var=method == "anova",
            effect_limitation="Eta-kare örneklem betimidir; Welch ANOVA için eşit varyanslı çıkarım değildir.",
        )
    elif method == "kruskal":
        result = stats.kruskal(*groups)
        n, k = sum(map(len, groups)), len(groups)
        out = effect(
            "Epsilon-kare (sıra etkisi; negatif tahmin0'a kırpılır)",
            max(0, (result.statistic - k + 1) / (n - k)),
        )
        extras = dict(df=k - 1, ties_correction=True)
    elif method == "chi2":
        table = arrays[0]
        result = stats.chi2_contingency(table, correction=False)
        out = effect(
            "Cramér V",
            math.sqrt(
                result.statistic
                / (table.sum() * min(table.shape[0] - 1, table.shape[1] - 1))
            ),
        )
        extras = dict(df=int(result.dof), yates_correction=False)
    elif method == "fisher":
        table = arrays[0]
        result = stats.fisher_exact(table, alternative=alternative)
        odds = odds_ratio(table, kind="conditional")
        interval = odds.confidence_interval(
            confidence_level=confidence, alternative=alternative
        )
        out = effect(
            "Koşullu odds oranı (satır1/satır2; sütun1/sütun2)",
            odds.statistic,
            dict(
                low=scalar(interval.low),
                high=scalar(interval.high),
                level=confidence,
                method="Koşullu exact",
                target="odds oranı",
            ),
        )
        extras = dict(
            statistic_name="Örneklem odds oranı; etki koşullu odds oranıdır",
            p_algorithm="exact fixed margins",
        )
    else:
        a, b = arrays
        result = (
            stats.pearsonr(a, b, alternative=alternative)
            if method == "pearson"
            else stats.spearmanr(a, b, alternative=alternative)
        )
        ci = None
        if method == "pearson" and len(a) > 3:
            interval = result.confidence_interval(confidence_level=confidence)
            ci = dict(
                low=scalar(interval.low),
                high=scalar(interval.high),
                level=confidence,
                method="Fisher-z",
                target="Pearson korelasyonu",
            )
        out = effect(
            "Pearson r" if method == "pearson" else "Spearman rho", result.statistic, ci
        )
        extras = dict(
            p_algorithm="beta exact under normal null"
            if method == "pearson"
            else "asymptotic t approximation"
        )
    p = float(result.pvalue)
    if not math.isfinite(p) or not 0 <= p <= 1 or scalar(result.statistic) is None:
        raise ProjectError(
            "Sayısal sonuç tanımlanamadı; sabit/çok küçük varyansı ve ölçüm ölçeğini inceleyin."
        )
    return dict(
        method=method,
        statistic=scalar(result.statistic),
        p_value=p,
        effect=out,
        details=extras,
    )


def calculate(request, spec, workspace, control=None, preflight=False):
    control = control or Control()
    spec = spec if isinstance(spec, AnalysisSpec) else AnalysisSpec.from_dict(spec)
    spec.validate(request["columns"], run=not preflight)
    if spec.path == "dimensions":
        from veri_ufku.statistics.dimensions import calculate as dimensions

        return dimensions(request, spec, workspace, control, preflight)
    if spec.path == "survival":
        from veri_ufku.statistics.survival import calculate as survival

        return survival(request, spec, workspace, control, preflight)
    if spec.path == "causal":
        from veri_ufku.statistics.causal import calculate as causal

        return causal(request, spec, workspace, control, preflight)
    if spec.path == "bayes":
        from veri_ufku.statistics.bayes import calculate as bayes

        return bayes(request, spec, workspace, control, preflight)
    if spec.path == "experiments":
        from veri_ufku.statistics.experiments import calculate as experiments

        return experiments(request, spec, workspace, control, preflight)
    if spec.path == "resampling":
        from veri_ufku.statistics.resampling import calculate as resampling

        return resampling(request, spec, workspace, control, preflight)
    if spec.path == "models":
        from veri_ufku.statistics.models import calculate as models

        return models(request, spec, workspace, control, preflight)
    if spec.path == "advanced":
        from veri_ufku.statistics.missing_sampling import calculate as advanced

        return advanced(request, spec, workspace, control, preflight)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        info, groups, arrays, members = prepare(request, spec, control)
        if preflight:
            return dict(
                info,
                spec=spec.data(),
                dataset_version=request["version_id"],
                config_revision=request.get("config_revision", 0),
            )
        control.progress("İstatistik hesaplanıyor", 0, None)
        primary = test(spec.method, groups, arrays, spec.alternative, spec.confidence)
        primary["n"] = info["n"]
        primary["excluded_rows"] = info["excluded_rows"]
        comparisons = []
        if spec.posthoc == "pairwise":
            method = "mann_whitney" if spec.method == "kruskal" else "welch_t"
            for i, j in itertools.combinations(range(len(groups)), 2):
                control.check()
                comparison = test(
                    method, [groups[i], groups[j]], [], "two-sided", spec.confidence
                )
                comparison.update(
                    groups=[info["group_labels"][i], info["group_labels"][j]],
                    n=[len(groups[i]), len(groups[j])],
                )
                comparisons.append(comparison)
            for comparison, p in zip(
                comparisons,
                adjusted([r["p_value"] for r in comparisons], spec.correction),
            ):
                comparison["p_adjusted"] = p
            info["warnings"].append(
                "Post-hoc ailesi: seçili kapsamın bütün grup çiftleri. Kruskal sonrası Mann–Whitney, diğerlerinde Welch t kullanılır; Dunn/Tukey testi değildir. CI'lar tek karşılaştırma içindir; eşzamanlı aile CI değildir."
            )
        if spec.correction == "none":
            info["warnings"].append(
                "Çoklu test düzeltmesi seçilmedi. Başka ayrı analizlerdeki p-değerleri bu aileye otomatik dahil edilmez."
            )
        if caught:
            info["warnings"].append(
                "Sayısal kütüphane uyarısı oluştu; varsayımlar ve güven aralığı sınırları incelenmelidir."
            )
    checked(request, control)
    from veri_ufku.domain.capabilities import get_capability

    capability = get_capability("statistics." + spec.method.replace("_", "-"))
    result = dict(
        info,
        method_version=capability.semantic_version,
        parameter_version=capability.version,
        primary=primary,
        comparisons=comparisons,
        spec=spec.data(),
        dataset_version=request["version_id"],
        config_revision=request.get("config_revision", 0),
        result_version="analysis:" + uid(),
        correction=dict(
            method=spec.correction,
            family="all selected group pairs" if comparisons else "single analysis",
            family_size=len(comparisons) or 1,
            scope="this run only",
            ci_adjusted=False,
        ),
        provenance=dict(
            snapshot_fingerprint=request["fingerprint"],
            snapshot_uri=request["snapshot_uri"],
            source_snapshot_id=request["source_snapshot_id"],
            array_source=request.get("format_metadata", {}),
            backend="scipy",
            scipy_version=scipy.__version__,
            numpy_version=np.__version__,
            schema="AnalysisResult/v1",
            help_content_version=15,
            bootstrap=None,
            seed=None,
            independence="between observation units; within-person pairs kept together"
            if spec.path == "paired"
            else "independent observation units",
        ),
    )
    directory = Path(workspace)
    membership = directory / "analysis-members.parquet"
    pl.DataFrame({"row_id": members}, schema={"row_id": pl.String}).write_parquet(
        membership
    )
    content = json.dumps(
        result, ensure_ascii=False, allow_nan=False, sort_keys=True
    ).encode()
    destination = directory / "analysis-result.json"
    destination.write_bytes(content)
    result["paths"] = dict(result=str(destination), members=str(membership))
    result["fingerprints"] = {
        k: hash_artifact(Path(v), control) for k, v in result["paths"].items()
    }
    result["member_digest"] = hashlib.sha256("\n".join(members).encode()).hexdigest()
    control.disk(directory)
    control.check()
    return result
