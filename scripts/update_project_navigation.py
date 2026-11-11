"""Update only project navigation, following the order in the two home pages.

Korean pages live in dist/projects and follow dist/index.html. English pages
live in dist/en/projects and follow dist/en/index.html; both lists must name the
same projects in the same order. Static HTML remains usable without JavaScript.
--check never writes files. All pages are validated before the first write;
bytes outside the navigation, header menu, language switch and stylesheet or
script cache tokens are retained, including line endings.
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
    'imu-lstm-fsm.html': 'IMU 주행 상태 판별',
    'argus-drone.html': 'ARGUS 온보드 AI 드론',
    'stm32-tracking.html': 'STM32 표적 탐지 및 추적',
    'manta.html': 'MANTA',
    'mosaic-c2.html': 'MOSAIC C2',
    'davinci-autonomous.html': '카메라 기반 장애물 회피',
    'rgb-classification.html': 'RGB 색상 분류',
    'crosswalk-gap.html': '비신호 횡단보도 연구',
}
EN_TITLES = {
    'sensor-fusion.html': 'Sensor-Fusion Vehicle Tracking',
    'roboracer.html': 'IFAC RoboRacer',
    'imu-lstm-fsm.html': 'IMU Driving-State Classification',
    'argus-drone.html': 'ARGUS Onboard AI Drone',
    'stm32-tracking.html': 'STM32 Target Detection and Tracking',
    'manta.html': 'MANTA',
    'mosaic-c2.html': 'MOSAIC C2',
    'davinci-autonomous.html': 'Camera-Based Obstacle Avoidance',
    'rgb-classification.html': 'RGB Color Classification',
    'crosswalk-gap.html': 'Unsignalized Crosswalk Study',
}
LANGUAGES = {
    'ko': {
        'index': 'index.html', 'pages': 'projects', 'titles': TITLES, 'assets': '../assets/',
        'back': '← 프로젝트 목록', 'prev': '← 이전 프로젝트', 'next': '다음 프로젝트 →',
        'all': '전체 프로젝트', 'first_all': '← 프로젝트 목록', 'last_all': '프로젝트 목록 →',
        'pagination': '프로젝트 이동', 'menu_label': '상세 페이지 메뉴',
        'menu': ('프로젝트', '연구성과'), 'switch_label': '언어 선택',
    },
    'en': {
        'index': 'en/index.html', 'pages': 'en/projects', 'titles': EN_TITLES, 'assets': '../../assets/',
        'back': '← All projects', 'prev': '← Previous project', 'next': 'Next project →',
        'all': 'All projects', 'first_all': '← Back to projects', 'last_all': 'Back to projects →',
        'pagination': 'Project navigation', 'menu_label': 'Project page menu',
        'menu': ('Projects', 'Research'), 'switch_label': 'Language',
    },
}
NAV = re.compile(r'<nav\b[^>]*>.*?</nav\s*>', re.S | re.I)
CLASS = re.compile(r'\bclass=["\']([^"\']+)["\']', re.I)
CSS_VERSION = 'project-navigation-20260913'
LANGUAGE_CSS_VERSION = '20261109'
SCRIPT_VERSION = 'languages-20261109b'


def classes(tag):
    match = CLASS.search(tag.split('>', 1)[0])
    return set(match[1].split()) if match else set()


class ProjectOrder(HTMLParser):
    def __init__(self, titles=TITLES):
        super().__init__()
        self.depth = 0
        self.titles = titles
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
            title = attrs.get('data-project-nav-title') or self.titles.get(filename)
            if not title:
                raise ValueError(f'Add a short navigation title for {filename}')
            self.projects.append((filename, title))

    def handle_endtag(self, tag):
        if tag == 'section' and self.depth:
            self.depth -= 1


def read_order(index, lang='ko'):
    parser = ProjectOrder(LANGUAGES[lang]['titles'])
    parser.feed(index)
    projects = parser.projects
    if not projects or len({p[0] for p in projects}) != len(projects):
        raise ValueError('Project list is empty or contains duplicate destinations')
    return projects


def pagination(projects, position, lang='ko'):
    text = LANGUAGES[lang]
    first, last = position == 0, position == len(projects) - 1
    modifier = ' project-pagination-first' if first else ' project-pagination-last' if last else ''
    links = []
    if not first:
        filename, title = projects[position - 1]
        links.append(f'<a class="project-pagination-prev" href="{filename}" rel="prev"><span>{text["prev"]}</span><strong>{html.escape(title)}</strong></a>')
    if first or last:
        label = text['first_all'] if first else text['last_all']
        links.append(f'<a class="project-pagination-all" href="../index.html#projects"><span>{text["all"]}</span><strong>{label}</strong></a>')
    else:
        links.append(f'<a class="project-pagination-all" href="../index.html#projects">{text["all"]}</a>')
    if not last:
        filename, title = projects[position + 1]
        links.append(f'<a class="project-pagination-next" href="{filename}" rel="next"><span>{text["next"]}</span><strong>{html.escape(title)}</strong></a>')
    return f'<nav class="project-pagination section-shell{modifier}" aria-label="{text["pagination"]}">' + ''.join(links) + '</nav>'


def language_switch(filename, lang='ko'):
    """Link to the same project in the other language and mark the current one."""
    korean = filename if lang == 'ko' else f'../../projects/{filename}'
    english = f'../en/projects/{filename}' if lang == 'ko' else filename
    current = ' aria-current="page"'
    return (f'<nav class="language-switch" aria-label="{LANGUAGES[lang]["switch_label"]}">'
            f'<a href="{korean}" hreflang="ko" lang="ko" aria-label="한국어" data-language-link{current if lang == "ko" else ""}>KOR</a>'
            f'<a href="{english}" hreflang="en" lang="en" aria-label="English" data-language-link{current if lang == "en" else ""}>ENG</a></nav>')


def update_page(original, projects, position, lang='ko'):
    text = LANGUAGES[lang]
    filename = projects[position][0]
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
    back = re.findall(r'<a class="back-link" href="\.\./index\.html#projects">\s*' + re.escape(text['back']) + r'\s*</a>', hero[0])
    if len(back) != 1:
        raise ValueError('Hero must have one static same-tab project-list link')
    updated = original[:match.start()] + pagination(projects, position, lang) + original[match.end():]
    menus = [m for m in NAV.finditer(updated) if 'primary-nav' in classes(m[0])]
    if len(menus) != 1:
        raise ValueError('Expected one detail header menu')
    menu = menus[0]
    projects_label, research_label = text['menu']
    normalized = (f'<nav class="primary-nav" aria-label="{text["menu_label"]}"><a href="../index.html#projects">{projects_label}</a>'
                  f'<a href="../index.html#research">{research_label}</a></nav>')
    updated = updated[:menu.start()] + normalized + updated[menu.end():]
    switches = [m for m in NAV.finditer(updated) if 'language-switch' in classes(m[0])]
    if len(switches) > 1:
        raise ValueError('Expected at most one language switch')
    switch = language_switch(filename, lang)
    if switches:
        updated = updated[:switches[0].start()] + switch + updated[switches[0].end():]
    else:
        end = updated.index(normalized) + len(normalized)
        updated = updated[:end] + switch + updated[end:]
    header = re.search(r'<header\b[^>]*class="site-header detail-header"[^>]*>.*?</header>', updated, re.S)
    if not header or switch not in header[0] or normalized not in header[0]:
        raise ValueError('Menu and language switch must be in the detail header')
    assets = re.escape(text['assets'])
    updated, count = re.subn(r'(?<=href=")' + assets + r'site\.css(?:\?[^"\s]*)?(?=")',
                             f'{text["assets"]}site.css?readability=20260914&amp;v={CSS_VERSION}', updated)
    if count != 1:
        raise ValueError('Expected one shared stylesheet')
    language_css = f'<link rel="stylesheet" href="{text["assets"]}project-languages.css?v={LANGUAGE_CSS_VERSION}">'
    existing = re.findall(r'<link rel="stylesheet" href="' + assets + r'project-languages\.css(?:\?[^"\s]*)?">', updated)
    if len(existing) > 1:
        raise ValueError('Expected at most one language stylesheet')
    if existing:
        updated = updated.replace(existing[0], language_css)
    elif '</head>' in updated:
        updated = updated.replace('</head>', f'  {language_css}\n</head>', 1)
    else:
        raise ValueError('Document head not found')
    updated, count = re.subn(r'(?<=src=")' + assets + r'site\.js(?:\?[^"\s]*)?(?=")',
                             f'{text["assets"]}site.js?v={SCRIPT_VERSION}', updated)
    if count != 1:
        raise ValueError('Expected one shared script')
    return updated


def read_orders(dist):
    orders = {lang: read_order((dist / text['index']).read_bytes().decode('utf-8'), lang)
              for lang, text in LANGUAGES.items()}
    if [p[0] for p in orders['ko']] != [p[0] for p in orders['en']]:
        raise ValueError('Korean and English home pages must list the same projects in the same order')
    return orders


def build(dist, check=False):
    orders = read_orders(dist)
    changes = []
    for lang, projects in orders.items():
        for position, (filename, _) in enumerate(projects):
            path = dist / LANGUAGES[lang]['pages'] / filename
            original = path.read_bytes().decode('utf-8')
            updated = update_page(original, projects, position, lang)
            if original != updated:
                changes.append((path, updated))
    if check:
        for path, _ in changes:
            print(f'Navigation out of date: {path.relative_to(dist).as_posix()}')
        return not changes
    for path, updated in changes:
        path.write_bytes(updated.encode('utf-8'))
    print(f'Navigation: {len(orders["ko"])} ordered projects in {len(orders)} languages, {len(changes)} pages updated')
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
