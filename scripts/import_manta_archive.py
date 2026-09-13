"""Import only explicit datasets; never recursively merge ZIP experiment copies."""
import argparse
import csv
import hashlib
import io
import json
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--latest', type=Path, required=True, help='Complete final DVO/Hybrid ZIP; audited before filtering public DVO results')
parser.add_argument('--baseline', type=Path, required=True, help='Unmodified initial A*/DVO ZIP')
parser.add_argument('--retain-pilots', action='store_true', help='Keep separate ignored local pilot copies')
args = parser.parse_args()
NAMES = ["runs.csv", "plans.csv", "events.csv", "kinematics.csv", "controls.csv", "run_metrics_extended.csv"]
EXPECTED = dict(zip(NAMES, [48, 23529, 147, 24104, 23599, 48]))
archive = args.latest.resolve()
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    tables = {n: list(csv.DictReader(io.StringIO(z.read(n).decode("utf-8-sig")))) for n in NAMES}
    reported = json.loads(z.read('analysis/final_integrity.json'))
    assert {n.removesuffix('.csv'):len(r) for n,r in tables.items()} == reported['rows']
    counts = Counter((r["planner"], r["outcome"]) for r in tables["runs.csv"])
    assert set(r['planner'] for r in tables['runs.csv']) == {'dvo','hybrid'}
    assert all(sum(v for (planner,_),v in counts.items() if planner==p)==24 for p in ('dvo','hybrid'))
    ids = {r["run_id"] for r in tables["runs.csv"]}
    assert len(ids) == 48
    assert all(int(r["plan_count"]) > 0 and int(r["engagements"]) > 0 for r in tables["runs.csv"])
    for n in NAMES[1:]:
        assert {r["run_id"] for r in tables[n]} == ids
    integrity = json.loads(z.read("analysis/final_integrity.json"))
    assert integrity["overall"] == "SUCCESS" and not integrity["problems"]
    pipeline = json.loads(z.read("analysis/pipeline_audit.json"))
    bags = json.loads(z.read("analysis/rosbag_integrity.json"))
    assert len(pipeline["runs"]) == 48 and all(r["pipeline_verified"] and r["nonzero_thrusters"] for r in pipeline["runs"])
    assert len(bags) == 48 and all(r["verified"] for r in bags)
    reuse = json.loads(z.read("metadata/reused_runs.json"))
    verification = json.loads(z.read("metadata/DVO_reuse_code_verification.json"))
    assert len(reuse) == verification["allowed_reuse_run_count"] == 4
    assert all(verification["checks"].values()) and all(r["DVO_logic_unchanged"] and r["run_id"] in ids for r in reuse)
    regression_log = z.read("tests/logs/regression_2.log").decode()
    regression_cases = [line.removeprefix("PASS ") for line in regression_log.splitlines() if line.startswith("PASS ")]
    assert len(regression_cases) == 14 and "ALL REGRESSIONS PASSED" in regression_log
    latest = ROOT / "portfolio_data/manta/latest"
    latest.mkdir(parents=True, exist_ok=True)
    for n in NAMES:
        (latest / n).write_bytes(z.read(n))
    (latest / "final_integrity.json").write_text(json.dumps(integrity, indent=2), encoding="utf-8")
    safe_pipeline = {"checked_at": pipeline["checked_at"], "all_pipelines_verified": pipeline["all_pipelines_verified"], "runs": pipeline["runs"]}
    (latest / "pipeline_audit.json").write_text(json.dumps(safe_pipeline, indent=2), encoding="utf-8")
    safe_bags = [{k: v for k, v in r.items() if k != "path"} for r in bags]
    (latest / "rosbag_integrity.json").write_text(json.dumps(safe_bags, indent=2), encoding="utf-8")
    config = json.loads(z.read("metadata/experiment_config.json"))
    provenance = {
        "archive": archive.name, "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "version": config["version"], "condition_values": config["condition_values"],
        "reused_runs": [{k: r[k] for k in ("run_id", "reused_from_version", "DVO_logic_unchanged")} for r in reuse],
        "reuse_code_verification": verification,
        "regression_cases": regression_cases, "regression_log_sha256": hashlib.sha256(z.read("tests/logs/regression_2.log")).hexdigest(),
        "code_sha256": {n: hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith("code/") and not n.endswith("/")},
        "validation_origin": "Supplied Linux ROS 2 experiment audit reports; native bags are not included in this archive.",
        "input_sha256": {n: hashlib.sha256(z.read(n)).hexdigest() for n in NAMES},
    }
    (latest / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    # Keep pilots physically separate. They are not input to the published results.
    for version in ("v1", "v2") if args.retain_pilots else ():
        for planner in ("dvo", "hybrid"):
            target = ROOT / f"portfolio_data/manta/pilot/{version}/{planner}"
            target.mkdir(parents=True, exist_ok=True)
            for n in NAMES:
                (target / n).write_bytes(z.read(f"pilot_versions/{version}/{planner}/{n}"))
    print("Latest independently verified:", reported['rows'], dict(counts), "14 upstream regressions; verified DVO reuse records")

baseline = args.baseline.resolve()
with zipfile.ZipFile(baseline) as z:
    assert z.testzip() is None
    target = ROOT / "portfolio_data/manta/baseline_original"
    target.mkdir(parents=True, exist_ok=True)
    for n in NAMES:
        (target / n).write_bytes(z.read(n))
    (target / "provenance.json").write_text(json.dumps({"archive": baseline.name, "archive_sha256": hashlib.sha256(baseline.read_bytes()).hexdigest(), "input_sha256": {n: hashlib.sha256(z.read(n)).hexdigest() for n in NAMES}, "purpose": "Before shared pipeline fixes. Not a same-code A* control group for the latest DVO/Hybrid comparison."}, indent=2), encoding="utf-8")
