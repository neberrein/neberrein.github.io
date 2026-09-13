"""Native-vector illustrations, separate from measured CSV trajectories.

Both planning panels deliberately share all initial coordinates.
"""
from pathlib import Path
from html import escape

OUT = Path(__file__).resolve().parents[1] / 'dist/assets/images'
NAVY, MUTED, BLUE, GREEN, RED = '#193044', '#536574', '#2b73b8', '#23774a', '#a83b38'


def start(w, h, title, desc):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc"><title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10" fill="context-stroke"/></marker></defs>',
            f'<rect width="{w}" height="{h}" fill="white"/><g font-family="Pretendard, Noto Sans KR, Arial, sans-serif" fill="{NAVY}">']


def text(s, x, y, label, size=21, color=NAVY, bold=False, anchor='start'):
    s.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{700 if bold else 400}" text-anchor="{anchor}">{escape(label)}</text>')


def rect(s, x, y, w, h, fill='white', stroke='#bccbd5', dash=''):
    s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.5" stroke-dasharray="{dash}"/>')


def path(s, d, color=MUTED, dash='', arrow=False, width=3):
    s.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-dasharray="{dash}"'+(' marker-end="url(#arrow)"' if arrow else '')+'/>')


def dot(s, x, y, color, r=9):
    s.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>')


def save(s, name):
    OUT.joinpath(name).write_text('\n'.join(s + ['</g></svg>']) + '\n', encoding='utf-8')


def scope(mobile=False):
    s = start(440 if mobile else 1100, 720 if mobile else 310,
              'MANTA 시스템 연결과 담당 범위',
              'BlueROV2와 어뢰 상태를 받아 담당 영역에서 위협 판단, A* 또는 DVO 경로 생성, 회피 경로 출력을 수행합니다. 팀의 경로 추종과 제어 모듈이 이를 Gazebo 기체의 움직임으로 연결합니다.')
    if mobile:
        rect(s, 20, 20, 190, 60, '#edf2f5')
        rect(s, 230, 20, 190, 60, '#edf2f5')
        text(s, 115, 57, 'BlueROV2 상태', 21, bold=True, anchor='middle')
        text(s, 325, 57, '어뢰 상태', 21, bold=True, anchor='middle')
        path(s, 'M115 80V103H220M325 80V103H220V133', arrow=True)
        rect(s, 20, 135, 400, 330, '#f4f8fb', BLUE)
        text(s, 40, 171, '담당 영역', 22, BLUE, True)
        for y, label in ((194, '위협 판단'), (280, 'A* 또는 DVO'), (366, '회피 경로')):
            rect(s, 95, y, 250, 60, '#fff', BLUE)
            text(s, 220, y+38, label, 23, BLUE, True, 'middle')
        path(s, 'M220 254V277', BLUE, arrow=True)
        path(s, 'M220 340V363', BLUE, arrow=True)
        text(s, 220, 449, 'nav_msgs/Path', 18, MUTED, anchor='middle')
        path(s, 'M220 465V497', arrow=True)
        rect(s, 35, 500, 370, 100, '#f3f5f6')
        text(s, 220, 532, '팀 제어 모듈', 18, MUTED, anchor='middle')
        text(s, 220, 563, '경로 추종과 제어', 23, bold=True, anchor='middle')
        text(s, 220, 588, 'PathFollower, PPID, 추진기 제어', 17, MUTED, anchor='middle')
        path(s, 'M220 600V632', arrow=True)
        rect(s, 95, 635, 250, 60, '#edf2f5')
        text(s, 220, 673, 'Gazebo 기체 동작', 22, bold=True, anchor='middle')
    else:
        rect(s, 20, 102, 172, 60, '#edf2f5')
        rect(s, 20, 185, 172, 60, '#edf2f5')
        text(s, 106, 139, 'BlueROV2 상태', 18, bold=True, anchor='middle')
        text(s, 106, 222, '어뢰 상태', 20, bold=True, anchor='middle')
        path(s, 'M192 132H215V174M192 215H215V174H253', arrow=True)
        rect(s, 255, 55, 460, 211, '#f4f8fb', BLUE)
        text(s, 278, 92, '담당 영역', 23, BLUE, True)
        for x, w, label in ((278, 112, '위협 판단'), (419, 143, 'A* 또는 DVO'), (591, 101, '회피 경로')):
            rect(s, x, 137, w, 74, '#fff', BLUE)
            text(s, x+w/2, 182, label, 19, BLUE, True, 'middle')
        path(s, 'M390 174H416', BLUE, arrow=True)
        path(s, 'M562 174H588', BLUE, arrow=True)
        text(s, 641, 241, 'nav_msgs/Path', 16, MUTED, anchor='middle')
        path(s, 'M715 174H750', arrow=True)
        rect(s, 753, 115, 203, 118, '#f3f5f6')
        text(s, 854, 146, '팀 제어 모듈', 17, MUTED, anchor='middle')
        text(s, 854, 180, '경로 추종과 제어', 21, bold=True, anchor='middle')
        text(s, 854, 208, 'PathFollower, PPID', 15, MUTED, anchor='middle')
        text(s, 854, 227, '추진기 제어', 15, MUTED, anchor='middle')
        path(s, 'M956 174H987', arrow=True)
        rect(s, 990, 137, 90, 74, '#edf2f5')
        text(s, 1035, 170, 'Gazebo', 19, bold=True, anchor='middle')
        text(s, 1035, 194, '기체 동작', 16, MUTED, anchor='middle')
    save(s, 'manta-system-scope-mobile.svg' if mobile else 'manta-system-scope.svg')


