"""PCA 고유분해 기반 조건부 잔차 탐지.

기존 v6 실험의 계산 순서를 보존해 분리한 코드.
작성 지원 및 모듈 분리: OpenAI Codex. 팀원의 독립 검토 범위는 docs/AI_USE_detection.md 참조.
"""
import numpy as np
from common.preprocess import fit_scaler, transform
from common.config import FIT_FRACTION

def lag(x, n):
    """파일 경계를 넘지 않는 과거 시점 배열. 처음 n행은 첫 관측값으로 채운다."""
    return np.concatenate([np.repeat(x[:1], n, axis=0), x[:-n]])


def top_three(x):
    """채널별 절대 조건부 잔차 중 큰 세 값의 log1p 평균."""
    return np.log1p(np.partition(np.abs(x), -3, axis=1)[:, -3:]).mean(axis=1)

def standardize(x, model):
    """학습 정상 자료의 공통 Scaler로 센서 배열을 정규화한다."""
    return transform(x, model['scaler'])


def score_components(z, parts):
    """각 시차에서 조건부 잔차 점수를 구한다. 파일별로 독립 호출한다."""
    scores = []
    for delay, beta, weight in parts:
        residual = z if not delay else z - lag(z, delay) @ beta
        scores.append(top_three(residual @ weight))
    return np.column_stack(scores)


def fit_normal(normal, ids):
    """파일별 앞 60%로 잔차 모델을 적합하고 뒤 40%로 점수의 99분위를 보정한다."""
    fit = [normal[i][:int(len(normal[i]) * FIT_FRACTION)] for i in ids]
    calibration = [normal[i][int(len(normal[i]) * FIT_FRACTION):] for i in ids]
    united = np.concatenate(fit)
    scaler = fit_scaler(united, fit_fraction=1.0)
    mean, scale = scaler.mean, scaler.std
    scale[scale < 1e-10] = 1
    del united
    model = dict(mean=mean, scale=scale, scaler=scaler)
    fit = [standardize(x, model) for x in fit]
    parts = []
    for delay in [0, 1, 10]:
        beta = None
        residual = fit
        if delay:
            count = sum((len(x) - delay for x in fit))
            xx = sum((x[:-delay].T @ x[:-delay] for x in fit))
            xy = sum((x[:-delay].T @ x[delay:] for x in fit))
            beta = np.linalg.solve(xx + np.eye(len(mean)) * count * 0.0001, xy)
            residual = [x[delay:] - x[:-delay] @ beta for x in fit]
        covariance = np.cov(np.concatenate(residual), rowvar=False)
        values, vectors = np.linalg.eigh(covariance)
        precision = vectors / (np.maximum(values, 0) + 0.0001) @ vectors.T
        parts.append((delay, beta, precision / np.sqrt(np.diag(precision))))
    model['parts'] = parts
    cal_scores = [score_components(standardize(x, model), parts) for x in calibration]
    model['score_scale'] = np.maximum(np.quantile(np.concatenate(cal_scores), 0.99, axis=0), 1e-08)
    return (model, [(value / model['score_scale']).max(1) for value in cal_scores])


def anomaly(x, model):
    """현재·1초·10초 조건부 잔차 점수의 최대값을 반환한다."""
    part_scores = score_components(standardize(x, model), model['parts'])
    return (part_scores / model['score_scale']).max(1)
