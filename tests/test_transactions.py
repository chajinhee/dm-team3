"""patterns/transactions.py 단위 테스트 (작은 합성 입력, 실제 데이터 아님).

작성: Claude Code (Anthropic, claude-opus-5-5), 2026-11-25.
실행: python -m unittest -v tests.test_transactions
"""

import unittest

import numpy as np

from patterns.transactions import (ATTACK, add_attack_item, attack_events, fit_scaler,
                                   make_transactions, window_labels, window_means)


class TestTransactions(unittest.TestCase):
    def test_fit_scaler_constant_column(self):
        x = np.array([[1.0, 5.0], [3.0, 5.0], [100.0, 5.0], [100.0, 5.0], [100.0, 5.0]])
        mean, std = fit_scaler(x, fit_fraction=0.4)   # 앞 2 행만 사용
        self.assertEqual(mean.tolist(), [2.0, 5.0])
        self.assertEqual(std.tolist(), [1.0, 1.0])   # 두 번째 열은 상수 → 1

    def test_window_means_drops_tail(self):
        z = np.arange(10, dtype=float).reshape(5, 2)  # 5 시점, 창 2 → 2 창, 마지막 1 시점 버림
        self.assertEqual(window_means(z, 2).tolist(), [[1.0, 2.0], [5.0, 6.0]])

    def test_items_threshold_and_top_m(self):
        z = np.array([[3.0, -2.0, 0.5, -4.0]])
        cols = ["a", "b", "c", "d"]
        tx = make_transactions(z, cols, window=1, threshold=1.5, top_m=2)
        self.assertEqual(tx, [frozenset({"d=LOW", "a=HIGH"})])  # |z| 상위 2개
        tx = make_transactions(z, cols, window=1, threshold=1.5, top_m=10)
        self.assertEqual(tx, [frozenset({"d=LOW", "a=HIGH", "b=LOW"})])  # c 는 기준 미달

    def test_empty_window_kept(self):
        z = np.zeros((4, 2))
        self.assertEqual(make_transactions(z, ["a", "b"], 2, 1.5, 8), [frozenset(), frozenset()])

    def test_labels_and_attack_item(self):
        y = np.array([0, 0, 0, 1, 0, 0, 1])
        wl = window_labels(y, 2)               # [0, 1, 0] (마지막 1 시점 버림)
        self.assertEqual(wl.tolist(), [0, 1, 0])
        tx = add_attack_item([frozenset({"a"})] * 3, wl)
        self.assertEqual(tx[1], frozenset({"a", ATTACK}))
        self.assertEqual(tx[0], frozenset({"a"}))

    def test_attack_events(self):
        self.assertEqual(attack_events(np.array([0, 1, 1, 0, 1])), [(1, 3), (4, 5)])
        self.assertEqual(attack_events(np.array([0, 0])), [])


if __name__ == "__main__":
    unittest.main()
