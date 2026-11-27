"""common/ 단위 테스트 (작은 합성 입력, 실제 데이터 아님).

작성: Claude Code (Anthropic, claude-opus-5-5), 2026-11-27. 본인 요청.
실행: python -m unittest -v tests.test_common
"""

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from common.config import HAI_FILES
from common.data import load_and_check
from common.preprocess import fit_scaler, transform
from common.windows import transactions, window_labels


class TestPreprocess(unittest.TestCase):
    def test_fit_uses_front_fraction_and_constant_std(self):
        x = np.array([[1.0, 5.0], [3.0, 5.0], [100.0, 5.0], [100.0, 5.0], [100.0, 5.0]])
        s = fit_scaler(x, fit_fraction=0.4)          # 앞 2행만 사용
        self.assertEqual(s.cut, 2)
        self.assertEqual(s.mean.tolist(), [2.0, 5.0])
        self.assertEqual(s.std.tolist(), [1.0, 1.0])  # 둘째 열은 상수 → 1
        self.assertEqual(s.constant.tolist(), [False, True])

    def test_transform_fills_missing_with_median(self):
        x = np.array([[1.0], [3.0], [5.0], [7.0], [9.0]])
        s = fit_scaler(x, fit_fraction=1.0)
        z = transform(np.array([[np.nan]]), s)
        self.assertAlmostEqual(z[0, 0], (5.0 - 5.0) / s.std[0])  # 중앙값 5 로 채움


class TestWindows(unittest.TestCase):
    def test_integer_items(self):
        z = np.zeros((60, 4))
        z[:, 1] = 2.0    # 변수 1 HIGH → 항목 3
        z[:, 3] = -3.0   # 변수 3 LOW  → 항목 6
        self.assertEqual(transactions(z), [frozenset({3, 6})])

    def test_partial_window_dropped(self):
        z = np.ones((125, 3)) * 2
        self.assertEqual(len(transactions(z)), 2)

    def test_window_labels(self):
        y = np.zeros(130, dtype=int)
        y[70] = 1
        self.assertEqual(window_labels(y).tolist(), [0, 1])


class TestLoadAndCheck(unittest.TestCase):
    def _write(self, folder: Path, label2_minutes: list[str]):
        cols = [f"v{i}" for i in range(86)]
        ts1 = pd.date_range("2022-01-01 00:00:01", periods=3, freq="s")
        for name in ("hai-train1.csv", "hai-test1.csv", "hai-test2.csv"):
            df = pd.DataFrame(np.zeros((3, 86)), columns=cols)
            df.insert(0, "timestamp", ts1.strftime("%Y-%m-%d %H:%M:%S"))
            df.to_csv(folder / name, index=False)
        pd.DataFrame({"timestamp": ts1.strftime("%Y-%m-%d %H:%M:%S"), "label": [0, 1, 0]}).to_csv(
            folder / "label-test1.csv", index=False)
        pd.DataFrame({"timestamp": label2_minutes, "label": [0, 0, 1]}).to_csv(
            folder / "label-test2.csv", index=False)

    def test_ok_with_minute_labels(self):
        with tempfile.TemporaryDirectory() as d:
            self._write(Path(d), ["2022-01-01 0:00"] * 3)
            frames, manifest, stats, cols = load_and_check(Path(d))
            self.assertEqual(len(cols), 86)
            self.assertEqual([m["file"] for m in manifest], HAI_FILES)

    def test_rejects_misaligned_test2_labels(self):
        with tempfile.TemporaryDirectory() as d:
            self._write(Path(d), ["2022-01-01 0:00", "2022-01-01 0:00", "2022-01-01 0:01"])
            with self.assertRaises(AssertionError):
                load_and_check(Path(d))


if __name__ == "__main__":
    unittest.main()
