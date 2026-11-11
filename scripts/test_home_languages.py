"""Ensure the Korean and English pages keep the same evidence and working links."""
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit

DIST = Path(__file__).resolve().parents[1] / 'dist'
SITE = 'https://neberrein.github.io'
PROJECTS = ['sensor-fusion.html', 'roboracer.html', 'imu-lstm-fsm.html', 'argus-drone.html',
            'stm32-tracking.html', 'manta.html', 'mosaic-c2.html', 'davinci-autonomous.html',
            'rgb-classification.html', 'crosswalk-gap.html']
HANGUL = re.compile('[가-힣]')
# The Korean share images for these pages show Korean text, so English pages use English cards.
ENGLISH_SHARE_IMAGES = {
    'argus-drone.html': 'argus-drone-en.png',
    'davinci-autonomous.html': 'davinci-autonomous-en.png',
    'crosswalk-gap.html': 'crosswalk-gap-en.png',
    'rgb-classification.html': 'rgb-classification-en.png',
}


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.tags = []
        self.text = []
        self.skip = 0
        self.source = path.read_text(encoding='utf-8')
        self.feed(self.source)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag in ('script', 'style'):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.text.append(data)

    def refs(self):
        for tag, attrs in self.tags:
            for key in ('href', 'src', 'poster'):
                if attrs.get(key) and tag in ('a', 'link', 'img', 'script', 'source', 'video', 'track', 'image'):
                    yield attrs[key]
            if attrs.get('srcset'):
                for item in attrs['srcset'].split(','):
                    yield item.split()[0]

    def meta(self, key):
        return [a.get('content') for tag, a in self.tags if tag == 'meta' and (a.get('property') or a.get('name')) == key]


def detail_pages():
    for name in PROJECTS:
        yield 'ko', DIST / 'projects' / name, f'{SITE}/projects/{name}'
        yield 'en', DIST / 'en/projects' / name, f'{SITE}/en/projects/{name}'


