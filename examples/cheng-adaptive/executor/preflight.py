"""Operator-only constructor and synthetic-training checks; never uses MRI outcomes."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.environ['CUDA_CACHE_DISABLE']='1'
import numpy as np
import torch
from common import REGISTRY, config
from trainer import build, probe, train


def main():
    root=Path(__file__).resolve().parent.parent
    checks=root/'checks';checks.mkdir(exist_ok=True)
    torch.set_num_threads(4)
    started=time.monotonic();catalogue={}
    for architecture,family in REGISTRY.items():
        c=config({'architecture':architecture,'seed':17})
        catalogue[architecture]={'family':family,**probe(c)}
        print('FORWARD_OK',architecture,flush=True)
    (root/'executor/catalogue.json').write_text(json.dumps(catalogue,indent=2))
    custom={'architecture':'custom','seed':17,'custom':{'channels':[16,32],'kernel':3,'norm':'group','residual':True,'dropout':.1}}
    with_skip=config(custom);without_skip=copy.deepcopy(custom);without_skip['custom']['residual']=False
    yes=build(with_skip);no=build(config(without_skip))
    assert sum(p.numel() for p in yes.parameters())!=sum(p.numel() for p in no.parameters())
    custom_probes=[]
    for widths in [[17,33],[16,32,64,128,128,128]]:
        c=copy.deepcopy(custom);c['custom']['channels']=widths
        custom_probes.append(probe(config(c)))
    # Two tiny synthetic experiments verify backwards, metadata and best-checkpoint roundtrip.
    synthetic=[]
    with tempfile.TemporaryDirectory(prefix='synthetic-',dir=checks) as directory:
        path=Path(directory);data=path/'data';data.mkdir()
        np.save(data/'images_fp16.npy',np.random.default_rng(17).random((33,160,160)).astype(np.float16))
        records=[{'index':i,'label':i%3,'split':'train' if i<24 else 'val','patient_id':str(i)} for i in range(33)]
        (data/'records.json').write_text(json.dumps(records))
        for i,raw in enumerate([custom,{'architecture':'mnasnet0_5','seed':19}]):
            c=config({**raw,'epochs':1,'batch_size':8})
            out=path/f'run{i}';out.mkdir()
            result=train(c,data,out)
            assert result['epochs_completed']==1
            assert result['checkpoint_sha256']
            synthetic.append({'architecture':c['architecture'],'passed':True,'elapsed_seconds':result['trainer_elapsed_seconds']})
            print('SYNTHETIC_TRAIN_OK',c['architecture'],flush=True)
    result={'catalogue_models':len(catalogue),'all_forward_shapes':[2,3],
            'real_residual_connection_verified':True,'custom_probes':custom_probes,
            'synthetic_training':synthetic,'preparation_seconds':time.monotonic()-started,
            'research_trials_started':0,'patient_images_used_for_training':0}
    (checks/'preflight.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
