"""V2-only fallback rain material: fade shell edges and remove cylinder caps.

This remains an inexpensive moving shell, not volumetric or collision rain.
"""
import sys
from pathlib import Path
import unreal


def build(api):
    if api.MAT!='/Game/VillageMeshV2/Materials':
        raise ValueError('Rain refinement is scoped to V2')
    mat=api.create('M_VGRainStreaks',unreal.Material,unreal.MaterialFactoryNew())
    api.MEL.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided',True)
    inputs=[]
    for name in ('P','O','N','Time','Amount'):
        item=unreal.CustomInput()
        item.set_editor_property('input_name',name)
        inputs.append(item)
    mask=api.expr(mat,unreal.MaterialExpressionCustom,
        inputs=inputs,
        code='''
float2 cell=floor(P.xy*.07);
float seed=frac(sin(dot(cell,float2(12.9898,78.233)))*43758.5453);
float stripe=pow(abs(sin(dot(P.xy,float2(.17,.13)))),32.0);
float drop=pow(1.0-frac(P.z*.027+Time*12.0+seed),14.0);
float edge=saturate((1100.0-abs(P.z-O.z))/350.0);
float side=1.0-saturate(abs(N.z));
return stripe*drop*edge*side*Amount*.32;
''')
    api.link(api.expr(mat,unreal.MaterialExpressionWorldPosition),mask,'P')
    api.link(api.expr(mat,unreal.MaterialExpressionObjectPositionWS),mask,'O')
    api.link(api.expr(mat,unreal.MaterialExpressionPixelNormalWS),mask,'N')
    api.link(api.expr(mat,unreal.MaterialExpressionTime),mask,'Time')
    api.link(api.expr(mat,unreal.MaterialExpressionScalarParameter,
        parameter_name='RainAmount',default_value=.6),mask,'Amount')
    api.MEL.connect_material_property(mask,'',unreal.MaterialProperty.MP_OPACITY)
    tint=api.expr(mat,unreal.MaterialExpressionConstant3Vector,constant=unreal.LinearColor(.5,.6,.7,1))
    api.MEL.connect_material_property(tint,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    return api.finish(mat)


if __name__=='__main__':
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    import build_open_world as api
    api.MAT='/Game/VillageMeshV2/Materials'
    build(api)
    unreal.log('VILLAGE_V2_RAIN_REFINED_OK')
