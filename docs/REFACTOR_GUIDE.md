# 코드 정리(리팩터링) 가이드: `run.py` → 파트별 파일

> 작성: 보안A, 2026-11-27 (초안은 Claude Code 로 작성 후 검토). 팀 논의로 바꿀 수 있어요.
> 목표 완료일: **2026-12-01** (보고서·발표 준비 시간 확보)

## 1. 왜 정리하나요

교수님 rubric 은 보고서와 GitHub 코드를 **함께** 채점해요.

| rubric 항목 | 지금 `run.py` 의 문제 | 정리하면 |
|---|---|---|
| Technical method descriptions (15점): 설명이 코드와 일치하는가 | 6개 알고리즘이 173줄 한 파일에 압축돼 있어 대응 부분을 찾기 어려움 | 보고서 절 ↔ 파일이 1:1 로 대응 |
| GitHub submission (10점): 모든 알고리즘·평가·실행 단계 | 실행 단계가 하나로 뭉쳐 있음 | 파트별 실행 명령, 파트별 결과 폴더 |
| 기여 명확성 | 한 파일이라 담당이 안 보임 | 폴더 = 담당 파트 |
| AI 공개 (10점): 파일별로 구체적으로 | 파일 단위 구분 불가 | 파일 맨 위에 작성자·AI 사용 표기 |

## 2. 절대 지킬 규칙 3가지

1. **결과가 바뀌면 안 돼요.** 이번 작업은 "정리"만 해요. 알고리즘, 설정값, seed, 데이터 분할, 임계값 선택 규칙은 그대로 둬요.
   보고서 숫자가 현재 결과 기준이고, 동작이 바뀌면 test2 를 다시 쓰게 되는 문제가 생겨요.
   → 4절의 검증 스크립트로 **수정 전후 결과가 같음**을 확인해요.
2. **seed 를 쓰는 세 곳은 지금처럼 각각 새로 만들어요.** 현재 `run.py` 는 아래 세 곳에서 `np.random.default_rng(331)` 을 **각자 새로** 만들어요. 하나로 합치거나 순서를 바꾸면 결과가 달라져요.
   - `kfit` (K-means 표본 추출·초기 중심)
   - `retrieval` (MinHash 해시 계수 a, b)
   - main 166–167줄 (test2 질의 200개 추출)
3. **정리 작업은 main 브랜치에 바로 올리지 않아요.** 새 브랜치에서 작업하고 PR 로 올려요 (5-2).
   예외는 원본 `HAI_Project/` 를 수정 없이 올리는 첫 commit 하나뿐이에요 (5-1).

## 3. 목표 구조와 `run.py` 대응표

```
common/        공통: 설정, 데이터 확보·검증, 정규화, 60초 창
detection/     전자공학: PCA, K-means, Z-score baseline, 탐지 지표
patterns/      보안A: Apriori, 연관 규칙, PCY, 거래 변환        ← 이미 완료
retrieval/     보안B: MinHash, LSH, 검색 평가
experiments/   실행 스크립트 (파트별), 그림
tests/         파트별 단위 테스트
tools/         compare_results.py (리팩터링 검증)
results/       detection/, patterns/, retrieval/
```

줄 번호는 `HAI_Submission_Local` (11/27) 의 `run.py` 기준이에요. 5-1 에서 `HAI_Project/run.py` 로 올라가는 파일과 같아요.

