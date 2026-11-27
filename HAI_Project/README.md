# HAI 23.05 산업제어 시계열의 이상 탐지·패턴 해석·유사 사례 검색

> SCE331 Data Mining 팀 프로젝트. 영상 제외 실험·보고서 패키지.
> **제출 전 필수 수정:** 팀 번호·이름·학번·실제 기여·GitHub URL·제출 commit hash 및 수업 알고리즘 인정 근거. 이 저장소는 아직 GitHub에 업로드되지 않았다.

## Team
| 역할 제안(실제 수행 기록으로 교체) | 이름 | 학번 | 기여 |
|---|---|---|---|
| 이상 탐지 / 공정 해석 | [입력] | [입력] | [실제 수행 기록] |
| 연관 패턴 / PCY 검증 | [입력] | [입력] | [실제 수행 기록] |
| MinHash / LSH / 통합 | [입력] | [입력] | [실제 수행 기록] |

## Overview
센서·제어 변수만으로 공격 이상을 발견하고, 공격과 동반 관측되는 상태 조합과 유사 운전 창을 분석한다. 실험은 모두 실제 공개 HAI 23.05 데이터에서 실행했다. 탐지(PCA/K-means), 해석(Apriori/PCY), 검색(MinHash/LSH)을 단일 점수로 강제 비교하지 않는다. PCA는 단순 전처리가 아니라 독립 재구성오차 탐지기다. Apriori는 빈발 1·2항목집합까지로 제한한다. MinHash는 집합 서명 및 유사도 추정, LSH는 해당 서명의 후보 검색으로 평가한다. **이 여섯 구현이 수업에서 서로 다른 주요 알고리즘으로 인정되는지는 별도 확인해야 한다.** 특히 전처리·변환 알고리즘 합산 최대 1개 및 강의 슬라이드 5장 이상 요건을 확인할 것.

## Repository layout
```
run.py                  데이터 확보·검증·전처리·6개 알고리즘·평가
figures.py              결과 CSV에서 보고서 그림 재생성
build_report.py         보고서 PDF/DOCX/MD 재생성(추가 문서 라이브러리 필요)
test_pipeline.py        소규모 합성 입력의 단위 검증(관측 결과와 분리)
requirements.txt        핵심 실험 의존성
requirements-report.txt 문서/그림 생성 추가 의존성
SUBMISSION_CHECKLIST.md  제출 절차와 미해결 항목
AI_USE.md               AI 사용 내역과 검증 범위
REFERENCES.md           데이터·방법·소프트웨어 출처
results/                실제 결과 CSV/JSON 및 전체 시점 점수
figures/                재생성 가능한 PNG 그림
reports/                10쪽 보고서 PDF·DOCX·MD
results/summary.json    보안 B 로컬 실행 요약
 test_log.txt           단위 테스트 결과
```

## Data sources and acquisition
원제공자: H.-K. Shin, W. Lee, S. Choi, J.-H. Yun, B.-G. Min, *HAI security datasets*, 2023. https://github.com/icsdataset/hai
- 버전: HAI 23.05 (HAIEnd가 아님), 접근일 2026-11-16.
- **원본 데이터 저장소 commit:** `2a814cebc9a66b06c9e5cd545e2d72e65d383737`.
- 사용 파일: `hai-train1.csv`, `hai-test1.csv`, `hai-test2.csv`, `label-test1.csv`, `label-test2.csv`.
- 원본은 Git LFS. `run.py --download`는 고정 commit의 GitHub media 파일을 HTTP로 받는다. 라이브러리나 외부 실행 프로그램을 다운로드하지 않는다.
- SHA-256과 bytes는 `results/data_manifest.json`. 원자료는 ZIP에 넣지 않았다. 재배포·사용 조건은 원제공자 저장소/배포 페이지를 직접 확인한다. 프로젝트 코드에 데이터의 권리를 부여하는 라이선스를 임의로 붙이지 않는다.
- 총 280,800개 학습 행, 개발 54,000행, 최종평가 230,400행. timestamp 외 86변수. 세 측정 파일은 1초 연속, 결측 없음.

### Important label alignment
`label-test2.csv`는 230,400행이지만 timestamp가 분 단위라 226,559개 중복이 있다. timestamp merge를 하면 안 된다. 코드가 (1) 행 수 동일, (2) 측정 시각의 분 내림값과 레이블 시각이 **모든 행에서 일치**, (3) 측정 시계열은 중복 없이 1초 연속임을 assert한 뒤 **행 순서 대응**을 사용한다. 이는 공개 파일의 행 순서가 보존됐다는 가정이다. 분 내의 초 단위 순서를 독립 검증한 것은 아니며, 최종 제출 전 기술 문서/제공자 확인을 권한다. test1은 초 단위 timestamp가 전부 일치한다. summary의 label-test2 `gaps` 값은 분 단위 표현의 차이 개수이지 실제 센서 수집 누락이 아니다.

