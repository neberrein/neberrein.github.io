#!/usr/bin/env python3
"""Build only the marked MANTA results block from measured experiment logs.

No dependencies, default speeds, invented trajectories or inferred verdicts.
Missing input is a no-op; malformed input fails before changing the page.
"""
import argparse
import csv
import hashlib
import html
import json
import math
import re
import statistics as stats
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- MANTA_RESULTS_AUTO_START -->"
END = "<!-- MANTA_RESULTS_AUTO_END -->"
SCENARIOS = ("front", "rear", "side", "diag")
PLANNERS = ("astar", "dvo")
LABEL = {"astar": "A*", "dvo": "Dynamic VO", "front": "정면", "rear": "후방", "side": "측면", "diag": "대각"}
COLOR = {"astar": "#2b73b8", "dvo": "#23774a"}
RUN_COLS = "run_id scenario planner mode torpedo outcome closest_m engagements avoided_count avoided_margins plan_count plan_ms_mean plan_ms_median plan_ms_max reaction_sec duration_sec".split()
PLAN_COLS = "run_id t_rel planner ms waypoints boxes vo_active".split()
EVENT_COLS = "run_id t_rel type value".split()
NUMERIC = "closest_m engagements avoided_count plan_count plan_ms_mean plan_ms_median plan_ms_max reaction_sec duration_sec".split()
INTEGERS = {"engagements", "avoided_count", "plan_count"}
EVENT_TYPES = {"MODE_AVOID", "MODE_NORMAL", "ENGAGE", "AVOIDED", "HIT", "RESET"}


def number(value, label, optional=False):
    if value is None or str(value).strip() == "":
        if optional:
            return None
        raise ValueError(f"{label}: 숫자 누락")
    try:
        result = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{label}: 숫자 형식 오류") from exc
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"{label}: 유한한 0 이상의 값 필요")
    return result


def read_csv(path, required):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError(f"{path.name}: 비어 있거나 중복된 헤더")
        missing = set(required) - set(reader.fieldnames)
        if missing:
            raise ValueError(f"{path.name}: 필수 열 누락 {sorted(missing)}")
        rows = []
        for index, row in enumerate(reader, 2):
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"{path.name}:{index}: 열 개수 불일치")
            rows.append({k: v.strip() for k, v in row.items()})
        return rows


def normalize_torpedo(value):
    aliases = {"청상어": "청상어", "blue_shark": "청상어", "blueshark": "청상어", "백상어": "백상어", "white_shark": "백상어", "whiteshark": "백상어", "mk48": "Mk48"}
    key = value.lower().replace(" ", "").replace("-", "")
    if key not in aliases:
        raise ValueError(f"torpedo: 알 수 없는 값 {value}")
    return aliases[key]


def combo(row):
    return tuple(row[k] for k in ("scenario", "planner", "mode", "torpedo"))


def newest(group, warnings):
    if len(group) == 1:
        return group[0], "unique valid combination"
    for field in ("timestamp", "index"):
        if not all(row.get(field) for row in group):
            continue
        try:
            if field == "timestamp":
                keys = [datetime.fromisoformat(row[field].replace("Z", "+00:00")) for row in group]
                if any(k.tzinfo is None for k in keys):
                    raise ValueError("timezone required")
            else:
                keys = [number(row[field], "index") for row in group]
                if any(not k.is_integer() for k in keys):
                    raise ValueError("integer required")
            if len(set(keys)) != len(keys):
                continue
            return group[keys.index(max(keys))], f"latest valid run by explicit {field}"
        except (ValueError, TypeError):
            continue
    warnings.append(f"중복 조합 제외(최신 유효 실행의 기준 모호): {combo(group[0])}")
    return None, "ambiguous duplicate combination excluded"


