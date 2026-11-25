"""patterns/pcy.py 채점용 테스트.

작성: Claude Code (Anthropic, claude-opus-5-5), 2026-11-25. 본인 구현을 검증하기 위한 용도.
실행: python -m unittest -v tests.test_pcy   (dm-team3 폴더에서)
"""

import itertools
import random
import unittest

from patterns.apriori import apriori
from patterns.pcy import first_pass, frequent_bucket_bitmap, pair_hash, pcy, second_pass
from tests.test_apriori import TX, fs


def observed_frequent_item_pairs(transactions, min_count):
    """빈발 항목끼리 실제로 함께 나온 서로 다른 쌍의 수 (해시 필터가 없을 때의 후보 수)."""
    singles = apriori(transactions, min_count, max_k=1)
    freq = {next(iter(s)) for s in singles}
    pairs = set()
    for t in transactions:
        pairs.update(itertools.combinations(sorted(t & freq), 2))
    return len(pairs)


class TestHash(unittest.TestCase):
    def test_order_and_range(self):
        for n in (1, 7, 1024):
            h = pair_hash("I1", "I2", n)
            self.assertEqual(h, pair_hash("I2", "I1", n))
            self.assertTrue(0 <= h < n)


class TestPasses(unittest.TestCase):
    def test_first_pass(self):
        items, buckets = first_pass(TX, 50)
        self.assertEqual(items[fs("I1")], 6)
        self.assertEqual(items[fs("I2")], 7)
        self.assertEqual(len(buckets), 50)
        # 거래별 쌍의 수: 3+1+1+3+1+1+1+6+3 = 20. 모든 쌍이 정확히 한 버킷에 들어간다
        self.assertEqual(sum(buckets), 20)

    def test_bitmap(self):
        self.assertEqual(frequent_bucket_bitmap([1, 3, 0, 5], 3), [False, True, False, True])

    def test_second_pass_all_buckets_open(self):
        counts, n_cand = second_pass(TX, {"I1", "I2", "I3"}, [True] * 10, 10)
        self.assertEqual(counts, {fs("I1", "I2"): 4, fs("I1", "I3"): 4, fs("I2", "I3"): 4})
        self.assertEqual(n_cand, 3)

    def test_second_pass_all_buckets_closed(self):
        counts, n_cand = second_pass(TX, {"I1", "I2", "I3"}, [False] * 10, 10)
        self.assertEqual(counts, {})
        self.assertEqual(n_cand, 0)


class TestPCY(unittest.TestCase):
    def test_textbook_same_as_apriori(self):
        for n_buckets in (1, 3, 7, 101):
            got, _ = pcy(TX, 2, n_buckets)
            self.assertEqual(got, apriori(TX, 2, max_k=2), f"n_buckets={n_buckets}")

    def test_stats_keys(self):
        _, stats = pcy(TX, 2, 7)
        self.assertEqual(set(stats), {"n_frequent_items", "n_frequent_buckets", "n_candidates"})
        self.assertEqual(stats["n_frequent_items"], 5)

    def test_random_same_as_apriori_and_fewer_candidates(self):
        rng = random.Random(331)
        items = [f"x{i}" for i in range(15)]
        for _ in range(20):
            tx = [frozenset(rng.sample(items, rng.randint(0, 7))) for _ in range(60)]
            min_count = rng.randint(3, 10)
            n_buckets = rng.choice([1, 5, 17, 64, 500])
            got, stats = pcy(tx, min_count, n_buckets)
            self.assertEqual(got, apriori(tx, min_count, max_k=2))
            # 해시 필터는 후보를 줄일 수만 있고 늘릴 수는 없다
            self.assertLessEqual(stats["n_candidates"], observed_frequent_item_pairs(tx, min_count))

    def test_empty(self):
        got, stats = pcy([], 1, 10)
        self.assertEqual(got, {})
        self.assertEqual(stats["n_candidates"], 0)


if __name__ == "__main__":
    unittest.main()