| 지금 `run.py` (줄) | 내용 | 옮길 곳 | 담당 |
|---|---|---|---|
| 8–10 `SEED`, `COMMIT`, `FILES` | 설정 상수 | `common/config.py` | 공통 |
| 11–22 `acquire` | 고정 commit 에서 데이터 다운로드 | `common/data.py` → `download_hai()` | 공통 |
| 92–108 (main) | 파일 읽기, SHA-256, 1초 연속·결측·레이블 정렬 검사 | `common/data.py` → `load_and_check()` | 공통 |
| 109–115 (main) | train1 앞 60% 로 median·mean·std, 상수 변수 std=1, `transform`, test1·test2 변환, 레이블 | `common/preprocess.py` → `fit_scaler()`, `transform()` | 공통 |
| 116 (main) | `features.csv` 저장 | `experiments/run_detection.py` | 전자공학 |
| 45–51 `transactions` | 60초 창 → 정수 항목 집합 (MinHash/LSH 입력) | `common/windows.py` → **출력(정수 항목) 그대로** | 공통 |
| 24–26 `intervals`, 27–33 `metrics` | 공격 구간, P/R/F1·이벤트·지연·오경보 | `detection/metrics.py` | 전자공학 |
| 34–35 `sqdist`, 36–44 `kfit`, 125–128 (main) | K-means (Lloyd), k=4/8/16 점수 | `detection/kmeans.py` | 전자공학 |
| 118, 121–124 (main) | PCA 고유분해, 설명분산 .90/.95/.99, 재구성오차 점수 | `detection/pca.py` | 전자공학 |
| 120 (main) | Z-score 최대 \|z\| 점수 | `detection/zscore.py` | 전자공학 |
| 129–145 (main) | 분위수 임계값 그리드, test1 F1 로 선택, test2 평가, 이벤트 CSV, Always normal | `experiments/run_detection.py` | 전자공학 |
| 67–69 `signature`, 70–71 `jacc` | MinHash 서명, Jaccard | `retrieval/minhash.py` | 보안B |
| 72 `topk`, 73–88 `retrieval` | LSH band 후보 검색, 재정렬, Recall@5 | `retrieval/lsh.py`, `retrieval/search.py` | 보안B |
| 166–168 (main) | 질의 추출, 검색 실행 | `experiments/run_retrieval.py` | 보안B |
| 169–172 (main) | `summary.json`, `data_manifest.json` | 각 실행 스크립트가 자기 결과 폴더에 저장 | 각자 |
| **53–65 `mine_pairs`, 146–165 (main)** | **Apriori-pairs, PCY, 쌍 ⇒ 공격 규칙** | **삭제** (→ `patterns/`, `experiments/run_patterns.py` 가 대체) | 보안A |
| `test_pipeline.py` | 단위 테스트 9개 | `tests/test_common.py`, `tests/test_detection.py`, `tests/test_retrieval.py` (`test_pcy_exhaustive` 는 `tests/test_pcy.py` 가 대체하므로 삭제) | 각자 |
| `figures.py` | 그림 5개 | `experiments/make_figures_detection.py` 등. `03_pcy.png` 는 삭제 (`results/patterns/figures/fig2` 가 대체) | 각자 |
| `build_report.py`, `reports/` | 보고서 생성 | `report/` 폴더로 이동 (코드 채점 대상과 분리) | 통합 담당 |

**보안A 부분을 삭제하는 이유.** 같은 알고리즘이 레포에 두 벌 있으면 어느 쪽이 보고서 기준인지 헷갈려요. 대표 규칙 수치(`P1_PCV01D=HIGH & P1_PCV01Z=HIGH`: test1 conf 0.850·lift 12.97, test2 conf 0.264·lift 6.06), 빈발 쌍 323/188개, 빈발 항목 49/41개가 두 구현에서 정확히 일치하는 것을 확인했어요. 보고서에는 "독립 구현 교차 검증"으로 한 줄 남겨요. 삭제 후 `summary.json` 의 `patterns`, `rule_count` 키가 없어지는 것은 정상이에요 (`results/patterns/run_info_*.json` 이 대체).

**`common/windows.py` 의 `transactions` 는 출력을 바꾸지 마세요.** 보안A 의 `patterns/transactions.py` 는 같은 규칙으로 **문자열** 항목(`"P1_PCV01D=HIGH"`)을 만들고, 지금 `run.py` 는 **정수** 항목(`2*j + HIGH여부`)을 만들어요. MinHash 해시는 정수 값에 걸리므로 문자열로 바꾸면 LSH 결과가 달라져요. 통일은 이번 범위가 아니에요.

## 4. 결과가 같은지 확인하는 방법 (필수)

```powershell
# 1) 정리 전: 원본 run.py (5-1 에서 올린 HAI_Project/) 로 결과를 한 번 만들어 보관
#    data/ 폴더는 레포 최상위에 있어요 (docs/DATA_HAI.md 참고)
python HAI_Project/run.py --data data --out results_before

# 2) 정리 후: 새 실행 스크립트로 결과 생성
python -m experiments.run_detection --data data --out results/detection
python -m experiments.run_retrieval --data data --out results/retrieval

# 3) 비교 (실행 시간 열은 자동으로 무시)
python -m tools.compare_results results_before results/detection
python -m tools.compare_results results_before results/retrieval
```

