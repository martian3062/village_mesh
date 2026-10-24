"""Build a separate, reference-guided Pardeep; source portraits stay local.

Run in a normal editor through build_pardeep_character_editor.py because
MetaHuman assembly requires Texture Graph initialization.
"""
import datetime
import hashlib
import json
import math
import runpy
from pathlib import Path
import sys
import time
import unreal

ROOT=Path(unreal.Paths.project_dir());sys.path.insert(0,str(ROOT/'Scripts'))
from metahuman_assembly_validation import validate_assembly
from pardeep_character_finish import refresh_runtime_actor, save_packages, finish_materials
EAL=unreal.EditorAssetLibrary
OUT=ROOT/'Saved/PardeepPlayer';OUT.mkdir(parents=True,exist_ok=True)
CHARACTER='/Game/MetaHumanPilot/Pardeep/Characters/MH_Pardeep'
ASSEMBLY='/Game/MetaHumanPilot/Pardeep/Assembled'
report={'passed':False,'started_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'character_asset':CHARACTER,'appearance':'Reference-guided artistic approximation; owner likeness review required',
        'source_photos_copied':False,'source_photos_uploaded':False}

def save_report():
    (OUT/'character_build.json').write_text(json.dumps(report,indent=2)+'\n')

sub=unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
character=EAL.load_asset(CHARACTER)
if not character:raise RuntimeError('Inspect and save the separate Pardeep character first')
try:
    save_report()
    runpy.run_path(str(ROOT/'Scripts/build_pardeep_turban.py'),run_name='__main__')
    if not sub.try_add_object_to_edit(character):raise RuntimeError('Could not open separate Pardeep for editing')
    design_bytes=(ROOT/'Assets/MetaHumans/pardeep_face_design.json').read_bytes()
    design=json.loads(design_bytes);design_hash=hashlib.sha256(design_bytes).hexdigest()
    stored_hash=EAL.get_metadata_tag(character,'VillageFaceDesign')
    if stored_hash and stored_hash!=design_hash:raise RuntimeError('Design changed; create a reviewed baseline before applying new face deltas')
    if not stored_hash:
        before=sub.get_face_landmarks(character)
        if len(before)!=design['landmark_count']:raise RuntimeError('MetaHuman landmark layout changed')
        sub.remove_face_rig(character)
        changes=design['landmark_deltas_cm']
        sub.translate_face_landmarks(character,[c['index'] for c in changes],[unreal.Vector(*c['delta']) for c in changes])
        sub.commit_face_state(character)
        after=sub.get_face_landmarks(character)
        movement=sum(math.dist((a.x,a.y,a.z),(b.x,b.y,b.z)) for a,b in zip(after,before))
        if movement<.05:raise RuntimeError('Face edits did not change the character')
        report['landmark_total_change_cm']=movement
        EAL.set_metadata_tag(character,'VillageFaceDesign',design_hash)
    else:
        report['face_sculpt_reused']=True
    report['applied_design']=design
    save_packages(CHARACTER,False)
    report['stage']='face_sculpt_saved';save_report()
    request=unreal.MetaHumanCharacterAutoRiggingRequestParams()
    request.blocking=True;request.report_progress=False
    request.rig_type=unreal.MetaHumanRigType.JOINTS_AND_BLEND_SHAPES
    if not character.get_editor_property('has_face_dna_blendshapes'):sub.request_auto_rigging(character,request)
    if not character.get_editor_property('has_face_dna_blendshapes'):raise RuntimeError('Pardeep face rigging failed')
    save_packages(CHARACTER,False)
    report['stage']='face_rig_saved';save_report()
    if not character.get_editor_property('has_high_resolution_textures'):
        textures=unreal.MetaHumanCharacterTextureRequestParams()
        textures.blocking=True;textures.report_progress=False
        sub.request_texture_sources(character,textures)
        if not character.get_editor_property('has_high_resolution_textures'):raise RuntimeError('Pardeep high-resolution texture sources were not available')
        save_packages(CHARACTER,False)
    params=unreal.MetaHumanCharacterEditorBuildParameters()
    params.pipeline_type=unreal.MetaHumanDefaultPipelineType.OPTIMIZED
    params.pipeline_quality=unreal.MetaHumanQualityLevel.HIGH
    params.absolute_build_path=ASSEMBLY;params.name_override='Pardeep'
    params.common_folder_path=ASSEMBLY+'/Common';params.enable_wardrobe_item_validation=True
    started=time.time();log=ROOT/'Saved/Logs/PardeepCharacterBuild.log'
    unreal.log_flush();offset=log.stat().st_size
    try:
        sub.build_meta_human(character,params)
    except RuntimeError as exc:
        # Only the known engine 5.8 passthrough-reroute migration diagnostics
        # are repaired, using the same verified procedure as the original pilot.
        expected={'CR_MetaHuman_HeadMovement_IK_Proc':['Multiply.Result.Z -> RerouteNode_1.Value','RerouteNode_1.Value -> Add.C'],
                  'Face_ControlBoard_CtrlRig':['MathFloatAdd_6_1.Result -> RerouteNode_19_1.Value','RerouteNode_19_1.Value -> SetControlVector2D_1_1.Vector.X']}
        allowed={f'MetaHumanCharacterEditorSubsystem: {params.common_folder_path}/Face/{name} : Cannot break link {edge} in package {params.common_folder_path}/Face/{name}' for name,edges in expected.items() for edge in edges}
        diagnostics=[line.strip().removeprefix('RuntimeError: ') for line in str(exc).splitlines() if line.strip()]
        if not diagnostics or not set(diagnostics).issubset(allowed):raise
        report['control_rig_migration_diagnostics']=diagnostics
    unreal.log_flush()
    with log.open('rb') as stream:stream.seek(offset);build_log=stream.read().decode('utf-8',errors='replace')
    if 'MetaHuman Character assembly succeeded' not in build_log:raise RuntimeError('No successful assembly reported by this run')
    report['engine_assembly_succeeded']=True;report['stage']='saving_assembled_packages';save_report()
    save_packages(ASSEMBLY,False)
    report['generated_assets_saved']=True;save_report()
    validate_assembly({'assembly_root':ASSEMBLY,'name':'Pardeep','quality':'High'},report,started,save_packages=save_packages)
    # Keep a stable runtime slot even though Epic's assembler nests its actor
    # inside a name-specific folder. Only this generated alias is replaced.
    refresh_runtime_actor(report)
    finish_materials(report)
    save_packages(CHARACTER,False)
    report['stage']='complete';report['passed']=True;save_report()
    unreal.log('PARDEEP_CHARACTER_BUILT')
except Exception as exc:
    report['stage']='failed';report['error']=str(exc);save_report();raise
finally:
    if sub.is_object_added_for_editing(character):sub.remove_object_to_edit(character)
