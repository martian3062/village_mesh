"""Regenerate only V2 pilot details on its source map, preserving background geometry."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import unreal
import build_open_world as api
import v2_layout as site
import build_v2_pilot

api.DEST='/Game/VillageMeshV2'
api.MAT=api.DEST+'/Materials'
api.TMP=api.ROOT/'Saved/VillageMeshV2'
world=unreal.EditorLoadingAndSavingUtils.load_map(api.DEST+'/Lvl_PandoriV2')
if not world:raise RuntimeError('Build V2 source map before running its detail pass')
api.WEATHER_MPC=api.EAL.load_asset(api.DEST+'/MPC_Weather')
for actor in api.EAS.get_all_level_actors():
    if actor.get_actor_label().startswith('V2_'):
        api.EAS.destroy_actor(actor)
build_v2_pilot.build(api,site,world)
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True)
unreal.log('VILLAGE_V2_POLISH_OK')