- 마지막 줄에 `결과: 모두 같음 (실행 시간 제외)` 가 나와야 해요. 파일을 파트별 폴더로 나누면 비교 대상이 아닌 파일은 `[한쪽에만 있음]` 으로 나오는데, **나눈 파일만 그렇게 나오면 정상**이에요.
- 무시하는 시간 열: `median_ms, exact_ms, minhash_ms, lsh_ms, runtime_s, index_build_s` (탐지 지연 `delay_s`, `delay_median_s` 는 지표라서 비교해요).
- 이 스크립트로 기존 `run.py` 두 번의 실행(11/16 실행과 보안B 의 Windows 재실행)을 비교했더니 14개 파일 모두 같았어요.
- `results_before/` 는 비교용이라 commit 하지 않아요.

## 5. 작업 순서 (역할별)

### 5-1. 레포 준비 — 차진희 (레포 관리)

1. 보안A PR [#1](https://github.com/chajinhee/dm-team3/pull/1) (`feat/apriori-pcy` → `main`) 을 merge 해요. 이후 모든 작업은 `main` 에서 출발해요.
2. 팀원 GitHub 아이디를 받아 레포에 초대해요 (Settings → Collaborators).
3. 최지혜 님이 공유한 `HAI_Submission_Local` 의 `HAI_Project` 를 **수정 없이 폴더째** `main` 에 올려요.
   - commit 메시지: `최지혜 님 작성 HAI_Project 원본 업로드 (11/27 로컬 실행본, 수정 없음)`
   - 원본이 git 에 남아 정리 전후 비교 기준이 되고, 카톡 zip 버전 혼동이 없어져요.
   - 폴더째 넣으므로 레포 최상위의 `README.md`·`requirements.txt` 와 충돌하지 않아요.

### 5-2. 파트별 정리 — 각 파트 담당

`HAI_Project/run.py` 에서 자기 파트를 3절 대응표의 새 폴더로 옮겨요. 공통(`common/`) 부분은 먼저 한 사람이 맡아 merge 한 뒤, 나머지가 그 위에서 작업하면 충돌이 적어요.

**git 을 쓰는 경우**
```powershell
git switch main
git pull
git switch -c refactor/detection      # 보안B 는 refactor/retrieval, 공통은 refactor/common
# ... 3절 대응표대로 파일 나누기, 6절 규칙대로 주석 달기 ...
python -m unittest discover tests      # 보안A 38개 + 옮긴 테스트
# 4절 방법으로 결과 비교 → "모두 같음" 확인
git add <나눈 파일들>
git commit -m "탐지 파트 run.py 에서 detection/ 으로 분리 (결과 동일 확인)"
git push -u origin refactor/detection
```
그다음 GitHub 에서 `main` 으로 PR 을 만들고, 다른 팀원 한 명이 리뷰한 뒤 merge 해요.

**git 이 어려운 경우 (지금처럼 카톡 공유도 괜찮아요)**
1. 로컬에서 3절·6절대로 정리하고 4절로 결과가 같은지 확인해요.
2. 정리한 폴더를 zip 으로 공유하면서 "결과 비교: 모두 같음" 출력도 같이 보내 주세요.
3. 차진희가 브랜치에 올리고 PR 을 만들어요. commit 메시지에 **작성자 이름**을 꼭 남겨요 (기여 기록).

### 5-3. 마무리 — 차진희

1. 모든 파트가 옮겨지면 `HAI_Project/` 폴더를 삭제해요 (원본은 git 기록에 남아요).
2. 7절 통합 마무리 항목을 진행해요.

## 6. 코드 작성 규칙

**형식**
- 한 줄에 한 문장. `;` 로 이어 쓰지 않기.
- 들여쓰기 4칸.
- 숫자 상수에 이름 붙이기: `0.6` → `FIT_FRACTION = 0.6`, `[.95, .975, .99, .995, .999]` → `THRESHOLD_QUANTILES`.
- 한 줄 함수(`def topk(...): return ...`)는 풀어 쓰기.

**주석·설명**
- 파일 맨 위 docstring: 무엇을 하는 파일인지, **작성자**, **AI 사용 여부**(예: "BAZE Mindlogic 생성 후 OOO 검토·정리"), 관련 보고서 절.
- 함수마다 docstring: 목적, 입력, 출력. 예:
  ```python
  def reconstruction_score(z, components):
      """PCA 재구성오차 점수 (보고서 3.2절).

      z          : (시점 수, 86) 정상 기준 z-score
      components : (86, r) 상위 r 개 주성분
      반환       : (시점 수,) 변수당 재구성 제곱오차. 클수록 이상
      """
  ```
- 주석은 "무엇을"보다 **"왜"** 를 써요. 예: `# 학습 앞 60% 만 사용: 뒤 40% 는 정상 임계값 보정용으로 남김`.
- 강의 알고리즘은 강의자료 쪽 번호를 적어요 (예: `# 강의 DM_xx p.NN`).
- 누출 방지 지점은 꼭 표시해요. 예: `# test2 는 여기서만 사용. 설정 선택에 쓰지 않음`.

**참고 예시:** 보안A 의 `patterns/apriori.py`, `patterns/pcy.py`, `experiments/run_patterns.py` 가 이 규칙대로 작성돼 있어요.

## 7. 통합 마무리 (통합 담당)

- [ ] `README.md` 하나로 합치기 (팀원 README 의 데이터·누출·레이블 설명 + 보안A README 의 실행 명령)
- [ ] `requirements.txt` 하나로 합치기. 팀이 쓰는 Python 버전 명시 (현재 3.13.0 / numpy 2.3.5 / pandas 2.2.3 과 3.14.4 / 2.5.5 / 3.1.1 두 환경). 다운로드에 `requests` 를 계속 쓰면 포함
- [ ] `.gitignore` 합치기 (`review.jpg`, `results_before/` 추가)
- [ ] 보안B 환경(Python 3.13)에서 보안A 테스트·실험도 실행해 교차 확인
- [ ] 보고서 3.6·4.3·5.3·5.4절과 요약·결론의 Apriori/PCY 문장을 `docs/report_securityA_draft.md` 기준으로 교체
- [ ] AI 공개란에 파트별 도구 기재 (BAZE Mindlogic, Claude Code), 기여란 작성
- [ ] 최종 commit hash 를 보고서에 기재

## 8. 체크리스트

**레포 준비 (차진희)**
- [ ] PR #1 merge
- [ ] 팀원 GitHub 아이디 받아 Collaborator 초대
- [ ] `HAI_Project/` 원본 업로드 (수정 없음)

**공통 (`common/`)** — 담당: [팀 입력]
- [ ] `config.py`, `data.py`, `preprocess.py`, `windows.py` 로 분리, 주석 작성
- [ ] 데이터 검사(해시, 1초 연속, 결측, 레이블 정렬) 동작 그대로

**전자공학 (`detection/`, `experiments/run_detection.py`)**
- [ ] `pca.py`, `kmeans.py`, `zscore.py`, `metrics.py` 분리, 주석 작성
- [ ] `kfit` 의 `default_rng(331)` 위치 유지
- [ ] `tools.compare_results` 로 탐지 결과 9개 파일(`detection_test2.csv`, `development_grid.csv`, `features.csv`, `*_events.csv` 3개, `*_test2_scores.csv.gz` 3개) 같음 확인
- [ ] 테스트 이동 (`test_intervals`, `test_metrics`, `test_zero_baseline`, `test_distance`)

**보안B (`retrieval/`, `experiments/run_retrieval.py`)**
- [ ] `minhash.py`, `lsh.py`, `search.py` 분리, 주석 작성
- [ ] `retrieval` 과 질의 추출의 `default_rng(331)` 위치 유지
- [ ] `retrieval_queries.csv` 같음 확인
- [ ] 테스트 이동 (`test_jaccard`, `test_signature_identical`)

**보안A (차진희)**
- [x] `patterns/` 4개 모듈, `experiments/run_patterns.py`, 테스트 38개, 결과·그림 (완료)
- [ ] `HAI_Project/run.py` 의 `mine_pairs`·규칙 부분 삭제 (다른 파트 정리 후 함께)
- [ ] 보고서 보안A 절 교체 문장 전달

**마무리 (차진희)**
- [ ] `HAI_Project/` 폴더 삭제
- [ ] 7절 통합 마무리