def load_inputs(folder):
    required = ("runs.csv", "plans.csv", "events.csv", "collect_log.txt", "scale_info.txt", "params.txt")
    for name in required:
        if not (folder / name).is_file():
            raise ValueError(f"필수 파일 누락: {name}")
    runs = read_csv(folder / "runs.csv", RUN_COLS)
    if not runs:
        raise ValueError("runs.csv: 측정 행 없음")
    warnings, invalid, selections = [], [], []
    ids = Counter(row["run_id"] for row in runs)
    groups = defaultdict(list)
    for row in runs:
        rid = row["run_id"]
        if not rid:
            raise ValueError("run_id 누락")
        if row["scenario"] not in SCENARIOS or row["planner"] not in PLANNERS:
            raise ValueError(f"{rid}: scenario/planner 허용 값 오류")
        modes = {"simpletracking": "SimpleTracking", "simple_tracking": "SimpleTracking", "png": "PNG"}
        if row["mode"].lower() not in modes:
            raise ValueError(f"{rid}: mode는 SimpleTracking 또는 PNG여야 함")
        row["mode"] = modes[row["mode"].lower()]
        row["torpedo"] = normalize_torpedo(row["torpedo"])
        if row["outcome"] not in {"HIT", "AVOIDED"} and not re.fullmatch(r"INVALID_[A-Za-z0-9_]+", row["outcome"]):
            raise ValueError(f"{rid}: outcome 허용 값 오류")
        valid = row["outcome"] in {"HIT", "AVOIDED"}
        for key in NUMERIC:
            row[key] = number(row[key], f"{rid}/{key}", optional=not valid or key == "reaction_sec")
            if key in INTEGERS and row[key] is not None and not row[key].is_integer():
                raise ValueError(f"{rid}/{key}: 정수 필요")
        row["avoided_margins"] = [number(x, f"{rid}/avoided_margins") for x in row["avoided_margins"].split("|")] if row["avoided_margins"] else []
        if row["avoided_count"] is not None and len(row["avoided_margins"]) != row["avoided_count"]:
            raise ValueError(f"{rid}: avoided_count와 avoided_margins 개수 불일치")
        if valid and row["avoided_count"] > row["engagements"]:
            raise ValueError(f"{rid}: avoided_count > engagements")
        if valid and not (row["plan_ms_median"] <= row["plan_ms_max"] and row["plan_ms_mean"] <= row["plan_ms_max"]):
            raise ValueError(f"{rid}: 계획 시간 통계 불일치")
        if row["reaction_sec"] is not None and row["duration_sec"] is not None and row["reaction_sec"] > row["duration_sec"]:
            raise ValueError(f"{rid}: reaction_sec > duration_sec")
        reason = None
        if ids[rid] > 1:
            reason = "duplicate run_id"
        elif not valid:
            reason = row["outcome"]
        elif row["plan_count"] == 0 or row["engagements"] == 0:
            reason = "INVALID_NO_PLAN_OR_ENGAGEMENT"
        if reason:
            invalid.append({"run_id": rid, "reason": reason})
        else:
            groups[combo(row)].append(row)
    selected = []
    for key, group in sorted(groups.items()):
        row, rule = newest(group, warnings)
        selections.append({"combination": list(key), "rule": rule, "selected_run_id": row["run_id"] if row else None, "candidates": [g["run_id"] for g in group]})
        if row:
            selected.append(row)
    plans = read_csv(folder / "plans.csv", PLAN_COLS)
    events = read_csv(folder / "events.csv", EVENT_COLS)
    for row in plans:
        if row["run_id"] not in ids or row["planner"] not in PLANNERS:
            raise ValueError("plans.csv: 참조 run_id/planner 오류")
        matching = [r for r in runs if r["run_id"] == row["run_id"]]
        if any(r["planner"] != row["planner"] for r in matching):
            raise ValueError("plans.csv: runs.csv와 planner 불일치")
        for key in ("t_rel", "ms", "waypoints", "boxes", "vo_active"):
            row[key] = number(row[key], f"plans/{key}")
        if any(not row[k].is_integer() for k in ("waypoints", "boxes", "vo_active")) or row["vo_active"] not in (0, 1):
            raise ValueError("plans.csv: waypoints/boxes는 정수, vo_active는 0/1 필요")
    for row in events:
        if row["run_id"] not in ids or row["type"] not in EVENT_TYPES:
            raise ValueError("events.csv: run_id/type 오류")
        row["t_rel"] = number(row["t_rel"], "events/t_rel")
    chosen = {row["run_id"]: row for row in selected}
    for row in plans + events:
        if row["run_id"] in chosen and row["t_rel"] > chosen[row["run_id"]]["duration_sec"]:
            raise ValueError("plans/events: duration_sec 이후의 이벤트")
    for row in selected:
        measured = [p for p in plans if p["run_id"] == row["run_id"]]
        if measured and len(measured) != row["plan_count"]:
            raise ValueError(f"{row['run_id']}: plans 행 수와 plan_count 불일치")
    empty = [f"{s}/{p}" for s in SCENARIOS for p in PLANNERS if not any(r["scenario"] == s and r["planner"] == p for r in selected)]
    if empty:
        warnings.append("빈 scenario/planner cell: " + ", ".join(empty))
    return selected, plans, events, invalid, selections, warnings, len(runs)


