"""세 검색 방식의 Top-5와 Recall@5 및 시간 비교.

담당: 보안 B (공통 모듈은 통합 담당 검토 대상).
작성 지원: BAZE Mindlogic; 팀원 검토 및 작성자 실명은 PR 전 기입.
보고서: 3.7·4.3·5.5절. 강의자료 쪽 번호는 확인 후 기입.
"""
import time
import numpy as np
import pandas as pd
from common.config import SEED
from .lsh import build_index, candidates
from .minhash import HASH_PRIME, SIGNATURE_SIZE, jacc, signature

TOP_K = 5
MS_PER_SECOND = 1000


def topk(scores, k=TOP_K):
    """점수 내림차순, 동점은 작은 ID 우선으로 상위 ID를 반환한다."""
    return np.lexsort((np.arange(len(scores)), -np.asarray(scores)))[:k]


def retrieval(gallery, queries):
    """창 집합과 (질의 ID, 집합) 목록을 받아 결과표와 구축 초를 반환한다."""
    # 질의 표본 추출 RNG와 공유하면 기존 해시 계수가 바뀐다.
    rng = np.random.default_rng(SEED)
    a = rng.integers(1, HASH_PRIME, SIGNATURE_SIZE)
    b = rng.integers(0, HASH_PRIME, SIGNATURE_SIZE)
    start = time.perf_counter()
    gallery_signatures = signature(gallery, a, b)
    index = build_index(gallery_signatures)
    build = time.perf_counter() - start
    rows = []
    for query_id, query in queries:
        start = time.perf_counter()
        exact = np.array([jacc(query, item) for item in gallery])
        truth = set(topk(exact))
        exact_time = time.perf_counter() - start

        start = time.perf_counter()
        query_signature = signature([query], a, b)[0]
        approximate = (gallery_signatures == query_signature).mean(1)
        predicted = set(topk(approximate))
        minhash_time = time.perf_counter() - start

        # 원본과 동일하게 각 검색시간에 질의 서명 계산을 별도로 포함한다.
        start = time.perf_counter()
        query_signature = signature([query], a, b)[0]
        found = candidates(index, query_signature)
        ranked = sorted(found, key=lambda i: (-jacc(query, gallery[i]), i))[:TOP_K]
        lsh_time = time.perf_counter() - start

        # 후보 부족 시 보충하지 않는다. exact 목록은 기존 CSV의 ID순을 보존한다.
        rows.append(dict(
            query_window=query_id,
            minhash_recall5=len(predicted & truth) / TOP_K,
            lsh_recall5=len(set(ranked) & truth) / TOP_K,
            exact_ms=exact_time * MS_PER_SECOND,
            minhash_ms=minhash_time * MS_PER_SECOND,
            lsh_ms=lsh_time * MS_PER_SECOND,
            candidates=len(found),
            best_exact=float(exact.max()),
            best_lsh=float(exact[ranked[0]]) if ranked else None,
            top5_exact=','.join(map(str, sorted(truth))),
            top5_lsh=','.join(map(str, ranked)),
        ))
    return pd.DataFrame(rows), build
