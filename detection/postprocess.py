"""인과적 평활·확인·유지와 개발 구간 분할.

기존 v6 실험의 계산 순서를 보존해 분리한 코드.
작성 지원 및 모듈 분리: OpenAI Codex. 팀원의 독립 검토 범위는 docs/AI_USE_detection.md 참조.
"""
import numpy as np
import pandas as pd

def causal_score(x, span, confirm, hold):
    """과거만 사용해 평활, 연속 초과 확인, 경보 유지를 적용한다. 경보를 소급하지 않는다."""
    s = pd.Series(x).ewm(span=span, adjust=False).mean()
    s = s.rolling(confirm, min_periods=confirm).min().fillna(0)
    return s.rolling(hold, min_periods=1).max().to_numpy()

def split_second(labels):
    """test1의 앞 60%를 경계로 정하고 진행 중인 공격을 자르지 않는다."""
    boundary = int(len(labels) * 0.6) // 60 * 60
    while boundary < len(labels) and (labels[boundary] or labels[boundary - 1]):
        boundary += 60
    if boundary >= len(labels):
        raise ValueError('No valid chronological split')
    return boundary
