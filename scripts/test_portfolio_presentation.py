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
    def test_project_copy_and_evidence_hierarchy(self):
        sensor = (DIST / 'projects/sensor-fusion.html').read_text(encoding='utf-8')
        robo = (DIST / 'projects/roboracer.html').read_text(encoding='utf-8')
        imu = (DIST / 'projects/imu-lstm-fsm.html').read_text(encoding='utf-8')
        mosaic = (DIST / 'projects/mosaic-c2.html').read_text(encoding='utf-8')
        davinci = (DIST / 'projects/davinci-autonomous.html').read_text(encoding='utf-8')

        self.assertIn('각 검증 환경에서 동일한 데이터를 사용해 두 방법을 비교했습니다.', sensor)
        self.assertNotIn('학위논문 표에 직접 기재된 값', sensor)
        self.assertIn('<h2>회피 상태 전환</h2>', robo)
        self.assertNotIn('<h2>주행 상태 판정</h2>', robo)
        self.assertNotIn('실제 대회에서는 발동하지 않았습니다.', robo)
        self.assertNotIn('해당 복구 모드가 발동하지 않음', robo)
        self.assertIn('<h3>세 실차 경로의 위치 RMSE</h3>', imu)
        for value in ('2.56 cm', '2.31 cm', '1.35 cm'):
            self.assertNotIn(value, imu)
        for old_copy in ('원본 시뮬레이터 실행', '원본 통합 임무 이벤트 로그',
                         '원본 WPF 화면', '동일한 원본 코드'):
            self.assertNotIn(old_copy, mosaic)
        self.assertIn('<h2>대표 운용 화면과 실행</h2>', mosaic)
        self.assertIn('<h2>검출 결과를 경로와 조향으로 연결</h2>', davinci)
        for step in ('차선과 장애물 검출 결과를 주행 판단에 활용',
                     '양쪽 차선 사이의 중앙 기준 경로 계산',
                     '경로의 횡방향 오차를 조향 명령으로 변환'):
            self.assertIn(step, davinci)

    def test_manta_explains_inputs_methods_and_validation_scope(self):
        home = (DIST / 'index.html').read_text(encoding='utf-8')
        manta = (DIST / 'projects/manta.html').read_text(encoding='utf-8')
        self.assertIn('카메라와 라이다 기반 센서융합 및 차량 상태 추정, IMU 기반 주행 상태 판별부터', home)
        self.assertIn('IMU 기반으로 전진, 후진, 정지의 주행 상태를 판별했습니다.', home)
        self.assertNotIn('카메라, 라이다, IMU 기반 센서융합', home)
        self.assertIn('한국교통연구원장상, 공과대학장상', home)
        self.assertEqual(len(re.findall(r'<section class="case-section(?: alt-section)?">', manta)), 4)
        self.assertIn('BlueROV2와 어뢰의 위치 상태는 Gazebo 시뮬레이션에서 입력받았습니다.', manta)
        self.assertIn('두 가지 접근을 구현했습니다.', manta)
        implementation = manta.split('03 / IMPLEMENTATION', 1)[1].split('04 / VALIDATION', 1)[0]
        self.assertLess(implementation.index('짧은 회피 경로를 반복해서 생성합니다.'),
                        implementation.index('class="manta-two-col"'))
        validation = manta.split('04 / VALIDATION', 1)[1]
        table = validation.index('<table')
        for explanation in ('A*와 DVO를 모두 구현하고 시험했으며',
                            'DVO의 24개 조건 결과를 대표로 정리했습니다.',
                            '현재 표적 방향을 따라가는 방식', '비례항법 유도(PN)',
                            '첫 접근만 피한 경우는 최종 회피로 보지 않았습니다.'):
            self.assertLess(validation.index(explanation), table)
        self.assertEqual(manta.count('두 플래너의 정량 우열은 비교하지 않았습니다.'), 1)
        self.assertGreater(validation.index('최신 동일 코드 기준의 A* 대조군은 없어'), table)
        self.assertNotIn('<th scope="col">PNG</th>', manta)
        self.assertIn('<details class="manta-data-details" open>', manta)
        self.assertIn('<strong>C</strong>', home)
        self.assertIn('<strong>C++</strong>', home)
        self.assertIn('DQN 학습과 추론', home)
        self.assertIn('24개 조건 중 15개', manta)
        self.assertIn('12개 중 11개', manta)
        self.assertIn('12개 중 4개', manta)
        self.assertIn('유도 방식에 따라 최종 회피가 가능한 조건이 크게 달라진다는 점', manta)
        self.assertNotIn('62.5%', home + manta)
        trajectory = (DIST / 'assets/generated/manta/dvo-measured-trajectory.svg').read_text(encoding='utf-8')
        mobile_trajectory = (DIST / 'assets/generated/manta/dvo-measured-trajectory-mobile.svg').read_text(encoding='utf-8')
        for figure in (trajectory, mobile_trajectory):
            self.assertIn('marker-end="url(#rov-direction)"', figure)
            self.assertIn('marker-end="url(#torpedo-direction)"', figure)
            self.assertIn('○ 시작 · 화살표 진행 방향', figure)

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

    def test_confirmed_scope_and_summary_polish(self):
        home = (DIST / 'index.html').read_text(encoding='utf-8')
        parser = MetaTags()
        parser.feed(home)
        self.assertEqual(parser.tags['description'], parser.tags['og:description'])
        self.assertNotIn('실제 플랫폼에 연결해', home)
        self.assertIn('센서융합과 상태 추정, 경로 계획을 구현해<br>시뮬레이션과 실제 환경에서 검증했습니다', home)
        self.assertNotIn('DVO/Hybrid', home)
        self.assertIn('A*, DVO 회피 경로 계획 구현, DVO 24조건 결과 분석', home)
        mosaic = (DIST / 'projects/mosaic-c2.html').read_text(encoding='utf-8')
        for page in (home, mosaic):
            self.assertIn('2026.07.17–2026.07.24', page)
        self.assertIn('7개 운용 화면', home)
        self.assertIn('전체 7개 중 대표 4종 소개', mosaic)
        self.assertIn('Command and Control, 지휘통제', mosaic)
        self.assertIn('실제 무기체계 성능을 의미하지 않습니다.', mosaic)
        imu = (DIST / 'projects/imu-lstm-fsm.html').read_text(encoding='utf-8')
        self.assertIn('판별 출력이 불필요하게 바뀌지 않도록', imu)
        self.assertIn('한 경로의 전진, 후진, 정지 혼동행렬입니다.', imu)
        self.assertEqual(len(re.findall(r'<div(?:\s|>)', imu)), imu.count('</div>'))
        davinci = (DIST / 'projects/davinci-autonomous.html').read_text(encoding='utf-8')
        self.assertIn('장애물 3개를 랜덤 배치한 10회 시험', davinci)
        self.assertIn('davinci-vehicle-original.png', davinci)
        self.assertNotIn('경로계획', davinci)
        stm = (DIST / 'projects/stm32-tracking.html').read_text(encoding='utf-8')
        self.assertIn('stm32-uart-detection-tracking.png', stm)
        self.assertIn('CANDIDATE CONFIRMED: angle=110', stm)
        self.assertIn('TRACKING START: angle=110', stm)
        self.assertIn('스캔 프레임 구성과 비교 규칙', stm)
        rgb = (DIST / 'projects/rgb-classification.html').read_text(encoding='utf-8')
        self.assertIn('<th scope="col">정확도</th>', rgb)
        self.assertNotIn('세 모델의 Confusion Matrix', rgb)
        self.assertIn('rgb-mobile-matrices', rgb)
        for box in ('0 0 390 388', '390 0 400 388', '790 0 476 388'):
            self.assertIn('viewBox="' + box + '"', rgb)
        self.assertIn('오렌지파이와 카메라를 사용해', rgb)
        self.assertIn('RGB 채널 평균값 3개를, CNN은 128×128×3 전체 이미지를', rgb)
        crosswalk = (DIST / 'projects/crosswalk-gap.html').read_text(encoding='utf-8')
        self.assertNotIn('·', crosswalk)
        self.assertIn('횡단 판단의 임계거리', crosswalk)
        self.assertIn('916건</strong><span>Lag 관측 사례', crosswalk)

    def test_share_image_is_landscape_jpeg(self):
        self.assertEqual(jpeg_size((DIST / 'assets/og/profile-share.jpg').read_bytes()), (1200, 630))

    def test_main_section_indices_remain_ordered(self):
        page = (DIST / 'index.html').read_text(encoding='utf-8')
        labels = re.findall(r'<header class="editorial-heading[^\"]*"><span>(\d+)</span>', page)
        self.assertEqual(labels, ['01', '02', '03', '04', '05'])
        css = (DIST / 'assets/site.css').read_text(encoding='utf-8')
        self.assertIn('.portfolio-home .editorial-heading>span { font-size:2rem;', css)
        self.assertIn('.portfolio-home .editorial-heading>span { font-size:2.5rem;', css)

    def test_crosswalk_uses_original_observation_material(self):
        page = (DIST / 'projects/crosswalk-gap.html').read_text(encoding='utf-8')
        for name in ('step1', 'step2', 'step3', 'zones', 'criteria'):
            filename = 'crosswalk-observation-' + name + '.png'
            self.assertIn(filename, page)
            self.assertEqual((DIST / 'assets/images' / filename).read_bytes()[:8], b'\x89PNG\r\n\x1a\n')
        for filename in ('crosswalk-filming-location.png', 'crosswalk-distance-calibration.png'):
            self.assertIn(filename, page)
            self.assertTrue((DIST / 'assets/images' / filename).is_file())
        for step in (1, 2, 3):
            self.assertNotIn('src="../assets/images/crosswalk-step' + str(step) + '.svg"', page)
        self.assertEqual(page.count('<section class="case-section'), 5)
        for value in ('15.33 m', '16.16 m', '3.27 s', '3.93 s', '916건', '675 Accept / 241 Reject'):
            self.assertIn(value, page)
        self.assertIn('viewBox="0 0 1421 436"', page)
        self.assertIn('crosswalk-evidence.css?v=originals-20260914', page)

    def test_davinci_path_labels_and_embedded_font(self):
        import xml.etree.ElementTree as ET
        for name in ('davinci-autonomous-overview.svg', 'davinci-autonomous-overview-mobile.svg'):
            svg = (DIST / 'assets/images' / name).read_text(encoding='utf-8')
            ET.fromstring(svg)
            self.assertIn('좌측 차선 가림', svg)
            self.assertIn('A* 생성 경로', svg)
            self.assertIn('파란 선: A*로 생성한 우회 및 복귀 경로', svg)
            self.assertIn('font-family:Pretendard;src:url(data:font/woff2;base64,', svg)
            self.assertNotIn('Arial,Malgun Gothic', svg)
            self.assertNotIn('M170 205H310V130H316', svg)
            self.assertNotIn('M236 347Q247 326 236 300', svg)
        page = (DIST / 'projects/davinci-autonomous.html').read_text(encoding='utf-8')
        self.assertEqual(page.count('?v=clarity-20260914'), 2)

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
        self.assertIn('실제 실행 기록입니다.', page)
        self.assertIn('CANDIDATE: frame=23, angle=110, distance=108 mm, delta=57 mm', page)
        self.assertIn('LOCK SAMPLE: 2/3, angle=110, distance=14.8 cm', page)
        self.assertIn('TRACK TARGET: angle=110, distance=6.1 cm', page)
        self.assertTrue((DIST / 'assets/images/stm32-uart-detection-tracking.png').is_file())
        import xml.etree.ElementTree as ET
        source = ET.parse(DIST / 'assets/images/stm32-uart-detection-tracking.svg')
        extracts = source.findall('.//*[@data-verbatim="true"]')
        self.assertEqual(len(extracts), 10)
        for line in extracts:
            self.assertIn(line.text, page)
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


    def test_readability_and_navigation_refinements(self):
        home = (DIST / 'index.html').read_text(encoding='utf-8')
        self.assertIn('국가 R&amp;D 과제 2건 수행', home)
        self.assertIn('교육부 / 한국연구재단 — 연구책임자', home)
        self.assertIn('과학기술정보통신부 — 학생연구원', home)
        self.assertIn('STM32 기반 탐지 및 추적 장치', home)
        self.assertNotIn('임베디드 실기기', home)
        imu = (DIST / 'projects/imu-lstm-fsm.html').read_text(encoding='utf-8')
        rgb = (DIST / 'projects/rgb-classification.html').read_text(encoding='utf-8')
        sensor = (DIST / 'projects/sensor-fusion.html').read_text(encoding='utf-8')
        manta = (DIST / 'projects/manta.html').read_text(encoding='utf-8')
        self.assertIn('CNN 정확도 99.91%', home)
        self.assertIn('시험 데이터 2,106장 기준', rgb)
        self.assertNotIn('0: 전진, 1: 후진, 2: 정지', imu)
        self.assertNotIn('상태 비교 그래프 원본 보기', imu)
        self.assertIn('Python 학습과 추론 구현', sensor)
        self.assertNotIn('전체 경로 생성 실패가 곧바로', manta)
        script = (DIST / 'assets/site.js').read_text(encoding='utf-8')
        self.assertIn("event.key === 'Escape'", script)
        self.assertIn("open ? '메뉴 닫기' : '메뉴 열기'", script)


if __name__ == '__main__':
    unittest.main()
