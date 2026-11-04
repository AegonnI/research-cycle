import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

EXECUTOR=Path(os.environ.get('ADAPTIVE_EXECUTOR_DIR',Path(__file__).resolve().parents[1]/'examples/cheng-adaptive/executor'))
sys.path.insert(0,str(EXECUTOR))
from common import config,packed,file_hash,scientific
from controller import Controller,recipe

class AdaptiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        for name in ['executor','agent','inputs']:(self.root/name).mkdir()
        contract={'max_wall_seconds':28800,'report_reserve_seconds':0,'runtime_python':sys.executable,'metric':{'target':.92}}
        (self.root/'executor/contract.json').write_text(json.dumps(contract))
        (self.root/'executor/catalogue.json').write_text(json.dumps({'resnet18':{'parameters':1000},'resnet34':{'parameters':1000}}))
        (self.root/'inputs/records.json').write_text(json.dumps([{'index':i,'label':i,'split':'val'} for i in range(3)]))
        (self.root/'agent/TASK.md').write_text('fixed task')
        seal={'files':{p.relative_to(self.root).as_posix():file_hash(p) for p in self.root.rglob('*') if p.is_file()}}
        (self.root/'executor/seal.json').write_text(json.dumps(seal))
        self.c=Controller(self.root,worker=False);self.addCleanup(self.c.shutdown);self.c.start()

    def trial(self,seed=1,**overrides):return {'architecture':'resnet18','seed':seed,'epochs':10,**overrides}
    def complete(self,trial_id,score=.90,status='completed',late=False):
        with self.c.db() as db:
            study=db.execute('SELECT * FROM study').fetchone()
            finished=study['started']+28801 if late else time.time()
            metrics={'validation_macro_f1':score,'validation_seconds':.1,'parameters':1000}
            db.execute('UPDATE trials SET status=?,elapsed=1,finished=?,metrics=?,artifacts=? WHERE id=?',
                       (status,finished,packed(metrics) if status=='completed' else None,'{}',trial_id))
            self.c.event(db,'finished',{'id':trial_id,'status':status,'elapsed':1,'error':None,'artifacts':{}})
    def candidate(self,seed=1,**kw):
        i=self.c.submit([self.trial(seed,**kw)])['accepted_ids'][0];self.complete(i);return i
    def group(self,seed=1,scores=(.93,.94,.92)):
        r=self.c.confirm(self.candidate(seed))
        for i,score in zip(r['confirmation_ids'],scores):self.complete(i,score)
        return r

    def test_new_config_has_no_short_timeout_or_30_epoch_ceiling(self):
        c=config(self.trial(epochs=500));self.assertIsNone(c['timeout_seconds']);self.assertEqual(c['epochs'],500)
    def test_no_total_attempt_or_compute_limit(self):
        with self.c.db() as db:db.execute("INSERT INTO charges(seconds,reason) VALUES(999999,'fixture, descriptive only')")
        for seed in range(105):self.c.submit([self.trial(seed)])
        self.assertEqual(self.c.info()['attempts'],105)
    def test_confirmation_can_start_after_one_candidate(self):
        r=self.c.confirm(self.candidate(),epochs=50)
        self.assertEqual(len(r['confirmation_ids']),3)
        self.assertEqual(len(set(r['seeds'])),3)
        self.assertNotIn(1,r['seeds'])
        for i in r['confirmation_ids']:self.assertEqual(json.loads(self.c.artifacts(i)['config'])['epochs'],50)
    def test_retry_changes_timeout_without_changing_science_or_erasing_failure(self):
        first=self.c.submit([self.trial(timeout_seconds=180)])['accepted_ids'][0];self.complete(first,status='timeout')
        second=self.c.retry(first,'Need longer process wall',timeout_seconds=900)['accepted_id']
        a=json.loads(self.c.artifacts(first)['config']);b=json.loads(self.c.artifacts(second)['config'])
        self.assertEqual(scientific(a),scientific(b));self.assertEqual(b['timeout_seconds'],900)
        self.assertEqual(self.c.info()['statuses']['timeout'],1)
    def test_retry_default_removes_old_timeout(self):
        first=self.c.submit([self.trial(timeout_seconds=180)])['accepted_ids'][0];self.complete(first,status='timeout')
        second=self.c.retry(first,'Use global deadline')['accepted_id']
        self.assertIsNone(json.loads(self.c.artifacts(second)['config'])['timeout_seconds'])
    def test_no_early_success_from_single_score(self):
        self.candidate();self.assertRaises(ValueError,self.c.finalize)
    def test_three_seed_mean_not_best_seed_determines_success(self):
        self.group(scores=(.99,.5,.5));self.assertFalse(self.c.info()['confirmations'][0]['target_met'])
        with self.assertRaises(ValueError):self.c.finalize()
    def test_below_target_can_return_to_search(self):
        self.group(scores=(.9,.9,.9));self.c.submit([self.trial(22,lr=.002)])
        self.assertEqual(self.c.info()['statuses']['queued'],1)
    def test_same_recipe_cannot_reroll_seeds(self):
        self.group()
        with self.assertRaisesRegex(ValueError,'already'):self.c.confirm(1)
    def test_confirmation_seeds_are_forbidden_in_search(self):
        r=self.c.confirm(self.candidate())
        with self.assertRaises(ValueError):self.c.submit([self.trial(r['seeds'][0])])
    def test_failed_confirmation_can_retry_with_longer_wall_and_preserve_group(self):
        r=self.c.confirm(self.candidate());ids=r['confirmation_ids']
        self.complete(ids[0],status='timeout');self.complete(ids[1],.93);self.complete(ids[2],.94)
        new=self.c.retry(ids[0],'Longer deadline',timeout_seconds=900)['accepted_id'];self.complete(new,.95)
        result=self.c.finalize();self.assertTrue(result['target_met']);self.assertEqual(result['status'],'complete')
        self.assertEqual(result['attempts'],5)
    def test_goal_close_cancels_queue_and_closed_state_is_immutable(self):
        self.group();self.c.submit([self.trial(99,lr=.002)])
        result=self.c.finalize();self.assertEqual(result['statuses']['cancelled'],1)
        with self.c.db() as db:
            with self.assertRaises(sqlite3.IntegrityError):db.execute("UPDATE study SET status='running'")
            with self.assertRaises(sqlite3.IntegrityError):db.execute('DELETE FROM trials')
    def test_deadline_closes_honestly_without_confirmations(self):
        self.c.submit([self.trial()]);future=time.time()+28801
        with patch('time.time',return_value=future):result=self.c.finalize()
        self.assertFalse(result['target_met']);self.assertEqual(result['status'],'inconclusive');self.assertEqual(result['statuses']['cancelled'],1)
    def test_late_confirmations_cannot_satisfy_goal(self):
        r=self.c.confirm(self.candidate())
        for i in r['confirmation_ids']:self.complete(i,.99,late=True)
        self.assertFalse(self.c.info()['confirmations'][0]['target_met'])
    def test_group_or_event_tampering_is_detected(self):
        self.group()
        with self.c.db() as db:
            db.execute('DROP TRIGGER no_group_delete');db.execute('DELETE FROM confirmations')
            with self.assertRaisesRegex(ValueError,'mismatch'):self.c.integrity(db)
    def test_path_boundaries_and_seal(self):
        with self.assertRaises(ValueError):self.c.note('../executor/contract.json','overwrite')
        with self.assertRaises(ValueError):self.c.read('../executor/contract.json')
        (self.root/'inputs/records.json').write_text('[]')
        with self.assertRaises(ValueError):self.c.verify_seal()

if __name__=='__main__':unittest.main()
