# 보안 B 리팩터링 검증

공식 HAI 23.05로 새 실행기를 실행했다. 기존 Windows 로컬 결과와 원자료 해시 및 검색 CSV 200행의 모든 비시간 열이 정확히 일치했다. 검색 요약의 공통 비시간 필드도 일치했다. 검색 단위 테스트 4개 통과. 새 실행시간은 보고서 수치로 대체하지 않는다.

`common/`은 독립 실행 및 검증용 공통 모듈이다. 팀 main에 이미 공통 코드가 있으면 덮지 말고 함수 계약을 대조해 실험 실행기의 호출부를 조정한 후 다시 검증한다. 원본 `HAI_Project/`는 수정하지 않는다. 강의자료 페이지 및 실제 팀원 검토는 PR 전 보완한다.

```powershell
python -m unittest discover -s tests
python HAI_Project/run.py --data data --out results_before
python -m experiments.run_retrieval --data data --out results/retrieval
python -m tools.compare_results results_before results/retrieval
```

팀 main의 common/을 반영하고, 팀 데이터 로더의 반환 형식에 맞게 보안 B 실행기의 호출부를 수정했다. 단위 테스트 4개를 통과했으며, 공식 HAI 데이터로 재실행한 결과 200개 질의의 실행시간 열을 제외한 결과가 기존 Windows 실행본과 일치했다. 검색 알고리즘과 설정값은 변경하지 않았다.