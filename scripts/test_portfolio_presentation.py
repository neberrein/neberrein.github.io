"""Social-card and presentation checks without third-party dependencies."""
import re
import struct
import unittest
from html.parser import HTMLParser
from pathlib import Path

DIST = Path(__file__).resolve().parents[1] / 'dist'


class MetaTags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta':
            key = attrs.get('property') or attrs.get('name')
            self.tags.setdefault(key, []).append(attrs.get('content'))


def jpeg_size(data):
    if data[:2] != b'\xff\xd8':
        raise ValueError('Not JPEG')
    offset = 2
    while offset < len(data):
        if data[offset] != 255:
            raise ValueError('Invalid JPEG segment')
        marker = data[offset + 1]
        length = struct.unpack('>H', data[offset + 2:offset + 4])[0]
        if marker in (0xc0, 0xc1, 0xc2):
            height, width = struct.unpack('>HH', data[offset + 5:offset + 9])
            return width, height
        offset += 2 + length
    raise ValueError('JPEG dimensions not found')


class PresentationTests(unittest.TestCase):
    def test_social_metadata_unique_and_consistent(self):
        parser = MetaTags()
        parser.feed((DIST / 'index.html').read_text(encoding='utf-8'))
        for key in ('og:type', 'og:title', 'og:description', 'og:url', 'og:image',
                    'og:image:width', 'og:image:height', 'twitter:card',
                    'twitter:title', 'twitter:description', 'twitter:image'):
            self.assertEqual(len(parser.tags.get(key, [])), 1, key)
        self.assertEqual(parser.tags['og:image'], ['https://neberrein.github.io/assets/og/profile-share.jpg'])
        for key in ('title', 'description', 'image'):
            self.assertEqual(parser.tags['og:' + key], parser.tags['twitter:' + key])
        self.assertEqual(parser.tags['og:url'], ['https://neberrein.github.io/'])
        self.assertEqual(parser.tags['twitter:card'], ['summary_large_image'])
        self.assertEqual(parser.tags['og:image:width'], ['1200'])
        self.assertEqual(parser.tags['og:image:height'], ['630'])

    def test_share_image_is_landscape_jpeg(self):
        self.assertEqual(jpeg_size((DIST / 'assets/og/profile-share.jpg').read_bytes()), (1200, 630))

    def test_main_section_indices_remain_ordered(self):
        page = (DIST / 'index.html').read_text(encoding='utf-8')
        labels = re.findall(r'<header class="editorial-heading[^\"]*"><span>(\d+)</span>', page)
        self.assertEqual(labels, ['01', '02', '03', '04', '05'])
        css = (DIST / 'assets/site.css').read_text(encoding='utf-8')
        self.assertIn('.portfolio-home .editorial-heading>span { font-size:2rem;', css)
        self.assertIn('.portfolio-home .editorial-heading>span { font-size:2.5rem;', css)

    def test_imu_disclaimer_removed(self):
        page = (DIST / 'projects/imu-lstm-fsm.html').read_text(encoding='utf-8')
        self.assertNotIn('분류 모듈 자체의 위치오차나 모든 시점의 최대 오차', page)

    def test_stm32_hardware_labels_and_readable_actual_log(self):
        page = (DIST / 'projects/stm32-tracking.html').read_text(encoding='utf-8')
        hero = page.split('stm32-hardware-photo', 1)[1].split('</figure>', 1)[0]
        self.assertIn('stm32-system-overview.jpg', hero)
        for part in ('hardware-board', 'hardware-sensor', 'hardware-servo', 'hardware-led'):
            self.assertIn(part, hero)
        self.assertEqual(hero.count('<circle '), 4)
        self.assertIn('텍스트로 재구성했습니다.', page)
        self.assertIn('[SCAN #25 FORWARD] valid=15/15', page)
        self.assertIn('[COMPARE #26&lt;-24 REVERSE] valid=15 changed=1 approaching=0', page)
        self.assertNotIn('src="../assets/images/stm32-uart-scan-compare.webp"', page)

    def test_manta_annotated_and_cropped_media(self):
        page = (DIST / 'projects/manta.html').read_text(encoding='utf-8')
        for name in ('manta-gazebo-motion-annotated.mp4', 'manta-rviz-path-only.mp4'):
            self.assertIn(name, page)
            data = (DIST / 'assets/videos' / name).read_bytes()
            self.assertEqual(data[4:8], b'ftyp')
            self.assertGreater(len(data), 100000)
        for name, size in (('manta-gazebo-motion-preview.jpg', (1280, 720)),
                           ('manta-rviz-path-preview.jpg', (718, 574))):
            self.assertIn(name, page)
            self.assertEqual(jpeg_size((DIST / 'assets/images' / name).read_bytes()), size)
        for video in re.findall(r'<video\b[^>]*>', page):
            self.assertIn('controls muted playsinline preload="metadata"', video)
            self.assertNotIn('autoplay', video)
        self.assertIn('화면상 이동 방향', page)
        self.assertIn('aspect-ratio:718/574', (DIST / 'assets/manta-evidence.css').read_text())

    def test_stm32_prose_uses_consistent_endings(self):
        page = (DIST / 'projects/stm32-tracking.html').read_text(encoding='utf-8')
        paragraphs = re.findall(r'<p(?:\s[^>]*)?>(.*?)</p>', page, re.S)
        for paragraph in paragraphs:
            text = re.sub('<[^>]+>', '', paragraph).strip()
            if text != 'EMBEDDED SOFTWARE, REAL-TIME SYSTEM':
                self.assertRegex(text, r'습니다\.$')
        self.assertNotRegex(page, r'목표였다\.|계산했다\.|확정했다\.|반영했다\.')


if __name__ == '__main__':
    unittest.main()
