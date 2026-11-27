"""K-means 거리, Lloyd 반복과 초기화.

기존 v6 실험의 계산 순서를 보존해 분리한 코드.
작성 지원 및 모듈 분리: OpenAI Codex. 팀원의 독립 검토 범위는 docs/AI_USE_detection.md 참조.
"""
import numpy as np
from common.config import SEED

def sqdist(x, centers):
    """표본과 군집 중심의 제곱 유클리드 거리 행렬을 반환한다."""
    return np.maximum((x * x).sum(axis=1)[:, None] + (centers * centers).sum(axis=1)[None, :] - 2 * x @ centers.T, 0)


def score_centers(x, centers, chunk=10000):
    """메모리 사용량을 제한하며 각 표본의 가장 가까운 중심까지 거리를 구한다."""
    return np.concatenate([sqdist(x[i:i + chunk], centers).min(axis=1) for i in range(0, len(x), chunk)])


def kmeans_plus_plus(x, k: int, seed: int, max_iter=30):
    """주어진 seed의 k-means++ 초기화 후 Lloyd 반복으로 중심을 적합한다."""
    rng = np.random.default_rng(seed)
    centers = [x[int(rng.integers(len(x)))].copy()]
    closest = sqdist(x, np.asarray(centers)).ravel()
    for _ in range(1, k):
        total = float(closest.sum())
        index = int(rng.integers(len(x))) if total <= 0 else int(rng.choice(len(x), p=closest / total))
        centers.append(x[index].copy())
        closest = np.minimum(closest, sqdist(x, np.asarray(centers[-1:])).ravel())
    centers = np.asarray(centers)
    for _ in range(max_iter):
        labels = sqdist(x, centers).argmin(axis=1)
        updated = np.asarray([x[labels == j].mean(axis=0) if (labels == j).any() else centers[j] for j in range(k)])
        if np.max(np.abs(updated - centers)) < 1e-05:
            centers = updated
            break
        centers = updated
    return centers

def kfit(x, k):
    """원본 비교용 K-means. seed 331로 최대 30,000개 정상 표본과 초기 중심을 뽑는다."""
    rng = np.random.default_rng(SEED)
    x = x[rng.choice(len(x), min(30000, len(x)), replace=False)]
    c = x[rng.choice(len(x), k, replace=False)].copy()
    for _ in range(40):
        lab = sqdist(x, c).argmin(1)
        new = np.array([x[lab == j].mean(0) if (lab == j).any() else c[j] for j in range(k)])
        if np.max(np.abs(new - c)) < 1e-05:
            break
        c = new
    return c
