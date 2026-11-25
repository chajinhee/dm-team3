"""PCY (Park-Chen-Yu) 빈발 쌍 마이닝 (보안A 담당).

작성: Claude Code가 함수 본문과 주석을 작성했고 (본인 요청), 본인이 검토했다.
      docs/AI_USE_apriori_pcy.md 참고.

Apriori 의 2단계(쌍 세기)를 개선한 알고리즘이다. 결과(빈발 쌍)는 Apriori 와 완전히 같아야 하고,
차이는 2차 패스에서 "세는 후보 쌍의 수" (= 필요한 메모리) 이다.

1차 패스: 단일 항목을 세면서, 동시에 거래 안의 모든 쌍을 해시 버킷에 넣어 버킷 개수를 센다.
패스 사이: 빈발 항목 집합 + 빈발 버킷 비트맵(버킷 개수 >= min_count 이면 True)을 만든다.
2차 패스: 쌍 {i, j} 는 (i, j 모두 빈발) AND (해당 버킷이 빈발) 일 때만 센다.

왜 맞는가: 쌍 {i, j} 가 빈발이면 그 쌍이 들어간 버킷 개수도 최소 count({i, j}) >= min_count 이므로
            빈발 쌍은 절대 버려지지 않는다. 버려지는 것은 빈발일 수 없는 쌍뿐이다.
"""

from __future__ import annotations

import itertools
import zlib


def pair_hash(a: str, b: str, n_buckets: int) -> int:
    """쌍 {a, b} 를 0 ~ n_buckets-1 사이 버킷 번호로 바꾼다.

    - 순서 무관: pair_hash(a, b) == pair_hash(b, a)  (정렬해서 해시)
    - 재현 가능: 파이썬 내장 hash() 는 실행할 때마다 문자열 해시값이 바뀌므로 (PYTHONHASHSEED)
      실험 결과가 매번 달라진다. 그래서 고정된 CRC32 를 쓴다.
    """
    x, y = sorted((a, b))
    # \x1f(구분 문자)를 사이에 넣어 ("ab","c") 와 ("a","bc") 가 같은 문자열이 되지 않게 한다
    return zlib.crc32(f"{x}\x1f{y}".encode("utf-8")) % n_buckets


def first_pass(transactions: list[frozenset], n_buckets: int) -> tuple[dict[frozenset, int], list[int]]:
    """1차 패스: (단일 항목 개수, 버킷 개수 리스트) 를 반환한다.

    - 단일 항목 개수: apriori.count_singletons 와 같은 형식 {frozenset({item}): count}
    - 버킷 개수: 길이 n_buckets 인 리스트. 거래 안의 모든 쌍 (a, b) 마다
      bucket_counts[pair_hash(a, b, n_buckets)] += 1
    데이터를 한 번만 훑으면서 두 가지를 동시에 센다.
    """
    item_counts = {}               # 장부 1: {항목 하나짜리 집합: 거래 수}  (Apriori 1단계와 동일)
    bucket_counts = [0] * n_buckets  # 장부 2: 버킷 번호별 개수. 1차 패스의 남는 메모리를 여기에 쓴다
    for t in transactions:  # 데이터 1회 스캔
        # (a) 단일 항목 세기: count_singletons 와 같은 방식
        for item in t:
            key = frozenset({item})
            item_counts[key] = item_counts.get(key, 0) + 1
        # (b) 거래 안의 모든 쌍을 해시해서 그 버킷에 +1
        #     쌍 자체를 세는 게 아니라 "버킷"만 세므로 메모리는 n_buckets 칸으로 고정된다.
        #     서로 다른 쌍이 같은 버킷에 들어갈 수 있다(충돌) → 버킷 개수는 쌍 개수의 상한이 된다.
        #     sorted 로 항상 같은 순서로 쌍을 만들어 재현성을 지킨다.
        for a, b in itertools.combinations(sorted(t), 2):
            bucket_counts[pair_hash(a, b, n_buckets)] += 1
    return item_counts, bucket_counts


