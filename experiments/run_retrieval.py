"""보안 B 검색 실험 단독 실행.

담당: 보안 B (공통 모듈은 통합 담당 검토 대상).
작성 지원: BAZE Mindlogic; 팀원 검토 및 작성자 실명은 PR 전 기입.
보고서: 4.3·5.5절. 강의자료 쪽 번호는 확인 후 기입.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from common.config import SEED
from common.data import download_hai, load_and_check
from common.preprocess import fit_scaler, transform
from common.windows import transactions
from retrieval.search import retrieval

MAX_QUERIES = 200


def main():
    """CLI 인자를 받아 검색 결과 CSV와 JSON을 출력한다."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--out', type=Path, default=Path('results/retrieval'))
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    if args.download:
        download_hai(args.data)

    frames, manifest, _stats, columns = load_and_check(args.data)
    scaler = fit_scaler(frames['hai-train1.csv'][columns].to_numpy(float))
    gallery = transactions(transform(frames['hai-test1.csv'][columns].to_numpy(float), scaler))
    # test2는 최종 질의용이며 스케일러 적합이나 설정 선택에 쓰지 않는다.
    test = transactions(transform(frames['hai-test2.csv'][columns].to_numpy(float), scaler))
    eligible = [i for i, items in enumerate(test) if items]
    rng = np.random.default_rng(SEED)
    ids = sorted(rng.choice(eligible, min(MAX_QUERIES, len(eligible)), replace=False).tolist())
    rows, build = retrieval(gallery, [(i, test[i]) for i in ids])
    means = rows[['minhash_recall5', 'lsh_recall5', 'exact_ms', 'minhash_ms',
                  'lsh_ms', 'candidates']].mean().to_dict()
    means.update(queries=len(rows), gallery=len(gallery), index_build_s=build)
    summary = dict(seed=SEED, dev_windows=len(gallery), test_windows=len(test),
                   empty_dev_windows=sum(not t for t in gallery),
                   empty_test_windows=sum(not t for t in test), retrieval=means)
    args.out.mkdir(parents=True, exist_ok=True)
    rows.to_csv(args.out / 'retrieval_queries.csv', index=False)
    (args.out / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    (args.out / 'data_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
