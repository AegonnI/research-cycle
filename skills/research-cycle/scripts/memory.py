"""Portable research ledger; stdlib only. Audit aid, not a security boundary."""
import argparse
import hashlib
import json
import math
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


def finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError('Nonfinite numeric value')
    if isinstance(value, dict):
        for item in value.values():
            finite(item)
    elif isinstance(value, list):
        for item in value:
            finite(item)
    return value


def read_json(path):
    return finite(json.loads(Path(path).read_text(encoding='utf-8-sig')))


def canonical(value):
    # Canonicalize equivalent JSON numbers without coercing booleans or strings.
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, dict):
        return {k: canonical(v) for k, v in value.items()}
    if isinstance(value, list):
        return [canonical(v) for v in value]
    return value


def packed(value):
    return json.dumps(finite(canonical(value)), ensure_ascii=False,
                      sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(packed(value).encode('utf-8')).hexdigest()


SCHEMA = '''
CREATE TABLE study(id INTEGER PRIMARY KEY CHECK(id=1), contract TEXT NOT NULL,
 contract_hash TEXT NOT NULL, created TEXT NOT NULL, status TEXT NOT NULL,
 frozen TEXT);
CREATE TABLE hypotheses(id INTEGER PRIMARY KEY, text TEXT NOT NULL,
 rationale TEXT NOT NULL, test TEXT NOT NULL, status TEXT NOT NULL, created TEXT NOT NULL);
CREATE TABLE experiments(id INTEGER PRIMARY KEY, hypothesis_id INTEGER NOT NULL
 REFERENCES hypotheses(id), fingerprint TEXT NOT NULL, config TEXT NOT NULL,
 status TEXT NOT NULL, reserve_seconds REAL NOT NULL CHECK(reserve_seconds>0),
 actual_seconds REAL CHECK(actual_seconds>=0), metrics TEXT, evidence TEXT,
 retry_reason TEXT, created TEXT NOT NULL, finished TEXT);
CREATE INDEX experiment_fingerprint ON experiments(fingerprint);
CREATE TABLE findings(id INTEGER PRIMARY KEY, text TEXT NOT NULL, created TEXT NOT NULL);
CREATE TABLE finding_evidence(finding_id INTEGER REFERENCES findings(id),
 experiment_id INTEGER REFERENCES experiments(id), PRIMARY KEY(finding_id,experiment_id));
CREATE TABLE charges(id INTEGER PRIMARY KEY, seconds REAL NOT NULL CHECK(seconds>=0),
 evidence TEXT NOT NULL, created TEXT NOT NULL);
CREATE TABLE events(id INTEGER PRIMARY KEY, time TEXT NOT NULL, kind TEXT NOT NULL,
 payload TEXT NOT NULL);
CREATE TRIGGER events_no_update BEFORE UPDATE ON events
 BEGIN SELECT RAISE(ABORT,'Events are append-only'); END;
CREATE TRIGGER events_no_delete BEFORE DELETE ON events
 BEGIN SELECT RAISE(ABORT,'Events are append-only'); END;
'''


def connect(path):
    if not Path(path).is_file():
        raise ValueError('Database missing; run init first')
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db


def event(db, kind, payload):
    db.execute('INSERT INTO events(time,kind,payload) VALUES(?,?,?)',
               (now(), kind, packed(payload)))


def state(db):
    row = db.execute('SELECT * FROM study WHERE id=1').fetchone()
    if row is None:
        raise ValueError('Invalid database')
    return row, json.loads(row['contract'])


def require_active(db, allow_frozen=False):
    row, contract = state(db)
    if row['status'] != 'running' and not (row['status'] == 'budget_violation' and allow_frozen):
        raise ValueError('Study is closed: ' + row['status'])
    if row['frozen'] and not allow_frozen:
        raise ValueError('Decisions already frozen; no further search')
    return row, contract


def usage(db):
    attempts = db.execute('SELECT COUNT(*) FROM experiments').fetchone()[0]
    used = db.execute('SELECT COALESCE(SUM(COALESCE(actual_seconds,reserve_seconds)),0) '
                      'FROM experiments').fetchone()[0]
    used += db.execute('SELECT COALESCE(SUM(seconds),0) FROM charges').fetchone()[0]
    return attempts, used


def evidence_files(db_path, paths):
    root = Path(db_path).resolve().parent
    output = []
    for name in paths:
        path = Path(name)
        path = (root / path).resolve() if not path.is_absolute() else path.resolve()
        relative = path.relative_to(root)  # Reject escape, including symlinks.
        if not path.is_file():
            raise ValueError('Evidence file missing: ' + str(relative))
        sha = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                sha.update(block)
        output.append({'path': relative.as_posix(), 'sha256': sha.hexdigest(),
                       'bytes': path.stat().st_size})
    if not output:
        raise ValueError('At least one evidence file required')
    return output


def positive_number(value, name, zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(name + ' must be numeric')
    if not math.isfinite(value) or value < 0 or (not zero and value == 0):
        raise ValueError(name + ' has invalid value')


def initialize(path, contract):
    path = Path(path)
    if path.exists():
        raise ValueError('Refuse to overwrite database')
    if not isinstance(contract, dict) or not contract.get('question'):
        raise ValueError('Contract requires a question')
    metric = contract.get('metric', {})
    if not metric.get('key') or metric.get('direction') not in ('maximize', 'minimize'):
        raise ValueError('Metric requires key and direction')
    count = contract.get('max_attempts')
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ValueError('max_attempts must be a positive integer')
    positive_number(contract.get('max_compute_seconds'), 'max_compute_seconds')
    reserve = contract.get('final_evaluation_reserve_seconds', 0)
    positive_number(reserve, 'final_evaluation_reserve_seconds', zero=True)
    if reserve >= contract['max_compute_seconds']:
        raise ValueError('Final reserve leaves no research budget')
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive file creation avoids accidental replacement during concurrent init.
    with path.open('xb'):
        pass
    db = sqlite3.connect(path)
    try:
        db.executescript(SCHEMA)
        with db:
            db.execute('INSERT INTO study VALUES(1,?,?,?,?,NULL)',
                       (packed(contract), digest(contract), now(), 'running'))
            event(db, 'init', {'contract_hash': digest(contract)})
    finally:
        db.close()
    return {'contract_hash': digest(contract)}


def perform(args):
    if args.command == 'init':
        return initialize(args.db, read_json(args.contract))
    db = connect(args.db)
    try:
        db.execute('BEGIN IMMEDIATE')
        result = execute(db, args)
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def execute(db, a):
    if a.command == 'snapshot':
        row, contract = state(db)
        attempts, used = usage(db)
        metric = contract['metric']
        completed = []
        for r in db.execute("SELECT id,metrics,config FROM experiments WHERE status='completed'"):
            values = json.loads(r['metrics'])
            completed.append({'id': r['id'], 'score': values[metric['key']],
                              'config': json.loads(r['config'])})
        completed.sort(key=lambda r: r['score'], reverse=metric['direction'] == 'maximize')
        hypotheses = [dict(r) for r in db.execute('SELECT * FROM hypotheses ORDER BY id DESC LIMIT 20')]
        return {'status': row['status'], 'contract': contract, 'contract_hash': row['contract_hash'],
                'frozen': row['frozen'] is not None, 'attempts': attempts,
                'compute_seconds_used_or_reserved': used,
                'compute_seconds_remaining': max(0, contract['max_compute_seconds'] - used),
                'open_attempts': [dict(r) for r in db.execute("SELECT id,created,reserve_seconds FROM experiments WHERE status='running'")],
                'hypotheses': hypotheses,
                'hypothesis_count': db.execute('SELECT COUNT(*) FROM hypotheses').fetchone()[0],
                'best': completed[:5],
                'findings': [dict(r) for r in db.execute('SELECT * FROM findings ORDER BY id DESC LIMIT 10')],
                'finding_count': db.execute('SELECT COUNT(*) FROM findings').fetchone()[0]}
    if a.command == 'show':
        # Table names are CLI enum values; no free SQL input is accepted.
        r = db.execute('SELECT * FROM ' + a.table + ' WHERE id=?', (a.id,)).fetchone()
        if r is None:
            raise ValueError('Record missing')
        return dict(r)
    row, contract = require_active(db, allow_frozen=a.command in ('finish', 'charge', 'close'))
    if a.command == 'hypothesis':
        cur = db.execute('INSERT INTO hypotheses(text,rationale,test,status,created) VALUES(?,?,?,?,?)',
                         (a.text, a.rationale, a.test, 'new', now()))
        event(db, 'hypothesis', {'id': cur.lastrowid})
        return {'id': cur.lastrowid}
    if a.command == 'begin':
        if db.execute('SELECT id FROM hypotheses WHERE id=?', (a.hypothesis,)).fetchone() is None:
            raise ValueError('Hypothesis missing')
        positive_number(a.reserve_seconds, 'reserve_seconds')
        config = read_json(a.config)
        if not isinstance(config, dict) or not config:
            raise ValueError('Configuration must be a nonempty JSON object')
        fingerprint = digest({'contract_hash': row['contract_hash'], 'config': config})
        previous = list(db.execute('SELECT status FROM experiments WHERE fingerprint=?', (fingerprint,)))
        if previous and (not a.retry_reason or any(r['status'] != 'failed' for r in previous)):
            raise ValueError('Duplicate configuration; retry only failed attempts with explicit reason')
        count, used = usage(db)
        reserve = contract.get('final_evaluation_reserve_seconds', 0)
        if count >= contract['max_attempts'] or used + a.reserve_seconds + reserve > contract['max_compute_seconds']:
            raise ValueError('Attempt or compute budget exhausted')
        cur = db.execute('INSERT INTO experiments(hypothesis_id,fingerprint,config,status,reserve_seconds,retry_reason,created) VALUES(?,?,?,?,?,?,?)',
                         (a.hypothesis, fingerprint, packed(config), 'running', a.reserve_seconds, a.retry_reason, now()))
        db.execute("UPDATE hypotheses SET status='testing' WHERE id=?", (a.hypothesis,))
        event(db, 'begin', {'id': cur.lastrowid, 'fingerprint': fingerprint})
        return {'id': cur.lastrowid, 'fingerprint': fingerprint, 'timeout_seconds': a.reserve_seconds}
    if a.command == 'finish':
        experiment = db.execute('SELECT * FROM experiments WHERE id=?', (a.experiment,)).fetchone()
        if experiment is None or experiment['status'] != 'running':
            raise ValueError('Attempt missing or already closed')
        positive_number(a.seconds, 'seconds', zero=True)
        values = read_json(a.metrics) if a.metrics else {}
        if not isinstance(values, dict):
            raise ValueError('Metrics must be a JSON object')
        if a.outcome == 'completed':
            score = values.get(contract['metric']['key'])
            positive_number(score, 'primary metric', zero=True) if contract['metric'].get('nonnegative', False) else None
            if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score):
                raise ValueError('Completed attempt requires finite primary metric')
        paths = list(a.evidence) + ([a.metrics] if a.metrics else [])
        evidence = evidence_files(a.db, paths)
        db.execute('UPDATE experiments SET status=?,actual_seconds=?,metrics=?,evidence=?,finished=? WHERE id=?',
                   (a.outcome, a.seconds, packed(values), packed(evidence), now(), a.experiment))
        _, used = usage(db)
        violation = a.seconds > experiment['reserve_seconds'] or used > contract['max_compute_seconds']
        if violation:
            db.execute("UPDATE study SET status='budget_violation' WHERE id=1")
        event(db, 'finish', {'id': a.experiment, 'outcome': a.outcome, 'seconds': a.seconds, 'budget_violation': violation})
        return {'id': a.experiment, 'budget_violation': violation}
    if a.command == 'finding':
        for eid in a.experiments:
            r = db.execute('SELECT status FROM experiments WHERE id=?', (eid,)).fetchone()
            if r is None or r['status'] == 'running':
                raise ValueError('Finding must cite closed attempts')
        cur = db.execute('INSERT INTO findings(text,created) VALUES(?,?)', (a.text, now()))
        for eid in set(a.experiments):
            db.execute('INSERT INTO finding_evidence VALUES(?,?)', (cur.lastrowid, eid))
        if a.hypothesis_status:
            for eid in a.experiments:
                db.execute('UPDATE hypotheses SET status=? WHERE id=(SELECT hypothesis_id FROM experiments WHERE id=?)',
                           (a.hypothesis_status, eid))
        event(db, 'finding', {'id': cur.lastrowid, 'experiments': a.experiments})
        return {'id': cur.lastrowid}
    if a.command == 'freeze':
        if db.execute("SELECT id FROM experiments WHERE status='running'").fetchone():
            raise ValueError('Cannot freeze with open attempts')
        if not db.execute("SELECT id FROM experiments WHERE status='completed'").fetchone():
            raise ValueError('Cannot freeze without completed attempts')
        decision = read_json(a.decision)
        evidence = evidence_files(a.db, [a.decision] + a.evidence)
        frozen = {'decision': decision, 'evidence': evidence, 'time': now()}
        db.execute('UPDATE study SET frozen=? WHERE id=1', (packed(frozen),))
        event(db, 'freeze', frozen)
        return frozen
    if a.command == 'charge':
        positive_number(a.seconds, 'seconds', zero=True)
        evidence = evidence_files(a.db, a.evidence)
        db.execute('INSERT INTO charges(seconds,evidence,created) VALUES(?,?,?)', (a.seconds, packed(evidence), now()))
        _, used = usage(db)
        violation = used > contract['max_compute_seconds']
        if violation:
            db.execute("UPDATE study SET status='budget_violation' WHERE id=1")
        event(db, 'charge', {'seconds': a.seconds, 'evidence': evidence, 'budget_violation': violation})
        return {'compute_seconds_used_or_reserved': used, 'budget_violation': violation}
    if a.command == 'close':
        if row['status'] == 'budget_violation' and a.status not in ('invalid', 'stopped'):
            raise ValueError('Budget violation cannot be relabeled as success')
        if db.execute("SELECT id FROM experiments WHERE status='running'").fetchone():
            raise ValueError('Resolve running attempts before closing')
        if a.status == 'achieved' and not row['frozen']:
            raise ValueError('Freeze evidence and verify contract before declaring achieved')
        db.execute('UPDATE study SET status=? WHERE id=1', (a.status,))
        event(db, 'close', {'status': a.status})
        return {'status': a.status}
    raise ValueError('Unknown command')


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    for name in ['init', 'hypothesis', 'begin', 'finish', 'finding', 'snapshot', 'show', 'freeze', 'charge', 'close']:
        s = sub.add_parser(name)
        s.add_argument('--db', required=True)
        if name == 'init':
            s.add_argument('--contract', required=True)
        elif name == 'hypothesis':
            for field in ['text', 'rationale', 'test']:
                s.add_argument('--' + field, required=True)
        elif name == 'begin':
            s.add_argument('--hypothesis', type=int, required=True)
            s.add_argument('--config', required=True)
            s.add_argument('--reserve-seconds', type=float, required=True)
            s.add_argument('--retry-reason')
        elif name == 'finish':
            s.add_argument('--experiment', type=int, required=True)
            s.add_argument('--outcome', choices=['completed', 'failed'], required=True)
            s.add_argument('--seconds', type=float, required=True)
            s.add_argument('--metrics')
            s.add_argument('--evidence', nargs='+', required=True)
        elif name == 'finding':
            s.add_argument('--text', required=True)
            s.add_argument('--experiments', type=int, nargs='+', required=True)
            s.add_argument('--hypothesis-status', choices=['supported', 'rejected', 'uncertain'])
        elif name == 'show':
            s.add_argument('--table', choices=['hypotheses', 'experiments', 'findings'], required=True)
            s.add_argument('--id', type=int, required=True)
        elif name == 'freeze':
            s.add_argument('--decision', required=True)
            s.add_argument('--evidence', nargs='+', required=True)
        elif name == 'charge':
            s.add_argument('--seconds', type=float, required=True)
            s.add_argument('--evidence', nargs='+', required=True)
        elif name == 'close':
            s.add_argument('--status', choices=['achieved', 'budget_exhausted', 'inconclusive', 'stopped', 'invalid'], required=True)
    return p


if __name__ == '__main__':
    try:
        print(json.dumps(perform(parser().parse_args()), ensure_ascii=False, indent=2, allow_nan=False))
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)
