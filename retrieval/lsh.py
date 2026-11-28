"""MinHash 밴드 인덱스와 후보 선택.

담당: 보안 B (공통 모듈은 통합 담당 검토 대상).
작성 지원: BAZE Mindlogic; 팀원 검토 및 작성자 실명은 PR 전 기입.
보고서: 3.7절. 강의자료 쪽 번호는 확인 후 기입.
"""
from collections import defaultdict

BANDS = 16
ROWS_PER_BAND = 4


def _keys(signature):
    """서명 하나에서 밴드 위치와 그 밴드 값의 튜플을 생성한다."""
    for band in range(BANDS):
        start = ROWS_PER_BAND * band
        yield band, tuple(signature[start:start + ROWS_PER_BAND])


def build_index(signatures):
    """갤러리 서명 행렬을 받아 밴드 키별 창 ID 집합을 반환한다."""
    index = defaultdict(set)
    for window_id, row in enumerate(signatures):
        for key in _keys(row):
            index[key].add(window_id)
    return index


def candidates(index, query_signature):
    """한 밴드라도 같은 갤러리 창의 ID 합집합을 반환한다."""
    found = set()
    for key in _keys(query_signature):
        found.update(index.get(key, set()))
    return found
