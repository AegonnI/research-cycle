"""Build the portable skill from explicit public inputs; old releases stay unchanged."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
VERSION='2.1.0-rc.1'
FILES={
    'skills/research-cycle/SKILL.md':'research-cycle/SKILL.md',
    'skills/research-cycle/scripts/memory.py':'research-cycle/scripts/memory.py',
    'LICENSE':'research-cycle/LICENSE',
    'THIRD_PARTY_NOTICES.md':'research-cycle/THIRD_PARTY_NOTICES.md',
    'docs/UPSTREAM_SOURCES.json':'research-cycle/docs/UPSTREAM_SOURCES.json',
}
for name in ['guide.ru.md','intake.md','intake.ru.md','search.md','search.ru.md',
             'memory.md','memory.ru.md','hermes.md','hermes.ru.md','adaptive.md','adaptive.ru.md']:
    FILES['skills/research-cycle/references/'+name]='research-cycle/references/'+name
for name in ['K-Dense-MIT.txt','Superpowers-MIT.txt','Hermes-MIT.txt']:
    FILES['licenses/'+name]='research-cycle/licenses/'+name
for name in ['RESEARCH_GOAL_TEMPLATE.md','RESEARCH_GOAL_TEMPLATE.en.md',
             'RESEARCH_TASK_TEMPLATE.en.md','RESEARCH_TASK_TEMPLATE.ru.md']:
    FILES['templates/'+name]='research-cycle/assets/'+name

def main():
    target=ROOT/'dist';target.mkdir(exist_ok=True)
    archive_path=target/('research-cycle-v'+VERSION+'.zip')
    manifest={'version':VERSION,'files':[]}
    with zipfile.ZipFile(archive_path,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for source,destination in sorted(FILES.items()):
            data=(ROOT/source).read_bytes();info=zipfile.ZipInfo(destination,date_time=(2026,11,10,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,data)
            manifest['files'].append({'path':destination,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    with zipfile.ZipFile(archive_path) as z:
        assert z.testzip() is None and set(z.namelist())==set(FILES.values())
        for entry in manifest['files']:assert hashlib.sha256(z.read(entry['path'])).hexdigest()==entry['sha256']
    manifest_path=target/'release-manifest.json';manifest_path.write_bytes((json.dumps(manifest,indent=2)+'\n').encode('utf-8'))
    exports=[]
    for name in ['metrics.json','seed_metrics.csv']:
        path=target/name;path.write_bytes((ROOT/'docs/benchmarks/2026-11-cheng'/name).read_bytes());exports.append(path)
    files=[archive_path,manifest_path,*exports]
    sums=[hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in files]
    (target/'SHA256SUMS').write_bytes(('\n'.join(sums)+'\n').encode('ascii'))
    print(json.dumps({'version':VERSION,'archive':str(archive_path),'files':len(FILES),'checksums':sums},indent=2))

if __name__=='__main__':main()
