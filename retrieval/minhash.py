"""Jaccard 유사도와 MinHash 서명.

담당: 보안 B (공통 모듈은 통합 담당 검토 대상).
작성 지원: BAZE Mindlogic; 팀원 검토 및 작성자 실명은 PR 전 기입.
보고서: 3.7절. 강의자료 쪽 번호는 확인 후 기입.
"""
import numpy as np

HASH_PRIME = 2147483647
SIGNATURE_SIZE = 64


def signature(transactions, a, b):
    """정수 집합과 해시 계수 배열을 받아 행별 MinHash 서명을 반환한다."""
    rows = []
    for items in transactions:
        if items:
            ids = np.array(sorted(items), dtype=np.int64)
            values = (a[:, None] * ids[None, :] + b[:, None]) % HASH_PRIME
            rows.append(np.min(values, axis=1))
        else:
            rows.append(np.full(len(a), HASH_PRIME, dtype=np.int64))
    return np.array(rows)


def jacc(a, b):
    """두 집합의 Jaccard 유사도. 둘 다 비면 기존과 같이 1을 반환한다."""
    union = a | b
    return len(a & b) / len(union) if union else 1.0