def percentile(values, q):
    values = sorted(values)
    if not values:
        return None
    index = (len(values) - 1) * q
    lo, hi = math.floor(index), math.ceil(index)
    return values[lo] + (values[hi] - values[lo]) * (index - lo)


def median(values):
    values = [v for v in values if v is not None]
    return stats.median(values) if values else None


def aggregate(rows, plans):
    n = len(rows)
    avoided = sum(r["outcome"] == "AVOIDED" for r in rows)
    times = [p["ms"] for p in plans if p["run_id"] in {r["run_id"] for r in rows}]
    return {"valid_runs": n, "avoided_runs": avoided, "hit_runs": n - avoided, "avoided_rate": avoided / n if n else None,
            "closest_m_median": median([r["closest_m"] for r in rows]), "closest_m_mean": stats.mean(r["closest_m"] for r in rows) if n else None,
            "closest_m_min": min((r["closest_m"] for r in rows), default=None), "plan_count_median": median([r["plan_count"] for r in rows]),
            "plan_ms_median": median(times), "plan_ms_p95": percentile(times, .95),
            "run_plan_ms_median": median([r["plan_ms_median"] for r in rows]), "reaction_sec_median": median([r["reaction_sec"] for r in rows]),
            "avoided_count_median": median([r["avoided_count"] for r in rows]), "engagements_median": median([r["engagements"] for r in rows])}


def summary_for(runs, plans, invalid, raw_count):
    result = aggregate(runs, plans)
    result.update(invalid_runs=len(invalid), raw_runs=raw_count, expected_combinations=48,
                  unselected_runs=raw_count - len(invalid) - len(runs), complete_matrix=len(runs) == 48)
    result["planners"] = {p: aggregate([r for r in runs if r["planner"] == p], plans) for p in PLANNERS}
    result["scenario_planner"] = {s: {p: aggregate([r for r in runs if r["scenario"] == s and r["planner"] == p], plans) for p in PLANNERS} for s in SCENARIOS}
    result["torpedo_planner"] = {t: {p: aggregate([r for r in runs if r["torpedo"] == t and r["planner"] == p], plans) for p in PLANNERS} for t in ("청상어", "백상어", "Mk48")}
    return result


def text(x, y, value, size=18, color="#172b3b", anchor="start"):
    return f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" fill="{color}" text-anchor="{anchor}">{html.escape(str(value))}</text>'


def svg_document(title, content, date, height=530):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="880" height="{height}" viewBox="0 0 880 {height}" font-family="Arial, Noto Sans KR, sans-serif">'
            f'<title>{html.escape(title)}</title><rect width="880" height="{height}" fill="white"/>' + text(28, 36, title, 23) + "".join(content)
            + text(28, height - 32, "Source: MANTA automated experiment logs", 14, "#536574")
            + text(28, height - 12, f"Generated {date}", 14, "#536574") + "</svg>")


def matrix_chart(summary, date):
    items = []
    for pi, p in enumerate(PLANNERS):
        x = 28 + pi * 425
        items.append(text(x, 75, LABEL[p], 22, COLOR[p]))
        for si, s in enumerate(SCENARIOS):
            a = summary["scenario_planner"][s][p]
            n, avoided, hit = a["valid_runs"], a["avoided_runs"], a["hit_runs"]
            color = "#eef1f4" if not n else "#e4f3e9" if avoided > hit else "#fbe6e8" if hit > avoided else "#fff0dd"
            y = 95 + si * 91
            items.append(f'<rect x="{x}" y="{y}" width="399" height="81" rx="6" fill="{color}"/>')
            items.append(text(x + 12, y + 25, LABEL[s], 18))
            verdict = "N/A · n=0" if not n else f'AVOIDED {avoided}/{n} · n={n}' if avoided > hit else f'HIT {hit}/{n} · n={n}' if hit > avoided else f'MIXED A{avoided}/H{hit} · n={n}'
            items.append(text(x + 115, y + 27, verdict, 19))
            items.append(text(x + 115, y + 59, "median closest " + (f"{a['closest_m_median']:.2f} m" if n else "N/A"), 16, "#536574"))
    return svg_document("접근 방향 × 플래너 결과", items, date)


