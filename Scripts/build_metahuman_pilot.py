"""Original, staged UE 5.8 orchestration. Epic content remains local and separately licensed."""
import datetime
import hashlib
import json
import re
import sys
import time
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.project_dir())
sys.path.insert(0, str(ROOT / 'Scripts'))
from metahuman_pilot_config import read_profile, PROFILE
from metahuman_assembly_validation import validate_assembly

PROFILE_DATA = read_profile()
OUTPUT = ROOT / 'Saved/MetaHumanPilot'
OUTPUT.mkdir(parents=True, exist_ok=True)
EAL = unreal.EditorAssetLibrary
match = re.search(r'-MHPilotAction=(\w+)', unreal.SystemLibrary.get_command_line())
ACTION = match.group(1) if match else 'Inspect'
REPORT = {'action': ACTION, 'passed': False, 'status': 'running',
          'started_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'profile_sha256': hashlib.sha256(PROFILE.read_bytes()).hexdigest(),
          'character_asset': PROFILE_DATA['character_asset']}


def save_report():
    (OUTPUT / (ACTION.lower() + '.json')).write_text(json.dumps(REPORT, indent=2) + '\n')
    if ACTION == 'ValidateAssembly' and REPORT['status'] == 'complete':
        assembled = dict(REPORT, action='Assemble')
        (OUTPUT / 'assemble.json').write_text(json.dumps(assembled, indent=2) + '\n')


def require_core_data():
    folder = Path(unreal.Paths.engine_plugins_dir()) / 'MetaHuman/MetaHumanCharacter/Content/Optional'
    if not folder.exists() or not any(folder.rglob('WI_*.uasset')):
        raise RuntimeError('MetaHuman Creator Core Data is missing. Install it through the UE 5.8 Options menu before this stage.')


def save_character(character):
    # Nested collection mutations do not always dirty the character package.
    if not EAL.save_loaded_asset(character, only_if_is_dirty=False):
        raise RuntimeError('Unreal could not save the pilot character')


