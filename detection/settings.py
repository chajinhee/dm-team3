"""v6에서 시험한 탐지 설정 후보. 결과를 보고 바꾸지 않는다.

기존 v6 실험의 계산 순서를 보존해 분리한 코드.
작성 지원 및 모듈 분리: OpenAI Codex. 팀원의 독립 검토 범위는 docs/AI_USE_detection.md 참조.
"""
from common.config import FIT_FRACTION, SEED

QUANTILES = [.90,.93,.95,.97,.975,.98,.99,.992,.995,.997,.998,.999,.9993,.9995,.9997,.9999,1.]
SHAPES = [(1,1,1),(3,1,1),(3,3,3),(5,1,6),(10,1,6),(5,3,6),(5,1,15),(1,3,1)]
MULTIPLIERS = [1., .95, 1.05, .9, 1.1, .8, 1.2]
PCA_KEYS = ["PCA-multi", "PCA-0.99", "PCA-0.995"]
KM_KEYS = ["KM-original", "KM-4", "KM-8", "KM-16", "KM-32"]
FAR = "false_alarms_per_normal_hour"
DURATION = "false_positive_seconds_per_normal_hour"
