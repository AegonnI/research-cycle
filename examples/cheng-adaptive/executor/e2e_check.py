"""Synthetic-only real process checks: fresh confirmations, automatic close, deadline kill."""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import numpy as np
from common import file_hash
from controller import Controller

def fixture(path,source,fake=False):
    for name in ['executor','inputs','agent']:(path/name).mkdir()
    for name in ['common.py','ledger.py','controller.py','trainer.py']:
        shutil.copyfile(source/'executor'/name,path/'executor'/name)
    if fake:(path/'executor/trainer.py').write_text("import subprocess,sys,time\nsubprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])\ntime.sleep(60)\n")
    contract=json.loads((source/'executor/contract.json').read_text())
    contract['metric']['target']=0.0
    if fake:contract['max_wall_seconds']=1.0
    (path/'executor/contract.json').write_text(json.dumps(contract))
    shutil.copyfile(source/'executor/catalogue.json',path/'executor/catalogue.json')
    np.save(path/'inputs/images_fp16.npy',np.random.default_rng(17).random((33,160,160)).astype(np.float16))
    records=[{'index':i,'label':i%3,'split':'train' if i<24 else 'val','patient_id':str(i)} for i in range(33)]
    (path/'inputs/records.json').write_text(json.dumps(records))
    files=[*(path/'executor').glob('*'),*(path/'inputs').glob('*')]
    (path/'executor/seal.json').write_text(json.dumps({'files':{p.relative_to(path).as_posix():file_hash(p) for p in files}}))

def until(c,predicate,limit=120):
    end=time.monotonic()+limit
    while True:
        info=c.info()
        if predicate(info):return info
        if time.monotonic()>end:raise RuntimeError('Fixture did not complete: '+str(info))
        time.sleep(.15)

def main():
    root=Path(__file__).resolve().parent.parent;result={}
    for label,fake in [('confirmation',False),('deadline',True)]:
        with tempfile.TemporaryDirectory(prefix='adaptive-e2e-',dir=root/'checks') as directory:
            path=Path(directory);fixture(path,root,fake);c=Controller(path)
            try:
                c.start()
                configs=[{'architecture':'mnasnet0_5','seed':71,'epochs':1,'batch_size':8}]
                if fake:configs*=1;configs += [{'architecture':'resnet18','seed':72,'epochs':1}]
                ids=c.submit(configs)['accepted_ids']
                if fake:
                    info=until(c,lambda i:i['study']['status']=='inconclusive',30)
                    assert info['statuses']['timeout']==1 and info['statuses']['cancelled']==1,info
                    final=json.loads((path/'agent/report/verified_results.json').read_text())
                    assert final['stop_reason']=='wall_deadline' and not final['target_met']
                else:
                    info=until(c,lambda i:i['statuses']['completed']==1)
                    group=c.confirm(ids[0])
                    info=until(c,lambda i:i['study']['status']=='complete',180)
                    final=json.loads((path/'agent/report/verified_results.json').read_text())
                    assert final['target_met'] and final['integrity']=='passed'
                    assert final['attempts']==4 and len(final['confirmations'][0]['completed_seeds'])==3
                    assert len(set(group['seeds']))==3
                with c.db() as db:c.integrity(db)
                result[label]={'passed':True,'statuses':info['statuses'],'target_met':final['target_met'],'integrity':final['integrity']}
            finally:c.shutdown()
        print('SYNTHETIC_E2E_OK',label,flush=True)
    (root/'checks/e2e.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)

if __name__=='__main__':main()