def axis_chart(title, series, date, xlabel, ylabel, threshold=None, line=False, raw_series=None, bands=None):
    points = [tuple(point[:2]) for _, data in series + (raw_series or []) for point in data]
    if not points:
        return None
    xmin, xmax = min(x for x, _ in points), max(x for x, _ in points)
    ymin, ymax = min(y for _, y in points), max(y for _, y in points)
    if threshold is not None:
        ymin, ymax = min(ymin, threshold), max(ymax, threshold)
    dx, dy = max(xmax - xmin, .5), max(ymax - ymin, .5)
    xmin, xmax, ymin, ymax = xmin - .08 * dx, xmax + .08 * dx, ymin - .08 * dy, ymax + .12 * dy
    xy = lambda x, y: (100 + (x - xmin) / (xmax - xmin) * 710, 407 - (y - ymin) / (ymax - ymin) * 285)
    items = [text(28, 93, ylabel, 18)]
    for i in range(5):
        y = ymin + (ymax - ymin) * i / 4
        _, sy = xy(xmin, y)
        items += [f'<path d="M100 {sy:.2f}H810" stroke="#e1e7ed"/>', text(89, sy + 6, f"{y:.2f}", 15, anchor="end")]
        x = xmin + (xmax - xmin) * i / 4
        sx, _ = xy(x, ymin)
        items.append(text(sx, 432, f"{x:.2f}", 15, anchor="middle"))
    if threshold is not None:
        _, sy = xy(xmin, threshold)
        items += [f'<path d="M100 {sy:.2f}H810" stroke="#a73140" stroke-dasharray="6 5"/>', text(808, sy - 7, "HIT radius 1.0 m", 16, "#a73140", "end")]
    for p, data in (bands or []):
        upper = [xy(x, hi) for x, lo, hi in data]
        lower = [xy(x, lo) for x, lo, hi in reversed(data)]
        if len(data) >= 2:
            polygon = " ".join(f"{x:.2f},{y:.2f}" for x, y in upper + lower)
            items.append(f'<polygon points="{polygon}" fill="{COLOR[p]}" fill-opacity=".12"/>')
    for p, data in series:
        coords = [xy(*point[:2]) for point in data]
        if line:
            items.append('<polyline points="' + " ".join(f"{x:.2f},{y:.2f}" for x, y in coords) + f'" fill="none" stroke="{COLOR[p]}" stroke-width="3"/>')
        for point, (x, y) in zip(data, coords):
            scenario = point[2] if len(point) > 2 else "front"
            common = f'fill="{COLOR[p]}" fill-opacity=".75"'
            if scenario == "rear":
                items.append(f'<rect x="{x-5:.2f}" y="{y-5:.2f}" width="10" height="10" {common}/>')
            elif scenario in {"side", "diag"}:
                vertices = [(x, y-7), (x+7, y), (x, y+7), (x-7, y)] if scenario == "side" else [(x,y-7),(x+7,y+6),(x-7,y+6)]
                items.append('<polygon points="' + ' '.join(f'{a:.2f},{b:.2f}' for a,b in vertices) + f'" {common}/>')
            else:
                items.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" {common}/>')
    for p, data in (raw_series or []):
        for point in data:
            x, y = xy(*point[:2])
            items.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="none" stroke="{COLOR[p]}" stroke-opacity=".6"/>')
    if any(len(point) > 2 for _, data in series for point in data):
        items.append(text(105, 114, "○ front   □ rear   ◇ side   △ diag", 15))
    for i, p in enumerate(PLANNERS):
        items.append(text(580 + i * 100, 76, LABEL[p], 18, COLOR[p]))
    items.append(text(450, 463, xlabel, 18, anchor="middle"))
    return svg_document(title, items, date)


