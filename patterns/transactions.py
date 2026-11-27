"""HAI 센서 시계열 -> 시간 창별 거래(transaction) 변환 (보안A 담당).

작성: Claude Code가 작성했고 (본인 요청), 본인이 검토했다. docs/AI_USE_apriori_pcy.md 참고.

연관 규칙 마이닝은 "항목들의 집합"을 입력으로 받으므로, 연속값 센서 시계열을 이산 항목으로 바꿔야 한다.
방법 (팀원 구현 run.py 의 transactions() 와 같은 규칙을 따른다):
  1) train1 의 앞 60% (정상 운전) 로 변수별 평균·표준편차를 구한다. (팀 공통 정규화 기준)
  2) 모든 시점을 z-score 로 바꾼다.
  3) 겹치지 않는 window 초 단위 창마다 변수별 평균 z 를 구한다.
  4) |평균 z| 가 threshold 이상인 변수 중 절댓값이 큰 순서로 top_m 개를 골라
     "변수=HIGH" (평균 z > 0) 또는 "변수=LOW" (평균 z < 0) 항목으로 만든다.
  HIGH/LOW 는 "정상 운전 대비 높다/낮다" 라는 통계적 상태이지, 물리적 안전 기준이 아니다.

레이블은 거래를 만드는 데 쓰지 않는다. 공격 여부는 window_labels() 로 따로 만들고,
규칙 마이닝 단계에서만 ATTACK 항목으로 붙인다 (add_attack_item).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

FIT_FRACTION = 0.6   # train1 중 정규화 기준을 구하는 앞부분 비율 (팀원 실험과 동일)
ATTACK = "ATTACK"    # 공격 창에 붙이는 특수 항목 이름


def load_measurements(path: str | Path) -> tuple[np.ndarray, pd.Series, list[str]]:
    """HAI CSV 를 읽어 (측정값 행렬, timestamp, 변수 이름 목록) 을 반환한다.

    측정값 행렬 크기: (시점 수, 86). timestamp 열은 모델 입력에서 뺀다.
    """
    df = pd.read_csv(path)
    cols = [c for c in df.columns if c != "timestamp"]
    values = df[cols].to_numpy(dtype=float)
    # 확보 단계에서 결측치 0 개를 확인했다. 혹시 다른 파일이 들어오면 바로 알 수 있게 멈춘다.
    assert np.isfinite(values).all(), f"{path}: 결측치/무한대 값이 있다"
    return values, df["timestamp"], cols


def fit_scaler(train_values: np.ndarray, fit_fraction: float = FIT_FRACTION) -> tuple[np.ndarray, np.ndarray]:
    """train1 앞부분으로 변수별 평균·표준편차를 구한다.

    학습 구간에서 값이 변하지 않는 변수(표준편차 0)는 나눗셈이 불가능하므로 표준편차를 1 로 둔다.
    (팀원 구현과 같은 처리. 이후 값이 변하면 원 단위 크기 그대로 z 에 반영되는 한계가 있다.)
    """
    cut = int(len(train_values) * fit_fraction)
    fit = train_values[:cut]
    mean = fit.mean(axis=0)
    std = fit.std(axis=0)
    std[std == 0] = 1.0
    return mean, std


def zscore(values: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    """정상 운전 기준으로 몇 표준편차만큼 벗어났는지로 바꾼다."""
    return (values - mean) / std


def load_labels(measure_ts: pd.Series, label_path: str | Path) -> np.ndarray:
    """측정 파일의 시점 순서에 맞춘 0/1 레이블 배열을 반환한다.

    - test1: 레이블 timestamp 가 측정 timestamp 와 초 단위로 전부 같다 → 그대로 사용
    - test2: 레이블 timestamp 가 분 단위로만 기록돼 있어 timestamp 로 합칠 수 없다.
      (1) 행 수가 같고 (2) 측정 시각을 분 단위로 내림한 값이 모든 행에서 레이블 시각과 같으며
      (3) 측정 시각이 1초 간격으로 연속일 때만 "행 순서 대응"을 사용한다. (팀원 구현과 같은 검사)
      분 안에서의 초 단위 순서가 보존됐다는 가정은 남는다 → 보고서 한계에 적을 것.
    """
    lab = pd.read_csv(label_path)
    assert len(lab) == len(measure_ts), "측정 파일과 레이블 파일의 행 수가 다르다"
    mt = pd.to_datetime(measure_ts)
    lt = pd.to_datetime(lab["timestamp"])
    if (mt.values == lt.values).all():
        return lab["label"].to_numpy(dtype=int)
    one_second = (mt.diff().dropna() == pd.Timedelta(seconds=1)).all()
    minute_match = (mt.dt.floor("min").values == lt.values).all()
    assert one_second and minute_match, "레이블을 행 순서로 대응시킬 근거가 없다"
    return lab["label"].to_numpy(dtype=int)


def window_means(z: np.ndarray, window: int) -> np.ndarray:
    """겹치지 않는 window 개 시점마다 변수별 평균을 낸다. 끝에 남는 불완전한 창은 버린다.

    반환 크기: (창 수, 변수 수)
    """
    n_windows = len(z) // window
    # (창 수 × window, 변수 수) → (창 수, window, 변수 수) 로 접은 뒤 창 안에서 평균
    return z[: n_windows * window].reshape(n_windows, window, z.shape[1]).mean(axis=1)


def make_transactions(z: np.ndarray, cols: list[str], window: int,
                      threshold: float, top_m: int) -> list[frozenset]:
    """z-score 시계열을 창별 거래 목록으로 바꾼다. 창 하나 = 거래 하나.

    정상 범위 안의 창은 빈 거래가 될 수 있다 (그대로 둔다: 전체 창 수 n 에 포함돼야 지지도가 맞다).
    """
    means = window_means(z, window)
    transactions = []
    for m in means:
        # 절댓값이 큰 순서. kind="stable" 로 같은 값일 때 변수 순서를 고정해 재현성을 지킨다
        order = np.argsort(-np.abs(m), kind="stable")[:top_m]
        items = []
        for j in order:
            if abs(m[j]) >= threshold:
                items.append(f"{cols[j]}={'HIGH' if m[j] > 0 else 'LOW'}")
        transactions.append(frozenset(items))
    return transactions


def window_labels(y: np.ndarray, window: int) -> np.ndarray:
    """창 안에 공격 초가 하나라도 있으면 1. make_transactions 와 같은 창 경계를 쓴다."""
    n_windows = len(y) // window
    return y[: n_windows * window].reshape(n_windows, window).max(axis=1)


def add_attack_item(transactions: list[frozenset], labels: np.ndarray) -> list[frozenset]:
    """공격 창의 거래에 ATTACK 항목을 붙인다. 규칙 마이닝(사후 연관 분석) 전용.

    ATTACK 이 들어간 거래는 탐지 입력이 아니다. "어떤 상태 조합이 공격 창과 함께 나타나는가"를
    support/confidence/lift 로 정량화하기 위한 것이다.
    """
    return [t | {ATTACK} if lab == 1 else t for t, lab in zip(transactions, labels)]


def attack_events(labels: np.ndarray) -> list[tuple[int, int]]:
    """연속된 1 구간을 (시작, 끝+1) 목록으로 반환한다. 공격 구간(이벤트) 단위 평가에 쓴다."""
    events = []
    start = None
    for i, v in enumerate(labels):
        if v == 1 and start is None:
            start = i
        elif v == 0 and start is not None:
            events.append((start, i))
            start = None
    if start is not None:
        events.append((start, len(labels)))
    return events
