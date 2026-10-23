"""Run inside Unreal to verify the portable map has no legacy-art dependencies."""
import json
from pathlib import Path
import unreal

IS_V2 = '-VillageV2' in unreal.SystemLibrary.get_command_line()
NAMESPACE = '/Game/VillageMeshV2' if IS_V2 else '/Game/VillageMesh'
SOURCE = NAMESPACE + ('/Lvl_PandoriV2' if IS_V2 else '/Lvl_PandoriNijjaran')
LEVEL = SOURCE + '_WP'
root = Path(unreal.Paths.project_dir())
approved = json.loads((root/'Assets/Architecture/authored_content.json').read_text())['approved_packages'] if IS_V2 else []
registry = unreal.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(True)
options = unreal.AssetRegistryDependencyOptions(
    include_soft_package_references=True, include_hard_package_references=True)
external = registry.get_assets_by_path(LEVEL.replace('/Game/','/Game/__ExternalActors__/'), recursive=True)
pending, visited, invalid = [LEVEL, SOURCE] + [str(a.package_name) for a in external], set(), []
while pending:
    package = pending.pop()
    if package in visited:
        continue
    visited.add(package)
    for dependency in registry.get_dependencies(package, options):
        name = str(dependency)
        if name.startswith("/Game/"):
            if not (name in approved or name.startswith((NAMESPACE+'/', NAMESPACE.replace('/Game/','/Game/__ExternalActors__/')+'/', NAMESPACE.replace('/Game/','/Game/__ExternalObjects__/')+'/'))):
                invalid.append(name)
            else:
                pending.append(name)
if invalid:
    raise RuntimeError("Nonportable dependencies: " + repr(sorted(set(invalid))))
report = dict(map=LEVEL, checked_packages=len(visited), legacy_dependencies=invalid)
path = Path(unreal.Paths.project_saved_dir()) / ('VillageMeshV2' if IS_V2 else 'VillageMeshGenerated') / 'portability.json'
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(report, indent=2))
unreal.log("VILLAGE_MESH_PORTABLE_OK " + json.dumps(report))