def planning_panel(s, x, y, method):
    """Same ROV (65,315), threat (180,145), goal (390,95) in both panels."""
    s.append(f'<g transform="translate({x} {y})">')
    color = BLUE if method == 'astar' else GREEN
    rect(s, 0, 0, 460, 470, '#f7f9fb' if method == 'astar' else '#f6f9f7', '#d5e1e8')
    text(s, 24, 38, 'A* / 목표까지 이어지는 경로' if method == 'astar' else 'DVO / 가까운 구간의 회피 경로', 22, color, True)
    path(s, 'M65 315L390 95', '#8795a1', '7 6', width=2)
    text(s, 270, 291, '기존 임무 경로', 18, MUTED)
    path(s, 'M302 274L269 178', '#8795a1', width=1)
    dot(s, 390, 95, NAVY, 8)
    text(s, 352, 76, '임무 목표', 18, bold=True)
    if method == 'astar':
        for bx, by in ((219, 172), (247, 191), (275, 210)):
            rect(s, bx-20, by-17, 40, 34, '#f6d9d6', '#c7776b', '4 3')
        text(s, 202, 365, '예상 위험 영역', 19, RED)
        path(s, 'M257 343L263 233', RED, width=1)
        path(s, 'M65 315C87 248 93 160 156 97S278 54 390 95', BLUE, arrow=True, width=4)
        text(s, 35, 429, 'A*가 생성한 경로', 19, BLUE, True)
        path(s, 'M98 407L108 204', BLUE, width=1)
    else:
        path(s, 'M195 158L320 241', RED, '6 5', True, width=2)
        text(s, 232, 365, '위협의 예상 이동', 19, RED)
        path(s, 'M290 344L287 223', RED, width=1)
        path(s, 'M65 315L170 278', '#a1adb5', arrow=True, width=2)
        path(s, 'M65 315L183 321', '#a1adb5', arrow=True, width=2)
        path(s, 'M65 315C75 281 88 246 115 218', GREEN, arrow=True, width=4)
        text(s, 188, 315, '이동 후보', 18, MUTED)
        text(s, 35, 429, '선택한 회피 경로', 19, GREEN, True)
        path(s, 'M98 407L94 267', GREEN, width=1)
    rect(s, 46, 303, 38, 25, '#dbe9f3', BLUE)
    text(s, 25, 355, 'BlueROV2', 18, BLUE, True)
    s.append('<g transform="translate(180 145) rotate(34)"><rect x="-17" y="-7" width="34" height="14" rx="7" fill="#a83b38"/><path d="M-16 -7L-23 -13V13L-16 7" fill="#a83b38"/></g>')
    text(s, 210, 138, '어뢰 현재 위치', 18, RED, True)
    s.append('</g>')


def threat(mobile=False):
    w, h = (500, 1000) if mobile else (1100, 555)
    s = start(w, h, '같은 상황에서 A*와 DVO의 경로 생성 비교',
              '회피 방식 개념도. 동일한 기체, 위협, 목표와 임무 경로에서 A*는 예측한 위험 영역을 피해 목표까지 경로를 탐색합니다. DVO는 위협의 예상 이동과 여러 이동 후보를 평가해 짧은 회피 경로를 생성합니다. 실제 실험 좌표나 축척이 아닌 설명용 평면 도식입니다.')
    planning_panel(s, 20 if mobile else 45, 20 if mobile else 30, 'astar')
    planning_panel(s, 20 if mobile else 595, 510 if mobile else 30, 'dvo')
    if not mobile:
        text(s, 550, 535, '같은 시작 상황, 서로 다른 경로 생성 방식', 21, MUTED, anchor='middle')
    save(s, 'manta-threat-models-mobile.svg' if mobile else 'manta-threat-models.svg')


if __name__ == '__main__':
    scope()
    scope(True)
    threat()
    threat(True)
    print('Generated paired planning and scope SVGs, desktop and mobile; measured charts unchanged.')
