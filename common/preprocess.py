"""정상 운전 기준 정규화 (z-score).

원 코드: HAI_Project/run.py 109–113줄 (최지혜 님 작성, BAZE Mindlogic 생성 코드).
정리: 차진희, Claude Code 지원 (2026-11-27). 계산 순서와 값은 그대로 두었다.

모든 파트가 같은 기준을 쓴다: train1 앞 60% (정상 운전) 의 변수별 중앙값·평균·표준편차.
test1·test2 의 정보는 기준 계산에 들어가지 않는다 (데이터 누출 방지).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from common.config import CONSTANT_STD_EPS, FIT_FRACTION


@dataclass
class Scaler:
    """정규화 기준값 묶음.

    cut      : train1 에서 적합에 쓴 앞부분 행 수 (= int(행 수 × 0.6))
    median   : 변수별 중앙값. 결측값을 채우는 데만 쓴다 (현재 HAI 23.05 파일에는 결측이 없음)
    mean     : 변수별 평균
    std      : 변수별 표준편차 (상수 변수는 1)
    constant : 상수 변수 여부 (표준편차 < 1e-10)
    """
    cut: int
    median: np.ndarray
    mean: np.ndarray
    std: np.ndarray
    constant: np.ndarray


def fit_scaler(train_values: np.ndarray, fit_fraction: float = FIT_FRACTION) -> Scaler:
    """train1 측정값 (행 = 초, 열 = 86 변수) 의 앞부분으로 정규화 기준을 구한다."""
    cut = int(len(train_values) * fit_fraction)
    fit = train_values[:cut]
    median = np.nanmedian(fit, axis=0)
    # 혹시 결측이 있으면 학습 구간 중앙값으로 채운 뒤 평균·표준편차를 구한다
    fit = np.where(np.isfinite(fit), fit, median)
    mean = fit.mean(0)
    std = fit.std(0)
    # 학습 구간에서 값이 변하지 않는 변수는 표준편차 1 로 둔다.
    # 이후 값이 변하면 원 단위 변화가 그대로 z 에 반영되는 한계가 있다 (21개 변수 해당).
    constant = std < CONSTANT_STD_EPS
    std[constant] = 1
    return Scaler(cut=cut, median=median, mean=mean, std=std, constant=constant)


def transform(values: np.ndarray, scaler: Scaler) -> np.ndarray:
    """측정값을 정상 기준 z-score 로 바꾼다. 결측은 학습 중앙값으로 채운다."""
    filled = np.where(np.isfinite(values), values, scaler.median)
    return (filled - scaler.mean) / scaler.std
