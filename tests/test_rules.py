"""patterns/rules.py 채점용 테스트.

작성: Claude Code (Anthropic, claude-opus-5-5), 2026-11-25. 본인 구현을 검증하기 위한 용도.
실행: python -m unittest -v tests.test_rules   (dm-team3 폴더에서)
"""

import itertools
import random
import unittest

from patterns.apriori import apriori
from patterns.rules import generate_rules, nonempty_proper_subsets, rule_metrics
from tests.test_apriori import EXPECTED, TX, fs


def as_keys(rules):
    return {(r["antecedent"], r["consequent"]) for r in rules}


def brute_force_rules(transactions, min_count, min_confidence):
    """거래를 직접 세서 규칙을 만드는 느린 정답 생성기 (비교용)."""
    n = len(transactions)

    def cnt(s):
        return sum(s <= t for t in transactions)

    items = sorted(set().union(*transactions)) if transactions else []
    out = {}
    for size in range(2, len(items) + 1):
        for combo in itertools.combinations(items, size):
            whole = frozenset(combo)
            c = cnt(whole)
            if c < min_count:
                continue
            for k in range(1, size):
                for a in itertools.combinations(combo, k):
                    a = frozenset(a)
                    b = whole - a
                    conf = c / cnt(a)
                    if conf >= min_confidence:
                        out[(a, b)] = (c / n, conf, conf / (cnt(b) / n))
    return out


class TestSubsets(unittest.TestCase):
    def test_three(self):
        got = nonempty_proper_subsets(fs("a", "b", "c"))
        self.assertEqual(len(got), 6)
        self.assertEqual(set(got), {fs("a"), fs("b"), fs("c"), fs("a", "b"), fs("a", "c"), fs("b", "c")})

    def test_single(self):
        self.assertEqual(list(nonempty_proper_subsets(fs("a"))), [])


class TestMetrics(unittest.TestCase):
    def test_I1I2_to_I5(self):
        s, c, l = rule_metrics(EXPECTED, 9, fs("I1", "I2"), fs("I5"))
        self.assertAlmostEqual(s, 2 / 9)
        self.assertAlmostEqual(c, 0.5)      # 2 / 4
        self.assertAlmostEqual(l, 2.25)     # 0.5 / (2/9)

    def test_I5_to_I1I2(self):
        s, c, l = rule_metrics(EXPECTED, 9, fs("I5"), fs("I1", "I2"))
        self.assertAlmostEqual(c, 1.0)      # 2 / 2
        self.assertAlmostEqual(l, 2.25)     # 1.0 / (4/9)


class TestGenerateRules(unittest.TestCase):
    def test_rule_format(self):
        rules = generate_rules(EXPECTED, 9, 0.0)
        self.assertTrue(rules)
        for r in rules:
            self.assertEqual(set(r), {"antecedent", "consequent", "support", "confidence", "lift"})
            self.assertFalse(r["antecedent"] & r["consequent"])  # A 와 B 는 겹치지 않는다

    def test_count_without_threshold(self):
        # 크기 2 빈발집합 6개 × 규칙 2개 + 크기 3 빈발집합 2개 × 규칙 6개 = 24
        self.assertEqual(len(generate_rules(EXPECTED, 9, 0.0)), 24)

    def test_textbook_high_confidence(self):
        rules = generate_rules(EXPECTED, 9, 0.7)
        from_125 = {k for k in as_keys(rules) if k[0] | k[1] == fs("I1", "I2", "I5")}
        self.assertEqual(from_125, {
            (fs("I1", "I5"), fs("I2")),
            (fs("I2", "I5"), fs("I1")),
            (fs("I5"), fs("I1", "I2")),
        })

    def test_singletons_only(self):
        self.assertEqual(generate_rules({fs("a"): 3, fs("b"): 2}, 5, 0.0), [])

    def test_random_vs_brute_force(self):
        rng = random.Random(331)
        items = [f"x{i}" for i in range(8)]
        for _ in range(15):
            tx = [frozenset(rng.sample(items, rng.randint(0, 5))) for _ in range(30)]
            min_count = rng.randint(2, 6)
            min_conf = rng.choice([0.0, 0.3, 0.6, 0.9])
            got = {(r["antecedent"], r["consequent"]): (r["support"], r["confidence"], r["lift"])
                   for r in generate_rules(apriori(tx, min_count), len(tx), min_conf)}
            want = brute_force_rules(tx, min_count, min_conf)
            self.assertEqual(set(got), set(want))
            for key, vals in want.items():
                for g, w in zip(got[key], vals):
                    self.assertAlmostEqual(g, w)


if __name__ == "__main__":
    unittest.main()