def speed_ratios(runs, folder, warnings):
    metadata = []
    for name in ("scale_info.txt", "params.txt"):
        raw = (folder / name).read_text(encoding="utf-8-sig").strip()
        try:
            data = json.loads(raw) if raw.startswith("{") else dict(re.findall(r"^\s*([\w.]+)\s*=\s*([0-9.]+)\s*$", raw, re.M))
            if isinstance(data, dict):
                metadata.append(data)
        except ValueError:
            warnings.append(f"{name}: 속도 매핑 해석 불가, 임의 추정하지 않음")
    ratios = {}
    for r in runs:
        candidates = []
        if r.get("speed_ratio"):
            candidates.append(number(r["speed_ratio"], "speed_ratio"))
        if r.get("torpedo_speed_mps") and r.get("rov_speed_mps"):
            denominator = number(r["rov_speed_mps"], "rov_speed_mps")
            if denominator > 0:
                candidates.append(number(r["torpedo_speed_mps"], "torpedo_speed_mps") / denominator)
        for meta in metadata:
            denominator = meta.get("rov_speed_mps")
            mapping = meta.get("torpedo_speed_mps", {})
            numerator = mapping.get(r["torpedo"]) if isinstance(mapping, dict) else None
            numerator = meta.get(f"torpedo_speed_mps.{r['torpedo']}", numerator)
            if denominator is not None and numerator is not None:
                den = number(denominator, "metadata/rov_speed_mps")
                if den > 0:
                    candidates.append(number(numerator, "metadata/torpedo_speed_mps") / den)
        if candidates and min(candidates) > 0 and max(candidates) - min(candidates) <= 1e-6:
            ratios[r["run_id"]] = candidates[0]
    if len(ratios) != len(runs):
        warnings.append("속도 매핑이 모든 유효 실행에서 명확하지 않아 속도비 차트 생략")
        return {}
    return ratios


def distribution_chart(title, groups, date, unit):
    items = [text(28, 83, unit)]
    maximum = max((v for data in groups.values() for v in data), default=0) or 1
    for pi, p in enumerate(PLANNERS):
        data = groups.get(p, [])
        x = 190 + pi * 425
        items += [text(x, 448, f"{LABEL[p]} · n={len(data)}", 19, COLOR[p], "middle")]
        if not data:
            items.append(text(x, 230, "N/A", 20, anchor="middle"))
            continue
        sy = lambda v: 403 - v / maximum * 290
        lo, mid, hi = percentile(data, .25), median(data), percentile(data, .75)
        items += [f'<path d="M{x} {sy(min(data))}V{sy(max(data))}" stroke="{COLOR[p]}" stroke-width="2"/>',
                  f'<rect x="{x-60}" y="{sy(hi)}" width="120" height="{max(1,sy(lo)-sy(hi))}" fill="{COLOR[p]}" fill-opacity=".18" stroke="{COLOR[p]}"/>',
                  f'<path d="M{x-60} {sy(mid)}H{x+60}" stroke="{COLOR[p]}" stroke-width="3"/>', text(x+75, sy(mid)+6, f"median {mid:.2f}", 17)]
    return svg_document(title, items, date)


def paired_rear(runs):
    grouped = defaultdict(dict)
    for r in runs:
        if r["scenario"] == "rear":
            grouped[(r["mode"], r["torpedo"])][r["planner"]] = r
    return [(key, value) for key, value in sorted(grouped.items()) if len(value) == 2]


