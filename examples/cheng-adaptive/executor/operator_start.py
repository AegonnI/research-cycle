"""Starts the global wall clock. Not an agent tool; does not submit training."""
import argparse
import fcntl
import json
from pathlib import Path
from controller import Controller

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);args=p.parse_args()
with (args.root/'executor/controller.lock').open('a+') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    controller=Controller(args.root,worker=False)
    try:
        info=controller.start()
        print(json.dumps({'study_status':info['study']['status'],'attempts':info['attempts'],
                          'remaining_wall_seconds':info['wall_remaining_seconds']}))
    finally:controller.shutdown()