class HomeLanguagesTests(unittest.TestCase):
    def assert_refs_exist(self, page):
        for ref in page.refs():
            if urlsplit(ref).scheme or ref.startswith('//'):
                continue
            parts = urlsplit(ref)
            target = (page.path.parent / unquote(parts.path)).resolve() if parts.path else page.path
            if target.is_dir():
                target /= 'index.html'
            self.assertTrue(target.is_file(), f'{page.path.relative_to(DIST)}: {ref}')
            if parts.fragment and target.suffix == '.html':
                self.assertIn(f'id="{parts.fragment}"', target.read_text(encoding='utf-8'), ref)

    def test_local_links_assets_and_fragments_exist(self):
        for path in [DIST / 'index.html', DIST / 'en/index.html'] + [p for _, p, _ in detail_pages()]:
            self.assert_refs_exist(Page(path))

    def test_language_metadata_and_reciprocal_controls(self):
        pages = [('ko', DIST / 'index.html', f'{SITE}/'), ('en', DIST / 'en/index.html', f'{SITE}/en/')]
        for lang, path, canonical in pages + list(detail_pages()):
            page = Page(path)
            self.assertIn(('html', {'lang': lang}), page.tags)
            self.assertIn(('link', {'rel': 'canonical', 'href': canonical}), page.tags)
            self.assertEqual(page.meta('og:url'), [canonical], path)
            self.assertEqual(page.meta('og:locale'), ['ko_KR' if lang == 'ko' else 'en_US'], path)
            alternate = {a['hreflang']: a['href'] for tag, a in page.tags if tag == 'link' and a.get('rel') == 'alternate'}
            korean = canonical.replace('/en/', '/')
            self.assertEqual(alternate, {'ko': korean, 'en': korean.replace(SITE + '/', SITE + '/en/'), 'x-default': korean}, path)
            controls = [a for tag, a in page.tags if tag == 'a' and 'data-language-link' in a]
            self.assertEqual({a['hreflang'] for a in controls}, {'ko', 'en'})
            self.assertEqual([a['hreflang'] for a in controls if a.get('aria-current') == 'page'], [lang])
            for control in controls:
                target = (path.parent / control['href']).resolve()
                if target.is_dir():
                    target /= 'index.html'
                self.assertTrue(target.is_file(), control['href'])

    def test_detail_pages_mirror_structure_and_indexing(self):
        for name in PROJECTS:
            ko, en = Page(DIST / 'projects' / name), Page(DIST / 'en/projects' / name)
            self.assertEqual(ko.meta('robots'), en.meta('robots'), name)
            for page in (ko, en):
                image = page.meta('og:image')
                self.assertEqual(len(image), 1, name)
                self.assertTrue((DIST / image[0].removeprefix(SITE + '/')).is_file(), image[0])
            if name in ENGLISH_SHARE_IMAGES:
                self.assertEqual(en.meta('og:image'), [f'{SITE}/assets/og/{ENGLISH_SHARE_IMAGES[name]}'], name)
            else:
                self.assertEqual(ko.meta('og:image'), en.meta('og:image'), name)
            ids = lambda page: [a['id'] for tag, a in page.tags if 'id' in a and tag == 'section']
            self.assertEqual(ids(ko), ids(en), name)
            self.assertEqual(en.source.count('<section'), ko.source.count('<section'), name)
            title = re.search(r'<title>(.*?)</title>', en.source)[1]
            self.assertTrue(title.endswith('| Minjae Kwak'), title)
            body = en.source.split('<main', 1)[1].split('</main>', 1)[0]
            self.assertNotIn('../../projects/', body, name)
            self.assertNotIn('../projects/', body.replace('../../assets/', ''), name)

    def test_english_text_and_labels_are_english(self):
        pages = [DIST / 'en/index.html'] + [DIST / 'en/projects' / name for name in PROJECTS]
        for path in pages:
            page = Page(path)
            visible = ''.join(page.text)
            self.assertIsNone(HANGUL.search(visible), f'{path.name}: {HANGUL.search(visible) and visible[max(0, HANGUL.search(visible).start()-40):HANGUL.search(visible).start()+40]}')
            for tag, attrs in page.tags:
                for key in ('alt', 'aria-label', 'content', 'label', 'placeholder'):
                    value = attrs.get(key) or ''
                    if HANGUL.search(value) and value != '한국어':
                        self.fail(f'{path.name}: {tag} {key}={value[:60]}')
            for ref in page.refs():
                if ref.endswith('.svg') or '.svg?' in ref:
                    svg = (path.parent / urlsplit(ref).path).resolve()
                    if svg.name != 'favicon.svg':
                        self.assertIsNone(HANGUL.search(svg.read_text(encoding='utf-8')), f'{path.name}: {svg.name}')

    def test_english_keeps_project_destinations_and_key_evidence(self):
        ko = Page(DIST / 'index.html')
        en = Page(DIST / 'en/index.html')
        def projects(page):
            return [urlsplit(a['href']).path for tag, a in page.tags if tag == 'a' and a.get('class') in ('selected-case', 'project-row')]
        self.assertEqual(projects(ko), projects(en))
        self.assertEqual(projects(en), [f'projects/{name}' for name in PROJECTS])
        english = (DIST / 'en/index.html').read_text(encoding='utf-8')
        for value in ('20.6%', '99.50%', '44%', '99.91%', '21,054', '10-2025-0136289'):
            self.assertIn(value, english)
        self.assertNotIn('currently in Korean', english)
        self.assertNotIn('(Korean)"', english)

    def test_language_switch_keeps_section_and_realigns(self):
        script = (DIST / 'assets/site.js').read_text(encoding='utf-8')
        self.assertIn('destination.hash = window.location.hash;', script)
        self.assertIn('if (window.location.hash) keepHashTarget(true);', script)
        self.assertIn("window.addEventListener('hashchange', () => keepHashTarget());", script)
        for name in PROJECTS:
            ko = re.findall(r'<section\b[^>]*\bid="([^"]+)"', (DIST / 'projects' / name).read_text(encoding='utf-8'))
            en = re.findall(r'<section\b[^>]*\bid="([^"]+)"', (DIST / 'en/projects' / name).read_text(encoding='utf-8'))
            self.assertEqual(ko, en, name)

    def test_detail_pages_keep_confirmed_facts(self):
        facts = {
            'sensor-fusion.html': ('20.6%', 'Python', 'MATLAB', '0.126 m', '0.100 m'),
            'roboracer.html': ('56', '16'),
            'imu-lstm-fsm.html': ('99.50%',),
            'argus-drone.html': ('8.7%', '0%', '44%', 'Hailo-8'),
            'manta.html': ('A*', 'DVO', '24', 'PN'),
            'rgb-classification.html': ('99.91%', '2,106'),
            'crosswalk-gap.html': ('15.33 m', '16.16 m', '3.27 s', '3.93 s', '916', '675', '241'),
            'mosaic-c2.html': ('2026.07.17–2026.07.24',),
        }
        for name, values in facts.items():
            page = (DIST / 'en/projects' / name).read_text(encoding='utf-8')
            for value in values:
                self.assertIn(value, page, f'{name}: {value}')
        imu = (DIST / 'en/projects/imu-lstm-fsm.html').read_text(encoding='utf-8')
        self.assertNotIn('99.52', imu)
        argus = (DIST / 'en/projects/argus-drone.html').read_text(encoding='utf-8')
        self.assertIn('<meta name="robots" content="noindex,follow">', argus)
        self.assertIn('data-project-status="ongoing"', argus)
        self.assertNotIn('separate demo', argus.lower())


if __name__ == '__main__':
    unittest.main()
