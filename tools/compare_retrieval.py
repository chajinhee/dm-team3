"""Compare only the outputs shared by the original and retrieval runners."""
import argparse
import json
from pathlib import Path

import pandas as pd

TIMING_COLUMNS = ('exact_ms', 'minhash_ms', 'lsh_ms')
SUMMARY_KEYS = ('queries', 'gallery', 'candidates', 'minhash_recall5', 'lsh_recall5')


def read_json(folder, name):
    return json.loads((folder / name).read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    args = parser.parse_args()
    before, after = args.before, args.after
    first = pd.read_csv(before / 'retrieval_queries.csv').drop(columns=list(TIMING_COLUMNS))
    second = pd.read_csv(after / 'retrieval_queries.csv').drop(columns=list(TIMING_COLUMNS))
    if len(first) != 200 or len(second) != 200:
        raise ValueError('Expected 200 queries in each CSV')
    pd.testing.assert_frame_equal(first, second, check_exact=True)
    if read_json(before, 'data_manifest.json') != read_json(after, 'data_manifest.json'):
        raise ValueError('Data manifests differ')
    a = read_json(before, 'summary.json')['retrieval']
    b = read_json(after, 'summary.json')['retrieval']
    for key in SUMMARY_KEYS:
        if a[key] != b[key]:
            raise ValueError(f'Retrieval summary mismatch for {key}: {a[key]} != {b[key]}')
    print('OK: 200 queries, data manifest and non-timing retrieval summary match.')


if __name__ == '__main__':
    main()
