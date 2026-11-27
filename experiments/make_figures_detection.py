"""탐지 결과와 버전 비교표로 그래프를 만든다. 작성 지원: OpenAI Codex."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd

COLORS = {"PCA": "#087870", "K-means": "#b45127"}


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
    """정밀도–재현율, 버전 지표, 개발 후보 선택 그래프를 각각 저장한다."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("results/detection"))
    args = parser.parse_args()
    folder = args.out / "figures"
    folder.mkdir(exist_ok=True)
    configure_font()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), layout="constrained")
    for ax, filename, split, title in zip(
        axes, ["pr_development", "pr_evaluation"], ["development", "train1-2"],
        ["test1 뒤 구간 · 설정 선택", "test2 · 고정한 설정 평가"],
    ):
        table = pd.read_csv(args.out / f"{filename}.csv")
        for name, color in COLORS.items():
            group = table[(table.split == split) & (table.model == name)]
            ax.plot(group.recall, group.precision, color=color,
                    label=f"{name} · AP {group.AP.iloc[0]:.3f}")
            ax.scatter(group.chosen_recall.iloc[0], group.chosen_precision.iloc[0],
                       marker="D", s=60, color=color, edgecolor="white", zorder=4)
        ax.set(title=title, xlabel="재현율", ylabel="정밀도", xlim=(0, 1), ylim=(0, 1.02))
        ax.legend(loc="lower left", fontsize=9)
        ax.grid(alpha=.18)
    fig.savefig(folder / "precision_recall.png", dpi=170)
    plt.close(fig)

    data = pd.read_csv(args.out / "version_history.csv")
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), layout="constrained")
    for ax, family in zip(axes, COLORS):
        mask = data.name.str.contains("K-means")
        part = data[~mask if family == "PCA" else mask]
        positions = np.arange(len(part))
        for delta, metric, label, color in [
            (-.24, "precision", "정밀도", "#295b9b"),
            (0, "recall", "재현율", "#b45127"),
            (.24, "f1", "F1", "#087870"),
        ]:
            ax.barh(positions + delta, part[metric], height=.21, color=color, label=label)
        ax.set(yticks=positions, yticklabels=part.name, xlim=(0, .95),
               title=family, xlabel="초 단위 성능 · †는 평가 이후 정상 자료 포함")
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
        ax.scatter(best.recall, best.precision, color=COLORS[family], marker="D", s=90, label="선정한 설정")
        ax.set(title=f"{family} · {len(part):,}개 설정", xlabel="재현율", ylabel="정밀도",
               xlim=(0, 1), ylim=(0, 1.02))
        ax.legend(loc="lower left", fontsize=8)
        ax.grid(alpha=.18)
    fig.savefig(folder / "development_selection.png", dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    main()
