"""Final-batch publication and preserved whole-batch comparison tests."""
import itertools
import json
import tempfile
import unittest
import re
import xml.etree.ElementTree as ET
from pathlib import Path
import build_manta_dvo as d
import build_manta_results as dispatch
import build_manta_explainers as explainers


def fixture(avoided):
    return [dict(run_id=f'FIXTURE_ONLY_{i}',scenario=s,mode=m,torpedo=t,planner='dvo',outcome='AVOIDED' if i in avoided else 'HIT',plan_count='2',engagements='1',closest_m='2' if i in avoided else '.8') for i,(s,m,t) in enumerate(itertools.product(d.SCENARIOS,d.MODES,d.TORPEDOES))]


class DvoPublicationTests(unittest.TestCase):
    def test_public_page_has_four_sections_and_no_repeated_pipeline(self):
        root=Path(__file__).resolve().parents[1]
        page=(root/'dist/projects/manta.html').read_text(encoding='utf-8')
        self.assertEqual(page.count('<section class="case-section'),4)
        for section in ('01 / SYSTEM','02 / APPROACH','03 / IMPLEMENTATION','04 / VALIDATION'):
            self.assertIn(section,page)
        self.assertNotIn('·',page)
        self.assertNotIn('manta-planning-architecture.svg',page)
        self.assertNotIn('dvo-before-after.svg',page)
        self.assertNotIn('manta-metrics',page)
        self.assertLess(page.index('manta-gazebo-avoidance.mp4'),page.index('01 / SYSTEM'))
        self.assertEqual(page.count(' controls muted playsinline preload="metadata"'),2)
        for filename in ('manta-gazebo-avoidance.mp4','manta-rviz-implementation.mp4'):
            self.assertTrue((root/'dist/assets/videos'/filename).is_file())
        self.assertIn('href="stm32-tracking.html"',page)
        self.assertIn('href="mosaic-c2.html"',page)
        for reference in re.findall(r'(?:src|srcset|href|poster)="(\.\./[^"?#]+)',page):
            self.assertTrue((root/'dist/projects'/reference).is_file(),reference)

    def test_planning_panels_share_initial_geometry(self):
        a,b=[],[]
        explainers.planning_panel(a,0,0,'astar')
        explainers.planning_panel(b,0,0,'dvo')
        for geometry in ('M65 315L390 95','cx="390" cy="95"','x="46" y="303"','translate(180 145) rotate(34)'):
            self.assertIn(geometry,'\n'.join(a))
            self.assertIn(geometry,'\n'.join(b))
        # Only the global method connects its planned path to the mission goal.
        self.assertIn('390 95',next(v for v in a if 'C87 248' in v))
        self.assertIn('115 218',next(v for v in b if 'C75 281' in v))

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
            self.assertEqual(manifest['selected_figures'],['dvo-measured-trajectory.svg'])
            self.assertEqual(result['published_batch']['name'],'latest')
            markup=page.read_text(encoding='utf-8')
            self.assertIn('11 / 12',markup)
            self.assertIn('4 / 12',markup)
            self.assertIn('24개 조건 중 15개',markup)
            self.assertNotIn('dvo-before-after',markup)
            self.assertNotIn('manta-metrics',markup)
            self.assertNotIn('kinematics.csv',markup)
            self.assertNotIn('·',markup)
            for n in manifest['selected_figures']:ET.parse(output/n)
            dispatch.build(source,output,page)
            self.assertEqual(built,page.read_bytes())

    def test_conditional_rendering_is_data_driven(self):
        cells={f'{s}|{m}':{'avoided':0,'closest_m_median':.8} for s in d.SCENARIOS for m in d.MODES}
        cells[f'{d.SCENARIOS[0]}|{d.MODES[0]}']['avoided']=2
        summary={'scenario_guidance':cells,'trajectory':{'condition':{'scenario':d.SCENARIOS[0],'mode':d.MODES[0],'torpedo':d.TORPEDOES[0]}},'plan_ms':{'median':1,'p95':2},'plan_count':{'median':3}}
        result=d.results_html(summary,{'dvo-measured-trajectory.svg':'<svg/>'},{'dvo-measured-trajectory-mobile.svg':'<svg/>'},'assets')
        self.assertIn('24개 조건 중 2개',result)
        self.assertIn('2 / 12',result)
        self.assertIn('0 / 12',result)
        self.assertNotIn('15개',result)


if __name__=='__main__':unittest.main()
