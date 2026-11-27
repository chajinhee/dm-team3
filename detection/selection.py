"""개발 자료로 설정 선택 및 PR 곡선 저장.

기존 v6 실험의 계산 순서를 보존해 분리한 코드.
작성 지원 및 모듈 분리: OpenAI Codex. 팀원의 독립 검토 범위는 docs/AI_USE_detection.md 참조.
"""
import numpy as np
import pandas as pd
from detection.models import raw
from detection.postprocess import causal_score
from detection.metrics import measure, pr
from detection.settings import PCA_KEYS, KM_KEYS, SHAPES, QUANTILES, FAR, DURATION

def smooth(x, cfg):
    """구성에 정한 인과적 후처리를 이상 점수에 적용한다."""
    return causal_score(x, int(cfg['span']), int(cfg['confirm']), int(cfg['hold']))


def metrics(y, score, threshold):
    """오경보 1회/h·60초/h 목표 초과분과 탐지 성능을 계산한다."""
    m = measure(y, score > threshold)
    return dict(**m, excess=max(m[FAR] - 1, 0) + max(m[DURATION] / 60 - 1, 0))


def rank(table):
    """목표 초과분 최소, F1·사건 재현율 조화평균 최대, F1 최대, 오탐 시간 최소 순."""
    return table.sort_values(['excess', 'utility', 'f1', DURATION], ascending=[True, False, False, True], kind='stable')


def detectors(model, cal, x, y, output):
    """test1 앞 구간에서 두 계열의 모델 및 임계값 분위수를 고른다."""
    rows, cache = ([], {})
    for key in PCA_KEYS + KM_KEYS:
        family = 'PCA' if key in PCA_KEYS else 'K-means'
        score = raw(model, x, key)
        cache[key] = score
        normals = [raw(model, c, key) for c in cal]
        for span, confirm, hold in SHAPES:
            cfg = dict(span=span, confirm=confirm, hold=hold)
            signal = smooth(score[:len(y)], cfg)
            calibrated = np.concatenate([smooth(c, cfg) for c in normals])
            for q, threshold in zip(QUANTILES, np.quantile(calibrated, QUANTILES)):
                rows.append(dict(
                    family=family, key=key, **cfg, quantile=q, threshold=threshold,
                    **metrics(y, signal, threshold)
                ))
    grid = pd.DataFrame(rows)
    grid.to_csv(output / 'detector_grid.csv', index=False)
    selected = {}
    scores = {}
    for family, group in grid.groupby('family'):
        best = rank(group).iloc[0]
        cfg = best[['key', 'span', 'confirm', 'hold', 'quantile', 'threshold']].to_dict()
        selected[family] = cfg
        scores[family] = smooth(cache[cfg['key']], cfg) / cfg['threshold']
    return (selected, scores)


def save_curve(records, split, name, score, y, threshold):
    """AP는 모든 초로 계산하고 그래프 좌표만 최대 1,200개로 축약한다."""
    recall, precision, ap = pr(y, score)
    idx = np.unique(np.linspace(0, len(recall) - 1, min(1200, len(recall)), dtype=int))
    met = measure(y, score > threshold)
    records.extend(
        dict(split=split, model=name, recall=recall[j], precision=precision[j], AP=ap,
             chosen_recall=met['recall'], chosen_precision=met['precision'])
        for j in idx
    )
