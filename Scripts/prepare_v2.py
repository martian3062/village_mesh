"""Create the explicit V2 pilot selection and reference register once, without downloads.

Existing authored manifests are never overwritten. Pass --audit-only for refreshable
reports; regeneration always consumes the previously saved selection.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
import subprocess
from pathlib import Path
import v2_data as data

ROOT=data.ROOT


def write_new(path, value):
    path=ROOT/path
    if path.exists(): return
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit-only',action='store_true')
    args=parser.parse_args()
    features=data.read('Assets/Geodata/pandori_nijjaran.buildings.geojson')['features']
    counts=Counter(k for f in features for k,v in f['properties'].items() if v is not None)
    report=dict(source_features=len(features),populated_attributes=dict(counts),
        height_present=sum(f['properties'].get('height') is not None for f in features),
        floors_present=sum(f['properties'].get('num_floors') is not None for f in features),
        has_parts_true=sum(f['properties'].get('has_parts') is True for f in features),
        statement='No measured height, floor or facade attributes are inferred from absent data.')
    folder=ROOT/'Docs/V2';folder.mkdir(parents=True,exist_ok=True)
    (folder/'building_attribute_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    if args.audit_only:
        print(json.dumps(report));return
    roads={r['id']:r for r in data.base.ROADS}
    route=roads[1114810501]['points']+roads[1114810502]['points'][2:]
    length=sum(math.dist(a,b) for a,b in zip(route,route[1:]))
    candidates=[]
    for building in data.normalized_buildings():
        edge=data.front_edge(building,route)
        if edge:
            d,index,chain=edge
            candidates.append(dict(building_id=building['id'],edge_index=index,chainage_cm=chain,
                setback_from_centerline_cm=d,confidence='procedural inference',interior=False))
    chosen=[]
    for chain in [length*i/15 for i in range(16)]:
        available=[c for c in candidates if c['building_id'] not in {c['building_id'] for c in chosen}]
        chosen.append(min(available,key=lambda c:abs(c['chainage_cm']-chain)+c['setback_from_centerline_cm']*.6))
    chosen.sort(key=lambda c:(c['chainage_cm'],c['building_id']))
    by_id={b['id']:b for b in data.normalized_buildings()}
    eligible=[c for c in chosen if data.entrance_clear(by_id[c['building_id']],c['edge_index'],list(by_id.values()))]
    for chain in (length*.2,length*.55,length*.8):
        candidate=min((c for c in eligible if not c['interior']),key=lambda c:abs(c['chainage_cm']-chain))
        candidate['interior']=True
    cameras=[]
    buildings={b['id']:b for b in data.normalized_buildings()}
    for i in range(8):
        pos,yaw=data.at_distance(route,length*(.03+.94*i/7))
        frontage=min(chosen,key=lambda c:abs(c['chainage_cm']-length*(.03+.94*i/7)))
        building=buildings[frontage['building_id']]
        edge=frontage['edge_index'];a=building['points'][edge];b=building['points'][(edge+1)%len(building['points'])]
        target=((a[0]+b[0])/2,(a[1]+b[1])/2)
        yaw=math.degrees(math.atan2(target[1]-pos[1],target[0]-pos[0]))
        cameras.append(dict(id='camera_%02d'%(i+1),position_cm=[*pos,170],yaw_degrees=yaw,
            pitch_degrees=-2,fov_degrees=85,reference_path=None,confidence='procedural inference',target_building_id=frontage['building_id']))
    pilot=dict(schema_version=1,selection='User-approved mapped street near V1 start',
        road_ids=[1114810501,1114810502],length_m=length/100,units='centimeters',
        centerline_cm=route,frontages=chosen,cameras=cameras,
        notes='Road alignment sourced from OSM; architecture/widths/ground levels inferred. No surveyed landmark selected.')
    data.aim_pilot_cameras(pilot,list(buildings.values()))
    write_new('Assets/Routes/pilot_street.json',pilot)
    write_new('Assets/Routes/validation_route.json',dict(schema_version=1,route_id='pandori_pilot_v2',
        units='centimeters',points_cm=[[x,y,110] for x,y in route],warmup_seconds=20,
        speed_cm_s=420,condition='daylight',resolution=[1440,900],target_p95_ms=33.3,
        notes='Proposed target, not achieved FPS. Route uses collision-aware movement; blocked sections fail.'))
    references=[]
    for c in chosen:
        references.append(dict(feature_id=c['building_id'],provider_id=c['building_id'],capture_date=None,
            source='Assets/Geodata/pandori_nijjaran.buildings.geojson',permission_or_license='ODbL-1.0; retained provider attribution',
            capture_position=None,orientation=None,measured_dimensions={},units='meters',uncertainty=None,
            reference_paths=[],confidence='sourced map attribute',reviewer=None,
            notes='Footprint only. Facade, height, room layout and props are procedural inference, not observed private interiors.'))
    write_new('Assets/Reference/manifest.json',dict(schema_version=1,confidence_categories=sorted(data.CONFIDENCE),
        local_photo_pack_available=False,features=references,local_review_status='pending'))
    paths=['Assets/Geodata/pandori_nijjaran.buildings.geojson','Assets/Geodata/pandori_nijjaran.osm.json',
        'Assets/textures.lock.json','Assets/models.lock.json','Content/Well/wind.csv','Content/Well/wind.source.json']
    write_new('Docs/V2/baseline_inputs.json',dict(baseline_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        recorded_date='2026-10-23',engine='5.8.3',seed=3062,files={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        notes='V1 input freeze. Packaged launch and performance must be recorded separately; no FPS claim.'))
    print(json.dumps(dict(audit=report,pilot_length_m=length/100,frontages=len(chosen),cameras=len(cameras))))


if __name__=='__main__':main()
