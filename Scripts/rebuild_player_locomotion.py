"""Rebuild and verify the serialized runtime blend data without rebuilding the map."""
import json
from pathlib import Path
import unreal
path='/Game/VillageMeshV3/Player/BS_PlayerLocomotion'
blend=unreal.load_asset(path)
if not blend or not unreal.PardeepAssetTools.rebuild_locomotion(blend):
    raise RuntimeError('Player locomotion runtime samples are invalid')
if not unreal.EditorAssetLibrary.save_loaded_asset(blend,only_if_is_dirty=False):
    raise RuntimeError('Could not save player locomotion')
out=Path(unreal.Paths.project_saved_dir())/'PardeepPlayer/locomotion_build.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(dict(passed=True,asset=path,validated_sample_speeds_cm_s=[0,180,420]),indent=2)+'\n')
unreal.log('PARDEEP_LOCOMOTION_RUNTIME_DATA_OK')
