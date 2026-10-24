import json
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
path='/Game/MetaHumanPilot/Pardeep/Characters/MH_Pardeep'
eal=unreal.EditorAssetLibrary
character=eal.load_asset(path) if eal.does_asset_exist(path) else eal.duplicate_asset('/Game/MetaHumanPilot/Characters/MH_Manpreet',path)
if not character: raise RuntimeError('Pardeep character copy failed')
sub=unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
if not sub.try_add_object_to_edit(character): raise RuntimeError('Could not edit separate Pardeep character')
try:
    points=sub.get_face_landmarks(character)
    report={'landmarks':[[p.x,p.y,p.z] for p in points], 'components':[]}
    (root/'Saved/PardeepPlayer/reference_landmarks.json').write_text(json.dumps(report,indent=2))
    eal.save_loaded_asset(character,only_if_is_dirty=False)
    actor=sub.spawn_meta_human_actor(character,True)
    for c in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        transform=c.get_socket_transform('head',unreal.RelativeTransformSpace.RTS_COMPONENT)
        report['components'].append({'name':c.get_name(),'mesh':str(c.skeletal_mesh_asset.get_path_name()) if c.skeletal_mesh_asset else None,'head':str(transform)})
    (root/'Saved/PardeepPlayer/reference_landmarks.json').write_text(json.dumps(report,indent=2))
    eal.save_loaded_asset(character,only_if_is_dirty=False)
    unreal.log('PARDEEP_REFERENCE_INSPECTED '+str(len(points)))
finally:
    sub.remove_object_to_edit(character)

import runpy
runpy.run_path(str(root/'Scripts/build_pardeep_turban.py'),run_name='__main__')
