"""60초 창 단위 변환: 정수 항목 거래와 창 레이블.

원 코드: HAI_Project/run.py 45–51줄 (transactions), 147줄 (창 레이블)
         (최지혜 님 작성, BAZE Mindlogic 생성 코드).
정리: 차진희, Claude Code 지원 (2026-11-27).

주의: 출력 형식(정수 항목)을 바꾸지 말 것.
  MinHash/LSH (retrieval/) 가 이 정수 값에 해시를 걸기 때문에, 형식을 바꾸면 검색 결과가 달라진다.
  보안A 의 patterns/transactions.py 는 같은 규칙으로 "변수=HIGH" 같은 문자열 항목을 만든다.
  두 함수가 같은 창·같은 항목을 만든다는 것은 보안A 의 대표 규칙 수치가 run.py 결과와 일치하는 것으로 확인했다.
"""

from __future__ import annotations

import numpy as np

WINDOW_SECONDS = 60    # 겹치지 않는 창 길이 (초). 끝에 남는 60초 미만 구간은 버린다
TOP_ITEMS = 8          # 창마다 최대 항목 수
Z_THRESHOLD = 1.5      # |창 평균 z| 가 이 값 이상인 변수만 항목이 된다


def transactions(z: np.ndarray) -> list[frozenset]:
    """z-score 시계열 (행 = 초, 열 = 86 변수) 을 60초 창별 정수 항목 집합으로 바꾼다.

    창마다 변수별 평균 z 를 구하고, |평균 z| ≥ 1.5 인 변수 중 절댓값이 큰 순서로 최대 8개를 고른다.
    항목 번호 = 2 × 변수 번호 + (평균 z > 0 이면 1, 아니면 0)
        예: 변수 7번이 HIGH → 15, 변수 7번이 LOW → 14
    HIGH/LOW 는 정상 운전 대비 높다/낮다는 통계적 상태이지 물리적 안전 기준이 아니다.
    """
    out = []
    for start in range(0, len(z) - (WINDOW_SECONDS - 1), WINDOW_SECONDS):
        window_mean = z[start:start + WINDOW_SECONDS].mean(0)
        # 절댓값이 큰 순서. kind="stable": 같은 값일 때 변수 순서를 고정해 재현성을 지킨다
        top = np.argsort(-np.abs(window_mean), kind="stable")[:TOP_ITEMS]
        items = frozenset(
            int(2 * j + (window_mean[j] > 0))
            for j in top
            if abs(window_mean[j]) >= Z_THRESHOLD
        )
        out.append(items)
    return out


def window_labels(y: np.ndarray) -> np.ndarray:
    """초 단위 0/1 레이블을 60초 창 레이블로 바꾼다. 창 안에 공격 초가 하나라도 있으면 1.

    transactions() 와 같은 창 경계를 쓴다.
    """
    return np.array([
        y[start:start + WINDOW_SECONDS].max()
        for start in range(0, len(y) - (WINDOW_SECONDS - 1), WINDOW_SECONDS)
    ])
