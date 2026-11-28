"""초·사건 단위 평가 및 정밀도–재현율.

기존 v6 실험의 계산 순서를 보존해 분리한 코드.
작성 지원 및 모듈 분리: OpenAI Codex. 팀원의 독립 검토 범위는 docs/AI_USE_detection.md 참조.
"""
import numpy as np

def intervals(values):
    """불리언 배열의 연속 True 구간을 [시작, 끝) 인덱스로 반환한다."""
    a = np.asarray(values, dtype=bool)
    changes = np.diff(np.r_[False, a, False].astype(np.int8))
    return list(zip(np.where(changes == 1)[0], np.where(changes == -1)[0]))


def average_precision(y_true, scores) -> float:
    """기존 함수의 호환용 평균 정밀도 계산."""
    y = np.asarray(y_true, dtype=bool)
    if not y.any():
        return 0.0
    order = np.argsort(-np.asarray(scores), kind='stable')
    ranked = y[order]
    precision = np.cumsum(ranked) / np.arange(1, len(ranked) + 1)
    return float(precision[ranked].sum() / ranked.sum())


def metrics(y_true, prediction, scores=None):
    """초 단위 혼동행렬과 사건 검출·지연·정상 시간당 오경보를 계산한다."""
    y = np.asarray(y_true, dtype=bool)
    p = np.asarray(prediction, dtype=bool)
    tp = int((y & p).sum())
    fp = int((~y & p).sum())
    fn = int((y & ~p).sum())
    tn = int((~y & ~p).sum())
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    detected_delays = [int(np.flatnonzero(p[start:end])[0]) for start, end in intervals(y) if p[start:end].any()]
    false_runs = len(intervals(p & ~y))
    result = {
        'precision': precision,
        'recall': recall,
        'f1': 2 * precision * recall / max(precision + recall, 1e-15),
        'accuracy': (tp + tn) / len(y),
        'tp': tp,
        'fp': fp,
        'fn': fn,
        'tn': tn,
        'event_recall': len(detected_delays) / max(len(intervals(y)), 1),
        'detected_events': len(detected_delays),
        'events': len(intervals(y)),
        'delay_median_s': float(np.median(detected_delays)) if detected_delays else None,
        'false_alarms_per_normal_hour': false_runs / max((~y).sum() / 3600, 1e-15),
        'false_positive_seconds_per_normal_hour': fp / max((~y).sum() / 3600, 1e-15),
    }
    if scores is not None:
        result['average_precision'] = average_precision(y, scores)
    return result

def utility(row):
    """초 단위 F1과 사건 재현율의 조화평균."""
    f1, event_recall = (row['f1'], row['event_recall'])
    return 2 * f1 * event_recall / max(f1 + event_recall, 1e-12)


def measure(y, prediction):
    """탐지 지표와 개발 선택용 종합 점수를 함께 반환한다."""
    result = metrics(y, prediction)
    result['utility'] = utility(result)
    return result

def pr(y, s):
    """동점 점수를 묶어 PR 곡선과 AP를 구한다. 사건이 없는 자료의 AP는 미정의."""
    if not np.asarray(y).any():
        return np.array([]), np.array([]), float('nan')
    order = np.argsort(-s, kind='stable')
    end = np.r_[np.where(np.diff(s[order]) != 0)[0], len(s) - 1]
    tp = np.cumsum(y[order])[end]
    p = tp / (end + 1)
    r = tp / y.sum()
    return (r, p, float(np.diff(np.r_[0, r]) @ p))
