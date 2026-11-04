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

    def test_renaming_execution_does_not_bypass_duplicate_detection(self):
        first = self.write('first.json', {'science': {'seed': 1, 'lr': 0.001},
                                         'execution': {'run_id': 'A', 'output_dir': 'a'}})
        self.finish(self.begin(config=first))
        renamed = self.write('renamed.json', {'science': {'lr': 0.001, 'seed': 1},
                                             'execution': {'run_id': 'B', 'output_dir': 'b'}})
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.begin(config=renamed)
        changed_seed = self.write('seed.json', {'science': {'lr': 0.001, 'seed': 2}})
        self.begin(config=changed_seed)

    def test_legacy_operational_fields_and_fidelity_are_handled_separately(self):
        first = self.write('a.json', {'seed': 1, 'run_id': 'a', 'fidelity': {'stage': 'screen', 'epochs': 2}})
        self.finish(self.begin(config=first))
        renamed = self.write('b.json', {'seed': 1, 'run_id': 'b', 'fidelity': {'stage': 'screen', 'epochs': 2}})
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.begin(config=renamed)
        longer = self.write('c.json', {'seed': 1, 'fidelity': {'stage': 'promote', 'epochs': 10}})
        self.finish(self.begin(config=longer))
        result = self.call('snapshot', stage='promote')
        self.assertEqual(len(result['best']), 1)
        self.assertEqual(result['best'][0]['config']['fidelity']['epochs'], 10)

    def test_method_scope_rejects_forbidden_or_missing_declarations(self):
        scope = {'required_fields': ['family'], 'allowed_values': {'pretrained': [False]},
                 'forbidden_values': {'family': ['transformer']},
                 'numeric_bounds': {'parameters': {'min': 10, 'max': 30}}}
        good = {'family': 'cnn', 'pretrained': False, 'parameters': 20}
        memory.validate_scope(good, scope)
        for bad in [{**good, 'family': 'transformer'}, {**good, 'parameters': 31},
                    {**good, 'pretrained': True}, {'pretrained': False, 'parameters': 20}]:
            with self.assertRaises(ValueError):
                memory.validate_scope(bad, scope)
        other_db = self.root / 'scoped.sqlite'
        memory.initialize(other_db, {**self.contract, 'method_scope': scope})
        h = memory.perform(argparse.Namespace(command='hypothesis', db=str(other_db), text='H', rationale='R', test='T'))['id']
        bad_path = self.write('forbidden.json', {'science': {**good, 'family': 'transformer'}})
        with self.assertRaisesRegex(ValueError, 'Forbidden'):
            memory.perform(argparse.Namespace(command='begin', db=str(other_db), hypothesis=h,
                config=bad_path, reserve_seconds=10, retry_reason=None))
        self.assertEqual(memory.perform(argparse.Namespace(command='snapshot', db=str(other_db)))['attempts'], 0)

    def test_explicit_config_cannot_hide_scientific_fields_outside_science(self):
        with self.assertRaises(ValueError):
            memory.scientific_config({'science': {'seed': 1}, 'lr': 0.1})
        with self.assertRaises(ValueError):
            memory.scientific_config({'execution': {'run_id': 'A'}, 'science': {}})

    def test_checkpoint_recovers_across_connections_and_references_real_trials(self):
        eid = self.begin()
        self.finish(eid)
        note = self.write('next.json', {'next_action': 'Confirm', 'reason': 'Promising', 'evidence_ids': [eid]})
        self.call('checkpoint', note=note)
        self.assertEqual(self.call('snapshot')['checkpoint']['next_action'], 'Confirm')
        bad = self.write('bad.json', {'next_action': 'Confirm', 'reason': 'Unknown', 'evidence_ids': [999]})
        with self.assertRaises(ValueError):
            self.call('checkpoint', note=bad)

    def test_audit_detects_modified_trial_and_frozen_evidence(self):
        self.finish(self.begin())
        self.assertEqual(self.call('audit')['audit'], 'passed')
        self.log.write_text('modified log')
        with self.assertRaisesRegex(ValueError, 'Audit failed'):
            self.call('audit')
        self.log.write_text('actual log')
        decision = self.write('decision.json', {'choice': 1})
        self.call('freeze', decision=decision, evidence=[str(self.log)])
        self.assertFalse(self.call('audit')['scientific_goal_verified'])
        Path(decision).write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Audit failed'):
            self.call('audit')

    def test_audit_rejects_unresolved_process_reservations(self):
        self.begin()
        with self.assertRaisesRegex(ValueError, 'open attempts'):
            self.call('audit')


if __name__ == '__main__':
    unittest.main()
