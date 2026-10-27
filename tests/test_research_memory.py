import argparse
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'skills/research-cycle/scripts/memory.py'
spec = importlib.util.spec_from_file_location('memory', MODULE)
memory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(memory)


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / 'research.sqlite'
        self.contract = {'question': 'Compare', 'metric': {'key': 'score', 'direction': 'maximize'},
                         'max_attempts': 3, 'max_compute_seconds': 100,
                         'final_evaluation_reserve_seconds': 10}
        memory.initialize(self.db, self.contract)
        self.h = self.call('hypothesis', text='H', rationale='R', test='T')['id']
        self.config = self.write('config.json', {'seed': 1, 'lr': 1})
        self.metrics = self.write('metrics.json', {'score': 0.9})
        self.log = self.root / 'log.txt'
        self.log.write_text('actual log')

    def write(self, name, obj):
        path = self.root / name
        path.write_text(json.dumps(obj))
        return str(path)

    def call(self, command, **kw):
        return memory.perform(argparse.Namespace(command=command, db=str(self.db), **kw))

    def begin(self, seconds=30, config=None, retry=None):
        return self.call('begin', hypothesis=self.h, config=config or self.config,
                         reserve_seconds=seconds, retry_reason=retry)['id']

    def finish(self, eid, outcome='completed', seconds=20, metrics=True):
        return self.call('finish', experiment=eid, outcome=outcome, seconds=seconds,
                         metrics=self.metrics if metrics else None, evidence=[str(self.log)])

    def test_duplicate_and_retry_are_not_free(self):
        eid = self.begin()
        with self.assertRaises(ValueError):
            self.begin(retry='still running')
        self.finish(eid, 'failed', metrics=False)
        equivalent = self.write('equivalent.json', {'lr': 1.0, 'seed': 1.0})
        with self.assertRaises(ValueError):
            self.begin(config=equivalent)
        retry = self.begin(config=equivalent, retry='fixed environment')
        self.finish(retry)
        with self.assertRaises(ValueError):
            self.begin(retry='successful duplicate')
        self.assertEqual(self.call('snapshot')['attempts'], 2)

    def test_reservations_survive_reconnection_and_limit_parallel_work(self):
        self.begin(seconds=70)
        other = self.write('other.json', {'seed': 2})
        with self.assertRaises(ValueError):
            self.begin(seconds=21, config=other)
        self.assertEqual(self.call('snapshot')['compute_seconds_used_or_reserved'], 70)

    def test_bad_metrics_do_not_close_attempt(self):
        eid = self.begin()
        self.write('metrics.json', {'score': float('nan')})
        with self.assertRaises(ValueError):
            self.finish(eid)
        self.assertEqual(len(self.call('snapshot')['open_attempts']), 1)
        self.write('metrics.json', {'wrong_key': 0.9})
        with self.assertRaises(ValueError):
            self.finish(eid)

    def test_evidence_cannot_escape_and_findings_need_real_attempts(self):
        eid = self.begin()
        outside = self.root.parent / 'missing-evidence.txt'
        with self.assertRaises(ValueError):
            self.call('finish', experiment=eid, outcome='failed', seconds=1,
                      metrics=None, evidence=[str(outside)])
        with self.assertRaises(ValueError):
            self.call('finding', text='unsupported', experiments=[999], hypothesis_status='supported')

    def test_freeze_blocks_search_and_records_hashes(self):
        eid = self.begin()
        self.finish(eid)
        self.call('finding', text='bounded observation', experiments=[eid], hypothesis_status='uncertain')
        decision = self.write('decision.json', {'selected_attempt': eid})
        frozen = self.call('freeze', decision=decision, evidence=[str(self.log)])
        self.assertEqual(len(frozen['evidence'][0]['sha256']), 64)
        with self.assertRaises(ValueError):
            self.begin(config=self.write('new.json', {'seed': 2}))
        self.call('charge', seconds=5, evidence=[str(self.log)])
        self.call('close', status='achieved')
        with self.assertRaises(ValueError):
            self.call('charge', seconds=1, evidence=[str(self.log)])
        self.assertEqual(self.call('snapshot')['status'], 'achieved')

    def test_overrun_is_recorded_and_not_silently_clipped(self):
        eid = self.begin(seconds=10)
        self.assertTrue(self.finish(eid, seconds=11)['budget_violation'])
        snapshot = self.call('snapshot')
        self.assertEqual(snapshot['status'], 'budget_violation')
        self.assertEqual(snapshot['compute_seconds_used_or_reserved'], 11)
        with self.assertRaises(ValueError):
            self.begin(config=self.write('new.json', {'seed': 2}))
        with self.assertRaises(ValueError):
            self.call('close', status='achieved')
        self.call('close', status='invalid')

    def test_failed_attempts_exhaust_count_even_with_zero_compute(self):
        for i in range(3):
            eid = self.begin(config=self.write('attempt.json', {'seed': i}))
            self.finish(eid, outcome='failed', seconds=0, metrics=False)
        with self.assertRaises(ValueError):
            self.begin(config=self.write('attempt.json', {'seed': 99}))
        self.assertEqual(self.call('snapshot')['attempts'], 3)

    def test_confirmation_status_is_not_inferred_from_one_high_score(self):
        self.finish(self.begin())
        with self.assertRaises(ValueError):
            self.call('close', status='achieved')
        self.assertEqual(self.call('snapshot')['status'], 'running')

    def test_events_are_append_only_and_contract_cannot_be_reinitialized(self):
        with self.assertRaises(ValueError):
            memory.initialize(self.db, self.contract)
        with sqlite3.connect(self.db) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE events SET kind='rewrite'")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('DELETE FROM events')


if __name__ == '__main__':
    unittest.main()
