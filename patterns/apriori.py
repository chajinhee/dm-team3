"""Apriori 빈발 항목집합 마이닝 (보안A 담당).

작성: 본인. 함수 뼈대·docstring·주석은 Claude Code가 제공했고, 함수 본문은 본인이 작성했다.
      apriori() while 루프의 일부 빈칸은 AI 힌트를 받았다 (docs/AI_USE_apriori_pcy.md 참고).

용어
- transaction: 한 시간 창에서 관측된 항목들의 집합 (frozenset). 예: {"P1_FT01=HIGH", "P1_PCV02Z=LOW"}
- itemset: 항목들의 집합 (frozenset)
- min_count: 최소 지지도 "개수" (비율이 아님). 비율 s 는 ceil(s * len(transactions)) 로 바꿔서 넘긴다.
"""

from __future__ import annotations

from collections.abc import Iterable
import itertools


def count_singletons(transactions: list[frozenset]) -> dict[frozenset, int]:
    """1단계(C1 세기): 모든 단일 항목의 등장 횟수를 센다.

    반환값의 키는 항목 하나짜리 frozenset 이다. 예: {frozenset({"a"}): 3, ...}
    """
    counts = {}  # 장부: {항목 하나짜리 집합: 등장한 거래 수}
    for t in transactions:  # 거래를 하나씩 본다 (데이터 1회 스캔)
        for item in t:  # 그 거래 안의 항목을 하나씩 본다
            # 크기 2, 3 집합과 같은 dict 형식을 쓰려고 항목을 frozenset 으로 감싼다
            key = frozenset({item})
            counts[key] = counts.get(key, 0) + 1  # 처음 보는 항목이면 0에서 시작해 +1
    return counts


def generate_candidates(prev_frequent: Iterable[frozenset], k: int) -> set[frozenset]:
    """L(k-1) 에서 크기 k 후보집합 C(k) 를 만든다.

    두 단계로 구현한다.
    1) join: 크기 k-1 인 빈발집합 두 개를 합쳐 크기 k 가 되는 것만 후보로 둔다.
    2) prune: 후보의 (k-1)-부분집합 중 하나라도 prev_frequent 에 없으면 버린다.
       (downward closure / Apriori 성질)

    이 함수는 거래 데이터를 보지 않는다. 개수 세기는 count_candidates 가 한다.
    """
    # dict 가 들어오면 키만 남는다. set 으로 바꿔 두면 `in` 검사가 빠르다
    prev = set(prev_frequent)
    candidates = set()

    # 1) join: L(k-1) 의 집합 두 개씩 골라 합집합을 만든다
    for a, b in itertools.combinations(prev, 2):
        union = a | b
        # 크기가 정확히 k 인 것만 후보. 더 크면 공통 항목이 부족했던 조합이다
        if len(union) == k:
            candidates.add(union)

    # 2) prune: Apriori 성질에 따라, 빈발하지 않은 부분집합이 있는 후보는 버린다
    #    → count_candidates 에서 셀 후보 수가 줄어 데이터 스캔 비용이 줄어든다
    result = set()
    for c in candidates:
        ok = True  # 일단 통과로 가정
        # c 의 크기 k-1 부분집합을 모두 확인 (prev 안의 집합 크기와 맞춰야 비교가 된다)
        for sub in itertools.combinations(c, k-1):
            # combinations 는 튜플을 돌려주므로 frozenset 으로 바꿔서 비교한다
            if frozenset(sub) not in prev:
                ok = False  # 부분집합 하나라도 빈발이 아니면 탈락
        if ok:
            result.add(c)
    return result

def count_candidates(transactions: list[frozenset], candidates: set[frozenset]) -> dict[frozenset, int]:
    """각 후보가 몇 개의 거래에 부분집합으로 들어 있는지 센다.

    후보가 하나도 포함되지 않은 경우도 0 으로 반환에 넣을지는 자유. (테스트는 >0 인 것만 본다)
    """
    counts = {}  # 장부: {후보 집합: 그 후보를 포함한 거래 수}
    # 비교 횟수 = 거래 수 N × 후보 수 C. 그래서 후보 수를 줄이는 것(prune, PCY)이 중요하다
    for t in transactions:  # 거래를 하나씩 본다 (데이터 1회 스캔)
        for c in candidates:
            if c <= t:  # 후보의 항목이 이 거래에 전부 들어 있으면 (부분집합 검사)
                counts[c] = counts.get(c, 0) + 1
    return counts  # 한 번도 등장하지 않은 후보는 장부에 없다



def apriori(transactions: list[frozenset], min_count: int, max_k: int | None = None) -> dict[frozenset, int]:
    """모든 빈발 항목집합과 그 지지도 개수를 반환한다.

    흐름: L1 = count_singletons 후 min_count 로 거르기
          k = 2, 3, ... 에 대해 C(k) = generate_candidates(L(k-1), k)
                                  L(k) = count_candidates 결과 중 개수 >= min_count
          L(k) 가 비면 (또는 k > max_k 이면) 멈춘다.
    반환: {itemset: count} — 모든 크기의 빈발집합을 한 dict 에 담는다.
    """
    result = {}  # 모든 크기의 빈발집합을 모으는 최종 장부

    # k = 1: 단일 항목을 세고 최소 지지도 이상만 남겨 L1 을 만든다
    current = {}  # 현재 단계의 L(k)
    for itemset, n in count_singletons(transactions).items():
        if n >= min_count:
            current[itemset] = n
    result.update(current)

    # k = 2, 3, ...: 한 단계씩 크기를 키운다
    k = 2
    # 멈추는 조건: 지난 단계 L 이 비었거나 (더 큰 빈발집합은 존재할 수 없음),
    #             max_k 가 정해져 있고 이미 넘었을 때 (예: max_k=2 면 쌍까지만)
    while current and (max_k is None or k <= max_k):
        candidates = generate_candidates(current,k)  # C(k): L(k-1) 로 후보 생성 (데이터 안 봄)
        counts = count_candidates(transactions,candidates)  # 후보마다 데이터를 훑어 개수 세기
        current = {}  # 새 단계의 L(k) 를 처음부터 채운다

        for itemset, n in counts.items():
            if n >= min_count:  # k=1 과 같은 기준으로 거른다
                current[itemset] = n
        result.update(current)
        k = k+1  # 다음 단계는 크기 하나 더 큰 집합
    return result
