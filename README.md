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
