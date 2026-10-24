"""Create or verify an explicit, hashed publication list; never stages files itself."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'Docs/LFS/assets.json'
NAMES = ('VillageMesh', 'VillageMeshV2', 'VillageMeshV25', 'VillageMeshV3', 'MetaHumanPilot')
RAW_ROOTS = ('Content/V25', 'Content/V3')


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def approved_path(relative):
    if '\\' in relative or '..' in Path(relative).parts or Path(relative).is_absolute():
        return False
    if relative.startswith('Assets/Downloaded/'):
        return relative in pinned_downloads()
    if any(relative.startswith(prefix + '/') for prefix in RAW_ROOTS):
        return Path(relative).suffix in ('.json', '.jsonl', '.geojson', '.ttf', '.txt')
    prefixes = ['Content/' + name + '/' for name in NAMES]
    prefixes += ['Content/' + kind + '/' + name + '/' for kind in ('__ExternalActors__', '__ExternalObjects__') for name in NAMES]
    return relative.startswith(tuple(prefixes)) and Path(relative).suffix in ('.uasset', '.umap', '.ubulk', '.uexp')


def pinned_downloads():
    textures = json.loads((ROOT / 'Assets/textures.lock.json').read_text())['textures']
    models = json.loads((ROOT / 'Assets/models.lock.json').read_text())['files']
    result = {'Assets/Downloaded/' + item['asset'] + '_' + item['channel'] + '.jpg': item for item in textures}
    result.update({'Assets/Downloaded/Models/' + item['path']: item for item in models})
    return result


def prepare():
    audit_path = ROOT / 'Saved/LFS/dependency_audit.json'
    audit = json.loads(audit_path.read_text())
    if not audit['passed']:
        raise ValueError('A successful Unreal dependency audit is required')
    paths = set()
    for name in NAMES:
        for folder in (ROOT / 'Content' / name, ROOT / 'Content/__ExternalActors__' / name, ROOT / 'Content/__ExternalObjects__' / name):
            paths.update(path for path in folder.rglob('*') if path.is_file() and path.suffix in ('.uasset', '.umap', '.ubulk', '.uexp'))
    for folder in RAW_ROOTS:
        paths.update(path for path in (ROOT / folder).rglob('*') if path.is_file())
    pinned = pinned_downloads()
    paths.update(ROOT / name for name in pinned)
    records = []
    for path in sorted(paths):
        relative = path.relative_to(ROOT).as_posix()
        if not approved_path(relative) or path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError('Unexpected publication input: ' + relative)
        digest = sha(path)
        if relative in pinned and digest != pinned[relative]['sha256']:
            raise ValueError('Pinned download changed: ' + relative)
        group = ('poly_haven_cc0' if relative in pinned else
                 'epic_metahuman' if relative.startswith('Content/MetaHumanPilot/') else
                 'runtime_inputs' if relative.startswith(tuple(p + '/' for p in RAW_ROOTS)) else
                 'generated_village')
        records.append({'path': relative, 'bytes': path.stat().st_size, 'sha256': digest, 'group': group,
                        'lfs': path.suffix in ('.uasset', '.umap', '.ubulk', '.uexp') or relative in pinned})
    report = {'schema_version': 1, 'recorded_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'files': records, 'file_count': len(records), 'total_bytes': sum(item['bytes'] for item in records),
              'dependency_audit': audit,
              'excluded': ['Unverified legacy Content/Village imports and unrelated templates',
                           'Engine binaries, plugin source/Core Data distribution, build products, caches, Saved logs and credentials'],
              'license_details': 'README.md and ../../THIRD_PARTY_NOTICES.md; MetaHuman assets are not MIT'}
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (ROOT / 'Saved/LFS/asset-paths.txt').write_text('\n'.join(item['path'] for item in records) + '\n', encoding='utf-8')
    print(json.dumps({'files': report['file_count'], 'bytes': report['total_bytes'], 'lfs_files': sum(item['lfs'] for item in records)}))


def verify(base):
    report = json.loads(MANIFEST.read_text())
    seen = set()
    for item in report['files']:
        name = item['path']
        if name in seen or not approved_path(name):
            raise ValueError('Invalid or duplicate manifest path: ' + name)
        seen.add(name)
        path = base / name
        if not path.is_file() or not path.resolve().is_relative_to(base.resolve()) or path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
            raise ValueError('Missing, modified or unhydrated asset: ' + name)
    if len(seen) != report['file_count'] or sum(item['bytes'] for item in report['files']) != report['total_bytes']:
        raise ValueError('Manifest totals do not match its entries')
    print('LFS_ASSET_BYTES_VERIFIED', len(seen))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'verify'))
    parser.add_argument('--root', type=Path, default=ROOT, help='Optional independent checkout to verify')
    args = parser.parse_args()
    prepare() if args.action == 'prepare' else verify(args.root.resolve())