## Environment/setup
실행 확인 버전: Windows PowerShell / Python 3.13.0, NumPy 2.3.5, pandas 2.2.3. 하드웨어 사양은 기록하지 않아 하드웨어 독립 속도 우월성을 주장하지 않는다. 시간 측정은 동일 프로세스 내 상대 비교이며 재실행하면 달라진다.
```
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest -v test_pipeline
python run.py --data data --out results --download
```
데이터가 이미 있으면 `--download`를 빼면 된다. 다른 버전 파일을 같은 이름으로 넣지 말고 manifest를 대조한다. 데이터 다운로드 약 332 MB(10진 bytes 합), 메모리는 여러 행렬을 동시에 보관하므로 수 GB의 여유를 권한다.

그림·보고서 재생성:
```
python -m pip install -r requirements-report.txt
python figures.py
python build_report.py
```
문서 재생성에는 NanumGothic 한글 글꼴이 필요하다. 보고서는 PDF 10pt·15pt leading(1.5배), Word는 Times New Roman / NanumGothic 10pt·1.5배다. 수동 페이지 나눔을 사용하며, Word의 렌더러에 따라 페이지가 달라질 수 있어 제출 기준은 PDF다. build_report.py의 `FONT_DIR`을 설치한 Nanum 폰트 경로로 변경할 수 있다.

## Preprocessing / leakage policy
- train1 앞 60%(168,480초)에서 median·mean·std와 모델을 적합, 뒤 40%(112,320초)는 정상 임계값 calibration.
- 학습 상수 변수 21개는 제거하지 않고 std=1로 둔다. 이후 값 변화는 남지만 원단위 크기의 영향을 받는 한계가 있다.
- 모든 탐지 입력에서 timestamp·label 제외. test1만 하이퍼파라미터 선택, test2는 결과 산출용. test2 결과를 보고 설정을 바꾸지 않았다.
- 데이터 누출을 막기 위해 랜덤 행 단위 train/test 분할을 사용하지 않는다. 이후 재실험에서 test2로 반복 튜닝하면 test2는 더 이상 보류 평가가 아니다.

## Algorithms and settings
1. PCA: 공분산 고유분해. 누적 설명분산 .90/.95/.99, 점수=변수당 재구성 SSE. 독립 이상 탐지.
2. K-means: Lloyd 반복 최대 40회, 변화량 <1e-5 종료, seed=331. 학습 앞 60%에서 균등 무복원 최대 30,000행, 무작위 중심 초기화 1회. k=4/8/16. 점수=가장 가까운 중심까지 제곱거리. 최적 전역해나 k-means++를 사용했다고 주장하지 않는다.
3. Apriori-pairs: 최소 지지도 .01/.02/.05. 단일 항목 빈도에 의한 downward closure 가지치기 후 관측 후보쌍 정확 집계. 3항목 이상 생성하지 않는다.
4. PCY: 위와 동일 입력·최소 지지도, 1,024 해시 버킷. 1차 패스 버킷 빈도 -> 빈발 버킷 필터 -> 정확 후보쌍 집계. 모든 비교에서 Apriori 결과와 assert로 동일성 확인.
5. MinHash: 64개 affine modular hash, prime=2,147,483,647, seed=331. 서명 일치율로 유사도 근사. 독립 무작위 순열의 정확 구현이 아닌 실용적 근사 해시족이다.
6. LSH: 16 bands × 4 rows, 같은 band 서명이 있는 갤러리 창을 합집합 후보로 검색 후 정확 Jaccard 재정렬. 후보 부족 시 전수검색으로 채우지 않는다.

탐지 임계값: 정상 calibration 점수의 .95/.975/.99/.995/.999 분위수. 각 계열의 모델 설정과 분위수를 test1 F1 최대 기준으로 선택, 동점은 모델 이름과 작은 분위수 순. 전부 고정한 후 test2 보고.

