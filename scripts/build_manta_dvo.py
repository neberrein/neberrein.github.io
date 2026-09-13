"""Public DVO results, following the user's final instruction to omit Hybrid.

Compare complete initial/latest 24-condition DVO batches, select one whole
batch by AVOIDED rate (latest wins ties). Never select the best run per case.
Shared path/controller changes prevent attributing the change to DVO alone.
The full supplied archive remains separate as provenance, not public results.
"""
import hashlib
import html
import json
import os
import statistics as stats
from collections import Counter, defaultdict
from pathlib import Path
import build_manta_hybrid as audit

START, END = audit.START, audit.END
SCENARIOS, MODES, TORPEDOES = audit.SCENARIOS, audit.MODES, audit.TORPEDOES
LABEL = audit.LABEL


def compare_batches(initial, latest):
    expected = {(s,m,t) for s in SCENARIOS for m in MODES for t in TORPEDOES}
    groups = {}
    for name, rows in (("initial",initial),("latest",latest)):
        mapping = {}
        for row in rows:
            k = audit.key(row)
            if k in mapping or row["planner"] != "dvo":
                raise ValueError("DVO comparison must contain unique DVO conditions only")
            if row["outcome"] not in ("AVOIDED","HIT") or audit.finite(row["plan_count"]) == 0 or audit.finite(row["engagements"]) == 0:
                raise ValueError("invalid DVO run cannot be selected as public performance")
            audit.finite(row["closest_m"])
            mapping[k]=row
        if set(mapping) != expected:
            raise ValueError("initial/latest DVO comparison requires the same complete 24 conditions")
        groups[name]=mapping
    counts = {name:sum(r["outcome"] == "AVOIDED" for r in rows.values()) for name,rows in groups.items()}
    selected = "latest" if counts["latest"] >= counts["initial"] else "initial"
    transitions = Counter((groups["initial"][k]["outcome"], groups["latest"][k]["outcome"]) for k in expected)
    info={"initial":{"avoided":counts["initial"],"hit":24-counts["initial"],"n":24},"latest":{"avoided":counts["latest"],"hit":24-counts["latest"],"n":24},"selected_batch":selected,"selection_rule":"Select the entire higher-AVOIDED-rate DVO batch; prefer latest on ties. No per-condition best-of selection.","changed_to_avoided":transitions[("HIT","AVOIDED")],"changed_to_hit":transitions[("AVOIDED","HIT")],"both_avoided":transitions[("AVOIDED","AVOIDED")],"both_hit":transitions[("HIT","HIT")]}
    return groups, info


def before_after_chart(info, mobile=False):
    if mobile:
        parts=audit.svg_start("초기·최신 DVO 회피율 비교", "같은 24개 조건의 초기·최신 배치 비교",width=440,height=405)
        parts += [audit.text(30,75,"같은 24개 조건 · 각 조건 최종 실행 1회",19)]
        for i,(name,label,color) in enumerate((("initial","초기 DVO","#778691"),("latest","최신 DVO","#23774a"))):
            y=113+i*91
            r=info[name]
            parts += [audit.text(30,y,f'{label} · {r["avoided"]}/24 ({r["avoided"]/24*100:.1f}%)',22),f'<rect x="30" y="{y+16}" width="{r["avoided"]/24*350}" height="32" fill="{color}"/>']
        parts += ['<path d="M30 274H380" stroke="#83939e"/>']
        for value in (0,50,100):parts.append(audit.text(30+value/100*350,302,f'{value}%',18,anchor='middle'))
        parts += [audit.text(30,345,f'새로 회피 {info["changed_to_avoided"]}개 / 반대로 피격 {info["changed_to_hit"]}개',20),audit.text(30,378,'경로·제어 연동도 함께 수정한 전후 비교',19)]
        return audit.finish(parts)
    parts=audit.svg_start("초기 DVO와 최신 DVO · 동일한 24개 조건", "경로·제어 연동 수정 전후 비교. 회피율이 높은 전체 배치를 선택하며 조건별 좋은 결과만 모으지 않습니다.",height=360)
    parts.append(audit.text(30,74,"경로·제어 연동 수정 전후 · DVO 단독 알고리즘의 효과로 단정하지 않음",16))
    for i,(name,label,color) in enumerate((("initial","초기 DVO","#778691"),("latest","최신 DVO","#23774a"))):
        y=112+i*87
        r=info[name]
        parts += [audit.text(30,y+30,label,20),f'<rect x="205" y="{y}" width="{r["avoided"]/24*465}" height="44" fill="{color}"/>',audit.text(230+r["avoided"]/24*465,y+30,f'{r["avoided"]}/24 · {r["avoided"]/24*100:.1f}%',21)]
    parts += ['<path d="M205 275H670" stroke="#83939e"/>']
    for value in (0,25,50,75,100):
        parts.append(audit.text(205+value/100*465,302,f"{value}%",15,anchor="middle"))
    parts.append(audit.text(30,340,f'새로 회피 {info["changed_to_avoided"]}개 / 반대로 피격 {info["changed_to_hit"]}개 · 각 조건당 최종 실행 1회',16))
    return audit.finish(parts)


