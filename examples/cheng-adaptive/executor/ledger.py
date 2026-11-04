"""Trusted study owner. Agent interface never exposes SQL, shell, resets or code edits."""
import copy
import csv
import json
import math
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import threading
import time

from common import config, raw_config, scientific, packed, digest, file_hash


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, *args):
        try:return super().__exit__(*args)
        finally:self.close()

SCHEMA = '''
CREATE TABLE study(id INTEGER PRIMARY KEY CHECK(id=1),contract_hash TEXT NOT NULL,started REAL,status TEXT NOT NULL,phase TEXT NOT NULL,selection TEXT);
CREATE TABLE trials(id INTEGER PRIMARY KEY AUTOINCREMENT,config TEXT NOT NULL,fingerprint TEXT NOT NULL,status TEXT NOT NULL,reserved REAL NOT NULL,elapsed REAL NOT NULL DEFAULT 0,created REAL NOT NULL,started REAL,finished REAL,metrics TEXT,error TEXT,artifacts TEXT);
CREATE TABLE events(id INTEGER PRIMARY KEY AUTOINCREMENT,time REAL NOT NULL,kind TEXT NOT NULL,payload TEXT NOT NULL,previous_hash TEXT NOT NULL,event_hash TEXT NOT NULL);
CREATE TABLE charges(id INTEGER PRIMARY KEY,seconds REAL NOT NULL,reason TEXT NOT NULL);
CREATE TRIGGER no_event_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'events immutable'); END;
CREATE TRIGGER no_event_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'events immutable'); END;
CREATE TRIGGER no_trial_delete BEFORE DELETE ON trials BEGIN SELECT RAISE(ABORT,'attempts cannot be deleted'); END;
CREATE TRIGGER no_science_edit BEFORE UPDATE OF config,fingerprint,reserved,created ON trials BEGIN SELECT RAISE(ABORT,'scientific configuration immutable'); END;
CREATE TRIGGER no_finished_edit BEFORE UPDATE ON trials WHEN OLD.status IN ('completed','failed','timeout','cancelled') BEGIN SELECT RAISE(ABORT,'closed attempt immutable'); END;
CREATE TRIGGER no_study_delete BEFORE DELETE ON study BEGIN SELECT RAISE(ABORT,'study cannot be deleted'); END;
CREATE TRIGGER no_contract_edit BEFORE UPDATE OF contract_hash ON study BEGIN SELECT RAISE(ABORT,'contract immutable'); END;
CREATE TRIGGER no_clock_reset BEFORE UPDATE OF started ON study WHEN OLD.started IS NOT NULL AND NEW.started!=OLD.started BEGIN SELECT RAISE(ABORT,'clock cannot reset'); END;
CREATE TRIGGER no_reopen BEFORE UPDATE ON study WHEN OLD.status IN ('complete','inconclusive','invalid','stopped') BEGIN SELECT RAISE(ABORT,'closed study immutable'); END;
'''


def recompute(path, expected):
    predicted = {}
    with path.open(newline='') as stream:
        for row in csv.DictReader(stream):
            index = int(row['index'])
            if index not in expected or index in predicted:
                raise ValueError('Duplicate/unknown validation index')
            probabilities = [float(row['p'+str(i)]) for i in range(3)]
            if any(not math.isfinite(p) or p < 0 for p in probabilities) or abs(sum(probabilities)-1) > .001:
                raise ValueError('Invalid probability row')
            predicted[index] = max(range(3), key=lambda k: probabilities[k])
    if set(predicted) != set(expected):
        raise ValueError('Incomplete validation predictions')
    cm = [[0]*3 for _ in range(3)]
    for index, label in expected.items():
        cm[label][predicted[index]] += 1
    f = []
    for i in range(3):
        denominator = sum(cm[i])+sum(cm[j][i] for j in range(3))
        f.append(2*cm[i][i]/denominator if denominator else 0.)
    return {'validation_macro_f1': sum(f)/3, 'validation_accuracy': sum(cm[i][i] for i in range(3))/len(expected),
            'confusion_matrix': cm, 'per_class_f1': f}