### Transactions / rules
연속 60초 비중첩 창에서 각 변수 평균 z를 계산. |평균 z|>=1.5인 변수 중 절댓값 상위 8개에 HIGH/LOW 부호를 부여한다. 이는 정상 대비 상태이지 물리적 안전 기준이 아니다. 개발 900창, 최종 3,840창. 창 레이블은 공격 초가 하나라도 있으면 1. test1에서 지지도 2% 빈발쌍을 만들고 `pair => attack_window` confidence/lift 순으로 10개를 고정해 test2에서 검증한다. 이 단계는 레이블을 쓰는 **사후 연관 분석**이며, 비지도 탐지기의 입력 또는 인과적 공격 원인 추정이 아니다. 정상/공격을 섞어 mining했다. 원래 센서 쌍 간 방향 규칙 전부가 아니라 센서쌍을 전건, 공격창을 후건으로 한 규칙이다.

### Retrieval
갤러리=test1의 900창, 질의=test2 비어 있지 않은 창 중 seed=331로 200개 무복원 추출. 정확 Jaccard 전수검색 Top-5를 정답 이웃으로 두고 MinHash/LSH Recall@5 평가. 동점은 갤러리 인덱스 오름차순. 동일 집합 중복·유사도 동점이 있어 같은 유사도 다른 이웃을 반환해도 불일치로 계산하는 엄격한 지표다. 공격 유형 정답 검색 성능과는 다르다. 서명·인덱스 구축은 질의 시간에서 제외하고 별도 기록; MinHash/LSH 질의 시간에는 질의 서명 계산 포함. 전체 관측 창을 사용해 검색 성능을 평가했으며, 자동 공격 알람과 검색을 연동한 운영 시스템은 구현하지 않았다.

## Evaluation / main results
`results/summary.json`과 CSV가 기준이다. Point adjustment 없이 초 단위 Precision/Recall/F1. 이벤트는 label=1 연속 구간, 그 안의 1초라도 탐지되면 검출. 지연은 **검출된 이벤트에서만** 최초 탐지 지연 중앙값. 오경보는 `(prediction=1 & label=0)` 연속 구간 개수 / 정상 시간(hour), 공격 경계에서 오경보 구간이 분할될 수 있다.

| test2 모델 | Precision | Recall | F1 | 검출 공격구간 | 정상 1시간당 오경보 구간 |
|---|---:|---:|---:|---:|---:|
| Z-score | .450 | .301 | .361 | 31/38 | 30.341 |
| PCA | .779 | .290 | .423 | 13/38 | .373 |
| K-means | .378 | .305 | .338 | 29/38 | 29.984 |
| Always normal | .000 | .000 | .000 | 0/38 | .000 |

PCA의 test1 F1 .754가 test2 .423으로 하락. 최종 평가에서 PCA는 오탐이 적지만 25개 공격 구간을 놓쳤다. 단순 기준 모델보다 모든 관점에서 우월하다고 해석하지 않는다.
- 지지도 2%: Apriori/PCY 빈발쌍 188개로 동일; 관측 집계 후보 586→298개, 중앙값 시간 7.932→19.222 ms. PCY 속도 향상 실패.
- MinHash Recall@5 .641, 평균 0.280 ms; LSH .432, 0.117 ms; exact 1.122 ms. 후보 평균 22.585/900. 작은 갤러리·단일 회차 질의 측정이므로 실서비스 확장성 근거가 아니다.
- 원시 데이터·분할·특징 통계·그리드·전체 점수·이벤트·규칙·질의별 결과가 results에 있다.

## External code / AI use
실험 핵심 6개 알고리즘은 `run.py`의 프로젝트용 구현(생성형 AI 지원)이다. 외부 저장소의 알고리즘 코드를 복사하지 않았고 NumPy/pandas 등의 라이브러리를 사용했다. AI 작성 기여를 팀원의 독자적 수작업으로 표시하지 않는다. AI_USE.md 및 REFERENCES.md 참조. AI의 실제 수업 사용 허용 범위는 교수 정책 확인 필요.

## 영문 글꼴 주의
PDF의 영문에는 Times New Roman 대신 메트릭 호환 Liberation Serif가 포함되어 있다. Word 수정본에는 Times New Roman을 지정했다. 가이드라인의 영문 글꼴 요구를 정확히 맞추려면 Times New Roman과 NanumGothic이 있는 환경에서 Word 파일을 PDF로 내보내고 8–10쪽·표/그림 잘림 여부를 다시 확인한다. 현재 PDF를 서식 요건까지 완전히 충족한 최종 제출본으로 간주하지 않는다.

## 로컬 결과 기준
보고서, 결과 14개와 그림은 모두 보안 B 팀원의 동일한 Windows 재실행을 기준으로 한다. 초 단위 점수 CSV 3개는 재생성을 위해 내용 변경 없이 gzip으로 포장했다. 검색 시간은 이 실행의 비교값이며 색인 구축 42.617 ms는 별도다. 초기 실행 로그와 영상, HAI 원본 데이터는 첨부하지 않았다.
