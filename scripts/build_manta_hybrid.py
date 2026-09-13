"""Auditable DVO/Hybrid paired results. Standard-library only; no invented samples.

Only six root CSVs are read. Baselines, pilots and by_planner copies are never
merged. Validate all inputs before writing assets or the marked HTML block.
"""
import csv
import hashlib
import html
import json
import math
import os
import statistics as stats
from collections import Counter, defaultdict
from pathlib import Path

START = "<!-- MANTA_RESULTS_AUTO_START -->"
END = "<!-- MANTA_RESULTS_AUTO_END -->"
SCENARIOS = ("front", "rear", "side", "diag")
PLANNERS = ("dvo", "hybrid")
MODES = ("2", "3")
TORPEDOES = ("baeksangeo", "cheongsangeo", "mk48")
LABEL = {"dvo": "DVO", "hybrid": "Hybrid", "front": "정면", "rear": "후방", "side": "측면", "diag": "대각", "2": "SimpleTracking", "3": "PNG", "baeksangeo": "백상어", "cheongsangeo": "청상어", "mk48": "Mk48"}
COLOR = {"dvo": "#23774a", "hybrid": "#2b73b8"}
COLUMNS = {
    "runs.csv": "run_id scenario planner mode torpedo outcome closest_m engagements plan_count plan_ms_mean plan_ms_median duration_sec".split(),
    "plans.csv": "run_id t_rel planner ms waypoints boxes vo_active".split(),
    "events.csv": "run_id t_rel type value".split(),
    "kinematics.csv": "run_id t_rel sim_time_sec rov_x rov_y rov_z torpedo_x torpedo_y torpedo_z distance_m".split(),
    "controls.csv": ["run_id", "t_rel"] + [f"thruster_{i}" for i in range(1, 7)],
    "run_metrics_extended.csv": "run_id scenario planner mode torpedo outcome min_distance_m HIT_or_AVOIDED".split(),
}


def read_table(path, required):
    if not path.exists():
        raise ValueError(f"missing required CSV: {path.name}")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError(f"{path.name}: missing or duplicate headers")
        if set(required) - set(reader.fieldnames):
            raise ValueError(f"{path.name}: missing columns {sorted(set(required)-set(reader.fieldnames))}")
        rows = []
        for row in reader:
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"{path.name}: inconsistent column count")
            rows.append({k: v.strip() for k, v in row.items()})
        return rows


def finite(value, signed=False):
    try:
        result = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"invalid measured number: {value!r}") from exc
    if not math.isfinite(result) or (not signed and result < 0):
        raise ValueError(f"invalid measured number: {value!r}")
    return result


def key(row):
    return tuple(row[k] for k in ("scenario", "mode", "torpedo"))


def percentile(values, fraction):
    values = sorted(values)
    if not values:
        return None
    index = (len(values) - 1) * fraction
    lo, hi = math.floor(index), math.ceil(index)
    return values[lo] + (values[hi] - values[lo]) * (index - lo)


def distribution(values):
    return {"median": percentile(values, .5), "q1": percentile(values, .25), "q3": percentile(values, .75), "p95": percentile(values, .95), "n": len(values)}


