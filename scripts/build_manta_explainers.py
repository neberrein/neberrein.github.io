"""Generate conceptual scope/threat SVGs adapted from the user's reference.

These diagrams contain no experiment exports and do not alter measured charts.
Run independently of build_manta_results.py after editing illustration layout.
"""
from pathlib import Path
from html import escape

OUT = Path(__file__).resolve().parents[1] / 'dist/assets/images'
NAVY, MUTED, BLUE, GREEN, RED = '#193044', '#536574', '#2b73b8', '#23774a', '#a83b38'

def start(w, h, title, desc):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc"><title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10" fill="context-stroke"/></marker></defs>',
            f'<rect width="{w}" height="{h}" fill="white"/><g font-family="Pretendard, Noto Sans KR, Arial, sans-serif" fill="{NAVY}">']

def text(s, x, y, label, size=21, color=NAVY, bold=False, anchor='start'):
    s.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{700 if bold else 400}" text-anchor="{anchor}">{escape(label)}</text>')

def rect(s, x, y, w, h, fill='white', stroke='#bccbd5', dash=''):
    s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="2" stroke-dasharray="{dash}"/>')

def path(s, d, color=MUTED, dash='', arrow=False, width=3):
    s.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-dasharray="{dash}"'+(' marker-end="url(#arrow)"' if arrow else '')+'/>')

def dot(s, x, y, color, r=9):
    s.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>')

def save(s, name):
    OUT.joinpath(name).write_text('\n'.join(s + ['</g></svg>']) + '\n', encoding='utf-8')

def scope():
    s = start(1100, 430, 'MANTA 시스템 연결과 담당 범위', '상태 입력과 DataHub에서 PlanningCore, PlanningModule worker, PlanningEngine으로 연결됩니다. 담당 회피 모듈이 reference_path를 발행하고 팀의 PathFollower, PPID, 추진기 제어로 전달합니다. 논리적 데이터 흐름을 설명한 도식입니다.')
    text(s, 25, 36, '상태를 받아 회피 경로를 만들고, 제어 모듈에 전달', 25, bold=True)
    rect(s, 362, 65, 540, 208, '#f1f7f3', GREEN)
    text(s, 384, 98, 'MY SCOPE · 위협 판단 / 경로계획 / 실행 연결', 21, GREEN, True)
    specs = [(25, 150, ['ROV / 어뢰', 'Odometry', '위치·상태 입력']),
             (200, 136, ['DataHub', '최신 상태', '스냅샷']),
             (384, 150, ['PlanningCore', '속도 추정 · TTC', '단계·참여 판정']),
             (557, 150, ['PlanningModule', 'worker 실행', '최신 입력 교체']),
             (730, 150, ['PlanningEngine', 'A* / DVO', '선택 플래너 실행'])]
    for i, (x, w, labels) in enumerate(specs):
        rect(s, x, 124, w, 121, '#fff' if i > 1 else '#edf2f5', GREEN if i > 1 else '#bccbd5')
        for j, label in enumerate(labels):
            text(s, x+w/2, 156+j*32, label, 18 if (j == 0 and i > 1) or (i == 2 and j == 2) else 20, bold=j==0, anchor='middle')
    for x1, x2 in [(175,198),(336,382),(534,555),(707,728)]:
        path(s, f'M{x1} 183H{x2}', arrow=True)
    rect(s, 927, 124, 148, 121, '#edf2f5', BLUE)
    text(s, 1001, 156, 'OUTPUT', 20, BLUE, True, 'middle')
    text(s, 1001, 189, 'reference_path', 18, BLUE, anchor='middle')
    text(s, 1001, 220, 'nav_msgs/Path', 17, anchor='middle')
    path(s, 'M880 183H925', arrow=True)
    rect(s, 25, 302, 1050, 80, '#f3f5f6', MUTED, '7 5')
    text(s, 45, 333, 'TEAM INTERFACE', 20, MUTED, True)
    text(s, 45, 362, '팀 제어 모듈', 19, MUTED)
    for x, label in [(375,'PathFollower'),(604,'PPID'),(790,'6개 추진기'),(979,'Gazebo 운동')]:
        text(s, x, 351, label, 22, anchor='middle')
    for x1,x2 in [(457,547),(645,717),(852,897)]:
        path(s, f'M{x1} 345H{x2}', arrow=True)
    path(s, 'M1001 245V286H375V316', arrow=True)
    text(s, 25, 414, '논리적 데이터 흐름 · 경로 발행은 PlanningModule에서 연결 · 어뢰 유도 제어도 팀 구현', 20, MUTED)
    save(s, 'manta-system-scope.svg')

