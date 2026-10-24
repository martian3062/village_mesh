"""Record saved skin resolution, topology and material controls for visual QA."""
import datetime
import json
from pathlib import Path
import unreal
root=Path(unreal.Paths.project_dir())
eal=unreal.EditorAssetLibrary;mel=unreal.MaterialEditingLibrary
meshes=unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
report={'recorded_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'meshes':{},'textures':{},'materials':{}}
for path in eal.list_assets('/Game/MetaHumanPilot/Pardeep/Assembled/Pardeep',recursive=True,include_folder=False):
    if not any(s in path for s in ('/Face/','/Body/')):continue
    asset=eal.load_asset(path)
    if isinstance(asset,unreal.SkeletalMesh):
        count=meshes.get_lod_count(asset)
        report['meshes'][path]={'lod_count':count,'vertices':[meshes.get_num_verts(asset,lod) for lod in range(count)],
                              'materials':[str(s.material_interface.get_path_name()) if s.material_interface else None for s in asset.get_editor_property('materials')]}
    if isinstance(asset,unreal.Texture2D) and '/Baked/' in path:
        report['textures'][path]={'width':asset.blueprint_get_size_x(),'height':asset.blueprint_get_size_y(),
                                  'virtual_texture':asset.get_editor_property('virtual_texture_streaming')}
    if isinstance(asset,unreal.MaterialInstanceConstant) and ('Skin' in path or 'MI_Body' in path):
        report['materials'][path]={
            'scalars':{str(n):mel.get_material_instance_scalar_parameter_value(asset,n) for n in mel.get_scalar_parameter_names(asset)},
            'switches':{str(n):mel.get_material_instance_static_switch_parameter_value(asset,n) for n in mel.get_static_switch_parameter_names(asset)}}
if len(report['meshes'])!=2 or not report['textures']:raise RuntimeError('Expected both face and body with baked texture assets')
report['passed']=True
report['scope']='Saved topology and texture resolution inventory; visual and runtime checks are separate'
(root/'Saved/PardeepPlayer/skin_asset_audit.json').write_text(json.dumps(report,indent=2)+'\n')
unreal.log('PARDEEP_SKIN_ASSETS_INSPECTED')
