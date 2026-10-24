"""Import the original turban and create its black cotton material."""
import json
import sys
from pathlib import Path
import unreal

ROOT=Path(unreal.Paths.project_dir());sys.path.insert(0,str(ROOT/'Scripts'))
import build_open_world as api
import pardeep_turban
api.MAT='/Game/VillageMeshV3/Player/Headwear'
path=pardeep_turban.generate()
mat=api.create('M_PardeepBlackCotton',unreal.Material,unreal.MaterialFactoryNew())
api.MEL.delete_all_material_expressions(mat)
uv=api.expr(mat,unreal.MaterialExpressionTextureCoordinate)
input_uv=unreal.CustomInput();input_uv.set_editor_property('input_name','UV')
color=api.expr(mat,unreal.MaterialExpressionCustom,
    code='float weave=sin(UV.x*2513)*sin(UV.y*1885); return float3(.006,.005,.004)*(1+weave*.10);',
    output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT3,inputs=[input_uv])
api.link(uv,color,'UV');api.MEL.connect_material_property(color,'',unreal.MaterialProperty.MP_BASE_COLOR)
api.MEL.connect_material_property(api.scalar(mat,.92),'',unreal.MaterialProperty.MP_ROUGHNESS)
api.MEL.connect_material_property(api.scalar(mat,.12),'',unreal.MaterialProperty.MP_SPECULAR)
api.finish(mat)
mesh=api.import_file(path,'SM_PardeepTurban',api.MAT)
mesh.set_material(0,mat)
api.EAL.save_loaded_asset(mesh,only_if_is_dirty=False)
(ROOT/'Saved/PardeepPlayer/turban_build.json').write_text(json.dumps({'passed':True,'mesh':mesh.get_path_name(),'material':mat.get_path_name(),'origin':'Original procedural folded cloth; black colour guided by owner-selected references'},indent=2)+'\n')
unreal.log('PARDEEP_TURBAN_BUILT')