def load_verified(source):
    for name in ("provenance.json", "final_integrity.json", "pipeline_audit.json", "rosbag_integrity.json"):
        if not (source / name).exists():
            raise ValueError(f"missing final-batch metadata: {name}; do not reuse a previous batch's audit")
    tables = {name: read_table(source / name, columns) for name, columns in COLUMNS.items()}
    raw = tables["runs.csv"]
    if not raw:
        raise ValueError("no final DVO/Hybrid runs")
    ids, combos, invalid = set(), set(), []
    for r in raw:
        if not r["run_id"] or r["run_id"] in ids:
            raise ValueError("duplicate/missing run_id")
        ids.add(r["run_id"])
        if r["planner"] not in PLANNERS or r["scenario"] not in SCENARIOS or r["mode"] not in MODES or r["torpedo"] not in TORPEDOES:
            raise ValueError("latest data must use DVO/Hybrid, four directions, modes 2/3 and the three configured torpedoes")
        combo = (*key(r), r["planner"])
        if combo in combos:
            raise ValueError("duplicate final condition: do not merge pilots or repeated ZIP copies")
        combos.add(combo)
        for field in ("closest_m", "engagements", "plan_count", "plan_ms_mean", "plan_ms_median", "duration_sec"):
            r[field] = finite(r[field])
        if not r["plan_count"].is_integer() or not r["engagements"].is_integer():
            raise ValueError("plan_count and engagements must be integers")
        if r["outcome"] not in ("HIT", "AVOIDED") or r["plan_count"] == 0 or r["engagements"] == 0:
            invalid.append(r["run_id"])
    if invalid:
        raise ValueError(f"final batch has invalid runs; page left untouched: {invalid}")
    grouped = {}
    for name, rows in tables.items():
        groups = defaultdict(list)
        for row in rows:
            if row["run_id"] not in ids:
                raise ValueError(f"{name}: unknown run_id")
            groups[row["run_id"]].append(row)
        if set(groups) != ids:
            raise ValueError(f"{name}: missing per-run evidence")
        grouped[name] = groups
    for run in raw:
        plans = grouped["plans.csv"][run["run_id"]]
        if len(plans) != run["plan_count"]:
            raise ValueError("plans.csv row count differs from run plan_count")
        for row in plans:
            if row["planner"] != run["planner"]:
                raise ValueError("plan planner differs from run planner")
            row["ms"] = finite(row["ms"])
            finite(row["t_rel"])
            finite(row["waypoints"])
        metric = grouped["run_metrics_extended.csv"][run["run_id"]]
        if len(metric) != 1 or any(metric[0][f] != run[f] for f in ("scenario", "planner", "mode", "torpedo", "outcome")) or metric[0]["HIT_or_AVOIDED"] != run["outcome"]:
            raise ValueError("extended metrics verdict or condition differs from runs.csv")
        # Minimum sample distance and interpolated HIT distance need not be identical.
        finite(metric[0]["min_distance_m"])
        for name in ("kinematics.csv", "controls.csv", "events.csv"):
            previous = -1.0
            for row in grouped[name][run["run_id"]]:
                t = finite(row["t_rel"])
                if t < previous:
                    raise ValueError(f"{name}: nonmonotonic run time")
                previous = t
                if name == "kinematics.csv":
                    for f in COLUMNS[name][2:]:
                        finite(row[f], signed=f != "distance_m")
                elif name == "controls.csv":
                    for i in range(1, 7):
                        finite(row[f"thruster_{i}"], signed=True)
    provenance = json.loads((source / "provenance.json").read_text(encoding="utf-8")) if (source / "provenance.json").exists() else {}
    hashes = {n: hashlib.sha256((source / n).read_bytes()).hexdigest() for n in COLUMNS}
    if provenance.get("input_sha256") != hashes:
        raise ValueError("CSV hashes differ from supplied provenance; import the complete new batch with refreshed metadata")
    integrity = json.loads((source / "final_integrity.json").read_text(encoding="utf-8")) if (source / "final_integrity.json").exists() else {}
    if integrity:
        expected_rows = {n.removesuffix(".csv"): len(rows) for n, rows in tables.items()}
        counts = {p: dict(Counter(r["outcome"] for r in raw if r["planner"] == p)) for p in PLANNERS}
        if integrity.get("rows") != expected_rows or integrity.get("outcomes_by_planner") != counts or integrity.get("valid") != len(raw) or integrity.get("invalid") != 0 or integrity.get("overall") != "SUCCESS" or integrity.get("problems") or integrity.get("zero_plan_run_ids"):
            raise ValueError("final integrity report does not match measured CSVs")
    else:
        raise ValueError("empty final integrity report")
    validation = {"origin": "supplied experiment audit reports", "pipeline_verified": False, "native_bags_verified": False, "regression_cases": len(provenance.get("regression_cases", []))}
    if (source / "pipeline_audit.json").exists():
        report = json.loads((source / "pipeline_audit.json").read_text())
        records = report["runs"]
        validation["pipeline_verified"] = len(records) == len(ids) and {r["run_id"] for r in records} == ids and all(r["pipeline_verified"] and r["nonzero_thrusters"] for r in records) and report["all_pipelines_verified"]
        if not validation["pipeline_verified"]:
            raise ValueError("pipeline audit failed")
    if (source / "rosbag_integrity.json").exists():
        records = json.loads((source / "rosbag_integrity.json").read_text())
        validation["native_bags_verified"] = len(records) == len(ids) and {r["run_id"] for r in records} == ids and all(r["verified"] for r in records)
        if not validation["native_bags_verified"]:
            raise ValueError("native bag audit report failed")
    if integrity.get("pipeline_verified") is not True or integrity.get("native_bags_verified") is not True or len(provenance.get("regression_cases", [])) != 14:
        raise ValueError("final validation report/regression provenance is incomplete")
    return tables, grouped, provenance, hashes, validation


