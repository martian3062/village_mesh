"""Compile and inspect only the generated pilot output, including rig migration."""
from pathlib import Path
import unreal


def validate_assembly(profile, report, not_before, save_packages=None):
    root = Path(unreal.Paths.project_dir())
    library = unreal.EditorAssetLibrary
    assets = library.list_assets(profile['assembly_root'], recursive=True, include_folder=False)
    compiled = []
    for asset_path in assets:
        asset = library.load_asset(asset_path)
        if isinstance(asset, unreal.Blueprint):
            if not unreal.BlueprintEditorLibrary.compile_blueprint(asset):
                raise RuntimeError('Generated Blueprint failed compilation: ' + asset_path)
            compiled.append(asset_path)
    report['compiled_blueprints'] = compiled
    if report.get('control_rig_migration_diagnostics'):
        expected_links = {
            'CR_MetaHuman_HeadMovement_IK_Proc': ('Multiply.Result.Z', 'Add.C'),
            'Face_ControlBoard_CtrlRig': ('MathFloatAdd_6_1.Result', 'SetControlVector2D_1_1.Vector.X'),
        }
        verified = {}
        for name, expected in expected_links.items():
            rig = library.load_asset(profile['assembly_root'] + '/Common/Face/' + name)
            graph = unreal.ControlRigBlueprintLibrary.get_model(rig)
            graphs = [graph] + list(graph.get_contained_graphs(True))
            matching_graphs = [model for model in graphs if model.find_pin(expected[0]) and model.find_pin(expected[1])]
            if len(matching_graphs) != 1:
                raise RuntimeError('Expected a unique graph for the reported reroute endpoints: ' + name)
            affected = matching_graphs[0]
            source_pin, target_pin = affected.find_pin(expected[0]), affected.find_pin(expected[1])
            connected = [pin.get_pin_path() for pin in target_pin.get_linked_source_pins()]
            if expected[0] not in connected:
                if connected:
                    raise RuntimeError('Refusing to replace an existing Control Rig input: ' + expected[1])
                # The engine diagnostics name both ends of a removed passthrough
                # reroute. Restore that exact numeric connection, only on our
                # generated copy, and only when its input is disconnected.
                controller = unreal.ControlRigBlueprintLibrary.get_controller(rig).get_controller_for_graph(affected)
                if not controller.add_link(expected[0], expected[1]):
                    raise RuntimeError('Could not restore the reported Control Rig connection: ' + name)
                unreal.ControlRigBlueprintLibrary.recompile_vm(rig)
                if not unreal.BlueprintEditorLibrary.compile_blueprint(rig):
                    raise RuntimeError('Repaired Control Rig did not compile: ' + name)
                if save_packages is None and not library.save_loaded_asset(rig, only_if_is_dirty=False):
                    raise RuntimeError('Repaired Control Rig could not be saved: ' + name)
                report.setdefault('restored_control_rig_links', []).append({'asset': rig.get_path_name(), 'source': expected[0], 'target': expected[1]})
            links = []
            for model in graphs:
                for link in model.get_links():
                    source, target = link.get_source_pin(), link.get_target_pin()
                    if not source or not target:
                        raise RuntimeError('Unresolved Control Rig graph link: ' + link.get_pin_path_representation())
                    links.append((source.get_pin_path(), target.get_pin_path()))
            verified[name] = expected in links
            report.setdefault('migration_link_evidence', {})[name] = [pair for pair in links if pair[0] == expected[0] or pair[1] == expected[1]]
            report.setdefault('migration_graph_inventory', {})[name] = {
                'graphs': len(graphs), 'links': len(links), 'sample': links[:5],
                'related': [pair for pair in links if any(token in str(pair) for token in ('Multiply', 'RerouteNode_1', 'MathFloatAdd_6_1', 'SetControlVector2D_1_1', 'Add.C'))],
            }
        report['migrated_direct_links_verified'] = verified
        if not all(verified.values()):
            raise RuntimeError('Control Rig reroute replacement links need review; saved assets are not yet accepted')
    saved = save_packages(profile['assembly_root'], True) if save_packages else library.save_directory(profile['assembly_root'], only_if_is_dirty=True, recursive=True)
    if not saved:
        raise RuntimeError('Unable to save compiled pilot assets')
    expected_actor = 'BP_' + profile['name']
    blueprints = [p for p in assets if p.rsplit('/', 1)[-1].split('.', 1)[0] == expected_actor]
    if not blueprints:
        raise RuntimeError('No assembled Manpreet actor Blueprint was found')
    fresh = []
    for asset_path in blueprints:
        package_path = asset_path.split('.', 1)[0].removeprefix('/Game/')
        disk_path = root / 'Content' / (package_path + '.uasset')
        if disk_path.exists() and disk_path.stat().st_mtime >= not_before - 1:
            fresh.append(asset_path)
    if not fresh:
        raise RuntimeError('Assembly produced no freshly saved actor Blueprint; cached older assets do not count as success')
    report['assembled_blueprints'] = blueprints
    report['fresh_assembled_blueprints'] = fresh
    report['saved_asset_count'] = len(assets)
    report['scope'] = 'Optimized '+profile.get('quality','Medium')+' assembly; no PIE, locomotion, packaging or performance claim'