def selected_matrix(cells, mobile=False):
    if mobile:
        parts=audit.svg_start('선택한 DVO · 방향별 결과','어뢰 3종 중 최종 회피 횟수와 최근접 거리 중앙값',width=440,height=690)
        parts += [audit.text(30,76,'AVOIDED / 3 · 최근접 거리 중앙값 (m)',19)]
        for j,m in enumerate(MODES):
            top=117+j*273
            parts.append(audit.text(30,top,LABEL[m],23))
            for i,s in enumerate(SCENARIOS):
                y=top+24+i*54
                v=cells[f'{s}|{m}']
                fill='#edf5ef' if v['avoided']>=2 else '#f8eeee'
                parts += [audit.text(30,y+33,LABEL[s],23),f'<rect x="117" y="{y}" width="287" height="47" rx="4" fill="{fill}"/>',audit.text(139,y+33,f'{v["avoided"]}/3',25),audit.text(383,y+33,f'{v["closest_m_median"]:.2f} m',23,anchor='end')]
        parts += [audit.text(30,666,'HIT도 유효 실험에 포함 · 각 조건 1회',19)]
        return audit.finish(parts)
    parts=audit.svg_start("선택한 DVO 결과 · 유도 방식과 접근 방향", "각 칸은 어뢰 3종의 AVOIDED 수와 최근접 거리 중앙값입니다.",height=700)
    parts.append(audit.text(30,72,"각 칸: AVOIDED / 3 · closest_m 중앙값 (m)",17))
    for j,m in enumerate(MODES):
        top=111+j*276
        parts.append(audit.text(30,top,LABEL[m],22))
        for i,s in enumerate(SCENARIOS):
            y=top+22+i*52
            v=cells[f"{s}|{m}"]
            fill="#edf5ef" if v["avoided"]>=2 else "#f8eeee"
            parts += [audit.text(45,y+32,LABEL[s],19),f'<rect x="240" y="{y}" width="475" height="46" rx="4" fill="{fill}"/>',audit.text(270,y+31,f'{v["avoided"]}/3 AVOIDED',20),audit.text(685,y+31,f'{v["closest_m_median"]:.2f} m',20,anchor="end")]
    parts.append(audit.text(30,673,"HIT도 유효 실험에 포함 · 각 조건 최종 실행 1회 · 신뢰구간이나 통계적 유의성을 뜻하지 않음",15))
    return audit.finish(parts)


