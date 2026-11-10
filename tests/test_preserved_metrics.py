"""Historical metric payloads are frozen by explicit project requirement."""
import hashlib
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]/'docs/benchmarks/2026-11-cheng'
EXPECTED={
    'metrics.json':'5cbcbf7a126f63ea9ecb01ea68036c89ccf71e76feb1f23a591f8a4ed4df4709',
    'seed_metrics.csv':'a0a24abe99ae330d31aafd7215984c043868745856eecebe2cc4bcee2a3b30b3',
    'adaptive_trials.json':'3c39e0353f1fc35ff4390b124053918c2a6347f81409ba2def757067d08ff73b',
}

class PreservedMetricsTests(unittest.TestCase):
    def test_historical_metric_payloads_are_unchanged(self):
        for name,value in EXPECTED.items():
            with self.subTest(name=name):self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),value)

if __name__=='__main__':unittest.main()
