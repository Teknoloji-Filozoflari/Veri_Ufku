"""Native bounded Apriori and conditional FP-tree; independent reference tested."""

import itertools
from collections import Counter

from veri_ufku.storage.project_model import ProjectError


def mine(baskets, spec, control):
    n = len(baskets)
    items = sorted(set.union(*(set(b) for b in baskets)))
    if len(items) > 64 or n > 2000:
        raise ProjectError(
            "Basket önkontrolü:64item/2000transaction sınırı; sessiz sampling yok."
        )
    tested = 0
    frequent = {}

    def count_candidate():
        nonlocal tested
        control.check()
        tested += 1
        if tested > spec.candidate_budget:
            raise ProjectError(
                "Candidate/node bütçesi aşıldı; eksik sonuç tamamlandı sayılmaz."
            )

    if spec.task == "apriori":
        candidates = [(i,) for i in items]
        for size in range(1, spec.max_length + 1):
            level = []
            for candidate in candidates:
                count_candidate()
                count = sum(set(candidate) <= b for b in baskets)
                if count / n >= spec.min_support:
                    frequent[candidate] = count
                    level.append(candidate)
            if size == spec.max_length:
                break
            previous = set(level)
            candidates_set = set()
            for j, left in enumerate(level):
                control.check()
                for right in level[j + 1 :]:
                    if left[:-1] != right[:-1]:
                        continue
                    merged = tuple(sorted(set(left) | set(right)))
                    if len(merged) == size + 1 and all(
                        tuple(part) in previous
                        for part in itertools.combinations(merged, size)
                    ):
                        candidates_set.add(merged)
                        if len(candidates_set) + tested > spec.candidate_budget:
                            raise ProjectError(
                                "Apriori candidate join önkontrol bütçesi aşıldı."
                            )
            candidates = sorted(candidates_set)
            if not candidates:
                break
    else:

        class Node:
            def __init__(self, item=None, parent=None):
                self.item, self.parent, self.count, self.children = item, parent, 0, {}

        def tree(paths):
            counts = Counter()
            for path, weight in paths:
                control.check()
                for i in path:
                    counts[i] += weight
            counts = {i: c for i, c in counts.items() if c / n >= spec.min_support}
            root, header = Node(), {i: [] for i in counts}
            for path, weight in paths:
                node = root
                for item in sorted(
                    (i for i in path if i in counts), key=lambda i: (-counts[i], i)
                ):
                    control.check()
                    if item not in node.children:
                        count_candidate()
                        node.children[item] = Node(item, node)
                        header[item].append(node.children[item])
                    node = node.children[item]
                    node.count += weight
            return counts, header

        def grow(paths, suffix):
            counts, header = tree(paths)
            for item in sorted(counts, key=lambda i: (counts[i], i)):
                control.check()
                key = tuple(sorted((*suffix, item)))
                frequent[key] = counts[item]
                if len(frequent) > spec.candidate_budget:
                    raise ProjectError("FP frequent itemset bütçesi aşıldı.")
                if len(key) >= spec.max_length:
                    continue
                conditional = []
                for node in header[item]:
                    prefix, parent = [], node.parent
                    while parent and parent.item is not None:
                        prefix.append(parent.item)
                        parent = parent.parent
                    if prefix:
                        conditional.append((prefix, node.count))
                if conditional:
                    grow(conditional, key)

        grow([(sorted(b), 1) for b in baskets], ())
    rules, examined = [], 0
    for full, count in sorted(frequent.items()):
        for size in range(1, len(full)):
            for part in itertools.combinations(full, size):
                control.check()
                examined += 1
                if examined > spec.rule_budget:
                    raise ProjectError(
                        "Rule keşif bütçesi aşıldı; eksik liste başarılı sayılmaz."
                    )
                other = tuple(i for i in full if i not in part)
                confidence = count / frequent[part]
                if confidence >= spec.min_confidence:
                    rules.append(
                        dict(
                            antecedent=list(part),
                            consequent=list(other),
                            support=count / n,
                            count=count,
                            confidence=confidence,
                            lift=confidence / (frequent[other] / n),
                        )
                    )
    return dict(
        transaction_total=n,
        distinct_items=len(items),
        candidates_or_nodes=tested,
        rules_examined=examined,
        itemsets=[
            dict(items=list(k), count=v, support=v / n)
            for k, v in sorted(frequent.items())
        ],
        rules=rules,
        denominator="all declared transaction IDs including explicit empty baskets; different IDs with identical contents retained",
        discovery="exploratory multiple search; no p-value/FDR or causality claim",
    )
