"""Navigation integrity, fail-before-write, and protected-content tests."""
import contextlib
import io
import re
import tempfile
import unittest
from pathlib import Path
import update_project_navigation as nav


def protected_content(page):
    page = nav.NAV.sub(lambda m: '' if nav.classes(m[0]) & {'primary-nav', 'next-project', 'project-pagination'} else m[0], page)
    return re.sub(r'(?<=href=")\.\./assets/site\.css(?:\?[^"\s]*)?(?=")', '../assets/site.css', page)


class NavigationTests(unittest.TestCase):
    def setUp(self):
        self.dist = nav.ROOT / 'dist'
        self.projects = nav.read_order((self.dist / 'index.html').read_text(encoding='utf-8'))

    def test_current_pages_match_main_order(self):
        self.assertEqual(len(self.projects), 9)
        self.assertNotIn('davinci-vision.html', [p[0] for p in self.projects])
        for i, (filename, _) in enumerate(self.projects):
            page = (self.dist / 'projects' / filename).read_bytes().decode('utf-8')
            self.assertEqual(page, nav.update_page(page, self.projects, i), filename)
            matches = [m[0] for m in nav.NAV.finditer(page) if 'project-pagination' in nav.classes(m[0])]
            self.assertEqual(len(matches), 1)
            block = matches[0]
            self.assertNotIn('next-project', page)
            self.assertNotIn('target=', block)
            self.assertEqual(block.count('href="../index.html#projects"'), 1)
            if i:
                self.assertIn(f'href="{self.projects[i-1][0]}" rel="prev"', block)
            else:
                self.assertNotIn('rel="prev"', block)
            if i < len(self.projects)-1:
                self.assertIn(f'href="{self.projects[i+1][0]}" rel="next"', block)
            else:
                self.assertNotIn('rel="next"', block)
            self.assertNotIn(f'href="{filename}"', block)

    def test_old_navigation_conversion_preserves_other_bytes(self):
        for i, (filename, _) in enumerate(self.projects):
            current = (self.dist / 'projects' / filename).read_bytes().decode('utf-8')
            old = nav.NAV.sub(lambda m: '<nav class="next-project"><a href="manta.html">OLD</a></nav>' if 'project-pagination' in nav.classes(m[0]) else m[0], current)
            old = old.replace('>연구성과</a>', '>논문, 특허</a>').replace(nav.CSS_VERSION, 'OLD-VERSION')
            updated = nav.update_page(old, self.projects, i)
            self.assertEqual(protected_content(old), protected_content(updated))
            self.assertEqual(updated, nav.update_page(updated, self.projects, i))

    def test_order_comes_only_from_formal_main_links(self):
        index = '<a class="project-row" href="projects/manta.html">OUTSIDE</a><section id="projects"><a class="project-row" href="projects/rgb-classification.html">RGB</a><a href="projects/sensor-fusion.html">RELATED</a><a class="selected-case" href="projects/manta.html">MANTA</a></section>'
        self.assertEqual([p[0] for p in nav.read_order(index)], ['rgb-classification.html', 'manta.html'])
        self.assertIn('href="manta.html" rel="next"', nav.pagination(nav.read_order(index), 0))

    def test_invalid_order_fails(self):
        for hrefs in (['manta.html','manta.html'], ['davinci-vision.html'], ['../manta.html']):
            index = '<section id="projects">'+''.join(f'<a class="project-row" href="projects/{h}"></a>' for h in hrefs)+'</section>'
            with self.assertRaises(ValueError):
                nav.read_order(index)

    def test_duplicate_navigation_fails(self):
        page = (self.dist / 'projects/manta.html').read_text(encoding='utf-8')
        with self.assertRaises(ValueError):
            nav.update_page(page.replace('</main>', nav.pagination(self.projects, 4)+'</main>'), self.projects, 4)

    def test_check_mode_does_not_write_and_all_pages_validate_first(self):
        with tempfile.TemporaryDirectory(prefix='project-navigation-') as folder:
            folder = Path(folder)
            (folder / 'projects').mkdir()
            (folder / 'index.html').write_bytes((self.dist / 'index.html').read_bytes())
            originals = {}
            for filename, _ in self.projects:
                original = (self.dist / 'projects' / filename).read_bytes().replace(nav.CSS_VERSION.encode(), b'OLD')
                originals[filename] = original
                (folder / 'projects' / filename).write_bytes(original)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertFalse(nav.build(folder, check=True))
            self.assertTrue(all((folder / 'projects' / n).read_bytes() == b for n, b in originals.items()))
            # A broken last page must not allow earlier pages to be updated.
            last = folder / 'projects' / self.projects[-1][0]
            last.write_bytes(b'BROKEN PAGE')
            with self.assertRaises(ValueError):
                nav.build(folder)
            self.assertEqual((folder / 'projects' / self.projects[0][0]).read_bytes(), originals[self.projects[0][0]])

    def test_final_results_block_stays_exactly_unchanged(self):
        page = (self.dist / 'projects/manta.html').read_bytes().decode('utf-8')
        updated = nav.update_page(page.replace(nav.CSS_VERSION, 'OLD'), self.projects, 4)
        pattern = r'<!-- MANTA_RESULTS_AUTO_START -->.*?<!-- MANTA_RESULTS_AUTO_END -->'
        self.assertEqual(re.search(pattern, page, re.S)[0], re.search(pattern, updated, re.S)[0])


if __name__ == '__main__':
    unittest.main()
