# dm-team3: HAI 23.05 산업제어 시계열의 공격 이상 탐지와 패턴 분석

데이터마이닝(SCE331) 3조 팀 프로젝트 저장소입니다.

> 이 README 는 보안A 파트(Apriori · 연관 규칙 · PCY)까지 채운 상태입니다.

## Overview

산업제어 시스템 테스트베드의 센서·제어 신호(HAI 23.05)만으로, 네트워크 로그 없이 공격을 발견하고 설명할 수 있는지 분석합니다.

| 파트 | 알고리즘 | 역할 | 담당 |
|---|---|---|---|
| 이상 탐지 | PCA, K-means | 정상 운전 학습 후 이상 점수 | 엄지혜 |
| 패턴 해석 | Apriori, 연관 규칙, PCY | 공격 창과 함께 나타나는 센서 상태 조합 | 차진희 |
| 사례 검색 | MinHash, LSH | 유사한 과거 운전 창 검색 | 최지혜 |

## Team

| 이름 | 학번 | 담당 |
|---|---|---|
| 엄지혜 | [입력] | 이상 탐지 (PCA, K-means) |
| 차진희 | [입력] | 패턴 해석 (Apriori, 연관 규칙, PCY) |
| 최지혜 | [입력] | 사례 검색 (MinHash, LSH) |

## Repository layout

```
common/                   팀 공통: 설정(config), 데이터 확보·검증(data), 정규화(preprocess), 60초 창(windows)
HAI_Project/              팀원 원본 코드 (정리 중, docs/REFACTOR_GUIDE.md)
patterns/                 보안A: 알고리즘 구현
  apriori.py              Apriori (join + prune, 크기 k 까지 단계적 확장)
  rules.py                연관 규칙 (support · confidence · lift)
  pcy.py                  PCY (CRC32 쌍 해시, 빈발 버킷 비트맵, 후보 수 통계)
  transactions.py         센서 시계열 → 60초 창 HIGH/LOW 거래, 레이블 정렬 검사
experiments/
  run_patterns.py         보안A 실험 E0~E3 (dev / final 단계)
  make_figures.py         결과 CSV → 그림 4개
tests/                    단위 테스트 38개 (강의자료 예제·작은 합성 입력, 실제 데이터 아님)
results/patterns/         실험 결과 CSV·JSON, figures/ 그림
docs/
  DATA_HAI.md             데이터 출처 · 버전 · SHA-256 · 다운로드 명령
  AI_USE_apriori_pcy.md   보안A 파트 AI 사용 기록 (파일별)
  report_securityA_draft.md  보고서 보안A 파트 초안
  REFACTOR_GUIDE.md       팀 코드(run.py) 파트별 정리 가이드
tools/compare_results.py  리팩터링 전후 결과 비교 (실행 시간 열 제외)
data/                     원본 데이터 (저장소에 포함하지 않음, .gitignore)
[팀 입력]                  이상 탐지 · 사례 검색 파트
```

**직접 작성한 코드와 외부 코드의 구분.** 모든 알고리즘은 프로젝트용으로 구현했으며 외부 저장소의 알고리즘 코드를 복사하지 않았습니다. 사용한 라이브러리는 NumPy, pandas, matplotlib 뿐입니다. 파일별 작성자(본인 / AI 지원)는 각 파일 상단과 `docs/AI_USE_apriori_pcy.md` 에 적었습니다.

## Data sources and acquisition

- 원제공자: H.-K. Shin, W. Lee, S. Choi, J.-H. Yun, B.-G. Min, *HAI security datasets*. https://github.com/icsdataset/hai
- 버전: **HAI 23.05**, 원본 저장소 고정 commit `2a814cebc9a66b06c9e5cd545e2d72e65d383737`
- 사용 파일: `hai-train1.csv`, `hai-test1.csv`, `hai-test2.csv`, `label-test1.csv`, `label-test2.csv` (합계 약 332 MB)
- 원본은 재배포하지 않습니다. 아래 명령으로 `data/` 에 받습니다. 파일별 SHA-256 은 [docs/DATA_HAI.md](docs/DATA_HAI.md) 에 있습니다.

