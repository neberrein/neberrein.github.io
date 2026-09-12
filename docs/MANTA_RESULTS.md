# MANTA CSV 결과 반영 규칙

`portfolio_data/manta/latest/`에 실제 수집 파일을 넣고 저장소 루트에서 실행합니다.

```sh
python scripts/build_manta_results.py
```

다른 위치를 사용할 때:

```sh
python scripts/build_manta_results.py --input portfolio_data/manta/latest --output dist/assets/generated/manta
```

CSV가 없으면 아무 결과도 생성하지 않고 대표 측정값을 유지합니다. 일부 파일만 있거나 무결성 검사가 실패하면 페이지를 변경하지 않고 종료합니다. GitHub Pages 게시 과정에서도 같은 생성기를 실행합니다. CSV를 커밋하면 공개 저장소에 원문이 남으므로 개인정보·비공개 정보가 없는 실험 기록만 넣으세요.

## 필수 파일과 열

- `runs.csv`: `run_id,scenario,planner,mode,torpedo,outcome,closest_m,engagements,avoided_count,avoided_margins,plan_count,plan_ms_mean,plan_ms_median,plan_ms_max,reaction_sec,duration_sec`
- `plans.csv`: `run_id,t_rel,planner,ms,waypoints,boxes,vo_active`
- `events.csv`: `run_id,t_rel,type,value`
- `collect_log.txt`, `scale_info.txt`, `params.txt`: 수집 조건·축척·파라미터 원문. 조건을 확인할 수 없는 내용은 임의로 보충하지 않습니다.
- `traj/`: 선택. `{run_id}.csv`의 `t_rel,uuv_x,uuv_y`를 사용하며 XY 평면의 실제 ROV 궤적만 표시합니다. 같은 조건 A*/DVO 쌍이 없으면 생성하지 않습니다.

`scenario`: front/rear/side/diag. `planner`: astar/dvo. `mode`는 유도 방식(SimpleTracking/PNG)입니다. `torpedo`: 청상어/백상어/Mk48. `outcome`: HIT/AVOIDED/INVALID_사유. AVOIDED는 한 번 빗나간 것이 아니라 연료 소진까지 생존했다는 실험 실행기의 최종 판정을 사용하세요. `reaction_sec`는 실행기의 일관된 정의를 유지하고 측정하지 않았다면 빈 값으로 둡니다. `avoided_margins`는 `12.4|8.1|3.2` 형식이며 `avoided_count`와 개수가 일치해야 합니다. 헤더만 있는 plans/events 파일은 허용하지만 해당 상세 차트는 생략합니다.

## 중복과 무효 결과

중복 run_id는 전부 제외합니다. 계획 0회 또는 교전 없음은 유효 성능표에서 제외합니다. 동일 scenario/planner/mode/torpedo 조합은 명시적 `timestamp`(시간대 포함 ISO 8601) 또는 `index`(고유 정수)로 최신 **유효** 실행을 결정할 수 있을 때만 하나를 선택합니다. 행 순서는 최신 기준이 아닙니다. 모호하면 해당 중복 조합 전체를 제외하고 manifest에 경고를 남깁니다. 재실행이 있어도 48행 제한을 두지 않습니다. 48개 모든 고유 유효 조합을 확인하기 전에는 전체 완료로 표시하지 않습니다.

## 속도비 입력

runs의 추가 열 `speed_ratio` 또는 `torpedo_speed_mps,rov_speed_mps`를 사용합니다. scale_info/params에 명확한 매핑이 있으면 다음 JSON 형식도 허용합니다(수치는 실제 측정·설정 값으로 채워야 하며 예시 수치는 제공하지 않습니다).

```text
{"rov_speed_mps": 측정값, "torpedo_speed_mps": {"청상어": 설정값, "백상어": 설정값, "Mk48": 설정값}}
```

또는 `rov_speed_mps=...`, `torpedo_speed_mps.청상어=...` 등 정확한 key=value를 사용합니다. 서로 충돌하는 매핑, 누락된 매핑, 0인 ROV 속도에서는 속도비 차트를 생성하지 않습니다. 어뢰 이름으로 기본 속도를 추정하지 않습니다.

## 출력과 해석

`dist/assets/generated/manta/summary.json`, `generated-manifest.json`과 데이터가 충분한 SVG만 생성합니다. 페이지는 `MANTA_RESULTS_AUTO_START/END` 사이만 변경합니다. 본문 차트는 최대 3개, 상단 카드는 최대 4개, 표는 접근 방향별 하나입니다. 확대 링크로 모바일에서도 차트 원본을 열 수 있습니다.

개별 계획의 median/p95는 plans.csv에서 계산하며 runs의 계획시간 중앙값 중앙값(`run_plan_ms_median`)과 구분합니다. 결측 값은 N/A이고 0으로 대체하지 않습니다. 상대 속도비 감소 경향·재공격 누적 악화·경로 안정성·통계적 유의성 등을 데이터 없이 주장하지 않습니다. 재공격 차트는 생존한 회차만 포함하므로 표본 구성이 바뀌는 점도 주의해야 합니다.

manifest에는 입력 SHA-256, 선택 실행과 기준, 무효 사유, 경고, 각 그림의 사용 열과 SHA-256을 저장합니다. CSV 원문과 collect/params 원문은 dist로 복사하지 않습니다. 생성된 summary/manifest만 공개 배포됩니다.
