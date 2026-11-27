"""patterns/apriori.py 채점용 테스트.

작성: Claude Code (Anthropic, claude-opus-5-5), 2026-11-25. 본인 구현을 검증하기 위한 용도.
실행: python -m unittest -v tests.test_apriori   (dm-team3 폴더에서)
"""

import itertools
import random
import unittest

from patterns.apriori import apriori, count_candidates, count_singletons, generate_candidates


def fs(*items):
    return frozenset(items)


# 교과서식 9개 거래 예제 (최소 지지도 개수 2). 정답은 손으로 확인 가능하다.
TX = [
    fs("I1", "I2", "I5"),
    fs("I2", "I4"),
    fs("I2", "I3"),
    fs("I1", "I2", "I4"),
    fs("I1", "I3"),
    fs("I2", "I3"),
    fs("I1", "I3"),
    fs("I1", "I2", "I3", "I5"),
    fs("I1", "I2", "I3"),
]

EXPECTED = {
    fs("I1"): 6, fs("I2"): 7, fs("I3"): 6, fs("I4"): 2, fs("I5"): 2,
    fs("I1", "I2"): 4, fs("I1", "I3"): 4, fs("I1", "I5"): 2,
    fs("I2", "I3"): 4, fs("I2", "I4"): 2, fs("I2", "I5"): 2,
    fs("I1", "I2", "I3"): 2, fs("I1", "I2", "I5"): 2,
}


def brute_force(transactions, min_count):
    """모든 부분집합을 직접 세는 느린 정답 생성기 (Apriori 아님, 비교용)."""
    counts = {}
    for t in transactions:
        for k in range(1, len(t) + 1):
            for sub in itertools.combinations(sorted(t), k):
                counts[frozenset(sub)] = counts.get(frozenset(sub), 0) + 1
    return {s: c for s, c in counts.items() if c >= min_count}


class TestSteps(unittest.TestCase):
    def test_count_singletons(self):
        got = count_singletons(TX)
        self.assertEqual(got[fs("I1")], 6)
        self.assertEqual(got[fs("I4")], 2)
        self.assertEqual(len(got), 5)

    def test_join_makes_size_k(self):
        l2 = [k for k in EXPECTED if len(k) == 2]
        for c in generate_candidates(l2, 3):
            self.assertEqual(len(c), 3)

    def test_prune(self):
        # {I1,I3,I5}: 부분집합 {I3,I5} 가 L2 에 없으므로 잘려야 한다.
        l2 = [k for k in EXPECTED if len(k) == 2]
        c3 = generate_candidates(l2, 3)
        self.assertEqual(c3, {fs("I1", "I2", "I3"), fs("I1", "I2", "I5")})

    def test_count_candidates(self):
        got = count_candidates(TX, {fs("I1", "I2"), fs("I4", "I5")})
        self.assertEqual(got[fs("I1", "I2")], 4)
        self.assertEqual(got.get(fs("I4", "I5"), 0), 0)


class TestLectureP40(unittest.TestCase):
    def test_careful_candidate_generation(self):
        # 강의 p.40 주석: L2 = {b,m} {b,c} {c,m} {c,j} 일 때 {b,m,j} 는 {m,j} 가 빈발이 아니므로
        # 후보가 될 수 없다. 부분집합 가지치기를 하면 C3 에는 {b,c,m} 만 남는다.
        l2 = [fs("b", "m"), fs("b", "c"), fs("c", "m"), fs("c", "j")]
        self.assertEqual(generate_candidates(l2, 3), {fs("b", "c", "m")})


class TestApriori(unittest.TestCase):
    def test_textbook(self):
        self.assertEqual(apriori(TX, 2), EXPECTED)

    def test_max_k(self):
        got = apriori(TX, 2, max_k=2)
        self.assertEqual(got, {k: v for k, v in EXPECTED.items() if len(k) <= 2})

    def test_empty(self):
        self.assertEqual(apriori([], 1), {})
        self.assertEqual(apriori(TX, 100), {})

    def test_random_vs_brute_force(self):
        rng = random.Random(331)
        items = [f"x{i}" for i in range(10)]
        for _ in range(20):
            tx = [frozenset(rng.sample(items, rng.randint(0, 6))) for _ in range(40)]
            min_count = rng.randint(2, 8)
            self.assertEqual(apriori(tx, min_count), brute_force(tx, min_count))


if __name__ == "__main__":
    unittest.main()