def dvo_trajectory(rows, grouped, mobile=False):
    # Choose the first complete AVOIDED condition, deterministic configured order.
    ordered=sorted(rows,key=lambda r:(SCENARIOS.index(r["scenario"]),MODES.index(r["mode"]),TORPEDOES.index(r["torpedo"])))
    chosen=next((r for r in ordered if r["outcome"]=="AVOIDED" and len(grouped[r["run_id"]])>=2),None)
    if chosen is None:
        raise ValueError("no measured DVO trajectory available")
    samples=grouped[chosen["run_id"]]
    closest=min(samples,key=lambda r:float(r["distance_m"]))
    center=float(closest["t_rel"])
    lo,hi=max(0,center-6),center+4
    window=[r for r in samples if lo<=float(r["t_rel"])<=hi]
    if len(window)<2:
        raise ValueError("not enough measured trajectory samples")
    coords=[(float(r[f"{v}_x"]),float(r[f"{v}_y"])) for r in window for v in ("rov","torpedo")]
    xs,ys=zip(*coords)
    span=max(max(xs)-min(xs),max(ys)-min(ys),1)*1.15
    xmin,ymin=(max(xs)+min(xs)-span)/2,(max(ys)+min(ys)-span)/2
    left,top,size=(76,210,290) if mobile else (215,150,360)
    project=lambda x,y:(left+(x-xmin)/span*size,top+size-(y-ymin)/span*size)
    parts=audit.svg_start("DVO 실제 회피 궤적" if mobile else "DVO 대표 회피 조건 · 실제 ROV·어뢰 궤적", "kinematics.csv 실제 좌표의 XY 투영. 최근접 표본 전후 10초 구간 확대. X와 Y 동일 축척; 실제 3D HIT 판정과 구분합니다.",width=440 if mobile else 880,height=590 if mobile else 600)
    s,m,t=audit.key(chosen)
    if mobile:
        parts += [audit.text(30,76,f'{LABEL[s]} / {LABEL[m]} / {LABEL[t]}',20),audit.text(30,108,f'AVOIDED · 전체 closest_m {float(chosen["closest_m"]):.2f} m',21),audit.text(30,140,f'로그 상대시간 {lo:.1f}–{hi:.1f} s 확대',19)]
    else:
        parts += [audit.text(30,73,f'{LABEL[s]} / {LABEL[m]} / {LABEL[t]} · AVOIDED · 전체 run closest_m {float(chosen["closest_m"]):.2f} m',18),audit.text(30,105,f'최근접 표본 주변 구간 확대 · 로그 상대시간(t_rel) {lo:.1f}–{hi:.1f} s',17)]
    for tick in range(5):
        f=tick/4
        x,y=left+size*f,top+size*(1-f)
        parts += [f'<path d="M{x} {top}V{top+size}M{left} {y}H{left+size}" stroke="#e1e7eb"/>',audit.text(x,top+size+25,f'{xmin+span*f:.1f}',15,anchor="middle"),audit.text(left-12,y+5,f'{ymin+span*f:.1f}',15,anchor="end")]
    for vehicle,color,dashed,label in (("rov","#23774a",False,"ROV · 실선"),("torpedo","#a83b38",True,"어뢰 · 점선")):
        points=[project(float(r[f"{vehicle}_x"]),float(r[f"{vehicle}_y"])) for r in window]
        line=" ".join(f'{x:.3f},{y:.3f}' for x,y in points)
        parts.append(f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="3"'+(' stroke-dasharray="7 4"' if dashed else '')+'/>')
        x,y=project(float(closest[f"{vehicle}_x"]),float(closest[f"{vehicle}_y"]))
        parts += [f'<circle cx="{x:.3f}" cy="{y:.3f}" r="6" fill="{color}" stroke="#fff" stroke-width="2"/>',audit.text(35 if vehicle=='rov' else 233,179,label,22,color) if mobile else audit.text(622,193 if vehicle=="rov" else 225,label,18,color)]
    if mobile:
        parts += [audit.text(left+size/2,549,'X (m)',22,anchor='middle'),audit.text(8,top+size/2,'Y (m)',19),audit.text(30,579,'점 · 최근접 표본 / 실제 좌표의 XY 투영',19)]
    else:
        parts += [audit.text(622,266,"점 · 최근접 표본",17),audit.text(left+size/2,555,"X (m)",17,anchor="middle"),audit.text(116,top+size/2,"Y (m)",17),audit.text(30,588,"실측 표본만 연결 · 전체 실험 궤적이 아닌 구간 확대 · XY 투영으로 3D 피격을 재판정하지 않음",15)]
    return audit.finish(parts),{"run_id":chosen["run_id"],"condition":{"scenario":s,"mode":m,"torpedo":t},"window_t_rel_sec":[lo,hi],"projection":"measured XY, equal X/Y aspect", "selection_rule":"First complete AVOIDED condition in configured direction/mode/torpedo order"}


def build_dvo(source,output,page,baseline=None):
    original=page.read_bytes().decode("utf-8")
    if original.count(START)!=1 or original.count(END)!=1 or original.index(START)>=original.index(END):
        raise ValueError("RESULTS marker error")
    tables,grouped,provenance,hashes,validation=audit.load_verified(source)
    baseline=baseline or source.parent/"baseline_original"
    base_tables={n:audit.read_table(baseline/n,required) for n,required in audit.COLUMNS.items()}
    base_provenance=json.loads((baseline/"provenance.json").read_text())
    base_hashes={n:hashlib.sha256((baseline/n).read_bytes()).hexdigest() for n in audit.COLUMNS}
    if base_provenance.get("input_sha256")!=base_hashes:
        raise ValueError("initial baseline hashes differ from preserved archive")
    initial=[r for r in base_tables["runs.csv"] if r["planner"]=="dvo"]
    latest=[r for r in tables["runs.csv"] if r["planner"]=="dvo"]
    mappings,comparison=compare_batches(initial,latest)
    selected_name=comparison["selected_batch"]
    rows=list(mappings[selected_name].values())
    selected_tables=tables if selected_name=="latest" else base_tables
    kin=defaultdict(list)
    for r in selected_tables["kinematics.csv"]:
        if r["run_id"] in {v["run_id"] for v in rows}:
            for field in ("t_rel","rov_x","rov_y","torpedo_x","torpedo_y","distance_m"):
                audit.finite(r[field],signed=field not in ("t_rel","distance_m"))
            kin[r["run_id"]].append(r)
    cells={}
    for s in SCENARIOS:
        for m in MODES:
            subset=[r for r in rows if r["scenario"]==s and r["mode"]==m]
            cells[f"{s}|{m}"]={"n":len(subset),"avoided":sum(r["outcome"]=="AVOIDED" for r in subset),"closest_m_median":stats.median(float(r["closest_m"]) for r in subset)}
    selected_ids={r["run_id"] for r in rows}
    plans=[r for r in selected_tables["plans.csv"] if r["run_id"] in selected_ids]
    times=[audit.finite(r["ms"]) for r in plans]
    trajectory,trajectory_info=dvo_trajectory(rows,kin)
    figures={"dvo-before-after.svg":before_after_chart(comparison),"dvo-scenario-guidance.svg":selected_matrix(cells),"dvo-measured-trajectory.svg":trajectory}
    mobile_figures={"dvo-before-after-mobile.svg":before_after_chart(comparison,True),"dvo-scenario-guidance-mobile.svg":selected_matrix(cells,True),"dvo-measured-trajectory-mobile.svg":dvo_trajectory(rows,kin,True)[0]}
    summary={"dataset":"DVO initial/latest whole-batch selection","public_planner":"DVO","valid_runs":24,"invalid_runs":0,"zero_plan_runs":0,"comparison":comparison,"selected_run_ids":sorted(selected_ids),"scenario_guidance":cells,"plan_ms":audit.distribution(times),"plan_count":audit.distribution([float(r["plan_count"]) for r in rows]),"trajectory":trajectory_info,"latest_pipeline_validation":validation,"limits":"Before/after shared path/controller changes, not an isolated DVO algorithm effect. One final run per condition; no statistical significance claim."}
    asset_path=Path(os.path.relpath(output,page.parent)).as_posix()
    selected=comparison[selected_name]
    captions={"dvo-before-after.svg":f'초기 DVO {comparison["initial"]["avoided"]}/24와 최신 DVO {comparison["latest"]["avoided"]}/24를 동일한 24개 조건으로 비교했습니다. 회피율이 높은 전체 배치를 사용했으며 조건별 좋은 결과만 모으지 않았습니다.',"dvo-scenario-guidance.svg":"선택한 DVO 24개 실행의 결과입니다. 각 칸은 어뢰 3종 중 최종 회피 횟수와 최근접 거리 중앙값입니다.","dvo-measured-trajectory.svg":"kinematics.csv의 실제 ROV·어뢰 좌표입니다. 정해진 순서에서 첫 회피 조건을 선택하고 최근접 표본 주변 구간만 확대했습니다. 두 축의 단위와 축척은 동일하며 도식으로 만든 궤적이 아닙니다."}
    block=['<!-- Public DVO results regenerated by scripts/build_manta_results.py -->','<div class="manta-metrics">']
    for label,value in (("선택한 결과", "최신 DVO" if selected_name=="latest" else "초기 DVO"),("최종 AVOIDED",f'{selected["avoided"]} / 24'),("회피율",f'{selected["avoided"]/24*100:.1f}%'),("유효 실험","24 / 24")):
        block.append(f'<article class="dvo"><span>{label}</span><strong>{value}</strong></article>')
    block += ['</div>',f'<p class="method-note">초기·최신 DVO는 각각 같은 24개 조건을 실행했습니다. 최종 결과는 회피율이 높은 {"최신" if selected_name=="latest" else "초기"} DVO 전체 배치입니다. HIT도 유효 실험에 포함합니다.</p>',f'<article class="manta-card"><h3>일부 조건에서 개선됐지만 일관된 우위는 아니었다</h3><p>초기 대비 최신 DVO에서 새로 회피한 조건은 {comparison["changed_to_avoided"]}개, 반대로 피격된 조건은 {comparison["changed_to_hit"]}개입니다. 경로·제어 연동도 함께 수정했으므로 회피율 변화를 DVO 알고리즘 단독의 효과로 단정하지 않았습니다.</p></article>']
    for name,content in figures.items():
        digest=hashlib.sha256(content.encode()).hexdigest()[:12]
        url=f'{asset_path}/{name}?v={digest}'
        mobile_name=name.replace('.svg','-mobile.svg')
        mobile_digest=hashlib.sha256(mobile_figures[mobile_name].encode()).hexdigest()[:12]
        mobile_url=f'{asset_path}/{mobile_name}?v={mobile_digest}'
        block.append(f'<figure class="research-figure manta-generated-figure"><picture><source media="(max-width:700px)" srcset="{mobile_url}"><img loading="lazy" decoding="async" src="{url}" alt="{html.escape(captions[name])}"></picture><figcaption>{captions[name]}</figcaption><a class="back-link" href="{url}" target="_blank" rel="noopener">차트 확대 ↗</a></figure>')
    block.append('<details class="manta-data-details"><summary>유도 방식·방향별 수치와 계획 비용 보기</summary><table class="metric-table manta-result-table"><caption>선택한 DVO 결과 · AVOIDED / 3 · 최근접 거리 중앙값</caption><thead><tr><th>유도 방식</th><th>접근 방향</th><th>DVO</th></tr></thead><tbody>')
    for m in MODES:
        for s in SCENARIOS:
            v=cells[f"{s}|{m}"]
            block.append(f'<tr><td data-label="유도 방식">{LABEL[m]}</td><td data-label="접근 방향">{LABEL[s]}</td><td data-label="DVO">{v["avoided"]}/3 · {v["closest_m_median"]:.2f} m</td></tr>')
    block += ['</tbody></table>',f'<p>실제 완료된 계획 로그 기준: 호출당 시간 중앙값 {summary["plan_ms"]["median"]:.3f} ms, p95 {summary["plan_ms"]["p95"]:.3f} ms. run당 호출 수 중앙값 {summary["plan_count"]["median"]:.1f}회입니다. 5 Hz 타이머가 항상 초당 5회 계획 완료를 보장하지는 않습니다.</p>','</details>','<p class="method-note">각 조건 최종 실행 1회이며 통계적 유의성이나 반복 실험의 신뢰구간을 주장하지 않습니다. CSV 거리값은 반올림 표시입니다. HIT는 틱 사이 상대운동의 3D 최근접 거리 ≤ 1.0 m 판정으로, XY 투영만으로 다시 판정하지 않았습니다.</p>']
    reuse=[r for r in provenance.get("reused_runs",[]) if r["run_id"] in selected_ids]
    if reuse:
        block.append(f'<p class="method-note">최신 DVO 중 {len(reuse)}개 실행은 해당 계획·제어 로직과 실험 조건이 동일함을 검증한 v2 기록을 재사용했습니다. 나머지 파일럿 실행은 제외했습니다.</p>')
    rendered="\n".join(block)
    if "hybrid" in rendered.lower():
        raise ValueError("excluded planner leaked into public results")
    replaced=original[:original.index(START)+len(START)]+"\n"+rendered+"\n"+original[original.index(END):]
    manifest={"dataset":summary["dataset"],"inputs_sha256":{"initial":base_hashes,"latest":hashes},"archive_sha256":{"initial":base_provenance["archive_sha256"],"latest":provenance["archive_sha256"]},"selection":comparison,"selected_figures":list(figures),"figures":{n:{"sha256":hashlib.sha256(content.encode()).hexdigest(),"source":"kinematics.csv" if "trajectory" in n else "runs.csv"} for n,content in figures.items()},"trajectory":trajectory_info}
    output.mkdir(parents=True,exist_ok=True)
    for name,content in {**figures,**mobile_figures}.items():
        (output/name).write_text(content,encoding="utf-8")
    for name,value in (("summary.json",summary),("generated-manifest.json",manifest)):
        (output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")
    standalone='<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MANTA DVO measured results</title><link rel="stylesheet" href="../../site.css"></head><body class="manta-page"><main class="section-shell"><div class="case-body">'+rendered.replace(asset_path+'/', '')+'</div></main></body></html>'
    (output/"generated-results.html").write_text(standalone,encoding="utf-8")
    page.write_bytes(replaced.encode())
    print(f'DVO: initial {comparison["initial"]["avoided"]}/24, latest {comparison["latest"]["avoided"]}/24; selected {selected_name}; 3 measured charts')
    return summary
