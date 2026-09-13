# MANTA measured datasets — public page follows the final DVO-only instruction

Raw CSVs, baseline/pilot exports and per-run audit reports are local ignored
inputs, not uploaded to the public repository. Only derived summaries,
native SVG evidence, source hashes and the labelled implementation video
are deployed. When raw CSVs are absent in CI, generation is a no-op and the
checked-in results are preserved. Recompute and verify locally before publishing.

`latest/` is the complete final DVO/Hybrid export: 48 runs, 24 matched conditions.
Its six root CSVs are audited as the complete supplied archive, then DVO is
filtered by run_id. The public page omits Hybrid at the user's final request.
The initial
`baseline_original/` export predates shared path/controller fixes; `pilot/`
exports are excluded. Do not recursively concatenate datasets or `by_planner`
copies. HIT is a valid measured outcome, not an invalid run.

The latest provenance records four v2 DVO runs reused after verification that
standalone DVO/path-control logic and experiment conditions were unchanged.
The native bags were verified in the supplied upstream experiment audit;
they are not included here. Fourteen ROS/C++ Debug regressions passed in the
supplied execution log, separate from the Python website-generator tests.

Run `python scripts/test_manta_results.py`,
`python scripts/test_manta_hybrid.py`,
`python scripts/test_manta_dvo.py`, then
`python scripts/build_manta_results.py`. Only the marked RESULTS block is
regenerated. All published charts are native SVG; trajectories use measured
kinematics samples, equal XY axes, and a disclosed closest-approach window.

The final implementation's audited v3 `latest/` export is the designated
public result batch: all 24 DVO conditions, 15/24 AVOIDED. Its public table
groups by approach direction and guidance mode (SimpleTracking 11/12, PNG
4/12). One optional measured trajectory is selected in configured condition
order, not by highest clearance. The final-batch version, selected run IDs
and input/archive hashes are recorded in summary.json and generated-manifest.json.

The initial DVO batch has 14/24 AVOIDED; latest DVO has 15/24. The identical
24-condition historical comparison and higher-rate selection utility are
preserved for development history, but do not automatically choose the
published implementation version. Never choose the better run per condition.
Three conditions changed to
AVOIDED and two to HIT; the +1 net change is not statistical significance or
an isolated DVO algorithm effect because shared path/control also changed.
The public summary and figures contain DVO only. Before/after and scenario
chart assets remain archived, not main-page evidence. Full-archive and historical
exports remain provenance, not three-way performance claims. Public copy does
not list private source paths, file hashes or run-reuse audit details.

Future refreshes require the complete six-CSV final export and refreshed
`provenance.json` and integrity/audit reports. Inconsistent hashes, duplicate
conditions, incomplete coverage or invalid runs abort before touching the
page. No logs is a no-op. Do not retain an old audit as proof for a new batch.
The old A*/DVO generator remains available for explicit historical inputs;
never use its baseline statistics as a latest same-code A* control group.

For a supplied complete archive, use
`python scripts/import_manta_archive.py --latest PATH_TO_FINAL_ZIP --baseline PATH_TO_ORIGINAL_ZIP`.
The importer CRC-checks explicit ZIP entries, verifies row counts and reports,
copies the raw CSV bytes, and strips private host paths from local audit
metadata. `--retain-pilots` keeps ignored local pilot copies separately.
