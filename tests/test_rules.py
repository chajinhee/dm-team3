"""patterns/rules.py 채점용 테스트.

작성: Claude Code (Anthropic, claude-opus-5-5), 2026-11-25. 본인 구현을 검증하기 위한 용도.
실행: python -m unittest -v tests.test_rules   (dm-team3 폴더에서)
"""

import itertools
import random
import unittest

from patterns.apriori import apriori
from patterns.rules import generate_rules, interest, nonempty_proper_subsets, rule_metrics
from tests.test_apriori import EXPECTED, TX, fs

# 강의자료 DM_03-Association Rules 의 예제 바구니 (PDF p.14 와 p.18. p.18 은 B3 에 n 이 추가됨)
LECTURE_P14 = [fs("m", "c", "b"), fs("m", "p", "j"), fs("m", "b"), fs("c", "j"),
               fs("m", "p", "b"), fs("m", "c", "b", "j"), fs("c", "b", "j"), fs("b", "c")]
LECTURE_P18 = [fs("m", "c", "b"), fs("m", "p", "j"), fs("m", "c", "b", "n"), fs("c", "j"),
               fs("m", "p", "b"), fs("m", "c", "b", "j"), fs("c", "b", "j"), fs("b", "c")]


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
            self.assertEqual(set(r), {"antecedent", "consequent", "support", "confidence", "interest", "lift"})
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


class TestLectureExamples(unittest.TestCase):
    """강의자료의 손 계산 예제를 그대로 재현하는지 확인한다."""

    def test_p14_confidence_and_interest(self):
        # 강의 p.14: {m,b} -> c 의 지지도 2, {m,b} 지지도 4, {c} 지지도 5,
        #            confidence 2/4 = 0.5, interest |0.5 - 5/8| = 1/8
        freq = apriori(LECTURE_P14, 1)
        self.assertEqual(freq[fs("m", "b", "c")], 2)
        self.assertEqual(freq[fs("m", "b")], 4)
        self.assertEqual(freq[fs("c")], 5)
        _, conf, _ = rule_metrics(freq, 8, fs("m", "b"), fs("c"))
        self.assertAlmostEqual(conf, 0.5)
        self.assertAlmostEqual(interest(conf, 5 / 8), 1 / 8)
        rule = next(r for r in generate_rules(freq, 8, 0.0)
                    if r["antecedent"] == fs("m", "b") and r["consequent"] == fs("c"))
        self.assertAlmostEqual(rule["interest"], 1 / 8)

    def test_interest_is_absolute(self):
        # 강의 p.13: 음의 연관도 잡기 위해 절댓값을 쓴다
        self.assertAlmostEqual(interest(0.1, 0.6), 0.5)
        self.assertAlmostEqual(interest(0.9, 0.4), 0.5)

    def test_p18_frequent_itemsets(self):
        # 강의 p.18: 지지도 기준 3 일 때 빈발 집합 {b,m} {b,c} {c,m} {c,j} {m,c,b} (단일 항목 제외)
        freq = apriori(LECTURE_P18, 3)
        multi = {s for s in freq if len(s) >= 2}
        self.assertEqual(multi, {fs("b", "m"), fs("b", "c"), fs("c", "m"), fs("c", "j"), fs("m", "c", "b")})

    def test_p18_rule_confidences(self):
        # 강의 p.18 에 적힌 confidence 값: b->m 4/6, b->c 5/6, b,c->m 3/5, m->b 4/5, b,m->c 3/4, b->c,m 3/6
        rules = {(r["antecedent"], r["consequent"]): r["confidence"]
                 for r in generate_rules(apriori(LECTURE_P18, 3), 8, 0.0)}
        self.assertAlmostEqual(rules[(fs("b"), fs("m"))], 4 / 6)
        self.assertAlmostEqual(rules[(fs("b"), fs("c"))], 5 / 6)
        self.assertAlmostEqual(rules[(fs("b", "c"), fs("m"))], 3 / 5)
        self.assertAlmostEqual(rules[(fs("m"), fs("b"))], 4 / 5)
        self.assertAlmostEqual(rules[(fs("b", "m"), fs("c"))], 3 / 4)
        self.assertAlmostEqual(rules[(fs("b"), fs("c", "m"))], 3 / 6)

    def test_p18_confidence_threshold(self):
        # 강의 p.18 의 기준 s = 3, c = 0.75 로 걸렀을 때 남는 규칙 (손 계산)
        got = {(r["antecedent"], r["consequent"]) for r in generate_rules(apriori(LECTURE_P18, 3), 8, 0.75)}
        self.assertEqual(got, {
            (fs("b"), fs("c")),        # 5/6
            (fs("c"), fs("b")),        # 5/6
            (fs("m"), fs("b")),        # 4/5
            (fs("j"), fs("c")),        # 3/4
            (fs("b", "m"), fs("c")),   # 3/4
            (fs("c", "m"), fs("b")),   # 3/3
        })


if __name__ == "__main__":
    unittest.main()
