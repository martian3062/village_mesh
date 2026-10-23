"""Inventory engine plugins and enable a reproducible toolkit authoring profile.

This configures installed plugins; it does not install external services, acquire
licensed assets, train models, or claim their features are integrated in the map.
"""
import argparse
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
CORE = {"PCG": False, "ModelContextProtocol": True, "EditorToolset": True, "MCPClientToolset": True, "PCGToolset": True}
AUTHORING = {**CORE, "ProceduralVegetationEditor": True, "MeshTerrainMode": True,
    "USDImporter": True, "Water": False, "Landmass": True, "NiagaraFluids": False,
    "NNERuntimeORT": False, "LearningAgents": True, "MassAI": False,
    "StateTree": False, "SmartObjects": False, "PoseSearch": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-root", required=True, type=Path)
    parser.add_argument("--profile", choices=("core", "authoring"), default="core")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    engine_plugins = args.engine_root / "Engine/Plugins"
    if not engine_plugins.is_dir():
        parser.error("Engine root does not contain Engine/Plugins")
    available = {p.stem: p for p in engine_plugins.rglob("*.uplugin")}
    project_path = ROOT / "rural_pardeep.uproject"
    project = json.loads(project_path.read_text())
    plugins = {entry["Name"]: entry for entry in project["Plugins"]}
    desired = CORE if args.profile == "core" else AUTHORING
    report = []
    for name, editor_only in AUTHORING.items():
        path = available.get(name)
        experimental = bool(path and re.search(r'"IsExperimentalVersion"\s*:\s*true', path.read_text(encoding="utf-8-sig")))
        if args.apply and path and name in desired:
            plugins[name] = dict(Name=name, Enabled=True)
            if editor_only:
                plugins[name]["TargetAllowList"] = ["Editor"]
        elif args.apply and name not in desired:
            plugins[name] = dict(Name=name, Enabled=False)
        report.append(dict(plugin=name, installed=bool(path), experimental=experimental,
            enabled_in_project=plugins.get(name, {}).get("Enabled", False)))
    if args.apply:
        missing = [name for name in desired if name not in available]
        if missing:
            raise RuntimeError("Requested plugins unavailable: " + ", ".join(missing))
        project["Plugins"] = list(plugins.values())
        project_path.write_text(json.dumps(project, indent=2) + "\n")
    result = dict(profile=args.profile, applied=args.apply, plugins=report,
        external_on_path={name: bool(shutil.which(name)) for name in ("blender", "gdal_translate", "qgis", "git-lfs")},
        cesium_installed="CesiumForUnreal" in available)
    output = ROOT / "Saved/VillageMeshGenerated/toolkit_inventory.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
