"""Publish explicit, source-bound local V2.5 evidence; never promote old runs."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
SAVED=ROOT/'Saved/VillageMeshV25';DOCS=ROOT/'Docs/V25'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    DOCS.mkdir(parents=True,exist_ok=True)
    package=ROOT/'Saved/Packages/V25/Windows'
    binary_hash=sha(package/'rural_pardeep/Binaries/Win64/rural_pardeep.exe')
    runs=[];monitors=[];routes=[]
    # Explicit final runs only. Earlier debugging/editor results remain local.
    for name in ('packaged_rendered','packaged_missing_model','packaged_rules','packaged_soak'):
        p=SAVED/('runtime_'+name+'.json')
        r=json.loads(p.read_text(encoding='utf-8-sig'));r['file']=p.name
        monitor=SAVED/('monitor_'+name+'.json');m=json.loads(monitor.read_text(encoding='utf-8-sig'))
        if m['exe_sha256']!=binary_hash:raise ValueError('Run used a different executable: '+name)
        if not r['passed'] or r['editor_build']:raise ValueError('Final standalone check failed: '+name)
        expected=1800 if name=='packaged_soak' else 120 if name=='packaged_missing_model' else 180
        if not expected<=r['wall_seconds']<=expected+10 or r['max_frame_ms']>60000:raise ValueError('Interrupted/noncontinuous run: '+name)
        runs.append(r);monitors.append(m);shutil.copyfile(monitor,DOCS/monitor.name)
    for condition in ('daylight','rain'):
        for repeat in range(1,4):
            p=SAVED/('route_'+condition+'_v25_'+condition+str(repeat)+'.json')
            r=json.loads(p.read_text(encoding='utf-8-sig'))
            if not r['passed'] or r['editor_build'] or not r['rendered']:raise ValueError('Failed traversal: '+p.name)
            if r['wall_seconds']>300 or r['max_frame_ms']>60000:raise ValueError('Interrupted traversal: '+p.name)
            m=json.loads((SAVED/('monitor_route_v25_'+condition+str(repeat)+'.json')).read_text(encoding='utf-8-sig'))
            if m['exe_sha256']!=binary_hash:raise ValueError('Traversal used a different executable: '+p.name)
            r['launch']=m
            r['file']=p.name;routes.append(r)
    images=[]
    for name in ('dialogue.png','farms_rain.png'):
        if (SAVED/name).exists():shutil.copyfile(SAVED/name,DOCS/name);images.append(dict(file=name,sha256=sha(DOCS/name)))
    manifest=json.loads((ROOT/'Assets/Models/npc_model_manifest.json').read_text())
    soak_log=(ROOT/'Saved/Logs/V25Packaged_packaged_soak.log').read_text(encoding='utf-8-sig',errors='replace')
    timeline=[dict(wall_seconds=float(w),completed_tasks=int(t),tractor_legs=int(v),inference_batches=int(b))
        for w,t,v,b in re.findall(r'V25_PROGRESS wall=([\d.]+) tasks=(\d+) tractor_legs=(\d+) batches=(\d+)',soak_log)]
    evidence=dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(),engine='5.8.3',model_sha256=manifest['deployed_models'][0]['sha256'],
        deployed_parameters=manifest['deployed_total_parameters'],exe_sha256=binary_hash,runs=runs,monitors=monitors,traversals=routes,soak_timeline=timeline,images=images,
        limits=['procedural character/vehicle art','unreviewed Punjabi and no recorded voices','no independent fresh-machine test','no separate GPU frame timings','no complete StateTree/NavMesh/cloth implementation'])
    (DOCS/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    lines=['# V2.5 local validation','',
        'These results belong to this workstation and Development build. Rendered checks use D3D12 at 1440 x 900, 67% render scale and a 60 FPS cap. The workstation also ran other applications; these are not isolated hardware benchmarks. Automated scene time/weather changes are labelled test behaviour; crop growth remains disabled.','',
        '| Run | Rendering / build | Outcome | Frame p95 / max ms | CPU batch p95 ms | Director tick p95 ms |',
        '| --- | --- | --- | --- | --- | --- |']
    for r in runs:
        render=('rendered' if r['rendered'] else 'NullRHI')+(' editor game' if r['editor_build'] else ' standalone')
        frames='%.2f / %.2f'%(r['p95_frame_ms'],r['max_frame_ms']) if r['rendered'] else 'not rendering evidence'
        lines.append('| %s | %s | %s | %s | %.3f | %.3f |'%(r['run_id'],render,'pass' if r['passed'] else 'FAIL',frames,r['p95_inference_batch_ms'],r['p95_director_tick_ms']))
    by_name={r['run_id']:r for r in runs}
    lines+=['','| Fictional resident | Rules / 180 s | Learned / 180 s | Learned soak / 1800 s |',
        '| --- | ---: | ---: | ---: |']
    personas=json.loads((ROOT/'Assets/NPC/personas.json').read_text())['people']
    for person in personas:
        counts=[next(p['completed_tasks'] for p in by_name[name]['final_state']['residents'] if p['id']==person['id'])
            for name in ('packaged_rules','packaged_rendered','packaged_soak')]
        lines.append('| %s | %d | %d | %d |'%(person['name'],*counts))
    incomplete=[person['name'] for person in personas if next(p['completed_tasks'] for p in by_name['packaged_soak']['final_state']['residents'] if p['id']==person['id'])==0]
    if incomplete:lines+=['','Activity-completion coverage remains open for **'+', '.join(incomplete)+'**: neither completed an activity in this accelerated weather/schedule run. The bounded stability pass does not accept every resident routine.']
    lines+=['','Counts represent completed generic prototype activities, not reviewed human work animations. The two short runs use matched time/weather/capture scripts; the camera follows a moving resident, so the resulting views can differ. These individual runs do not establish a statistical behaviour or frame-rate advantage. The longer run uses a different weather period and is not a direct speed comparison.']
    lines+=['','A CPU batch is up to eight serialized policy calls on one worker-owned instance. The director tick excludes worker inference. Frame distributions exclude the first 20 simulation seconds; later streaming, font and capture hitches remain included. Queue delay, stale rejections, per-person activity and save/restore results are retained in [evidence.json](evidence.json). A successful bounded check does not certify every daily routine or an animation/vehicle swept path.','',
        'Six collision-enabled pedestrian traversals (three daylight, three rain) ran in the V2.5 standalone scene with residents and the CPU policy loaded in shadow mode. Exact paths, durations and frame measurements are retained in the traversal records in evidence.json. These checks are not vehicle clearance certification. The separate 30-minute simulation soak keeps the player at the start and exercises accelerated schedules/weather; it is not the earlier V2 moving-camera soak.','',
        'The original synthetic policy achieved 99.65% agreement with its rule teacher on the held-out scenario dataset; no advantage over that teacher is established. Rules remain the default. [Training evaluation](policy_evaluation.json).','',
        '## Open acceptance','',
        'Local wardrobe/voice/language review, complete cloth/contact/vehicle animation, measured roads/farms, separate GPU profiling, and independent fresh-machine release testing remain open. See the [acceptance register](../V25_ACCEPTANCE.txt).','']
    for r in runs:
        if r['wall_seconds']>=1800:lines+=['Continuous run `%s`: %.2f minutes, %d completed tractor legs, peak process physical memory %.1f MiB. These bounded observations are not a memory-leak proof.'%(r['run_id'],r['wall_seconds']/60,r['tractor_legs'],r['peak_process_bytes']/1048576),'']
    (DOCS/'RESULTS.md').write_text('\n'.join(lines),encoding='utf-8')
    paths=[]
    for directory in ('Source','Scripts','Config','Assets/NPC','Assets/Models','Assets/Dialogue','Assets/Wardrobe','Assets/Farms','Assets/Roads','Assets/Fonts'):
        paths.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths.extend(ROOT/p for p in ('rural_pardeep.uproject','Assets/Routes/tractor_route.json','Assets/v25_assets.lock.json','requirements-v25-tools.txt','requirements-tools.txt','.gitattributes','LICENSE','THIRD_PARTY_NOTICES.md'))
    ignored=subprocess.run(['git','check-ignore','-z','--stdin'],input=('\0'.join(p.relative_to(ROOT).as_posix() for p in paths)+'\0').encode(),capture_output=True)
    if ignored.returncode not in (0,1):raise RuntimeError(ignored.stderr)
    ignore=set(ignored.stdout.decode().split('\0'))
    sources={}
    for p in paths:
        name=p.relative_to(ROOT).as_posix()
        if name in ignore:continue
        data=p.read_bytes()
        if p.suffix not in ('.onnx','.ttf','.geojson'):data=data.replace(b'\r\n',b'\n')
        sources[name]=hashlib.sha256(data).hexdigest()
    artifacts={p.relative_to(package).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(package.rglob('*')) if p.is_file() and p.suffix in ('.exe','.utoc','.ucas','.pak')}
    (DOCS/'build_manifest.json').write_text(json.dumps(dict(source_convention='canonical LF text; exact bytes for ONNX/TTF/GeoJSON',source_sha256=sources,package_files=artifacts),indent=2)+'\n')
    print(json.dumps(dict(runs=len(runs),traversals=len(routes),images=len(images),source_files=len(sources),package_artifacts=len(artifacts))))
if __name__=='__main__':main()