def astar_geometry(s, x, y, scale=1):
    s.append(f'<g transform="translate({x} {y}) scale({scale})">')
    # A top-view schematic: future torpedo occupancy intersects a mission route.
    path(s, 'M40 172L390 18', MUTED, '8 5')
    rect(s, 22, 151, 44, 35, '#dbe9f3', BLUE)
    text(s, 23, 212, 'ROV', 20, BLUE, True)
    path(s, 'M35 32C134 20 189 44 228 91S297 141 368 149', RED, '6 5')
    for i,(bx,by) in enumerate([(20,17),(85,12),(147,28),(197,66),(243,113),(310,134)]):
        rect(s,bx,by,36,31,'#a83b38' if i==0 else '#f8dde1',RED)
    text(s, 20, 3, '어뢰 현재 위치', 20, RED, True)
    path(s, 'M185 99L203 117M203 99L185 117', RED, width=4)
    text(s, 245, 84, '통로와 경로가 겹침', 19, RED)
    text(s, 224, 201, '점선: ROV 임무 경로', 19, MUTED)
    s.append('</g>')

def dvo_geometry(s, x, y, scale=1):
    s.append(f'<g transform="translate({x} {y}) scale({scale})">')
    rect(s, 35, 136, 44, 35, '#dbe9f3', BLUE)
    text(s, 32, 205, 'ROV', 20, BLUE, True)
    rect(s, 304, 19, 48, 31, '#f8dde1', RED)
    text(s, 280, 4, '어뢰 현재 박스', 20, RED, True)
    path(s, 'M315 50L209 105', RED, '6 5', True)
    text(s, 244, 82, '추정 속도', 19, RED)
    # Neutral velocity candidates; no fabricated safe/unsafe classification.
    for xx,yy in [(110,55),(167,102),(189,155)]:
        path(s, f'M78 151L{xx} {yy}', GREEN, arrow=True)
    text(s, 92, 199, 'ROV 속도 후보 (예시)', 19, GREEN)
    path(s, 'M174 113L227 103', MUTED, '4 4')
    dot(s, 174, 113, MUTED, 4)
    dot(s, 227, 103, MUTED, 4)
    text(s, 181, 137, '최근접 거리 평가', 19, MUTED)
    s.append('</g>')

def threat(mobile=False):
    w,h = (440,930) if mobile else (1100,660)
    s = start(w,h,'A*와 DVO의 위협 모델 차이','설명용 평면 투영 도식입니다. A*는 유도 예측으로 미래 박스 통로를 만들고 공간 충돌을 검사합니다. DVO는 현재 어뢰 박스와 추정 상대속도로 각 후보의 최근접 거리를 검사합니다. 박스와 후보 화살표는 예시이며 측정 결과가 아닙니다.')
    text(s,20 if mobile else 28,36,'A* / DVO · 무엇을 예측하는가',22 if mobile else 25,bold=True)
    text(s,20 if mobile else 28,66,'설명용 평면 투영 · 실제 계획은 3D',18 if mobile else 21,MUTED)
    for row in range(2):
        y = (87+row*402) if mobile else (87+row*272)
        rect(s,15 if mobile else 28,y,410 if mobile else 1044,386 if mobile else 253,'#f0f5fa' if row==0 else '#f0f6f1', '#d5e1e8')
        text(s,30 if mobile else 48,y+34,'A* · 미래 박스 통로' if row==0 else 'DVO · 현재 박스 + 상대속도',21 if mobile else 24,BLUE if row==0 else GREEN,True)
        geom = astar_geometry if row==0 else dvo_geometry
        geom(s,30 if mobile else 48,y+58,0.9 if mobile else 0.82)
        lines = (['유도 모델로 미래 위치를 샘플링', '4.0 s / 약 1.5 m 간격 / 상한 32개', '3 × 3 × 3 m 박스로 위협 공간 구성', '박스 통로와 겹치는 공간을 피해 탐색'] if row==0 else
                 ['추정 상대속도를 6.0 s 동안 등속 외삽','각 ROV 속도 후보의 최근접 거리 검사','충돌 후보를 제외해 국소 경로 생성','계획 여유 약 3.85 m ≠ 실험 HIT 1.0 m'])
        for i,label in enumerate(lines):
            text(s,30 if mobile else 493,y+(279 if mobile else 87)+i*(29 if mobile else 41),label,20 if mobile else 22)
    text(s,20 if mobile else 28,h-27,'박스·속도 후보는 예시이며 측정 궤적이 아닙니다.',17 if mobile else 20,MUTED)
    save(s,'manta-threat-models-mobile.svg' if mobile else 'manta-threat-models.svg')

if __name__ == '__main__':
    scope()
    threat()
    threat(True)
    print('Generated scope and threat model SVGs (desktop/mobile); experimental charts unchanged.')
