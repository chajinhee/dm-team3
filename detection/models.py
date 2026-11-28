"""재구성오차 PCA, 시차 잔차 탐지, K-means의 학습과 점수 API.

기존 v6 실험의 계산 순서를 보존해 분리한 코드.
작성 지원 및 모듈 분리: OpenAI Codex. 팀원의 독립 검토 범위는 docs/AI_USE_detection.md 참조.
"""
import numpy as np
from detection.pca import fit_normal, standardize, anomaly
from detection.kmeans import kfit, kmeans_plus_plus, score_centers
from detection.settings import KM_KEYS, FIT_FRACTION, SEED

def fit(ids, keys, dataset):
    """지정 정상 파일로 모델과 원자료 단위의 파일별 보정 구간을 만든다."""
    files = {i: dataset.read(f'train{i}')[0] for i in ids}
    model, _ = fit_normal(files, ids)
    blocks, cal = ([], [])
    for x in files.values():
        cut = int(FIT_FRACTION * len(x))
        blocks.append(standardize(x[:cut], model))
        cal.append(x[cut:])
    normal = np.concatenate(blocks)
    del blocks, files
    eigen, vectors = np.linalg.eigh(np.cov(normal, rowvar=False))
    cumulative = np.cumsum(eigen[::-1]) / eigen.sum()
    sample = normal[np.linspace(0, len(normal) - 1, 15000, dtype=int)]
    model.update(projections={}, centers={}, seeds={})
    for key in keys:
        if key.startswith('PCA-0'):
            # 누적 설명분산 기준으로 상위 성분을 남기는 강의식 PCA다.
            rank = int(np.searchsorted(cumulative, float(key.split('-')[1])) + 1)
            model['projections'][key] = vectors[:, ::-1][:, :rank]
        elif key == 'KM-original':
            model['centers'][key] = kfit(normal, 16)
            model['seeds'][key] = SEED
        elif key in KM_KEYS:
            trials = []
            for seed in (SEED, SEED + 1, SEED + 2):
                centers = kmeans_plus_plus(sample, int(key.split('-')[1]), seed)
                trials.append((score_centers(sample, centers).sum(), seed, centers))
            _, model['seeds'][key], model['centers'][key] = min(trials, key=lambda t: t[:2])
    return (model, cal)


def raw(model, x, key):
    """동결된 모델 키에 해당하는 이상 점수를 반환한다."""
    # PCA-multi는 기존 결과와 호환되는 시차 잔차 탐지의 키다.
    if key == 'PCA-multi':
        return anomaly(x, model)
    z = standardize(x, model)
    if key in model['projections']:
        v = model['projections'][key]
        return np.maximum((z * z).sum(1) - ((z @ v) ** 2).sum(1), 0) / z.shape[1]
    return score_centers(z, model['centers'][key])
