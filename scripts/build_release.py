"""Build the v2 skill ZIP from an explicit, non-sensitive allowlist."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '2.0.0-rc.2'
FILES = {
    "skills/research-cycle/SKILL.md": "research-cycle/SKILL.md",
    "skills/research-cycle/scripts/memory.py": "research-cycle/scripts/memory.py",
    "LICENSE": "research-cycle/LICENSE",
    "THIRD_PARTY_NOTICES.md": "research-cycle/THIRD_PARTY_NOTICES.md",
    "docs/UPSTREAM_SOURCES.json": "research-cycle/docs/UPSTREAM_SOURCES.json",
    "skills/research-cycle/references/guide.ru.md": "research-cycle/references/guide.ru.md",
    "skills/research-cycle/references/search.md": "research-cycle/references/search.md",
    "skills/research-cycle/references/search.ru.md": "research-cycle/references/search.ru.md",
    "skills/research-cycle/references/memory.md": "research-cycle/references/memory.md",
    "skills/research-cycle/references/memory.ru.md": "research-cycle/references/memory.ru.md",
    "skills/research-cycle/references/hermes.md": "research-cycle/references/hermes.md",
    "skills/research-cycle/references/hermes.ru.md": "research-cycle/references/hermes.ru.md",
    "skills/research-cycle/references/adaptive.md": "research-cycle/references/adaptive.md",
    "skills/research-cycle/references/adaptive.ru.md": "research-cycle/references/adaptive.ru.md",
    "licenses/K-Dense-MIT.txt": "research-cycle/licenses/K-Dense-MIT.txt",
    "licenses/Superpowers-MIT.txt": "research-cycle/licenses/Superpowers-MIT.txt",
    "licenses/Hermes-MIT.txt": "research-cycle/licenses/Hermes-MIT.txt",
    "templates/RESEARCH_TASK_TEMPLATE.en.md": "research-cycle/assets/RESEARCH_TASK_TEMPLATE.en.md",
    "templates/RESEARCH_TASK_TEMPLATE.ru.md": "research-cycle/assets/RESEARCH_TASK_TEMPLATE.ru.md",
    "templates/ADAPTIVE_GOAL_TEMPLATE.en.md": "research-cycle/assets/ADAPTIVE_GOAL_TEMPLATE.en.md",
    "templates/ADAPTIVE_GOAL_TEMPLATE.ru.md": "research-cycle/assets/ADAPTIVE_GOAL_TEMPLATE.ru.md"
}


def main():
    target = ROOT / 'dist'
    target.mkdir(exist_ok=True)
    archive_path = target / ('research-cycle-v' + VERSION + '.zip')
    manifest = {'version': VERSION, 'files': []}
    with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for source, destination in FILES.items():
            data = (ROOT / source).read_bytes()
            info = zipfile.ZipInfo(destination, date_time=(2026, 11, 4, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
            manifest['files'].append({'path': destination, 'bytes': len(data),
                                      'sha256': hashlib.sha256(data).hexdigest()})
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == set(FILES.values())
        for entry in manifest['files']:
            assert hashlib.sha256(archive.read(entry['path'])).hexdigest() == entry['sha256']
    extra=['README.md','README.ru.md','CHANGELOG.md','docs/KNOWN_LIMITATIONS.md','docs/USAGE.md',
           'examples/cheng-adaptive/README.md','examples/cheng-adaptive/prepare.py',
           'examples/cheng-adaptive/contract.example.json','examples/cheng-adaptive/EXECUTOR_SOURCE_HASHES.json',
           'tests/test_adaptive_executor.py','tests/test_public_prepare.py','tests/test_research_memory.py','tests/test_public_metrics.py']
    extra += ['examples/cheng-adaptive/executor/'+name for name in
              ['common.py','controller.py','ledger.py','trainer.py','mcp_server.py','operator_start.py','operator_close.py','preflight.py','e2e_check.py']]
    extra += ['docs/benchmarks/2026-11-cheng/'+name for name in
              ['REPORT.en.md','REPORT.ru.md','metrics.json','seed_metrics.csv','adaptive_trials.json']]
    reference_path=target/('research-cycle-reference-v'+VERSION+'.zip')
    sources=sorted(set(FILES)|set(extra))
    manifest['reference_files']=[]
    with zipfile.ZipFile(reference_path,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for source in sources:
            data=(ROOT/source).read_bytes();destination='research-cycle-reference/'+source
            info=zipfile.ZipInfo(destination,date_time=(2026,11,4,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
            archive.writestr(info,data)
            manifest['reference_files'].append({'path':destination,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    with zipfile.ZipFile(reference_path) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist())=={e['path'] for e in manifest['reference_files']}
        for entry in manifest['reference_files']:assert hashlib.sha256(archive.read(entry['path'])).hexdigest()==entry['sha256']
    manifest_path = target / 'release-manifest.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    exports=[]
    for name in ['metrics.json','seed_metrics.csv']:
        path=target/name;path.write_bytes((ROOT/'docs/benchmarks/2026-11-cheng'/name).read_bytes());exports.append(path)
    sums = []
    for path in [archive_path, reference_path, manifest_path, *exports]:
        sums.append(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name)
    (target / 'SHA256SUMS').write_text('\n'.join(sums) + '\n', encoding='ascii')
    print(json.dumps({'archive': str(archive_path), 'files': len(FILES), 'checksums': sums}, indent=2))


if __name__ == '__main__':
    main()