class Controller:
    def __init__(self, root, worker=True, verify=True):
        self.root = Path(root).resolve(); self.executor = self.root/'executor'
        self.inputs = self.root/'inputs'; self.agent = self.root/'agent'
        self.contract = json.loads((self.executor/'contract.json').read_text(encoding='utf-8-sig'))
        self.seal = json.loads((self.executor/'seal.json').read_text())
        if verify:
            self.verify_seal()
        self.catalogue = json.loads((self.executor/'catalogue.json').read_text())
        records = json.loads((self.inputs/'records.json').read_text())
        self.expected = {r['index']:r['label'] for r in records if r['split']=='val'}
        if not self.expected or any(r['split'] not in ('train','val') for r in records):
            raise ValueError('Missing validation or forbidden split')
        self.db_path = self.executor/'study.sqlite'
        self.lock = threading.RLock(); self.stop = threading.Event(); self.wakeup = threading.Event()
        self.active = None; self.probes = {}; self.thread = None
        if not self.db_path.exists():
            db = self.db(); db.executescript(SCHEMA)
            with db:
                db.execute('INSERT INTO study VALUES(1,?,NULL,?,?,NULL)',(digest(self.contract),'ready','search'))
                self.event(db,'initialized',{'contract_hash':digest(self.contract),'seal_hash':digest(self.seal)})
            db.close()
        with self.db() as db:
            if db.execute('SELECT contract_hash FROM study').fetchone()[0] != digest(self.contract):
                raise ValueError('Contract differs from the original study')
            if db.execute("SELECT id FROM trials WHERE status='running'").fetchone():
                raise ValueError('Unresolved running attempt. Operator must reconcile it; no automatic reset.')
        if worker:
            self.thread = threading.Thread(target=self.loop,daemon=True); self.thread.start()

    def db(self):
        db = sqlite3.connect(self.db_path,timeout=10,factory=ClosingConnection); db.row_factory = sqlite3.Row
        return db

    def verify_seal(self, code_only=False):
        for relative, expected in self.seal['files'].items():
            if code_only and relative.startswith('inputs/'):
                continue
            path = (self.root/relative).resolve(); path.relative_to(self.root)
            if not path.is_file() or file_hash(path) != expected:
                raise ValueError('Trusted input/code modified: '+relative)

    def event(self, db, kind, payload):
        previous = db.execute('SELECT event_hash FROM events ORDER BY id DESC LIMIT 1').fetchone()
        previous = previous[0] if previous else '0'*64
        timestamp = time.time(); text = packed(payload)
        value = digest({'time':timestamp,'kind':kind,'payload':text,'previous_hash':previous})
        db.execute('INSERT INTO events(time,kind,payload,previous_hash,event_hash) VALUES(?,?,?,?,?)',
                   (timestamp,kind,text,previous,value))

    def usage(self, db):
        rows = list(db.execute('SELECT * FROM trials ORDER BY id'))
        used = sum(r['elapsed'] if r['status'] not in ('queued','running') else r['reserved'] for r in rows)
        used += db.execute('SELECT COALESCE(SUM(seconds),0) FROM charges').fetchone()[0]
        return rows, used

    def coverage(self, rows):
        architectures = {json.loads(r['config'])['architecture_id']:json.loads(r['config']) for r in rows if r['status']=='completed'}
        return {'trained_architectures':len(architectures),'library_architectures':sum(c['family']!='custom_cnn' for c in architectures.values()),
                'custom_architectures':sum(c['family']=='custom_cnn' for c in architectures.values()),
                'families':len({c['family'] for c in architectures.values()})}

    def coverage_passed(self, rows):
        actual = self.coverage(rows)
        return all(actual[key.removeprefix('min_')]>=value for key,value in self.contract['coverage'].items())

    def wall_remaining(self, study):
        return self.contract['max_wall_seconds']-max(0,time.time()-study['started']) if study['started'] else self.contract['max_wall_seconds']

    def search_limit(self):
        return self.contract['max_attempts']-self.contract['confirmation_attempt_reserve']

    def search_exhausted(self, db):
        rows, used = self.usage(db)
        count = sum(json.loads(r['config'])['stage']!='confirm' for r in rows)
        return (count>=self.search_limit() or
                used+self.contract['confirmation_training_reserve_seconds']+self.contract['final_evaluation_reserve_seconds']+20>=self.contract['max_compute_seconds'])

    def info(self):
        with self.lock,self.db() as db:
            study = dict(db.execute('SELECT * FROM study').fetchone()); rows, used = self.usage(db)
            short = []
            for row in rows:
                c=json.loads(row['config']); m=json.loads(row['metrics']) if row['metrics'] else {}
                short.append({'id':row['id'],'architecture_id':c['architecture_id'],'family':c['family'],
                              'stage':c['stage'],'epochs':c['epochs'],'seed':c['seed'],'status':row['status'],
                              'score':m.get('validation_macro_f1'),'elapsed':row['elapsed'],'error':row['error']})
            return {'study':study,'attempts':len(rows),'statuses':{s:sum(r['status']==s for r in rows) for s in ('queued','running','completed','failed','timeout','cancelled')},
                    'compute_used_or_reserved_seconds':used,'compute_remaining_seconds':max(0,self.contract['max_compute_seconds']-used),
                    'wall_remaining_seconds':max(0,self.wall_remaining(study)),'coverage':self.coverage(rows),
                    'coverage_passed':self.coverage_passed(rows),'search_attempt_limit':self.search_limit(),
                    'search_exhausted':self.search_exhausted(db),'recent_trials':short[-16:],
                    'leaders':sorted([r for r in short if r['score'] is not None],key=lambda r:r['score'],reverse=True)[:8],
                    'ranking_warning':'Only compare scores at equal training fidelity.',
                    'llm_requests':None,'llm_tokens':None,'llm_enforcement':'Not observed by this executor; operator/provider telemetry required.'}

    def start(self):
        """Operator launcher starts the global clock before the first LLM turn."""
        with self.lock,self.db() as db:
            study=db.execute('SELECT * FROM study').fetchone()
            if study['status'] not in ('ready','running'):
                raise ValueError('Study already closed; cannot restart')
            if study['started'] is None:
                db.execute("UPDATE study SET started=?,status='running' WHERE id=1",(time.time(),))
                self.event(db,'study_started_by_operator',{})
        return self.info()

    def probe(self, raw):
        c=config(raw)
        if c['architecture']!='custom':
            result=self.catalogue[c['architecture']]
            return {**c,'actual_parameters':result['parameters']}
        key=c['architecture_id']
        if key not in self.probes:
            with self.db() as db:
                state=db.execute('SELECT * FROM study').fetchone(); _,used=self.usage(db)
                if state['status'] not in ('ready','running') or used+45>self.contract['max_compute_seconds'] or self.wall_remaining(state)<self.contract['report_reserve_seconds']+45:
                    raise ValueError('Probe budget exhausted or study closed')
            path=self.executor/'probe-config.json'; path.write_text(packed(raw_config(c)))
            started=time.monotonic()
            result=None
            try:
                result=subprocess.run([self.contract['runtime_python'],'-B',str(self.executor/'trainer.py'),
                                       '--probe','--config',str(path)],capture_output=True,text=True,timeout=45)
            finally:
                elapsed=time.monotonic()-started
                with self.db() as db:
                    db.execute('INSERT INTO charges(seconds,reason) VALUES(?,?)',(elapsed,'custom architecture probe'))
                    self.event(db,'probe',{'architecture_id':key,'seconds':elapsed,'passed':result is not None and result.returncode==0})
            if result.returncode:
                raise ValueError('Custom model rejected: '+result.stderr[-1500:])
            self.probes[key]=json.loads(result.stdout)
        return {**c,'actual_parameters':self.probes[key]['parameters']}

    def _submit(self, db, c, reason=None, confirmation=False):
        study=db.execute('SELECT * FROM study').fetchone(); rows, used=self.usage(db)
        if study['status'] not in ('ready','running'):
            raise ValueError('Study is closed')
        if study['started'] is None:
            raise ValueError('Use START_CONTROLLED.cmd: operator must start the global clock')
        if self.wall_remaining(study)<=self.contract['report_reserve_seconds']:
            raise ValueError('Wall budget reserved for finalization; no new jobs')
        if len(rows)>=self.contract['max_attempts']:
            raise ValueError('Attempt budget exhausted')
        if c['stage']=='confirm' and not confirmation:
            raise ValueError('Confirmation jobs are created only by study_confirm')
        if not confirmation and (study['phase']!='search' or self.search_exhausted(db)):
            raise ValueError('Search allocation exhausted or phase locked')
        margin=self.contract['final_evaluation_reserve_seconds']+(0 if confirmation else self.contract['confirmation_training_reserve_seconds'])
        reservation=c['timeout_seconds']+5  # bounded cleanup, metrics verification and hashing
        if used+reservation+margin>self.contract['max_compute_seconds']:
            raise ValueError('Not enough unreserved compute for this timeout')
        seeds=self.contract['evaluation']['confirmation_seeds']
        if c['stage']!='confirm' and c['seed'] in seeds:
            raise ValueError('Confirmation seeds cannot be used in preliminary search')
        fp=digest({'science':scientific(c),'seal':digest(self.seal)})
        previous=list(db.execute('SELECT status FROM trials WHERE fingerprint=?',(fp,)))
        if previous and (not reason or any(r['status'] not in ('failed','timeout','cancelled') for r in previous)):
            raise ValueError('Duplicate scientific config; only failed trials can be retried with a reason')
        now=time.time()
        cursor=db.execute('INSERT INTO trials(config,fingerprint,status,reserved,created) VALUES(?,?,?,?,?)',
                          (packed(c),fp,'queued',reservation,now))
        trial_id=cursor.lastrowid
        self.event(db,'submitted',{'id':trial_id,'fingerprint':fp,'config':c,'retry_reason':reason})
        return trial_id

    def submit(self, configs):
        if not isinstance(configs,list) or not 1<=len(configs)<=12:
            raise ValueError('Submit 1..12 configurations per batch')
        with self.lock:
            normalized=[self.probe(raw) for raw in configs]
            with self.db() as db:
                ids=[self._submit(db,c) for c in normalized]
            self.wakeup.set()
            return {'accepted_ids':ids,'status':self.info()}

    def retry(self, trial_id, reason):
        if not isinstance(reason,str) or not reason.strip():
            raise ValueError('Retry needs a concrete reason')
        with self.lock,self.db() as db:
            row=db.execute('SELECT * FROM trials WHERE id=?',(trial_id,)).fetchone()
            if not row or row['status'] not in ('failed','timeout','cancelled'):
                raise ValueError('Only failed/timeout/cancelled jobs can be retried')
            c=json.loads(row['config']); result=self._submit(db,c,reason,c['stage']=='confirm')
            self.wakeup.set(); return {'accepted_id':result}

    def confirm(self, ids):
        if not isinstance(ids,list) or len(ids)!=2 or len(set(ids))!=2:
            raise ValueError('Choose two different completed promotion trial IDs')
        with self.lock,self.db() as db:
            study=db.execute('SELECT * FROM study').fetchone(); rows,_=self.usage(db)
            if study['phase']!='search' or any(r['status'] in ('queued','running') for r in rows):
                raise ValueError('Finish all pending search jobs before confirmation')
            if not self.search_exhausted(db) or not self.coverage_passed(rows):
                raise ValueError('Search allocation and coverage are not satisfied; inspect study_info')
            chosen=[]
            for trial_id in ids:
                row=db.execute('SELECT * FROM trials WHERE id=?',(trial_id,)).fetchone()
                if not row or row['status']!='completed':
                    raise ValueError('Candidate is not a completed trial')
                chosen.append(json.loads(row['config']))
            if chosen[0]['architecture_id']==chosen[1]['architecture_id'] or chosen[0]['epochs']!=chosen[1]['epochs'] or chosen[0]['epochs']<10:
                raise ValueError('Finalists need different architectures and equal promotion fidelity >=10 epochs')
            created=[]
            for c in chosen:
                for seed in self.contract['evaluation']['confirmation_seeds']:
                    trial=copy.deepcopy(c); trial.update(stage='confirm',epochs=30,seed=seed,timeout_seconds=600)
                    created.append(self._submit(db,trial,confirmation=True))
            selection={'candidate_trial_ids':ids,'architecture_ids':[c['architecture_id'] for c in chosen]}
            db.execute("UPDATE study SET phase='confirm',selection=? WHERE id=1",(packed(selection),))
            self.event(db,'selection_locked',selection)
            self.wakeup.set(); return {'confirmation_ids':created,'selection':selection}

    def artifacts(self, trial_id):
        with self.db() as db:
            row=db.execute('SELECT * FROM trials WHERE id=?',(trial_id,)).fetchone()
            if not row:raise ValueError('Trial missing')
            return dict(row)

    def trials(self, stage=None, offset=0, limit=40):
        if stage not in (None,'screen','promote','confirm') or not isinstance(offset,int) or offset<0 or not isinstance(limit,int) or not 1<=limit<=100:
            raise ValueError('Invalid trial list filter')
        with self.db() as db:
            items=[]
            for row in db.execute('SELECT * FROM trials ORDER BY id'):
                c=json.loads(row['config'])
                if stage and c['stage']!=stage:continue
                m=json.loads(row['metrics']) if row['metrics'] else {}
                items.append({'id':row['id'],'config':c,'status':row['status'],'elapsed':row['elapsed'],
                              'score':m.get('validation_macro_f1'),'error':row['error']})
            return {'total':len(items),'items':items[offset:offset+limit]}

    def checkpoint(self, next_action, reason, evidence_ids):
        if not isinstance(next_action,str) or not next_action.strip() or len(next_action)>3000 or not isinstance(reason,str) or not reason.strip() or len(reason)>6000:
            raise ValueError('Checkpoint requires bounded next_action and reason')
        if not isinstance(evidence_ids,list) or len(evidence_ids)>20 or not evidence_ids:
            raise ValueError('Checkpoint must cite 1..20 real trial IDs')
        with self.db() as db:
            for trial_id in evidence_ids:
                if not db.execute('SELECT id FROM trials WHERE id=?',(trial_id,)).fetchone():raise ValueError('Unknown evidence ID')
            note={'next_action':next_action,'reason':reason,'evidence_ids':evidence_ids}
            self.event(db,'checkpoint',note)
        (self.agent/'notes').mkdir(exist_ok=True)
        (self.agent/'notes/LAST_CHECKPOINT.json').write_text(json.dumps(note,ensure_ascii=False,indent=2))
        return {'saved':note}

    def read(self, path):
        relative=Path(path)
        p=(self.agent/relative).resolve(); p.relative_to(self.agent)
        if not p.is_file() or p.stat().st_size>180000 or p.suffix not in ('.md','.json','.txt'):
            raise ValueError('Only small agent-facing text files can be read')
        return {'path':relative.as_posix(),'text':p.read_text(encoding='utf-8-sig')}

    def note(self, path, text):
        p=(self.agent/path).resolve(); relative=p.relative_to(self.agent)
        if (relative.parts[0]!='notes' or p.suffix!='.md') and relative.as_posix()!='report/INTERPRETATION_RU.md':
            raise ValueError('Agent may write only notes/*.md or report/INTERPRETATION_RU.md')
        if not isinstance(text,str) or len(text)>100000:
            raise ValueError('Note too large')
        p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text,encoding='utf-8')
        with self.db() as db:self.event(db,'agent_note',{'path':relative.as_posix(),'sha256':file_hash(p)})
        return {'saved':relative.as_posix()}

    def wait(self, seconds=90):
        deadline=time.monotonic()+max(0,min(120,seconds))
        while time.monotonic()<deadline:
            if self.stop.wait(1):break
            with self.db() as db:
                pending=db.execute("SELECT COUNT(*) FROM trials WHERE status IN ('queued','running')").fetchone()[0]
            if not pending:break
        return self.info()

    def loop(self):
        while not self.stop.is_set():
            with self.lock,self.db() as db:
                row=db.execute("SELECT * FROM trials WHERE status='queued' ORDER BY id LIMIT 1").fetchone()
                if row:
                    self.event(db,'started',{'id':row['id']})
                    db.execute("UPDATE trials SET status='running',started=? WHERE id=?",(time.time(),row['id']))
            if not row:
                self.wakeup.wait(1); self.wakeup.clear(); continue
            self.execute(row)

    def execute(self, row):
        c=json.loads(row['config']); directory=self.executor/'runs'/f"{row['id']:06d}"
        started=time.monotonic(); metrics=None; error=None; artifacts={}; outcome='failed'
        try:
            self.verify_seal(code_only=True)
            directory.mkdir(parents=True,exist_ok=False)
            (directory/'config.json').write_text(packed(raw_config(c)))
            with self.db() as db:study=db.execute('SELECT * FROM study').fetchone()
            remaining=max(0,self.wall_remaining(study))
            limit=min(c['timeout_seconds'] or remaining,remaining)
            if limit<=0 or self.stop.is_set():raise ValueError('Global deadline or controller shutdown')
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',CUDA_CACHE_DISABLE='1',
                     TMPDIR=str(directory),TORCH_HOME=str(directory/'cache'))
            command=[self.contract['runtime_python'],'-B',str(self.executor/'trainer.py'),'--config',str(directory/'config.json'),
                     '--data',str(self.inputs),'--output',str(directory)]
            with (directory/'stdout.log').open('wb') as stdout,(directory/'stderr.log').open('wb') as stderr:
                p=subprocess.Popen(command,cwd=directory,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
                self.active=p
                try:p.wait(timeout=limit)
                except subprocess.TimeoutExpired:
                    self.kill(p); outcome='timeout'; raise ValueError('External process timeout')
                finally:self.active=None
            if p.returncode:raise ValueError('Trainer failed: '+(directory/'stderr.log').read_text(errors='replace')[-2200:])
            metrics=json.loads((directory/'metrics.json').read_text())
            check=recompute(directory/'validation.csv',self.expected)
            if abs(check['validation_macro_f1']-metrics['validation_macro_f1'])>1e-12 or check['confusion_matrix']!=metrics['confusion_matrix']:
                raise ValueError('Independent metric arithmetic mismatch')
            if metrics['epochs_completed']!=c['epochs'] or metrics['parameters']!=c['actual_parameters']:
                raise ValueError('Fidelity/actual parameter mismatch')
            metrics.update(check); outcome='completed'
        except Exception as exc:error=str(exc)
        if directory.is_dir():
            for name in ('config.json','metrics.json','history.json','validation.csv','best_model.pt','stdout.log','stderr.log'):
                p=directory/name
                if p.is_file():artifacts[name]={'sha256':file_hash(p),'bytes':p.stat().st_size}
        elapsed=time.monotonic()-started
        with self.lock,self.db() as db:
            db.execute('UPDATE trials SET status=?,elapsed=?,finished=?,metrics=?,error=?,artifacts=? WHERE id=?',
                       (outcome,elapsed,time.time(),packed(metrics) if metrics else None,error,packed(artifacts),row['id']))
            self.event(db,'finished',{'id':row['id'],'status':outcome,'elapsed':elapsed,'error':error,'artifacts':artifacts})
            if elapsed>row['reserved']+2:
                self.event(db,'timeout_cleanup_overrun',{'id':row['id'],'seconds':elapsed-row['reserved']})

    def integrity(self, db):
        previous='0'*64; submitted=[]; finished=[]
        for e in db.execute('SELECT * FROM events ORDER BY id'):
            expected=digest({'time':e['time'],'kind':e['kind'],'payload':e['payload'],'previous_hash':previous})
            if e['previous_hash']!=previous or e['event_hash']!=expected:raise ValueError('Event chain corrupted')
            p=json.loads(e['payload'])
            if e['kind']=='submitted':submitted.append(p['id'])
            if e['kind']=='finished':finished.append(p['id'])
            previous=e['event_hash']
        ids=[r[0] for r in db.execute('SELECT id FROM trials ORDER BY id')]
        if sorted(submitted)!=ids or sorted(finished)!=ids:raise ValueError('Event/table attempt mismatch or unresolved jobs')
        for row in db.execute("SELECT * FROM trials WHERE status='completed'"):
            for name,record in json.loads(row['artifacts']).items():
                path=self.executor/'runs'/f"{row['id']:06d}"/name
                if not path.is_file() or file_hash(path)!=record['sha256']:raise ValueError('Evidence modified')

    def finalize(self):
        verification_started=time.monotonic()
        with self.lock,self.db() as db:
            study=db.execute('SELECT * FROM study').fetchone(); rows,used=self.usage(db)
            if study['status'] not in ('ready','running'):
                return {'already_closed':dict(study),'report':'report/VERIFIED_RESULTS.md'}
            if any(r['status'] in ('queued','running') for r in rows):raise ValueError('Pending jobs must finish first')
            self.verify_seal(); self.integrity(db)
            wall_exhausted=self.wall_remaining(study)<=self.contract['report_reserve_seconds']
            if not self.search_exhausted(db) and not wall_exhausted:
                raise ValueError('Search allocation remains. Continue experiments; early success is not permitted in maximize mode.')
            selection=json.loads(study['selection']) if study['selection'] else None
            confirmations={}; confirmation_rows={}; required=set(self.contract['evaluation']['confirmation_seeds'])
            for row in rows:
                c=json.loads(row['config'])
                if c['stage']=='confirm' and row['status']=='completed':
                    confirmations.setdefault(c['architecture_id'],{})[c['seed']]=json.loads(row['metrics'])['validation_macro_f1']
                    confirmation_rows.setdefault(c['architecture_id'],[]).append((dict(row),c,json.loads(row['metrics'])))
            means={a:sum(scores.values())/3 for a,scores in confirmations.items() if set(scores)==required}
            valid=(self.coverage_passed(rows) and selection and set(means)==set(selection['architecture_ids']))
            finalization_seconds=time.monotonic()-verification_started
            used+=finalization_seconds
            within=used<=self.contract['max_compute_seconds'] and self.wall_remaining(study)>=0
            if not valid and not wall_exhausted and len(rows)<self.contract['max_attempts'] and used+15<self.contract['max_compute_seconds']:
                raise ValueError('Coverage/confirmations incomplete while budget remains')
            status='complete' if valid and within else ('invalid' if not within else 'inconclusive')
            rankings=[]
            for arch,mean in means.items():
                items=confirmation_rows[arch]
                rankings.append({'architecture_id':arch,'mean_validation_macro_f1':mean,
                                 'mean_validation_seconds':sum(m['validation_seconds'] for _,_,m in items)/len(items),
                                 'parameters':items[0][2]['parameters'],
                                 'trial_ids':[r['id'] for r,_,_ in items],
                                 'seed_scores':confirmations[arch], 'recipe':items[0][1]})
            rankings.sort(key=lambda r:(-r['mean_validation_macro_f1'],r['mean_validation_seconds'],r['parameters'],r['architecture_id']))
            result={'status':status,'coverage':self.coverage(rows),'coverage_passed':self.coverage_passed(rows),
                    'confirmation_means':means,'ranking':rankings,'winner':rankings[0]['architecture_id'] if rankings else None,
                    'attempts':len(rows),'compute_used_seconds':used,'wall_seconds':time.time()-study['started'] if study['started'] else 0,
                    'reference_target_met':bool(means and max(means.values())>=self.contract['metric']['reference_target']),
                    'llm_tokens':None,'llm_requests':None,'llm_limits_verified':False,'integrity':'passed'}
            db.execute('INSERT INTO charges(seconds,reason) VALUES(?,?)',(finalization_seconds,'final integrity verification'))
            self.event(db,'finalized',result)
            db.execute('UPDATE study SET status=?,phase=?,selection=? WHERE id=1',(status,'closed',packed(result)))
            report=self.agent/'report'; report.mkdir(exist_ok=True)
            (report/'verified_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
            lines=['# Проверенный результат контроллера','',f'Статус: {status}',f'Попытки: {len(rows)}',
                   f'Учтено секунд: {used:.2f}',f'Охват: {packed(result["coverage"])}','',
                   '| Архитектура | Mean validation macro-F1 |','|---|---:|']
            lines.extend(f'| {a} | {score:.8f} |' for a,score in sorted(means.items(),key=lambda x:x[1],reverse=True))
            lines.extend(['','LLM токены/запросы: unknown. Достижение их лимитов не подтверждено.',
                          'Test не использовался. complete означает выполнение протокола, не достижение 0.97.'])
            (report/'VERIFIED_RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
            return result

    @staticmethod
    def kill(process):
        if process.poll() is not None:return
        try:os.killpg(process.pid,signal.SIGTERM)
        except ProcessLookupError:return
        try:process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL);process.wait()

    def shutdown(self):
        self.stop.set(); self.wakeup.set()
        if self.active:self.kill(self.active)
        if self.thread:self.thread.join(timeout=10)