def generate_figures(runs, plans, events, summary, folder, date, warnings):
    figures = {"scenario-matrix.svg": (matrix_chart(summary, date), ["scenario", "planner", "outcome", "closest_m"])}
    ratios = speed_ratios(runs, folder, warnings)
    if ratios:
        series = [(p, [(ratios[r["run_id"]], r["closest_m"], r["scenario"]) for r in runs if r["planner"] == p]) for p in PLANNERS]
        figures["closest-vs-speed-ratio.svg"] = (axis_chart("최근접 거리와 상대 속도비", series, date, "Torpedo / ROV speed ratio", "closest (m)", 1), ["scenario", "closest_m", "speed_ratio", "torpedo_speed_mps", "rov_speed_mps"])
    margins = defaultdict(lambda: defaultdict(list))
    for r in runs:
        for i, value in enumerate(r["avoided_margins"], 1):
            margins[r["planner"]][i].append(value)
    if any(len(data) >= 2 for data in margins.values()):
        series = [(p, [(i, median(v)) for i, v in sorted(margins[p].items())]) for p in PLANNERS]
        raw = [(p, [(i, value) for i, values in sorted(margins[p].items()) for value in values]) for p in PLANNERS]
        bands = [(p, [(i, percentile(v,.25), percentile(v,.75)) for i,v in sorted(margins[p].items()) if len(v) >= 4]) for p in PLANNERS]
        chart = axis_chart("재공격 이격거리 · 중앙값, 원자료 / n≥4 IQR", series, date, "Engagement number", "separation (m)", line=True, raw_series=raw, bands=bands)
        figures["reattack-margins.svg"] = (chart, ["avoided_margins", "planner"])
    times = {p: [v["ms"] for v in plans if v["planner"] == p and v["run_id"] in {r["run_id"] for r in runs}] for p in PLANNERS}
    if any(times.values()):
        figures["plan-time.svg"] = (distribution_chart("계획 시간 분포 · 개별 계획 기준", times, date, "ms"), ["plans.run_id", "plans.planner", "plans.ms"])
    if any(r["reaction_sec"] is not None for r in runs):
        data = [(p, [(i+1, summary["scenario_planner"][s][p]["reaction_sec_median"]) for i, s in enumerate(SCENARIOS) if summary["scenario_planner"][s][p]["reaction_sec_median"] is not None]) for p in PLANNERS]
        figures["reaction-time.svg"] = (axis_chart("접근 방향별 반응시간 중앙값", data, date, "1 front / 2 rear / 3 side / 4 diag", "reaction (s)"), ["scenario", "planner", "reaction_sec"])
    for (mode, torpedo), pair in paired_rear(runs):
        lines = []
        complete = True
        for pi, p in enumerate(PLANNERS):
            r = pair[p]
            ev = [e for e in events if e["run_id"] == r["run_id"]]
            pp = [v for v in plans if v["run_id"] == r["run_id"]]
            engage = [e for e in ev if e["type"] == "ENGAGE"]
            end = [e for e in ev if e["type"] == r["outcome"]]
            if not engage or not end or not pp:
                complete = False
                break
            chosen = [("ENGAGE", min(e["t_rel"] for e in engage)), ("first PLAN", min(v["t_rel"] for v in pp)), (r["outcome"], max(e["t_rel"] for e in end))]
            lines.append(text(28, 110+pi*150, f"{LABEL[p]} · closest {r['closest_m']:.2f} m", 20, COLOR[p]))
            for j, (name, t) in enumerate(chosen):
                lines.append(text(50+j*270, 165+pi*150, f"{name}: {t:.2f} s", 18))
        if complete:
            figures["rear-timeline.svg"] = (svg_document(f"후방 동일 조건 · {torpedo} / {mode}", lines, date), ["events.run_id", "events.t_rel", "events.type", "plans.t_rel", "closest_m"])
            break
    # Trajectory inputs are optional and must use the documented coordinate columns.
    for _, pair in paired_rear(runs):
        tracks = []
        try:
            for p in PLANNERS:
                rid = pair[p]["run_id"]
                if not re.fullmatch(r"[A-Za-z0-9_-]+", rid):
                    raise ValueError("trajectory filename에 안전한 run_id 필요")
                path = folder / "traj" / f"{rid}.csv"
                if not path.is_file():
                    raise ValueError("동일 조건 trajectory 쌍 없음")
                rows = read_csv(path, ["t_rel", "uuv_x", "uuv_y"])
                if len(rows) < 2:
                    raise ValueError("trajectory 측정점 부족")
                data = []
                previous = -1
                for row in rows:
                    t = number(row["t_rel"], "traj/t_rel")
                    if t <= previous or t > pair[p]["duration_sec"]:
                        raise ValueError("trajectory 시간 순서/범위 오류")
                    previous = t
                    x, y = float(row["uuv_x"]), float(row["uuv_y"])
                    if not math.isfinite(x) or not math.isfinite(y):
                        raise ValueError("trajectory 유한 좌표 필요")
                    data.append((x, y))
                tracks.append((p, data))
            figures["trajectory-compare.svg"] = (axis_chart("동일 후방 조건 ROV 궤적 · XY 평면", tracks, date, "map x (m)", "map y (m)", line=True), ["traj.t_rel", "traj.uuv_x", "traj.uuv_y"])
            break
        except (ValueError, OSError) as exc:
            warnings.append(f"trajectory 생략: {exc}")
    return figures, ratios


