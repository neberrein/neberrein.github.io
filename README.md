# 곽민재 연구개발 포트폴리오

자율주행, 센서융합, 임베디드 소프트웨어 연구개발 포트폴리오입니다.

## 구성

- `dist/index.html`: 메인 페이지
- `dist/projects/`: 대표 프로젝트 상세 페이지
- `dist/assets/images/`: 프로젝트 결과 이미지
- `dist/assets/docs/`: 논문 원문
- `.github/workflows/pages.yml`: GitHub Pages 자동 배포

## 배포

GitHub 사용자 이름과 동일한 `<username>.github.io` 저장소의 `main` 브랜치에 올리면 GitHub Actions가 `dist` 폴더를 Pages로 배포합니다.

## MANTA 설명 그림

`python scripts/build_manta_explainers.py`는 담당 범위와 A*/DVO 위협 모델의 설명용 SVG를 생성합니다. 사용자 제공 그림 생성 묶음을 참고하되 현재 담당 범위에 맞게 정리했으며, 위협 모델에는 모바일 전용 도식도 제공합니다. 박스와 속도 후보는 예시입니다. 실제 CSV 기반 결과 그림은 별도의 `scripts/build_manta_results.py`에서 관리하며 이 스크립트로 변경하지 않습니다.

## 프로젝트 이동 메뉴

`python scripts/update_project_navigation.py`는 메인 `#projects`의 대표 카드와 프로젝트 행 순서를 읽어 9개 상세페이지의 이전/전체/다음 메뉴를 갱신합니다. 짧은 표시명은 스크립트의 `TITLES`에서 관리하며, 새 프로젝트에는 메인 링크의 `data-project-nav-title`도 사용할 수 있습니다. 본문, 미디어와 자동 결과 영역은 수정하지 않습니다. 첫 페이지와 마지막 페이지를 순환 연결하지 않습니다.

`python scripts/update_project_navigation.py --check`는 파일을 쓰지 않고 일치 여부를 검사합니다. `python scripts/test_project_navigation.py`는 연결 순서, 중복 방지, 반복 실행과 본문 보존을 검사합니다. 배포 과정에도 두 검사를 적용했습니다.

## 공유 이미지와 표현 검사

`scripts/build_profile_share.ps1`은 Windows의 맑은 고딕과 원본 프로필 사진으로 1200×630 JPEG 공유 카드를 생성합니다. 사진은 전체가 보이도록 축소 배치하며 얼굴을 재생성하거나 보정하지 않습니다. 배포 이미지는 `dist/assets/og/profile-share.jpg`입니다.

`python scripts/test_portfolio_presentation.py`는 공유 메타 태그의 중복·일치, JPEG 크기, 메인 섹션 번호와 STM32 본문 종결을 검사합니다. 배포 과정에서도 실행합니다.