def svg_start(title, desc, width=880, height=440):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc"><title id="title">{html.escape(title)}</title><desc id="desc">{html.escape(desc)}</desc><rect width="100%" height="100%" fill="#fff"/><g font-family="Arial, Noto Sans KR, sans-serif" fill="#193044">', f'<text x="30" y="38" font-size="23" font-weight="700">{html.escape(title)}</text>']


def text(x, y, value, size=17, color="#193044", anchor="start"):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}">{html.escape(str(value))}</text>'


def finish(parts):
    return "\n".join(parts + ["</g></svg>"])


def paired_chart(counts, n):
    categories = [("both_avoided", "둘 다 AVOIDED", "#376d67"), ("dvo_only", "DVO만 AVOIDED", COLOR["dvo"]), ("hybrid_only", "Hybrid만 AVOIDED", COLOR["hybrid"]), ("both_hit", "둘 다 HIT", "#a83b38")]
    parts = svg_start("같은 위협 조건에서 결과가 갈린 경우", f"{n}개 paired 조건. " + ", ".join(f"{label} {counts[k]}" for k, label, _ in categories))
    parts.append(text(30, 69, f"동일 조건 {n}쌍 · 방향 × 유도 방식 × 어뢰 유형", 16))
    scale = 540 / max(n, 1)
    for i, (k, label, color) in enumerate(categories):
        y = 106 + i * 65
        parts += [text(30, y + 25, label), f'<rect x="230" y="{y}" width="{counts[k]*scale:.2f}" height="36" fill="{color}"/>', text(245 + counts[k]*scale, y + 25, f"{counts[k]}쌍", 19)]
    for tick in range(0, n + 1, 6):
        x = 230 + tick * scale
        parts += [f'<path d="M{x} 360v6" stroke="#85929d"/>', text(x, 391, tick, 15, anchor="middle")]
    parts += [f'<path d="M230 360H770" stroke="#85929d"/>', text(30, 421, "AVOIDED는 연료 소진까지 생존한 최종 판정이며 단일 스쳐 지나감 횟수가 아닙니다.", 15)]
    return finish(parts)


def matrix_chart(cells):
    parts = svg_start("접근 방향과 유도 방식별 결과", "각 칸은 3종 어뢰 중 AVOIDED 횟수와 최근접 거리 중앙값입니다.", height=700)
    parts.append(text(30, 70, "각 칸: AVOIDED / 3 · closest_m 중앙값 (m)", 16))
    for m, mode in enumerate(MODES):
        top = 105 + m * 285
        parts += [text(30, top, LABEL[mode], 21), text(380, top, "DVO", 19, COLOR["dvo"]), text(635, top, "Hybrid", 19, COLOR["hybrid"])]
        for i, scenario in enumerate(SCENARIOS):
            y = top + 20 + 55 * i
            parts.append(text(30, y + 34, LABEL[scenario], 18))
            for p, planner in enumerate(PLANNERS):
                v = cells[f"{scenario}|{mode}|{planner}"]
                x = 260 + p * 255
                fill = "#edf5ef" if v["avoided"] >= 2 else "#f8eeee"
                parts += [f'<rect x="{x}" y="{y}" width="235" height="49" rx="3" fill="{fill}"/>', text(x + 18, y + 32, f'{v["avoided"]}/{v["n"]} · {v["closest_m_median"]:.2f} m', 20)]
    parts.append(text(30, 679, "각 조건당 최종 실험 1회 · 반복 실험의 통계적 유의성이나 신뢰구간을 의미하지 않습니다.", 15))
    return finish(parts)


