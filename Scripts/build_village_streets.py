"""Build the third-person village copy, preserving the previous V3 maps."""
import hashlib
import json
import math
import sys
from pathlib import Path
import unreal

ROOT=Path(unreal.Paths.project_dir());sys.path.insert(0,str(ROOT/'Scripts'))
import build_open_world as api
import pandori_layout as layout
api.DEST='/Game/VillageMeshV3';api.MAT=api.DEST+'/Streets/Materials'
OUT=ROOT/'Saved/VillageStreets';OUT.mkdir(parents=True,exist_ok=True)
PLAN=json.loads((OUT/'geometry.json').read_text())
MAP=api.DEST+'/Lvl_PandoriV3_Pardeep'


def paving(name, tile, color):
    mat=api.create(name,unreal.Material,unreal.MaterialFactoryNew())
    api.MEL.delete_all_material_expressions(mat)
    uv=api.expr(mat,unreal.MaterialExpressionTextureCoordinate)
    def input_uv():
        item=unreal.CustomInput();item.set_editor_property('input_name','UV');return item
    common=f'''float2 q=UV/float2({tile[0]},{tile[1]});
float row=floor(q.y); q.x+=fmod(row,2)*0.5;
float2 cell=floor(q); float2 f=frac(q);
float2 d=min(f,1-f)*float2({tile[0]},{tile[1]});
float edge=min(d.x,d.y); float mask=smoothstep(.0015,.0045,edge);
float variation=frac(sin(dot(cell,float2(127.1,311.7)))*43758.5453);
'''
    rgb=api.expr(mat,unreal.MaterialExpressionCustom,
        code=common+f'return lerp(float3(.055,.045,.03),float3({color[0]},{color[1]},{color[2]})*(.82+variation*.30),mask);',
        output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT3,
        inputs=[input_uv()])
    api.link(uv,rgb,'UV');api.MEL.connect_material_property(rgb,'',unreal.MaterialProperty.MP_BASE_COLOR)
    normal=api.expr(mat,unreal.MaterialExpressionCustom,
        code=common+'''float bevel=1-smoothstep(.0015,.006,edge);
float2 n=(d.x<d.y)?float2(f.x<.5?-bevel:bevel,0):float2(0,f.y<.5?-bevel:bevel);
return normalize(float3(n*.48,1));''',
        output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT3,
        inputs=[input_uv()])
    api.link(uv,normal,'UV');api.MEL.connect_material_property(normal,'',unreal.MaterialProperty.MP_NORMAL)
    wet=api.expr(mat,unreal.MaterialExpressionCollectionParameter,
        collection=api.EAL.load_asset('/Game/VillageMeshV2/MPC_Weather'),parameter_name='Wetness')
    rough=api.expr(mat,unreal.MaterialExpressionLinearInterpolate)
    api.link(api.scalar(mat,.88),rough,'A');api.link(api.scalar(mat,.27),rough,'B');api.link(wet,rough,'Alpha')
    api.MEL.connect_material_property(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
    dark=api.expr(mat,unreal.MaterialExpressionMultiply);api.link(rgb,dark,'A');api.link(api.scalar(mat,.62),dark,'B')
    blend=api.expr(mat,unreal.MaterialExpressionLinearInterpolate);api.link(rgb,blend,'A');api.link(dark,blend,'B');api.link(wet,blend,'Alpha')
    api.MEL.connect_material_property(blend,'',unreal.MaterialProperty.MP_BASE_COLOR)
    return api.finish(mat)


def locomotion():
    folder=api.DEST+'/Player';api.EAL.make_directory(folder)
    unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(
        ['/MetaHumanCharacter/Optional/Animation'],force_rescan=True)
    appearance=folder+'/BP_PardeepAppearance'
    if not api.EAL.does_asset_exist(appearance):
        blueprint=api.EAL.duplicate_asset('/Game/MetaHumanPilot/Assembled/Manpreet/BP_Manpreet',appearance)
        if not blueprint:raise RuntimeError('Could not create the replaceable player appearance')
        unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
        api.EAL.save_loaded_asset(blueprint,only_if_is_dirty=False)
    base='/MetaHumanCharacter/Optional/Animation/UEFNAnimPreset/Locomotion/'
    names=['AS_MH_Neutral_Stand_Idle_Loop','AS_MH_Neutral_Walk_Loop_F','AS_MH_Neutral_Run_Loop_F']
    clips=[]
    for name in names:
        clip=api.EAL.load_asset(base+name)
        if not clip:raise RuntimeError('Required installed animation missing: '+name)
        clips.append(clip)
    factory=unreal.BlendSpaceFactory1D();factory.set_editor_property('target_skeleton',clips[0].get_editor_property('skeleton'))
    blend=api.create('BS_PlayerLocomotion',unreal.BlendSpace1D,factory,folder)
    axes=list(blend.get_editor_property('blend_parameters'))
    axes[0].set_editor_property('display_name','Speed');axes[0].set_editor_property('min',0.)
    axes[0].set_editor_property('max',420.);axes[0].set_editor_property('grid_num',7)
    blend.set_editor_property('blend_parameters',axes)
    samples=[]
    for clip,speed in zip(clips,(0,180,420)):
        sample=unreal.BlendSample();sample.set_editor_property('animation',clip)
        sample.set_editor_property('sample_value',unreal.Vector(speed,0,0));sample.set_editor_property('rate_scale',1.)
        samples.append(sample)
    blend.set_editor_property('sample_data',samples)
    blend.set_editor_property('target_weight_interpolation_speed_per_sec',6.)
    if not unreal.PardeepAssetTools.rebuild_locomotion(blend):
        raise RuntimeError('Locomotion samples did not create usable runtime blend data')
    api.EAL.save_loaded_asset(blend,only_if_is_dirty=False)
    return blend.get_path_name()


blend=locomotion()
world=unreal.EditorLoadingAndSavingUtils.load_map(MAP if api.EAL.does_asset_exist(MAP) else '/Game/VillageMeshV3/Lvl_PandoriV3')
if not world:raise RuntimeError('V3 source map missing')
if not api.EAL.does_asset_exist(MAP):
    if not unreal.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Map copy failed')
    world=unreal.EditorLoadingAndSavingUtils.load_map(MAP)
removed=[]
for actor in api.EAS.get_all_level_actors():
    label=actor.get_actor_label()
    if (label.startswith('SM_GIS_') and label.endswith('_road')) or label.startswith(('V2_Road_','V2_Shoulder_','SM_Street_','StreetDetail_')):
        removed.append(label);api.EAS.destroy_actor(actor)
def copy_material(source,name):
    path=api.MAT+'/'+name
    return api.EAL.load_asset(path) if api.EAL.does_asset_exist(path) else api.EAL.duplicate_asset(source,path)
mats={
    'asphalt':copy_material('/Game/VillageMeshV2/Materials/M_PandoriRoad','M_StreetAsphalt'),
    'dirt':copy_material('/Game/VillageMeshV2/Materials/M_V2RoadsideSoil','M_StreetDirt'),
    'shoulder':copy_material('/Game/VillageMeshV2/Materials/M_V2RoadsideSoil','M_StreetShoulder'),
    'brick':paving('M_StreetBrick',(.22,.11),(.32,.13,.065)),
    'pavers':paving('M_StreetPavers',(.30,.15),(.39,.34,.26))}
if not all(mats.values()):raise RuntimeError('Street material dependency missing')
for item in PLAN['items']:
    path=Path(item['file'])
    if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:raise RuntimeError('Street geometry changed')
    mesh=api.import_file(path,item['name'],api.DEST+'/Streets/Geometry')
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    settings=mesh.get_editor_property('nanite_settings');settings.set_editor_property('enabled',True)
    settings.set_editor_property('fallback_target',unreal.NaniteFallbackTarget.RELATIVE_ERROR);settings.set_editor_property('fallback_relative_error',0.)
    mesh.set_editor_property('nanite_settings',settings);api.EAL.save_loaded_asset(mesh)
    actor=api.mesh_actor(mesh,mats[item['surface']],item['name'],(0,0,0),collide=True)
    actor.set_folder_path('Village/Streets')

# Small street furniture is placed only at clear road edges, never inside homes.
cube=api.EAL.load_asset('/Engine/BasicShapes/Cube');metal=api.solid('M_StreetMetal',(.055,.07,.07),.45)
solar=api.solid('M_StreetSolar',(.015,.04,.075),.3);cream=api.solid('M_StreetLamp',(.8,.70,.45),.5)
lights=[]
def box(label,mat,pos,size,yaw=0):
    actor=api.mesh_actor(cube,mat,label,pos,tuple(v/100 for v in size),yaw,True)
    actor.set_folder_path('Village/StreetFurniture');return actor
for road in PLAN['roads']:
    if road['surface'] not in ('brick','pavers'):continue
    for index,(a,b) in enumerate(road['segments_cm']):
        if index%9 or len(lights)>=45:continue
        dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
        if length<500:continue
        nx,ny=-dy/length,dx/length
        x,y=(a[0]+b[0])/2+nx*(road['width_cm']/2+90),(a[1]+b[1])/2+ny*(road['width_cm']/2+90)
        if not layout.clear_site(x,y,35):continue
        yaw=math.degrees(math.atan2(dy,dx));tag='StreetDetail_'+str(len(lights))
        box(tag+'_Pole',metal,(x,y,205),(12,12,410))
        box(tag+'_Solar',solar,(x,y,420),(110,65,6),yaw)
        box(tag+'_Lamp',cream,(x-nx*32,y-ny*32,380),(60,42,9),yaw)
        lights.append([x,y,380])
world.get_world_settings().set_editor_property('default_game_mode',unreal.PardeepVillageGameMode)
starts=[a for a in api.EAS.get_all_level_actors() if isinstance(a,unreal.PlayerStart)]
for start in starts:
    start.set_actor_location(unreal.Vector(3748,-18128,110),False,False)
    start.set_actor_rotation(unreal.Rotator(0,96,0),False)
if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level():raise RuntimeError('Map save failed')
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True)
report=dict(passed=True,map=MAP,roads=len(PLAN['roads']),surfaces=PLAN['counts'],chunks=len(PLAN['items']),
    removed_old_road_actors=len(removed),solar_street_lights=len(lights),locomotion=blend,
    appearance='User-approved temporary Manpreet visual in a replaceable player Blueprint; Pardeep likeness deferred',street_surface_assignment='authored; not ground surveyed')
(OUT/'build_report.json').write_text(json.dumps(report,indent=2)+'\n')
unreal.log('VILLAGE_STREETS_BUILT '+json.dumps(report))
