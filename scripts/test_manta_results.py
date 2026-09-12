"""Synthetic fixtures test the generator only; nothing is published as research data."""
import csv
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
import build_manta_results as m


class MantaResultsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="manta-generator-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.input = self.root / "input"
        self.input.mkdir()
        self.page = self.root / "manta.html"
        self.original = "UNTOUCHED BEFORE\n" + m.START + "\nrepresentative only\n" + m.END + "\nUNTOUCHED AFTER"
        self.page.write_text(self.original, encoding="utf-8")
        self.output = self.root / "generated"

    def row(self, rid="test-only-a", planner="astar", **kwargs):
        row = dict(zip(m.RUN_COLS, [rid,"rear",planner,"PNG","Mk48","AVOIDED",3,2,2,"3|2",1,2,2,2,.2,8]))
        row.update(kwargs)
        return row

    def csv(self, name, columns, rows):
        with (self.input / name).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, columns)
            writer.writeheader()
            writer.writerows(rows)

    def inputs(self, rows, extra=None):
        self.csv("runs.csv", m.RUN_COLS + (extra or []), rows)
        self.csv("plans.csv", m.PLAN_COLS, [])
        self.csv("events.csv", m.EVENT_COLS, [])
        for name in ("collect_log.txt", "scale_info.txt", "params.txt"):
            (self.input / name).write_text("TEST FIXTURE ONLY", encoding="utf-8")

    def build(self):
        return m.build(self.input, self.output, self.page)

    def test_no_csv_no_mutation(self):
        self.assertIsNone(self.build())
        self.assertEqual(self.page.read_text(encoding="utf-8"), self.original)
        self.assertFalse(self.output.exists())

    def test_partial_input_fails(self):
        (self.input / "plans.csv").write_text("", encoding="utf-8")
        with self.assertRaises(ValueError): self.build()
        self.assertEqual(self.page.read_text(encoding="utf-8"), self.original)

    def test_marked_block_only_and_no_invented_figures(self):
        self.inputs([self.row(), self.row("test-only-d", "dvo")])
        summary = self.build()
        self.assertEqual(summary["valid_runs"], 2)
        self.assertFalse(summary["complete_matrix"])
        self.assertIsNone(summary["plan_ms_p95"])
        self.assertTrue(self.page.read_text(encoding="utf-8").startswith("UNTOUCHED BEFORE\n" + m.START))
        self.assertTrue(self.page.read_text(encoding="utf-8").endswith(m.END + "\nUNTOUCHED AFTER"))
        manifest = json.loads((self.output / "generated-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["valid_runs"], 2)
        self.assertLessEqual(len(manifest["selected_figures"]), 3)
        self.assertNotIn("closest-vs-speed-ratio.svg", manifest["figures"])
        self.assertNotIn("trajectory-compare.svg", manifest["figures"])
        self.assertIn("runs.csv", manifest["inputs"])

    def test_ambiguous_duplicate_not_last_row(self):
        self.inputs([self.row(), self.row("test-only-b")])
        self.assertEqual(self.build()["valid_runs"], 0)
        self.assertEqual(self.page.read_text(encoding="utf-8"), self.original)

    def test_latest_valid_explicit_index(self):
        self.inputs([self.row(index=1), self.row("test-only-b",index=2), self.row("test-only-invalid",index=3,outcome="INVALID_ABORT")], ["index"])
        self.assertEqual(self.build()["valid_runs"], 1)
        manifest = json.loads((self.output / "generated-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["selected_run_ids"], ["test-only-b"])

    def test_duplicate_run_id_excluded(self):
        self.inputs([self.row(), self.row(planner="dvo")])
        self.assertEqual(self.build()["valid_runs"], 0)

    def test_nan_rejected_without_output(self):
        self.inputs([self.row(closest_m="nan")])
        with self.assertRaises(ValueError): self.build()
        self.assertEqual(self.page.read_text(encoding="utf-8"), self.original)
        self.assertFalse(self.output.exists())

    def test_missing_column_rejected(self):
        self.inputs([self.row()])
        self.csv("runs.csv", ["run_id"], [{"run_id":"test-only"}])
        with self.assertRaises(ValueError): self.build()

    def test_no_plan_is_invalid(self):
        self.inputs([self.row(plan_count=0)])
        self.assertEqual(self.build()["invalid_runs"], 1)

    def test_speed_metadata_conflict_skips_chart(self):
        self.inputs([self.row(speed_ratio=2)], ["speed_ratio"])
        (self.input / "scale_info.txt").write_text(json.dumps({"rov_speed_mps":1,"torpedo_speed_mps":{"Mk48":3}}), encoding="utf-8")
        self.build()
        self.assertFalse((self.output / "closest-vs-speed-ratio.svg").exists())

    def test_signed_trajectory_axes(self):
        svg = m.axis_chart("test only", [("astar", [(-3,-8),(-1,-5)]),("dvo",[(-4,-9),(-2,-6)])], "2000-01-01", "map x", "map y", line=True)
        self.assertIn("-9", svg)

    def test_full_48_combinations_and_xml(self):
        rows = []
        for s in m.SCENARIOS:
            for p in m.PLANNERS:
                for mode in ("SimpleTracking", "PNG"):
                    for torpedo in ("청상어", "백상어", "Mk48"):
                        rows.append(self.row(f"test-only-{len(rows)}", p, scenario=s, mode=mode, torpedo=torpedo, speed_ratio=2))
        self.inputs(rows, ["speed_ratio"])
        summary = self.build()
        self.assertEqual(summary["valid_runs"], 48)
        self.assertTrue(summary["complete_matrix"])
        for path in self.output.glob("*.svg"):
            ET.fromstring(path.read_text(encoding="utf-8"))
        page = self.page.read_text(encoding="utf-8")
        self.assertEqual(page.count("<figure"), 3)
        self.assertEqual(page.count("<table"), 1)
        self.assertNotIn("representative only", page)

    def test_plan_p95_uses_individual_records(self):
        self.inputs([self.row(plan_count=2, plan_ms_mean=5,plan_ms_median=5,plan_ms_max=9)])
        self.csv("plans.csv", m.PLAN_COLS, [dict(zip(m.PLAN_COLS,["test-only-a",t,"astar",ms,2,2,0])) for t,ms in ((1,1),(2,9))])
        summary = self.build()
        self.assertEqual(summary["plan_ms_median"], 5)
        self.assertAlmostEqual(summary["plan_ms_p95"], 8.6)

    def test_crlf_outside_block_preserved(self):
        self.inputs([self.row()])
        original = self.original.replace("\n", "\r\n").encode("utf-8")
        self.page.write_bytes(original)
        self.build()
        after = self.page.read_bytes()
        start, end = m.START.encode(), m.END.encode()
        self.assertEqual(after.split(start)[0], original.split(start)[0])
        self.assertEqual(after.split(end)[1], original.split(end)[1])


if __name__ == "__main__":
    unittest.main()
