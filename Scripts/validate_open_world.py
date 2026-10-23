"""Run inside Unreal to verify the portable map has no legacy-art dependencies."""
import json
from pathlib import Path
import unreal

LEVEL = "/Game/VillageMesh/Lvl_PandoriNijjaran_WP"
registry = unreal.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(True)
options = unreal.AssetRegistryDependencyOptions(
    include_soft_package_references=True, include_hard_package_references=True)
external = registry.get_assets_by_path("/Game/__ExternalActors__/VillageMesh/Lvl_PandoriNijjaran_WP", recursive=True)
pending, visited, invalid = [LEVEL, "/Game/VillageMesh/Lvl_PandoriNijjaran"] + [str(a.package_name) for a in external], set(), []
while pending:
    package = pending.pop()
    if package in visited:
        continue
    visited.add(package)
    for dependency in registry.get_dependencies(package, options):
        name = str(dependency)
        if name.startswith("/Game/"):
            if not name.startswith(("/Game/VillageMesh/", "/Game/__ExternalActors__/VillageMesh/", "/Game/__ExternalObjects__/VillageMesh/")):
                invalid.append(name)
            else:
                pending.append(name)
if invalid:
    raise RuntimeError("Nonportable dependencies: " + repr(sorted(set(invalid))))
report = dict(map=LEVEL, checked_packages=len(visited), legacy_dependencies=invalid)
path = Path(unreal.Paths.project_saved_dir()) / "VillageMeshGenerated/portability.json"
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(report, indent=2))
unreal.log("VILLAGE_MESH_PORTABLE_OK " + json.dumps(report))
