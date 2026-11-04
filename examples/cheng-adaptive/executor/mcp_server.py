"""Dependency-free MCP stdio facade. The only agent tools in the study profile."""
import argparse
import fcntl
import json
from pathlib import Path
import sys
from controller import Controller


def schema(properties=None, required=None):
    return {'type':'object','properties':properties or {},'required':required or [],'additionalProperties':False}


TOOLS = [
    {'name':'study_info','description':'Read remaining total wall time, target, all confirmation groups and current trials. details=true includes contract and registry. Coverage is descriptive, never a gate.',
     'inputSchema':schema({'details':{'type':'boolean'}})},
    {'name':'study_read','description':'Read an agent-facing instruction, skill, checkpoint or generated report. Paths relative to agent workspace; no arbitrary filesystem access.',
     'inputSchema':schema({'path':{'type':'string'}},['path'])},
    {'name':'study_submit','description':'Submit 1..12 configs per message for sequential training. No total attempt limit. Epochs chosen by agent; timeout_seconds defaults to remaining global wall, not a short timeout. No code/paths.',
     'inputSchema':schema({'configs':{'type':'array','minItems':1,'maxItems':12,'items':{'type':'object'}}},['configs'])},
    {'name':'study_probe','description':'Validate a model specification, actual parameter count and forward shape. Does not train; probe compute is accounted.',
     'inputSchema':schema({'config':{'type':'object'}},['config'])},
    {'name':'study_trials','description':'Read scientific configs and outcomes, optionally for one fidelity stage. Does not expose SQL or mutations.',
     'inputSchema':schema({'stage':{'type':'string','enum':['screen','promote','confirm']},'offset':{'type':'integer','minimum':0},'limit':{'type':'integer','minimum':1,'maximum':100}})},
    {'name':'study_trial','description':'Read one trial, verified metrics, last 50 history epochs and log tails, resource use and artifact hashes.',
     'inputSchema':schema({'trial_id':{'type':'integer','minimum':1}},['trial_id'])},
    {'name':'study_wait','description':'Wait up to 120 seconds for the current queue to finish; returns a compact status. Prefer this to rapid polling.',
     'inputSchema':schema({'seconds':{'type':'integer','minimum':0,'maximum':120}})},
    {'name':'study_retry','description':'Retry failed/timeout/cancelled science with a new recorded ID and optional longer timeout_seconds; omission uses remaining wall instead of the old timeout.',
     'inputSchema':schema({'trial_id':{'type':'integer','minimum':1},'reason':{'type':'string'},'timeout_seconds':{'type':['number','null'],'minimum':0.01,'maximum':28800}},['trial_id','reason'])},
    {'name':'study_confirm','description':'Freeze ONE completed candidate recipe now and create three fresh-seed trainings. No coverage/exhaustion requirement. Optional epochs chosen before seeds. Below-target confirmation can return to search; same recipe cannot reroll seeds.',
     'inputSchema':schema({'trial_id':{'type':'integer','minimum':1},'epochs':{'type':'integer','minimum':1},'timeout_seconds':{'type':['number','null'],'minimum':0.01,'maximum':28800}},['trial_id'])},
    {'name':'study_checkpoint','description':'Persist a compact recovery decision citing actual trial IDs, outside editable agent notes.',
     'inputSchema':schema({'next_action':{'type':'string'},'reason':{'type':'string'},'evidence_ids':{'type':'array','items':{'type':'integer'}}},['next_action','reason','evidence_ids'])},
    {'name':'study_note','description':'Write notes/*.md or report/INTERPRETATION_RU.md only. Cannot edit instructions, data, trainer, ledger or verified report.',
     'inputSchema':schema({'path':{'type':'string'},'text':{'type':'string'}},['path','text'])},
    {'name':'study_finalize','description':'Verify and close on confirmed mean>=target or global deadline. No quota or forced budget exhaustion. Numeric report and honest reached/inconclusive status; auto-close also runs in background.',
     'inputSchema':schema()},
]


def dispatch(controller, name, args):
    if name=='study_info':
        result=controller.info()
        if args.get('details'):
            result.update(contract=controller.contract,catalogue=controller.catalogue)
        return result
    if name=='study_read':return controller.read(args['path'])
    if name=='study_submit':return controller.submit(args['configs'])
    if name=='study_probe':
        with controller.lock:return controller.probe(args['config'])
    if name=='study_trials':return controller.trials(**args)
    if name=='study_trial':return controller.artifacts(args['trial_id'])
    if name=='study_wait':return controller.wait(args.get('seconds',90))
    if name=='study_retry':return controller.retry(**args)
    if name=='study_confirm':return controller.confirm(**args)
    if name=='study_checkpoint':return controller.checkpoint(**args)
    if name=='study_note':return controller.note(args['path'],args['text'])
    if name=='study_finalize':return controller.finalize()
    raise ValueError('Unknown tool')


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    # WSL process lock prevents two independent controllers owning the same study.
    lock=(a.root/'executor/controller.lock').open('a+')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    controller=Controller(a.root)
    allowed={t['name']:t for t in TOOLS}
    try:
        for line in sys.stdin.buffer:
            request=json.loads(line.decode('utf-8'))
            if 'id' not in request:continue
            try:
                method=request['method'];params=request.get('params',{})
                if method=='initialize':
                    protocol=params.get('protocolVersion','2024-11-05')
                    if protocol not in ['2024-11-05','2025-03-26','2025-06-18','2025-11-25']:protocol='2024-11-05'
                    result={'protocolVersion':protocol,'capabilities':{'tools':{}},'serverInfo':{'name':'controlled-research','version':'0.1.0'}}
                elif method=='ping':result={}
                elif method=='tools/list':result={'tools':TOOLS}
                elif method=='tools/call':
                    name=params['name'];arguments=params.get('arguments',{})
                    if name not in allowed:raise ValueError('Tool not exposed')
                    spec=allowed[name]['inputSchema']
                    if not isinstance(arguments,dict) or set(arguments)-set(spec['properties']) or any(k not in arguments for k in spec['required']):
                        raise ValueError('Invalid tool arguments')
                    try:
                        value=dispatch(controller,name,arguments)
                        result={'content':[{'type':'text','text':json.dumps(value,ensure_ascii=False,allow_nan=False)}],'isError':False}
                    except Exception as exc:
                        result={'content':[{'type':'text','text':json.dumps({'error':str(exc)},ensure_ascii=False)}],'isError':True}
                else:raise ValueError('Method not implemented')
                response={'jsonrpc':'2.0','id':request['id'],'result':result}
            except Exception as exc:
                response={'jsonrpc':'2.0','id':request['id'],'error':{'code':-32602,'message':str(exc)}}
            print(json.dumps(response,ensure_ascii=False,allow_nan=False),flush=True)
    finally:
        controller.shutdown();lock.close()


if __name__=='__main__':main()
