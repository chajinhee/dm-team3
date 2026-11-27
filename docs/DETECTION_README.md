# PCA와 K-means 탐지 파트

이 코드는 원본 HAI_Project를 바탕으로 개선한 v6 실험 중 탐지 부분을 분리한 것이다. 두 탐지기를 각각 평가하고, 최종 경보 모델로 PCA 기반 시계열 잔차 탐지를 채택한다. 2026-11-27 main에 병합된 공통 모듈 PR #2, commit 22b92fe18650893f0b12a00a04e70ebaa1586cc8에서 실행을 확인했다.

원본의 폴더 분리 작업에 비해 알고리즘과 설정이 달라졌으므로 feat/detection-v6 PR에서 개선 범위를 검토한다. 원본 동작은 HAI_Project/run.py로 비교할 수 있다.

## 파일과 공통 모듈

| 파일 | 내용 |
|---|---|
| detection/pca.py | 시차 0·1·10초 조건부 잔차, 고유분해, 정상 99분위 점수 보정 |
| detection/kmeans.py | 원본 Lloyd와 k-means++, 거리 계산 |
| detection/models.py | 파일별 정상 60% 적합·40% 보정, 여러 seed 중 정상 inertia 선택 |
| detection/postprocess.py | 과거만 쓰는 지수평활, 연속 초과 확인, 유지 |
| detection/selection.py, settings.py | 후보 그리드와 오경보 제약 및 PR 곡선 계산 |
| detection/datasets.py, data_hashes.json | 단계별 원자료 읽기·SHA-256·초/분 레이블 대응 검사 |
| detection/metrics.py | 초 단위 P/R/F1·AP와 사건 검출·경보 지연·오경보 횟수 및 시간 |
| experiments/run_detection.py | fetch, develop, final 실행 |
| experiments/make_figures_detection.py | 탐지 전용 그래프 3개 |
| tests/test_detection.py | 분리 시점에 추가한 회귀 검사 4개 |

common.config의 버전·seed·적합 비율과 common.preprocess의 fit_scaler·transform을 사용한다. 확대 학습에서는 train1과 train2 각 파일 앞 60%를 합쳐 Scaler를 적합한다. 공통 함수에 fit_fraction=1.0으로 전달하는 배열 자체가 두 정상 파일에서 먼저 분리한 적합 구간이다.

common.data.load_and_check는 다섯 원본 파일을 한꺼번에 읽는다. 개발에서 test2를 읽지 않도록 탐지 데이터 어댑터는 파일별로 검증한다. 추가 train2·train4는 고정 해시와 센서 열 및 초 단위 연속성을 확인한다.

## 실행

명령은 저장소 최상위에서 실행한다. Python 3.13.2, NumPy 2.2.3, pandas 2.3.3 환경에서 원 실험과 수치 일치를 확인했다. 팀의 다른 환경에서 재실행한 기록은 별도로 추가한다.

~~~sh
python -m pip install -r requirements-detection.txt
python -m experiments.run_detection --stage fetch
python -m unittest discover tests
python -m experiments.run_detection --stage develop
python -m experiments.run_detection --stage final
python -m experiments.make_figures_detection
~~~

fetch는 공식 고정 commit에서 train1·2·4, test1·2 및 레이블을 받는다. develop은 train1과 test1만 읽는다. final은 train1~2로 정상 모델을 재적합한 뒤 고정 설정으로 test2와 정상 train4를 평가한다. train3는 이 코드의 학습 범위에 포함되지 않는다. 원자료 사용량은 약 600MB다.

별도 폴더 결과를 쓰려면 develop과 final에 같은 --out 경로를 준다. 코드를 바꾸면 설정 파일의 해시 검사에서 차이를 확인한다. 숫자에 영향을 주는 변경 후에는 개발부터 다시 수행하고 이전 결과와 구분해 기록한다. 기존 test2는 여러 버전에서 반복 확인했으므로 후속 비교 데이터로 기술한다.

## 선택된 설정과 결과

| 모델 | 설정 |
|---|---|
| PCA | 시차 0·1·10초 최대 점수, span 10, 확인 1초, 유지 6초, 보정 99.8분위 × 0.95 |
| K-means | k=32, 일반 제곱거리, span 10, 확인 1초, 유지 6초, 보정 95분위 × 0.90, 최종 seed 331 |

test1 앞 구간의 1,088개 후보와 뒤 구간의 단독 모델별 배수 7개를 같은 오경보 제약에서 비교했다. 선정 기준은 정상 1시간당 오경보 1회와 오탐 시간 60초 초과 최소, 초 단위 F1과 사건 재현율의 조화평균 최대 순이다. 전체 설정은 selection.json, 재적합 후 보정 임계값은 applied_settings.json에 있다. 실제 경보 기준은 보정 임계값에 모드 배수를 곱한다.

| test2 모델 | 정밀도 | 재현율 | F1 | 사건/38 | 오경보/정상h | 오경보 초/정상h |
|---|---:|---:|---:|---:|---:|---:|
| 원본 PCA | .779 | .290 | .423 | 13 | .373 | 11.24 |
| v6 PCA | .767 | .437 | .557 | 21 | .681 | 18.10 |
| 원본 K-means | .378 | .305 | .338 | 29 | 29.984 | 68.40 |
| v6 K-means | .096 | .450 | .158 | 28 | 19.671 | 580.29 |

PCA는 원본의 13건을 유지하고 8건을 더 찾았다. 정밀도 하락과 오경보 증가는 남는다. K-means의 최신 설정은 원본보다 F1과 오경보 지속시간이 나빠 최종 경보 결정에 채택하지 않았다.

train4 정상 55시간에서 v6 PCA의 오경보는 .327회/h와 7.29초/h였다. v5의 train1~2 PCA는 test2에서 24건을 찾았고 F1 .539, 오경보 1.022회/h와 41.68초/h였다. v6는 그중 3건을 놓치는 대신 오경보와 정밀도를 개선했다. 모든 지표의 최고값이 한 설정에 모이지 않는다.

version_history.csv에는 과거 대표 운영점도 수록했다. v5의 train1~3 행은 test2 이후의 정상 기록을 포함한 후향 비교다. v2 K-means는 3초 지속을 확인한 뒤 첫 초까지 표시하는 과거 평가 방식이므로 온라인 경보와 지연 해석에 이 조건을 적는다.

PCA 기반 잔차 탐지는 공분산 고유분해에 선형 시계열 예측을 결합했다. 수업의 주요 알고리즘 인정 범위는 팀이 강의 자료와 대조한다. test2 초 단위 레이블은 분 안에서 행 순서가 보존됐다는 가정을 따른다. AI 사용 내역은 AI_USE_detection.md에 있다.
