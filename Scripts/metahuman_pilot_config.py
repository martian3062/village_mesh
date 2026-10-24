"""Offline configuration and installation checks for the isolated MetaHuman pilot."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / 'Assets/MetaHumans/manpreet.json'
PLUGIN_NAMES = ('MetaHumanCharacter', 'MetaHumanSDK', 'HairStrands', 'RigLogic',
                'ChaosClothAsset', 'ChaosOutfitAsset')


def read_profile(path=PROFILE):
    value = json.loads(Path(path).read_text(encoding='utf-8'))
    if value['schema_version'] != 1 or not value['fictional'] or not value['adult']:
        raise ValueError('The pilot must be a fictional adult with schema version 1')
    if value['integration'] != 'isolated_pilot' or value['resident_id'] is not None:
        raise ValueError('Resident replacement requires a separately validated integration')
    for key in ('character_asset', 'assembly_root'):
        if not value[key].startswith('/Game/MetaHumanPilot/') or '..' in value[key]:
            raise ValueError('Pilot outputs must stay in /Game/MetaHumanPilot')
    if not 140 <= value['height_cm'] <= 210:
        raise ValueError('Pilot height is outside the reviewed design range')
    if any(not 0 <= value['skin'][k] <= 1 for k in ('u', 'v', 'roughness')):
        raise ValueError('Skin coordinates and roughness must be in [0, 1]')
    if value['assembly'] != {'pipeline': 'optimized', 'quality': 'medium'}:
        raise ValueError('This pilot targets the optimized Medium assembly')
    for slot, asset in value['wardrobe'].items():
        if asset is not None and not asset.startswith(('/MetaHumanCharacter/', '/Game/MetaHumanPilot/')):
            raise ValueError('Wardrobe items require an explicitly reviewed asset namespace: ' + slot)
    return value


def check_install(engine_root):
    engine = Path(engine_root)
    optional = engine / 'Engine/Plugins/MetaHuman/MetaHumanCharacter/Content/Optional'
    descriptor = json.loads((ROOT / 'rural_pardeep.uproject').read_text())
    enabled = {p['Name'] for p in descriptor['Plugins'] if p.get('Enabled')}
    version = json.loads((engine / 'Engine/Build/Build.version').read_text())
    paths = sorted(optional.rglob('WI_*.uasset')) if optional.exists() else []
    items = ['/MetaHumanCharacter/Optional/' + p.relative_to(optional).with_suffix('').as_posix() for p in paths]
    profile = read_profile()
    blockers = []
    if not optional.exists() or not items:
        blockers.append('Install MetaHuman Creator Core Data from UE 5.8 Options in Epic Games Launcher')
    missing_plugins = sorted(set(PLUGIN_NAMES) - enabled)
    if missing_plugins:
        blockers.append('Enable plugins: ' + ', '.join(missing_plugins))
    return {
        'engine_version': '.'.join(str(version[k]) for k in ('MajorVersion', 'MinorVersion', 'PatchVersion')),
        'optional_content_present': optional.exists(),
        'wardrobe_item_count': len(items),
        'wardrobe_items': items,
        'required_plugins_enabled': not missing_plugins,
        'installation_ready': not blockers,
        'blockers': blockers,
        'unselected_wardrobe_slots': [s for s in profile['required_wardrobe_slots'] if not profile['wardrobe'].get(s)],
        'cloud_authentication': 'not_verified',
        'pilot_assembled': False,
        'scope': 'Filesystem/configuration preflight; no rig, appearance or runtime validation'
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine-root', default=r'E:\U.E\UE_5.8')
    args = parser.parse_args()
    result = check_install(args.engine_root)
    output = ROOT / 'Saved/MetaHumanPilot/preflight.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'wardrobe_items'}, indent=2))
    return 0 if result['installation_ready'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
