"""Clear inherited vegetation from authored public sites/fields in V3-only graph copies."""
import json,sys
from pathlib import Path
import unreal
ROOT=Path(unreal.Paths.project_dir());sys.path.insert(0,str(ROOT/'Scripts'))

def polish(world):
    eal=unreal.EditorAssetLibrary;eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    plan=json.loads((ROOT/'Assets/World/v3_world.json').read_text())
    areas=[]
    for p in plan['landmarks']+plan['fields']:
        x,y,_=p['center_cm'];w,d=p['size_cm'];areas.append((x-w/2-500,y-d/2-500,x+w/2+500,y+d/2+500))
    count=0;graphs={}
    for actor in eas.get_all_level_actors():
        comp=actor.get_component_by_class(unreal.PCGComponent)
        if not comp:continue
        original=comp.get_graph()
        if not original:continue
        name=original.get_name();dest='/Game/VillageMeshV3/PCG/'+name
        if name not in graphs:
            graph=eal.load_asset(dest) if eal.does_asset_exist(dest) else eal.duplicate_asset(original.get_path_name().split('.')[0],dest)
            if not graph:raise RuntimeError('Could not create V3 PCG graph copy')
            baseline=eal.load_asset('/Game/VillageMeshV2/PCG/'+name)
            baseline_nodes=list(baseline.get_editor_property('nodes')) if baseline else []
            for index,node in enumerate(graph.get_editor_property('nodes')):
                settings=node.get_settings()
                if not isinstance(settings,unreal.PCGCreatePointsSettings):continue
                if not settings.get_path_name().startswith('/Game/VillageMeshV3/'):
                    raise RuntimeError('Refusing to mutate a shared source PCG settings object')
                source_settings=baseline_nodes[index].get_settings() if index<len(baseline_nodes) else settings
                points=source_settings.get_editor_property('points_to_create');kept=[]
                for p in points:
                    q=p.get_editor_property('transform').translation
                    if any(a<q.x<c and b<q.y<d for a,b,c,d in areas):count+=1
                    else:kept.append(p)
                settings.set_editor_property('points_to_create',kept)
            eal.save_loaded_asset(graph);graphs[name]=graph
        comp.cleanup(True);comp.set_graph(graphs[name]);comp.set_editor_property('generation_trigger',unreal.PCGComponentGenerationTrigger.GENERATE_ON_LOAD)
    flag=eal.load_asset('/Game/VillageMeshV3/Materials/M_V3_saffron')
    if flag:
        flag.set_editor_property('two_sided',True);unreal.MaterialEditingLibrary.recompile_material(flag);eal.save_loaded_asset(flag)
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True)
    unreal.log('V3_CLEARANCE_OK removed_vegetation_points='+str(count)+' graphs='+str(len(graphs)))
    return count

if __name__=='__main__':
    for name in ('Lvl_PandoriV3','Lvl_PandoriV3_WP'):
        if name.endswith('_WP') and not unreal.EditorAssetLibrary.does_asset_exist('/Game/VillageMeshV3/'+name):continue
        world=unreal.EditorLoadingAndSavingUtils.load_map('/Game/VillageMeshV3/'+name)
        if not world:raise RuntimeError('Missing V3 map '+name)
        polish(world)
