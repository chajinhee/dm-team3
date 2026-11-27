"""보안A 실험: HAI 23.05 에서 Apriori / 연관 규칙 / PCY 실험 (E0~E3).

작성: Claude Code가 작성했고 (본인 요청), 본인이 검토했다. docs/AI_USE_apriori_pcy.md 참고.

실행 (dm-team3 폴더에서):
    python -m experiments.run_patterns --stage dev      # train1·test1 만 사용 (개발 단계)
    python -m experiments.run_patterns --stage final    # 규칙을 test1 로 고정한 뒤 test2 에서 한 번 평가

데이터 사용 규칙 (팀 합의):
    train1 → 정규화 기준(앞 60%)        test1 → 규칙 선택·파라미터 결정        test2 → 최종 평가에만 사용
    dev 단계는 test2 를 읽지 않는다. final 단계도 test2 결과를 보고 설정을 바꾸지 않는다.
    (창 크기·기준값은 E3 결과와 무관하게 DEFAULT_CFG 로 미리 고정했다.)

결과는 results/patterns/ 에 CSV / JSON 으로 저장된다.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import platform
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from patterns.apriori import apriori
from patterns.pcy import pcy
from patterns.rules import interest, rule_metrics
from patterns.transactions import (ATTACK, add_attack_item, attack_events, fit_scaler, load_labels,
                                   load_measurements, make_transactions, window_labels, zscore)

# ---- 미리 고정한 설정 (test2 를 보기 전에 정함) ----
DEFAULT_CFG = {"window": 60, "threshold": 1.5, "top_m": 8}   # 팀원 구현과 같은 거래 생성 규칙
RULE_MIN_SUPPORT = 0.01   # 규칙 마이닝 최소 지지도 (창 수 대비 비율)
TOP_N_RULES = 10          # 선택해서 고정할 규칙 수 (팀원 구현과 같음)
K_LIST = [1, 2, 3, 4]     # 규칙 전건(antecedent)의 최대 항목 수. K=1 은 단일 센서 baseline, K=2 는 팀원 방식

# 규칙 선택 기준 (개발 단계 1차 결과를 보고 test1 안에서 추가함. test2 는 보지 않은 상태)
#   lift     : lift 내림차순 (1차 방식, 팀원 방식과 같음) → confidence 1.0 의 시나리오 전용 규칙이 뽑혀 과적합
#   coverage : lift >= MIN_LIFT 인 규칙 중 공격 창을 많이 덮는 순 → 여러 공격에 공통인 규칙을 우선
#   novel    : coverage 조건 + 전건이 train1(정상 운전)에서 한 번도 나오지 않은 규칙만
# 강의(DM_03 p.15-17) 와의 대응 (2026-11-27 정리. 선택 동작은 바꾸지 않음):
#   - support >= s : 모든 기준에서 A ∪ {ATTACK} 이 최소 지지도 이상이어야 규칙이 된다.
#   - confidence >= c : lift >= 2 는 confidence >= 2·P(ATTACK) 와 같으므로,
#     coverage·novel 은 c = 2·P(ATTACK) (test1 전체 기준 약 0.131) 인 confidence 기준을 쓰는 셈이다.
#     lift 기준은 confidence 기준 없이 상위 10개를 고른다.
#   - interest (p.13) : 후건이 ATTACK 하나로 고정되면 interest 와 lift 는 confidence 의 증가함수라 순위가 같다.
#     그래서 lift 기준 = interest 기준이다. 결과 CSV 에는 interest 를 함께 보고한다.
STRATEGIES = ["lift", "coverage", "novel"]
MIN_LIFT = 2.0
LECTURE_INTEREST = 0.5    # 강의 p.13 "Interesting rules: usually above 0.5" — 보고용 표시만, 선택에는 쓰지 않음
# 주 기준: test2 실행 전(2026-11-26)에 개발 단계 결과만으로 결정.
# 근거: E3 18개 설정 평균 holdout F1(coverage .115 / lift .067 / novel .006)과 평균 검출 공격 구간 수가 가장 높고,
#       K>=2 에서도 holdout F1 이 0 으로 무너지지 않음. final 단계에서도 세 기준 모두 보고한다.
PRIMARY_STRATEGY = "coverage"

# E3 민감도 분석 격자 (test1 안에서만)
E3_WINDOWS = [30, 60, 120]
E3_THRESHOLDS = [1.0, 1.5, 2.0]
E3_TOP_M = [8, 15]
E3_K = [2, 3]

# E2 PCY 비교 설정
E2_BUCKETS = [64, 256, 1024, 4096]
E2_SUPPORTS = [0.005, 0.01, 0.02]
E2_LARGE_CFG = {"window": 30, "threshold": 1.0, "top_m": 15}  # 거래가 많고 길어지는 조건


def min_count(support: float, n: int) -> int:
    """비율 지지도를 개수로 바꾼다. 최소 1."""
    return max(1, math.ceil(support * n))


def itemset_text(s: frozenset) -> str:
    """CSV 에 쓰기 좋은 정렬된 문자열."""
    return " & ".join(sorted(s))


# =====================================================================================
# 규칙 선택과 평가
# =====================================================================================

def mine_attack_rules(tx: list[frozenset], wl: np.ndarray, min_support: float, max_k: int) -> tuple[list[dict], int]:
    """공격 창에 ATTACK 을 붙여 Apriori 로 마이닝하고, '{센서 조건들} -> {ATTACK}' 규칙을 모두 만든다.

    반환: (규칙 목록, 빈발집합 수). 규칙은 lift 내림차순 → support 내림차순 → 항목 이름 순으로 정렬.
    전건 크기 max_k 까지 보려면 ATTACK 까지 포함해 max_k+1 크기 집합이 필요하다.
    """
    data = add_attack_item(tx, wl)
    n = len(data)
    frequent = apriori(data, min_count(min_support, n), max_k=max_k + 1)
    target = frozenset({ATTACK})
    rules = []
    for itemset, count in frequent.items():
        if ATTACK in itemset and len(itemset) >= 2:
            antecedent = itemset - target
            # 본인이 구현한 rule_metrics 사용. Apriori 성질로 antecedent 와 {ATTACK} 개수가 frequent 에 있다
            support, confidence, lift = rule_metrics(frequent, n, antecedent, target)
            rules.append({"antecedent": antecedent, "count": count,
                          "support": support, "confidence": confidence,
                          "interest": interest(confidence, frequent[target] / n),  # 강의 p.13
                          "lift": lift})
    rules.sort(key=lambda r: (-r["lift"], -r["support"], sorted(r["antecedent"])))
    return rules, len(frequent)


def attach_normal_counts(rules: list[dict], tx_normal: list[frozenset]) -> None:
    """각 규칙의 전건이 정상 운전 거래(train1)에서 몇 번 나왔는지 'normal_count' 로 붙인다.

    레이블이 필요 없는 정보다: train1 은 공격이 없는 정상 운전 기록이므로,
    정상에서 한 번도 안 나온 조합이라면 '정상 운전 변화'보다 '이상 상태'일 가능성이 높다는 근거가 된다.
    """
    for r in rules:
        r["normal_count"] = sum(1 for t in tx_normal if r["antecedent"] <= t)


def select_rules(all_rules: list[dict], k: int, strategy: str = "lift", top_n: int = TOP_N_RULES) -> list[dict]:
    """전건 크기가 k 이하인 규칙 중 선택 기준(strategy)에 따라 상위 top_n 개를 고른다.

    all_rules 는 mine_attack_rules 에서 이미 lift 순으로 정렬돼 있다.
    """
    pool = [r for r in all_rules if len(r["antecedent"]) <= k]
    if strategy == "lift":
        return pool[:top_n]
    # coverage / novel: 우연보다 확실히 공격과 관련된 규칙(lift >= MIN_LIFT)만 남긴 뒤
    # 공격 창을 많이 덮는 순(count = 전건과 ATTACK 이 함께 나온 창 수)으로 고른다.
    # confidence 가 조금 낮더라도 여러 공격 구간에 걸쳐 나타나는 규칙이 다른 구간에도 맞을 가능성이 높다.
    pool = [r for r in pool if r["lift"] >= MIN_LIFT]
    if strategy == "novel":
        pool = [r for r in pool if r["normal_count"] == 0]
    elif strategy != "coverage":
        raise ValueError(f"알 수 없는 선택 기준: {strategy}")
    pool.sort(key=lambda r: (-r["count"], -r["lift"], sorted(r["antecedent"])))
    return pool[:top_n]


def evaluate_rules(rules: list[dict], tx: list[frozenset], wl: np.ndarray, window: int) -> tuple[list[dict], dict]:
    """고정한 규칙을 다른 구간 거래에 적용해 규칙별·전체 지표를 계산한다.

    - 규칙별: 매칭 창 수, 그중 공격 창 수, confidence, lift(그 구간의 공격 비율 대비), coverage(공격 창 중 매칭 비율)
    - 전체: 규칙 중 하나라도 매칭되면 '경보'로 보고 창 단위 precision / recall / F1,
            공격 구간(연속 공격 창) 중 경보가 하나라도 있는 구간 수, 정상 1시간당 오경보 창 수
    이 '경보'는 규칙의 설명력을 정량화하려는 것이지, 독립 탐지기를 제안하는 것이 아니다.
    """
    y = wl.astype(bool)
    base = y.mean() if len(y) else float("nan")
    n_attack = int(y.sum())
    alarm = np.zeros(len(tx), dtype=bool)
    per_rule = []
    for r in rules:
        match = np.fromiter((r["antecedent"] <= t for t in tx), dtype=bool, count=len(tx))
        alarm |= match
        cnt = int(match.sum())
        hit = int((match & y).sum())
        conf = hit / cnt if cnt else float("nan")
        per_rule.append({"match": cnt, "attack_hits": hit, "confidence": conf,
                         "interest": interest(conf, base) if cnt else float("nan"),
                         "lift": conf / base if cnt and base > 0 else float("nan"),
                         "coverage": hit / n_attack if n_attack else float("nan")})
    summary = alarm_summary(alarm, y, window)
    return per_rule, summary


def alarm_summary(alarm: np.ndarray, y: np.ndarray, window: int) -> dict:
    """창 단위 경보 배열과 정답으로 지표를 계산한다."""
    tp = int((alarm & y).sum())
    fp = int((alarm & ~y).sum())
    fn = int((~alarm & y).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    events = attack_events(y.astype(int))
    detected = sum(bool(alarm[s:e].any()) for s, e in events)
    normal_hours = (~y).sum() * window / 3600
    return {"windows": int(len(y)), "attack_windows": int(y.sum()), "alarm_windows": int(alarm.sum()),
            "precision": precision, "recall": recall, "f1": f1,
            "events_detected": detected, "events_total": len(events),
            "false_alarm_windows_per_normal_hour": fp / normal_hours if normal_hours else float("nan")}


def rules_to_rows(rules, per_select, per_eval, k, select_name, eval_name, strategy):
    """규칙 목록과 두 구간 평가 결과를 CSV 행으로 합친다."""
    rows = []
    for rank, (r, a, b) in enumerate(zip(rules, per_select, per_eval), start=1):
        rows.append({"strategy": strategy, "K": k, "rank": rank, "antecedent": itemset_text(r["antecedent"]),
                     "size": len(r["antecedent"]), "train1_normal_count": r["normal_count"],
                     f"{select_name}_rule_support": r["count"],   # 강의 p.15: count(A ∪ {ATTACK})
                     f"{select_name}_match": a["match"], f"{select_name}_confidence": a["confidence"],
                     f"{select_name}_interest": a["interest"],
                     f"{select_name}_interest_ge_{LECTURE_INTEREST}": bool(a["interest"] >= LECTURE_INTEREST),
                     f"{select_name}_lift": a["lift"], f"{select_name}_coverage": a["coverage"],
                     f"{eval_name}_match": b["match"], f"{eval_name}_confidence": b["confidence"],
                     f"{eval_name}_interest": b["interest"],
                     f"{eval_name}_lift": b["lift"], f"{eval_name}_coverage": b["coverage"]})
    return rows


def run_rule_comparison(tx_sel, wl_sel, tx_eval, wl_eval, tx_normal, window, select_name, eval_name):
    """선택 기준 × K 마다 select 구간에서 규칙을 골라 고정하고, select·eval 두 구간에서 평가한다. baseline 포함.

    tx_normal: train1 거래 (novel 기준용, 레이블 없음)
    """
    all_rules, n_frequent = mine_attack_rules(tx_sel, wl_sel, RULE_MIN_SUPPORT, max(K_LIST))
    attach_normal_counts(all_rules, tx_normal)
    summary_rows, rule_rows = [], []
    for strategy in STRATEGIES:
        for k in K_LIST:
            chosen = select_rules(all_rules, k, strategy)
            per_s, sum_s = evaluate_rules(chosen, tx_sel, wl_sel, window)
            per_e, sum_e = evaluate_rules(chosen, tx_eval, wl_eval, window)
            for part, s in ((select_name, sum_s), (eval_name, sum_e)):
                summary_rows.append({"method": f"{strategy}_K<={k}", "strategy": strategy, "K": k,
                                     "part": part, "n_rules": len(chosen), **s})
            rule_rows += rules_to_rows(chosen, per_s, per_e, k, select_name, eval_name, strategy)
    # baseline: 모든 창을 공격이라고 하는 규칙 ({} -> ATTACK). confidence = 공격 비율, lift = 1
    for part, wl in ((select_name, wl_sel), (eval_name, wl_eval)):
        y = wl.astype(bool)
        summary_rows.append({"method": "always_attack", "strategy": "baseline", "K": 0, "part": part,
                             "n_rules": 0, **alarm_summary(np.ones(len(y), dtype=bool), y, window)})
    return pd.DataFrame(summary_rows), pd.DataFrame(rule_rows), n_frequent


# =====================================================================================
# 데이터 준비
# =====================================================================================

def load_split(data_dir: Path, name: str, mean, std, label_file: str | None):
    """측정 파일을 z-score 로, 레이블 파일이 있으면 0/1 배열로 읽는다."""
    values, ts, cols = load_measurements(data_dir / name)
    z = zscore(values, mean, std)
    y = load_labels(ts, data_dir / label_file) if label_file else None
    return z, y, cols


def transaction_stats(name: str, tx: list[frozenset], wl: np.ndarray | None, cfg: dict) -> dict:
    """E0: 거래 데이터 기술 통계."""
    lengths = np.array([len(t) for t in tx])
    row = {"split": name, **cfg, "windows": len(tx), "empty_ratio": float((lengths == 0).mean()),
           "mean_items": float(lengths.mean()), "max_items": int(lengths.max()),
           "distinct_items": len(set().union(*tx))}
    if wl is not None:
        row.update({"attack_windows": int(wl.sum()), "attack_ratio": float(wl.mean()),
                    "attack_events": len(attack_events(wl))})
    return row


# =====================================================================================
# E2: PCY 대 Apriori
# =====================================================================================

def observed_pairs(tx: list[frozenset], frequent_items: set[str]) -> int:
    """빈발 항목끼리 실제로 함께 나온 서로 다른 쌍의 수."""
    pairs = set()
    for t in tx:
        pairs.update(itertools.combinations(sorted(t & frequent_items), 2))
    return len(pairs)


def run_pcy_comparison(datasets: dict[str, list[frozenset]], repeats: dict[str, int]) -> pd.DataFrame:
    """같은 거래·같은 최소 지지도에서 Apriori(쌍까지) 와 PCY 를 비교한다.

    메모리 추정은 수업 교재(MMDS) 의 방식: 삼각행렬 4 bytes/쌍, triples 12 bytes/쌍, 비트맵 1 bit/버킷.
    Apriori 는 빈발 항목 m 개의 모든 쌍 C(m,2) 칸을 삼각행렬로 세고,
    PCY 는 후보가 흩어져 있어 삼각행렬을 못 쓰고 triples 로 세야 한다.
    → PCY 가 메모리에서 이기려면 후보를 삼각행렬 칸 수의 1/3 미만으로 줄여야 한다.
    """
    rows = []
    for name, tx in datasets.items():
        n = len(tx)
        for support in E2_SUPPORTS:
            mc = min_count(support, n)
            times = []
            for _ in range(repeats[name]):
                t0 = time.perf_counter()
                ref = apriori(tx, mc, max_k=2)
                times.append(time.perf_counter() - t0)
            frequent_items = {next(iter(s)) for s in ref if len(s) == 1}
            m = len(frequent_items)
            tri = m * (m - 1) // 2
            obs = observed_pairs(tx, frequent_items)
            n_frequent_pairs = sum(1 for s in ref if len(s) == 2)
            for nb in E2_BUCKETS:
                ptimes = []
                for _ in range(repeats[name]):
                    t0 = time.perf_counter()
                    got, stats = pcy(tx, mc, nb)
                    ptimes.append(time.perf_counter() - t0)
                assert got == ref, f"PCY 결과가 Apriori 와 다르다: {name}, s={support}, buckets={nb}"
                pcy_pass2 = 12 * stats["n_candidates"] + math.ceil(nb / 8)
                rows.append({
                    "dataset": name, "transactions": n, "support": support, "min_count": mc,
                    "buckets": nb, "frequent_items": m, "frequent_pairs": n_frequent_pairs,
                    "apriori_pair_slots": tri, "observed_frequent_item_pairs": obs,
                    "pcy_frequent_buckets": stats["n_frequent_buckets"], "pcy_candidates": stats["n_candidates"],
                    "candidate_reduction_vs_slots": 1 - stats["n_candidates"] / tri if tri else float("nan"),
                    "apriori_triangular_bytes": 4 * tri,
                    "pcy_pass2_bytes": pcy_pass2,
                    "pcy_pass1_bucket_bytes": 4 * nb,
                    "pcy_memory_wins": pcy_pass2 < 4 * tri,
                    "apriori_median_s": float(np.median(times)), "pcy_median_s": float(np.median(ptimes)),
                    "repeats": repeats[name],
                })
    return pd.DataFrame(rows)


# =====================================================================================
# 단계별 실행
# =====================================================================================

def run_dev(data_dir: Path, out: Path) -> dict:
    t_start = time.perf_counter()
    train_values, _, cols = load_measurements(data_dir / "hai-train1.csv")
    mean, std = fit_scaler(train_values)
    z_train = zscore(train_values, mean, std)
    z_t1, y_t1, _ = load_split(data_dir, "hai-test1.csv", mean, std, "label-test1.csv")
    w = DEFAULT_CFG["window"]

    # ---- E0: 거래 기술 통계 ----
    tx_train = make_transactions(z_train, cols, **DEFAULT_CFG)
    tx_t1 = make_transactions(z_t1, cols, **DEFAULT_CFG)
    wl_t1 = window_labels(y_t1, w)
    e0 = pd.DataFrame([transaction_stats("train1", tx_train, None, DEFAULT_CFG),
                       transaction_stats("test1", tx_t1, wl_t1, DEFAULT_CFG)])
    e0.to_csv(out / "e0_transactions.csv", index=False)

    # ---- E1 (개발): test1 앞 절반에서 규칙 선택 → 뒤 절반에서 검증 (test2 는 아직 사용하지 않음) ----
    half = len(tx_t1) // 2
    e1_sum, e1_rules, n_freq = run_rule_comparison(tx_t1[:half], wl_t1[:half], tx_t1[half:], wl_t1[half:],
                                                   tx_train, w, "test1_first_half", "test1_second_half")
    e1_sum.to_csv(out / "e1_dev_summary.csv", index=False)
    e1_rules.to_csv(out / "e1_dev_rules.csv", index=False)

    # ---- E3: 민감도 분석 (test1 안에서만, 같은 앞/뒤 절반 프로토콜) ----
    e3_rows = []
    for window, thr, top_m in itertools.product(E3_WINDOWS, E3_THRESHOLDS, E3_TOP_M):
        cfg = {"window": window, "threshold": thr, "top_m": top_m}
        tx = make_transactions(z_t1, cols, **cfg)
        wl = window_labels(y_t1, window)
        h = len(tx) // 2
        t0 = time.perf_counter()
        all_rules, n_frequent = mine_attack_rules(tx[:h], wl[:h], RULE_MIN_SUPPORT, max(E3_K))
        mine_s = time.perf_counter() - t0
        # novel 기준용: 같은 설정으로 만든 train1 거래와 대조
        attach_normal_counts(all_rules, make_transactions(z_train, cols, **cfg))
        stats = transaction_stats("test1", tx, wl, cfg)
        for strategy in STRATEGIES:
            for k in E3_K:
                chosen = select_rules(all_rules, k, strategy)
                _, s = evaluate_rules(chosen, tx[h:], wl[h:], window)
                e3_rows.append({**cfg, "strategy": strategy, "K": k, "windows": stats["windows"],
                                "mean_items": stats["mean_items"], "empty_ratio": stats["empty_ratio"],
                                "frequent_itemsets": n_frequent, "n_rules": len(chosen), "mine_s": mine_s,
                                **{f"holdout_{key}": v for key, v in s.items()}})
    pd.DataFrame(e3_rows).to_csv(out / "e3_sensitivity.csv", index=False)

    # ---- E2: PCY 대 Apriori (레이블 사용 안 함) ----
    tx_large = (make_transactions(z_train, cols, **E2_LARGE_CFG)
                + make_transactions(z_t1, cols, **E2_LARGE_CFG))
    e2 = run_pcy_comparison({"test1_60s_top8": tx_t1, "train1+test1_30s_top15": tx_large},
                            repeats={"test1_60s_top8": 5, "train1+test1_30s_top15": 1})
    e2.to_csv(out / "e2_pcy.csv", index=False)

    return {"stage": "dev", "e1_frequent_itemsets": n_freq, "test1_half_windows": half,
            "runtime_s": time.perf_counter() - t_start}


def run_final(data_dir: Path, out: Path) -> dict:
    t_start = time.perf_counter()
    train_values, _, cols = load_measurements(data_dir / "hai-train1.csv")
    mean, std = fit_scaler(train_values)
    tx_train = make_transactions(zscore(train_values, mean, std), cols, **DEFAULT_CFG)
    z_t1, y_t1, _ = load_split(data_dir, "hai-test1.csv", mean, std, "label-test1.csv")
    z_t2, y_t2, _ = load_split(data_dir, "hai-test2.csv", mean, std, "label-test2.csv")
    w = DEFAULT_CFG["window"]
    tx_t1, wl_t1 = make_transactions(z_t1, cols, **DEFAULT_CFG), window_labels(y_t1, w)
    tx_t2, wl_t2 = make_transactions(z_t2, cols, **DEFAULT_CFG), window_labels(y_t2, w)
    pd.DataFrame([transaction_stats("test1", tx_t1, wl_t1, DEFAULT_CFG),
                  transaction_stats("test2", tx_t2, wl_t2, DEFAULT_CFG)]).to_csv(out / "e0_final_transactions.csv", index=False)
    # test1 전체에서 규칙 선택·고정 → test2 에서 한 번 평가
    e1_sum, e1_rules, n_freq = run_rule_comparison(tx_t1, wl_t1, tx_t2, wl_t2, tx_train, w, "test1", "test2")
    e1_sum.to_csv(out / "e1_final_summary.csv", index=False)
    e1_rules.to_csv(out / "e1_final_rules.csv", index=False)
    return {"stage": "final", "e1_frequent_itemsets": n_freq, "runtime_s": time.perf_counter() - t_start}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stage", choices=["dev", "final"], required=True)
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--out", type=Path, default=Path("results/patterns"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    info = run_dev(args.data, args.out) if args.stage == "dev" else run_final(args.data, args.out)
    info.update({"default_cfg": DEFAULT_CFG, "rule_min_support": RULE_MIN_SUPPORT, "top_n_rules": TOP_N_RULES,
                 "k_list": K_LIST, "strategies": STRATEGIES, "min_lift": MIN_LIFT, "primary_strategy": PRIMARY_STRATEGY,
                 "lecture_interest_reporting_threshold": LECTURE_INTEREST, "python": sys.version.split()[0], "numpy": np.__version__,
                 "pandas": pd.__version__, "platform": platform.platform(),
                 "run_at": time.strftime("%Y-%m-%d %H:%M:%S")})
    (args.out / f"run_info_{args.stage}.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(info, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
