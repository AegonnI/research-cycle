"""Adaptive goal owner: only global wall deadline, verified three-seed target."""
import copy
import json
from pathlib import Path
import secrets
import sqlite3
import threading
import time

from common import config, raw_config, scientific, packed, digest, file_hash
from ledger import Controller as Ledger, recompute

GROUP_SCHEMA='''
CREATE TABLE IF NOT EXISTS confirmations(id INTEGER PRIMARY KEY, candidate_id INTEGER NOT NULL,
 recipe_hash TEXT UNIQUE NOT NULL, config TEXT NOT NULL, seeds TEXT NOT NULL,
 trial_ids TEXT NOT NULL, created REAL NOT NULL);
CREATE TRIGGER IF NOT EXISTS no_group_edit BEFORE UPDATE ON confirmations BEGIN SELECT RAISE(ABORT,'confirmation immutable'); END;
CREATE TRIGGER IF NOT EXISTS no_group_delete BEFORE DELETE ON confirmations BEGIN SELECT RAISE(ABORT,'confirmation immutable'); END;
'''

def recipe(c):
    return {k:v for k,v in scientific(c).items() if k!='seed'}

class Controller(Ledger):
    def __init__(self,root,worker=True,verify=True):
        super().__init__(root,worker=False,verify=verify)
        with self.db() as db:db.executescript(GROUP_SCHEMA)
        if worker:
            self.thread=threading.Thread(target=self.loop,daemon=True);self.thread.start()

    def used(self,db):
        return sum(r['elapsed'] for r in db.execute('SELECT elapsed FROM trials'))+db.execute('SELECT COALESCE(SUM(seconds),0) FROM charges').fetchone()[0]

    def groups(self,db):
        rows=list(db.execute('SELECT * FROM trials ORDER BY id'));study=db.execute('SELECT * FROM study').fetchone()
        deadline=study['started']+self.contract['max_wall_seconds'] if study['started'] else float('inf')
        result=[]
        for g in db.execute('SELECT * FROM confirmations ORDER BY id'):
            frozen=json.loads(g['config']);seeds=json.loads(g['seeds']);members={}
            for r in rows:
                c=json.loads(r['config'])
                if c['stage']=='confirm' and digest(recipe(c))==g['recipe_hash'] and c['seed'] in seeds:
                    if r['status']=='completed' and r['finished'] is not None and r['finished']<=deadline:
                        members[c['seed']]={'trial_id':r['id'],'score':json.loads(r['metrics'])['validation_macro_f1']}
            mean=sum(x['score'] for x in members.values())/3 if set(members)==set(seeds) else None
            result.append({'id':g['id'],'candidate_id':g['candidate_id'],'recipe':frozen,'seeds':seeds,
                           'completed_seeds':members,'mean_validation_macro_f1':mean,
                           'target_met':mean is not None and mean>=self.contract['metric']['target']})
        return result

    def info(self):
        with self.lock,self.db() as db:
            study=dict(db.execute('SELECT * FROM study').fetchone());rows=list(db.execute('SELECT * FROM trials ORDER BY id'))
            short=[]
            for r in rows:
                c=json.loads(r['config']);m=json.loads(r['metrics']) if r['metrics'] else {}
                short.append({'id':r['id'],'architecture_id':c['architecture_id'],'stage':c['stage'],
                              'epochs':c['epochs'],'seed':c['seed'],'status':r['status'],'elapsed':r['elapsed'],
                              'score':m.get('validation_macro_f1'),'error':r['error']})
            return {'study':study,'attempts':len(rows),'statuses':{s:sum(r['status']==s for r in rows) for s in ['queued','running','completed','failed','timeout','cancelled']},
                    'wall_remaining_seconds':max(0,self.wall_remaining(study)),'compute_used_seconds':self.used(db),
                    'target':self.contract['metric']['target'],'confirmations':self.groups(db),'coverage':self.coverage(rows),
                    'coverage_is_descriptive_only':True,'recent_trials':short[-16:],
                    'leaders':sorted([r for r in short if r['score'] is not None],key=lambda r:r['score'],reverse=True)[:8],
                    'limits':'Only total wall time. No attempt, coverage, separate compute or fixed reserve limits.',
                    'ranking_warning':'Screening scores at different fidelities/seeds are provisional.',
                    'llm_requests':None,'llm_tokens':None}

    def probe(self,raw):
        c=config(raw)
        with self.db() as db:
            state=db.execute('SELECT * FROM study').fetchone()
            if state['status'] not in ('ready','running') or self.wall_remaining(state)<=0:raise ValueError('Study closed or deadline reached')
        if c['architecture']!='custom':return {**c,'actual_parameters':self.catalogue[c['architecture']]['parameters']}
        key=c['architecture_id']
        if key not in self.probes:
            import subprocess
            path=self.executor/'probe-config.json';path.write_text(packed(raw_config(c)))
            started=time.monotonic();p=None
            try:
                with self.db() as db:remaining=self.wall_remaining(db.execute('SELECT * FROM study').fetchone())
                p=subprocess.run([self.contract['runtime_python'],'-B',str(self.executor/'trainer.py'),'--probe','--config',str(path)],
                                 capture_output=True,text=True,timeout=max(.01,remaining))
            finally:
                elapsed=time.monotonic()-started
                with self.db() as db:
                    db.execute('INSERT INTO charges(seconds,reason) VALUES(?,?)',(elapsed,'custom architecture probe'))
                    self.event(db,'probe',{'architecture_id':key,'seconds':elapsed,'passed':p is not None and p.returncode==0})
            if p.returncode:raise ValueError('Custom constructor failed: '+p.stderr[-1500:])
            self.probes[key]=json.loads(p.stdout)
        return {**c,'actual_parameters':self.probes[key]['parameters']}

    def _submit(self,db,c,reason=None,confirmation=False):
        study=db.execute('SELECT * FROM study').fetchone()
        if study['status'] not in ('ready','running') or study['started'] is None:raise ValueError('Use START_ADAPTIVE.cmd; study must be open with its operator clock started')
        if self.wall_remaining(study)<=0:raise ValueError('Global deadline reached')
        if c['stage']=='confirm' and not confirmation:raise ValueError('Use study_confirm for fresh-seed verification')
        reserved_seeds={seed for g in db.execute('SELECT seeds FROM confirmations') for seed in json.loads(g['seeds'])}
        if not confirmation and c['seed'] in reserved_seeds:raise ValueError('Confirmation seeds cannot be used in search')
        fp=digest({'science':scientific(c),'seal':digest(self.seal)})
        previous=list(db.execute('SELECT status FROM trials WHERE fingerprint=?',(fp,)))
        if previous and (not reason or any(r['status'] not in ('failed','timeout','cancelled') for r in previous)):
            raise ValueError('Duplicate scientific config; use study_retry for failed jobs, with a longer timeout if needed')
        now=time.time();limit=c['timeout_seconds'] or self.wall_remaining(study)
        cursor=db.execute('INSERT INTO trials(config,fingerprint,status,reserved,created) VALUES(?,?,?,?,?)',
                          (packed(c),fp,'queued',limit,now))
        trial_id=cursor.lastrowid
        self.event(db,'submitted',{'id':trial_id,'fingerprint':fp,'config':c,'retry_reason':reason})
        return trial_id

    def retry(self,trial_id,reason,timeout_seconds=None):
        if not isinstance(reason,str) or not reason.strip():raise ValueError('A concrete retry reason is required')
        with self.lock,self.db() as db:
            row=db.execute('SELECT * FROM trials WHERE id=?',(trial_id,)).fetchone()
            if not row or row['status'] not in ('failed','timeout','cancelled'):raise ValueError('Only failed/timeout/cancelled jobs can be retried')
            c=json.loads(row['config']);c['timeout_seconds']=timeout_seconds
            c={**config(raw_config(c)),'actual_parameters':c['actual_parameters']}
            accepted=self._submit(db,c,reason,c['stage']=='confirm')
        self.wakeup.set();return {'accepted_id':accepted}

    def confirm(self,trial_id,epochs=None,timeout_seconds=None):
        with self.lock,self.db() as db:
            if db.execute("SELECT 1 FROM trials WHERE status IN ('queued','running')").fetchone():raise ValueError('Finish pending jobs before freezing a confirmation recipe')
            row=db.execute('SELECT * FROM trials WHERE id=?',(trial_id,)).fetchone()
            if not row or row['status']!='completed':raise ValueError('Choose a completed candidate trial')
            c=json.loads(row['config'])
            if c['stage']=='confirm':raise ValueError('Choose a search candidate, not a confirmation seed')
            c.update(stage='confirm',epochs=epochs if epochs is not None else c['epochs'],timeout_seconds=timeout_seconds)
            c={**config(raw_config(c)),'actual_parameters':c['actual_parameters']}
            key=digest(recipe(c))
            if db.execute('SELECT 1 FROM confirmations WHERE recipe_hash=?',(key,)).fetchone():raise ValueError('This recipe already has a confirmation group; retry failed members rather than rerolling seeds')
            used={json.loads(r['config'])['seed'] for r in db.execute('SELECT config FROM trials')}
            # Never recycle older conventional confirmation seeds or any seed from this study.
            used.update([137,211,307]);seeds=[]
            while len(seeds)<3:
                seed=secrets.randbelow(2147483647)
                if seed not in used:seeds.append(seed);used.add(seed)
            ids=[]
            for seed in seeds:
                trial=copy.deepcopy(c);trial['seed']=seed;ids.append(self._submit(db,trial,confirmation=True))
            cursor=db.execute('INSERT INTO confirmations(candidate_id,recipe_hash,config,seeds,trial_ids,created) VALUES(?,?,?,?,?,?)',
                              (trial_id,key,packed(c),packed(seeds),packed(ids),time.time()))
            self.event(db,'confirmation_locked',{'group_id':cursor.lastrowid,'candidate_id':trial_id,'recipe_hash':key,'config':c,'seeds':seeds,'trial_ids':ids})
        self.wakeup.set();return {'group_id':cursor.lastrowid,'confirmation_ids':ids,'seeds':seeds,'frozen_recipe':recipe(c)}

    def artifacts(self,trial_id):
        row=super().artifacts(trial_id);folder=self.executor/'runs'/f'{trial_id:06d}'
        for name in ['history.json','stdout.log','stderr.log']:
            p=folder/name
            if p.is_file():
                if name=='history.json':row['history_last_50_epochs']=json.loads(p.read_text())[-50:]
                else:row[name+'_tail']=p.read_text(errors='replace')[-6000:]
        return row

    def integrity(self,db):
        super().integrity(db)
        locks=[json.loads(e['payload']) for e in db.execute("SELECT payload FROM events WHERE kind='confirmation_locked'")]
        groups=list(db.execute('SELECT * FROM confirmations ORDER BY id'))
        if [g['id'] for g in groups]!=[e['group_id'] for e in locks]:raise ValueError('Confirmation/event mismatch')
        prior=set()
        for group,event in zip(groups,locks):
            seeds=json.loads(group['seeds']);ids=json.loads(group['trial_ids']);c=json.loads(group['config'])
            if len(seeds)!=3 or len(set(seeds))!=3 or prior.intersection(seeds):raise ValueError('Invalid fresh confirmation seeds')
            if event['recipe_hash']!=group['recipe_hash'] or event['config']!=c or event['seeds']!=seeds or event['trial_ids']!=ids or digest(recipe(c))!=group['recipe_hash']:raise ValueError('Frozen recipe changed')
            for seed,trial_id in zip(seeds,ids):
                r=db.execute('SELECT config FROM trials WHERE id=?',(trial_id,)).fetchone();actual=json.loads(r['config'])
                if actual['seed']!=seed or actual['stage']!='confirm' or recipe(actual)!=recipe(c):raise ValueError('Confirmation member changed')
            search_seeds={json.loads(r['config'])['seed'] for r in db.execute('SELECT config FROM trials') if json.loads(r['config'])['stage']!='confirm'}
            if search_seeds.intersection(seeds):raise ValueError('Confirmation seed leaked into search')
            prior.update(seeds)

    def cancel_queued(self,db,reason):
        for r in db.execute("SELECT * FROM trials WHERE status='queued'").fetchall():
            db.execute("UPDATE trials SET status='cancelled',elapsed=0,finished=?,error=?,artifacts='{}' WHERE id=?",(time.time(),reason,r['id']))
            self.event(db,'finished',{'id':r['id'],'status':'cancelled','elapsed':0,'error':reason,'artifacts':{}})

    def save_live(self):
        report=self.agent/'report';report.mkdir(exist_ok=True)
        p=report/'LIVE_RESULTS.json';temp=p.with_suffix('.tmp')
        temp.write_text(json.dumps(self.info(),ensure_ascii=False,indent=2));temp.replace(p)

    def loop(self):
        while not self.stop.is_set():
            with self.lock,self.db() as db:
                study=db.execute('SELECT * FROM study').fetchone()
                if study['status'] not in ('ready','running'):return
                expired=study['started'] is not None and self.wall_remaining(study)<=0
                met=any(g['target_met'] for g in self.groups(db))
                if expired or met:
                    self.cancel_queued(db,'Global deadline reached' if expired else 'Verified confirmation target reached');row=None
                else:
                    row=db.execute("SELECT * FROM trials WHERE status='queued' ORDER BY id LIMIT 1").fetchone()
                    if row:
                        self.event(db,'started',{'id':row['id']})
                        db.execute("UPDATE trials SET status='running',started=? WHERE id=?",(time.time(),row['id']))
            if expired or met:self.finalize();return
            if row:
                self.execute(row);self.save_live()
            else:self.wakeup.wait(.5);self.wakeup.clear()

    def finalize(self):
        started=time.monotonic()
        with self.lock,self.db() as db:
            study=db.execute('SELECT * FROM study').fetchone()
            if study['status'] not in ('ready','running'):return json.loads(study['selection'])
            groups=self.groups(db);met=any(g['target_met'] for g in groups);expired=study['started'] is not None and self.wall_remaining(study)<=0
            if not met and not expired:raise ValueError('Target not confirmed and wall time remains: continue research')
            if db.execute("SELECT 1 FROM trials WHERE status='running'").fetchone():raise ValueError('Active process must finish or stop first')
            self.cancel_queued(db,'Target met' if met else 'Global deadline reached')
            integrity='passed';error=None
            try:self.verify_seal();self.integrity(db)
            except Exception as exc:integrity='failed';error=str(exc)
            rows=list(db.execute('SELECT * FROM trials ORDER BY id'));complete=[g for g in groups if g['mean_validation_macro_f1'] is not None]
            ranking=sorted(complete,key=lambda g:(-g['mean_validation_macro_f1'],g['id']))
            best=ranking[0] if ranking else None;status='invalid' if error else ('complete' if met else 'inconclusive')
            elapsed=time.monotonic()-started
            result={'status':status,'stop_reason':'integrity_failure' if error else ('target_reached' if met else 'wall_deadline'),
                    'target':self.contract['metric']['target'],'target_met':met and not error,
                    'winner':best['recipe']['architecture_id'] if best else None,
                    'mean_validation_macro_f1':best['mean_validation_macro_f1'] if best else None,'confirmations':groups,
                    'attempts':len(rows),'statuses':{s:sum(r['status']==s for r in rows) for s in ['completed','failed','timeout','cancelled','queued','running']},
                    'coverage':self.coverage(rows),'compute_used_seconds':self.used(db)+elapsed,
                    'wall_seconds':time.time()-study['started'] if study['started'] else 0,
                    'research_deadline_unix':study['started']+self.contract['max_wall_seconds'] if study['started'] else None,
                    'closing_audit_seconds':elapsed,'closing_may_finish_after_deadline':True,'llm_tokens':None,'llm_requests':None,
                    'integrity':integrity,'integrity_error':error,'test_used':False}
            db.execute('INSERT INTO charges(seconds,reason) VALUES(?,?)',(elapsed,'final integrity verification'))
            self.event(db,'finalized',result)
            db.execute('UPDATE study SET status=?,phase=?,selection=? WHERE id=1',(status,'closed',packed(result)))
        report=self.agent/'report';report.mkdir(exist_ok=True)
        (report/'verified_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
        lines=['# Проверенный результат адаптивного исследования','',f'Статус: {status}',f'Причина: {result["stop_reason"]}',
               f'Цель: mean validation macro-F1 >= {result["target"]} на трёх новых seeds.',
               f'Победитель подтверждений: {result["winner"]}; среднее: {result["mean_validation_macro_f1"]}',
               f'Попытки: {len(rows)}; статусы: {packed(result["statuses"])}',
               f'Учтённые вычисления: {result["compute_used_seconds"]:.2f} с (отдельного лимита нет).',
               f'Wall до записи результата: {result["wall_seconds"]:.2f} с; deadline исследований: 28800 с.',
               'После deadline новые эксперименты не допускаются; поздние результаты не подтверждают цель.',
               f'Целостность: {integrity}. Ошибка: {error}',
               'LLM-токены/запросы: unknown. Test не использовался.','',
               '| Группа | Архитектура | Mean validation F1 | Цель |','|---|---|---:|---|']
        lines += [f'| {g["id"]} | {g["recipe"]["architecture_id"]} | {g["mean_validation_macro_f1"]} | {g["target_met"]} |' for g in groups]
        (report/'VERIFIED_RESULTS.md').write_text('\n'.join(lines)+'\n')
        (self.agent/'notes').mkdir(exist_ok=True)
        (self.agent/'notes/LAST_CHECKPOINT.json').write_text(json.dumps({'next_action':'closed','reason':result['stop_reason'],'report':'report/verified_results.json'},indent=2))
        self.save_live();return result

    def shutdown(self):
        self.stop.set();self.wakeup.set()
        if self.active:self.kill(self.active)
        if self.thread and threading.current_thread()!=self.thread:self.thread.join(timeout=60)
        with self.db() as db:
            study=db.execute('SELECT * FROM study').fetchone();running=db.execute("SELECT 1 FROM trials WHERE status='running'").fetchone()
        if not running and study['status']=='running' and self.wall_remaining(study)<=0:self.finalize()
