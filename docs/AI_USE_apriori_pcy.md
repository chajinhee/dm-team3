# AI 사용 기록: Apriori / PCY 파트 (보안A)

보고서 AI-use disclosure 작성용 원자료. 작업할 때마다 한 줄씩 추가한다.

- 도구: Claude Code (Anthropic), 모델 Claude Opus 5.5 (`claude-opus-5-5`)
- 원칙: 알고리즘 함수 본문은 본인이 작성. AI는 개념 설명, 함수 뼈대(서명·docstring), 테스트 작성, 코드 리뷰만 담당.

| 날짜 | AI가 한 일 | 영향받은 파일 | 본인이 검증·수정한 내용 |
|---|---|---|---|
| 2026-11-25 | 과제 안내문·팀 기획안·팀원 구현 분석, 개선 방향 제안 | (없음) | |
| 2026-11-25 | Apriori 함수 뼈대(서명·docstring·TODO) 작성 | `patterns/apriori.py` (본문은 본인 작성) | |
| 2026-11-25 | Apriori 테스트 작성 (교과서 예제, brute-force 대조) | `tests/test_apriori.py` | 교과서 예제 정답을 손으로 검산: [ ] |
| 2026-11-25 | 함수별 빈칸 채우기 힌트 제공. `count_singletons`·`generate_candidates`·`count_candidates`는 본인이 빈칸을 채우고 AI가 버그 위치를 지적(import 누락, prune 부분집합 크기). `apriori` 본문의 while 루프 빈칸 3곳(함수 호출 인자, `k = k + 1`)은 AI가 답을 알려줌 | `patterns/apriori.py` | 테스트 8개 실행으로 확인 |
| 2026-11-25 | 본인 요청으로 코드 주석 추가 (코드 동작 변경 없음), 파일 상단 작성자 표기 수정 | `patterns/apriori.py` | 주석 추가 후 테스트 8개 재통과. 주석 내용 직접 읽고 확인: [ ] |
| 2026-11-25 | 연관 규칙 생성: 뼈대(서명·docstring·공식)에 더해 본인 요청으로 **함수 본문 3개와 주석 전체를 AI가 작성** | `patterns/rules.py` | 테스트 9개 통과. 코드·주석 직접 읽고 이해 확인: [ ] |
| 2026-11-25 | 규칙 생성 테스트 작성 (교과서 예제 수치, brute-force 대조) | `tests/test_rules.py` | 예제 confidence·lift 손 계산 검산: [ ] |
| 2026-11-25 | PCY: 뼈대(서명·docstring)·`pair_hash`에 더해 본인 요청으로 **함수 본문 4개와 주석 전체를 AI가 작성** | `patterns/pcy.py` | 테스트 9개 통과 (Apriori 결과와 동일). 코드·주석 직접 읽고 이해 확인: [ ] |
| 2026-11-25 | HAI 23.05 다운로드 실행·SHA-256 대조, 데이터 확보 기록 문서 작성 | `docs/DATA_HAI.md`, `requirements.txt` | 해시가 팀원 기록과 일치함을 확인 |
| 2026-11-25 | 본인 요청으로 **실험 코드 전체를 AI가 작성**: 거래 변환 모듈·단위 테스트, 실험 스크립트(E0 거래 통계, E1 공격 규칙 선택·검증, E2 PCY 대 Apriori, E3 민감도) | `patterns/transactions.py`, `tests/test_transactions.py`, `experiments/run_patterns.py` | 단위 테스트 6개 통과. 실험 설계(데이터 분할·지표)와 코드 직접 검토: [ ] |
| 2026-11-25 | 개발 단계 1차 결과 해석(lift 순 선택의 과적합, PCY 메모리 조건) 및 개선 방향 제안 | (없음) | 결과 CSV 와 해석이 일치하는지 직접 확인: [ ] |
| 2026-11-26 | 본인 요청으로 규칙 선택 기준 2개(coverage, novel) 추가 구현. test2 는 보지 않은 상태에서 test1 결과만 근거로 변경 | `experiments/run_patterns.py` | |
| 2026-11-26 | 세 기준 개발 단계 비교 해석. **test2 실행 전 주 기준을 coverage 로 결정**(본인 승인), 코드에 `PRIMARY_STRATEGY` 로 기록 | `experiments/run_patterns.py` | |
| 2026-11-26 | test2 최종 평가 1회 실행 (설정·기준 사전 고정) | `results/patterns/*final*` | |
| 2026-11-25 | PCY 테스트 작성 (Apriori 결과와 동일성, 후보 수 감소 확인) | `tests/test_pcy.py` | |
