"""Build the v1.0.0 skill ZIP from an explicit, non-sensitive allowlist."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.0.0'
FILES = {
    'skills/research-cycle/SKILL.md': 'research-cycle/SKILL.md',
    'skills/research-cycle/scripts/memory.py': 'research-cycle/scripts/memory.py',
    'skills/research-cycle/references/memory.md': 'research-cycle/references/memory.md',
    'templates/RESEARCH_GOAL_TEMPLATE.md': 'research-cycle/assets/goal-template.md',
    'LICENSE': 'research-cycle/LICENSE',
}


def main():
    target = ROOT / 'dist'
    target.mkdir(exist_ok=True)
    archive_path = target / ('research-cycle-v' + VERSION + '.zip')
    manifest = {'version': VERSION, 'files': []}
    with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for source, destination in FILES.items():
            data = (ROOT / source).read_bytes()
            info = zipfile.ZipInfo(destination, date_time=(2026, 10, 27, 0, 0, 0))
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
    manifest_path = target / 'release-manifest.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    sums = []
    for path in [archive_path, manifest_path]:
        sums.append(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name)
    (target / 'SHA256SUMS').write_text('\n'.join(sums) + '\n', encoding='ascii')
    print(json.dumps({'archive': str(archive_path), 'files': len(FILES), 'checksums': sums}, indent=2))


if __name__ == '__main__':
    main()
