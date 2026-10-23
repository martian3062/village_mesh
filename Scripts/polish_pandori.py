"""Apply the last material/detail pass without reimporting the GIS geometry."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import unreal
import build_open_world as api
import pandori_layout as site
import decorate_pandori

world=unreal.EditorLoadingAndSavingUtils.load_map("/Game/VillageMesh/Lvl_PandoriNijjaran")
api.WEATHER_MPC=api.EAL.load_asset(api.DEST+"/MPC_Weather")
api.houses.MAT_DIR=api.MAT
bulb=api.houses.make_bulb_material()
earth=api.pbr("M_PandoriEarth","aerial_grass_rock")
road=api.pbr("M_PandoriRoad","asphalt_02")
api.pbr("M_Plaster","rough_plaster_03",True)
for actor in api.EAS.get_all_level_actors():
    label=actor.get_actor_label()
    if label.startswith("VM_Approx"):
        api.EAS.destroy_actor(actor)
    elif label.startswith("VM_Terrain"):
        actor.static_mesh_component.set_material(0,earth)
    elif label.startswith("VM_LampLens"):
        actor.static_mesh_component.set_material(0,bulb)
    elif label.startswith("SM_GIS_") and label.endswith("_road"):
        actor.static_mesh_component.set_material(0,road)
count=decorate_pandori.build(api,site)
for path in api.EAL.list_assets(api.MAT):
    material=api.EAL.load_asset(path)
    if isinstance(material,unreal.Material):
        api.finish(material)
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True)
unreal.log("VILLAGE_MESH_POLISH_OK details="+str(count))
