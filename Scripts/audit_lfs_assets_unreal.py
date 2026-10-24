"""Read-only package dependency audit for the published Unreal asset namespaces."""
import datetime
import json
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.project_dir())
NAMES = ('VillageMesh', 'VillageMeshV2', 'VillageMeshV25', 'VillageMeshV3', 'MetaHumanPilot')
PREFIXES = tuple('/Game/' + name + '/' for name in NAMES) + tuple(
    '/Game/' + external + '/' + name + '/'
    for external in ('__ExternalActors__', '__ExternalObjects__') for name in NAMES)
registry = unreal.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(True)
options = unreal.AssetRegistryDependencyOptions(
    include_soft_package_references=True, include_hard_package_references=True)
packages = set()
for prefix in PREFIXES:
    packages.update(str(asset.package_name) for asset in registry.get_assets_by_path(prefix.rstrip('/'), recursive=True))
missing, excluded, plugin_mounts = [], [], set()
for package in sorted(packages):
    for dependency in registry.get_dependencies(package, options):
        name = str(dependency)
        if name.startswith('/Game/'):
            if not name.startswith(PREFIXES):
                excluded.append({'package': package, 'dependency': name})
            elif not any((ROOT / 'Content' / (name.removeprefix('/Game/') + ext)).is_file() for ext in ('.uasset', '.umap')):
                missing.append({'package': package, 'dependency': name})
        elif name.startswith('/'):
            plugin_mounts.add(name.split('/')[1])
report = {
    'recorded_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'passed': bool(packages) and not excluded and not missing,
    'checked_packages': len(packages), 'namespaces': list(NAMES),
    'excluded_project_dependencies': excluded, 'missing_project_dependencies': missing,
    'installation_mounts': sorted(plugin_mounts),
    'scope': 'Read-only saved-asset registry audit, including hard and soft package references. Engine/plugin content is supplied by the licensed UE installation; not a clean-machine play or packaging test.'}
output = ROOT / 'Saved/LFS/dependency_audit.json'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
if not report['passed']:
    raise RuntimeError('LFS dependency audit failed; inspect Saved/LFS/dependency_audit.json')
unreal.log('LFS_DEPENDENCIES_OK packages=' + str(len(packages)))
