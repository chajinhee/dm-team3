import unittest,itertools
from collections import Counter
import numpy as np
import pandas as pd
from run import metrics, intervals, mine_pairs, signature, jacc, transactions, sqdist

class PipelineTests(unittest.TestCase):
 def test_intervals(self):
  self.assertEqual(intervals([0,1,1,0,1]),[(1,3),(4,5)])
 def test_metrics(self):
  r=metrics([0,1,1,0],[0,1,0,1]);self.assertEqual(r['tp'],1);self.assertAlmostEqual(r['f1'],.5);self.assertEqual(r['event_recall'],1);self.assertEqual(r['delay_median_s'],0)
 def test_zero_baseline(self):
  r=metrics([0,1],[0,0]);self.assertEqual(r['f1'],0);self.assertIsNone(r['delay_median_s'])
 def test_pcy_exhaustive(self):
  rng=np.random.default_rng(331)
  tx=[frozenset(np.flatnonzero(rng.random(12)<.4).tolist()) for _ in range(200)]
  brute=Counter(p for t in tx for p in itertools.combinations(sorted(t),2));expected={p:n for p,n in brute.items() if n>=20}
  for buckets in [1,7,1024]:
   self.assertEqual(mine_pairs(tx,.1,buckets,True)[0],expected)
  self.assertEqual(mine_pairs(tx,.1,pcy=False)[0],expected)
 def test_jaccard(self):
  self.assertAlmostEqual(jacc({1,2},{2,3}),1/3);self.assertEqual(jacc(set(),set()),1)
 def test_signature_identical(self):
  s=signature([{1,3},{3,1}],np.array([5,7]),np.array([2,4]));np.testing.assert_array_equal(s[0],s[1])
 def test_distance(self):
  np.testing.assert_allclose(sqdist(np.array([[0.,0.],[3.,4.]]),np.array([[0.,0.]])),[[0],[25]])
 def test_windows_no_partial(self):
  z=np.ones((125,3))*2;tx=transactions(z);self.assertEqual(len(tx),2);self.assertEqual(tx[0],frozenset({1,3,5}))
 def test_label_minute_alignment(self):
  a=pd.Series(pd.to_datetime(['2022-08-17 00:00:01','2022-08-17 00:00:02']))
  b=pd.Series(pd.to_datetime(['2022-08-17 00:00','2022-08-17 00:00']))
  self.assertTrue(a.dt.floor('min').equals(b));self.assertFalse(b.is_unique)
if __name__=='__main__':unittest.main(verbosity=2)