def fmt(value, digits=2):
    return "N/A" if value is None else f"{value:.{digits}f}"


def results_html(summary, selected, figures, asset_path, date):
    a, d = summary["planners"]["astar"], summary["planners"]["dvo"]
    card = lambda label, value, cls="": f'<article class="{cls}"><span>{html.escape(label)}</span><strong>{html.escape(value)}</strong></article>'
    block = ['<!-- Full-batch MANTA results are regenerated by scripts/build_manta_results.py -->',
             f'<p class="method-note">CSV에서 검증된 유효 조합 {summary["valid_runs"]}개를 집계했습니다. 무효 실행 {summary["invalid_runs"]}개와 미선택 실행 {summary["unselected_runs"]}개는 성능 통계에서 분리했습니다.</p>',
             '<div class="manta-metrics">', card("유효 실험 조합", f'{summary["valid_runs"]} / 48'),
             card("A*", f'AVOIDED {a["avoided_runs"]} / {a["valid_runs"]}', "astar"), card("Dynamic VO", f'AVOIDED {d["avoided_runs"]} / {d["valid_runs"]}', "dvo"),
             card("최근접 거리 중앙값", fmt(summary["closest_m_median"]) + " m"), '</div>']
    for name in selected:
        source = html.escape(asset_path + "/" + name)
        block.append(f'<figure class="research-figure manta-generated-figure"><img loading="lazy" decoding="async" width="880" height="530" src="{source}" alt="{html.escape(name.replace(".svg", ""))}"><figcaption>Source: MANTA automated experiment logs · Generated {date}</figcaption><a class="back-link" href="{source}" target="_blank" rel="noopener">차트 확대 ↗</a></figure>')
    block.append('<table class="metric-table manta-result-table"><caption>접근 방향별 유효 실행 결과 · 중앙값 기준</caption><thead><tr><th>접근 방향</th><th>A*</th><th>Dynamic VO</th><th>관측</th></tr></thead><tbody>')
    for s in SCENARIOS:
        cells = summary["scenario_planner"][s]
        block.append('<tr><td data-label="접근 방향">' + LABEL[s] + '</td>')
        for p in PLANNERS:
            v = cells[p]
            value = f'{v["avoided_runs"]}/{v["valid_runs"]} AVOIDED<br>median {fmt(v["closest_m_median"])} m' if v["valid_runs"] else "N/A · n=0"
            block.append(f'<td data-label="{LABEL[p]}">{value}</td>')
        observation = "두 플래너의 유효 실행을 함께 확인했습니다." if all(cells[p]["valid_runs"] for p in PLANNERS) else "비교할 유효 표본이 부족합니다."
        block.append('<td data-label="관측">' + observation + '</td></tr>')
    block.append('</tbody></table>')
    # Only describe computations directly supported by the selected measured runs.
    rates = [(s, summary["scenario_planner"][s]) for s in SCENARIOS if all(summary["scenario_planner"][s][p]["valid_runs"] >= 3 for p in PLANNERS)]
    signs = [cells["astar"]["avoided_rate"] - cells["dvo"]["avoided_rate"] for _, cells in rates]
    if signs and min(signs) < 0 < max(signs):
        block.append('<p class="method-note">접근 방향에 따라 회피 비율의 순서가 달랐습니다. 전체 평균만으로 한 플래너의 일관된 우위를 판단하지 않았습니다.</p>')
    if a["valid_runs"] and d["valid_runs"] and a["plan_count_median"] < d["plan_count_median"]:
        block.append(f'<p class="method-note">재계획 횟수 중앙값은 A* {fmt(a["plan_count_median"], 1)}회, Dynamic VO {fmt(d["plan_count_median"], 1)}회였습니다. 적은 재계획 횟수만으로 회피 안전성을 판단하지 않습니다.</p>')
    return "\n".join(block)


