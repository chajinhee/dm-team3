"""팀 공통 설정값.

원 코드: HAI_Project/run.py 8–10줄 (최지혜 님 작성, BAZE Mindlogic 생성 코드).
정리: 차진희, Claude Code 지원 (2026-11-27). 값은 바꾸지 않았다.
"""

# 무작위 요소의 seed. K-means 표본·초기 중심, MinHash 해시 계수, test2 질의 추출에서
# 각자 np.random.default_rng(SEED) 를 "새로" 만들어 쓴다 (한 생성기를 공유하면 결과가 달라짐).
SEED = 331

# HAI 공식 저장소(https://github.com/icsdataset/hai) 의 고정 commit. 팀 전체가 같은 파일을 받도록 고정.
HAI_COMMIT = "2a814cebc9a66b06c9e5cd545e2d72e65d383737"

# 사용하는 HAI 23.05 파일 (train1: 정상 학습, test1: 개발·설정 선택, test2: 최종 평가)
HAI_FILES = ["hai-train1.csv", "hai-test1.csv", "hai-test2.csv", "label-test1.csv", "label-test2.csv"]

# 센서·제어 변수 수 (timestamp 제외)
N_VARIABLES = 86

# train1 중 정규화 기준(평균·표준편차)과 탐지 모델 적합에 쓰는 앞부분 비율.
# 뒤 40% 는 정상 임계값 보정(calibration) 용으로 남긴다.
FIT_FRACTION = 0.6

# 학습 구간에서 표준편차가 이 값보다 작으면 "상수 변수" 로 보고 표준편차를 1 로 둔다 (0 으로 나누기 방지).
CONSTANT_STD_EPS = 1e-10
