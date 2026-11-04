"""Prepare a fresh Linux/WSL workspace with existing dependencies and train/val inputs."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
CODE=['common.py','controller.py','ledger.py','trainer.py','mcp_server.py','operator_start.py','operator_close.py','preflight.py','e2e_check.py']

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()

def prepare(workspace,inputs_dir,runtime_python,target=.92,hours=8,manifest=None):
    workspace=Path(workspace).resolve();inputs_dir=Path(inputs_dir).resolve();runtime_python=Path(runtime_python).resolve()
    if workspace.exists():raise ValueError('Workspace already exists; refusing to overwrite')
    if not runtime_python.is_file():raise ValueError('Supply the existing Python executable; no installation is performed')
    if not math.isfinite(target) or not 0<=target<=1 or not math.isfinite(hours) or hours<=0:raise ValueError('Invalid target or wall time')
    names=['images_fp16.npy','records.json','input_manifest.json']
    for name in names:
        if not (inputs_dir/name).is_file():raise ValueError('Missing prepared input: '+name)
    records=json.loads((inputs_dir/'records.json').read_text())
    if not records or {r['split'] for r in records}!={'train','val'}:raise ValueError('Only train and validation inputs are permitted')
    if len({r['index'] for r in records})!=len(records):raise ValueError('Duplicate indices')
    train={r['patient_id'] for r in records if r['split']=='train'};val={r['patient_id'] for r in records if r['split']=='val'}
    if train&val:raise ValueError('Patient overlap')
    workspace.mkdir(parents=True)
    for name in ['executor','inputs','agent','checks']:(workspace/name).mkdir()
    for name in CODE:shutil.copyfile(HERE/'executor'/name,workspace/'executor'/name)
    for name in names:shutil.copyfile(inputs_dir/name,workspace/'inputs'/name)
    contract=json.loads((HERE/'contract.example.json').read_text(encoding='utf-8'))
    contract.update(runtime_python=str(runtime_python),max_wall_seconds=hours*3600)
    contract['metric']['target']=target
    for name in ['executor/contract.json','agent/contract.json']:(workspace/name).write_text(json.dumps(contract,indent=2))
    shutil.copytree(REPO/'skills/research-cycle',workspace/'agent/skill/research-cycle',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    (workspace/'agent/TASK.md').write_text('Use contract.json and the adaptive_executor skill route. Choose experiments adaptively. Target '+str(target)+' on three fresh seeds; total wall '+str(hours)+' hours. Only supplied train/val inputs and study tools. No history, other projects, test access or environment changes. Save verified metrics and an honest interpretation.\n')
    if manifest:shutil.copyfile(manifest,workspace/'agent/MANIFEST.txt')
    else:(workspace/'agent/MANIFEST.txt').write_text('Existing runtime: '+str(runtime_python)+'\nNo dependency installation is authorized by this example.\n')
    result=subprocess.run([str(runtime_python),'-B',str(workspace/'executor/trainer.py'),'--catalogue'],capture_output=True,text=True,check=True)
    catalogue=json.loads(result.stdout)
    (workspace/'executor/catalogue.json').write_text(json.dumps(catalogue,indent=2))
    files=[*(workspace/'executor').glob('*.py'),workspace/'executor/contract.json',workspace/'executor/catalogue.json',
           *(workspace/'inputs').glob('*'),workspace/'agent/TASK.md',workspace/'agent/contract.json',workspace/'agent/MANIFEST.txt',
           *(workspace/'agent/skill/research-cycle').rglob('*.md')]
    seal={'files':{p.relative_to(workspace).as_posix():sha(p) for p in files}}
    (workspace/'executor/seal.json').write_text(json.dumps(seal,indent=2))
    return {'workspace':str(workspace),'catalogue_models':len(catalogue),'research_started':False,'target':target,'max_wall_seconds':hours*3600}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True);p.add_argument('--inputs-dir',type=Path,required=True)
    p.add_argument('--runtime-python',type=Path,required=True);p.add_argument('--target',type=float,default=.92)
    p.add_argument('--hours',type=float,default=8);p.add_argument('--manifest',type=Path)
    args=p.parse_args();print(json.dumps(prepare(**vars(args)),indent=2))

if __name__=='__main__':main()