```powershell
$c = "2a814cebc9a66b06c9e5cd545e2d72e65d383737"
foreach ($f in "hai-train1.csv","hai-test1.csv","hai-test2.csv","label-test1.csv","label-test2.csv") {
  curl.exe -sSfL -o "data\$f" "https://media.githubusercontent.com/media/icsdataset/hai/$c/hai-23.05/$f"
}
Get-FileHash data\*.csv -Algorithm SHA256
```

`label-test2.csv` 는 timestamp 가 분 단위로만 기록되어 있어 timestamp 로 합칠 수 없습니다. 코드는 행 수, 분 단위 시각, 1초 연속성을 검사한 뒤 행 순서로 대응시킵니다 (`patterns/transactions.py` 의 `load_labels`).

## Environment / setup

확인한 환경: Python 3.14.4, numpy 2.5.5, pandas 3.1.1, matplotlib 3.11.2, Windows 11.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Reproducing the main results (보안A 파트)

모든 명령은 저장소 최상위 폴더에서 실행합니다.

```powershell
# 1. 단위 테스트 (38개)
python -m unittest discover tests

# 2. 개발 단계: train1 · test1 만 사용 (약 5분)
python -m experiments.run_patterns --stage dev

# 3. 최종 단계: test1 로 고정한 규칙을 test2 에서 한 번 평가 (약 15초)
python -m experiments.run_patterns --stage final

# 4. 그림 4개 재생성
python -m experiments.make_figures
```

| 출력 | 내용 |
|---|---|
| `e0_transactions.csv`, `e0_final_transactions.csv` | 거래 데이터 기술 통계 |
| `e1_dev_summary.csv`, `e1_dev_rules.csv` | 규칙 선택 기준 비교 (test1 앞 절반 선택 → 뒤 절반 검증) |
| `e1_final_summary.csv`, `e1_final_rules.csv` | test1 로 고정한 규칙의 test2 결과 |
| `e2_pcy.csv` | PCY 대 Apriori: 후보 수, 추정 메모리, 시간 (결과 동일성 assert) |
| `e3_sensitivity.csv` | 창 크기 · 기준값 · 항목 수 민감도 (test1 안에서만) |
| `figures/fig1~fig4` | 보고서 그림 |
| `run_info_*.json` | 설정, 라이브러리 버전, 실행 시각 (무작위 요소가 없어 seed 없이도 결과가 같음) |

**설정과 누출 방지.** 60초 창, |z| ≥ 1.5, 창당 최대 8개 항목, 최소 지지도 1%, 고정 규칙 10개, 주 선택 기준 `coverage` 는 test2 실행 전에 `experiments/run_patterns.py` 상단에 고정했습니다. 레이블은 거래 생성에 쓰지 않고, 규칙 마이닝 단계에서만 `ATTACK` 항목으로 붙입니다. 실행 시간은 실행마다 달라집니다.

**보안A 주요 결과 (test2).** 주 기준(coverage, 전건 2항목 이하) 규칙의 창 단위 F1 0.223 (baseline 0.083, lift 기준 0.084), 정상 1시간당 오경보 2.9창, 공격 구간 38개 중 13개 검출. PCY 는 24개 조건 모두에서 Apriori 와 같은 결과를 내고 후보를 5.9~74.1% 줄였지만, 추정 메모리 이득은 1개 조건에서만 나타났습니다.

[팀 입력: 이상 탐지 · 사례 검색 파트 실행 방법]

## References and external code

[docs/report_securityA_draft.md](docs/report_securityA_draft.md) 의 참고문헌과 [팀 입력: 팀 참고문헌 파일] 을 참고하세요.

## AI-use statement

보안A 파트는 Anthropic Claude Code (claude-opus-5-5) 의 도움을 받았습니다 (2026-11-25~27). 파일별 내역과 검증 방법은 [docs/AI_USE_apriori_pcy.md](docs/AI_USE_apriori_pcy.md) 에 있습니다. [팀 입력: 다른 파트의 AI 사용]
