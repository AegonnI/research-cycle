"""After the global watchdog, close without new research or resetting state."""
import argparse
import fcntl
import json
import time
from pathlib import Path
from controller import Controller

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
with (a.root/'executor/controller.lock').open('a+') as lock:
    deadline=time.monotonic()+90
    while True:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);break
        except BlockingIOError:
            if time.monotonic()>deadline:raise RuntimeError('MCP owner still holds lock; inspect state, do not reset')
            time.sleep(.5)
    c=Controller(a.root,worker=False)
    try:
        state=c.info();remaining=state['wall_remaining_seconds']
        if remaining>2:raise RuntimeError('Cannot force an early close; global time remains')
        if remaining>0:time.sleep(remaining+.05)
        print(json.dumps(c.finalize()))
    finally:c.shutdown()
