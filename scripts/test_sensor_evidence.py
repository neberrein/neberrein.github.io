"""Guard scenario grouping, original image dimensions and requested cleanup."""
import re
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SensorEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.page = (ROOT / 'dist/projects/sensor-fusion.html').read_text(encoding='utf-8')
        self.sim = self.page.split('04 / SIMULATION')[1].split('05 / FIELD TEST')[0]
        self.field = self.page.split('05 / FIELD TEST')[1].split('06 / OCCLUSION')[0]
        self.occlusion = self.page.split('06 / OCCLUSION')[1].split('07 / RESULT')[0]

    def test_scenarios_are_visible_and_separate(self):
        self.assertNotIn('<details', self.sim)
        self.assertNotIn('추가 시뮬레이션 결과 보기', self.sim)
        turn, straight = self.sim.split('직진 결과 — 단일차량')
        self.assertEqual(turn.count('sensor-sim-turn-state.png'), 1)
        self.assertNotIn('sensor-sim-straight-state.png', turn)
        self.assertEqual(straight.count('sensor-sim-straight-state.png'), 1)
        self.assertNotIn('sensor-sim-turn-state.png', straight)

    def test_image_dimensions_match_png(self):
        for name in ('sensor-simulation-environment-hires.png', 'sensor-sim-turn-state.png',
                     'sensor-sim-straight-state.png', 'sensor-occlusion-result-marked.png'):
            tag = re.search(r'<img\b[^>]*src="\.\./assets/images/' + re.escape(name) + r'[^>]*>', self.page)[0]
            width, height = struct.unpack('>II', (ROOT / 'dist/assets/images' / name).read_bytes()[16:24])
            self.assertIn(f'width="{width}"', tag)
            self.assertIn(f'height="{height}"', tag)

    def test_removed_notes_and_field_row(self):
        self.assertNotIn('Table 1', self.sim)
        self.assertNotIn('연속 다중차량 좌회전', self.field)
        self.assertNotIn('0.147 m', self.field)
        self.assertNotIn('원본 보기', self.sim + self.occlusion)
        self.assertIn('단일차량 좌회전', self.sim)
        self.assertIn('다중차량 좌회전', self.sim)

    def test_marked_occlusion_and_result_unchanged(self):
        self.assertIn('빨간 원: 가림 발생 구간', self.occlusion)
        self.assertNotIn('Fig. 13', self.occlusion)
        self.assertEqual(self.occlusion.count('class="research-figure occlusion-step"'), 3)
        for value in ('20.6%', '0.126 m', '0.100 m', '0.043 m', '0.030 m', '30.2%'):
            self.assertIn(value, self.page.split('07 / RESULT')[1].split('08 / OWNERSHIP')[0])


if __name__ == '__main__':
    unittest.main()
