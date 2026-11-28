## PR #4 · 이상 탐지 리뷰 반영

- **강의 알고리즘**은 v1 재구성오차 PCA(`PCA-0.99`, 상위 32개 성분, test2 F1 .423)와 v1 K-means(k=16, F1 .338)로 제시합니다. 강의노트 기준은 PCA가 DM_06 PDF 58–59, 61쪽이고 K-means가 DM_05 PDF 35–36쪽입니다.
- **v6 추가 실험**의 `PCA-multi`는 전체 차원의 역공분산을 활용한 **시차 예측 잔차 탐지**로 명시했습니다. 후향 비교인 test2에서 F1 .557, 사건 검출 21/38, 정밀도 .767, 오경보 18.10초/정상h였습니다. v1 PCA는 13/38, 정밀도 .779, 오경보 11.24초/정상h였습니다. v6 K-means는 F1 .158, 오경보 580.29초/정상h였습니다.
- **평가 범위**를 구분했습니다. v1은 설정 고정 후 test2를 평가했습니다. v6 개발 실행은 test2를 읽지 않지만, 여러 실험 버전에서 test2를 확인했으므로 v6 수치는 후향 비교로 보고합니다. 독립적인 공격 일반화 검증에는 새 레이블 자료가 필요합니다.
- **저장소에서 재현 가능한 결과**만 비교표와 그래프에 넣었습니다. v1은 `HAI_Project/run.py`, v6는 `experiments/run_detection.py`로 다시 실행할 수 있습니다. 두 실행 결과를 대조한 범위와 AI 사용 기록도 업데이트했습니다.

[실행 방법과 결과](https://github.com/chajinhee/dm-team3/blob/feat/PCA-Kmeans/docs/DETECTION_README.md) · [재현 검증](https://github.com/chajinhee/dm-team3/blob/feat/PCA-Kmeans/results/detection/verification.json) · [AI 사용 기록](https://github.com/chajinhee/dm-team3/blob/feat/PCA-Kmeans/docs/AI_USE_detection.md)
