"""Guard the published ARGUS project page."""
import unittest
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
                     'AI-powered Real-time Ground Object UAV Surveillance', '측정 예정', '검증 예정'):
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


if __name__ == '__main__':
    unittest.main()