def build(input_path, output_path, page):
    if (input_path / "runs.csv").exists():
        with (input_path / "runs.csv").open(encoding="utf-8-sig", newline="") as stream:
            planners = {row.get("planner", "").strip().lower() for row in csv.DictReader(stream)}
        if "hybrid" in planners or (input_path / "final_integrity.json").exists():
            from build_manta_dvo import build_dvo
            return build_dvo(input_path, output_path, page)
    if not (input_path / "runs.csv").exists():
        if any((input_path / name).exists() for name in ("plans.csv", "events.csv", "collect_log.txt", "scale_info.txt", "params.txt")):
            raise ValueError("일부 입력만 존재하고 runs.csv가 없습니다")
        print("MANTA CSV 없음: 대표 결과와 페이지를 변경하지 않았습니다.")
        return None
    # Preserve outside-block bytes, including CRLF and an optional UTF-8 BOM.
    original = page.read_bytes().decode("utf-8")
    if original.count(START) != 1 or original.count(END) != 1 or original.index(START) >= original.index(END):
        raise ValueError("RESULTS marker가 없거나 중복/순서 오류")
    runs, plans, events, invalid, selections, warnings, raw_count = load_inputs(input_path)
    summary = summary_for(runs, plans, invalid, raw_count)
    generated = datetime.now(timezone.utc)
    date = generated.date().isoformat()
    manifest = {"generated_at": generated.isoformat(), "inputs": {}, "valid_runs": len(runs), "invalid_runs": len(invalid),
                "invalid_details": invalid, "selection_rules": selections, "warnings": warnings, "figures": {}, "selected_figures": [],
                "expected_combinations": 48, "selected_run_ids": [r["run_id"] for r in runs]}
    for path in sorted(input_path.rglob("*")):
        if path.is_file() and path.suffix in {".csv", ".txt"}:
            manifest["inputs"][path.relative_to(input_path).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    if runs:
        figures, ratios = generate_figures(runs, plans, events, summary, input_path, date, warnings)
        priority = ["scenario-matrix.svg", "closest-vs-speed-ratio.svg", "reattack-margins.svg", "reaction-time.svg", "trajectory-compare.svg", "plan-time.svg", "rear-timeline.svg"]
        rear = summary["scenario_planner"]["rear"]
        ar, dr = rear["astar"], rear["dvo"]
        if all(v["valid_runs"] >= 3 and v["reaction_sec_median"] is not None for v in (ar, dr)) and abs(ar["reaction_sec_median"] - dr["reaction_sec_median"]) >= .2:
            priority.remove("reaction-time.svg")
            priority.insert(1, "reaction-time.svg")
        selected = [name for name in priority if name in figures][:3]
        # Content-hash query prevents cached SVGs after CSV-only updates.
        asset_path = Path(__import__('os').path.relpath(output_path, page.parent)).as_posix()
        block = results_html(summary, selected, figures, asset_path, date)
        for name in selected:
            digest = hashlib.sha256(figures[name][0].encode()).hexdigest()[:12]
            block = block.replace(f'{asset_path}/{name}"', f'{asset_path}/{name}?v={digest}"')
        replaced = original[:original.index(START)+len(START)] + "\n" + block + "\n" + original[original.index(END):]
    else:
        figures, selected, replaced = {}, [], original
        warnings.append("유효 실행 없음: 기존 대표 결과 유지")
    output_path.mkdir(parents=True, exist_ok=True)
    for name, (content, columns) in figures.items():
        (output_path / name).write_text(content, encoding="utf-8")
        manifest["figures"][name] = {"source_columns": columns, "sha256": hashlib.sha256(content.encode()).hexdigest()}
    manifest["selected_figures"] = selected
    (output_path / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_path / "generated-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if replaced != original:
        page.write_bytes(replaced.encode("utf-8"))
    print(f"MANTA 유효 조합 {len(runs)}/48, 무효 {len(invalid)}, 본문 차트 {len(selected)}개")
    for warning in warnings:
        print("주의: " + warning)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "portfolio_data/manta/latest")
    parser.add_argument("--output", type=Path, default=ROOT / "dist/assets/generated/manta")
    parser.add_argument("--html", type=Path, default=ROOT / "dist/projects/manta.html")
    args = parser.parse_args()
    try:
        build(args.input.resolve(), args.output.resolve(), args.html.resolve())
    except (ValueError, OSError, csv.Error) as exc:
        print(f"MANTA 생성 중단: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
