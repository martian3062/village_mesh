"""Publication/package audit for V3: input identity, namespaces and reproducibility."""
import json,hashlib
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def source_sha(p):return hashlib.sha256(p.read_bytes() if p.suffix=='.png' else p.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
def main():
    package=ROOT/'Saved/Packages/V3/Windows'
    paths=[s.split('\t')[0] for s in (package/'Manifest_UFSFiles_Win64.txt').read_text().splitlines()]
    content=[p.split('/Content/',1)[1] for p in paths if p.startswith('rural_pardeep/Content/')]
    unreviewed=[p for p in content if p.endswith(('.uasset','.umap')) and not p.startswith(('VillageMeshV2/','VillageMeshV25/','VillageMeshV3/'))]
    if unreviewed:raise ValueError('Unreviewed asset namespaces: '+str(unreviewed))
    for p in ['VillageMeshV3/UI/T_VillageAtlas.uasset','VillageMeshV3/Lvl_PandoriV3_WP.umap','VillageMeshV25/Models/npc_policy_v1.uasset']:
        if p not in content:raise ValueError('Required cooked asset missing: '+p)
    source=ROOT/'Assets/World/v3_world.json';staged=package/'rural_pardeep/Content/V3/Data/v3_world.json'
    if sha(source)!=sha(staged):raise ValueError('World contract differs from staged copy')
    frozen=json.loads((ROOT/'Docs/V2/baseline_inputs.json').read_text())['files']
    for name,expected in frozen.items():
        if sha(ROOT/name)!=expected:raise ValueError('Frozen source changed: '+name)
    inputs=json.loads((package/'rural_pardeep/Content/V25/Data/input_hashes.json').read_text())
    for name,expected in inputs.items():
        if sha(ROOT/'Assets'/name)!=expected or sha(package/'rural_pardeep/Content/V25/Data'/Path(name).name)!=expected:raise ValueError('V2.5 input changed: '+name)
    lock=json.loads((ROOT/'Assets/v25_assets.lock.json').read_text())
    for item in lock['assets']:
        if sha(package/'rural_pardeep/Content/V25/Fonts'/Path(item['file']).name)!=item['sha256']:raise ValueError('Pinned font/licence changed')
    build=json.loads((ROOT/'Saved/VillageMeshV3/build_report.json').read_text())
    runtime=json.loads((ROOT/'Docs/V3/runtime_packaged.json').read_text(encoding='utf-8-sig'))
    if not runtime['passed'] or not runtime['overview_streaming_complete'] or runtime['overview_mesh_chunks']!=build['mesh_chunks']:
        raise ValueError('Standalone overview did not load every generated village mesh chunk')
    files=[p for folder in ('Scripts','Source','Config') for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in ('.py','.ps1','.cpp','.h','.cs','.ini','.json') and '__pycache__' not in str(p) and p.name!='DefaultEditorPerProjectUserSettings.ini']
    files += [ROOT/p for p in ['Assets/World/v3_world.json','Assets/World/v3_map.png','README.md','Docs/V3/README.md','Tests/test_v3_world.py','THIRD_PARTY_NOTICES.md','requirements-v3-tools.txt']]
    report=dict(passed=True,scope='Exact staged inputs and cooked namespace audit; not independent machine validation',
        counts={k:build[k] for k in ('buildings','roads','landmarks','fields','styles','mesh_chunks','triangles')},
        namespaces=dict(Counter(p.split('/')[0] for p in content if p.endswith(('.uasset','.umap')))),
        world_sha256=sha(source),frozen_inputs=frozen,source_hash_encoding='LF-normalized text; PNG exact bytes',
        source_sha256={p.relative_to(ROOT).as_posix():source_sha(p) for p in sorted(files)})
    (ROOT/'Docs/V3/package_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('V3 package audit passed; atlas, map, model, input hashes, fonts and frozen sources verified.')
if __name__=='__main__':main()
