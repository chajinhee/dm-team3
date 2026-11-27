# PCA와 K-means 코드의 AI 사용 기록

OpenAI Codex를 사용해 원본 HAI_Project 코드의 감사, v2~v6 실험 설계와 실행, 코드 작성, 탐지 모듈 분리, 주석과 그래프 및 해석을 작성했다. 이번 분리 작업에는 현재 세션 모델 gpt-6.1-sol을 사용했다. 이전 실험은 원본 AI_USE.md에 기록된 모델과 도구를 사용했다.

| 파일 | 작성 지원 범위 |
|---|---|
| detection/pca.py | 공분산 고유분해, 시차 조건부 잔차와 점수 보정 구현 |
| detection/kmeans.py | 원본 Lloyd 반복 보존, k-means++ 초기화와 여러 seed 비교 |
| detection/models.py, postprocess.py, selection.py, settings.py | 학습 조립, 인과적 경보 후처리, 개발 설정 선택 |
| detection/datasets.py, data_hashes.json | 고정 해시, 단계별 읽기, 추가 정상 자료의 독립 파일 검사 |
| experiments/run_detection.py | 개발·평가 분리, 동결 및 결과 저장, 원 실험과 수치 대조 |
| experiments/make_figures_detection.py | 저장 결과의 정밀도–재현율·버전·후보 비교 그래프 |
| tests/test_detection.py | 경보 소급·파일 경계·동점 AP·오경보 지표 회귀 검사 |
| docs/ 및 results/detection/ | 사용법, 실험 기준, 실행과 결과 해석 |

common/의 코드는 main에 병합된 진희님 모듈을 불러온다. 이 업로드의 AI 작성 범위를 팀원의 독자적 구현으로 표시하지 않는다. 제출 담당자는 실제로 검토한 파일, 확인 날짜, 직접 변경한 부분을 아래에 기록한다.

- 팀원 검토자 및 날짜 —
- 직접 확인한 알고리즘·함수 —
- 직접 재실행한 명령과 환경 —
- 강의 알고리즘 인정 기준과 대조한 내용 —

로컬 자동 검증은 v6 후보 그리드 1,088행, 단독 탐지 평가 6행, 사건표 114행, PR 좌표의 수치 대조를 포함한다. 최종 검증 기록은 results/detection/verification.json에 있다. 사람의 독립 검토와 과제 적격성 확인은 팀이 실제 수행한 범위대로 기록한다.