def tradeoff_chart(planners):
    parts = svg_start("계획 호출 수와 호출당 계산 시간", "조건별 호출 수 분포 및 실제 plans.csv 계산 시간 분포. IQR은 조건/호출 간 분산이며 신뢰구간이 아닙니다.", height=410)
    for i, (field, title, unit) in enumerate((("plan_count", "run당 계획 호출 수", "회"), ("plan_ms", "호출당 계산 시간", "ms"))):
        y = 102 + 132 * i
        parts.append(text(30, y, title, 20))
        max_v = max(planners[p][field]["p95"] for p in PLANNERS) * 1.12
        for j, p in enumerate(PLANNERS):
            d = planners[p][field]
            row_y = y + 30 + j * 36
            transform = lambda value: 220 + value / max_v * 430
            parts += [text(30, row_y + 5, LABEL[p], 17, COLOR[p]), f'<path d="M220 {row_y}H650" stroke="#e1e7eb"/>', f'<path d="M{transform(d["q1"])} {row_y}H{transform(d["q3"])}" stroke="{COLOR[p]}" stroke-width="14"/>', f'<circle cx="{transform(d["median"])}" cy="{row_y}" r="5" fill="#fff" stroke="{COLOR[p]}" stroke-width="3"/>', text(674, row_y + 5, f'{d["median"]:.2f} {unit}', 17)]
    parts.append(text(30, 384, "중앙값 + IQR · 내부 A*/DVO 분기 호출 수는 로그에 없어 별도로 추정하지 않았습니다.", 15))
    return finish(parts)


