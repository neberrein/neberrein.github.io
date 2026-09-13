"""DVO-only publication tests, including whole-batch rather than best-of selection."""
import itertools
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
import build_manta_dvo as d
import build_manta_results as dispatch


def fixture(avoided):
    return [dict(run_id=f'FIXTURE_ONLY_{i}',scenario=s,mode=m,torpedo=t,planner='dvo',outcome='AVOIDED' if i in avoided else 'HIT',plan_count='2',engagements='1',closest_m='2' if i in avoided else '.8') for i,(s,m,t) in enumerate(itertools.product(d.SCENARIOS,d.MODES,d.TORPEDOES))]


class DvoPublicationTests(unittest.TestCase):
    def test_select_latest_whole_batch(self):
        groups,info=d.compare_batches(fixture(set(range(14))),fixture(set(range(15))))
        self.assertEqual(info['selected_batch'],'latest')
        self.assertEqual(len(groups[info['selected_batch']]),24)
        self.assertEqual(info['latest']['avoided'],15)

    def test_select_initial_when_higher(self):
        self.assertEqual(d.compare_batches(fixture(set(range(16))),fixture(set(range(15))))[1]['selected_batch'],'initial')

    def test_latest_wins_ties(self):
        self.assertEqual(d.compare_batches(fixture(set(range(15))),fixture(set(range(15))))[1]['selected_batch'],'latest')

    def test_never_per_case_best_of(self):
        a=fixture(set(range(14)))
        b=fixture(set(range(9,24)))
        groups,info=d.compare_batches(a,b)
        self.assertEqual(info['latest']['avoided'],15)
        self.assertEqual(sum(r['outcome']=='AVOIDED' for r in groups[info['selected_batch']].values()),15)
        self.assertNotEqual(info['latest']['avoided'],24)

    def test_missing_condition_abort(self):
        with self.assertRaises(ValueError): d.compare_batches(fixture(set())[:-1],fixture(set()))

    def test_duplicate_condition_abort(self):
        a=fixture(set());a[-1]=dict(a[0])
        with self.assertRaises(ValueError):d.compare_batches(a,fixture(set()))

    def test_other_planner_abort(self):
        a=fixture(set());a[0]['planner']='hybrid'
        with self.assertRaises(ValueError):d.compare_batches(a,fixture(set()))

    def test_invalid_run_abort(self):
        a=fixture(set());a[0]['plan_count']='0'
        with self.assertRaises(ValueError):d.compare_batches(a,fixture(set()))

    def test_actual_batch_and_public_result_integrity(self):
        root=Path(__file__).resolve().parents[1]
        source=root/'portfolio_data/manta/latest'
        if not (source/'runs.csv').exists(): self.skipTest('Actual supplied archive remains local, not published')
        with tempfile.TemporaryDirectory(prefix='manta-public-dvo-test-') as folder:
            folder=Path(folder)
            page=folder/'page.html'
            original='\ufeffUNCHANGED\r\n'+d.START+'\r\nplaceholder\r\n'+d.END+'\r\nUNCHANGED END'
            page.write_bytes(original.encode())
            output=folder/'generated'
            result=dispatch.build(source,output,page)
            self.assertEqual(result['comparison']['initial']['avoided'],14)
            self.assertEqual(result['comparison']['latest']['avoided'],15)
            self.assertEqual(result['comparison']['changed_to_avoided'],3)
            self.assertEqual(result['comparison']['changed_to_hit'],2)
            self.assertEqual(result['valid_runs'],24)
            self.assertTrue(all('_dvo_' in rid for rid in result['selected_run_ids']))
            self.assertNotIn('hybrid',page.read_text(encoding='utf-8').lower())
            self.assertNotIn('hybrid',(output/'summary.json').read_text(encoding='utf-8').lower())
            built=page.read_bytes()
            self.assertEqual(built.split(d.START.encode())[0],original.encode().split(d.START.encode())[0])
            self.assertEqual(built.split(d.END.encode())[1],original.encode().split(d.END.encode())[1])
            manifest=json.loads((output/'generated-manifest.json').read_text())
            self.assertEqual(len(manifest['selected_figures']),3)
            for n in manifest['selected_figures']:ET.parse(output/n)
            dispatch.build(source,output,page)
            self.assertEqual(built,page.read_bytes())


if __name__=='__main__':unittest.main()
