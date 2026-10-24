"""Check final package namespaces, staged contracts, pinned fonts and frozen inputs."""
from pathlib import Path
from collections import Counter
import hashlib,json

ROOT=Path(__file__).resolve().parents[1]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    package=ROOT/'Saved/Packages/V25/Windows'
    paths=[s.split('\t')[0] for s in (package/'Manifest_UFSFiles_Win64.txt').read_text().splitlines()]
    content=[p.split('/Content/',1)[1] for p in paths if p.startswith('rural_pardeep/Content/')]
    unreviewed=[p for p in content if p.endswith(('.uasset','.umap')) and not p.startswith(('VillageMeshV2/','VillageMeshV25/'))]
    if unreviewed:raise ValueError('Unreviewed project asset namespaces: '+str(unreviewed))
    required=['VillageMeshV25/Models/npc_policy_v1.uasset','VillageMeshV25/Materials/M_V25Color.uasset']
    if not all(p in content for p in required):raise ValueError('Required V2.5 cooked assets missing')
    runtime=package/'rural_pardeep/Content/V25'
    hashes=json.loads((runtime/'Data/input_hashes.json').read_text())
    for name,expected in hashes.items():
        if sha(ROOT/'Assets'/name)!=expected or sha(runtime/'Data'/Path(name).name)!=expected:
            raise ValueError('Staged authoring contract differs: '+name)
    font_lock=json.loads((ROOT/'Assets/v25_assets.lock.json').read_text())
    for item in font_lock['assets']:
        if sha(runtime/'Fonts'/Path(item['file']).name)!=item['sha256']:raise ValueError('Font/license mismatch')
    frozen=json.loads((ROOT/'Docs/V2/baseline_inputs.json').read_text())['files']
    for name,expected in frozen.items():
        if sha(ROOT/name)!=expected:raise ValueError('Frozen input changed: '+name)
    report=dict(passed=True,scope='Local package manifests and exact staged source bytes; not a fresh-machine or full licence audit',
        project_asset_namespaces=dict(Counter(p.split('/')[0] for p in content if p.endswith(('.uasset','.umap')))),
        unreviewed_project_assets=unreviewed,staged_contract_sha256=hashes,pinned_font_assets=font_lock['assets'],frozen_input_sha256=frozen)
    (ROOT/'Docs/V25/package_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('V2.5 package audit passed: namespaces, '+str(len(hashes))+' contracts, pinned font/license and six frozen inputs.')

if __name__=='__main__':main()
