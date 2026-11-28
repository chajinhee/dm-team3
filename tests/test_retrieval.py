"""검색 모듈 단위 테스트.

담당: 보안 B (공통 모듈은 통합 담당 검토 대상).
작성 지원: BAZE Mindlogic; 팀원 검토 및 작성자 실명은 PR 전 기입.
보고서: 3.7절. 강의자료 쪽 번호는 확인 후 기입.
"""
import unittest
import numpy as np
from retrieval.minhash import jacc, signature
from retrieval.lsh import build_index, candidates
from retrieval.search import topk


class RetrievalTests(unittest.TestCase):
    def test_jaccard(self):
        """공통 항목 비율과 공집합 규칙을 확인한다."""
        self.assertAlmostEqual(jacc({1, 2}, {2, 3}), 1 / 3)
        self.assertEqual(jacc(set(), set()), 1)

    def test_signature_identical(self):
        """같은 집합은 입력 순서에 무관하게 서명이 같다."""
        rows = signature([{1, 3}, {3, 1}], np.array([5, 7]), np.array([2, 4]))
        np.testing.assert_array_equal(rows[0], rows[1])

    def test_lsh_band_match(self):
        """밴드 하나가 완전히 일치할 때만 후보로 선택한다."""
        index = build_index(np.array([[0] * 64, [1] * 64]))
        self.assertEqual(candidates(index, [0] * 4 + [2] * 60), {0})
        self.assertEqual(candidates(index, [2] * 64), set())

    def test_topk_ties(self):
        """동점이면 번호가 작은 사례를 먼저 반환한다."""
        np.testing.assert_array_equal(topk([0.3, 0.3, 0.4], 2), [2, 0])
