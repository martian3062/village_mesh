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

PROFILE_DATA = read_profile()
OUTPUT = ROOT / 'Saved/MetaHumanPilot'
OUTPUT.mkdir(parents=True, exist_ok=True)
EAL = unreal.EditorAssetLibrary
match = re.search(r'-MHPilotAction=(\w+)', unreal.SystemLibrary.get_command_line())
ACTION = match.group(1) if match else 'Inspect'
REPORT = {'action': ACTION, 'passed': False,
          'started_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'profile_sha256': hashlib.sha256(PROFILE.read_bytes()).hexdigest(),
          'character_asset': PROFILE_DATA['character_asset']}


def save_report():
    (OUTPUT / (ACTION.lower() + '.json')).write_text(json.dumps(REPORT, indent=2) + '\n')


def require_core_data():
    folder = Path(unreal.Paths.engine_plugins_dir()) / 'MetaHuman/MetaHumanCharacter/Content/Optional'
    if not folder.exists() or not any(folder.rglob('WI_*.uasset')):
        raise RuntimeError('MetaHuman Creator Core Data is missing. Install it through the UE 5.8 Options menu before this stage.')


def save_character(character):
    if not EAL.save_loaded_asset(character):
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
        REPORT['can_assemble'] = bool(character and subsystem.can_build_meta_human(character, True))
        REPORT['scope'] = 'API and asset inventory; does not certify the character appearance or performance'
        return
    if not character:
        raise RuntimeError('Create the pilot character first')
    require_core_data()
    if ACTION == 'Edit':
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([character])
        REPORT['scope'] = 'Creator editor opened; appearance and cloud authentication require review'
        return
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
            missing = [s for s in PROFILE_DATA['required_wardrobe_slots'] if not PROFILE_DATA['wardrobe'].get(s)]
            if missing:
                raise RuntimeError('Select installed wardrobe paths in Assets/MetaHumans/manpreet.json for: ' + ', '.join(missing))
            wardrobe = {s: EAL.load_asset(p) for s, p in PROFILE_DATA['wardrobe'].items() if p}
            if any(not item for item in wardrobe.values()):
                raise RuntimeError('At least one selected wardrobe asset is missing')
            for slot, item in wardrobe.items():
                key = character.internal_collection.try_add_item_from_wardrobe_item(slot, item)
                selection = unreal.MetaHumanPipelineSlotSelection(slot_name=slot, selected_item=key)
                character.internal_collection.default_instance.try_add_slot_selection(selection)
            subsystem.assemble_for_preview(character)
            REPORT['wardrobe'] = PROFILE_DATA['wardrobe']
            REPORT['scope'] = 'Wardrobe selections applied; fitting and intersections still require visual review'
        elif ACTION == 'Rig':
            request = unreal.MetaHumanCharacterAutoRiggingRequestParams()
            request.blocking = True
            request.report_progress = False
            # Blendshape state provides an observable success condition in the Python API.
            request.rig_type = unreal.MetaHumanRigType.JOINTS_AND_BLENDSHAPES
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
            subsystem.build_meta_human(character, params)
            assets = EAL.list_assets(PROFILE_DATA['assembly_root'], recursive=True, include_folder=False)
            blueprints = [p for p in assets if p.rsplit('/', 1)[-1].startswith('BP_') and 'Manpreet' in p]
            if not blueprints:
                raise RuntimeError('No assembled Manpreet actor Blueprint was found')
            fresh = []
            for asset_path in blueprints:
                package_path = asset_path.split('.', 1)[0].removeprefix('/Game/')
                disk_path = ROOT / 'Content' / (package_path + '.uasset')
                if disk_path.exists() and disk_path.stat().st_mtime >= build_started - 1:
                    fresh.append(asset_path)
            if not fresh:
                raise RuntimeError('Assembly produced no freshly saved actor Blueprint; cached older assets do not count as success')
            REPORT['assembled_blueprints'] = blueprints
            REPORT['fresh_assembled_blueprints'] = fresh
            REPORT['scope'] = 'Optimized Medium assembly; no PIE, locomotion, packaging or performance claim'
        else:
            raise ValueError('Unsupported action: ' + ACTION)
        save_character(character)
    finally:
        if subsystem.is_object_added_for_editing(character):
            subsystem.remove_object_to_edit(character)


try:
    main()
    REPORT['passed'] = True
except Exception as exc:
    REPORT['error'] = str(exc)
    save_report()
    raise
else:
    save_report()
    unreal.log('MH_PILOT_STAGE ' + json.dumps(REPORT))
