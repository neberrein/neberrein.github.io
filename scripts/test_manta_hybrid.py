"""Synthetic fixtures test mechanics only; actual latest CSV has a separate audit."""
import csv
import hashlib
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
import build_manta_hybrid as h
import build_manta_results as dispatch


class HybridResultsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="manta-paired-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "input"
        self.source.mkdir()
        self.output = self.root / "output"
        self.page = self.root / "page.html"
        self.original = '\ufeffUNTOUCHED\r\n' + h.START + '\r\nfixture\r\n' + h.END + '\r\nUNTOUCHED END'
        self.page.write_bytes(self.original.encode())
        self.tables = {n: [] for n in h.COLUMNS}
        index = 0
        for scenario in h.SCENARIOS:
            for mode in h.MODES:
                for torpedo in h.TORPEDOES:
                    for p in h.PLANNERS:
                        rid = f"FIXTURE_ONLY_{scenario}_{mode}_{torpedo}_{p}"
                        avoided = index < 11 or (p == "dvo" and 11 <= index < 15) or (p == "hybrid" and 15 <= index < 17)
                        outcome = "AVOIDED" if avoided else "HIT"
                        row = {k: "0" for k in h.COLUMNS["runs.csv"]}
                        row.update(run_id=rid, scenario=scenario, mode=mode, torpedo=torpedo, planner=p, outcome=outcome, closest_m="2" if avoided else ".8", engagements="1", plan_count="2", plan_ms_mean="1.5", plan_ms_median="1.5", duration_sec="10")
                        self.tables["runs.csv"].append(row)
                        for t in range(2):
                            self.tables["plans.csv"].append(dict(run_id=rid,t_rel=str(t),planner=p,ms=str(t+1),waypoints="2",boxes="0",vo_active="1"))
                        self.tables["events.csv"].append(dict(run_id=rid,t_rel="0",type="ENGAGE",value="30"))
                        for t in range(4):
                            row = {k: "0" for k in h.COLUMNS["kinematics.csv"]}
                            row.update(run_id=rid,t_rel=str(t),sim_time_sec=str(t),rov_x=str(t),torpedo_x=str(t+2),distance_m=str(2+t))
                            self.tables["kinematics.csv"].append(row)
                        row = {k: "1" for k in h.COLUMNS["controls.csv"]}
                        row.update(run_id=rid,t_rel="0")
                        self.tables["controls.csv"].append(row)
                        self.tables["run_metrics_extended.csv"].append(dict(run_id=rid,scenario=scenario,planner=p,mode=mode,torpedo=torpedo,outcome=outcome,min_distance_m="2",HIT_or_AVOIDED=outcome))
                    index += 1
        self.write_tables()
        self.metadata()

    def write_tables(self):
        for name, rows in self.tables.items():
            with (self.source / name).open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, h.COLUMNS[name])
                writer.writeheader()
                writer.writerows(rows)

    def json(self, name, value):
        (self.source / name).write_text(json.dumps(value), encoding="utf-8")

    def metadata(self):
        from collections import Counter
        runs = self.tables["runs.csv"]
        self.json("provenance.json", {"archive": "TEST_FIXTURE_ONLY.zip", "version": "fixture", "input_sha256": {n: hashlib.sha256((self.source/n).read_bytes()).hexdigest() for n in h.COLUMNS}, "regression_cases": [f"fixture {i}" for i in range(14)]})
        self.json("final_integrity.json", {"rows": {n.removesuffix('.csv'):len(r) for n,r in self.tables.items()}, "valid":len(runs), "invalid":0, "overall":"SUCCESS", "problems":[], "zero_plan_run_ids":[], "pipeline_verified":True,"native_bags_verified":True, "outcomes_by_planner": {p:dict(Counter(r["outcome"] for r in runs if r["planner"]==p)) for p in h.PLANNERS}})
        self.json("pipeline_audit.json", {"all_pipelines_verified":True, "runs":[{"run_id":r["run_id"], "pipeline_verified":True,"nonzero_thrusters":True} for r in runs]})
        self.json("rosbag_integrity.json", [{"run_id":r["run_id"],"verified":True} for r in runs])

    def build(self):
        return h.build_hybrid(self.source, self.output, self.page)

    def assert_abort(self):
        with self.assertRaises(ValueError):
            self.build()
        self.assertEqual(self.page.read_bytes(), self.original.encode())
        self.assertFalse(self.output.exists())

    def test_actual_latest_batch(self):
        source = Path(__file__).resolve().parents[1] / "portfolio_data/manta/latest"
        if not (source/"runs.csv").exists():
            self.skipTest("actual final batch not present")
        tables, grouped, provenance, hashes, verification = h.load_verified(source)
        self.assertEqual([len(tables[n]) for n in h.COLUMNS], [48,23529,147,24104,23599,48])
        self.assertTrue(verification["pipeline_verified"] and verification["native_bags_verified"])
        self.assertEqual(len(provenance["reused_runs"]),4)

    def test_complete_pairing_and_three_charts(self):
        result = self.build()
        self.assertEqual(result["paired_outcomes"], dict(both_avoided=11,dvo_only=4,hybrid_only=2,both_hit=7))
        self.assertEqual(result["planners"]["dvo"]["avoided"],15)
        self.assertEqual(result["planners"]["hybrid"]["avoided"],13)
        self.assertEqual(result["paired_conditions"],24)
        manifest = json.loads((self.output/"generated-manifest.json").read_text())
        self.assertEqual(len(manifest["selected_figures"]),3)
        for n in manifest["figures"]:
            ET.parse(self.output/n)

    def test_only_result_block_and_idempotence(self):
        self.build()
        first = self.page.read_bytes()
        self.assertEqual(first.split(h.START.encode())[0],self.original.encode().split(h.START.encode())[0])
        self.assertEqual(first.split(h.END.encode())[1],self.original.encode().split(h.END.encode())[1])
        self.build()
        self.assertEqual(first,self.page.read_bytes())

    def test_pilots_never_merged(self):
        pilot = self.source/"pilot/v2"
        pilot.mkdir(parents=True)
        (pilot/"runs.csv").write_text("deliberately malformed fixture")
        self.assertEqual(self.build()["valid_runs"],48)

    def test_duplicate_condition_abort(self):
        row = dict(self.tables["runs.csv"][0],run_id="fixture_duplicate")
        self.tables["runs.csv"].append(row)
        self.write_tables(); self.metadata(); self.assert_abort()

    def test_missing_csv_abort(self):
        (self.source/"controls.csv").unlink()
        self.assert_abort()

    def test_incomplete_matrix_abort(self):
        rid = self.tables["runs.csv"][0]["run_id"]
        for n in self.tables:
            self.tables[n] = [r for r in self.tables[n] if r["run_id"] != rid]
        self.write_tables(); self.metadata(); self.assert_abort()

    def test_zero_plans_abort(self):
        self.tables["runs.csv"][0]["plan_count"]="0"
        self.write_tables(); self.metadata(); self.assert_abort()

    def test_stale_hash_abort(self):
        self.tables["runs.csv"][0]["closest_m"]="3"
        self.write_tables(); self.assert_abort()

    def test_plan_count_mismatch_abort(self):
        self.tables["plans.csv"].pop()
        self.write_tables(); self.metadata(); self.assert_abort()

    def test_unknown_run_abort(self):
        self.tables["controls.csv"][0]["run_id"]="unknown_fixture"
        self.write_tables(); self.metadata(); self.assert_abort()

    def test_nonfinite_coordinate_abort(self):
        self.tables["kinematics.csv"][0]["rov_x"]="nan"
        self.write_tables(); self.metadata(); self.assert_abort()

    def test_inconsistent_verdict_abort(self):
        self.tables["run_metrics_extended.csv"][0]["HIT_or_AVOIDED"]="HIT"
        self.write_tables(); self.metadata(); self.assert_abort()

    def test_audit_failed_abort(self):
        self.json("pipeline_audit.json", {"all_pipelines_verified":False,"runs":[]})
        self.assert_abort()

    def test_missing_metadata_abort(self):
        (self.source/"rosbag_integrity.json").unlink()
        self.assert_abort()

    def test_integrity_report_mismatch_abort(self):
        data=json.loads((self.source/"final_integrity.json").read_text())
        data["valid"]=47
        self.json("final_integrity.json",data)
        self.assert_abort()


if __name__ == "__main__":
    unittest.main()
