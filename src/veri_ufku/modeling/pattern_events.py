"""Calendar cohorts, censored sequential funnels, and observed directly-follows graphs."""

from collections import Counter
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from veri_ufku.storage.project_model import ProjectError


def period_start(t, zone, period):
    dt = datetime.fromtimestamp(t, ZoneInfo(zone))
    d = dt.date()
    if period == "week":
        d -= timedelta(days=d.weekday())
    elif period == "month":
        d = d.replace(day=1)
    result = datetime(d.year, d.month, d.day, tzinfo=dt.tzinfo)
    if datetime.fromtimestamp(result.timestamp(), dt.tzinfo).replace(
        tzinfo=None
    ) != result.replace(tzinfo=None):
        raise ProjectError(
            "Timezone dönem sınırı nonexistent; başka açık sınır/takvim gerekir."
        )
    return result


def advance(dt, period, count=1):
    if period == "month":
        m = dt.year * 12 + dt.month - 1 + count
        return dt.replace(year=m // 12, month=m % 12 + 1)
    return dt + timedelta(days=count * (7 if period == "week" else 1))


def ordered(rows, spec):
    keys = [
        (r["entity"], r["time"], r["order"] if spec.ties == "order" else None)
        for r in rows
    ]
    if len(set(keys)) != len(keys):
        raise ProjectError(
            "Eşit timestamp belirsiz: unique kaynak sıra kolonu seçin veya tie'ı kaynakta çözün."
        )
    return sorted(rows, key=lambda r: (r["entity"], r["time"], r["order"] or 0))


def cohort(rows, spec, control):
    groups = {}
    excluded = []
    for who in sorted({r["entity"] for r in rows}):
        control.check()
        events = sorted(
            (r for r in rows if r["entity"] == who), key=lambda r: r["time"]
        )
        starts = (
            events
            if spec.cohort_start == "first_observed"
            else [r for r in events if r["activity_raw"] == spec.start_activity]
        )
        if not starts:
            excluded.append(who)
            continue
        origin = starts[0]["time"]
        key = period_start(origin, spec.timezone, spec.period)
        groups.setdefault(key, []).append(
            (who, origin, [r for r in events if r["time"] >= origin])
        )
    cells = []
    for start, people in sorted(groups.items()):
        denominator_events = sum(
            sum(
                start.timestamp() <= r["time"] < advance(start, spec.period).timestamp()
                for r in events
            )
            for _, _, events in people
        )
        for i in range(24):
            control.check()
            left, right = (
                advance(start, spec.period, i),
                advance(start, spec.period, i + 1),
            )
            if left.timestamp() >= spec.observation_end:
                break
            active = [
                r
                for _, _, events in people
                for r in events
                if left.timestamp() <= r["time"] < right.timestamp()
            ]
            complete = (
                start.timestamp() >= spec.observation_start
                and right.timestamp() <= spec.observation_end
            )
            denominator = len(people) if spec.unit == "person" else denominator_events
            count = (
                len({r["entity"] for r in active})
                if spec.unit == "person"
                else len(active)
            )
            cells.append(
                dict(
                    cohort=start.isoformat(),
                    period_index=i,
                    period_start=left.isoformat(),
                    period_end=right.isoformat(),
                    cohort_people=len(people),
                    denominator=denominator,
                    observed_count=count,
                    complete=complete,
                    right_censored=right.timestamp() > spec.observation_end,
                    left_truncated=start.timestamp() < spec.observation_start,
                    retention=count / denominator if complete and denominator else None,
                    row_ids=[r["row_id"] for r in active],
                )
            )
        if advance(start, spec.period, 24).timestamp() < spec.observation_end:
            raise ProjectError("Cohort24period bütçesi; daha dar gözlem aralığı seçin.")
    return dict(
        cells=cells,
        excluded_entities_without_start=excluded,
        unit=spec.unit,
        denominator="initial cohort people"
        if spec.unit == "person"
        else "period0 event count of cohort; event-volume ratio, may exceed1; not person retention",
        cohort_start=spec.cohort_start,
        timezone=spec.timezone,
        observation_end=spec.observation_end,
    )


def funnel(rows, spec, control):
    rows = ordered(rows, spec)
    attempts = []
    for who in sorted({r["entity"] for r in rows}):
        control.check()
        events = [r for r in rows if r["entity"] == who]
        starts = [
            i for i, r in enumerate(events) if r["activity_raw"] == spec.stages[0]
        ]
        if spec.unit == "person":
            starts = starts[:1]
        for j, index in enumerate(starts):
            anchor = events[index]
            end = anchor["time"] + spec.window_seconds
            stop = (
                starts[j + 1]
                if spec.unit == "event" and j + 1 < len(starts)
                else len(events)
            )
            if stop < len(events):
                end = min(end, events[stop]["time"])
            reached, selected = 1, [anchor["row_id"]]
            for r in events[index + 1 : stop]:
                control.check()
                if r["time"] >= end or reached == len(spec.stages):
                    break
                if r["activity_raw"] == spec.stages[reached]:
                    reached += 1
                    selected.append(r["row_id"])
            attempts.append(
                dict(
                    entity=who,
                    anchor_row_id=anchor["row_id"],
                    start=anchor["time"],
                    deadline=end,
                    complete=end <= spec.observation_end,
                    reached=reached,
                    row_ids=selected,
                )
            )
    mature = [a for a in attempts if a["complete"]]
    return dict(
        unit=spec.unit,
        attempts=attempts,
        denominator=len(mature),
        censored_attempts=len(attempts) - len(mature),
        stages=[
            dict(
                activity=stage,
                count=sum(a["reached"] > i for a in mature),
                observed_including_censored=sum(a["reached"] > i for a in attempts),
                fraction=sum(a["reached"] > i for a in mature) / len(mature)
                if mature
                else None,
            )
            for i, stage in enumerate(spec.stages)
        ],
        policy="person: first start per person; event: each stage0 is an attempt cut at next stage0; strictly ordered events; deadline exclusive; rates only fully observed attempts",
    )


def process(rows, spec, control):
    rows = ordered(rows, spec)
    edges, nodes, starts, ends = Counter(), Counter(), Counter(), Counter()
    traces = []
    model = spec.conformance
    for case in sorted({r["entity"] for r in rows}):
        control.check()
        events = [r for r in rows if r["entity"] == case]
        flags = {r["complete"] for r in events}
        if len(flags) > 1:
            raise ProjectError("Case complete bayrağı trace boyunca sabit olmalı.")
        complete = flags == {True}
        activities = [r["activity_raw"] for r in events]
        nodes.update(activities)
        starts[activities[0]] += 1
        if complete:
            ends[activities[-1]] += 1
        transitions = list(zip(activities, activities[1:]))
        edges.update(transitions)
        violations = []
        if model:
            allowed = {tuple(pair) for pair in model["edges"]}
            if activities[0] not in model["starts"]:
                violations.append(
                    dict(
                        kind="start", activity=activities[0], row_id=events[0]["row_id"]
                    )
                )
            for i, pair in enumerate(transitions):
                if pair not in allowed:
                    violations.append(
                        dict(
                            kind="transition",
                            source=pair[0],
                            target=pair[1],
                            row_ids=[events[i]["row_id"], events[i + 1]["row_id"]],
                        )
                    )
            if complete and activities[-1] not in model["ends"]:
                violations.append(
                    dict(
                        kind="end", activity=activities[-1], row_id=events[-1]["row_id"]
                    )
                )
        traces.append(
            dict(
                case=case,
                activities=activities,
                row_ids=[r["row_id"] for r in events],
                complete=complete,
                completion="declared complete"
                if complete
                else "incomplete/unknown; no terminal activity inferred",
                violations=violations,
                fitting=False if violations else True if model and complete else None,
                elapsed_seconds=events[-1]["time"] - events[0]["time"],
            )
        )
    if len(nodes) > 32:
        raise ProjectError("Process32activity önkontrol sınırı.")
    return dict(
        nodes=[dict(activity=k, count=v) for k, v in sorted(nodes.items())],
        edges=[
            dict(source=a, target=b, count=v) for (a, b), v in sorted(edges.items())
        ],
        starts=dict(starts),
        complete_ends=dict(ends),
        traces=traces,
        incomplete_traces=sum(not t["complete"] for t in traces),
        conformance_backend="native ActivityTransitionModel/v1 allowed starts/adjacent transitions/ends; no Petri token replay, concurrency or alignment fitness"
        if model
        else None,
        fitting_complete=sum(t["fitting"] is True for t in traces),
        graph_meaning="observed directly-follows counts including partial traces; cycles/repeats allowed; not causal DAG",
    )
