"""Guard the published ARGUS project page."""
import unittest
import xml.etree.ElementTree as ET
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
PAGE = DIST / 'projects' / 'argus-drone.html'


class ArgusPageTests(unittest.TestCase):
    def test_page_is_linked_but_search_indexing_is_deferred(self):
        page = PAGE.read_text(encoding='utf-8')
        home = (DIST / 'index.html').read_text(encoding='utf-8')
        self.assertIn('<meta name="robots" content="noindex,follow">', page)
        self.assertIn('data-project-status="ongoing"', page)
        self.assertIn('argus-draft-badge">진행 중</span>', page)
        self.assertIn('projects/argus-drone.html', home)
        self.assertIn('rel="canonical"', page)
        self.assertIn('og:url', page)
        self.assertIn('argus-og.png', page)

    def test_draft_describes_plan_without_claiming_results(self):
        page = PAGE.read_text(encoding='utf-8')
        for text in ('ARGUS 6인 팀', '팀장', 'YOLOX 학습', 'Hailo NPU',
                     'AI-powered Real-time Ground Object UAV Surveillance', '검증 계획', '검증할 계획입니다'):
            self.assertIn(text, page)
        for unsupported in ('실기체 검증을 완료', '탐지 정확도 달성', 'FPS를 달성', '자율 추종에 성공'):
            self.assertNotIn(unsupported, page)

    def test_required_evidence_assets_exist(self):
        page = PAGE.read_text(encoding='utf-8')
        for name in ('argus-system-architecture.svg', 'argus-system-architecture-mobile.svg',
                     'argus-software-pipeline.svg', 'argus-software-pipeline-mobile.svg',
                     'argus-loss-response.svg', 'argus-loss-response-mobile.svg'):
            self.assertIn(name, page)
            path = DIST / 'assets' / 'images' / name
            self.assertTrue(path.is_file(), name)
        self.assertNotIn('DX-M1', page)
        self.assertNotIn('DeepX', page)
        self.assertNotIn('·', page)
        self.assertNotIn('06 / OWNERSHIP', page)
        self.assertNotIn('argus-loss-response.png', page)
        for name in ('argus-system-architecture.svg', 'argus-system-architecture-mobile.svg',
                     'argus-software-pipeline.svg', 'argus-software-pipeline-mobile.svg'):
            source = (DIST / 'assets' / 'images' / name).read_text(encoding='utf-8')
            self.assertIn('Hailo NPU', source)
            self.assertNotIn('DX-M1', source)

    def test_diagrams_have_explicit_direction_and_valid_dimensions(self):
        for path in (DIST / 'assets' / 'images').glob('argus-*.svg'):
            root = ET.parse(path).getroot()
            self.assertEqual(list(map(float, root.get('viewBox').split()))[2:],
                             [float(root.get('width')), float(root.get('height'))])
            self.assertNotIn('·', path.read_text(encoding='utf-8'))
            for elem in root.iter('{http://www.w3.org/2000/svg}path'):
                if elem.get('marker-end'):
                    self.assertEqual(elem.get('d').count('M'), 1, path.name)

    def test_pipeline_does_not_bypass_inference(self):
        source = (DIST / 'assets/images/argus-software-pipeline.svg').read_text(encoding='utf-8')
        self.assertIn('M345 210H370', source)  # Preprocessing -> NPU.
        self.assertIn('M510 210H535', source)  # NPU -> postprocessing.
        self.assertNotIn('M345 210H535', source)

    def test_manual_override_is_separate_from_target_loss(self):
        for name in ('argus-loss-response.svg', 'argus-loss-response-mobile.svg'):
            text = ''.join(ET.parse(DIST / 'assets/images' / name).getroot().itertext())
            self.assertIn('수동', text)
            self.assertIn('자동 추종 해제', text)
            self.assertNotIn('관측 만료 또는 수동 개입', text)
        self.assertNotIn('argus-safety-summary', PAGE.read_text(encoding='utf-8'))

    def test_single_platform_photo_and_updated_dimensions(self):
        page = PAGE.read_text(encoding='utf-8')
        self.assertEqual(page.count('argus-drone-platform.jpg'), 1)
        self.assertTrue((DIST / 'assets/images/argus-drone-platform.jpg').is_file())
        for name, width, height in re.findall(r'<img src="../assets/images/(argus-[^"?]+\.svg)[^"]*" width="(\d+)" height="(\d+)"', page):
            root = ET.parse(DIST / 'assets/images' / name).getroot()
            self.assertEqual((width, height), (root.get('width'), root.get('height')))


if __name__ == '__main__':
    unittest.main()
