"""재구성오차 PCA·시차 잔차·K-means 후보를 비교한 v6 탐지 실험을 실행한다.

작성 지원 및 분리: OpenAI Codex. 원 실험과 수치 동일성을 확인한 별도 추가 기능이다.
저장소 최상위에서 python -m experiments.run_detection --stage develop/final 실행.
v6의 test2는 여러 버전에서 확인한 후향 비교 자료다. v1은 HAI_Project/run.py로 재실행한다.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from detection.datasets import Dataset, download, sha256
from detection.metrics import intervals, pr
from detection.models import fit, raw
from detection.postprocess import split_second
from detection.selection import detectors, metrics, rank, save_curve, smooth
from detection.settings import KM_KEYS, MULTIPLIERS, PCA_KEYS

PROTOCOL = Path("docs/DETECTION_PROTOCOL.txt")


def write_json(path, value):
    """비 ASCII 문자를 유지해 설정과 검증 기록을 저장한다."""
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def source_hashes():
    """숫자에 영향을 주는 코드·설정·공통 모듈을 개발 동결에 포함한다."""
    files = sorted(Path("detection").glob("*.py"))
    files.extend([Path("detection/data_hashes.json"), Path("experiments/run_detection.py"), PROTOCOL])
    files.extend([Path("common/config.py"), Path("common/preprocess.py")])
    return {str(path): sha256(path) for path in files}


def develop(data, output):
    """test2를 읽지 않고 test1의 앞·뒤 구간에서 두 탐지기의 설정을 확정한다."""
    model, calibration = fit([1], PCA_KEYS + KM_KEYS, data)
    values, _, labels = data.read("test1")
    boundary = split_second(labels)
    configs, scores = detectors(model, calibration, values, labels[:boundary], output)
    rows, curves, multipliers = [], [], {}
    for family in ["PCA", "K-means"]:
        signal = scores[family][boundary:]
        candidates = pd.DataFrame([
            dict(mode=family, multiplier=threshold,
                 **metrics(labels[boundary:], signal, threshold))
            for threshold in MULTIPLIERS
        ])
        selected = rank(candidates).iloc[0]
        multipliers[family] = float(selected.multiplier)
        rows.extend(candidates.to_dict("records"))
        save_curve(curves, "development", family, signal, labels[boundary:], selected.multiplier)
    pd.DataFrame(rows).to_csv(output / "operating_grid.csv", index=False)
    pd.DataFrame(curves).to_csv(output / "pr_development.csv", index=False)
    freeze = dict(
        code=source_hashes(), manifest=data.manifest, features=data.columns,
        front_end=boundary, detectors=configs, multipliers=multipliers,
        training_seeds=model["seeds"], refit_files=[1, 2],
    )
    write_json(output / "selection.json", freeze)
    print(json.dumps(dict(detectors=configs, multipliers=multipliers), indent=2))


def evaluate(data, output):
    """확정한 설정으로 train1 대조군과 train1~2 재학습을 평가한다."""
    config = json.loads((output / "selection.json").read_text())
    if config["code"] != source_hashes() or config["features"] != data.columns:
        raise ValueError("개발 동결 이후 코드·스키마가 변경됐다. 설정을 다시 확인해야 한다.")
    rows, event_rows, curves, applied = [], [], [], {}
    keys = [item["key"] for item in config["detectors"].values()]
    for policy, ids in [("train1", [1]), ("train1-2", [1, 2])]:
        model, calibration = fit(ids, keys, data)
        thresholds = {}
        for family, settings in config["detectors"].items():
            normal_scores = np.concatenate([
                smooth(raw(model, block, settings["key"]), settings)
                for block in calibration
            ])
            thresholds[family] = float(np.quantile(normal_scores, settings["quantile"]))
            if policy == "train1":
                np.testing.assert_allclose(thresholds[family], settings["threshold"], rtol=1e-10)
        applied[policy] = dict(thresholds=thresholds, seeds=model["seeds"])
        for split in ["test2", "train4"]:
            values, times, labels = data.read(split)
            families = ["PCA"] if policy == "train1" else ["PCA", "K-means"]
            export = dict(timestamp=times, label=labels.astype(int))
            for family in families:
                settings = config["detectors"][family]
                score = smooth(raw(model, values, settings["key"]), settings) / thresholds[family]
                multiplier = config["multipliers"][family]
                prediction = score > multiplier
                rows.append(dict(policy=policy, split=split, mode=family, multiplier=multiplier,
                                 AP=pr(labels, score)[2] if labels.any() else None,
                                 **metrics(labels, score, multiplier)))
                if split == "test2":
                    save_curve(curves, policy, family, score, labels, multiplier)
                    for event, (start, end) in enumerate(intervals(labels), 1):
                        hits = np.flatnonzero(prediction[start:end])
                        event_rows.append(dict(policy=policy, mode=family, event=event,
                                               detected=bool(len(hits)),
                                               delay=int(hits[0]) if len(hits) else None))
                    export[f"{family}_score_ratio"] = score
                    export[f"{family}_alarm"] = prediction.astype(int)
            if policy == "train1-2" and split == "test2":
                pd.DataFrame(export).to_csv(output / "test2_scores.csv.gz", index=False)
            print("평가 완료", policy, split, flush=True)
    pd.DataFrame(rows).to_csv(output / "evaluation.csv", index=False)
    pd.DataFrame(event_rows).to_csv(output / "events.csv", index=False)
    pd.DataFrame(curves).to_csv(output / "pr_evaluation.csv", index=False)
    write_json(output / "applied_settings.json", applied)
    write_json(output / "data_manifest.json", data.manifest)


def main():
    """데이터 확보·개발·평가 단계를 명시적으로 구분한다."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True, choices=["fetch", "develop", "final"])
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--out", type=Path, default=Path("results/detection"))
    args = parser.parse_args()
    if args.stage == "fetch":
        download(args.data)
        return
    args.out.mkdir(parents=True, exist_ok=True)
    dataset = Dataset(args.data)
    if args.stage == "develop":
        develop(dataset, args.out)
    else:
        evaluate(dataset, args.out)


if __name__ == "__main__":
    main()
