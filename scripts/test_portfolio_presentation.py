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
