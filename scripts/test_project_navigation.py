"""Navigation integrity, fail-before-write, and protected-content tests."""
import contextlib
import io
import re
import tempfile
import unittest
from pathlib import Path
import update_project_navigation as nav

GENERATED = {'primary-nav', 'next-project', 'project-pagination', 'language-switch'}


def protected_content(page):
    page = nav.NAV.sub(lambda m: '' if nav.classes(m[0]) & GENERATED else m[0], page)
    page = re.sub(r'\s*<link rel="stylesheet" href="(?:\.\./)+assets/project-languages\.css[^"]*">', '', page)
    page = re.sub(r'(?<=src=")((?:\.\./)+assets/site\.js)(?:\?[^"\s]*)?(?=")', r'\1', page)
    return re.sub(r'(?<=href=")((?:\.\./)+assets/site\.css)(?:\?[^"\s]*)?(?=")', r'\1', page)


class NavigationTests(unittest.TestCase):
    def setUp(self):
        self.dist = nav.ROOT / 'dist'
        self.orders = nav.read_orders(self.dist)
        self.projects = self.orders['ko']

    def page(self, lang, filename):
        return (self.dist / nav.LANGUAGES[lang]['pages'] / filename).read_bytes().decode('utf-8')

    def test_current_pages_match_main_order(self):
        for lang, projects in self.orders.items():
            self.assertEqual(len(projects), 10)
            self.assertNotIn('davinci-vision.html', [p[0] for p in projects])
            for i, (filename, _) in enumerate(projects):
                page = self.page(lang, filename)
                self.assertEqual(page, nav.update_page(page, projects, i, lang), (lang, filename))
                matches = [m[0] for m in nav.NAV.finditer(page) if 'project-pagination' in nav.classes(m[0])]
                self.assertEqual(len(matches), 1)
                block = matches[0]
                self.assertNotIn('next-project', page)
                self.assertNotIn('target=', block)
                self.assertEqual(block.count('href="../index.html#projects"'), 1)
                if i:
                    self.assertIn(f'href="{projects[i-1][0]}" rel="prev"', block)
                else:
                    self.assertNotIn('rel="prev"', block)
                if i < len(projects)-1:
                    self.assertIn(f'href="{projects[i+1][0]}" rel="next"', block)
                else:
                    self.assertNotIn('rel="next"', block)
                self.assertNotIn(f'href="{filename}"', block)

    def test_pagination_uses_page_language(self):
        for i in range(len(self.projects)):
            ko = nav.pagination(self.orders['ko'], i, 'ko')
            en = nav.pagination(self.orders['en'], i, 'en')
            self.assertIsNone(re.search('[가-힣]', en))
            self.assertIn('전체 프로젝트', ko)
            self.assertIn('All projects', en)
            self.assertIn('aria-label="Project navigation"', en)

    def test_language_switch_links_to_same_project(self):
        for filename, _ in self.projects:
            for lang, other in (('ko', 'en'), ('en', 'ko')):
                page = self.page(lang, filename)
                header = re.search(r'<header\b.*?</header>', page, re.S)[0]
                switch = [m[0] for m in nav.NAV.finditer(header) if 'language-switch' in nav.classes(m[0])]
                self.assertEqual(len(switch), 1, (lang, filename))
                links = dict(re.findall(r'<a href="([^"]+)" hreflang="(ko|en)"', switch[0]))
                links = {code: href for href, code in links.items()}
                self.assertEqual(set(links), {'ko', 'en'})
                base = self.dist / nav.LANGUAGES[lang]['pages']
                self.assertEqual((base / links[lang]).resolve(), (base / filename).resolve())
                target = (base / links[other]).resolve()
                self.assertEqual(target, (self.dist / nav.LANGUAGES[other]['pages'] / filename).resolve())
                self.assertTrue(target.is_file())
                self.assertEqual(re.findall(r'hreflang="(ko|en)"[^>]*aria-current="page"', switch[0]), [lang])
                self.assertIn('data-language-link', switch[0])

    def test_english_header_and_links_stay_english(self):
        for filename, _ in self.orders['en']:
            page = self.page('en', filename)
            header = re.search(r'<header\b.*?</header>', page, re.S)[0]
            self.assertIn('<a class="brand" href="../index.html">', header)
            self.assertIn('<a href="../index.html#projects">Projects</a><a href="../index.html#research">Research</a>', header)
            self.assertIn('<a class="back-link" href="../index.html#projects">← All projects</a>', page)
            pager = [m[0] for m in nav.NAV.finditer(page) if 'project-pagination' in nav.classes(m[0])][0]
            self.assertNotIn('../../projects/', pager)

    def test_old_navigation_conversion_preserves_other_bytes(self):
        for lang, projects in self.orders.items():
            for i, (filename, _) in enumerate(projects):
                current = self.page(lang, filename)
                old = nav.NAV.sub(lambda m: '<nav class="next-project"><a href="manta.html">OLD</a></nav>' if 'project-pagination' in nav.classes(m[0])
                                  else '' if 'language-switch' in nav.classes(m[0]) else m[0], current)
                old = old.replace('>연구성과</a>', '>논문, 특허</a>').replace(nav.CSS_VERSION, 'OLD-VERSION')
                old = re.sub(r'\s*<link rel="stylesheet" href="(?:\.\./)+assets/project-languages\.css[^"]*">', '', old)
                old = old.replace(f'site.js?v={nav.SCRIPT_VERSION}', 'site.js')
                updated = nav.update_page(old, projects, i, lang)
                self.assertEqual(protected_content(old), protected_content(updated))
                self.assertEqual(updated, nav.update_page(updated, projects, i, lang))
                self.assertEqual(protected_content(updated), protected_content(current), (lang, filename))

    def test_order_comes_only_from_formal_main_links(self):
        index = '<a class="project-row" href="projects/manta.html">OUTSIDE</a><section id="projects"><a class="project-row" href="projects/rgb-classification.html">RGB</a><a href="projects/sensor-fusion.html">RELATED</a><a class="selected-case" href="projects/manta.html">MANTA</a></section>'
        self.assertEqual([p[0] for p in nav.read_order(index)], ['rgb-classification.html', 'manta.html'])
        self.assertIn('href="manta.html" rel="next"', nav.pagination(nav.read_order(index), 0))

    def test_invalid_order_fails(self):
        for hrefs in (['manta.html','manta.html'], ['davinci-vision.html'], ['../manta.html']):
            index = '<section id="projects">'+''.join(f'<a class="project-row" href="projects/{h}"></a>' for h in hrefs)+'</section>'
            with self.assertRaises(ValueError):
                nav.read_order(index)
        # English links that point back to Korean detail pages are rejected.
        with self.assertRaises(ValueError):
            nav.read_order('<section id="projects"><a class="project-row" href="../projects/manta.html"></a></section>', 'en')

    def test_language_orders_must_match(self):
        with tempfile.TemporaryDirectory(prefix='project-navigation-') as folder:
            folder = Path(folder)
            (folder / 'en').mkdir()
            (folder / 'index.html').write_bytes((self.dist / 'index.html').read_bytes())
            english = (self.dist / 'en/index.html').read_text(encoding='utf-8')
            swapped = english.replace('projects/manta.html', 'projects/TMP.html').replace('projects/mosaic-c2.html', 'projects/manta.html').replace('projects/TMP.html', 'projects/mosaic-c2.html')
            (folder / 'en/index.html').write_text(swapped, encoding='utf-8')
            with self.assertRaises(ValueError):
                nav.read_orders(folder)

    def test_duplicate_navigation_fails(self):
        page = self.page('ko', 'manta.html')
        with self.assertRaises(ValueError):
            nav.update_page(page.replace('</main>', nav.pagination(self.projects, 5)+'</main>'), self.projects, 5)
        with self.assertRaises(ValueError):
            nav.update_page(page.replace('</header>', nav.language_switch('manta.html')+'</header>'), self.projects, 5)

    def test_check_mode_does_not_write_and_all_pages_validate_first(self):
        with tempfile.TemporaryDirectory(prefix='project-navigation-') as folder:
            folder = Path(folder)
            originals = {}
            for lang, text in nav.LANGUAGES.items():
                (folder / text['pages']).mkdir(parents=True)
                (folder / text['index']).write_bytes((self.dist / text['index']).read_bytes())
                for filename, _ in self.orders[lang]:
                    original = (self.dist / text['pages'] / filename).read_bytes().replace(nav.CSS_VERSION.encode(), b'OLD')
                    originals[(lang, filename)] = original
                    (folder / text['pages'] / filename).write_bytes(original)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertFalse(nav.build(folder, check=True))
            self.assertTrue(all((folder / nav.LANGUAGES[l]['pages'] / n).read_bytes() == b for (l, n), b in originals.items()))
            # A broken last English page must not allow earlier pages to be updated.
            last = folder / 'en/projects' / self.projects[-1][0]
            last.write_bytes(b'BROKEN PAGE')
            with self.assertRaises(ValueError):
                nav.build(folder)
            self.assertEqual((folder / 'projects' / self.projects[0][0]).read_bytes(), originals[('ko', self.projects[0][0])])

    def test_final_results_block_stays_exactly_unchanged(self):
        pattern = r'<!-- MANTA_RESULTS_AUTO_START -->.*?<!-- MANTA_RESULTS_AUTO_END -->'
        for lang in nav.LANGUAGES:
            page = self.page(lang, 'manta.html')
            position = [p[0] for p in self.orders[lang]].index('manta.html')
            updated = nav.update_page(page.replace(nav.CSS_VERSION, 'OLD'), self.orders[lang], position, lang)
            original_block = re.search(pattern, page, re.S)
            if original_block:
                self.assertEqual(original_block[0], re.search(pattern, updated, re.S)[0])


if __name__ == '__main__':
    unittest.main()
