"""Derive V3 from the V2 source map without mutating V2 assets or its pilot."""
from pathlib import Path
import sys,json,hashlib
import unreal
ROOT=Path(unreal.Paths.project_dir());sys.path.insert(0,str(ROOT/'Scripts'))
import build_open_world as api
from v3_layout import COLORS
api.DEST='/Game/VillageMeshV3';api.MAT=api.DEST+'/Materials';api.TMP=ROOT/'Saved/VillageMeshV3'
api.TMP.mkdir(parents=True,exist_ok=True)
map_path=api.DEST+'/Lvl_PandoriV3'
if not api.EAL.does_asset_exist(map_path):
    source=unreal.EditorLoadingAndSavingUtils.load_map('/Game/VillageMeshV2/Lvl_PandoriV2')
    if not source:raise RuntimeError('V2 source map required: run V2 Build first')
    if not unreal.EditorLoadingAndSavingUtils.save_map(source,map_path):raise RuntimeError('Could not create V3 map copy')
# Save-as can leave the caller's UWorld pointing to the source. Reload the
# destination explicitly, then save the current level rather than another Save As.
world=unreal.EditorLoadingAndSavingUtils.load_map(map_path)
if not world:raise RuntimeError('Could not load the V3 destination map')
for actor in api.EAS.get_all_level_actors():
    label=actor.get_actor_label()
    if (label.startswith('SM_GIS_') and not label.endswith('_road')) or label.startswith('SM_V3_'):api.EAS.destroy_actor(actor)
import polish_v3
cleared_vegetation=polish_v3.polish(world)
api.WEATHER_MPC=api.EAL.load_asset('/Game/VillageMeshV2/MPC_Weather')
parent=api.pbr('M_V3Paint','rough_plaster_03',True)
node=api.MEL.get_material_property_input_node(parent,unreal.MaterialProperty.MP_BASE_COLOR)
blend=api.expr(parent,unreal.MaterialExpressionLinearInterpolate)
api.link(node,blend,'A')
api.link(api.expr(parent,unreal.MaterialExpressionVectorParameter,parameter_name='Paint',default_value=unreal.LinearColor(.7,.6,.5,1)),blend,'B')
api.link(api.scalar(parent,.87),blend,'Alpha');api.MEL.connect_material_property(blend,'',unreal.MaterialProperty.MP_BASE_COLOR)
normal=api.MEL.get_material_property_input_node(parent,unreal.MaterialProperty.MP_NORMAL)
flat=api.expr(parent,unreal.MaterialExpressionLinearInterpolate);api.link(normal,flat,'A','RGB')
api.link(api.expr(parent,unreal.MaterialExpressionConstant3Vector,constant=unreal.LinearColor(0,0,1,1)),flat,'B')
api.link(api.scalar(parent,.86),flat,'Alpha');api.MEL.connect_material_property(flat,'',unreal.MaterialProperty.MP_NORMAL);api.finish(parent)
mats={}
for i,c in enumerate(COLORS):
    m=api.create('MI_Paint'+str(i),unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
    api.MEL.set_material_instance_parent(m,parent)
    api.MEL.set_material_instance_vector_parameter_value(m,'Paint',unreal.LinearColor(*c,1))
    api.EAL.save_loaded_asset(m);mats['paint'+str(i)]=m
for key,name in [('brick','M_Brick'),('roof','M_Roof'),('glass','M_GISGlass')]:
    mats[key]=api.EAL.load_asset('/Game/VillageMeshV2/Materials/'+name)
for key,c in dict(cream=(.78,.74,.62),ochre=(.52,.33,.12),concrete=(.40,.39,.34),
    wood=(.19,.10,.045),metal=(.10,.14,.15),tank=(.035,.04,.045),terracotta=(.48,.21,.12),
    solar=(.025,.07,.12),teal=(.07,.25,.23),saffron=(.95,.36,.035),paving=(.53,.48,.38),
    straw=(.44,.34,.12),soil=(.20,.14,.075),soil_light=(.31,.22,.11),water=(.075,.18,.15),
    leaves=(.17,.26,.055),crop=(.14,.30,.08)).items():mats[key]=api.solid('M_V3_'+key,c,.38 if key in ('metal','water','solar') else .85)
mats['saffron'].set_editor_property('two_sided',True);api.finish(mats['saffron'])
plan=json.loads((ROOT/'Assets/World/v3_world.json').read_text(encoding='utf-8'))
# Generate OBJ files in external Python first, so its transient geometry memory
# is released before Unreal loads the world and builds Nanite/distance fields.
manifest=json.loads((api.TMP/'geometry_manifest.json').read_text())
if manifest['plan_sha256']!=hashlib.sha256((ROOT/'Assets/World/v3_world.json').read_bytes()).hexdigest() or manifest['generator_sha256']!=hashlib.sha256((ROOT/'Scripts/v3_geometry.py').read_bytes()).hexdigest():
    raise RuntimeError('Geometry manifest is stale; run python Scripts/v3_geometry.py')
items=manifest['items']
previous_path=api.TMP/'build_report.json'
previous=json.loads(previous_path.read_text()) if previous_path.exists() else {}
previous_hashes={p['name']:p.get('sha256') for p in previous.get('items',[])}
force='-V3ForceReimport' in unreal.SystemLibrary.get_command_line();reused=0
for i,item in enumerate(items):
    if hashlib.sha256(Path(item['file']).read_bytes()).hexdigest()!=item['sha256']:raise RuntimeError('Geometry file differs from manifest')
    asset_path=api.DEST+'/Geometry/'+item['name']
    if not force and previous_hashes.get(item['name'])==item['sha256'] and api.EAL.does_asset_exist(asset_path):
        mesh=api.EAL.load_asset(asset_path);reused+=1
    else:
        mesh=api.import_file(item['file'],item['name'],api.DEST+'/Geometry')
        mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        settings=mesh.get_editor_property('nanite_settings');settings.set_editor_property('enabled',True)
        settings.set_editor_property('fallback_target',unreal.NaniteFallbackTarget.RELATIVE_ERROR);settings.set_editor_property('fallback_relative_error',0.0)
        mesh.set_editor_property('nanite_settings',settings);api.EAL.save_loaded_asset(mesh)
    actor=api.mesh_actor(mesh,mats[item['material']],item['name'],(0,0,0),collide=item['collision'])
    actor.set_folder_path('V3/FullVillage')
    if i%40==0:unreal.log('V3_IMPORT '+str(i)+'/'+str(len(items)))
atlas=api.import_file(ROOT/'Assets/World/v3_map.png','T_VillageAtlas',api.DEST+'/UI')
atlas.set_editor_property('srgb',True)
atlas.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_EDITOR_ICON)
atlas.set_editor_property('mip_gen_settings',unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
api.EAL.save_loaded_asset(atlas)
# package_v3 explicitly cooks this namespace, including the dynamically loaded atlas.
world.get_world_settings().set_editor_property('default_game_mode',unreal.VillageAtlasGameMode)
if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level():raise RuntimeError('V3 save failed')
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True)
report=dict(**plan['counts'],mesh_chunks=len(items),triangles=sum(i['triangles'] for i in items),
            source_map='/Game/VillageMeshV2/Lvl_PandoriV2',map='/Game/VillageMeshV3/Lvl_PandoriV3',
            geometry='Original procedural interpretation; representative public sites',cleared_vegetation_points=cleared_vegetation,reused_meshes=reused,items=items)
(api.TMP/'build_report.json').write_text(json.dumps(report,indent=2))
unreal.log('V3_BUILD_OK '+str(len(items))+' mesh chunks')
