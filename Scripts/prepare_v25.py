"""Create missing V2.5 authored contracts, validate them, stage runtime data.

Existing authoring files are never overwritten. Runtime copies are disposable.
All positions are design inference on the V2 map, not cadastral field data.
"""
from pathlib import Path
import json,math,shutil,hashlib
import pandori_layout as geo
import v25_contracts as rules
ROOT=Path(__file__).resolve().parents[1]

def write_missing(name,value):
    path=ROOT/name;path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return json.loads(path.read_text(encoding='utf-8'))

def main():
    route=json.loads((ROOT/'Assets/Routes/validation_route.json').read_text())['points_cm']
    nodes=[dict(id='lane_%02d'%i,position_cm=[p[0],p[1],90]) for i,p in enumerate(route)]
    edges=[[nodes[i]['id'],nodes[i+1]['id']] for i in range(len(nodes)-1)]
    nodes += [dict(id='farm_gate',position_cm=[3200,-2300,90]),dict(id='farm_south',position_cm=[3200,-5500,90]),dict(id='farm_shelter',position_cm=[2600,-1300,90])]
    edges += [['lane_14','farm_gate'],['farm_gate','farm_south'],['farm_gate','farm_shelter']]
    nodes += [dict(id='plot_access',position_cm=[2800,-2300,90]),dict(id='vehicle_stop',position_cm=[3500,-5100,90])]
    edges += [['farm_gate','plot_access'],['farm_south','vehicle_stop']]
    crop=['rice','managed_residue','prepared_soil','fodder']
    parcels=[]
    for i,(x,y) in enumerate([(200,-1800),(1600,-1800),(200,-4000),(1600,-4000)]):
        ring=[[x,y],[x+1050,y],[x+1050,y-1500],[x,y-1500],[x,y]]
        lonlat=[[geo.LON+a/100/geo.EARTH*180/math.pi/math.cos(math.radians(geo.LAT)),geo.LAT+b/100/geo.EARTH*180/math.pi] for a,b in ring]
        parcels.append({'type':'Feature','id':'plot_%d'%i,'geometry':{'type':'Polygon','coordinates':[lonlat]},'properties':{
            'plot_id':'plot_%d'%i,'polygon_cm':ring,'access_node':'farm_gate' if i<2 else 'farm_south',
            'assigned_jobs':['inspect','irrigation_check'],'crop_type':crop[i],'growth_stage':['maturing','harvested','awaiting_sowing','vegetative'][i],
            'sowing_date':None,'variety_if_known':None,'irrigation_state':'check_due','residue_state':'managed',
            'soil_visual_state':'dry','machinery_route':'farm_shuttle','source':'original demonstration design on flat V2 terrain',
            'confidence':'procedural inference','ownership':None,'scene_date':'2026-10-23'}})
    names=['Harjit','Simran','Aman','Gurleen','Navdeep','Mehar','Kiran','Jas']
    roles=['plot_inspector','shopkeeper','vehicle_operator','commuter','student_adult','errands','courtyard_visitor','visitor']
    homes=[0,5,10,12,17,19,6,20];dest=['plot_access','lane_06','vehicle_stop','lane_21','lane_17','lane_08','lane_05','lane_12']
    people=[];schedules=[];outfits=[]
    colors=[[.22,.34,.30],[.41,.19,.24],[.17,.25,.38],[.48,.37,.18],[.23,.18,.31],[.46,.24,.15],[.17,.35,.43],[.34,.36,.25]]
    for i in range(8):
        identifier='resident_%02d'%i
        people.append(dict(id=identifier,name=names[i],fictional=True,adult=True,role=roles[i],home_node='lane_%02d'%homes[i],
            work_node=dest[i],shelter_node='farm_shelter',outfit_id='outfit_%02d'%i,voice_set=None,
            capabilities=[['inspect','carry'],['stock','converse'],['drive','inspect'],['commute'],['commute','visit'],['carry','visit'],['visit','converse'],['visit']][i],
            preferences=dict(talkativeness=.25+.08*i,rest_preference=.3+.05*(i%3)),relationships={},
            assigned_plot='plot_%d'%(i%4) if i in (0,2) else None,reviewer=None,review_status='fictional_unreviewed_design'))
        schedules.append(dict(npc_id=identifier,windows=[dict(start_hour=8+i*.15,end_hour=17-i*.1,task=roles[i],destination=dest[i])],
            rainy_task='shelter',fallback='return_home',minimum_task_seconds=8))
        outfits.append(dict(id='outfit_%02d'%i,garment_family=['shirt_trousers','long_tunic_trousers','jacket_trousers','shirt_trousers'][i%4],
            color=colors[i],headwear=None,footwear='closed_shoes',voice=None,review_status='prototype_not_locally_reviewed',
            source='original procedural visualization; replace through approved asset manifest',cloth_enabled=False,distance_fallback='rigid/skinned'))
    write_missing('Assets/NPC/personas.json',{'schema_version':1,'people':people})
    write_missing('Assets/NPC/schedules.json',{'schema_version':1,'schedules':schedules})
    write_missing('Assets/NPC/action_schema.json',{'schema_version':rules.SCHEMA,'features':[dict(index=i,name=n,range=[0,1],missing=0) for i,n in enumerate(rules.FEATURES)],
        'invalid_input':'reject snapshot; deterministic fallback','actions':[dict(index=i,name=n,implemented=i<9) for i,n in enumerate(rules.ACTIONS)],
        'mask_version':'v25.mask.v1','default_policy':'rules','learned_mode':'experimental explicit opt-in'})
    write_missing('Assets/NPC/navigation.json',{'schema_version':1,'units':'centimeters','nodes':nodes,'edges':edges,
        'source':'OSM V2 centerline plus explicitly inferred farm access links','navigation':'authored graph with character collision sweeps; not a NavMesh claim'})
    write_missing('Assets/Wardrobe/outfits.json',{'schema_version':1,'outfits':outfits,'local_review':None,'release_quality_accepted':False})
    write_missing('Assets/Farms/parcels.geojson',{'type':'FeatureCollection','features':parcels})
    write_missing('Assets/Farms/crop_calendar.json',{'schema_version':1,'scene_date':'2026-10-23','progression':'explicit scenario change only; no real-time growth',
        'provenance':'illustrative late-October design, not observed crop states or agronomic advice','review_status':'pending_dated_local_reference',
        'presets':{'late_october':['maturing_rice','managed_residue','prepared_soil','fodder']},
        'references':['https://pau.edu/content/ccil/pf/pp_kharif.pdf','https://pau.edu/content/ccil/pf/pp_rabi.pdf']})
    write_missing('Assets/Roads/road_profiles.json',{'schema_version':1,'traffic_side':'left','confidence':'procedural inference; widths not surveyed','profiles':[
        dict(id='connector',surface='existing_asphalt',width_cm=450,crown_cm=6,wet_speed_factor=.7),
        dict(id='lane',surface='existing_V2_paved_lane',width_cm=420,crown_cm=6,wet_speed_factor=.6),
        dict(id='field_track',surface='compacted_soil',width_cm=280,crown_cm=3,wet_speed_factor=.5)],
        'passages':[dict(id='farm_passage',nodes=['lane_14','farm_gate','farm_south'],capacity=1,release_on_cancel=True)],
        'measurement_status':'unmeasured_design','engineering_compliance_claim':False})
    write_missing('Assets/Routes/tractor_route.json',{'schema_version':1,'id':'farm_shuttle','nodes':['lane_14','farm_gate','farm_south'],
        'mode':'reserved single-vehicle bidirectional shuttle','speed_cm_s':110,'turning':'stop and turn within authored endpoint clearance; no calibrated vehicle dynamics',
        'vehicle_width_cm':160,'vehicle_length_cm':250,'trolley_enabled':False,'confidence':'procedural inference'})
    lines=[('greeting','ਸਤ ਸ੍ਰੀ ਅਕਾਲ ਜੀ।','Sat Sri Akal ji.','Hello.'),
        ('directions','ਤੁਸੀਂ ਕਿੱਥੇ ਜਾਣਾ ਹੈ?','Tusi kithe jana hai?','Where would you like to go?'),
        ('rain','ਮੀਂਹ ਆ ਰਿਹਾ ਹੈ, ਅੰਦਰ ਆ ਜਾਓ।','Meenh aa riha hai, andar aa jao.','It is raining; come inside.'),
        ('shop_closed','ਦੁਕਾਨ ਅਜੇ ਬੰਦ ਹੈ।','Dukan aje band hai.','The shop is still closed.'),
        ('unknown','ਮੈਨੂੰ ਇਸ ਬਾਰੇ ਪਤਾ ਨਹੀਂ।','Mainu is bare pata nahi.','I do not know about this.'),
        ('thanks','ਧੰਨਵਾਦ ਜੀ।','Dhanvaad ji.','Thank you.'),
        ('farewell','ਫਿਰ ਮਿਲਾਂਗੇ ਜੀ।','Phir milange ji.','See you again.')]
    path=ROOT/'Assets/Dialogue/punjabi_lines.jsonl';path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        path.write_text(''.join(json.dumps(dict(line_id='pa_'+intent,intent=intent,speaker_style='neutral',context_requirements={'rain':'raining','shop_closed':'shop_closed'}.get(intent,'none'),
            permitted_slots=[],Gurmukhi_text=g,Roman_transliteration=r,English_gloss=e,audio_id=None,cooldown=8,reviewer=None,review_status='draft_unreviewed'),ensure_ascii=False)+'\n' for intent,g,r,e in lines),encoding='utf-8')
    write_missing('Assets/NPC/scene.json',{'schema_version':1,'scene_date':'2026-10-23','timezone':'Asia/Kolkata','start_hour':13.5,'game_minutes_per_real_minute':5,
        'active_npcs':8,'decision_interval_seconds':.4,'max_inflight_batches':1,'stale_result_seconds':1,'save_version':1,
        'default_policy':'rules','experimental_policy_switch':'-V25Learned','dialogue_mode':'draft_subtitles_and_choices','crop_progression_enabled':False})
    validate()
    target=ROOT/'Content/V25/Data';target.mkdir(parents=True,exist_ok=True)
    files=['NPC/personas.json','NPC/schedules.json','NPC/action_schema.json','NPC/navigation.json','NPC/scene.json','Wardrobe/outfits.json','Farms/parcels.geojson','Farms/crop_calendar.json','Roads/road_profiles.json','Routes/tractor_route.json','Dialogue/punjabi_lines.jsonl','Models/npc_model_manifest.json','Models/policy_parity.json']
    hashes={}
    for name in files:
        path=ROOT/'Assets'/name;dest=target/path.name;shutil.copyfile(path,dest);hashes[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    (target/'input_hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
    font_target=ROOT/'Content/V25/Fonts';font_target.mkdir(parents=True,exist_ok=True)
    lock=json.loads((ROOT/'Assets/v25_assets.lock.json').read_text())
    for asset in lock['assets']:
        source=ROOT/asset['file']
        if hashlib.sha256(source.read_bytes()).hexdigest()!=asset['sha256']:raise ValueError('Font/source asset checksum mismatch: '+asset['file'])
        shutil.copyfile(source,font_target/source.name)
    print('V2.5 contracts validated and staged; existing authored manifests preserved.')

def validate():
    read=lambda name:json.loads((ROOT/'Assets'/name).read_text(encoding='utf-8'))
    people=read('NPC/personas.json')['people'];nav=read('NPC/navigation.json');nodes={n['id'] for n in nav['nodes']}
    assert len(people)==8 and len({p['id'] for p in people})==8
    assert len(rules.FEATURES)==64 and len(rules.ACTIONS)==48
    for p in people:
        assert p['fictional'] and all(p[k] in nodes for k in ('home_node','work_node','shelter_node'))
    for a,b in nav['edges']:assert a in nodes and b in nodes
    for parcel in read('Farms/parcels.geojson')['features']:
        props=parcel['properties'];assert props['access_node'] in nodes and props['scene_date']=='2026-10-23'
        ring=props['polygon_cm'];xs=[p[0] for p in ring];ys=[p[1] for p in ring]
        for x in range(int(min(xs)),int(max(xs))+1,75):
            for y in range(int(min(ys)),int(max(ys))+1,75):
                if not geo.clear_site(x,y,0):raise ValueError('Plot overlaps mapped building/road: '+props['plot_id']+' '+str((x,y)))
    for line in (ROOT/'Assets/Dialogue/punjabi_lines.jsonl').read_text(encoding='utf-8').splitlines():
        row=json.loads(line);rules.normalize_text(row['Gurmukhi_text']);assert row['reviewer'] is None

if __name__=='__main__':main()
