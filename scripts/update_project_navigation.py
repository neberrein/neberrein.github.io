"""Update only project navigation, following the order in dist/index.html.

Static HTML remains usable without JavaScript. --check never writes files.
All pages are validated before the first write; bytes outside the navigation,
header menu and stylesheet cache token are retained, including line endings.
"""
import argparse
import html
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TITLES = {
    'sensor-fusion.html': '센서융합 차량 추적',
    'roboracer.html': 'IFAC RoboRacer',
    'imu-lstm-fsm.html': 'IMU 주행상태 판별',
    'stm32-tracking.html': 'STM32 표적 탐지 및 추적',
    'manta.html': 'MANTA',
    'mosaic-c2.html': 'MOSAIC C2',
    'davinci-autonomous.html': '카메라 기반 장애물 회피',
    'rgb-classification.html': 'RGB 색상 분류',
    'crosswalk-gap.html': '비신호 횡단보도 연구',
}
NAV = re.compile(r'<nav\b[^>]*>.*?</nav\s*>', re.S | re.I)
CLASS = re.compile(r'\bclass=["\']([^"\']+)["\']', re.I)
CSS_VERSION = 'project-navigation-20260913'


def classes(tag):
    match = CLASS.search(tag.split('>', 1)[0])
    return set(match[1].split()) if match else set()


class ProjectOrder(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.projects = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'section':
            if self.depth:
                self.depth += 1
            elif attrs.get('id') == 'projects':
                self.depth = 1
        if self.depth and tag == 'a' and set(attrs.get('class', '').split()) & {'selected-case', 'project-row'}:
            href = attrs.get('href', '')
            if not re.fullmatch(r'projects/[\w-]+\.html', href):
                raise ValueError(f'Unexpected project destination: {href}')
            filename = href.removeprefix('projects/')
            if filename == 'davinci-vision.html':
                raise ValueError('Redirect cannot be a formal project')
            title = attrs.get('data-project-nav-title') or TITLES.get(filename)
            if not title:
                raise ValueError(f'Add a short navigation title for {filename}')
            self.projects.append((filename, title))

    def handle_endtag(self, tag):
        if tag == 'section' and self.depth:
            self.depth -= 1


def read_order(index):
    parser = ProjectOrder()
    parser.feed(index)
    projects = parser.projects
    if not projects or len({p[0] for p in projects}) != len(projects):
        raise ValueError('Project list is empty or contains duplicate destinations')
    return projects


def pagination(projects, position):
    first, last = position == 0, position == len(projects) - 1
    modifier = ' project-pagination-first' if first else ' project-pagination-last' if last else ''
    links = []
    if not first:
        filename, title = projects[position - 1]
        links.append(f'<a class="project-pagination-prev" href="{filename}" rel="prev"><span>← 이전 프로젝트</span><strong>{html.escape(title)}</strong></a>')
    if first or last:
        label = '← 프로젝트 목록' if first else '프로젝트 목록 →'
        links.append(f'<a class="project-pagination-all" href="../index.html#projects"><span>전체 프로젝트</span><strong>{label}</strong></a>')
    else:
        links.append('<a class="project-pagination-all" href="../index.html#projects">전체 프로젝트</a>')
    if not last:
        filename, title = projects[position + 1]
        links.append(f'<a class="project-pagination-next" href="{filename}" rel="next"><span>다음 프로젝트 →</span><strong>{html.escape(title)}</strong></a>')
    return f'<nav class="project-pagination section-shell{modifier}" aria-label="프로젝트 이동">'+''.join(links)+'</nav>'


def update_page(original, projects, position):
    matches = [m for m in NAV.finditer(original) if classes(m[0]) & {'next-project', 'project-pagination'}]
    if len(matches) != 1:
        raise ValueError('Expected exactly one existing project navigation')
    match = matches[0]
    # Do not move navigation into a disclosure or regenerated results block.
    prefix = original[:match.start()]
    if prefix.count('<details') != prefix.count('</details>'):
        raise ValueError('Navigation is inside a disclosure')
    if prefix.count('<!-- MANTA_RESULTS_AUTO_START -->') != prefix.count('<!-- MANTA_RESULTS_AUTO_END -->'):
        raise ValueError('Navigation is inside the generated results block')
    if not ('</main' in original[match.end():] and '<footer' in original[match.end():]):
        raise ValueError('Navigation must be at the end of main, before footer')
    hero = re.search(r'<section\b[^>]*class="case-hero\b[^>]*>.*?</section>', original, re.S)
    if not hero:
        raise ValueError('Hero not found')
    back = re.findall(r'<a class="back-link" href="\.\./index\.html#projects">\s*← 프로젝트 목록\s*</a>', hero[0])
    if len(back) != 1:
        raise ValueError('Hero must have one static same-tab project-list link')
    updated = original[:match.start()] + pagination(projects, position) + original[match.end():]
    menus = [m for m in NAV.finditer(updated) if 'primary-nav' in classes(m[0])]
    if len(menus) != 1:
        raise ValueError('Expected one detail header menu')
    menu = menus[0]
    normalized = '<nav class="primary-nav" aria-label="상세 페이지 메뉴"><a href="../index.html#projects">프로젝트</a><a href="../index.html#research">연구성과</a></nav>'
    updated = updated[:menu.start()] + normalized + updated[menu.end():]
    updated, count = re.subn(r'(?<=href=")\.\./assets/site\.css(?:\?[^"\s]*)?(?=")', f'../assets/site.css?v={CSS_VERSION}', updated)
    if count != 1:
        raise ValueError('Expected one shared stylesheet')
    return updated


def build(dist, check=False):
    projects = read_order((dist / 'index.html').read_bytes().decode('utf-8'))
    changes = []
    for position, (filename, _) in enumerate(projects):
        path = dist / 'projects' / filename
        original = path.read_bytes().decode('utf-8')
        updated = update_page(original, projects, position)
        if original != updated:
            changes.append((path, updated))
    if check:
        for path, _ in changes:
            print(f'Navigation out of date: {path.name}')
        return not changes
    for path, updated in changes:
        path.write_bytes(updated.encode('utf-8'))
    print(f'Navigation: {len(projects)} ordered projects, {len(changes)} pages updated')
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--dist', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    try:
        return 0 if build(args.dist, args.check) else 1
    except (ValueError, OSError) as error:
        print(f'Navigation validation failed: {error}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
