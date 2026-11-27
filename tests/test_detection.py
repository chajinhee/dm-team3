"""탐지 코드 분리 때 생길 수 있는 시점·경계·동점 처리 회귀를 검사한다.

작성 지원: OpenAI Codex. 작은 합성 입력과 독립 계산 기준을 사용한다.
"""
import unittest

import numpy as np

from common.preprocess import transform
from detection.metrics import measure, pr
from detection.pca import fit_normal
from detection.postprocess import causal_score


class DetectionRegressionTests(unittest.TestCase):
    def test_confirmation_does_not_backdate_and_is_causal(self):
        raw = np.array([0., 0., 2., 2., 2., 0., 0., 9.])
        score = causal_score(raw, span=1, confirm=3, hold=1)
        np.testing.assert_array_equal(score > 1, [False, False, False, False, True, False, False, False])
        for stop in range(1, len(raw) + 1):
            np.testing.assert_array_equal(causal_score(raw[:stop], 1, 3, 1), score[:stop])

    def test_normal_file_boundary_excluded_from_lagged_fit(self):
        rng = np.random.default_rng(331)
        normal = {1: rng.normal(size=(80, 4)), 2: rng.normal(5., size=(80, 4))}
        model, _ = fit_normal(normal, (1, 2))
        fitted = [transform(x[:48], model["scaler"]) for x in normal.values()]
        delay, beta, _ = model["parts"][1]
        self.assertEqual(delay, 1)
        count = sum(len(x) - 1 for x in fitted)
        xx = sum(x[:-1].T @ x[:-1] for x in fitted)
        xy = sum(x[:-1].T @ x[1:] for x in fitted)
        expected = np.linalg.solve(xx + np.eye(4) * count * .0001, xy)
        np.testing.assert_allclose(beta, expected)
        # 창 경계의 마지막 행→다음 파일 첫 행을 이어 붙인 계산과 구분한다.
        joined = np.concatenate(fitted)
        incorrect = np.linalg.solve(
            joined[:-1].T @ joined[:-1] + np.eye(4) * (len(joined)-1) * .0001,
            joined[:-1].T @ joined[1:],
        )
        self.assertFalse(np.allclose(beta, incorrect))

    def test_ap_groups_ties(self):
        recall, precision, ap = pr(np.array([1, 0, 1, 0], bool), np.array([2., 2., 1., 0.]))
        np.testing.assert_allclose(recall, [.5, 1., 1.])
        np.testing.assert_allclose(precision, [.5, 2/3, .5])
        self.assertAlmostEqual(ap, .5*.5 + .5*2/3)

    def test_false_run_count_and_duration_are_distinct(self):
        result = measure(np.zeros(3600, bool), np.r_[np.ones(60, bool), np.zeros(3540, bool)])
        self.assertEqual(result["false_alarms_per_normal_hour"], 1)
        self.assertEqual(result["false_positive_seconds_per_normal_hour"], 60)


if __name__ == "__main__":
    unittest.main()
