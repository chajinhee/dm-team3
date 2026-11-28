"""저장소에서 재현 가능한 이상 탐지 결과를 그린다. 작성 지원: OpenAI Codex."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd

COLORS = {"PCA": "#087870", "K-means": "#b45127"}
V6_NAMES = {"PCA": "시차 잔차", "K-means": "K-means"}


def configure_font():
    """사용 가능한 한글 폰트를 우선 적용한다."""
    apple = Path("/System/Library/Fonts/AppleSDGothicNeo.ttc")
    if apple.exists():
        font_manager.fontManager.addfont(str(apple))
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=str(apple)).get_name()
    else:
        plt.rcParams["font.family"] = ["Noto Sans CJK KR", "Malgun Gothic", "DejaVu Sans"]
    plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False,
                         "axes.unicode_minus": False, "font.size": 10})


def main():
    """정밀도–재현율, v1·v6 비교, 개발 후보 선택 그래프를 저장한다."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("results/detection"))
    parser.add_argument(
        "--baseline-summary", type=Path, default=Path("HAI_Project/results/summary.json"),
        help="원본 HAI_Project/run.py가 저장한 summary.json",
    )
    args = parser.parse_args()
    folder = args.out / "figures"
    folder.mkdir(exist_ok=True)
    configure_font()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), layout="constrained")
    for ax, filename, split, title in zip(
        axes, ["pr_development", "pr_evaluation"], ["development", "train1-2"],
        ["v6 test1 뒤 구간 · 설정 선택", "v6 test2 · 후향 비교"],
    ):
        table = pd.read_csv(args.out / f"{filename}.csv")
        for name, color in COLORS.items():
            group = table[(table.split == split) & (table.model == name)]
            ax.plot(group.recall, group.precision, color=color,
                    label=f"{V6_NAMES[name]} · AP {group.AP.iloc[0]:.3f}")
            ax.scatter(group.chosen_recall.iloc[0], group.chosen_precision.iloc[0],
                       marker="D", s=60, color=color, edgecolor="white", zorder=4)
        ax.set(title=title, xlabel="재현율", ylabel="정밀도", xlim=(0, 1), ylim=(0, 1.02))
        ax.legend(loc="lower left", fontsize=9)
        ax.grid(alpha=.18)
    fig.savefig(folder / "precision_recall.png", dpi=170)
    plt.close(fig)

    original = json.loads(args.baseline_summary.read_text(encoding="utf-8"))
    baseline = pd.DataFrame(original["detection"]).set_index("model")
    evaluation = pd.read_csv(args.out / "evaluation.csv")
    retrospective = evaluation[
        (evaluation.policy == "train1-2") & (evaluation.split == "test2")
    ].set_index("mode")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), layout="constrained")
    fig.suptitle("HAI test2 이상 탐지 · v1 고정 후 평가와 v6 후향 비교", fontsize=14)
    for ax, family in zip(axes, COLORS):
        comparison = pd.DataFrame([baseline.loc[family], retrospective.loc[family]])
        names = ["v1 재구성오차 PCA", "v6 시차 잔차"] if family == "PCA" else [
            "v1 K-means (k=16)", "v6 K-means (k=32)",
        ]
        positions = np.arange(len(names))
        for delta, metric, label, color in [
            (-.24, "precision", "정밀도", "#295b9b"),
            (0, "recall", "재현율", "#b45127"),
            (.24, "f1", "F1", "#087870"),
        ]:
            bars = ax.barh(positions + delta, comparison[metric], height=.21, color=color, label=label)
            ax.bar_label(bars, fmt="%.3f", fontsize=8, padding=3)
        ax.set(yticks=positions, yticklabels=names, xlim=(0, 1),
               title="재구성오차 PCA와 시차 잔차" if family == "PCA" else family,
               xlabel="초 단위 성능")
        ax.invert_yaxis()
        ax.legend(loc="lower right", fontsize=8)
        ax.grid(axis="x", alpha=.18)
    fig.savefig(folder / "version_comparison.png", dpi=170)
    plt.close(fig)

    grid = pd.read_csv(args.out / "detector_grid.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), layout="constrained")
    for ax, family in zip(axes, COLORS):
        part = grid[grid.family == family]
        feasible = part[part.excess == 0]
        best = part.sort_values(
            ["excess", "utility", "f1", "false_positive_seconds_per_normal_hour"],
            ascending=[True, False, False, True], kind="stable",
        ).iloc[0]
        ax.scatter(part.recall, part.precision, color="#dce5e8", s=12, label="전체 후보")
        ax.scatter(feasible.recall, feasible.precision, color="#8092a4", s=15, label="오경보 예산 충족")
        chosen = "선정한 시차 잔차" if best.key == "PCA-multi" else f"선정한 {best.key}"
        ax.scatter(best.recall, best.precision, color=COLORS[family], marker="D", s=90, label=chosen)
        title = "재구성오차 PCA·시차 잔차" if family == "PCA" else family
        ax.set(title=f"{title} · {len(part):,}개 설정", xlabel="재현율", ylabel="정밀도",
               xlim=(0, 1), ylim=(0, 1.02))
        ax.legend(loc="lower left", fontsize=8)
        ax.grid(alpha=.18)
    fig.savefig(folder / "development_selection.png", dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    main()
