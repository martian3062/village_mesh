"""Import the audited policy and original parameterized prototype materials."""
from pathlib import Path
import json,sys
import unreal
ROOT=Path(unreal.Paths.project_dir())
sys.path.insert(0,str(ROOT/'Scripts'))
import build_open_world as api
api.DEST='/Game/VillageMeshV25';api.MAT=api.DEST+'/Materials'
api.EAL.make_directory(api.MAT)
mat=api.create('M_V25Color',unreal.Material,unreal.MaterialFactoryNew())
api.MEL.delete_all_material_expressions(mat)
color=api.expr(mat,unreal.MaterialExpressionVectorParameter,parameter_name='Color',default_value=unreal.LinearColor(.3,.3,.3,1))
api.MEL.connect_material_property(color,'',unreal.MaterialProperty.MP_BASE_COLOR)
api.MEL.connect_material_property(api.scalar(mat,.85),'',unreal.MaterialProperty.MP_ROUGHNESS)
api.finish(mat)
task=unreal.AssetImportTask();task.filename=str(ROOT/'Assets/Models/npc_policy_v1.onnx')
task.destination_path=api.DEST+'/Models';task.destination_name='npc_policy_v1';task.automated=True;task.replace_existing=True;task.save=True
api.TOOLS.import_asset_tasks([task])
model=api.EAL.load_asset(api.DEST+'/Models/npc_policy_v1')
if not model:raise RuntimeError('NNE model import did not create an asset')
if hasattr(model,'set_target_runtimes'):model.set_target_runtimes(['NNERuntimeORTCpu'])
api.EAL.save_loaded_asset(model)
unreal.log('V25_ASSETS_OK '+str(task.imported_object_paths))