def trajectory_chart(pairs, grouped):
    # Deterministic priority: DVO survived / Hybrid HIT, then the reverse.
    chosen = next((p for p in pairs if p["dvo"]["outcome"] == "AVOIDED" and p["hybrid"]["outcome"] == "HIT"), None)
    if chosen is None:
        chosen = next((p for p in pairs if p["dvo"]["outcome"] != p["hybrid"]["outcome"]), None)
    if chosen is None:
        candidates = [p for p in pairs if all(p[n]["outcome"] == "AVOIDED" for n in PLANNERS)]
        chosen = max(candidates, key=lambda p: abs(p["dvo"]["closest_m"] - p["hybrid"]["closest_m"]), default=None)
    if chosen is None:
        return None, None
    full = {p: grouped["kinematics.csv"][chosen[p]["run_id"]] for p in PLANNERS}
    anchor = "hybrid" if chosen["hybrid"]["outcome"] == "HIT" else "dvo"
    center = float(min(full[anchor], key=lambda r: float(r["distance_m"]))["t_rel"])
    lo, hi = max(0, center - 6), center + 4
    rows = {p: [r for r in full[p] if lo <= float(r["t_rel"]) <= hi] for p in PLANNERS}
    if any(len(v) < 2 for v in rows.values()):
        return None, None
    xs = [float(r[f"{vehicle}_x"]) for values in rows.values() for r in values for vehicle in ("rov", "torpedo")]
    ys = [float(r[f"{vehicle}_y"]) for values in rows.values() for r in values for vehicle in ("rov", "torpedo")]
    midx, midy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    span = max(max(xs) - min(xs), max(ys) - min(ys), 1) * 1.15
    xmin, ymin = midx - span/2, midy - span/2
    parts = svg_start("결과가 갈린 동일 조건의 실제 궤적", "kinematics.csv 실측 XY 투영. 두 패널 축 범위와 축척 동일. 최근접 표본 부근의 동일 경과시간 구간만 표시.", height=560)
    scenario, mode, torpedo = key(chosen["dvo"])
    parts.append(text(30, 72, f"{LABEL[scenario]} · {LABEL[mode]} · {LABEL[torpedo]} · run 경과 {lo:.1f}–{hi:.1f} s", 17))
    for i, p in enumerate(PLANNERS):
        left, top, size = 72 + i * 425, 155, 310
        project = lambda x,y: (left + (x-xmin)/span*size, top+size-(y-ymin)/span*size)
        parts.append(text(left, 111, f'{LABEL[p]} · {chosen[p]["outcome"]}', 21, COLOR[p]))
        parts.append(text(left, 137, f'전체 run closest_m {chosen[p]["closest_m"]:.2f} m', 16))
        for tick in range(5):
            v = tick / 4
            x, y = left + size*v, top + size*(1-v)
            parts += [f'<path d="M{x} {top}V{top+size}M{left} {y}H{left+size}" stroke="#e1e7eb"/>', text(x, top+size+24, f"{xmin+span*v:.0f}", 13, anchor="middle"), text(left-9, y+5, f"{ymin+span*v:.0f}", 13, anchor="end")]
        for vehicle, color, dashed in (("rov", COLOR[p], False), ("torpedo", "#a83b38", True)):
            points = [project(float(r[f"{vehicle}_x"]), float(r[f"{vehicle}_y"])) for r in rows[p]]
            line = " ".join(f"{x:.2f},{y:.2f}" for x,y in points)
            parts.append(f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="3"' + (' stroke-dasharray="7 4"' if dashed else '') + '/>')
            sample = min(rows[p], key=lambda r: float(r["distance_m"]))
            x,y = project(float(sample[f"{vehicle}_x"]), float(sample[f"{vehicle}_y"]))
            parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="{color}" stroke="#fff" stroke-width="2"/>')
        parts += [text(left+size/2, 515, "X (m)", 16, anchor="middle"), text(left-42, top+size/2, "Y (m)", 15)]
    parts.append(text(30, 547, "실선 ROV / 점선 어뢰 / 점 최근접 표본 · XY 투영으로 3D 피격 여부를 판정하지 않습니다.", 15))
    info = {"condition": {"scenario": scenario, "mode": mode, "torpedo": torpedo}, "run_ids": {p: chosen[p]["run_id"] for p in PLANNERS}, "window_t_rel_sec": [lo,hi], "projection": "XY, equal axes/aspect; measured samples only", "selection_rule": "DVO-only avoided first, reverse second, largest difference among both-avoided third"}
    return finish(parts), info


def build_hybrid(source, output, page):
    original = page.read_bytes().decode("utf-8")
    if original.count(START) != 1 or original.count(END) != 1 or original.index(START) >= original.index(END):
        raise ValueError("RESULTS markers missing, duplicate or reversed")
    tables, grouped, provenance, hashes, validation = load_verified(source)
    runs = tables["runs.csv"]
    conditions = defaultdict(dict)
    for run in runs:
        conditions[key(run)][run["planner"]] = run
    pairs = [conditions[k] for k in sorted(conditions, key=lambda k: (SCENARIOS.index(k[0]), MODES.index(k[1]), TORPEDOES.index(k[2]))) if set(conditions[k]) == set(PLANNERS)]
    outcomes = Counter()
    for pair in pairs:
        d, h = pair["dvo"]["outcome"] == "AVOIDED", pair["hybrid"]["outcome"] == "AVOIDED"
        outcomes["both_avoided" if d and h else "dvo_only" if d else "hybrid_only" if h else "both_hit"] += 1
    paired = {k: outcomes[k] for k in ("both_avoided", "dvo_only", "hybrid_only", "both_hit")}
    planners = {}
    for p in PLANNERS:
        subset = [r for r in runs if r["planner"] == p]
        times = [r["ms"] for r in tables["plans.csv"] if r["planner"] == p]
        planners[p] = {"n": len(subset), "avoided": sum(r["outcome"] == "AVOIDED" for r in subset), "hit": sum(r["outcome"] == "HIT" for r in subset), "plan_count": distribution([r["plan_count"] for r in subset]), "plan_ms": distribution(times)}
    cells = {}
    for s in SCENARIOS:
        for mode in MODES:
            for p in PLANNERS:
                subset = [r for r in runs if r["scenario"] == s and r["mode"] == mode and r["planner"] == p]
                cells[f"{s}|{mode}|{p}"] = {"n": len(subset), "avoided": sum(r["outcome"] == "AVOIDED" for r in subset), "closest_m_median": stats.median([r["closest_m"] for r in subset]) if subset else None}
    if len(runs) != 48 or len(pairs) != 24 or any(v["n"] != 3 for v in cells.values()):
        raise ValueError("final comparison requires complete 48-run / 24-pair matrix; incomplete batch left unpublished")
    figures = {"paired-outcomes.svg": paired_chart(paired, len(pairs)), "scenario-guidance-matrix.svg": matrix_chart(cells), "planning-tradeoff.svg": tradeoff_chart(planners)}
    trajectory, trajectory_info = trajectory_chart(pairs, grouped)
    if trajectory:
        figures["matched-trajectory.svg"] = trajectory
    selected = ["paired-outcomes.svg", "scenario-guidance-matrix.svg", "matched-trajectory.svg" if trajectory else "planning-tradeoff.svg"]
    summary = {"dataset": "latest DVO/Hybrid final", "valid_runs": len(runs), "invalid_runs": 0, "zero_plan_runs": 0, "paired_conditions": len(pairs), "paired_outcomes": paired, "planners": planners, "scenario_guidance": cells, "rows": {n: len(r) for n,r in tables.items()}, "trajectory": trajectory_info, "validation": validation, "reused_DVO_runs": provenance.get("reused_runs", []), "comparison_limit": "No latest same-code A* control group. One final run per condition; not a confidence interval or claim of overall Hybrid superiority."}
    assets = Path(os.path.relpath(output, page.parent)).as_posix()
    captions = {
        "paired-outcomes.svg": f"동일한 {len(pairs)}개 조건을 한 쌍씩 비교했습니다. 두 플래너 모두 회피 {paired['both_avoided']}쌍, DVO만 회피 {paired['dvo_only']}쌍, Hybrid만 회피 {paired['hybrid_only']}쌍, 둘 다 피격 {paired['both_hit']}쌍입니다.",
        "scenario-guidance-matrix.svg": "유도 방식별로 나눠 접근 방향을 비교했습니다. 각 칸의 분모는 어뢰 3종이며, 거리는 해당 세 실험의 closest_m 중앙값입니다.",
        "matched-trajectory.svg": "kinematics.csv의 실제 ROV·어뢰 좌표입니다. 결과가 갈린 조건을 규칙에 따라 선택하고, 최근접 시점 주변의 동일 경과시간 구간을 같은 축으로 비교했습니다. 전체 실험 궤적이 아닌 구간 확대입니다.",
        "planning-tradeoff.svg": "run당 계획 호출 수와 호출당 계산 시간의 중앙값·IQR입니다. 조건·호출 간 분포이지 반복 실험의 신뢰구간은 아닙니다.",
    }
    block = ['<!-- Measured final DVO/Hybrid results: scripts/build_manta_results.py -->', '<div class="manta-metrics">']
    for label, value, cls in (("유효 실험", "48 / 48", ""), ("DVO · 최종 AVOIDED", f'{planners["dvo"]["avoided"]} / 24', "dvo"), ("Hybrid · 최종 AVOIDED", f'{planners["hybrid"]["avoided"]} / 24', "hybrid"), ("계획 발행 0회", "0 runs", "")):
        block.append(f'<article class="{cls}"><span>{label}</span><strong>{value}</strong></article>')
    block += ['</div>', '<p class="method-note">48개 실행은 24개 동일 조건의 DVO/Hybrid 쌍입니다. 각 조건당 최종 실행 1회이며 초기 A*/DVO와 파일럿 데이터는 집계하지 않았습니다.</p>', '<article class="manta-card manta-warning"><h3>구조적 개선과 회피율 개선은 같지 않았다</h3><p>Hybrid는 A* 전역 경로와 DVO 국소 회피를 연결한 구조적 개선이지만, 이번 24조건 paired 실험에서 DVO 단독보다 높은 전체 회피율을 보이지는 않았습니다.</p></article>']
    for name in selected:
        digest = hashlib.sha256(figures[name].encode()).hexdigest()[:12]
        url = f"{assets}/{name}?v={digest}"
        block.append(f'<figure class="research-figure manta-generated-figure"><img loading="lazy" decoding="async" src="{url}" alt="{html.escape(captions[name])}"><figcaption>{captions[name]}</figcaption><a class="back-link" href="{url}" target="_blank" rel="noopener">차트 확대 ↗</a></figure>')
    # Text equivalents remain readable on narrow screens and with images disabled.
    block.append('<details class="manta-data-details"><summary>유도 방식·방향별 수치와 계획 비용 보기</summary><table class="metric-table manta-result-table"><caption>방향별 결과 · AVOIDED / 3 · 최근접 거리 중앙값</caption><thead><tr><th>유도 방식 / 방향</th><th>DVO</th><th>Hybrid</th></tr></thead><tbody>')
    for mode in MODES:
        for s in SCENARIOS:
            block.append(f'<tr><td data-label="조건">{LABEL[mode]} / {LABEL[s]}</td>')
            for p in PLANNERS:
                v = cells[f"{s}|{mode}|{p}"]
                block.append(f'<td data-label="{LABEL[p]}">{v["avoided"]}/3 · {v["closest_m_median"]:.2f} m</td>')
            block.append('</tr>')
    block.append('</tbody></table><p>계획 호출 수와 계산 시간은 실제 완료된 계획 로그를 기준으로 집계했습니다. 5 Hz 타이머가 항상 초당 5회 계획 완료를 보장하지는 않습니다.</p><ul>')
    for p in PLANNERS:
        v = planners[p]
        block.append(f'<li>{LABEL[p]}: run당 호출 수 중앙값 {v["plan_count"]["median"]:.1f}회 · 호출당 시간 중앙값 {v["plan_ms"]["median"]:.3f} ms / p95 {v["plan_ms"]["p95"]:.3f} ms</li>')
    block.append('</ul></details><p class="method-note">거리값은 CSV 반올림 표시입니다. HIT는 틱 사이 상대운동의 3D 최근접 거리 ≤ 1.0 m 판정이며, 표본 최소거리나 XY 투영만으로 판정을 다시 만들지 않았습니다.</p>')
    if provenance.get("reused_runs"):
        block.append(f'<p class="method-note">DVO {len(provenance["reused_runs"])}개 실행은 해당 계획·제어 로직과 실험 조건이 동일함을 검증한 v2 기록을 재사용했습니다. 나머지 파일럿 실행은 포함하지 않았습니다.</p>')
    rendered = "\n".join(block)
    replaced = original[:original.index(START)+len(START)] + "\n" + rendered + "\n" + original[original.index(END):]
    manifest = {"dataset": summary["dataset"], "inputs_sha256": hashes, "archive": provenance.get("archive"), "archive_sha256": provenance.get("archive_sha256"), "version": provenance.get("version"), "selection_rule": "Read six root final CSVs only; require complete unique matrix; no recursive pilot/baseline merge", "selected_figures": selected, "figures": {n: {"sha256": hashlib.sha256(svg.encode()).hexdigest(), "source": "kinematics.csv" if n == "matched-trajectory.svg" else "runs.csv + plans.csv"} for n,svg in figures.items()}, "trajectory": trajectory_info, "validation": validation, "reused_DVO_runs": provenance.get("reused_runs", [])}
    # Nothing above this line mutates the page or output directory.
    output.mkdir(parents=True, exist_ok=True)
    for name, content in figures.items():
        (output / name).write_text(content, encoding="utf-8")
    for name, value in (("summary.json", summary), ("generated-manifest.json", manifest)):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "generated-results.html").write_text(rendered, encoding="utf-8")
    page.write_bytes(replaced.encode("utf-8"))
    print(f"MANTA latest: {len(runs)} valid runs / {len(pairs)} pairs; {paired}; {len(selected)} displayed charts")
    return summary