def frequent_bucket_bitmap(bucket_counts: list[int], min_count: int) -> list[bool]:
    """버킷마다 개수가 min_count 이상이면 True, 아니면 False 인 리스트.

    (실제 PCY 는 이걸 비트 1개씩으로 압축해서 메모리를 아낀다. 여기선 bool 리스트로 단순화.)
    """
    bitmap = []
    for count in bucket_counts:
        # 버킷 개수 < min_count 이면, 이 버킷에 들어간 어떤 쌍도 빈발일 수 없다
        # (쌍 개수 <= 버킷 개수 < min_count). 그래서 False 로 표시해 2차 패스에서 버린다.
        bitmap.append(count >= min_count)
    return bitmap


def second_pass(transactions: list[frozenset], frequent_items: set[str],
                bitmap: list[bool], n_buckets: int) -> tuple[dict[frozenset, int], int]:
    """2차 패스: 조건을 통과한 쌍만 센다.

    조건: a, b 모두 frequent_items 에 있고 AND bitmap[pair_hash(a, b, n_buckets)] 가 True.
    frequent_items 는 frozenset 이 아니라 항목 문자열의 set 이다. 예: {"I1", "I2"}
    반환: (쌍 개수 dict {frozenset({a, b}): count}, 센 서로 다른 후보 쌍의 수)
    """
    pair_counts = {}  # 장부: {후보 쌍: 거래 수}. 이 장부의 크기가 PCY 가 줄이려는 메모리다
    for t in transactions:  # 데이터 2회째 스캔
        # 조건 ①: 빈발 항목만 남긴다 (집합 교집합). Apriori 와 같은 조건
        frequent_in_t = t & frequent_items
        for a, b in itertools.combinations(sorted(frequent_in_t), 2):
            # 조건 ②: 같은 해시 함수로 버킷을 다시 계산해 빈발 버킷인지 확인. PCY 가 추가한 조건
            if bitmap[pair_hash(a, b, n_buckets)]:
                key = frozenset({a, b})
                pair_counts[key] = pair_counts.get(key, 0) + 1
    # 장부에 한 번이라도 들어간 서로 다른 쌍의 수 = 실제로 칸을 만들어 센 후보 수
    n_candidates = len(pair_counts)
    return pair_counts, n_candidates


def pcy(transactions: list[frozenset], min_count: int, n_buckets: int) -> tuple[dict[frozenset, int], dict]:
    """빈발 단일 항목 + 빈발 쌍과, 비교 실험용 통계를 반환한다.

    첫 번째 반환값은 apriori(transactions, min_count, max_k=2) 와 완전히 같아야 한다.
    두 번째 반환값(통계) 키:
        "n_frequent_items":   빈발 단일 항목 수
        "n_frequent_buckets": bitmap 에서 True 인 버킷 수
        "n_candidates":       2차 패스에서 센 서로 다른 후보 쌍 수
    """
    # 1차 패스: 단일 항목 개수와 버킷 개수를 한 번에 센다
    item_counts, bucket_counts = first_pass(transactions, n_buckets)

    # 패스 사이 (1): 빈발 단일 항목 L1 을 고른다
    result = {}  # 최종 결과: 빈발 단일 항목 + 빈발 쌍
    for itemset, n in item_counts.items():
        if n >= min_count:
            result[itemset] = n
    # second_pass 는 문자열 set 을 받으므로, frozenset({"I1"}) 에서 "I1" 을 꺼낸다
    # (원소가 하나뿐인 집합이므로 iter 로 첫 원소를 꺼내면 그게 전부다)
    frequent_items = {next(iter(itemset)) for itemset in result}

    # 패스 사이 (2): 빈발 버킷 비트맵
    bitmap = frequent_bucket_bitmap(bucket_counts, min_count)

    # 2차 패스: 두 조건을 통과한 후보 쌍만 센다
    pair_counts, n_candidates = second_pass(transactions, frequent_items, bitmap, n_buckets)

    # 후보 쌍 중 실제로 min_count 이상인 것만 빈발 쌍으로 남긴다
    # (버킷 통과는 "빈발일 수도 있다"는 뜻일 뿐이라, 정확한 개수로 한 번 더 걸러야 한다)
    for pair, n in pair_counts.items():
        if n >= min_count:
            result[pair] = n

    # Apriori 와 비교할 통계. 결과는 같고, n_candidates 가 얼마나 줄었는지가 PCY 의 효과다
    stats = {
        "n_frequent_items": len(frequent_items),
        "n_frequent_buckets": sum(bitmap),  # True 는 1, False 는 0 으로 더해진다
        "n_candidates": n_candidates,
    }
    return result, stats