def main():
    path = PROFILE_DATA['character_asset']
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem:
        raise RuntimeError('MetaHumanCharacterEditorSubsystem is unavailable')
    character = EAL.load_asset(path) if EAL.does_asset_exist(path) else None
    if ACTION == 'Create':
        REPORT['reused_existing_asset'] = character is not None
        if not character:
            parent, name = path.rsplit('/', 1)
            character = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                name, parent, unreal.MetaHumanCharacter,
                unreal.new_object(unreal.MetaHumanCharacterFactoryNew))
        if not character:
            raise RuntimeError('Character asset creation failed')
        save_character(character)
        REPORT['asset_created_or_reused'] = True
        REPORT['scope'] = 'Base character asset only; not a styled, rigged or assembled villager'
        return
    if ACTION == 'Inspect':
        REPORT['character_exists'] = character is not None
        registry = unreal.AssetRegistryHelpers.get_asset_registry()
        registry.scan_paths_synchronous(['/MetaHumanCharacter/Optional'], force_rescan=True)
        items = registry.get_assets_by_path('/MetaHumanCharacter/Optional', recursive=True)
        REPORT['wardrobe_items'] = sorted(str(a.package_name) for a in items if str(a.asset_name).startswith('WI_'))
        # CanBuildMetaHuman requires edit-state data. Inventory runs with NullRHI and
        # must not open Creator or turn an expected unrigged state into a logged error.
        REPORT['can_assemble'] = None
        REPORT['assembly_readiness'] = 'Deferred to the Assemble stage with character data loaded'
        if character:
            REPORT['slot_names'] = [str(s) for s in unreal.MetaHumanCollectionBlueprintLibrary.get_slot_names(character.internal_collection)]
            REPORT['face_blendshape_rig_present'] = bool(character.get_editor_property('has_face_dna_blendshapes'))
            REPORT['high_resolution_textures_present'] = bool(character.get_editor_property('has_high_resolution_textures'))
            REPORT['saved_selections'] = {
                str(d.selection.slot_name): d.selection.selected_item.export_text()
                for d in character.internal_collection.default_instance.get_slot_selection_data()}
            REPORT['saved_wardrobe_matches_profile'] = bool(PROFILE_DATA['wardrobe']) and all(
                p and ('Asset="' + p + '.' + p.rsplit('/', 1)[-1] + '"') in REPORT['saved_selections'].get(s, '')
                for s, p in PROFILE_DATA['wardrobe'].items())
        REPORT['scope'] = 'API and asset inventory; does not certify the character appearance or performance'
        return
    if not character:
        raise RuntimeError('Create the pilot character first')
    require_core_data()
    if ACTION == 'ValidateAssembly':
        previous = json.loads((OUTPUT / 'assemble.json').read_text())
        if not previous.get('engine_assembly_succeeded') or not previous.get('generated_assets_saved') or previous.get('profile_sha256') != REPORT['profile_sha256']:
            raise RuntimeError('Saved assembly recovery requires a completed engine build for the current profile')
        original_start = previous.get('source_assembly_started_at_utc', previous['started_at_utc'])
        REPORT['source_assembly_started_at_utc'] = original_start
        for key in ('engine_assembly_succeeded', 'generated_assets_saved', 'control_rig_migration_diagnostics', 'restored_control_rig_links'):
            if key in previous:
                REPORT[key] = previous[key]
        validate_assembly(PROFILE_DATA, REPORT, datetime.datetime.fromisoformat(original_start).timestamp())
        return
    if ACTION == 'Edit':
        unreal.EditorPythonScripting.set_keep_python_script_alive(True)
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([character])
        REPORT['scope'] = 'Creator editor opened; appearance and cloud authentication require review'
        return
    if ACTION == 'Wardrobe':
        missing = [s for s in PROFILE_DATA['required_wardrobe_slots'] if not PROFILE_DATA['wardrobe'].get(s)]
        if missing:
            raise RuntimeError('Select installed wardrobe paths in Assets/MetaHumans/manpreet.json for: ' + ', '.join(missing))
        # Newly installed plugin content is not scanned automatically by commandlets.
        unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(
            ['/MetaHumanCharacter/Optional'], force_rescan=True)
        wardrobe = {s: EAL.load_asset(p) for s, p in PROFILE_DATA['wardrobe'].items() if p}
        missing = [s for s, item in wardrobe.items() if not item]
        if missing:
            raise RuntimeError('Selected wardrobe assets could not be loaded for: ' + ', '.join(missing))
        instance = character.internal_collection.default_instance
        for slot, item in wardrobe.items():
            key = character.internal_collection.try_add_item_from_wardrobe_item(slot, item)
            if key is None:
                raise RuntimeError('Creator rejected the wardrobe item for slot: ' + slot)
            instance.set_single_slot_selection(slot, key)
            selections = [d.selection for d in instance.get_slot_selection_data() if str(d.selection.slot_name) == slot]
            if len(selections) != 1 or selections[0].selected_item.export_text() != key.export_text():
                REPORT['selection_debug'] = {'slot': slot, 'requested': key.export_text(),
                    'actual': [s.selected_item.export_text() for s in selections]}
                raise RuntimeError('Wardrobe selection did not persist for slot: ' + slot)
        # Match Epic's examples: select items before opening the preview edit state.
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError('Creator could not open the pilot for editing. Check Core Data and close any existing character editor.')
    try:
        if ACTION == 'Style':
            # Editing a face/body can invalidate a rig. Never silently remove an existing rig.
            if character.get_editor_property('has_face_dna_blendshapes') or subsystem.can_build_meta_human(character, False):
                raise RuntimeError('This pilot is already rigged. Edit intentionally in Creator instead of overwriting it with Style.')
            constraints = list(subsystem.get_body_constraints(character))
            height = next((c for c in constraints if str(c.name).lower().replace(' ', '_') == 'height'), None)
            if height is None:
                raise RuntimeError('Creator did not expose a height constraint')
            height.is_active = True
            height.target_measurement = PROFILE_DATA['height_cm']
            subsystem.set_body_constraints(character, constraints)
            subsystem.commit_body_state(character)
            REPORT['height_target_cm'] = PROFILE_DATA['height_cm']
            skin = character.get_editor_property('skin_settings')
            props = skin.skin
            props.u = PROFILE_DATA['skin']['u']
            props.v = PROFILE_DATA['skin']['v']
            props.roughness = PROFILE_DATA['skin']['roughness']
            props.show_top_underwear = True
            skin.skin = props
            subsystem.commit_skin_settings(character, skin)
            REPORT['scope'] = 'Body/skin design applied; a rendered appearance review is still required'
        elif ACTION == 'Wardrobe':
            subsystem.assemble_for_preview(character)
            REPORT['wardrobe'] = PROFILE_DATA['wardrobe']
            REPORT['scope'] = 'Wardrobe selections applied; fitting and intersections still require visual review'
        elif ACTION == 'Rig':
            request = unreal.MetaHumanCharacterAutoRiggingRequestParams()
            request.blocking = True
            request.report_progress = False
            # Blendshape state provides an observable success condition in the Python API.
            request.rig_type = unreal.MetaHumanRigType.JOINTS_AND_BLEND_SHAPES
            subsystem.request_auto_rigging(character, request)
            if not character.get_editor_property('has_face_dna_blendshapes'):
                raise RuntimeError('Cloud rigging did not produce a blendshape rig. Check Epic sign-in and the Unreal log.')
            REPORT['face_blendshape_rig_present'] = True
        elif ACTION == 'Textures':
            request = unreal.MetaHumanCharacterTextureRequestParams()
            request.blocking = True
            request.report_progress = False
            subsystem.request_texture_sources(character, request)
            if not character.get_editor_property('has_high_resolution_textures'):
                raise RuntimeError('Cloud texture synthesis did not complete. Check Epic sign-in and the Unreal log.')
            REPORT['high_resolution_textures_present'] = True
        elif ACTION == 'Assemble':
            if not subsystem.can_build_meta_human(character, True):
                raise RuntimeError('Creator reports that this character is not ready for assembly')
            if not character.get_editor_property('has_high_resolution_textures'):
                raise RuntimeError('Finish the Textures stage before assembling the reviewed pilot')
            wardrobe_report = OUTPUT / 'wardrobe.json'
            if not wardrobe_report.exists():
                raise RuntimeError('Run and review the Wardrobe stage before assembly')
            earlier = json.loads(wardrobe_report.read_text())
            if not earlier.get('passed') or earlier.get('profile_sha256') != REPORT['profile_sha256']:
                raise RuntimeError('The wardrobe report is failed or belongs to an older profile')
            params = unreal.MetaHumanCharacterEditorBuildParameters()
            params.pipeline_type = unreal.MetaHumanDefaultPipelineType.OPTIMIZED
            params.pipeline_quality = unreal.MetaHumanQualityLevel.MEDIUM
            params.absolute_build_path = PROFILE_DATA['assembly_root']
            params.name_override = PROFILE_DATA['name']
            params.common_folder_path = PROFILE_DATA['assembly_root'] + '/Common'
            params.enable_wardrobe_item_validation = True
            build_started = time.time()
            assembly_log = ROOT / 'Saved/Logs/MetaHumanPilot_Assemble.log'
            unreal.log_flush()
            log_offset = assembly_log.stat().st_size
            try:
                subsystem.build_meta_human(character, params)
            except RuntimeError as exc:
                # UE 5.8.4 can return these four legacy reroute diagnostics even
                # after reporting assembly success. Accept only these exact
                # messages, then verify the replacement graph links and compile.
                known = {
                    'CR_MetaHuman_HeadMovement_IK_Proc': [
                        'Multiply.Result.Z -> RerouteNode_1.Value',
                        'RerouteNode_1.Value -> Add.C'],
                    'Face_ControlBoard_CtrlRig': [
                        'MathFloatAdd_6_1.Result -> RerouteNode_19_1.Value',
                        'RerouteNode_19_1.Value -> SetControlVector2D_1_1.Vector.X'],
                }
                allowed = set()
                for name, edges in known.items():
                    rig_path = params.common_folder_path + '/Face/' + name
                    allowed.update(f'MetaHumanCharacterEditorSubsystem: {rig_path} : Cannot break link {edge} in package {rig_path}' for edge in edges)
                diagnostics = [line.strip().removeprefix('RuntimeError: ') for line in str(exc).splitlines() if line.strip()]
                if not diagnostics or not set(diagnostics).issubset(allowed):
                    raise
                REPORT['control_rig_migration_diagnostics'] = diagnostics
            unreal.log_flush()
            with assembly_log.open('rb') as stream:
                stream.seek(log_offset)
                build_log = stream.read().decode('utf-8', errors='replace')
            if 'LogMetaHumanCharacterEditor: Display: MetaHuman Character assembly succeeded' not in build_log:
                raise RuntimeError('The current engine invocation did not confirm successful assembly')
            REPORT['engine_assembly_succeeded'] = True
            # BuildMetaHuman leaves generated assets in memory. Persist only the
            # isolated output tree, then validate it before reporting success.
            if not EAL.save_directory(PROFILE_DATA['assembly_root'], only_if_is_dirty=False, recursive=True):
                raise RuntimeError('Unable to save all generated pilot assets')
            REPORT['generated_assets_saved'] = True
            save_report()
            validate_assembly(PROFILE_DATA, REPORT, build_started)
        else:
            raise ValueError('Unsupported action: ' + ACTION)
        save_character(character)
    finally:
        if subsystem.is_object_added_for_editing(character):
            subsystem.remove_object_to_edit(character)


try:
    save_report()
    main()
    REPORT['passed'] = True
    REPORT['status'] = 'complete'
except Exception as exc:
    REPORT['status'] = 'failed'
    REPORT['error'] = str(exc)
    save_report()
    raise
else:
    save_report()
    unreal.log('MH_PILOT_STAGE ' + json.dumps(REPORT))
