"""Maintain the generated, stable runtime Blueprint for Pardeep."""
from pathlib import Path
import shutil
import unreal


def save_packages(root, only_dirty=True):
    count=unreal.PardeepAssetTools.save_loaded_pardeep_packages(root,only_dirty)
    if count<0:raise RuntimeError('Direct package save failed: '+root)
    if not only_dirty and count==0:raise RuntimeError('No loaded generated packages to save: '+root)
    return True


def finish_materials(report):
    eal=unreal.EditorAssetLibrary;mel=unreal.MaterialEditingLibrary
    assembly='/Game/MetaHumanPilot/Pardeep/Assembled'
    groom_materials=[];eye_materials=[];skin_materials=[]
    for path in eal.list_assets(assembly,recursive=True,include_folder=False):
        if '/Materials/' not in path:continue
        material=eal.load_asset(path)
        if not isinstance(material,unreal.MaterialInstanceConstant):continue
        names={str(n) for n in mel.get_scalar_parameter_names(material)}
        if 'hairMelanin' in names:
            for name,value in {'hairMelanin':.90,'hairRedness':.05,'HairRoughness':.38,'WhiteAmount':0.0,'LightAmount':0.0}.items():
                if name in names:mel.set_material_instance_scalar_parameter_value(material,name,value)
            groom_materials.append(path)
        if '/Pardeep/Face/Materials/MI_Eye' in path and '_Baked.' in path:
            switches={str(n) for n in mel.get_static_switch_parameter_names(material)}
            if not {'Use Baked Material','Use Custom Iris'}.issubset(switches):raise RuntimeError('Expected editable eye shader switches')
            # Baked iris textures bypass the colour parameters entirely.
            mel.set_material_instance_static_switch_parameter_value(material,'Use Baked Material',False)
            mel.set_material_instance_static_switch_parameter_value(material,'Use Custom Iris',False)
            for name,value in {'Iris Primary Color Value':.24,'Iris Secondary Color Value':.16,'Iris Global Saturation':1.3}.items():
                if name not in names:raise RuntimeError('Eye material parameter missing: '+name)
                mel.set_material_instance_scalar_parameter_value(material,name,value)
            mel.set_material_instance_vector_parameter_value(material,'Iris Color Multiply',unreal.LinearColor(.45,.26,.18,1))
            mel.update_material_instance(material)
            eye_materials.append(path)
        is_face='/Pardeep/Face/Materials/MI_Face_Skin_Baked_' in path
        is_body='/Pardeep/Body/Materials/MI_Body_Baked' in path
        if is_face or is_body:
            values={'Roughness Global Offset Post-Bake':.08 if is_face else .04,
                    'Specular Global Multiply Post-Bake':.85,
                    'Micro Skin Normal Strength':.8 if is_face else .85,
                    'Normal Global Strength Post-Bake':1.0 if is_face else 1.05}
            for name,value in values.items():
                if name in names:mel.set_material_instance_scalar_parameter_value(material,name,value)
            mel.update_material_instance(material)
            skin_materials.append(path)
    if len(eye_materials)!=2:raise RuntimeError('Expected both assembled eye materials')
    save_packages(assembly,True)
    report.update(dark_groom_materials=groom_materials,dark_brown_eye_materials=eye_materials,skin_roughness_materials=skin_materials)


def refresh_runtime_actor(report):
    root=Path(unreal.Paths.project_dir());eal=unreal.EditorAssetLibrary
    assembly='/Game/MetaHumanPilot/Pardeep/Assembled'
    stable_actor=assembly+'/BP_Pardeep'
    sources=[p.split('.')[0] for p in report['assembled_blueprints'] if p.split('.')[0]!=stable_actor]
    if len(sources)!=1 or not sources[0].startswith(assembly+'/') or not sources[0].endswith('/BP_Pardeep'):
        raise RuntimeError('Expected one generated Pardeep source actor')
    if eal.does_asset_exist(stable_actor):
        previous=root/'Content'/(stable_actor.removeprefix('/Game/')+'.uasset')
        backup=root/'Saved/PardeepPlayer/previous_pardeep_blueprint.uasset'
        backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(previous,backup)
        if not eal.delete_asset(stable_actor):raise RuntimeError('Could not refresh generated player alias')
    actor_blueprint=eal.duplicate_asset(sources[0],stable_actor)
    if not actor_blueprint or not unreal.BlueprintEditorLibrary.compile_blueprint(actor_blueprint):
        raise RuntimeError('Player alias compile failed')
    save_packages(stable_actor,False)
    report['runtime_blueprint']=stable_actor
