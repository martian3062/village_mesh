"""Publish a small evidence index; never interpret NullRHI timing as rendered FPS."""
import hashlib
import json
from pathlib import Path
import shutil
from readme_sections import update_report

ROOT=Path(__file__).resolve().parents[1]
SAVED=ROOT/'Saved/VillageMeshV2'
DOCS=ROOT/'Docs/V2'


def main():
    DOCS.mkdir(parents=True,exist_ok=True)
    runs=[]
    for path in sorted(SAVED.glob('*.json')):
        if path.name.startswith(('route_','capture_','interactions_','soak_')) and '_lumen_' not in path.name:
            record=json.loads(path.read_text(encoding='utf-8-sig'))
            if not record.get('rendered',False):record['p95_target_met']=None
            record['file']=path.name;runs.append(record)
    captures=[]
    for condition in ('daylight','evening','overcast','rain'):
        for index in range(1,9):
            path=SAVED/(condition+'_%02d.png'%index)
            if path.exists():captures.append(dict(file=path.name,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        preview=SAVED/(condition+'_04.png')
        if preview.exists():shutil.copyfile(preview,DOCS/(condition+'.png'))
    for name in ('pilot_report.json','generation_manifest.json','portability.json','runtime_smoke.json','overview.png'):
        if (SAVED/name).exists():shutil.copyfile(SAVED/name,DOCS/name)
    summary=dict(schema_version=1,runs=runs,captures=captures,
        rendered_route_runs=sum(r['mode']=='route' and r.get('rendered',False) for r in runs),
        scope='Local development evidence only. Capture and interaction timing is not a traversal benchmark. Complete logs and all views remain under Saved.',
        unverified=['local architectural review','independent fresh-machine setup','shipping release','separate CPU/GPU frame timing and VRAM peak'])
    (DOCS/'evidence.json').write_text(json.dumps(summary,indent=2)+'\n')
    lines=['# Local V2 results','',
        'Unreal 5.8.3 on the [recorded workstation](hardware_snapshot.json). Rendered diagnostics use offscreen D3D12, Epic scalability, 1440 x 900 output, 67% render scale for traversal and 100% for captures. Timings are observed frame wall time after warmup, not a separate CPU/GPU profile.','',
        '| Run | Build | Outcome | p95 / max frame ms | Peak process MiB |',
        '| --- | --- | --- | --- | --- |']
    for r in runs:
        timing='not a route benchmark'
        if r['mode']=='route' and r.get('rendered'):
            timing='%.2f / %.2f'%(r['p95_frame_ms'],r['max_frame_ms'])
        build='editor game' if r.get('editor_build',True) else 'standalone package'
        if not r.get('rendered',False):build+=' (NullRHI)'
        lines.append('| %s | %s | %s | %s | %.1f |'%(r['file'],build,'pass' if r['passed'] else 'FAIL',timing,r['peak_process_physical_bytes']/1024**2))
    lines+=['','The proposed route target is p95 <=33.3 ms. Passing that percentile does not mean every frame stayed below the target. Capture and interaction timings are deliberately excluded from this comparison.','',
        '## Captures','',f'{len(captures)} fixed-camera PNGs indexed with SHA256 checksums in [evidence.json](evidence.json). Four representative views appear in the [pilot section](../../README.md#v2); the complete set remains in `Saved/VillageMeshV2`.','']
    soaks=[r for r in runs if r['mode']=='soak']
    if soaks:
        lines+=['## Continuous soak','']
        for r in soaks:
            lines+=['%s: **%s**, %.1f wall-clock minutes, %d completed route legs. Weather cycled between daylight, overcast, rain and evening. Per-minute process memory samples are retained in the evidence index.'%(r['file'],'pass' if r['passed'] else 'FAIL',r.get('soak_wall_seconds',0)/60,r.get('completed_route_legs',0)),'',
                'Mixed-weather frame p95 %.2f ms; largest frame %.2f ms. This is not an additional comparable daylight trial.'%(r['p95_frame_ms'],r['max_frame_ms']),'']
            monitor=SAVED/('package_monitor_soak_'+r['run_id']+'.json')
            if monitor.exists():
                samples=json.loads(monitor.read_text(encoding='utf-8-sig')).get('gpu_samples',[])
                rows=[]
                for sample in samples:
                    values=sample.get('adapter_csv',[])
                    for value in ([values] if isinstance(values,str) else values):
                        fields=value.split(',')
                        try:rows.append((float(fields[0]),float(fields[1])))
                        except (ValueError,IndexError):continue
                if rows:
                    lines+=['Whole-adapter monitoring for this run peaked at %s MiB and %s C, including other applications.'%(format(max(v[0] for v in rows),',.0f'),format(max(v[1] for v in rows),'.0f')),'']
        lines+=['Interactive launchers cap at 60 FPS; automated measurements remain uncapped. Process-memory samples do not prove absence of all leaks.','']
    else:lines+=['Continuous 30-minute soak: no completed result recorded yet.','']
    lines+=['## Acceptance limits','',
        'Local facade photographs, measured ground/facade dimensions, local architectural review, dedicated Lumen diagnostic views, complete people/animal/traffic/audio work, separate CPU/GPU frame profiling, and independent fresh-machine testing remain outstanding. This is a reproducible procedural pilot, not an accepted hyperrealistic reconstruction. See the [milestone register](../V2_ACCEPTANCE.txt).','',
        'The offscreen Lumen visualization attempts produced lit images despite accepting the console settings. They are excluded from the beauty evidence and do not establish surface-cache coverage. See the [attempt record](lumen_diagnostic_attempt.json).','']
    update_report('v2-results', '\n'.join(lines), 'Docs/V2')
    for path in SAVED.glob('package_monitor_*.json'):
        shutil.copyfile(path,DOCS/path.name)
    print(json.dumps(dict(runs=len(runs),capture_files=len(captures),rendered_route_runs=summary['rendered_route_runs'])))


if __name__=='__main__':main()
