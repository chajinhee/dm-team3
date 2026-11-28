# 보안 B 리팩터링 검증

팀 `main`의 `common/`을 사용하며 팀 데이터 로더의 반환 순서에 맞춰 검색 실행기를 조정했다. `load_split()` 추가는 기존 `load_and_check()` 호출을 대체할 필요가 없다. 원본 `HAI_Project/run.py`와 팀 공통 모듈은 수정하지 않는다.

저장소 최상위에서 실행한다. `data`는 공식 HAI CSV가 있는 실제 폴더 경로로 바꿀 수 있다.

```text
python -m unittest discover -s tests -p "test_retrieval.py" -v
python HAI_Project/run.py --data data --out results_before
python -m experiments.run_retrieval --data data --out results/retrieval_check
python tools/compare_retrieval.py results_before results/retrieval_check
```

비교 범위는 `retrieval_queries.csv` 200행의 비시간 열, `data_manifest.json` 전체, `summary.json`의 `retrieval` 내 비시간 지표 5개다. 탐지·패턴 전용 파일 및 시간 측정값은 비교하지 않는다. `OK`가 출력되면 이 범위에서 일치한다. `results_before/`와 `results/retrieval_check/`는 재검증용이므로 커밋하지 않는다.

PR #5 리뷰에서는 macOS 재실행으로 위 비교 범위의 일치를 확인했다. 기대 검색 지표: MinHash Recall@5 0.641, LSH Recall@5 0.432, LSH 평균 후보 수 22.585.

`results/retrieval/`에는 보고서와 같은 기존 Windows 실행의 검색 CSV·원자료 해시 기록·검색 전용 요약을 보관한다. 이 스냅샷의 시간은 리팩터링 후 측정값이 아니며, 코드 분리에 따른 속도 변화로 해석하지 않는다.
