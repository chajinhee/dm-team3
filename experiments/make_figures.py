"""보안A 실험 결과 CSV(results/patterns/) 에서 보고서·발표용 그림을 다시 만든다.

작성: Claude Code가 작성했고 (본인 요청), 본인이 검토했다. docs/AI_USE_apriori_pcy.md 참고.
실행 (dm-team3 폴더에서, run_patterns 의 dev·final 단계를 먼저 실행해야 함):
    python -m experiments.make_figures
출력: results/patterns/figures/fig1~fig4 (.png)

색은 시각화 가이드의 기본 팔레트를 쓴다. 범주형은 순서 고정(파랑 → 주황 → 청록), 크기는 파랑 단일 색조.
보고서 인쇄를 고려해 흰 배경 정적 이미지로 만들고, 색만으로 구분하지 않도록 범례와 직접 레이블을 함께 단다.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 화면 없이 파일로만 저장
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

RES = Path("results/patterns")
OUT = RES / "figures"

# ---- 팔레트 (가이드 기본값, 라이트 모드) ----
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
GRAY = "#898781"            # baseline 처럼 비교 기준이 되는 표식
TEXT, TEXT2 = "#0b0b0b", "#52514e"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
SURFACE = "#ffffff"
BLUE_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
STRATEGY_COLOR = {"lift": BLUE, "coverage": ORANGE, "novel": AQUA, "baseline": GRAY}


def style():
    """얇은 표식, 옅은 격자, 눈에 덜 띄는 축."""
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.family": "DejaVu Sans", "font.size": 9, "text.color": TEXT,
        "axes.edgecolor": AXIS, "axes.labelcolor": TEXT2, "axes.titlesize": 10, "axes.titleweight": "bold",
        "axes.titlecolor": TEXT, "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
        "xtick.color": TEXT2, "ytick.color": TEXT2, "legend.frameon": False,
    })


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("saved", OUT / f"{name}.png")


# ---------------------------------------------------------------------------------------------
# 그림 1: 규칙 선택 기준별 F1 — 고른 구간(test1) 대 처음 보는 구간(test2). 과적합 차이를 보여준다.
# ---------------------------------------------------------------------------------------------
def fig1_strategy_f1():
    s = pd.read_csv(RES / "e1_final_summary.csv")
    rows = [("always_attack", "Always attack (baseline)"),
            ("lift_K<=1", "lift, K=1"), ("lift_K<=2", "lift, K≤2"),
            ("coverage_K<=1", "coverage, K=1"), ("coverage_K<=2", "coverage, K≤2  (primary)"),
            ("novel_K<=2", "novel, K≤2")]
    labels = [lab for _, lab in rows]
    f1_t1 = [s[(s.method == m) & (s.part == "test1")].f1.iloc[0] for m, _ in rows]
    f1_t2 = [s[(s.method == m) & (s.part == "test2")].f1.iloc[0] for m, _ in rows]

    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    y = np.arange(len(rows))[::-1]
    h = 0.36
    ax.barh(y + h / 2 + 0.01, f1_t1, height=h, color=BLUE, label="test1 (rules selected here)")
    ax.barh(y - h / 2 - 0.01, f1_t2, height=h, color=ORANGE, label="test2 (held out, evaluated once)")
    for yi, v in zip(y, f1_t2):  # 결론을 내리는 test2 값만 직접 표시
        ax.text(v + 0.008, yi - h / 2 - 0.01, f"{v:.3f}", va="center", fontsize=8, color=TEXT)
    ax.set_yticks(y, labels)
    ax.set_xlabel("Window-level F1 (alarm when any frozen rule matches)")
    ax.set_xlim(0, 0.65)
    ax.grid(axis="y", visible=False)
    ax.set_title("Fig. 1  Rule selection: in-sample vs held-out F1")
    # 막대를 가리지 않도록 범례는 축 아래에 둔다
    ax.legend(loc="upper center", bbox_to_anchor=(0.4, -0.17), ncol=2, fontsize=8)
    save(fig, "fig1_strategy_f1")


# ---------------------------------------------------------------------------------------------
# 그림 2: PCY 가 2차 패스에서 세는 후보 비율 대 버킷 수. 1/3 아래여야 메모리 이득(triples 12B vs 삼각행렬 4B).
# ---------------------------------------------------------------------------------------------
def fig2_pcy():
    e2 = pd.read_csv(RES / "e2_pcy.csv")
    e2["ratio"] = e2.pcy_candidates / e2.apriori_pair_slots
    datasets = [("test1_60s_top8", "test1, 60 s windows, top-8 items\n(900 transactions)"),
                ("train1+test1_30s_top15", "train1+test1, 30 s windows, top-15 items\n(11,160 transactions)")]
    supports = [(0.005, BLUE), (0.01, ORANGE), (0.02, AQUA)]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), sharey=True)
    for ax, (ds, title) in zip(axes, datasets):
        d = e2[e2.dataset == ds]
        ax.axhline(1 / 3, color=TEXT2, linewidth=1, linestyle=(0, (4, 3)))
        ax.text(70, 1 / 3 - 0.035, "memory break-even (1/3)", fontsize=7.5, color=TEXT2, va="top")
        for sup, color in supports:
            g = d[d.support == sup].sort_values("buckets")
            ax.plot(g.buckets, g.ratio, color=color, linewidth=2, marker="o", markersize=5,
                    markeredgecolor=SURFACE, markeredgewidth=1.2, label=f"min support {sup:.1%}")
        ax.set_xscale("log", base=2)
        ax.set_xticks([64, 256, 1024, 4096], ["64", "256", "1024", "4096"])
        ax.set_xlabel("Number of hash buckets")
        ax.set_ylim(0, 1.02)
        ax.set_title(title, fontsize=8.5, fontweight="normal", color=TEXT2)
    axes[0].set_ylabel("PCY candidate pairs / Apriori pair slots")
    axes[0].legend(loc="lower left", fontsize=7.5)
    fig.suptitle("Fig. 2  PCY candidate reduction (results identical to Apriori in all 24 settings)",
                 fontsize=10, fontweight="bold", x=0.02, ha="left", y=1.1)
    save(fig, "fig2_pcy_candidates")


# ---------------------------------------------------------------------------------------------
# 그림 3: 민감도 — 창 크기 × 기준값 별 holdout F1 (coverage, K≤2). test1 안에서만 계산.
# ---------------------------------------------------------------------------------------------
def fig3_sensitivity():
    e3 = pd.read_csv(RES / "e3_sensitivity.csv")
    d = e3[(e3.strategy == "coverage") & (e3.K == 2)]
    cmap = LinearSegmentedColormap.from_list("blue", BLUE_RAMP)
    vmax = max(0.25, d.holdout_f1.max())
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.9))
    for ax, top_m in zip(axes, [8, 15]):
        g = d[d.top_m == top_m].pivot(index="window", columns="threshold", values="holdout_f1")
        im = ax.imshow(g.values, cmap=cmap, vmin=0, vmax=vmax, aspect="auto")
        for i in range(g.shape[0]):
            for j in range(g.shape[1]):
                v = g.values[i, j]
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8,
                        color="#ffffff" if v > vmax * 0.55 else TEXT)
        ax.set_xticks(range(g.shape[1]), [f"|z| ≥ {t}" for t in g.columns])
        # 두 패널의 창 크기가 같으므로 오른쪽 패널은 눈금 이름을 생략해 겹침을 막는다
        ax.set_yticks(range(g.shape[0]), [f"{w} s" for w in g.index] if top_m == 8 else [])
        ax.grid(False)
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.set_title(f"top-{top_m} items per window", fontsize=8.5, fontweight="normal", color=TEXT2)
    axes[0].set_ylabel("Window length")
    cb = fig.colorbar(im, ax=axes, shrink=0.85, pad=0.02)
    cb.set_label("Holdout F1 (test1 2nd half)", color=TEXT2)
    cb.outline.set_visible(False)
    fig.suptitle("Fig. 3  Sensitivity of coverage rules (K≤2), selected on test1 1st half",
                 fontsize=10, fontweight="bold", x=0.02, ha="left", y=1.03)
    save(fig, "fig3_sensitivity")


# ---------------------------------------------------------------------------------------------
# 그림 4: test2 에서 검출한 공격 구간 수 대 정상 1시간당 오경보 창 수. 왼쪽 위가 좋다.
# ---------------------------------------------------------------------------------------------
def fig4_tradeoff():
    s = pd.read_csv(RES / "e1_final_summary.csv")
    t2 = s[(s.part == "test2") & (s.K.isin([0, 1, 2]))]
    fig, ax = plt.subplots(figsize=(5.6, 3.6))
    # 점 이름이 서로 겹치지 않도록 점마다 레이블 위치를 따로 정한다 (x 오프셋, y 오프셋, 정렬)
    offsets = {"always_attack": (-6, -12, "right"), "lift_K<=1": (6, -10, "left"), "lift_K<=2": (6, 2, "left"),
               "coverage_K<=1": (6, 2, "left"), "coverage_K<=2": (-2, -14, "left"), "novel_K<=2": (6, 2, "left")}
    for strategy in ["baseline", "lift", "coverage", "novel"]:
        g = t2[t2.strategy == strategy]
        if strategy == "novel":
            g = g[g.K == 2]   # novel K=1 은 규칙이 0 개라 표시하지 않음
        ax.scatter(g.false_alarm_windows_per_normal_hour, g.events_detected, s=46,
                   color=STRATEGY_COLOR[strategy], edgecolor=SURFACE, linewidth=1.5, zorder=3,
                   label={"baseline": "baseline"}.get(strategy, strategy))
        for _, r in g.iterrows():
            dx, dy, ha = offsets.get(r.method, (6, 4, "left"))
            if r.method == "always_attack":
                name = "always attack"
            else:
                name = f"{r.strategy}, " + ("K=1" if r.K == 1 else f"K≤{r.K}")
            ax.annotate(name, (r.false_alarm_windows_per_normal_hour, r.events_detected),
                        textcoords="offset points", xytext=(dx, dy), ha=ha, fontsize=7.5, color=TEXT2)
    total = int(t2.events_total.iloc[0])
    ax.axhline(total, color=AXIS, linewidth=1)
    ax.text(0.5, total - 0.6, f"all {total} attack intervals", fontsize=7.5, color=TEXT2, va="top")
    ax.set_xlabel("False-alarm windows per normal hour (test2)")
    ax.set_ylabel("Attack intervals detected (test2)")
    ax.set_xlim(-1, 64)
    ax.set_ylim(0, total + 3)
    ax.legend(loc="center right", fontsize=8, title="selection", title_fontsize=8)
    ax.set_title("Fig. 4  Detected attack intervals vs false alarms on test2")
    save(fig, "fig4_tradeoff")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    style()
    fig1_strategy_f1()
    fig2_pcy()
    fig3_sensitivity()
    fig4_tradeoff()


if __name__ == "__main__":
    main()
